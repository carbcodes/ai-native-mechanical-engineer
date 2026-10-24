"""`mechy agent run <task-id>` and `mechy plan`."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

import yaml

from ..events import Events, now_iso
from ..project import Project, git_commit, load_yaml
from . import cards as C
from .providers import build_invocation, parse_stream_line, resolve_provider

VARIANT_IN_PATH = re.compile(r"(?:design|control|docs)/(v\d+[a-z0-9_-]*)")
AGENT_TIMEOUT_S = 3600


def worker_prompt(card: dict, summary: str) -> str:
    body = yaml.safe_dump({k: v for k, v in card.items() if not k.startswith("_")}, sort_keys=False)
    return (f"Your task card (tasks/{card['id']}.yaml):\n\n```yaml\n{body}```\n\n"
            f"Do the task. Read only the inputs. Write the outputs, then write {summary} "
            f"(<= 300 words). You are done when: {card['done_when']}")


GLOBAL_TOOLS = ("intake.digest",)     # not per variant: run once per card


def _run_none(project: Project, card: dict, ev: Events) -> dict:
    """provider: none: run the card's tools directly (cad.build, sim.catch, render.views, control.gen,
    doc.build per variant; intake.digest once)."""
    from .. import tools as T
    paths = " ".join((card.get("inputs") or []) + (card.get("outputs") or []))
    variants = list(dict.fromkeys(VARIANT_IN_PATH.findall(paths))) or [project.chosen() or "v1"]
    summaries, results = [], []
    for tool in card.get("tools") or []:
        if tool in GLOBAL_TOOLS:
            ev.progress(card["id"], tool)
            r = T.intake_digest_all(project)
            if r.get("errors") and not r.get("digested"):
                raise RuntimeError(f"{tool}: " + "; ".join(f"{e['source']}: {e['error']}" for e in r["errors"]))
            results.append({"tool": tool, "digested": len(r.get("digested") or []),
                            "errors": len(r.get("errors") or [])})
            summaries += [d["note"] for d in r.get("digested") or [] if d.get("note")]
            continue
        for v in variants:
            ev.progress(card["id"], f"{tool} {v}")
            if tool == "cad.build":
                r = T.cad_build(project, v)
                summaries.append(f"design/{v}/summary.md")
            elif tool == "sim.catch":
                task = card["id"] if len(variants) == 1 else f"{card['id']}-{v}"
                r = T.sim_catch(project, v, int(card.get("throws", 200)), int(card.get("seed", 0)), task)
                summaries.append(f"sim/{task}/summary.md")
            elif tool == "render.views":
                r = T.render_views(project, v)
            elif tool == "control.gen":
                r = T.control_gen(project, v, card.get("board"))
                summaries.append(f"control/{v}/summary.md")
            elif tool == "doc.build":
                r = T.doc_build(project, v, card.get("only"), bool(card.get("print_paper", False)))
            else:
                raise RuntimeError(f"provider none cannot run tool {tool!r}")
            if r.get("ok") is False:
                raise RuntimeError(f"{tool} {v}: {r.get('error')}")
            results.append({"tool": tool, "variant": v, **{k: r[k] for k in ("catch_rate", "reach_rate") if k in r}})
    summ = C.summary_path_for(card)
    sp = project.path(summ)
    if not sp.exists() or sp.is_dir():
        if len(summaries) == 1 and project.path(summaries[0]).exists():
            summ = summaries[0]
        else:
            sp.parent.mkdir(parents=True, exist_ok=True)
            lines = [f"# {card['id']}", "", card["goal"], ""]
            for s in summaries:
                if project.path(s).exists():
                    lines += [project.path(s).read_text(), ""]
            sp.write_text("\n".join(lines)[:4000])
    return {"summary": summ, "results": results, "tokens": None, "model": None, "cost_usd": None}


def _run_llm(project: Project, card: dict, provider: str, prompt: str, ev: Events) -> dict:
    inv = build_invocation(project, card, prompt, provider)
    run_dir = project.path(".mechy", "runs")
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / f"{card['id']}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
    usage, model, err, cost, final = None, inv.model, None, None, False
    try:
        proc = subprocess.Popen(inv.argv, cwd=inv.cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, bufsize=1)
    except FileNotFoundError as e:
        raise RuntimeError(f"{provider} CLI not found ({inv.argv[0]}); install it or set "
                           f"MECHY_{provider.upper()}_BIN / MECHY_PROVIDER") from e
    t_start = time.time()
    with open(log_path, "w") as log:
        assert proc.stdout is not None
        for line in proc.stdout:
            log.write(line)
            info = parse_stream_line(provider, line)
            if info.get("text"):
                ev.emit("agent.output", task=card["id"], text=info["text"][:240])
            if info.get("usage"):
                usage = info["usage"]
            if info.get("model"):
                model = info["model"]
            if info.get("cost_usd") is not None:
                cost = info["cost_usd"]
            if info.get("error"):
                err = info["error"]
            final = final or bool(info.get("final"))
            if time.time() - t_start > AGENT_TIMEOUT_S:
                proc.kill()
                err = f"timed out after {AGENT_TIMEOUT_S}s"
                break
    rc = proc.wait()
    stderr = proc.stderr.read() if proc.stderr else ""
    if rc != 0 and not err:
        err = f"{provider} exited with {rc}: {stderr.strip()[-400:]}"
    tokens = None
    if usage:
        tokens = {k: v for k, v in usage.items() if k.endswith("tokens") and isinstance(v, (int, float))}
    return {"error": err, "tokens": tokens, "model": model, "cost_usd": cost,
            "log": str(log_path.relative_to(project.root))}


def run_task(project: Project, task_id: str, events: Events | None = None,
             provider_override: str | None = None, commit: bool = True) -> dict:
    ev = events or Events(project.root, quiet=True)
    card = C.load_card(project, task_id)
    provider = resolve_provider(card["provider"], provider_override)
    summ = C.summary_path_for(card)
    card["_summary"] = summ
    C.write_status(project, task_id, "running", summary=None)
    ev.emit("task.started", task=task_id)
    t0 = time.time()
    res: dict = {}
    error = None
    try:
        if provider == "none":
            res = _run_none(project, card, ev)
            summ = res["summary"]
        else:
            res = _run_llm(project, card, provider, worker_prompt(card, summ), ev)
            error = res.get("error")
    except Exception as e:  # noqa: BLE001
        error = f"{type(e).__name__}: {e}"
    duration = round(time.time() - t0, 2)
    if not error:
        missing = [o for o in card["outputs"] if not project.path(o).exists()]
        if missing:
            error = f"outputs missing: {', '.join(missing)}"
        elif not project.path(summ).is_file():
            error = f"summary missing: {summ}"
    project.append_usage({"ts": now_iso(), "task": task_id, "provider": provider, "model": res.get("model"),
                          "duration_s": duration, "tokens": res.get("tokens"), "cost_usd": res.get("cost_usd")})
    if error:
        C.write_status(project, task_id, "failed", error=error, summary=summ if project.path(summ).is_file() else None)
        ev.emit("task.failed", task=task_id, error=error)
        return {"ok": False, "task": task_id, "provider": provider, "error": error, "duration_s": duration}
    C.write_status(project, task_id, "done", summary=summ)
    ev.emit("task.done", task=task_id, summary=summ)
    if commit:
        git_commit(project.root, f"{task_id}: {card['goal'][:60]}")
    return {"ok": True, "task": task_id, "provider": provider, "summary": summ, "duration_s": duration,
            **({"log": res["log"]} if res.get("log") else {})}


# ------------------------------------------------------------------ planner
def pending_inbox(project: Project) -> list[Path]:
    d = project.path("inbox")
    return sorted(p for p in d.glob("*.md") if p.is_file()) if d.is_dir() else []


def planner_prompt(project: Project, inbox: list[Path]) -> str:
    parts = ["Plan the next steps for this project. Brief, requirements and hardware:"]
    for rel in ("brief.md", "requirements.yaml", "decisions.md", "hw/motors.yaml", "hw/drivers.yaml"):
        p = project.path(rel)
        if p.exists():
            parts.append(f"\n## {rel}\n\n{p.read_text()[:6000]}")
    if inbox:
        parts.append("\n## New requests from the user (inbox)\n")
        for p in inbox:
            parts.append(f"### inbox/{p.name}\n\n{p.read_text()[:4000]}")
    cards, _ = C.load_cards(project)
    if cards:
        parts.append("\n## Existing task cards\n")
        for cid, c in cards.items():
            st = C.read_status(project, cid)
            parts.append(f"- {cid} [{st['state']}] {c['goal']}" + (f" (summary: {st['summary']})" if st.get("summary") else ""))
    parts.append("\nWrite new task cards in tasks/, ask questions with question_ask, present options with "
                 "options_present, and finish with tasks/summary.md (<= 300 words).")
    return "\n".join(parts)


def digest_pending(project: Project, ev: Events) -> dict | None:
    """Digest inspiration that is not digested yet (links.yaml, media in inspiration/), so the planner
    and research cards see the notes. Failures (no network, missing yt-dlp) are reported, never raised."""
    from .. import tools as T
    try:
        items = T.intake_pending(project)["pending"]
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}
    if not items:
        return None
    ev.emit("task.started", task="intake")
    ev.progress("intake", f"digesting {len(items)} inspiration source(s)")
    try:
        r = T.intake_digest_all(project, events=ev)
    except Exception as e:  # noqa: BLE001
        r = {"digested": [], "errors": [{"source": "*", "error": f"{type(e).__name__}: {e}"}]}
    out = {"digested": [d["note"] for d in r.get("digested") or []], "errors": r.get("errors") or []}
    if out["errors"] and not out["digested"]:
        ev.emit("task.failed", task="intake", error="; ".join(e["error"] for e in out["errors"])[:400])
    else:
        ev.emit("task.done", task="intake", summary=(out["digested"] or [None])[0])
    return out


def run_planner(project: Project, events: Events | None = None, provider: str = "claude",
                intake: bool = True) -> dict:
    ev = events or Events(project.root, quiet=True)
    prov = resolve_provider(provider)
    if prov == "none":
        raise RuntimeError("the planner needs an LLM provider (claude or codex)")
    intake_res = digest_pending(project, ev) if intake else None
    inbox = pending_inbox(project)
    existing = {p.name for p in project.path("tasks").glob("*.yaml")}
    card = {"id": "T000-planner", "role": "planner", "provider": provider, "tier": "strong",
            "goal": "Plan the next task cards from the brief, requirements, inbox and summaries.",
            "inputs": ["brief.md", "requirements.yaml", "decisions.md", "hw/motors.yaml"] +
                      [f"inbox/{p.name}" for p in inbox],
            "tools": ["project.summary", "question.ask", "options.present", "cad.params_get", "cad.params_set",
                      "ik.solve", "motor.check", "intake.digest", "intake.pending"],
            "outputs": [], "depends_on": [], "done_when": "New task cards are written and tasks/summary.md exists.",
            "_summary": "tasks/summary.md"}
    ev.emit("task.started", task=card["id"])
    t0 = time.time()
    res = _run_llm(project, card, prov, planner_prompt(project, inbox), ev)
    duration = round(time.time() - t0, 2)
    project.append_usage({"ts": now_iso(), "task": card["id"], "provider": prov, "model": res.get("model"),
                          "duration_s": duration, "tokens": res.get("tokens"), "cost_usd": res.get("cost_usd")})
    if res.get("error"):
        ev.emit("task.failed", task=card["id"], error=res["error"])
        return {"ok": False, "error": res["error"], "duration_s": duration,
                **({"intake": intake_res} if intake_res else {})}
    new_cards = sorted({p.name for p in project.path("tasks").glob("*.yaml")} - existing)
    bad = {}
    for name in new_cards:
        try:
            C.validate(load_yaml(project.path("tasks", name)), name)
        except Exception as e:  # noqa: BLE001
            bad[name] = str(e)
    for name in new_cards:
        ev.file_written(project.path("tasks", name))
    for q in project.path("questions").glob("*.yaml"):
        if q.stat().st_mtime >= t0:
            ev.emit("question.asked", id=q.stem)
    for o in project.path("options").glob("*.yaml"):
        if o.stat().st_mtime >= t0:
            ev.emit("options.presented", id=o.stem)
    done_dir = project.path("inbox", "done")
    if inbox:
        done_dir.mkdir(parents=True, exist_ok=True)
        for p in inbox:
            shutil.move(str(p), done_dir / p.name)
    ev.emit("task.done", task=card["id"], summary="tasks/summary.md")
    git_commit(project.root, "planner: " + (", ".join(c.removesuffix(".yaml") for c in new_cards) or "no new cards"))
    return {"ok": not bad, "new_cards": [c.removesuffix(".yaml") for c in new_cards], "invalid_cards": bad,
            "inbox_processed": [p.name for p in inbox], "summary": "tasks/summary.md", "duration_s": duration,
            **({"intake": intake_res} if intake_res else {})}
