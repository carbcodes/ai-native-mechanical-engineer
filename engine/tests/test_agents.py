import json

import yaml

from mechy.agents.providers import allowed_mcp_tools, build_invocation, resolve_provider
from conftest import mechy

FAKE = {"MECHY_FAKE_PROVIDER": "1", "MECHY_FAKE_DELAY": "0.05"}


def card(path, **kw):
    path.write_text(yaml.safe_dump(kw, sort_keys=False))


def test_scheduler_with_fake_provider(project):
    t = project.path("tasks")
    card(t / "T001-research-a.yaml", id="T001-research-a", role="research", provider="claude", tier="fast",
         goal="A.", inputs=["brief.md"], tools=[], outputs=["research/a/notes.md"], depends_on=[],
         done_when="notes exist.")
    card(t / "T002-research-b.yaml", id="T002-research-b", role="research", provider="codex", tier="fast",
         goal="B.", inputs=[], tools=[], outputs=["research/b/notes.md"], depends_on=[], done_when="x")
    card(t / "T003-docs-c.yaml", id="T003-docs-c", role="docs", provider="claude", goal="C.",
         outputs=["docs/c.md"], depends_on=["T001-research-a", "T002-research-b"], done_when="x")
    card(t / "T004-docs-fail.yaml", id="T004-docs-fail", role="docs", provider="claude", goal="FAIL now.",
         outputs=["docs/d.md"], depends_on=[], done_when="x")
    card(t / "T005-docs-blocked.yaml", id="T005-docs-blocked", role="docs", provider="claude", goal="E.",
         outputs=["docs/e.md"], depends_on=["T004-docs-fail"], done_when="x")
    code, events, res = mechy("run", "--jobs", "3", "--project", str(project.root), env=FAKE)
    assert res["ok"] is False and code == 1
    assert res["ran"] == {"T001-research-a": "done", "T002-research-b": "done", "T003-docs-c": "done",
                          "T004-docs-fail": "failed", "T005-docs-blocked": "blocked"}
    st = json.loads(project.path("tasks/T003-docs-c.status.json").read_text())
    assert st["state"] == "done" and st["summary"] == "docs/summary.md" and st["started"] and st["finished"]
    assert project.path("research/a/summary.md").exists() and project.path("docs/c.md").exists()
    # T003 starts only after both dependencies finished
    order = [e for e in events if e["type"] in ("task.started", "task.done")]
    i3 = next(i for i, e in enumerate(order) if e["type"] == "task.started" and e["task"] == "T003-docs-c")
    done_before = {e["task"] for e in order[:i3] if e["type"] == "task.done"}
    assert {"T001-research-a", "T002-research-b"} <= done_before
    usage = [json.loads(l) for l in project.path(".mechy/usage.jsonl").read_text().splitlines()]
    assert len(usage) == 4 and all(u["provider"] == "fake" for u in usage)
    assert usage[0]["tokens"]["input_tokens"] > 0
    assert any(e["type"] == "agent.output" for e in events)


def test_agent_run_none_provider_builds_cad(project):
    card(project.path("tasks/T010-cad-v1.yaml"), id="T010-cad-v1", role="cad", provider="none", goal="Build v1.",
         inputs=["design/v1/params.yaml"], tools=["cad.build"], outputs=["design/v1/arm.xml"],
         depends_on=[], done_when="arm.xml loads")
    code, _, res = mechy("agent", "run", "T010-cad-v1", "--project", str(project.root))
    assert code == 0 and res["ok"], res
    assert json.loads(project.path("tasks/T010-cad-v1.status.json").read_text())["summary"] == "design/v1/summary.md"


def test_plan_reads_inbox(project):
    inbox = project.path("inbox")
    (inbox / "20261023-120000.md").write_text("---\nfrom: app\ncreated: 2026-10-23T12:00:00Z\n---\nDeeper cup please.\n")
    code, events, res = mechy("plan", "--project", str(project.root), env=FAKE)
    assert code == 0 and res["ok"], res
    assert res["inbox_processed"] == ["20261023-120000.md"]
    assert (inbox / "done" / "20261023-120000.md").exists() and not (inbox / "20261023-120000.md").exists()
    assert len(res["new_cards"]) == 2
    assert any(e["type"] == "question.asked" for e in events)
    assert any(e["type"] == "options.presented" for e in events)
    assert project.path("tasks/summary.md").exists()


