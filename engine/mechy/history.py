"""`mechy history`: project version history on top of git (contracts: history is append-only;
restore is always a new commit so it can itself be undone)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from .events import Events
from .project import Project, ProjectError, git_commit

EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69217fbee4904"
MAX_PATCH = 200_000
TASK_RE = re.compile(r"\b(T\d{3,}[a-z]?-[a-z0-9][a-z0-9-]*)\b")
_AREA_TWO = {"design", "sim", "control", "docs"}
_FMT = "%H%x1f%h%x1f%aI%x1f%an%x1f%s"


def _git(project: Project, *args: str, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=project.root, capture_output=True, text=text)


def _git_ok(project: Project, *args: str) -> str:
    r = _git(project, *args)
    if r.returncode != 0:
        raise ProjectError(f"git {' '.join(args[:2])}: {r.stderr.strip() or r.stdout.strip()}")
    return r.stdout


def _require_git(project: Project) -> None:
    if not (project.root / ".git").is_dir():
        raise ProjectError(f"{project.root} is not a git repo (was it created with --no-git?)")


def _area(path: str) -> str:
    parts = path.split("/")
    if parts[0] in _AREA_TWO and len(parts) > 1:
        return "/".join(parts[:2])
    return parts[0]


def _changed_files(project: Project, sha: str) -> list[dict]:
    out = _git_ok(project, "diff-tree", "--no-commit-id", "--name-status", "-r", "-M", "--root", sha)
    files = []
    for line in out.splitlines():
        cols = line.split("\t")
        st = cols[0]
        path = cols[-1]
        if path.startswith(".mechy/") or path == ".mechy":
            continue
        files.append({"path": path, "status": st[0]})
    return files


def _dirty(project: Project) -> list[str]:
    """Uncommitted paths; .mechy/ (events.jsonl etc.) changes on every command, so it does
    not count as unsaved work."""
    out = _git_ok(project, "status", "--porcelain")
    return [l[3:].split(" -> ")[-1] for l in out.splitlines()
            if l.strip() and not l[3:].split(" -> ")[-1].startswith(".mechy")]


def list_commits(project: Project, path: str | None = None, limit: int = 100) -> dict:
    _require_git(project)
    argv = ["log", f"--format={_FMT}", "-n", str(limit)]
    if path:
        argv += ["--", path]
    out = _git(project, *argv).stdout
    commits = []
    for line in out.splitlines():
        if "\x1f" not in line:
            continue
        sha, short, t, author, msg = line.split("\x1f", 4)
        m = TASK_RE.search(msg)
        files = _changed_files(project, sha)
        commits.append({"sha": sha, "short": short, "time": t, "message": msg, "author": author,
                        "task": m.group(1) if m else None,
                        "files": files,
                        "areas": sorted({_area(f["path"]) for f in files})})
    return {"ok": True, "commits": commits, "dirty": _dirty(project)}


def show_file(project: Project, sha: str, path: str, out: str) -> dict:
    _require_git(project)
    if path.startswith(".mechy"):
        raise ProjectError(".mechy paths are not in the project history")
    r = _git(project, "show", f"{sha}:{path}", text=False)
    if r.returncode != 0:
        raise ProjectError(f"no {path!r} at {sha}: {r.stderr.decode(errors='replace').strip()}")
    dest = Path(out).expanduser()
    if not dest.is_absolute():
        dest = Path.cwd() / dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(r.stdout)
    return {"ok": True, "out": str(dest)}


def _parent(project: Project, sha: str) -> str:
    r = _git(project, "rev-parse", "--verify", "--quiet", f"{sha}^")
    return r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else EMPTY_TREE


def diff_commit(project: Project, sha: str, path: str | None = None) -> dict:
    _require_git(project)
    base = _parent(project, sha)
    spec = ["--", path] if path else []
    patch = _git_ok(project, "diff", base, sha, *spec)
    truncated = len(patch) > MAX_PATCH
    if truncated:
        patch = patch[:MAX_PATCH]
    stats = []
    for line in _git_ok(project, "diff", "--numstat", base, sha, *spec).splitlines():
        a, r, p = (line.split("\t") + ["", "", ""])[:3]
        if p.startswith(".mechy"):
            continue
        stats.append({"path": p, "added": int(a) if a.isdigit() else None,
                      "removed": int(r) if r.isdigit() else None})
    return {"ok": True, "patch": patch, "truncated": truncated, "stats": stats}


def snapshot(project: Project, message: str) -> dict:
    _require_git(project)
    dirty = _dirty(project)
    if dirty:
        if not git_commit(project.root, message):
            raise ProjectError("git commit failed")
    sha = _git_ok(project, "rev-parse", "HEAD").strip()
    return {"ok": True, "sha": sha, "committed": bool(dirty)}


def _running_tasks(project: Project) -> list[str]:
    running = []
    for p in project.path("tasks").glob("*.status.json"):
        try:
            if json.loads(p.read_text()).get("state") == "running":
                running.append(p.name)
        except (json.JSONDecodeError, OSError):
            continue
    return running


def restore(project: Project, sha: str, path: str | None, events: Events | None = None) -> dict:
    _require_git(project)
    if path and path.split("/")[0] == ".mechy":
        raise ProjectError(".mechy paths are not part of the project history")
    running = _running_tasks(project)
    if running:
        raise ProjectError(f"cannot restore while tasks are running: {', '.join(sorted(running))}")
    subject = _git_ok(project, "log", "-1", "--format=%s", sha).strip()
    short = _git_ok(project, "rev-parse", "--short", sha).strip()
    what = path or "project"
    if _dirty(project):
        if not git_commit(project.root, f"before restore to {short}"):
            raise ProjectError("could not snapshot the current state before restore")
    spec = path if path else "."
    added = [l for l in _git_ok(project, "diff", "--name-only", "--diff-filter=A", sha, "HEAD",
                                "--", spec).splitlines() if l.strip() and not l.startswith(".mechy")]
    pathspec = [spec] if path else [".", ":(exclude).mechy"]
    r = _git(project, "checkout", sha, "--", *pathspec)
    if r.returncode != 0:
        raise ProjectError(f"git checkout {short}: {r.stderr.strip()}")
    removed = []
    for rel in added:
        p = project.root / rel
        if p.is_file():
            p.unlink()
            removed.append(rel)
    changed = _dirty(project)
    if not git_commit(project.root, f"restore {what} to {short}: {subject}"):
        raise ProjectError("git commit of the restore failed")
    new_sha = _git_ok(project, "rev-parse", "HEAD").strip()
    if events:
        for rel in changed:
            events.file_written(project.root / rel)
    return {"ok": True, "sha": new_sha, "restored_from": sha, "path": path, "removed": removed}


def run(project: Project, args: argparse.Namespace, events: Events) -> dict[str, Any]:
    cmd = args.history_cmd
    if cmd == "list":
        return list_commits(project, path=args.path, limit=args.limit)
    if cmd == "show":
        return show_file(project, args.sha, args.path, args.out)
    if cmd == "diff":
        return diff_commit(project, args.sha, args.path)
    if cmd == "snapshot":
        return snapshot(project, args.message)
    if cmd == "restore":
        return restore(project, args.sha, args.path, events)
    raise SystemExit(f"unknown history command {cmd}")  # pragma: no cover
