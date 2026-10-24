"""Video digestion with ffmpeg: probe, scene-change keyframes, contact sheet, subtitles and
optional local transcription (faster-whisper, only when installed)."""

from __future__ import annotations

import html
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .common import MAX_KEYFRAMES, IntakeError, fmt_ts, have_ffmpeg, run

SCENE_THRESHOLD = 0.25


# ------------------------------------------------------------------ probe
def probe(path: Path) -> dict[str, Any]:
    """Duration, size, fps and whether there is an audio track (ffprobe)."""
    if not have_ffmpeg():
        raise IntakeError("ffmpeg/ffprobe not found on PATH (macOS: brew install ffmpeg)")
    r = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
            timeout=60)
    if r.returncode != 0:
        raise IntakeError(f"ffprobe could not read {path.name}: {r.stderr.strip()[-300:]}")
    info = json.loads(r.stdout or "{}")
    streams = info.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), None)
    if v is None:
        raise IntakeError(f"{path.name} has no video stream")
    dur = info.get("format", {}).get("duration") or v.get("duration")
    fps = None
    if v.get("avg_frame_rate") and v["avg_frame_rate"] != "0/0":
        n, d = v["avg_frame_rate"].split("/")
        fps = round(float(n) / float(d), 3) if float(d) else None
    return {
        "duration_s": round(float(dur), 3) if dur else None,
        "width": v.get("width"), "height": v.get("height"), "fps": fps,
        "video_codec": v.get("codec_name"),
        "has_audio": any(s.get("codec_type") == "audio" for s in streams),
        "format_tags": {k: v for k, v in (info.get("format", {}).get("tags") or {}).items()
                        if k.lower() in ("title", "artist", "comment", "copyright", "license")},
    }


# -------------------------------------------------------------- keyframes
def scene_scores(path: Path, duration: float) -> list[tuple[float, float]]:
    """(time, scene score) for frames sampled at a low rate. Deterministic for a given file."""
    rate = 4 if duration <= 300 else 2 if duration <= 1200 else 1
    with tempfile.TemporaryDirectory() as td:
        r = run(["ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error", "-i", str(path), "-an", "-sn",
                 "-vf", f"fps={rate},scale=160:-2,select='gte(scene\\,0)',metadata=print:file=scores.txt",
                 "-f", "null", "-"], timeout=max(120, duration * 2), cwd=td)
        txt = Path(td, "scores.txt").read_text() if Path(td, "scores.txt").exists() else ""
    if r.returncode != 0 and not txt:
        raise IntakeError(f"ffmpeg scene detection failed: {r.stderr.strip()[-300:]}")
    out: list[tuple[float, float]] = []
    t = None
    for line in txt.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t = float(m.group(1))
            continue
        m = re.search(r"lavfi\.scene_score=([\d.]+)", line)
        if m and t is not None:
            out.append((round(t, 3), round(float(m.group(1)), 4)))
            t = None
    return out