def test_provider_resolution_and_commands(project, monkeypatch):
    monkeypatch.delenv("MECHY_FAKE_PROVIDER", raising=False)
    monkeypatch.setenv("MECHY_PROVIDER", "codex")
    assert resolve_provider("claude") == "codex"
    assert resolve_provider("none") == "none"
    monkeypatch.setenv("MECHY_PROVIDER", "auto")
    monkeypatch.setenv("MECHY_CLAUDE_BIN", "/nonexistent/claude")
    monkeypatch.setenv("MECHY_CODEX_BIN", "/nonexistent/codex")
    assert resolve_provider("claude") == "claude"   # nothing installed: keep the card's choice
    c = {"id": "T020-x", "role": "sim", "provider": "claude", "tier": "fast", "goal": "g",
         "tools": ["sim.catch", "motor.check"], "inputs": [], "outputs": [], "depends_on": [], "done_when": "d"}
    assert allowed_mcp_tools(c) == ["mcp__mechy-tools__sim_catch", "mcp__mechy-tools__motor_check"]
    inv = build_invocation(project, c, "PROMPT", "claude")
    a = inv.argv
    assert a[0] == "/nonexistent/claude" and a[1:3] == ["-p", "PROMPT"]
    assert a[a.index("--output-format") + 1] == "stream-json" and "--verbose" in a
    cfg = json.loads(open(a[a.index("--mcp-config") + 1]).read())
    assert cfg["mcpServers"]["mechy-tools"]["args"][-2:] == ["--project", str(project.root)]
    assert "mcp__mechy-tools__sim_catch" in a[a.index("--allowedTools") + 1]
    assert "summary.md" in a[a.index("--append-system-prompt") + 1]
    assert any(d.endswith("knowledge") for d in a[a.index("--add-dir") + 1:a.index("--append-system-prompt")])
    inv = build_invocation(project, c, "PROMPT", "codex")
    assert inv.argv[:3] == ["/nonexistent/codex", "exec", "--json"]
    assert any(x.startswith("mcp_servers.mechy-tools.command=") for x in inv.argv)
    assert inv.argv[-1].endswith("PROMPT")
    assert "sandbox_workspace_write.network_access=true" not in inv.argv
    # Research gets web access and Python; sim gets Python but no web.
    sim_tools = build_invocation(project, c, "P", "claude").argv
    sim_allowed = sim_tools[sim_tools.index("--allowedTools") + 1].split(",")
    assert "Bash(python3:*)" in sim_allowed and "WebSearch" not in sim_allowed
    r = dict(c, id="T021-prior-art", role="research", tools=[])
    ra = build_invocation(project, r, "P", "claude").argv
    r_allowed = ra[ra.index("--allowedTools") + 1].split(",")
    assert {"WebSearch", "WebFetch", "Bash(git clone:*)"} <= set(r_allowed)
    assert "sandbox_workspace_write.network_access=true" in build_invocation(project, r, "P", "codex").argv


def test_codex_stream_parsing():
    """Real `codex exec --json` output (codex-cli 0.163.0)."""
    from mechy.agents.providers import parse_stream_line
    lines = [
        '{"type":"thread.started","thread_id":"01a16eeb-ac3e-7ce2-9be0-ed9df5879e24"}',
        '{"type":"turn.started"}',
        '{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"ok"}}',
        '{"type":"turn.completed","usage":{"input_tokens":15118,"cached_input_tokens":0,'
        '"cache_write_input_tokens":15115,"output_tokens":5,"reasoning_output_tokens":0}}',
    ]
    outs = [parse_stream_line("codex", l) for l in lines]
    assert outs[2] == {"text": "ok"}
    assert outs[3]["final"] is True and outs[3]["usage"]["output_tokens"] == 5
    assert not outs[0] and not outs[1]


def test_accounts_status(tmp_path, monkeypatch):
    from mechy.accounts import status
    monkeypatch.setenv("MECHY_CLAUDE_BIN", "/nonexistent/claude")
    s = status("claude")
    assert s["installed"] is False and s["logged_in"] is None
    fake = tmp_path / "codex"
    fake.write_text('#!/bin/sh\nif [ "$1" = "--version" ]; then echo "codex-cli 0.0.0"; '
                    'elif [ "$1" = "login" ]; then echo "Logged in using an API key - sk-proj-***XXX"; '
                    'else exit 1; fi\n')
    fake.chmod(0o755)
    monkeypatch.setenv("MECHY_CODEX_BIN", str(fake))
    s = status("codex")
    assert s["logged_in"] is True and s["method"] == "api_key"
    assert "sk-proj" not in (s["detail"] or "") and "XXX" not in (s["detail"] or "")
    fake.write_text('#!/bin/sh\necho "Not logged in"; exit 1\n')
    s = status("codex")
    assert s["logged_in"] is False and s["method"] is None


def test_card_ids_allow_letter_suffix():
    from mechy.agents.cards import CardError, validate

    base = {"role": "cad", "provider": "claude", "goal": "g", "outputs": ["x"], "done_when": "d"}
    validate({**base, "id": "T004a-cad-opt-a"})
    try:
        validate({**base, "id": "T4-bad"})
    except CardError:
        pass
    else:
        raise AssertionError("short id accepted")


