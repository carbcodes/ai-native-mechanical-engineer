"""Project folder model (contracts section 1)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import yaml

from .events import Events, now_iso

SCHEMA = 1
EXAMPLES_DIR = Path(__file__).parent / "examples"
EXAMPLES = {"tennis-catcher": "tennis_catcher", "drone": "drone", "bam-arm": "bam_arm"}

# Folders every project has (contracts section 1).
PROJECT_DIRS = [
    "inspiration", "inspiration/notes", "research", "hw", "design", "sim",
    "control", "docs", "tasks", "questions", "options", "inbox", ".mechy",
]

PROJECT_GITIGNORE = """\
.DS_Store
__pycache__/
*.pyc
.mechy/mcp-*.json
.mechy/runs/
.mechy/viewer/
.mechy/history-cache/
"""


class ProjectError(Exception):
    pass


# --------------------------------------------------------------------- yaml
def load_yaml(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_yaml(path: str | Path, data: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    return p


def write_json(path: str | Path, data: Any) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, p)
    return p


# ------------------------------------------------------------------ project
class Project:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    # paths
    def path(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    def variant_dir(self, variant: str) -> Path:
        return self.path("design", variant)

    def exists(self) -> bool:
        return self.path(".mechy", "project.json").is_file()

    def require(self) -> "Project":
        if not self.exists():
            raise ProjectError(f"{self.root} is not a Mechy project (no .mechy/project.json); "
                               "run `mechy init` first")
        return self

    # data
    def meta(self) -> dict:
        return json.loads(self.path(".mechy", "project.json").read_text())

    def requirements(self) -> dict:
        p = self.path("requirements.yaml")
        return (load_yaml(p) or {}) if p.exists() else {}

    def params(self, variant: str) -> dict:
        p = self.variant_dir(variant) / "params.yaml"
        if not p.exists():
            raise ProjectError(f"no params.yaml for variant {variant!r} ({p})")
        return load_yaml(p)

    def hardware(self) -> dict:
        """motors from hw/motors.yaml; drivers/controller from hw/drivers.yaml,
        falling back to the copies in motors.yaml (contracts 1.2 shows both there)."""
        def ld(name: str) -> dict:
            p = self.path("hw", name)
            return (load_yaml(p) or {}) if p.exists() else {}
        m, d = ld("motors.yaml"), ld("drivers.yaml")
        return {
            "motors": m.get("motors") or [],
            "drivers": d.get("drivers") or m.get("drivers") or [],
            "controller": d.get("controller") or m.get("controller"),
        }

    def drivers_doc(self) -> dict:
        """hw/drivers.yaml as written (power_supply, bulk_capacitor, shield, ... for the BOM)."""
        p = self.path("hw", "drivers.yaml")
        return (load_yaml(p) or {}) if p.exists() else {}

    def motor(self, motor_id: str) -> dict:
        for m in self.hardware()["motors"]:
            if m.get("id") == motor_id:
                return m
        raise ProjectError(f"motor {motor_id!r} not in hw/motors.yaml")

    def variants(self) -> list[str]:
        d = self.path("design")
        if not d.is_dir():
            return []
        vs = [p.name for p in d.iterdir() if p.is_dir() and (p / "params.yaml").exists()]
        return sorted(vs, key=lambda s: (len(s), s))

    def chosen(self) -> str | None:
        p = self.path("design", "chosen")
        return (p.read_text().strip() or None) if p.exists() else None

    def append_usage(self, row: dict) -> None:
        with open(self.path(".mechy", "usage.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps(row, default=str) + "\n")


def check_variant_style(project: "Project", variant: str, what: str) -> None:
    """Sim/control/docs only exist for the arm styles; give a clean error for others."""
    p = project.path("design", variant, "params.yaml")
    style = (load_yaml(p) or {}).get("style") if p.exists() else None
    if style == "quad_frame":
        raise ProjectError(f"{what} is not available for style quad_frame yet")


def find_project(start: str | Path | None) -> Project:
    """The project at `start` (default cwd) or the nearest parent holding .mechy/project.json."""
    p = Path(start or os.getcwd()).resolve()
    for cand in [p, *p.parents]:
        if (cand / ".mechy" / "project.json").is_file():
            return Project(cand)
    return Project(p)


# --------------------------------------------------------------------- init
def init_project(root: str | Path, example: str | None = None, name: str | None = None,
                 goal: str | None = None, events: Events | None = None, git: bool = True) -> Project:
    root = Path(root).resolve()
    if root.exists() and (root / ".mechy" / "project.json").exists():
        raise ProjectError(f"{root} is already a Mechy project")
    root.mkdir(parents=True, exist_ok=True)
    proj = Project(root)
    ev = events or Events(root, quiet=True)
    for d in PROJECT_DIRS:
        proj.path(d).mkdir(parents=True, exist_ok=True)
    write_json(proj.path(".mechy", "project.json"),
               {"name": name or root.name, "created": now_iso(), "schema": SCHEMA})
    ev.project = root  # log exists from here on
    ev.file_written(proj.path(".mechy", "project.json"))
    proj.path(".mechy", "events.jsonl").touch()
    proj.path(".mechy", "usage.jsonl").touch()

    written: list[Path] = []
    if example:
        if example not in EXAMPLES:
            raise ProjectError(f"unknown example {example!r}; known: {', '.join(EXAMPLES)}")
        src = EXAMPLES_DIR / EXAMPLES[example]
        for f in sorted(src.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts:
                dst = root / f.relative_to(src)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                written.append(dst)
        if goal:
            brief = root / "brief.md"
            brief.write_text(brief.read_text() + f"\n## User notes\n\n{goal}\n")
    else:
        defaults = {
            "brief.md": f"# {name or root.name}\n\n## Goal\n\n{goal or '(Write the goal with the user.)'}\n",
            "requirements.yaml": "{}\n",
            "decisions.md": "# Decisions\n\n",
            "hw/motors.yaml": "motors: []\n",
            "hw/drivers.yaml": "drivers: []\ncontroller: null\n",
            "inspiration/links.yaml": "links: []\n",
        }
        for rel, text in defaults.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_text(text)
                written.append(p)
    gi = root / ".gitignore"
    if not gi.exists():
        gi.write_text(PROJECT_GITIGNORE)
        written.append(gi)
    # keep empty folders in git
    for d in PROJECT_DIRS:
        dp = proj.path(d)
        if d != ".mechy" and not any(dp.iterdir()):
            (dp / ".gitkeep").touch()
    for p in written:
        ev.file_written(p)
    if git:
        git_init(root)
    return proj


def git_init(root: Path) -> bool:
    if shutil.which("git") is None:
        return False
    if not (root / ".git").exists():
        r = subprocess.run(["git", "init", "-q"], cwd=root, capture_output=True)
        if r.returncode != 0:
            return False
    return git_commit(root, "mechy init")


def git_commit(root: Path, message: str) -> bool:
    """Commit everything in the project; supplies a fallback identity if none is set."""
    if shutil.which("git") is None or not (root / ".git").exists():
        return False
    subprocess.run(["git", "add", "-A"], cwd=root, capture_output=True)
    ident: list[str] = []
    r = subprocess.run(["git", "config", "user.email"], cwd=root, capture_output=True, text=True)
    if not r.stdout.strip():
        ident = ["-c", "user.name=Mechy", "-c", "user.email=mechy@localhost"]
    r = subprocess.run(["git", *ident, "commit", "-q", "-m", message, "--allow-empty"],
                       cwd=root, capture_output=True)
    return r.returncode == 0
