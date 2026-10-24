"""Documents: `mechy doc build <variant>` -> docs/<variant>/build_guide.pdf and report.pdf (Typst)."""

from .build import DocError, doc_build

__all__ = ["DocError", "doc_build"]
