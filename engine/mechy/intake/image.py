"""Image intake: EXIF-free copy (orientation applied, GPS and camera data dropped) + thumbnail."""

from __future__ import annotations

import io
import shutil
import subprocess
import tempfile
from pathlib import Path

from .common import IntakeError

MAX_SIDE = 2048
THUMB_SIDE = 320


def _open(data: bytes | Path):
    from PIL import Image
    try:
        im = Image.open(io.BytesIO(data) if isinstance(data, bytes) else data)
        im.load()
        return im
    except Exception as first:  # noqa: BLE001
        # HEIC/HEIF (iPhone photos): pillow-heif if present, else macOS `sips`.
        try:
            import pillow_heif  # type: ignore
            pillow_heif.register_heif_opener()
            im = Image.open(io.BytesIO(data) if isinstance(data, bytes) else data)
            im.load()
            return im
        except Exception:  # noqa: BLE001
            pass
        if shutil.which("sips"):
            with tempfile.TemporaryDirectory() as td:
                src = Path(td, "in")
                src.write_bytes(data if isinstance(data, bytes) else Path(data).read_bytes())
                out = Path(td, "out.jpg")
                r = subprocess.run(["sips", "-s", "format", "jpeg", str(src), "--out", str(out)],
                                   capture_output=True, timeout=60)
                if r.returncode == 0 and out.exists():
                    im = Image.open(out)
                    im.load()
                    return im
        raise IntakeError(f"cannot read image: {first}") from first


def save_clean(data: bytes | Path, dst_stem: Path, max_side: int = MAX_SIDE,
               thumb: Path | None = None) -> dict:
    """Decode, apply EXIF orientation, drop all metadata, save as JPEG (or PNG with alpha).
    Returns {path, width, height, format, thumb}."""
    from PIL import Image, ImageOps
    im = _open(data)
    src_format = im.format
    if getattr(im, "is_animated", False):
        im.seek(0)
    im = ImageOps.exif_transpose(im)
    has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
    im = im.convert("RGBA" if has_alpha else "RGB")
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    dst = dst_stem.with_suffix(".png" if has_alpha else ".jpg")
    dst.parent.mkdir(parents=True, exist_ok=True)
    # a fresh image carries no EXIF/XMP/ICC text: only pixels are copied
    clean = Image.new(im.mode, im.size)
    clean.paste(im)
    if has_alpha:
        clean.save(dst, "PNG", optimize=True)
    else:
        clean.save(dst, "JPEG", quality=88, optimize=True)
    out = {"path": dst, "width": clean.width, "height": clean.height, "format": src_format}
    if thumb is not None:
        t = clean.convert("RGB")
        t.thumbnail((THUMB_SIDE, THUMB_SIDE), Image.LANCZOS)
        thumb.parent.mkdir(parents=True, exist_ok=True)
        t.save(thumb, "JPEG", quality=80)
        out["thumb"] = thumb
    return out


def image_size(data: bytes) -> tuple[int, int] | None:
    try:
        im = _open(data)
        return im.size
    except IntakeError:
        return None
