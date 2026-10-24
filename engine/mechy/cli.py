"""`mechy` command line (contracts section 3)."""

from __future__ import annotations

import argparse
import os
import sys
import traceback

from .events import Events
from .project import EXAMPLES, Project, ProjectError, find_project, init_project


def _common(p: argparse.ArgumentParser, suppress: bool) -> None:
    d = argparse.SUPPRESS if suppress else None
    p.add_argument("--project", default=d, help="project folder (default: cwd or its nearest parent project)")
    p.add_argument("--json", action="store_true", default=argparse.SUPPRESS if suppress else False,
                   help="print events and the result as JSON lines on stdout")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="mechy", description="Mechy engine")
    _common(ap, False)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, **kw):
        sp = sub.add_parser(name, **kw)
        _common(sp, True)
        return sp

    p = add("init", help="create a project folder")
    p.add_argument("dir")
    p.add_argument("--example", choices=list(EXAMPLES), default=None)
    p.add_argument("--name", default=None)
    p.add_argument("--goal", default=None, help="goal text: brief.md '## Goal' (blank) or '## User notes' (examples)")
    p.add_argument("--no-git", action="store_true")

    p = add("cad", help="CAD commands")
    csub = p.add_subparsers(dest="cad_cmd", required=True)
    b = csub.add_parser("build", help="params.yaml -> step/stl/glb/xml/thumb")
    _common(b, True)
    b.add_argument("variant")

    p = add("sim", help="simulation commands")
    ssub = p.add_subparsers(dest="sim_cmd", required=True)
    c = ssub.add_parser("catch", help="run the catch sweep")
    _common(c, True)
    c.add_argument("variant")
    c.add_argument("--throws", type=int, default=200)
    c.add_argument("--seed", type=int, default=0)
    c.add_argument("--task", default=None, help="task id; output goes to sim/<task>/ (default catch-<variant>)")
    c.add_argument("--workers", type=int, default=None, help="processes (default: CPU count)")
    c.add_argument("--video", action="store_true", help="try to render video.mp4 (needs headless GL)")
    c.add_argument("--microsteps", type=int, default=None, help="override the driver microstep setting")

    c = ssub.add_parser("pick", help="pick-and-place study: payload map, cycle time, motor load")
    _common(c, True)
    c.add_argument("variant")
    c.add_argument("--task", default=None, help="task id; output goes to sim/<task>/ (default pick-<variant>)")
    c.add_argument("--payload", type=float, default=None, help="payload in kg (default: requirements pick.payload_kg)")
    c.add_argument("--microsteps", type=int, default=None, help="override the driver microstep setting")

    p = add("control", help="firmware and host control code")
    ksub = p.add_subparsers(dest="control_cmd", required=True)
    g = ksub.add_parser("gen", help="params + hw -> control/<variant>/ (Arduino firmware, host tracker, README)")
    _common(g, True)
    g.add_argument("variant")
    g.add_argument("--board", choices=["uno_cnc", "mega_ramps"], default=None,
                   help="controller board (default: from hw/drivers.yaml controller, else uno_cnc)")

    p = add("doc", help="documents")
    dsub = p.add_subparsers(dest="doc_cmd", required=True)
    d = dsub.add_parser("build", help="docs/<variant>/build_guide.pdf and report.pdf (Typst; sources kept)")
    _common(d, True)
    d.add_argument("variant")
    d.add_argument("--only", choices=["build_guide", "report"], default=None, help="build one document")
    d.add_argument("--print", dest="print_paper", action="store_true",
                   help="white paper for home printing (default: the drawing-sheet paper colour)")

    from .intake.register import add_intake_parser
    add_intake_parser(sub, _common)

    p = add("agent", help="agent commands")
    asub = p.add_subparsers(dest="agent_cmd", required=True)
    r = asub.add_parser("run", help="run one task card through its provider")
    _common(r, True)
    r.add_argument("task_id")
    r.add_argument("--provider", default=None, help="override the card's provider")

    p = add("plan", help="run the planner (digests pending inspiration first): write task cards, questions, options")
    p.add_argument("--provider", default="claude")
    p.add_argument("--no-intake", action="store_true", help="skip digesting pending inspiration first")

    p = add("run", help="scheduler: digest pending inspiration, then run all ready task cards")
    p.add_argument("--no-intake", action="store_true", help="skip digesting pending inspiration first")
    p.add_argument("--jobs", type=int, default=3)
    p.add_argument("--max-rounds", type=int, default=50)

    add("mcp", help="start the mechy-tools MCP server over stdio")
    add("doctor", help="check CLIs, logins, Python deps and mechy_core")

    p = add("accounts", help="provider accounts")
    asub2 = p.add_subparsers(dest="accounts_cmd", required=True)
    st = asub2.add_parser("status", help="installed/version/login per provider CLI")
    _common(st, True)

    p = add("history", help="project version history (git)")
    hsub = p.add_subparsers(dest="history_cmd", required=True)
    hl = hsub.add_parser("list", help="commits + dirty files")
    _common(hl, True)
    hl.add_argument("--path", default=None, help="only commits touching this path")
    hl.add_argument("--limit", type=int, default=100)
    hs = hsub.add_parser("show", help="write a file's content at a commit")
    _common(hs, True)
    hs.add_argument("sha")
    hs.add_argument("path")
    hs.add_argument("--out", required=True)
    hd = hsub.add_parser("diff", help="patch and per-file stats for a commit vs its parent")
    _common(hd, True)
    hd.add_argument("sha")
    hd.add_argument("--path", default=None)
    hn = hsub.add_parser("snapshot", help="commit all current changes")
    _common(hn, True)
    hn.add_argument("-m", "--message", required=True)
    hr = hsub.add_parser("restore", help="restore files from a commit (new commit; never rewrites history)")
    _common(hr, True)
    hr.add_argument("sha")
    hr.add_argument("--path", default=None)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    json_out = bool(getattr(args, "json", False))

    if args.cmd == "mcp":
        from .mcp_server import serve
        root = args.project or os.environ.get("MECHY_PROJECT") or os.getcwd()
        serve(root)
        return 0

    if args.cmd == "init":
        ev = Events(None, json_stdout=json_out)
        try:
            proj = init_project(args.dir, example=args.example, name=args.name, goal=args.goal,
                                events=ev, git=not args.no_git)
        except ProjectError as e:
            ev.result(ok=False, error=str(e))
            return 1
        ev.result(ok=True, project=str(proj.root), example=args.example, name=proj.meta()["name"])
        return 0

    proj = find_project(args.project)
    ev = Events(proj.root, json_stdout=json_out)
    try:
        if args.cmd == "doctor":
            from .doctor import doctor
            res = doctor(proj if proj.exists() else None)
            ev.result(ok=res["ok"], **{k: v for k, v in res.items() if k != "ok"})
            return 0 if res["ok"] else 1
        if args.cmd == "accounts":
            from .accounts import status_all
            ev.result(ok=True, accounts=status_all())
            return 0
        proj.require()
        if args.cmd == "cad":
            from .cad.build import cad_build
            res = cad_build(proj, args.variant, ev)
        elif args.cmd == "sim" and args.sim_cmd == "pick":
            from .sim.pick import run_pick
            res = run_pick(proj, args.variant, task_id=args.task, events=ev, microsteps=args.microsteps,
                           payload_kg=args.payload)
        elif args.cmd == "sim":
            from .sim.catch import run_catch
            res = run_catch(proj, args.variant, throws=args.throws, seed=args.seed, task_id=args.task,
                            workers=args.workers, video=args.video, events=ev,
                            microsteps=args.microsteps)
        elif args.cmd == "control":
            from .control.generate import control_gen
            cmd = f"mechy control gen {args.variant}" + (f" --board {args.board}" if args.board else "")
            res = control_gen(proj, args.variant, board=args.board, events=ev, command=cmd)
        elif args.cmd == "doc":
            from .docgen import doc_build
            res = doc_build(proj, args.variant, events=ev, which=args.only or "all", paper="white" if args.print_paper else "sheet")
        elif args.cmd == "agent":
            from .agents.runner import run_task
            res = run_task(proj, args.task_id, events=ev, provider_override=args.provider)
        elif args.cmd == "plan":
            from .agents.runner import run_planner
            res = run_planner(proj, events=ev, provider=args.provider, intake=not args.no_intake)
        elif args.cmd == "intake":
            from .intake.register import run_intake_cli
            res = run_intake_cli(proj, args, ev)
        elif args.cmd == "run":
            from .agents.scheduler import run_all
            res = run_all(proj, jobs=args.jobs, events=ev, max_rounds=args.max_rounds, intake=not args.no_intake)
        elif args.cmd == "history":
            from . import history
            res = history.run(proj, args, ev)
        else:  # pragma: no cover
            raise SystemExit(f"unknown command {args.cmd}")
    except Exception as e:  # noqa: BLE001 - every failure becomes a result line
        if os.environ.get("MECHY_DEBUG"):
            traceback.print_exc()
        ev.result(ok=False, error=f"{type(e).__name__}: {e}")
        return 1
    ok = bool(res.pop("ok", True)) if isinstance(res, dict) else True
    ev.result(ok=ok, **res)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
