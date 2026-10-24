"""Remote video intake through yt-dlp (YouTube and any site/direct URL yt-dlp supports):
metadata, subtitles or auto-captions, and a low-resolution video for keyframes."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import IntakeError

SUB_FORMATS = "vtt/srt/best"


class _Log:
    def __init__(self):
        self.warnings: list[str] = []

    def debug(self, msg):  # yt-dlp routes info through debug
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        self.warnings.append(str(msg))

    def error(self, msg):
        self.warnings.append(str(msg))


def _ydl(opts: dict, log: _Log):
    try:
        import yt_dlp  # type: ignore
    except ImportError as e:
        raise IntakeError("yt-dlp is not installed (pip install yt-dlp)") from e
    base = {"quiet": True, "no_warnings": True, "noprogress": True, "noplaylist": True, "logger": log,
            "socket_timeout": 30, "retries": 2, "extractor_retries": 1, "color": {"stderr": "never"}}
    return yt_dlp.YoutubeDL({**base, **opts})


def ytdlp_version() -> str | None:
    try:
        import yt_dlp  # type: ignore
        return yt_dlp.version.__version__
    except Exception:  # noqa: BLE001
        return None


def pick_sub_lang(info: dict) -> tuple[str | None, bool]:
    """(language, automatic?) for the best English-or-original subtitle track."""
    lang0 = (info.get("language") or "").split("-")[0] or None
    for automatic, tracks in ((False, info.get("subtitles") or {}), (True, info.get("automatic_captions") or {})):
        keys = [k for k in tracks if k != "live_chat"]
        if not keys:
            continue
        prefs = ["en", "en-US", "en-GB", "en-orig"] + ([f"{lang0}-orig", lang0] if lang0 else [])
        if automatic and lang0 and lang0 != "en":
            prefs = [f"{lang0}-orig", lang0] + prefs        # original-language auto captions are best
        for p in prefs:
            if p in keys:
                return p, automatic
        en = [k for k in keys if k.startswith("en")]
        if en:
            return sorted(en)[0], automatic
        if not automatic:
            return sorted(keys)[0], automatic
    return None, False


def fetch_video(url: str, out_dir: Path, audio_if_no_subs: bool = False, enable_file_urls: bool = False,
                max_height: int = 360, download_video: bool = True) -> dict[str, Any]:
    """Extract metadata, write subtitles (if any) and a low-res video into out_dir.
    The video is picture-only when subtitles exist (or audio_if_no_subs is False); otherwise
    it keeps the audio so a local transcriber can run on it.
    Returns {info, video, subtitles, sub_lang, sub_auto, has_audio, warnings}. Raises IntakeError
    only when even the metadata cannot be read."""
    log = _Log()
    out_dir.mkdir(parents=True, exist_ok=True)
    opts: dict[str, Any] = {"skip_download": True}
    if enable_file_urls:
        opts["enable_file_urls"] = True
    try:
        with _ydl(opts, log) as y:
            info = y.extract_info(url, download=False)
    except IntakeError:
        raise
    except Exception as e:  # noqa: BLE001
        msg = str(e).replace("\n", " ").split("; please report this issue")[0].removeprefix("ERROR: ")
        if "Tunnel connection failed: 403" in msg:
            msg += " (the network proxy blocks this host)"
        raise IntakeError(f"yt-dlp could not read {url}: {msg[:400]}") from e
    if info.get("_type") == "playlist":
        entries = [e for e in (info.get("entries") or []) if e]
        if not entries:
            raise IntakeError(f"{url} is an empty playlist")
        info = entries[0]
        log.warnings.append("playlist given: digested the first video only")

    lang, auto = pick_sub_lang(info)
    for old in list(out_dir.glob("video.*")) + list(out_dir.glob("subs.*")):
        old.unlink()
    res: dict[str, Any] = {"info": info, "video": None, "subtitles": None, "sub_lang": lang, "sub_auto": auto,
                           "warnings": log.warnings}

    if lang:
        sopts = {**opts, "skip_download": True, "writesubtitles": not auto, "writeautomaticsub": auto,
                 "subtitleslangs": [lang], "subtitlesformat": SUB_FORMATS,
                 "outtmpl": {"default": str(out_dir / "subs.%(ext)s")}}
        try:
            with _ydl(sopts, log) as y:
                y.process_ie_result(dict(info), download=True)
        except Exception as e:  # noqa: BLE001
            log.warnings.append(f"subtitle download failed: {str(e)[:200]}")
        subs = sorted(p for p in out_dir.glob("subs.*") if p.suffix in (".vtt", ".srt"))
        res["subtitles"] = subs[0] if subs else None

    need_audio = audio_if_no_subs and res["subtitles"] is None
    res["has_audio"] = need_audio
    if download_video:
        h = int(max_height)
        if need_audio:
            fmt = f"b[height<={h}]/bv*[height<={h}]+ba/w/b"
        else:   # subtitles cover the words: the picture is enough
            fmt = f"bv*[height<={h}][ext=mp4]/bv*[height<={h}]/wv*/b[height<={h}]/w/b"
        vopts = {**opts, "skip_download": False, "format": fmt, "max_filesize": 400_000_000,
                 "outtmpl": {"default": str(out_dir / "video.%(ext)s")}, "writesubtitles": False,
                 "writeautomaticsub": False, "merge_output_format": "mp4"}
        try:
            with _ydl(vopts, log) as y:
                y.process_ie_result(dict(info), download=True)
        except Exception as e:  # noqa: BLE001
            log.warnings.append(f"video download failed: {str(e)[:300]}")
        vids = sorted(p for p in out_dir.glob("video.*") if not p.name.endswith((".part", ".ytdl")))
        res["video"] = vids[0] if vids else None
    return res


def metadata(info: dict) -> dict[str, Any]:
    """The source.json fields we keep from a yt-dlp info dict."""
    chapters = [{"t": round(float(c.get("start_time") or 0), 1), "title": c.get("title")}
                for c in (info.get("chapters") or [])]
    lic = info.get("license")
    return {
        "id": info.get("id"), "title": info.get("title"),
        "uploader": info.get("uploader") or info.get("channel"),
        "channel_url": info.get("channel_url") or info.get("uploader_url"),
        "upload_date": info.get("upload_date"),
        "duration_s": info.get("duration"),
        "license": lic,
        "webpage_url": info.get("webpage_url") or info.get("original_url"),
        "extractor": info.get("extractor_key") or info.get("extractor"),
        "description": (info.get("description") or "")[:1200],
        "chapters": chapters,
        "tags": (info.get("tags") or [])[:15],
        "language": info.get("language"),
    }
