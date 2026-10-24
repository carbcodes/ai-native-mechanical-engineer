"""Plot style shared by every sim: the app's drafting-sheet look (docs/architecture/ui-style.md).

Paper background, ink hairlines, mono annotations, no top/right spines, accent blue only for the
thing that matters. `apply()` is cheap and idempotent; call it before building a figure."""

from __future__ import annotations

PAPER = "#ECECEA"
SURFACE = "#F5F5F3"
INK = "#1C1C1C"
MUTED = "#6B6B6B"
GRID = "#D5D5D2"
ACCENT = "#20A4F3"
GOOD = "#1E7F4F"
DANGER = "#C8102E"
WARN = "#D98A00"
# one hue per motor / joint, muted enough to sit on paper
JOINT_COLORS = {"base": "#1C1C1C", "shoulder": ACCENT, "elbow": "#D98A00", "wrist": "#8A8A86"}


def apply():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "figure.facecolor": PAPER, "savefig.facecolor": PAPER, "axes.facecolor": SURFACE,
        "axes.edgecolor": INK, "axes.linewidth": 0.8, "axes.labelcolor": INK, "axes.titlecolor": INK,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
        "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.labelsize": 8, "axes.axisbelow": True,
        "grid.color": GRID, "grid.linewidth": 0.5, "grid.linestyle": "-",
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
        "xtick.major.width": 0.6, "ytick.major.width": 0.6, "xtick.major.size": 3, "ytick.major.size": 3,
        "text.color": INK, "font.family": ["Menlo", "DejaVu Sans Mono"], "font.size": 8,
        "legend.frameon": False, "legend.fontsize": 7.5, "lines.linewidth": 1.4,
        "savefig.dpi": 200, "figure.dpi": 110,
    })
    # Menlo is macOS only; matplotlib warns once per missing family, which is just noise here
    import logging
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    return plt


def title_block(fig, left: str, right: str):
    """Small drawing-sheet strip under the plot: what it is on the left, variant / sheet on the right."""
    fig.text(0.012, 0.012, left.upper(), fontsize=6.5, color=MUTED, ha="left", va="bottom")
    fig.text(0.988, 0.012, right.upper(), fontsize=6.5, color=MUTED, ha="right", va="bottom")
