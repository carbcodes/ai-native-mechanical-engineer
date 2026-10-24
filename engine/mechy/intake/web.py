"""Web page intake: title, description, main text (trafilatura when installed, else a
stdlib parser), licence hints, embedded videos and the top images."""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from .common import IntakeError, fetch, youtube_id

SKIP_TEXT_TAGS = {"script", "style", "noscript", "template", "svg", "nav", "footer", "header", "aside", "form"}
BLOCK_TAGS = {"p", "h1", "h2", "h3", "h4", "li", "td", "th", "pre", "blockquote", "figcaption", "dd", "dt"}
ICON_HINT = re.compile(r"(logo|icon|avatar|sprite|badge|emoji|spinner|pixel|tracking|placeholder|gravatar)",
                       re.IGNORECASE)
LICENSE_RE = re.compile(r"\b(CC[ -]BY(?:[ -](?:NC|SA|ND))*(?:[ -]\d\.\d)?|CC0|Creative Commons[\w\s.-]{0,40}|"
                        r"GPL-?v?\d(?:\.\d)?|LGPL-?v?\d(?:\.\d)?|MIT License|Apache License 2\.0|Apache-2\.0|"
                        r"CERN-OHL-[A-Z]-?\d\.\d|BSD[ -]\d-Clause|Public Domain)\b", re.IGNORECASE)


class _PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta: dict[str, str] = {}
        self.images: list[dict] = []
        self.iframes: list[str] = []
        self.links: list[str] = []
        self.license_links: list[str] = []
        self.blocks: list[str] = []
        self._stack: list[str] = []
        self._skip = 0
        self._in_title = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag in SKIP_TEXT_TAGS:
            self._skip += 1
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or "").lower()
            if key and a.get("content"):
                self.meta.setdefault(key, a["content"].strip())
        elif tag == "img":
            src = a.get("src") or a.get("data-src") or a.get("data-original") or ""
            if not src and a.get("srcset"):
                src = a["srcset"].split(",")[0].strip().split(" ")[0]
            if src:
                def num(x):
                    m = re.match(r"\d+", x or "")
                    return int(m.group(0)) if m else None
                self.images.append({"src": src, "alt": a.get("alt", "").strip(),
                                    "width": num(a.get("width")), "height": num(a.get("height"))})
        elif tag in ("iframe", "embed", "video", "source"):
            if a.get("src"):
                self.iframes.append(a["src"])
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if "license" in (a.get("rel") or "").lower():
                self.license_links.append(a["href"])
        elif tag == "link" and "license" in (a.get("rel") or "").lower() and a.get("href"):
            self.license_links.append(a["href"])
        if tag in BLOCK_TAGS:
            self._flush()
        self._stack.append(tag)

    def handle_endtag(self, tag):
        if tag in SKIP_TEXT_TAGS and self._skip:
            self._skip -= 1
        if tag == "title":
            self._in_title = False
        if tag in BLOCK_TAGS:
            self._flush()
        if tag in self._stack:
            while self._stack and self._stack.pop() != tag:
                pass

    def handle_data(self, data):
        if self._in_title:
            self.title += data
            return
        if not self._skip:
            self._buf.append(data)

    def _flush(self):
        txt = re.sub(r"\s+", " ", "".join(self._buf)).strip()
        self._buf = []
        if len(txt.split()) >= 3:
            self.blocks.append(txt)

    def close(self):
        super().close()
        self._flush()


def _decode(body: bytes, ctype_header: str = "") -> str:
    m = re.search(rb"<meta[^>]+charset=[\"']?([A-Za-z0-9_-]+)", body[:4096], re.IGNORECASE)
    for enc in ([m.group(1).decode("ascii", "ignore")] if m else []) + ["utf-8", "cp1252", "latin-1"]:
        try:
            return body.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return body.decode("utf-8", "replace")


