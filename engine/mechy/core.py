"""Access to the fast math core: the C++ `mechy_core` when importable, else the fallback."""

from __future__ import annotations

import importlib
import os
from types import ModuleType

_core: ModuleType | None = None


def get_core() -> ModuleType:
    """Return `mechy_core` if it imports (and MECHY_FORCE_FALLBACK is unset), else fallback_core."""
    global _core
    if _core is None:
        mod = None
        if not os.environ.get("MECHY_FORCE_FALLBACK"):
            try:
                mod = importlib.import_module("mechy_core")
            except ImportError:
                mod = None
        if mod is None:
            from . import fallback_core as mod  # type: ignore[no-redef]
        _core = mod
    return _core


def core_name() -> str:
    c = get_core()
    return "fallback" if getattr(c, "IS_FALLBACK", False) else "mechy_core"
