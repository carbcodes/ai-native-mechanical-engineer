import asyncio
import json

import yaml

from mechy.mcp_server import create_server
from mechy.tools import TOOL_NAMES, mcp_name


def call(server, name, args):
    res = asyncio.run(server.call_tool(name, args))
    content = res[0] if isinstance(res, tuple) else res
    return json.loads(content[0].text)


def test_tools_listed(project):
    s = create_server(project.root)
    names = {t.name for t in asyncio.run(s.list_tools())}
    assert names == {mcp_name(t) for t in TOOL_NAMES}


def test_light_tools(project):
    s = create_server(project.root)
    summ = call(s, "project_summary", {})
    assert summ["variants"][0]["name"] == "v1"
    ik = call(s, "ik_solve", {"variant": "v1", "target_xyz": [0.3, 0.05, 0.3]})
    assert ik["reachable"] and len(ik["q_deg"]) == 4
    far = call(s, "ik_solve", {"variant": "v1", "target_xyz": [2.0, 0, 0.3]})
    assert far["reachable"] is False
    mc = call(s, "motor_check", {"variant": "v1", "trajectory": [{"q_deg": [30, 60, -60, 20], "t": 0.6}]})
    assert "segments" in mc and mc["max_motor_rps"][0] == 5.0      # 4 microsteps, 4000 steps/s cap
    bp = call(s, "ball_predict", {"points": [[0, 1.8, 0, 1], [0.05, 1.7, 0, 1.12], [0.1, 1.6, 0, 1.22]]})
    assert bp["landing"] is not None
    ps = call(s, "cad_params_set", {"variant": "v9", "patch": {"catcher": {"depth_m": 0.1},
                                                                "joints": {"1": {"gear_ratio": 5}}}})
    assert ps["created"] and ps["copied_from"]
    p = call(s, "cad_params_get", {"variant": "v9"})["params"]
    assert p["catcher"]["depth_m"] == 0.1 and p["joints"][1]["gear_ratio"] == 5 and p["name"] == "v9"
    q = call(s, "question_ask", {"id": "Q001-throw", "text": "How?", "kind": "choice", "choices": ["a", "b"]})
    qd = yaml.safe_load(project.path(q["path"]).read_text())
    assert qd["answer"] is None and qd["choices"] == ["a", "b"]
    o = call(s, "options_present", {"id": "O001-cup", "prompt": "Pick",
                                    "options": [{"id": "v1", "title": "a"}, {"id": "v2", "title": "b"}]})
    od = yaml.safe_load(project.path(o["path"]).read_text())
    assert od["chosen"] is None and od["feedback"] is None and len(od["options"]) == 2
    ev = project.path(".mechy/events.jsonl").read_text()
    assert '"question.asked"' in ev and '"options.presented"' in ev


def test_render_views(project):
    s = create_server(project.root)
    r = call(s, "render_views", {"variant": "v1"})
    assert len(r["files"]) == 4 and all(project.path(f).exists() for f in r["files"])


def test_cad_build_tool(project):
    s = create_server(project.root)
    r = call(s, "cad_build", {"variant": "v1"})
    assert r["ok"] and project.path("design/v1/arm.xml").exists()
