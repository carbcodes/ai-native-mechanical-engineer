"""`mechy accounts status`: whether the provider CLIs are installed and signed in."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

from .agents.providers import cli_bin

PROVIDERS = ("claude", "codex")


def _which(b: str) -> str | None:
    return shutil.which(b) or (b if os.path.isabs(b) and os.access(b, os.X_OK) else None)


def _run(argv: list[str], timeout: float = 15) -> tuple[int, str]:
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def _claude_login(path: str) -> dict:
    rc, out = _run([path, "auth", "status"])
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        return {"logged_in": None, "method": None, "detail": out.splitlines()[0][:200] if out else None}
    return {"logged_in": bool(d.get("loggedIn")), "method": d.get("authMethod") or None,
            "detail": None if d.get("loggedIn") else (d.get("message") or out[:200] or None)}


def _codex_login(path: str) -> dict:
    """`codex login status` prints e.g. 'Logged in using an API key - sk-proj-***x' or
    'Logged in using ChatGPT'; nonzero exit / 'Not logged in' when signed out.
    Never echo key material: anything after 'API key' is dropped."""
    rc, out = _run([path, "login", "status"])
    first = out.splitlines()[0].strip() if out else ""
    detail = re.sub(r"(?i)api key.*$", "API key", first).strip() or None
    if rc != 0 or re.search(r"not logged in", out, re.IGNORECASE):
        return {"logged_in": False, "method": None, "detail": detail}
    method = "api_key" if "API key" in out else "chatgpt" if "ChatGPT" in out else None
    return {"logged_in": True, "method": method, "detail": detail}


def status(provider: str) -> dict:
    b = cli_bin(provider)
    path = _which(b)
    if not path:
        return {"installed": False, "bin": b, "version": None, "logged_in": None, "method": None,
                "detail": "not installed"}
    rc, out = _run([path, "--version"])
    info = {"installed": True, "bin": path, "version": out.splitlines()[0] if out else None}
    info.update(_claude_login(path) if provider == "claude" else _codex_login(path))
    return info


def status_all() -> dict:
    return {p: status(p) for p in PROVIDERS}
