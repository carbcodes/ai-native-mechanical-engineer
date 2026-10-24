"""File intake: PDFs, plain text/markdown, and 3D/CAD files dropped into inspiration/.

Each writes inspiration/<slug>/source.json with kind "pdf" | "text" | "cad", a copy of the
file in inspiration/<slug>/, and the usual note skeleton in inspiration/notes/<slug>.md.
PDF text (first 20 pages) lands in <slug>/text.txt; the note quotes an excerpt so it stays
inside the skeleton word budget."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .common import IntakeError, rel_or_abs, slugify, truncate_words
from .notes import TODO

MAX_PDF_PAGES = 20
CAD_EXTS = {".stl", ".step", ".stp", ".3mf", ".obj", ".dxf", ".svg"}
TEXT_EXTS = {".txt", ".md", ".markdown"}
PDF_EXTS = {".pdf"}


def _copy(ctx, path: Path) -> Path:
    dst = ctx.dir / path.name
    if dst.resolve() != path.resolve():
        shutil.copy2(path, dst)
    ctx.wrote(dst)
    return dst


def _bbox_mm(path: Path) -> list | None:
    """Bounding box in mm when build123d can read the file (STL/STEP), else None."""
    ext = path.suffix.lower()
    try:
        if ext == ".stl":
            from build123d import import_stl
            s = import_stl(str(path))
        elif ext in (".step", ".stp"):
            from build123d import import_step
            s = import_step(str(path))
        else:
            return None
        bb = s.bounding_box()
        return [round(bb.max.X - bb.min.X, 2), round(bb.max.Y - bb.min.Y, 2),
                round(bb.max.Z - bb.min.Z, 2)]
    except Exception:  # noqa: BLE001 - odd/ascii STEP variants etc.
        return None


def _pdf(path: Path) -> dict:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise IntakeError("pypdf is required for PDFs: pip install pypdf") from e
    r = PdfReader(str(path))
    meta = r.metadata or {}
    pages = []
    for pg in r.pages[:MAX_PDF_PAGES]:
        try:
            pages.append(pg.extract_text() or "")
        except Exception:  # noqa: BLE001
            pages.append("")
    return {"pages": len(r.pages), "title": (meta.title or "").strip() or None,
            "author": (meta.author or "").strip() or None, "text": "\n\n".join(pages)}


def digest_file(ctx, src) -> tuple[dict, str, dict]:
    """Returns (meta, note, extra) like the other digest branches."""
    p = src.path
    ext = p.suffix.lower()
    dst = _copy(ctx, p)
    size_kb = dst.stat().st_size / 1024
    meta: dict[str, Any] = {"file": ctx.rel(dst), "file_type": ext.lstrip("."), "size_kb": round(size_kb, 1)}
    rows = [("File", ctx.rel(dst)), ("Source metadata", f"inspiration/{ctx.slug}/source.json")]
    excerpt = ""
    extra: dict[str, Any] = {}

    if src.kind == "pdf":
        ctx.progress("extracting text (pypdf)")
        d = _pdf(dst)
        meta.update({"pages": d["pages"], "title": d["title"], "author": d["author"]})
        tp = ctx.dir / "text.txt"
        tp.write_text(d["text"], encoding="utf-8")
        ctx.wrote(tp)
        meta["text_pages"] = min(d["pages"], MAX_PDF_PAGES)
        rows.append((f"Text (first {meta['text_pages']} of {d['pages']} pages)", ctx.rel(tp)))
        excerpt = d["text"]
        label = f"PDF, {d['pages']} pages"
    elif src.kind == "text":
        text = dst.read_text(encoding="utf-8", errors="replace")
        meta["words"] = len(text.split())
        excerpt = text
        label = f"{ext.lstrip('.')} file"
    else:  # cad
        bb = _bbox_mm(dst)
        if bb:
            meta["bbox_mm"] = bb
            label = f"{ext.lstrip('.').upper()} model, about {bb[0]:g} x {bb[1]:g} x {bb[2]:g} mm"
        else:
            label = f"{ext.lstrip('.').upper()} model ({size_kb:.0f} KB)"
    title = meta.get("title") or p.stem

    note = "\n".join([
        f"# {title} ({label})", "",
        "Source: local file", "",
        "| What | Where |", "|---|---|",
        *[f"| {w} | {p_} |" for w, p_ in rows], "",
        *([f"Excerpt: {truncate_words(' '.join(excerpt.split()), 60)}", ""] if excerpt else []),
        "## Research notes",
        f"- What it shows / why it matters for this build: {TODO}",
        f"- Dimensions, parts, specs worth copying (cite page/figure): {TODO}",
        "",
        "Not verified: machine-made digest; file contents are unchecked.",
    ])
    return meta, note, extra
