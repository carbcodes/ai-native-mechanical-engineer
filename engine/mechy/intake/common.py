"""Shared helpers for inspiration intake: source classification, slugs, links.yaml,
HTTP fetching, timestamps and word counting. Pure functions, no LLM calls."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..events import now_iso
from ..project import Project, load_yaml, save_yaml, write_json

NOTE_WORD_LIMIT = 300          # contracts section 1: inspiration/notes/<source>.md <= 300 words
SKELETON_WORD_BUDGET = 220     # leave the research agent ~80 words to fill in
MAX_KEYFRAMES = 12
RESERVED_SLUGS = {"notes", "links", "frames"}
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/605.1.15 (KHTML, like Gecko) " \
             "Version/17.0 Safari/605.1.15 mechy-intake/1"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif", ".avif"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi", ".mpg", ".mpeg", ".wmv", ".flv", ".3gp"}
HTML_EXTS = {".html", ".htm", ".xhtml"}
PDF_EXTS = {".pdf"}
TEXT_EXTS = {".txt", ".md", ".markdown"}
CAD_EXTS = {".stl", ".step", ".stp", ".3mf", ".obj", ".dxf", ".svg"}
VIDEO_HOSTS = ("youtube.com", "youtu.be", "youtube-nocookie.com", "vimeo.com", "dailymotion.com",
               "streamable.com", "tiktok.com", "instagram.com/reel", "bilibili.com")

# Mechanism words the transcript/page excerpts are anchored on (word-boundary, plural ok).
MECH_KEYWORDS = [
    "gear", "gearbox", "belt", "pulley", "stepper", "servo", "bearing", "linkage", "torque",
    "catch", "motor", "spring", "encoder", "planetary", "cycloidal", "harmonic", "actuator",
    "lead screw", "ball screw", "cam", "clutch", "brake", "nema",
]
_KW_RE = re.compile(r"\b(" + "|".join(re.escape(k).replace(r"\ ", r"[\s-]?") for k in
                                       sorted(MECH_KEYWORDS, key=len, reverse=True)) + r")(?:e?s|ing|ed|er)?\b",
                    re.IGNORECASE)
_YT_ID_RE = re.compile(r"(?:v=|/shorts/|/embed/|/live/|youtu\.be/|/v/)([A-Za-z0-9_-]{11})")


class IntakeError(Exception):
    pass


@dataclass
class Source:
    """A classified inspiration source."""
    kind: str                 # youtube | video_url | video | image | image_url | web
    raw: str                  # what the user gave
    url: str | None = None    # for remote sources
    path: Path | None = None  # for local files


# ------------------------------------------------------------- classification
def is_url(s: str) -> bool:
    return bool(re.match(r"^(https?|file)://", s.strip(), re.IGNORECASE))


def youtube_id(url: str) -> str | None:
    u = urllib.parse.urlparse(url)
    host = (u.hostname or "").lower()
    if not any(h in host for h in ("youtube.com", "youtu.be", "youtube-nocookie.com")):
        return None
    if host.endswith("youtu.be"):
        vid = u.path.strip("/").split("/")[0]
        return vid if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid) else None
    q = urllib.parse.parse_qs(u.query).get("v")
    if q and re.fullmatch(r"[A-Za-z0-9_-]{11}", q[0]):
        return q[0]
    m = _YT_ID_RE.search(u.path)
    return m.group(1) if m else None


def classify(source: str | Path, project: Project | None = None) -> Source:
    """Decide how to digest `source` (a URL or a file path) without touching the network."""
    s = str(source).strip()
    if is_url(s):
        u = urllib.parse.urlparse(s)
        if u.scheme.lower() == "file":
            return classify(Path(urllib.request.url2pathname(u.path)), project)
        ext = Path(u.path).suffix.lower()
        if youtube_id(s):
            return Source("youtube", s, url=s)
        if ext in VIDEO_EXTS or any(h in (u.netloc + u.path).lower() for h in VIDEO_HOSTS):
            return Source("video_url", s, url=s)
        if ext in IMAGE_EXTS:
            return Source("image_url", s, url=s)
        return Source("web", s, url=s)
    p = Path(s).expanduser()
    if not p.is_absolute() and project is not None and not p.exists():
        p = project.path(s)
    p = p.resolve()
    if not p.is_file():
        raise IntakeError(f"no such file or URL: {s}")
    ext = p.suffix.lower()
    if ext in VIDEO_EXTS:
        return Source("video", s, path=p)
    if ext in IMAGE_EXTS:
        return Source("image", s, path=p)
    if ext in HTML_EXTS:
        return Source("web", s, path=p)
    if ext in PDF_EXTS:
        return Source("pdf", s, path=p)
    if ext in TEXT_EXTS:
        return Source("text", s, path=p)
    if ext in CAD_EXTS:
        return Source("cad", s, path=p)
    raise IntakeError(f"unsupported file type {ext or '(none)'} for {s}; use an image "
                      f"({', '.join(sorted(IMAGE_EXTS))}), a video, an .html file, a PDF, "
                      f"a .txt/.md file or a CAD file ({', '.join(sorted(CAD_EXTS))})")


# ----------------------------------------------------------------- slugs
def slugify(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    s = re.sub(r"-{2,}", "-", s)[:max_len].strip("-")
    return s or "source"


def short_hash(text: str, n: int = 6) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def source_key(src: Source, project: Project) -> str:
    """Stable identity of a source: canonical URL, or project-relative / absolute path."""
    if src.kind == "youtube":
        return f"youtube:{youtube_id(src.url or '')}"
    if src.url:
        return src.url.strip()
    return rel_or_abs(project, src.path)


def base_slug(src: Source) -> str:
    if src.kind == "youtube":
        return f"yt-{youtube_id(src.url or '')}"   # ids are case-sensitive: keep case
    if src.url:
        u = urllib.parse.urlparse(src.url)
        host = (u.hostname or "").lower().removeprefix("www.").removeprefix("m.")
        host = host.rsplit(".", 1)[0] if host.count(".") >= 1 else host
        path = re.sub(r"\.(html?|php|aspx?)$", "", u.path, flags=re.IGNORECASE)
        return slugify(f"{host} {path}")
    return slugify(src.path.stem)


def choose_slug(project: Project, src: Source, key: str) -> str:
    """Slug for inspiration/<slug>/; reuses the folder of an earlier digest of the same source."""
    slug = base_slug(src)
    if slug in RESERVED_SLUGS:
        slug = f"{slug}-src"
    candidates = [slug, f"{slug}-{short_hash(key)}"] + [f"{slug}-{short_hash(key)}-{i}" for i in range(2, 50)]
    for cand in candidates:
        sj = project.path("inspiration", cand, "source.json")
        if not sj.exists():
            return cand
        try:
            if json.loads(sj.read_text()).get("key") == key:
                return cand
        except (json.JSONDecodeError, OSError):
            pass
    raise IntakeError(f"could not find a free slug for {key}")


# ------------------------------------------------------------------ paths
def rel_or_abs(project: Project, p: str | Path | None) -> str:
    if p is None:
        return ""
    p = Path(p).resolve()
    try:
        return p.relative_to(project.root).as_posix()
    except ValueError:
        return str(p)


def fmt_ts(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    s = int(round(max(0.0, float(seconds))))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h}:{m:02d}:{sec:02d}" if h else f"{m}:{sec:02d}"


def word_count(text: str) -> int:
    """Words as a reader counts them: markdown pipes, dashes and #s are not words."""
    return len(re.findall(r"[A-Za-z0-9][\w'’./:@%()+-]*", text))