def pick_times(duration: float, scores: list[tuple[float, float]], max_frames: int = MAX_KEYFRAMES
               ) -> list[tuple[float, float | None]]:
    """Choose keyframe times: strongest scene cuts first (spread at least min_gap apart),
    then fill evenly so long shots are still covered. Returns [(t, score or None)] by time."""
    if duration <= 0:
        return [(0.0, None)]
    target = max(1, min(max_frames, int(duration // 2) or 1))
    min_gap = max(1.0, duration / (2.5 * target))
    end = max(0.0, duration - 0.05)
    picked: list[tuple[float, float | None]] = []

    def far(t: float) -> bool:
        return all(abs(t - p) >= min_gap for p, _ in picked)

    cuts = sorted((s for s in scores if s[1] >= SCENE_THRESHOLD and 0 < s[0] < end), key=lambda s: (-s[1], s[0]))
    for t, sc in cuts:
        if len(picked) >= target:
            break
        # a cut's first frame can be a blend; nudge a little into the new shot
        tt = min(end, t + 0.25)
        if far(tt):
            picked.append((round(tt, 2), sc))
    grid = [round((i + 0.5) * duration / target, 2) for i in range(target)]
    for t in grid:
        if len(picked) >= target:
            break
        if far(t):
            picked.append((min(t, round(end, 2)), None))
    return sorted(picked, key=lambda p: p[0])


def extract_frames(path: Path, times: list[tuple[float, float | None]], out_dir: Path) -> list[dict]:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink()
    frames = []
    for i, (t, sc) in enumerate(times, 1):
        m, s = divmod(int(t), 60)
        name = f"{i:02d}_{m:02d}m{s:02d}s.jpg"
        dst = out_dir / name
        r = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{t:.3f}", "-i", str(path),
                 "-frames:v", "1", "-an", "-vf", "scale='min(640,iw)':-2", "-q:v", "4", str(dst)], timeout=120)
        if r.returncode != 0 or not dst.exists():
            continue
        frames.append({"t": t, "path": dst, "scene_score": sc})
    return frames


def contact_sheet(frames: list[dict], dst: Path, cols: int = 4, width: int = 320) -> Path | None:
    """One image with every keyframe and its timestamp, for a quick look."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:  # pragma: no cover - Pillow comes with matplotlib
        return None
    if not frames:
        return None
    thumbs = []
    for f in frames:
        with Image.open(f["path"]) as im:
            im = im.convert("RGB")
            h = max(1, round(im.height * width / im.width))
            thumbs.append((im.resize((width, h)), f["t"]))
    cell_h = max(t.height for t, _ in thumbs)
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * width, rows * cell_h), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for i, (im, t) in enumerate(thumbs):
        x, y = (i % cols) * width, (i // cols) * cell_h
        sheet.paste(im, (x, y))
        label = f"{i + 1:02d}  {fmt_ts(t)}"
        draw.rectangle([x, y, x + 8 + 7 * len(label), y + 16], fill=(0, 0, 0))
        draw.text((x + 4, y + 3), label, fill=(255, 255, 255))
    dst.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dst, "JPEG", quality=82)
    return dst


# ------------------------------------------------------------ subtitles
_TS = r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})"


def _ts_seconds(m: re.Match) -> float:
    h, mi, s, ms = m.groups()
    return int(h or 0) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse_subtitles(text: str) -> list[tuple[float, str]]:
    """WebVTT or SRT -> [(start_s, text)], with YouTube auto-caption roll-up duplicates removed."""
    segs: list[tuple[float, str]] = []
    last_line = ""
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    for b in blocks:
        lines = b.strip("\n").split("\n")
        idx = next((i for i, l in enumerate(lines) if "-->" in l), None)
        if idx is None:
            continue
        m = re.search(_TS, lines[idx])
        if not m:
            continue
        start = _ts_seconds(m)
        for raw in lines[idx + 1:]:
            line = html.unescape(re.sub(r"<[^>]+>", "", raw)).strip()
            line = re.sub(r"\s+", " ", line)
            if not line or line == last_line or line in ("[Music]", "[Applause]"):
                continue
            # roll-up captions repeat the previous line as a prefix
            if last_line and line.startswith(last_line):
                line = line[len(last_line):].strip()
                if not line:
                    continue
            segs.append((round(start, 2), line))
            last_line = line
    return segs


def write_transcript(segs: list[tuple[float, str]], dst: Path) -> Path:
    dst.write_text("".join(f"[{fmt_ts(t)}] {txt}\n" for t, txt in segs), encoding="utf-8")
    return dst


def read_transcript(path: Path) -> list[tuple[float, str]]:
    """Parse a transcript.txt written by write_transcript ("[m:ss] text" or "[h:mm:ss] text")."""
    segs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\[([\d:]+)\]\s*(.*)", line)
        if not m:
            continue
        parts = [int(x) for x in m.group(1).split(":")]
        t = 0
        for x in parts:
            t = t * 60 + x
        segs.append((float(t), m.group(2)))
    return segs


def sidecar_subtitles(video: Path) -> Path | None:
    for ext in (".vtt", ".srt", ".en.vtt", ".en.srt"):
        p = video.with_name(video.stem + ext)
        if p.exists():
            return p
    return None


def whisper_transcribe(video: Path, events_cb=None) -> tuple[list[tuple[float, str]], str]:
    """Transcribe with faster-whisper if it is installed. Returns (segments, note).
    Lazy import: when the package is absent this returns ([], reason) and costs nothing."""
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        return [], "faster-whisper not installed (pip install faster-whisper for local transcription)"
    model_name = os.environ.get("MECHY_WHISPER_MODEL", "base")
    try:
        with tempfile.TemporaryDirectory() as td:
            wav = Path(td, "audio.wav")
            r = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(video), "-vn", "-ac", "1",
                     "-ar", "16000", str(wav)], timeout=900)
            if r.returncode != 0:
                return [], f"audio extraction failed: {r.stderr.strip()[-200:]}"
            if events_cb:
                events_cb(f"transcribing with faster-whisper ({model_name})")
            model = WhisperModel(model_name, device="cpu", compute_type="int8")
            segments, _info = model.transcribe(str(wav), beam_size=1, vad_filter=True)
            return [(round(s.start, 2), s.text.strip()) for s in segments if s.text.strip()], \
                f"faster-whisper {model_name}"
    except Exception as e:  # noqa: BLE001 - transcription is optional
        return [], f"faster-whisper failed: {type(e).__name__}: {e}"
