import json

import yaml

from mechy.project import PROJECT_DIRS, Project
from conftest import mechy


def test_init_example_layout(tmp_path):
    root = tmp_path / "p"
    code, events, res = mechy("init", str(root), "--example", "tennis-catcher")
    assert code == 0 and res["ok"] is True
    for d in PROJECT_DIRS:
        assert (root / d).is_dir(), d
    for f in ["brief.md", "requirements.yaml", "decisions.md", "hw/motors.yaml", "hw/drivers.yaml",
              "design/v1/params.yaml", "inspiration/links.yaml", ".mechy/project.json", ".mechy/events.jsonl"]:
        assert (root / f).is_file(), f
    meta = json.loads((root / ".mechy/project.json").read_text())
    assert set(meta) == {"name", "created", "schema"} and meta["schema"] == 1
    params = yaml.safe_load((root / "design/v1/params.yaml").read_text())
    assert [j["name"] for j in params["joints"]] == ["base", "shoulder", "elbow", "wrist"]
    req = yaml.safe_load((root / "requirements.yaml").read_text())
    assert req["catch"]["throw_distance_m"] == 1.8 and req["vision"]["fps"] == 60
    assert yaml.safe_load((root / "inspiration/links.yaml").read_text()) == {"links": []}
    assert ".mechy/viewer/" in (root / ".gitignore").read_text()
    assert (root / ".git").is_dir()
    logged = [json.loads(l) for l in (root / ".mechy/events.jsonl").read_text().splitlines()]
    assert any(e["type"] == "file.written" and e["path"] == "brief.md" for e in logged)
    assert all("ts" in e for e in events)
    drv = Project(root).hardware()["drivers"][0]
    assert drv["max_step_rate_hz"] == 4000


def test_init_twice_fails(tmp_path):
    root = tmp_path / "p"
    assert mechy("init", str(root))[0] == 0
    code, _, res = mechy("init", str(root))
    assert code == 1 and res["ok"] is False and "already" in res["error"]


def test_flags_after_args_and_failure_result(project):
    # contracts 8.3: --project/--json after the subcommand's own arguments; 8.6: ok false
    code, _, res = mechy("cad", "build", "v9", "--project", str(project.root))
    assert code == 1 and res["ok"] is False and "v9" in res["error"]


def test_not_a_project(tmp_path):
    code, _, res = mechy("sim", "catch", "v1", "--project", str(tmp_path))
    assert code == 1 and res["ok"] is False
