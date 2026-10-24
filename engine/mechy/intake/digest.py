"""`digest(project, source)`: turn a picture, link or video into inspiration/<slug>/ files and a
note skeleton in inspiration/notes/<slug>.md. Deterministic: no LLM calls here."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from ..events import Events
from ..project import Project, find_project, load_yaml
from . import notes as N
from .common import (CAD_EXTS, IMAGE_EXTS, MAX_KEYFRAMES, PDF_EXTS, TEXT_EXTS, VIDEO_EXTS, IntakeError, Source,
                     choose_slug, classify, is_url, rel_or_abs, save_source_json, source_key, update_links)

SCHEMA = 1
MAX_WEB_IMAGES = 6


def _project(project: Project | str | Path) -> Project:
    p = project if isinstance(project, Project) else find_project(project)
    return p.require()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class _Ctx:
    def __init__(self, project: Project, src: Source, slug: str, events: Events | None):
        self.project, self.src, self.slug, self.ev = project, src, slug, events
        self.dir = project.path("inspiration", slug)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.warnings: list[str] = []
        self.written: list[Path] = []

    def rel(self, p: Path | None) -> str | None:
        return rel_or_abs(self.project, p) if p else None

    def progress(self, msg: str) -> None:
        if self.ev:
            self.ev.progress("intake", f"{self.slug}: {msg}")

    def wrote(self, *paths: Path | None) -> None:
        self.written += [p for p in paths if p]


# ------------------------------------------------------------------ video
def _video_common(c: _Ctx, video: Path | None, subs_path: Path | None, transcribe: bool, max_frames: int,
                  meta: dict[str, Any]) -> dict[str, Any]:
    """Keyframes, contact sheet and transcript for a local video file (downloaded or user's)."""
    from . import video as V
    out: dict[str, Any] = {"frames": [], "contact": None, "transcript": None, "transcript_origin": None, "segs": []}
    probe = None
    if video is not None:
        try:
            probe = V.probe(video)
        except IntakeError as e:
            c.warnings.append(str(e))
    if probe:
        meta.update({k: probe[k] for k in ("width", "height", "fps", "video_codec", "has_audio")})
        if not meta.get("duration_s"):
            meta["duration_s"] = probe["duration_s"]
        for k, v in probe["format_tags"].items():
            if k.lower() in ("copyright", "license") and not meta.get("license"):
                meta["license"] = v
        dur = float(probe["duration_s"] or meta.get("duration_s") or 0)
        c.progress("finding scene changes")
        try:
            scores = V.scene_scores(video, dur)
        except IntakeError as e:
            c.warnings.append(str(e))
            scores = []
        times = V.pick_times(dur, scores, max_frames)
        c.progress(f"extracting {len(times)} keyframes")
        frames = V.extract_frames(video, times, c.dir / "frames")
        for f in frames:
            f["rel"] = c.rel(f["path"])
        out["frames"] = frames
        sheet = V.contact_sheet(frames, c.dir / "contact.jpg")
        out["contact"] = c.rel(sheet)
        c.wrote(*(f["path"] for f in frames), sheet)

    segs: list[tuple[float, str]] = []
    origin = None
    if subs_path is None and video is not None and c.src.kind == "video":
        subs_path = V.sidecar_subtitles(video)
    if subs_path is not None:
        segs = V.parse_subtitles(subs_path.read_text(encoding="utf-8", errors="replace"))
        origin = meta.get("_sub_origin") or f"sidecar {subs_path.name}"
    elif video is not None and probe and probe["has_audio"] and transcribe:
        segs, origin = V.whisper_transcribe(video, c.progress)
    elif c.src.kind != "video":
        origin = "no captions on the site" + ("" if transcribe and probe and probe["has_audio"] else
                                               "; pip install faster-whisper to transcribe locally")
    elif probe and not probe["has_audio"]:
        origin = "no audio track"
    else:
        origin = "no subtitles; transcription off" if not transcribe else "no subtitles"
    meta.pop("_sub_origin", None)
    tpath = c.dir / "transcript.txt"
    if segs:
        V.write_transcript(segs, tpath)
        out["transcript"] = c.rel(tpath)
        c.wrote(tpath)
    elif tpath.exists():
        tpath.unlink()
    out["transcript_origin"] = origin
    out["segs"] = segs
    return out


def _video_remote(c: _Ctx, transcribe: bool, max_frames: int, download_video: bool) -> tuple[dict, str, dict]:
    from . import youtube as Y
    url = c.src.url or ""
    c.progress("reading metadata and subtitles (yt-dlp)")
    import importlib.util
    whisper = transcribe and importlib.util.find_spec("faster_whisper") is not None
    r = Y.fetch_video(url, c.dir, audio_if_no_subs=whisper, enable_file_urls=url.startswith("file://"),
                      download_video=download_video)
    info, video = r["info"], r["video"]
    c.warnings += r["warnings"]
    if download_video and video is None:
        c.warnings.append("no video file: keyframes skipped")
    meta = Y.metadata(info)
    meta["ytdlp"] = Y.ytdlp_version()
    if r["subtitles"]:
        meta["_sub_origin"] = f"{'auto-captions' if r['sub_auto'] else 'subtitles'}, {r['sub_lang']}"
    if video is not None:
        (c.dir / ".gitignore").write_text("# downloaded copy; re-create with `mechy intake add <url>`\nvideo.*\n")
    v = _video_common(c, video, r["subtitles"], transcribe, max_frames, meta)
    if r["subtitles"] is not None:
        r["subtitles"].unlink(missing_ok=True)   # transcript.txt holds the clean text
    title = meta.get("title") or url
    note = N.video_note(slug=c.slug, kind=c.src.kind, title=title, source=meta.get("webpage_url") or url, meta=meta,
                        frames=v["frames"], contact=v["contact"], transcript_rel=v["transcript"],
                        transcript_origin=v["transcript_origin"], segs=v["segs"], video_rel=c.rel(video),
                        warnings=c.warnings)
    meta.update({"url": url, "video": c.rel(video)})
    return meta, note, v


def _video_local(c: _Ctx, transcribe: bool, max_frames: int) -> tuple[dict, str, dict]:
    path = c.src.path
    meta: dict[str, Any] = {"title": path.stem.replace("_", " ").replace("-", " ").strip() or path.name,
                            "path": c.rel(path), "license": None}
    v = _video_common(c, path, None, transcribe, max_frames, meta)
    if not v["frames"]:
        raise IntakeError(f"could not read any frames from {path.name}: {'; '.join(c.warnings)}")
    note = N.video_note(slug=c.slug, kind="video", title=meta["title"], source=c.rel(path), meta=meta,
                        frames=v["frames"], contact=v["contact"], transcript_rel=v["transcript"],
                        transcript_origin=v["transcript_origin"], segs=v["segs"], video_rel=None,
                        warnings=c.warnings)
    return meta, note, v


# ------------------------------------------------------------------ image
def _image(c: _Ctx) -> tuple[dict, str, dict]:
    from . import image as I
    if c.src.url:
        from .web import fetch_image_bytes
        data: bytes | Path = fetch_image_bytes(c.src.url)
        source = c.src.url
        title = Path(c.src.url.split("?")[0]).stem or "image"
    else:
        data = c.src.path
        source = c.rel(c.src.path)
        title = c.src.path.stem
    for old in list(c.dir.glob("image.*")):
        old.unlink()
    im = I.save_clean(data, c.dir / "image", thumb=c.dir / "thumb.jpg")
    im["rel"] = c.rel(im["path"])
    c.wrote(im["path"], im.get("thumb"))
    kept = None
    if c.src.path is not None:
        try:
            c.src.path.resolve().relative_to(c.project.root)
            kept = c.rel(c.src.path)
        except ValueError:
            kept = None   # outside the project: only the EXIF-free copy is stored
    note = N.image_note(slug=c.slug, title=title, source=source, image=im, thumb_rel=c.rel(im.get("thumb")),
                        original_kept=kept)
    meta = {"title": title, "url": c.src.url, "path": None if c.src.url else source, "license": None,
            "width": im["width"], "height": im["height"], "original_format": im.get("format"),
            "image": im["rel"], "thumb": c.rel(im.get("thumb"))}
    return meta, note, {"images": [im["rel"]]}


# -------------------------------------------------------------------- web
def _web(c: _Ctx, max_images: int = MAX_WEB_IMAGES) -> tuple[dict, str, dict]:
    from . import image as I
    from . import web as W
    c.progress("fetching page")
    if c.src.url:
        html, base = W.load_page(c.src.url)
        source = c.src.url
    else:
        html, base = W.load_page(c.src.path)
        source = c.rel(c.src.path)
    page = W.parse_page(html, base)
    title = page["title"] or (c.src.path.stem if c.src.path else c.src.url)
    tpath = c.dir / "page.txt"
    text_rel = None
    if page["text"].strip():
        tpath.write_text(page["text"].strip() + "\n", encoding="utf-8")
        text_rel = c.rel(tpath)
        c.wrote(tpath)
    img_dir = c.dir / "images"
    if img_dir.exists():
        shutil.rmtree(img_dir)
    images: list[dict] = []
    tried = 0
    for cand in page["images"]:
        if len(images) >= max_images or tried >= 3 * max_images:
            break
        tried += 1
        try:
            data = W.fetch_image_bytes(cand["url"])
            im = I.save_clean(data, img_dir / f"{len(images) + 1:02d}")
        except IntakeError as e:
            c.warnings.append(f"image skipped: {str(e)[:120]}")
            continue
        if min(im["width"], im["height"]) < 120:
            im["path"].unlink()
            continue
        im.update({"rel": c.rel(im["path"]), "url": cand["url"], "alt": cand.get("alt")})
        images.append(im)
        c.wrote(im["path"])
    c.progress(f"{len(images)} images kept")
    note = N.web_note(slug=c.slug, title=title, source=source, page=page, images=images, text_rel=text_rel,
                      warnings=[w for w in c.warnings if not w.startswith("image skipped")][:2])
    meta = {"title": title, "url": c.src.url, "path": None if c.src.url else source, "license": page["license"],
            "site": page["site"], "author": page["author"], "description": page["description"][:600],
            "text_extractor": page["extractor"], "page_text": text_rel, "embedded_videos": page["videos"],
            "images": [{"path": im["rel"], "url": im["url"], "alt": im["alt"], "width": im["width"],
                        "height": im["height"]} for im in images]}
    return meta, note, {"images": [im["rel"] for im in images], "videos": page["videos"]}


# ------------------------------------------------------------------ entry
def digest(project: Project | str | Path, source: str | Path, *, events: Events | None = None,
           force: bool = False, transcribe: bool = True, max_frames: int = MAX_KEYFRAMES,
           download_video: bool = True) -> dict[str, Any]:
    """Digest one inspiration source into the project.

    source: a YouTube/video URL, a web page URL, an image URL, or a local video/image/.html
    path (absolute, or relative to the cwd or the project root).

    Writes inspiration/<slug>/source.json (+ frames/, contact.jpg, transcript.txt, page.txt,
    images/, image.jpg, thumb.jpg as relevant) and inspiration/notes/<slug>.md (a skeleton of
    <= 220 words with TODO(research) lines). URL sources get `digested: <note path>` in
    inspiration/links.yaml. A note a research agent already edited is never overwritten
    (the new skeleton goes to inspiration/<slug>/note.skeleton.md) unless force=True.

    Returns {ok, slug, kind, title, note, source_json, frames, transcript, images, warnings, files}.
    Raises IntakeError when nothing useful could be read."""
    proj = _project(project)
    src = classify(source, proj)
    key = source_key(src, proj)
    slug = choose_slug(proj, src, key)
    c = _Ctx(proj, src, slug, events)
    sj = c.dir / "source.json"
    prior = json.loads(sj.read_text()) if sj.exists() else {}
    c.progress(f"digesting {src.kind}")

    if src.kind in ("youtube", "video_url"):
        meta, note, extra = _video_remote(c, transcribe, max_frames, download_video)
    elif src.kind == "video":
        meta, note, extra = _video_local(c, transcribe, max_frames)
    elif src.kind in ("image", "image_url"):
        meta, note, extra = _image(c)
    elif src.kind in ("pdf", "text", "cad"):
        from .files import digest_file
        meta, note, extra = digest_file(c, src)
    else:
        meta, note, extra = _web(c)

    note_path = proj.path("inspiration", "notes", f"{slug}.md")
    note_path.parent.mkdir(parents=True, exist_ok=True)
    edited = note_path.exists() and _sha(note_path.read_text(encoding="utf-8")) != prior.get("note_sha256")
    skeleton_path = c.dir / "note.skeleton.md"
    if edited and not force:
        skeleton_path.write_text(note, encoding="utf-8")
        c.warnings.append(f"{c.rel(note_path)} was edited after the last digest; kept it, new skeleton in "
                          f"{c.rel(skeleton_path)}")
        c.wrote(skeleton_path)
        note_sha = prior.get("note_sha256")
    else:
        note_path.write_text(note, encoding="utf-8")
        skeleton_path.unlink(missing_ok=True)
        note_sha = _sha(note)
        c.wrote(note_path)
    note_rel = c.rel(note_path)

    frames = [{"t": f["t"], "path": f["rel"], "scene_score": f["scene_score"]} for f in extra.get("frames", [])]
    data = {"schema": SCHEMA, "kind": src.kind, "key": key, "slug": slug, "input": str(source),
            "title": meta.get("title"), "url": meta.get("url") or src.url, "duration_s": meta.get("duration_s"),
            "license": meta.get("license"), **{k: v for k, v in meta.items() if k not in ("title", "url")}}
    if frames:
        data["frames"] = frames
        data["contact_sheet"] = extra.get("contact")
    if src.kind in ("youtube", "video_url", "video"):
        data["transcript"] = {"path": extra.get("transcript"), "origin": extra.get("transcript_origin")}
    data.update({"note": note_rel, "note_sha256": note_sha, "warnings": c.warnings})
    save_source_json(sj, data)
    c.wrote(sj)
    link = src.url or (str(source).strip() if is_url(str(source)) else None)   # file:// links too
    if link:
        update_links(proj, link, note_rel, meta.get("title"))
        c.wrote(proj.path("inspiration", "links.yaml"))
    if c.ev:
        for p in dict.fromkeys(c.written):
            c.ev.file_written(p)
    return {"ok": True, "slug": slug, "kind": src.kind, "title": meta.get("title"), "note": note_rel,
            "source_json": c.rel(sj), "frames": [f["path"] for f in frames], "contact_sheet": extra.get("contact"),
            "transcript": extra.get("transcript"), "images": extra.get("images", []),
            "embedded_videos": extra.get("videos", []), "warnings": c.warnings,
            "files": [c.rel(p) for p in dict.fromkeys(c.written)]}


# ------------------------------------------------------------------- batch
def digested_sources(project: Project) -> dict[str, str]:
    """key -> note path, from every inspiration/*/source.json."""
    out = {}
    for sj in sorted(project.path("inspiration").glob("*/source.json")):
        try:
            d = json.loads(sj.read_text())
            out[d["key"]] = d.get("note", "")
            if d.get("input"):
                out.setdefault(f"input:{d['input']}", d.get("note", ""))
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return out


def pending(project: Project | str | Path) -> list[str]:
    """Sources not digested yet: links.yaml entries without a live `digested` note, and image or
    video files dropped at the top of inspiration/ that have no digest."""
    proj = _project(project)
    done = digested_sources(proj)
    out: list[str] = []
    lp = proj.path("inspiration", "links.yaml")
    links = ((load_yaml(lp) or {}).get("links") or []) if lp.exists() else []
    for l in links:
        if not isinstance(l, dict) or not l.get("url"):
            continue
        d = l.get("digested")
        if not d or not proj.path(d).exists():
            out.append(str(l["url"]))
    insp = proj.path("inspiration")
    for f in sorted(insp.iterdir()) if insp.is_dir() else []:
        if f.is_file() and f.suffix.lower() in IMAGE_EXTS | VIDEO_EXTS | PDF_EXTS | TEXT_EXTS | CAD_EXTS:
            rel = rel_or_abs(proj, f)
            if rel not in done and f"input:{rel}" not in done:
                out.append(rel)
    return out


def digest_all(project: Project | str | Path, *, events: Events | None = None, **kw: Any) -> dict[str, Any]:
    """Digest everything `pending()` lists; one failure does not stop the rest."""
    proj = _project(project)
    results, errors = [], []
    for s in pending(proj):
        try:
            results.append(digest(proj, s, events=events, **kw))
        except IntakeError as e:
            errors.append({"source": s, "error": str(e)})
    return {"ok": not errors, "digested": [{"source": r["source_json"], "note": r["note"], "kind": r["kind"]}
                                           for r in results], "errors": errors}