def test_concept_role_can_always_present_options():
    from mechy.agents.providers import allowed_mcp_tools

    assert "mcp__mechy-tools__options_present" in allowed_mcp_tools({"role": "concept", "tools": ["ik.solve"]})
    assert "mcp__mechy-tools__options_present" not in allowed_mcp_tools({"role": "cad", "tools": []})


def _photo(path):
    from PIL import Image
    Image.new("RGB", (400, 300), (200, 120, 40)).save(path, "JPEG")


def test_intake_cli_and_run_digests_first(project):
    """`mechy intake pending|all`, and `mechy run` digests pending inspiration before running cards."""
    _photo(project.path("inspiration", "arm_photo.jpg"))
    code, _, res = mechy("intake", "pending", "--project", str(project.root))
    assert code == 0 and res["ok"] and res["pending"] == ["inspiration/arm_photo.jpg"], res
    code, events, res = mechy("run", "--project", str(project.root), env=FAKE)
    assert code == 0 and res["ok"], res
    assert res["intake"]["digested"] and not res["intake"]["errors"]
    assert any(e["type"] == "task.done" and e["task"] == "intake" for e in events)
    assert project.path(res["intake"]["digested"][0]).exists()
    code, _, res = mechy("intake", "pending", "--project", str(project.root))
    assert res["count"] == 0
    # nothing pending: run does not mention intake; --no-intake skips it
    _photo(project.path("inspiration", "second.jpg"))
    code, _, res = mechy("run", "--no-intake", "--project", str(project.root), env=FAKE)
    assert code == 0 and "intake" not in res
    code, _, res = mechy("intake", "all", "--project", str(project.root))
    assert code == 0 and res["ok"] and len(res["digested"]) == 1


def test_plan_digests_pending_and_lists_intake_tools(project):
    from mechy.agents import runner
    _photo(project.path("inspiration", "ref.jpg"))
    code, _, res = mechy("plan", "--project", str(project.root), env=FAKE)
    assert code == 0 and res["ok"], res
    assert res["intake"]["digested"] and res["intake"]["digested"][0].startswith("inspiration/notes/")
    seen = {}
    real = runner._run_llm

    def spy(project_, card_, prov, prompt, ev):
        seen["tools"] = card_["tools"]
        return real(project_, card_, prov, prompt, ev)
    runner._run_llm = spy
    try:
        import os
        os.environ.update(FAKE)
        runner.run_planner(project, intake=False)
    finally:
        runner._run_llm = real
        for k in FAKE:
            os.environ.pop(k, None)
    assert {"intake.digest", "intake.pending"} <= set(seen["tools"])


def test_run_none_intake_and_control_cards(project):
    _photo(project.path("inspiration", "pic.jpg"))
    card(project.path("tasks/T020-research-intake.yaml"), id="T020-research-intake", role="research", provider="none",
         goal="Digest inspiration.", inputs=["inspiration/links.yaml"], tools=["intake.digest"],
         outputs=["inspiration/notes/pic.md"], depends_on=[], done_when="notes exist")
    code, _, res = mechy("agent", "run", "T020-research-intake", "--project", str(project.root))
    assert code == 0 and res["ok"], res
    card(project.path("tasks/T021-controls-v1.yaml"), id="T021-controls-v1", role="controls", provider="none",
         goal="Generate firmware.", inputs=["design/v1/params.yaml"], tools=["control.gen"],
         outputs=["control/v1/firmware/mechy_arm/config.h"], depends_on=[], done_when="config.h exists")
    code, _, res = mechy("agent", "run", "T021-controls-v1", "--project", str(project.root))
    assert code == 0 and res["ok"], res
    assert res["summary"] == "control/v1/summary.md"


def test_run_none_doc_build_dispatch(project, monkeypatch):
    """A `provider: none` docs card calls doc.build for the variant its paths name (tool stubbed: the
    real build is covered in test_docgen)."""
    from mechy import tools as T
    from mechy.agents.runner import run_task
    calls = []

    def fake(proj, v, only=None, print_paper=False):
        calls.append((v, only, print_paper))
        out = proj.path("docs", v)
        out.mkdir(parents=True, exist_ok=True)
        (out / "build_guide.pdf").write_bytes(b"%PDF-1.7")
        return {"ok": True}
    monkeypatch.setattr(T, "doc_build", fake)
    card(project.path("tasks/T030-docs-v2.yaml"), id="T030-docs-v2", role="docs", provider="none",
         goal="Build the guide.", inputs=["design/v2/params.yaml"], tools=["doc.build"], only="build_guide",
         print_paper=True, outputs=["docs/v2/build_guide.pdf"], depends_on=[], done_when="pdf exists")
    res = run_task(project, "T030-docs-v2", commit=False)
    assert res["ok"], res
    assert calls == [("v2", "build_guide", True)]
