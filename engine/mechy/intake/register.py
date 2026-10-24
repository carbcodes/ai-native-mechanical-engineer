"""`mechy intake` (CLI) and the `intake_digest` / `intake_pending` MCP tools.

Wired in (round 4b): cli.py calls `add_intake_parser` / `run_intake_cli`; mcp_server.create_server
calls `register_mcp_tools`; tools.py lists "intake.digest" and "intake.pending" in TOOL_NAMES and
has `intake_digest` / `intake_pending` / `intake_digest_all`; the planner card carries both tools;
a `provider: none` card with `intake.digest` runs `digest_all` once; `mechy plan` and `mechy run`
digest pending sources first (`--no-intake` skips it; agents/runner.digest_pending).

Usage:
    mechy intake add <url-or-file> [<more> ...] [--force] [--no-transcribe] [--no-video]
                     [--max-frames 12] [--project P] [--json]
    mechy intake all       # digest every link/file in inspiration/ not digested yet
    mechy intake pending   # list them
"""

from __future__ import annotations

import argparse
from typing import Any, Callable

from ..events import Events
from ..project import Project
from .common import MAX_KEYFRAMES, IntakeError
from .digest import digest, digest_all, pending


# ------------------------------------------------------------------- CLI
def add_intake_parser(sub: argparse._SubParsersAction, common: Callable[[argparse.ArgumentParser, bool], None]
                      ) -> argparse.ArgumentParser:
    """Add `mechy intake {add,all,pending}`. `common` is cli._common (adds --project/--json)."""
    p = sub.add_parser("intake", help="digest inspiration: YouTube/video links, web pages, images, video files")
    common(p, True)
    isub = p.add_subparsers(dest="intake_cmd", required=True)
    a = isub.add_parser("add", help="digest one or more sources into inspiration/<slug>/ and inspiration/notes/")
    common(a, True)
    a.add_argument("sources", nargs="+", help="URL (YouTube, video, web page, image) or local image/video/.html/"
                   "PDF/.txt/.md/CAD file")
    a.add_argument("--force", action="store_true", help="overwrite a note a research agent already edited")
    a.add_argument("--no-transcribe", action="store_true", help="skip local faster-whisper transcription")
    a.add_argument("--no-video", action="store_true", help="remote video: metadata and captions only, no keyframes")
    a.add_argument("--max-frames", type=int, default=MAX_KEYFRAMES)
    al = isub.add_parser("all", help="digest every link in links.yaml and media file in inspiration/ not digested yet")
    common(al, True)
    al.add_argument("--no-transcribe", action="store_true")
    al.add_argument("--no-video", action="store_true")
    pe = isub.add_parser("pending", help="list sources that are not digested yet")
    common(pe, True)
    return p


def run_intake_cli(project: Project, args: argparse.Namespace, events: Events) -> dict[str, Any]:
    """Run the parsed `mechy intake ...` command; returns the result dict for ev.result()."""
    if args.intake_cmd == "pending":
        items = pending(project)
        return {"ok": True, "pending": items, "count": len(items)}
    kw = {"transcribe": not args.no_transcribe, "download_video": not args.no_video}
    if args.intake_cmd == "all":
        return digest_all(project, events=events, **kw)
    results, errors = [], []
    for s in args.sources:
        try:
            r = digest(project, s, events=events, force=args.force, max_frames=args.max_frames, **kw)
            results.append({k: r[k] for k in ("slug", "kind", "title", "note", "source_json", "frames",
                                              "contact_sheet", "transcript", "images", "embedded_videos",
                                              "warnings")})
        except IntakeError as e:
            errors.append({"source": s, "error": str(e)})
    out: dict[str, Any] = {"ok": not errors, "digested": results, "errors": errors}
    if errors and not results:
        out["error"] = "; ".join(e["error"] for e in errors)
    return out


# ------------------------------------------------------------------- MCP
def intake_digest_tool(project: Project, source: str, force: bool = False) -> dict[str, Any]:
    """Body of the `intake_digest` MCP tool (errors come back as {ok: false, error})."""
    try:
        r = digest(project, source, force=force)
    except IntakeError as e:
        return {"ok": False, "error": str(e)}
    r.pop("files", None)
    return r


def intake_pending_tool(project: Project) -> dict[str, Any]:
    items = pending(project)
    return {"ok": True, "pending": items, "count": len(items)}


def register_mcp_tools(mcp: Any, proj: Project) -> None:
    """Register intake tools on a FastMCP server (call inside mcp_server.create_server)."""

    @mcp.tool()
    def intake_digest(source: str, force: bool = False) -> dict:
        """Digest one inspiration source: a YouTube/video URL, web page URL, image URL, or a project
        path to an image/video/.html. Writes inspiration/<slug>/ (source.json, frames/ keyframes,
        contact.jpg, transcript.txt or page.txt, images/) and the skeleton note
        inspiration/notes/<slug>.md with TODO(research) lines to complete; marks links.yaml
        `digested`. Never overwrites a note you already edited unless force=true."""
        return intake_digest_tool(proj, source, force)

    @mcp.tool()
    def intake_pending() -> dict:
        """List inspiration sources (links.yaml entries and image/video files in inspiration/)
        that have no digest yet."""
        return intake_pending_tool(proj)
