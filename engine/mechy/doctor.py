"""`mechy doctor`: check provider CLIs, logins, Python deps, mechy_core and rendering."""

from __future__ import annotations

import importlib
import importlib.metadata as md
import os
import shutil
import subprocess
import sys

from .agents.providers import cli_bin, fake_enabled


def _run(argv: list[str], timeout: float = 15) -> tuple[int, str]:
    try:
        r = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def check_cli(provider: str) -> dict:
    from .accounts import status
    info = status(provider)
    info["login"] = {True: "yes", False: "no"}.get(info["logged_in"], "unknown")
    if info.get("detail"):
        info["login_detail"] = info["detail"]
    return info


def _module(mod: str, dist: str) -> str | None:
    try:
        importlib.import_module(mod)
    except Exception:  # noqa: BLE001
        return None
    try:
        return md.version(dist)
    except md.PackageNotFoundError:
        return "installed"


def _binary(name: str, arg: str = "-version") -> dict:
    path = shutil.which(name)
    if not path:
        return {"installed": False}
    rc, out = _run([path, arg], timeout=10)
    first = out.splitlines()[0] if out else ""
    return {"installed": True, "bin": path, "version": " ".join(first.split()[:3]) or None}


def intake_check() -> dict:
    """Optional extras for `mechy intake` (pip install -e 'engine[intake]', plus ffmpeg from the OS)."""
    yt_mod = _module("yt_dlp", "yt-dlp")
    yt_bin = shutil.which("yt-dlp")
    ff, fp = _binary("ffmpeg"), _binary("ffprobe")
    out = {
        "yt-dlp": yt_mod or (f"binary {yt_bin}" if yt_bin else "MISSING (YouTube/video links: pip install yt-dlp)"),
        "trafilatura": _module("trafilatura", "trafilatura") or "missing (optional: web pages use the stdlib parser)",
        "ffmpeg": ff.get("version") if ff["installed"] else "MISSING (video keyframes: brew install ffmpeg / apt install ffmpeg)",
        "ffprobe": fp.get("version") if fp["installed"] else "MISSING (comes with ffmpeg)",
        "faster-whisper": _module("faster_whisper", "faster-whisper") or "missing (optional: transcribe videos without captions)",
        "pillow": _module("PIL", "pillow") or "MISSING (images: pip install pillow)",
    }
    out["videos_ready"] = bool((yt_mod or yt_bin) and ff["installed"] and fp["installed"])
    out["pages_ready"] = True
    out["images_ready"] = bool(_module("PIL", "pillow"))
    return out


def docs_check() -> dict:
    """`mechy doc build` compiles with the typst Python package; the typst CLI is only for rebuilding by hand."""
    pkg = _module("typst", "typst")
    cli = _binary("typst", "--version")
    return {"typst_python": pkg or "MISSING (pip install typst)",
            "typst_cli": cli.get("version") if cli["installed"] else "not installed (optional: `typst compile` by hand)",
            "ready": bool(pkg)}


def doctor(project=None) -> dict:
    deps = {}
    ok = True
    for mod, dist in (("build123d", "build123d"), ("mujoco", "mujoco"), ("yaml", "pyyaml"), ("numpy", "numpy"),
                      ("matplotlib", "matplotlib"), ("mcp", "mcp"), ("typst", "typst")):
        try:
            importlib.import_module(mod)
            deps[dist] = md.version(dist)
        except Exception as e:  # noqa: BLE001
            deps[dist] = f"MISSING ({e.__class__.__name__})"
            ok = False
    try:
        import mechy_core  # noqa: F401
        core = {"available": True, "version": getattr(mechy_core, "__version__", "?")}
    except ImportError:
        core = {"available": False, "note": "using the pure-Python fallback (slower); pip install ./core"}
    from .cad.render import mujoco_gl_available
    gl = mujoco_gl_available()
    clis = {p: check_cli(p) for p in ("claude", "codex")}
    providers_ok = fake_enabled() or any(c["installed"] for c in clis.values())
    res = {
        "ok": ok,
        "python": sys.version.split()[0],
        "deps": deps,
        "mechy_core": core,
        "providers": clis,
        "provider_setting": os.environ.get("MECHY_PROVIDER", "auto"),
        "fake_provider": fake_enabled(),
        "agents_ready": providers_ok,
        "mujoco_gl": gl or "none (thumbnails use matplotlib; no sim video)",
        "docs": docs_check(),
        "intake": intake_check(),
        "project": str(project.root) if project is not None else None,
    }
    return res
