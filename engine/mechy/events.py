"""Event log (contracts section 6).

Every event is one JSON object per line, appended to `.mechy/events.jsonl`
(when the project folder exists) and, with `--json`, printed to stdout.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_lock = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Events:
    """Writes events to the project log and optionally to stdout as JSON lines."""

    def __init__(self, project: str | Path | None = None, json_stdout: bool = False,
                 quiet: bool = False):
        self.project = Path(project) if project is not None else None
        self.json_stdout = json_stdout
        self.quiet = quiet

    @property
    def log_path(self) -> Path | None:
        if self.project is None:
            return None
        d = self.project / ".mechy"
        return d / "events.jsonl" if d.is_dir() else None

    def emit(self, type: str, **fields: Any) -> dict:
        ev = {"ts": now_iso(), "type": type, **fields}
        line = json.dumps(ev, default=str)
        with _lock:
            lp = self.log_path
            if lp is not None:
                with open(lp, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
            if self.json_stdout:
                sys.stdout.write(line + "\n")
                sys.stdout.flush()
            elif not self.quiet and type != "result":
                sys.stderr.write(_human(ev) + "\n")
        return ev

    # convenience helpers -------------------------------------------------
    def file_written(self, path: str | Path) -> None:
        self.emit("file.written", path=self.rel(path))

    def progress(self, task: str, message: str, fraction: float | None = None) -> None:
        f = {"task": task, "message": message}
        if fraction is not None:
            f["fraction"] = round(float(fraction), 3)
        self.emit("task.progress", **f)

    def result(self, **fields: Any) -> dict:
        ev = self.emit("result", **fields)
        if not self.json_stdout and not self.quiet:
            sys.stdout.write(json.dumps({k: v for k, v in ev.items() if k not in ("ts", "type")},
                                        indent=2, default=str) + "\n")
        return ev

    def rel(self, path: str | Path) -> str:
        p = Path(path)
        if self.project is not None:
            try:
                return os.path.relpath(p.resolve(), self.project.resolve())
            except ValueError:
                pass
        return str(p)


def _human(ev: dict) -> str:
    t = ev["type"]
    rest = {k: v for k, v in ev.items() if k not in ("ts", "type")}
    if t == "file.written":
        return f"  wrote {rest['path']}"
    if t == "task.progress":
        return f"  [{rest.get('task')}] {rest.get('message')}"
    return f"  {t} " + " ".join(f"{k}={v}" for k, v in rest.items())