def main_text(html_text: str, url: str | None, fallback_blocks: list[str]) -> tuple[str, str]:
    """(text, extractor). trafilatura when installed, else readability-lxml, else stdlib blocks."""
    try:
        import trafilatura  # type: ignore
        txt = trafilatura.extract(html_text, url=url, include_comments=False, include_tables=True,
                                  favor_recall=True, deduplicate=True)
        if txt and len(txt.split()) >= 20:
            return txt.strip(), "trafilatura"
    except Exception:  # noqa: BLE001 - optional dependency
        pass
    try:
        from readability import Document  # type: ignore
        doc = Document(html_text)
        p = _PageParser()
        p.feed(doc.summary())
        p.close()
        if p.blocks and len(" ".join(p.blocks).split()) >= 20:
            return "\n\n".join(p.blocks), "readability-lxml"
    except Exception:  # noqa: BLE001
        pass
    return "\n\n".join(fallback_blocks), "html.parser"


def parse_page(html_text: str, base_url: str) -> dict:
    p = _PageParser()
    p.feed(html_text)
    p.close()
    meta = p.meta
    title = (meta.get("og:title") or p.title or "").strip()
    title = re.sub(r"\s+", " ", title)
    desc = (meta.get("og:description") or meta.get("description") or meta.get("twitter:description") or "").strip()
    text, extractor = main_text(html_text, base_url if base_url.startswith("http") else None, p.blocks)

    imgs: list[dict] = []
    seen: set[str] = set()
    og = meta.get("og:image") or meta.get("twitter:image")
    cands = ([{"src": og, "alt": "og:image", "width": None, "height": None}] if og else []) + p.images
    for im in cands:
        src = im["src"].strip()
        if src.startswith("data:") or src.lower().endswith(".svg") or ICON_HINT.search(src + " " + im["alt"]):
            continue
        if (im["width"] and im["width"] < 120) or (im["height"] and im["height"] < 120):
            continue
        absu = urllib.parse.urljoin(base_url, src)
        if absu in seen:
            continue
        seen.add(absu)
        imgs.append({**im, "url": absu})

    videos: list[str] = []
    for s in p.iframes + p.links:
        absu = urllib.parse.urljoin(base_url, s)
        if youtube_id(absu):
            canon = f"https://www.youtube.com/watch?v={youtube_id(absu)}"
            if canon not in videos:
                videos.append(canon)
        elif re.search(r"(vimeo\.com/(?:video/)?\d+|\.(mp4|webm|mov)(\?|$))", absu, re.IGNORECASE):
            if absu not in videos:
                videos.append(absu)

    lic = None
    if p.license_links:
        href = urllib.parse.urljoin(base_url, p.license_links[0])
        m = re.search(r"creativecommons\.org/(?:licenses|publicdomain)/([a-z-]+)/(\d\.\d)", href)
        lic = f"CC {m.group(1).upper()} {m.group(2)} ({href})" if m else href
    if lic is None:
        m = LICENSE_RE.search(text + " " + " ".join(meta.values()))
        lic = m.group(0).strip() if m else None
    return {"title": title, "description": desc, "text": text, "extractor": extractor, "images": imgs,
            "videos": videos[:8], "license": lic, "site": meta.get("og:site_name"),
            "author": meta.get("author") or meta.get("article:author")}


def load_page(url_or_path: str | Path) -> tuple[str, str]:
    """(html, base_url) for an http(s)/file URL or a local .html path."""
    if isinstance(url_or_path, Path):
        return _decode(url_or_path.read_bytes()), url_or_path.resolve().as_uri()
    body, ctype, final = fetch(url_or_path)
    if ctype and "html" not in ctype and "xml" not in ctype and ctype != "text/plain":
        raise IntakeError(f"{url_or_path} is {ctype}, not a web page")
    return _decode(body), final


def fetch_image_bytes(url: str) -> bytes:
    if url.startswith("file://"):
        try:
            return Path(urllib.request.url2pathname(urllib.parse.urlparse(url).path)).read_bytes()
        except OSError as e:
            raise IntakeError(f"cannot read {url}: {e.strerror or e}") from e
    body, ctype, _ = fetch(url, max_bytes=15_000_000, timeout=20)
    if ctype and not ctype.startswith("image/") and ctype not in ("application/octet-stream", "binary/octet-stream"):
        raise IntakeError(f"{url} is {ctype}, not an image")
    return body

