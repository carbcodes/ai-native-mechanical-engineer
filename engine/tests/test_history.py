"""`mechy history` on a temp project with real git commits."""

import json

import pytest

from conftest import mechy
from mechy.project import init_project, write_json

pytestmark = pytest.mark.skipif(__import__("shutil").which("git") is None, reason="git not installed")


@pytest.fixture
def hist_project(tmp_path):
    proj = init_project(tmp_path / "proj", git=True)
    d = proj.path("design", "v1")
    d.mkdir(parents=True, exist_ok=True)
    (d / "params.yaml").write_text("name: v1\nx: 1\n")
    (proj.root / "brief.md").write_text("# P\n")
    code, _, res = mechy("history", "snapshot", "-m", "T012-arms: add v1", "--project", str(proj.root))
    assert res["ok"] and res["committed"], res
    (d / "params.yaml").write_text("name: v1\nx: 2\n")
    (d / "later.txt").write_text("added after the snapshot target\n")
    mechy("history", "snapshot", "-m", "bump x and add later.txt", "--project", str(proj.root))
    return proj


def test_list(hist_project):
    code, _, res = mechy("history", "list", "--project", str(hist_project.root))
    assert code == 0 and res["ok"], res
    commits = res["commits"]
    assert commits[0]["message"].startswith("bump x")
    tagged = next(c for c in commits if c["task"])
    assert tagged["task"] == "T012-arms" and tagged["author"]
    assert any(f["path"] == "design/v1/params.yaml" for f in tagged["files"])
    assert "design/v1" in tagged["areas"]
    assert all(not f["path"].startswith(".mechy") for c in commits for f in c["files"])
    code, _, res = mechy("history", "list", "--path", "design/v1", "--project", str(hist_project.root))
    assert all(any(f["path"].startswith("design/v1") for f in c["files"]) for c in res["commits"])


def test_show_and_diff(hist_project):
    code, _, res = mechy("history", "list", "--project", str(hist_project.root))
    sha = next(c["sha"] for c in res["commits"] if c["task"] == "T012-arms")
    out = hist_project.root / ".mechy" / "old-params.yaml"
    code, _, res = mechy("history", "show", sha, "design/v1/params.yaml", "--out", str(out),
                         "--project", str(hist_project.root))
    assert res["ok"] and out.read_text().endswith("x: 1\n")
    code, _, res = mechy("history", "diff", sha, "--project", str(hist_project.root))
    assert res["ok"] and "params.yaml" in res["patch"] and not res["truncated"]
    assert any(s["path"] == "design/v1/params.yaml" for s in res["stats"])


def test_restore_variant_and_dirty_snapshot(hist_project):
    code, _, res = mechy("history", "list", "--project", str(hist_project.root))
    sha = next(c["sha"] for c in res["commits"] if c["task"] == "T012-arms")
    # an unrelated dirty file gets snapshotted first
    (hist_project.root / "research").mkdir(exist_ok=True)
    (hist_project.root / "research" / "note.md").write_text("wip\n")
    code, events, res = mechy("history", "restore", sha, "--path", "design/v1",
                              "--project", str(hist_project.root))
    assert res["ok"], res
    assert "design/v1/later.txt" in res["removed"]
    assert not hist_project.path("design", "v1", "later.txt").exists()
    assert hist_project.path("design", "v1", "params.yaml").read_text().endswith("x: 1\n")
    assert hist_project.path("research", "note.md").read_text() == "wip\n"   # untouched
    assert hist_project.path(".mechy", "events.jsonl").exists()
    # a snapshot commit of the dirty state happened before the restore commit
    msgs = [c["message"] for c in mechy("history", "list", "--project",
                                        str(hist_project.root))[2]["commits"]]
    assert msgs[0].startswith(f"restore design/v1 to {sha[:7]}")
    assert msgs[1].startswith("before restore to")
    assert any(e["type"] == "file.written" and e["path"] == "design/v1/params.yaml" for e in events)


def test_restore_refuses_running_task(hist_project):
    write_json(hist_project.path("tasks", "T001-x.status.json"), {"state": "running", "started": "t",
                                                                 "finished": None, "summary": None,
                                                                 "error": None})
    mechy("history", "snapshot", "-m", "running status", "--project", str(hist_project.root))
    code, _, res = mechy("history", "restore", "HEAD~1", "--project", str(hist_project.root))
    assert code == 1 and res["ok"] is False and "running" in res["error"]


def test_snapshot_clean(hist_project):
    code, _, res = mechy("history", "snapshot", "-m", "nothing", "--project", str(hist_project.root))
    assert res["ok"] and res["committed"] is False and res["sha"]