def keyword_hits(text: str) -> list[str]:
    """Normalised mechanism keywords found in `text`, in order of first appearance."""
    out: list[str] = []
    for m in _KW_RE.finditer(text):
        k = re.sub(r"[\s-]+", " ", m.group(1).lower())
        if k not in out:
            out.append(k)
    return out


def keyword_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for m in _KW_RE.finditer(text):
        k = re.sub(r"[\s-]+", " ", m.group(1).lower())
        counts[k] = counts.get(k, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def truncate_words(text: str, n: int) -> str:
    w = text.split()
    return " ".join(w[:n]) + (" ..." if len(w) > n else "")


# ------------------------------------------------------------------- tools
def have_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def run(cmd: list[str], timeout: float = 600, cwd: str | Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)


def fetch(url: str, max_bytes: int = 20_000_000, timeout: float = 30) -> tuple[bytes, str, str]:
    """GET url (http/https/file) honouring HTTPS_PROXY/NO_PROXY and SSL_CERT_FILE.
    Returns (body, content_type, final_url)."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*",
                                               "Accept-Language": "en;q=0.9,*;q=0.5"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - user-supplied inspiration URL
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            body = r.read(max_bytes + 1)
            if len(body) > max_bytes:
                raise IntakeError(f"{url}: larger than {max_bytes // 1_000_000} MB")
            return body, ctype, r.geturl()
    except IntakeError:
        raise
    except Exception as e:  # noqa: BLE001 - network errors become one readable message
        raise IntakeError(f"could not fetch {url}: {type(e).__name__}: {e}") from e


# -------------------------------------------------------------- links.yaml
def _same_link(a: str, b: str) -> bool:
    if a.strip() == b.strip():
        return True
    ya, yb = youtube_id(a), youtube_id(b)
    if ya and ya == yb:
        return True
    return a.strip().rstrip("/") == b.strip().rstrip("/")


def update_links(project: Project, url: str, note_rel: str, title: str | None) -> dict:
    """Mark the links.yaml entry for `url` as digested (adding the entry if it is missing).
    Shape (contracts section 8.2 + this module): links: [{url, title?, added, digested}]."""
    p = project.path("inspiration", "links.yaml")
    data = (load_yaml(p) or {}) if p.exists() else {}
    links = data.get("links") or []
    entry = next((l for l in links if isinstance(l, dict) and _same_link(str(l.get("url", "")), url)), None)
    if entry is None:
        entry = {"url": url}
        if title:
            entry["title"] = title
        entry["added"] = now_iso()
        links.append(entry)
    elif title and not entry.get("title"):
        entry["title"] = title
    entry["digested"] = note_rel
    data["links"] = links
    save_yaml(p, data)
    return entry


def save_source_json(path: Path, data: dict[str, Any]) -> Path:
    return write_json(path, data)


def env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")
