"""Fake LLM provider for tests and demos (MECHY_FAKE_PROVIDER=1).

Speaks the same stream-json shape as `claude -p --output-format stream-json`, writes
plausible placeholder outputs and summary.md. A planner card writes two task cards, one
question and one option set. A card whose goal contains "FAIL" exits with an error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import yaml


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def say(text: str) -> None:
    emit({"type": "assistant", "message": {"model": "fake", "content": [{"type": "text", "text": text}]}})


def placeholder(path: Path, card: dict) -> None:
    if not path.suffix:
        path.mkdir(parents=True, exist_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    if path.suffix == ".json":
        path.write_text(json.dumps({"fake": True, "task": card["id"]}, indent=2) + "\n")
    elif path.suffix in (".yaml", ".yml"):
        path.write_text(yaml.safe_dump({"fake": True, "task": card["id"]}))
    else:
        path.write_text(f"# {card['id']} (fake output)\n\n{card['goal']}\n")


def plan(root: Path, card: dict) -> list[str]:
    tasks = root / "tasks"
    existing = sorted(int(p.name[1:4]) for p in tasks.glob("T[0-9][0-9][0-9]-*.yaml"))
    n = (existing[-1] if existing else 0) + 1
    a, b = f"T{n:03d}-research-grippers", f"T{n + 1:03d}-sim-notes"
    cards = [
        {"id": a, "role": "research", "provider": "claude", "tier": "fast",
         "goal": "Survey cup and net catchers for tennis balls.", "inputs": ["brief.md"],
         "tools": ["project.summary"], "outputs": [f"research/{a}/notes.md"], "depends_on": [],
         "done_when": "notes.md lists at least three catcher designs with sizes."},
        {"id": b, "role": "sim", "provider": "claude", "tier": "fast",
         "goal": "Write notes on the catch simulation setup.", "inputs": ["requirements.yaml"],
         "tools": ["sim.catch"], "outputs": [f"sim/{b}/notes.md"], "depends_on": [a],
         "done_when": "notes.md exists."},
    ]
    written = []
    for c in cards:
        p = tasks / f"{c['id']}.yaml"
        p.write_text(yaml.safe_dump(c, sort_keys=False))
        written.append(str(p.relative_to(root)))
    q = root / "questions" / "Q001-throw-style.yaml"
    q.parent.mkdir(exist_ok=True)
    q.write_text(yaml.safe_dump({"id": "Q001-throw-style", "asked_by": card["id"],
                                 "text": "How will the ball usually be thrown?", "kind": "choice",
                                 "choices": ["Underhand from waist", "Overhand from shoulder", "Not sure"],
                                 "answer": None}, sort_keys=False))
    o = root / "options" / "O001-catcher.yaml"
    o.parent.mkdir(exist_ok=True)
    o.write_text(yaml.safe_dump({"id": "O001-catcher", "prompt": "Pick a catcher",
                                 "options": [{"id": "cup", "title": "Foam-lined cup"},
                                             {"id": "net", "title": "Small net"}],
                                 "chosen": None, "feedback": None}, sort_keys=False))
    return written + [str(q.relative_to(root)), str(o.relative_to(root))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--card", required=True)
    a = ap.parse_args()
    root = Path(a.project)
    card = json.loads(a.card)
    t0 = time.time()
    emit({"type": "system", "subtype": "init", "model": "fake", "tools": card.get("tools", [])})
    say(f"Reading {', '.join(card.get('inputs') or []) or 'the card'}.")
    time.sleep(float(os.environ.get("MECHY_FAKE_DELAY", "0.2")))
    if "FAIL" in card.get("goal", ""):
        emit({"type": "result", "subtype": "error_during_execution", "is_error": True,
              "result": "fake failure requested", "usage": {"input_tokens": 10, "output_tokens": 0}})
        return 1
    written = plan(root, card) if card["role"] == "planner" else []
    for o in card.get("outputs") or []:
        placeholder(root / o, card)
        written.append(o)
    summ = root / card["_summary"]
    summ.parent.mkdir(parents=True, exist_ok=True)
    summ.write_text(f"# {card['id']}\n\nFake run of a {card['role']} task: {card['goal']}\n\n"
                    f"Wrote: {', '.join(written) or 'nothing'}.\n\nOpen issues: none (fake provider).\n")
    say(f"Done. Wrote {len(written)} files and {card['_summary']}.")
    emit({"type": "result", "subtype": "success", "is_error": False, "result": "ok",
          "duration_ms": int((time.time() - t0) * 1000), "total_cost_usd": 0.0,
          "usage": {"input_tokens": 1200, "output_tokens": 300}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
