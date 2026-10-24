"""Inspiration intake: pictures, links and videos -> inspiration/<slug>/ + note skeletons.

    from mechy.intake import digest, digest_all, pending
    digest(project, "https://www.youtube.com/watch?v=...")   # or a web page, image, video file

Deterministic (ffmpeg, yt-dlp, Pillow, trafilatura); no LLM calls. A research agent completes
the TODO(research) lines of inspiration/notes/<slug>.md afterwards."""

from .common import IntakeError, classify
from .digest import digest, digest_all, pending

__all__ = ["IntakeError", "classify", "digest", "digest_all", "pending"]
