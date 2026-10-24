"""Task cards (contracts section 2) and their status files."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..events import now_iso
from ..project import Project, load_yaml, write_json

ROLES = ("planner", "research", "concept", "cad", "sim", "controls", "docs")
PROVIDERS = ("claude", "codex", "none")
STATES = ("queued", "running", "done", "failed", "blocked")
ID_RE = re.compile(r"^T\d{3,}[a-z]?-[a-z0-9][a-z0-9-]*$")
REQUIRED = ("id", "role", "provider", "goal", "outputs", "done_when")


class CardError(ValueError):
    pass


def card_path(project: Project, task_id: str) -> Path:
    return project.path("tasks", f"{task_id}.yaml")


def status_path(project: Project, task_id: str) -> Path:
    return project.path("tasks", f"{task_id}.status.json")


def validate(card: dict, name: str = "") -> dict:
    if not isinstance(card, dict):
        raise CardError(f"{name}: card is not a mapping")
    missing = [k for k in REQUIRED if not card.get(k)]
    if missing:
        raise CardError(f"{name}: missing {', '.join(missing)}")
    if not ID_RE.match(str(card["id"])):
        raise CardError(f"{name}: id {card['id']!r} must look like T014-shoulder-torque")
    if card["role"] not in ROLES:
        raise CardError(f"{name}: role must be one of {ROLES}")
    if card["provider"] not in PROVIDERS:
        raise CardError(f"{name}: provider must be one of {PROVIDERS}")
    card.setdefault("tier", "strong")
    for k in ("inputs", "tools", "outputs", "depends_on"):
        v = card.get(k) or []
        if isinstance(v, str):
            v = [v]
        card[k] = list(v)
    return card


def load_card(project: Project, task_id: str) -> dict:
    p = card_path(project, task_id)
    if not p.exists():
        raise CardError(f"no task card tasks/{task_id}.yaml")
    return validate(load_yaml(p), p.name)


def load_cards(project: Project) -> tuple[dict[str, dict], dict[str, str]]:
    """All valid cards by id, and errors by file name for invalid ones."""
    cards, errors = {}, {}
    for p in sorted(project.path("tasks").glob("*.yaml")):
        try:
            c = validate(load_yaml(p), p.name)
            cards[c["id"]] = c
        except Exception as e:  # noqa: BLE001
            errors[p.name] = str(e)
    return cards, errors


def read_status(project: Project, task_id: str) -> dict:
    p = status_path(project, task_id)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except json.JSONDecodeError:
            pass
    return {"state": "queued", "started": None, "finished": None, "summary": None, "error": None}


def write_status(project: Project, task_id: str, state: str, **fields) -> dict:
    assert state in STATES
    st = read_status(project, task_id)
    st["state"] = state
    if state == "running":
        st["started"] = now_iso()
        st["finished"] = None
        st["error"] = None
    if state in ("done", "failed", "blocked"):
        st["finished"] = now_iso()
    st.update(fields)
    for k in ("started", "finished", "summary", "error"):
        st.setdefault(k, None)
    write_json(status_path(project, task_id), st)
    return st


def summary_path_for(card: dict) -> str:
    """summary.md next to the first output (contracts 2)."""
    outs = card.get("outputs") or []
    if not outs:
        return f"tasks/{card['id']}.summary.md"
    first = Path(outs[0])
    d = first if not first.suffix else first.parent
    return str(d / "summary.md")
