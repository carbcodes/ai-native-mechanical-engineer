"""Figures for the documents: dimensioned part drawings (true scale), assembly-step renders, and
result charts, all in the drawing-sheet style (ui-style.md)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .raster import STYLE, camera, paper, read_stl, render, save_png

MONO = "DejaVu Sans Mono"        # ships with matplotlib, so every machine has it
GOOD, DANGER = "#1E7F4F", "#C8102E"
SCALES = [(5, "5:1"), (2, "2:1"), (1, "1:1"), (0.5, "1:2"), (0.4, "1:2.5"), (0.25, "1:4"), (0.2, "1:5"),
          (0.1, "1:10")]
DPI = 200


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.family": MONO, "font.size": 6.5, "svg.fonttype": "path",
                         "axes.edgecolor": "#1C1C1C", "axes.linewidth": 0.5, "text.color": "#1C1C1C",
                         "axes.labelcolor": "#1C1C1C", "xtick.color": "#1C1C1C", "ytick.color": "#1C1C1C",
                         "xtick.major.width": 0.4, "ytick.major.width": 0.4, "hatch.linewidth": 0.3})
    return plt


# ------------------------------------------------------------------ part drawings
def _dim(ax, p0, p1, offset, text, vertical=False, ext_from=None):
    """Dimension line between paper points p0..p1, pushed `offset` mm outward, with extension lines."""
    (x0, y0), (x1, y1) = p0, p1
    kw = dict(color="#1C1C1C", lw=0.35)
    if vertical:
        xd = x0 + offset
        ax.plot([x0 + np.sign(offset) * 1, xd + np.sign(offset) * 1.5], [y0, y0], **kw)
        ax.plot([x1 + np.sign(offset) * 1, xd + np.sign(offset) * 1.5], [y1, y1], **kw)
        ax.annotate("", (xd, y0), (xd, y1), arrowprops=dict(arrowstyle="<|-|>", lw=0.35, color="#1C1C1C",
                                                             shrinkA=0, shrinkB=0, mutation_scale=4))
        if abs(y1 - y0) < 9:            # too short for the text: put it above the dimension
            ax.text(xd, max(y0, y1) + 2, text, ha="center", va="bottom", fontsize=6.5)
        else:
            ax.text(xd - 1.6, (y0 + y1) / 2, text, rotation=90, ha="center", va="center", fontsize=6.5,
                    bbox=dict(facecolor=paper(), edgecolor="none", pad=0.6))
    else:
        yd = y0 + offset
        ax.plot([x0, x0], [y0 + np.sign(offset) * 1, yd + np.sign(offset) * 1.5], **kw)
        ax.plot([x1, x1], [y1 + np.sign(offset) * 1, yd + np.sign(offset) * 1.5], **kw)
        ax.annotate("", (x0, yd), (x1, yd), arrowprops=dict(arrowstyle="<|-|>", lw=0.35, color="#1C1C1C",
                                                             shrinkA=0, shrinkB=0, mutation_scale=4))
        if abs(x1 - x0) < 9:
            ax.text(max(x0, x1) + 2, yd, text, ha="left", va="center", fontsize=6.5)
        else:
            ax.text((x0 + x1) / 2, yd + 1.3, text, ha="center", va="bottom", fontsize=6.5,
                    bbox=dict(facecolor=paper(), edgecolor="none", pad=0.6))


def part_drawing(stl: Path, out: Path, area_mm=(190.0, 140.0)) -> dict:
    """Third-angle drawing of one printed part in its print orientation: FRONT (x-z), TOP (x-y) above it,
    RIGHT (y-z) beside it, all at one standard scale, overall dimensions, plus a not-to-scale iso view in the
    free corner. Saved as SVG sized area_mm, so it prints true to scale. Returns dims and scale."""
    plt = _plt()
    v, t = read_stl(stl)
    lo, hi = v.min(0), v.max(0)
    X, Y, Z = (hi - lo)
    Wp, Hp = area_mm
    gap, pad = 22.0, 13.0
    iso_w = 0.36 * Wp
    scale, label = SCALES[-1]
    for s, lab in SCALES:
        if (X + Y) * s + gap + 2 * pad <= Wp and (Z + Y) * s + gap + 2 * pad <= Hp and Y * s + pad <= Wp - iso_w:
            scale, label = s, lab
            break
    fig = plt.figure(figsize=(Wp / 25.4, Hp / 25.4))
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, Wp)
    ax.set_ylim(0, Hp)
    ax.set_aspect("equal")
    ax.set_axis_off()
    fig.patch.set_alpha(0)
    mesh = [(v, t, STYLE["printed"])]
    fx, fy = pad + 4, pad + 2                                     # front view origin on paper (mm)
    views = {
        "front": ((lo[0], hi[0], lo[2], hi[2]), (fx, fy)),
        "top": ((lo[0], hi[0], lo[1], hi[1]), (fx, fy + Z * scale + gap)),
        "right": ((lo[1], hi[1], lo[2], hi[2]), (fx + X * scale + gap, fy)),
    }
    m = 0.5                                                      # world-mm margin around each view
    for name, ((u0, u1, w0, w1), (px, py)) in views.items():
        fr = (u0 - m, u1 + m, w0 - m, w1 + m)
        wpx = max(8, int((u1 - u0 + 2 * m) * scale / 25.4 * DPI))
        hpx = max(8, int((w1 - w0 + 2 * m) * scale / 25.4 * DPI))
        img, _ = render(mesh, name, (wpx, hpx), frame=fr, ss=2, bg=paper())
        rgba = np.dstack([img, np.where(np.all(np.abs(img - np.asarray(paper())) < 1e-3, axis=2), 0.0, 1.0)])
        ax.imshow(rgba, extent=(px - m * scale, px + (u1 - u0 + m) * scale, py - m * scale,
                                py + (w1 - w0 + m) * scale), interpolation="bilinear", zorder=2)
        lw = (u1 - u0) * scale
        ax.text(px + lw / 2, py - 3 if name == "top" else py - 13.5, name.upper(), ha="center", va="top",
                fontsize=6, color="#6B6B6B")
    # bed line under FRONT and RIGHT (the print bed is z = 0)
    for px, w in ((fx, X), (fx + X * scale + gap, Y)):
        ax.plot([px - 3, px + w * scale + 3], [fy, fy], color="#1C1C1C", lw=0.5, ls=(0, (4, 3)), zorder=1)
    ax.text(fx + X * scale + gap + Y * scale + 4, fy, "BED", fontsize=5, ha="left", va="center", color="#6B6B6B")
    # overall dimensions
    _dim(ax, (fx, fy), (fx + X * scale, fy), -9, f"{X:.1f}")
    _dim(ax, (fx, fy), (fx, fy + Z * scale), -9, f"{Z:.1f}", vertical=True)
    rx = fx + X * scale + gap
    _dim(ax, (rx, fy), (rx + Y * scale, fy), -9, f"{Y:.1f}")
    # iso, not to scale, in the free top-right corner
    ix0 = max(rx + 4, Wp - iso_w)
    iy0 = fy + Z * scale + gap * 0.6
    iw, ih = Wp - ix0 - 2, Hp - iy0 - 2
    if iw > 25 and ih > 25:
        img, _ = render(mesh, "iso", (int(iw / 25.4 * DPI), int(ih / 25.4 * DPI)), ss=2, bg=paper(), margin=0.08)
        rgba = np.dstack([img, np.where(np.all(np.abs(img - np.asarray(paper())) < 1e-3, axis=2), 0.0, 1.0)])
        ax.imshow(rgba, extent=(ix0, ix0 + iw, iy0, iy0 + ih), interpolation="bilinear", zorder=2)
        ax.text(ix0 + iw / 2, iy0 - 1, "ISO (NOT TO SCALE)", ha="center", va="top", fontsize=6, color="#6B6B6B")
    out = Path(out)
    fig.savefig(out, format=out.suffix[1:], transparent=True)
    plt.close(fig)
    return {"dims_mm": [round(float(X), 1), round(float(Y), 1), round(float(Z), 1)], "scale": label,
            "triangles": int(len(t))}


# ------------------------------------------------------------------ assembly renders
def step_render(meshes: list[dict], new: set[str], done: set[str], out: Path, size=(1100, 820),
                explode_m: float = 0.05, view=(24, -58), focus: float = 0.45) -> Path:
    """Assembly so far: parts from earlier steps light grey, this step's parts in accent blue, moved
    `explode_m` away from the earlier parts (none for the first step). Orthographic. When the new parts
    are small next to the whole, the view zooms on them (their box grown by 1.6x, but never below
    `focus` of the whole assembly's extent) so small parts stay legible."""
    prev = [m for m in meshes if m["name"] in done]
    cur = [m for m in meshes if m["name"] in new]
    shift = np.zeros(3)
    if prev and cur and explode_m:
        cp = np.vstack([m["v"] for m in prev]).mean(0)
        cn = np.vstack([m["v"] for m in cur]).mean(0)
        dvec = cn - cp
        if np.linalg.norm(dvec) > 1e-6:
            shift = dvec / np.linalg.norm(dvec) * explode_m
    items = [(m["v"], m["t"], STYLE["context"]) for m in prev]
    items += [(m["v"] + shift, m["t"], STYLE["new"]) for m in cur]
    if not items:
        items = [(m["v"], m["t"], STYLE["context"]) for m in meshes]
    frame = None
    if cur and prev:
        _, r, u = camera(view)
        allv = np.vstack([it[0] for it in items])
        nv = np.vstack([m["v"] + shift for m in cur])
        pa = np.stack([allv @ r, allv @ u], 1)
        pn = np.stack([nv @ r, nv @ u], 1)
        span_all = pa.max(0) - pa.min(0)
        c = (pn.max(0) + pn.min(0)) / 2
        span = np.maximum((pn.max(0) - pn.min(0)) * 1.6, span_all * focus)
        aspect = size[0] / size[1]
        span = np.array([max(span[0], span[1] * aspect), max(span[1], span[0] / aspect)])
        if span[0] < span_all[0] * 0.9 or span[1] < span_all[1] * 0.9:
            frame = (c[0] - span[0] / 2, c[0] + span[0] / 2, c[1] - span[1] / 2, c[1] + span[1] / 2)
    img, _ = render(items, view, size, frame=frame, ss=2, bg=paper(), margin=0.05)
    return save_png(img, out)


def full_render(meshes: list[dict], out: Path, size=(1300, 1000), view=(22, -58)) -> Path:
    def sty(m):
        k = m.get("kind")
        return STYLE["printed"] if k == "printed" else STYLE["dark"] if k == "motor" else STYLE["hardware"]
    img, _ = render([(m["v"], m["t"], sty(m)) for m in meshes], view, size, ss=2, bg=paper(), margin=0.04)
    return save_png(img, out)


# ------------------------------------------------------------------ charts
def _axes_style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=2.5, labelsize=6)
    ax.set_facecolor("none")


def catch_map(throws: list[dict], reach_m: float, shoulder_z: float, out: Path, size_mm=(180, 112)) -> Path:
    """Top (x-y) and side (x-z) view of where each throw was caught or failed, with the reach circle
    (top: about the base axis; side: about the shoulder)."""
    plt = _plt()
    fig, axs = plt.subplots(1, 2, figsize=(size_mm[0] / 25.4, size_mm[1] / 25.4), sharex=True)
    fig.patch.set_alpha(0)
    marks = {"caught": (GOOD, "o", "CAUGHT"), "out_of_reach": (DANGER, "x", "OUT OF REACH"),
             "too_slow": (DANGER, "s", "TOO SLOW"), "bounced_out": (DANGER, "^", "BOUNCED OUT"),
             "skipped_steps": (DANGER, "D", "SKIPPED STEPS"), "missed": (DANGER, "v", "MISSED")}
    for ax, (i, j, name) in zip(axs, ((0, 1, "TOP  X-Y"), (0, 2, "SIDE  X-Z"))):
        _axes_style(ax)
        th = np.linspace(0, 2 * np.pi, 200)
        cz = 0.0 if j == 1 else shoulder_z
        ax.plot(reach_m * np.cos(th), cz + reach_m * np.sin(th), color="#1C1C1C", lw=0.5, ls=(0, (4, 4)))
        ax.text(reach_m * 0.71, cz + reach_m * 0.71, f" REACH {reach_m:.3f} m", fontsize=5.5, color="#6B6B6B")
        ax.plot([0], [cz], marker="+", color="#1C1C1C", ms=6, mew=0.6)
        for oc, (col, mk, lab) in marks.items():
            pts = [tr for tr in throws if tr.get("outcome") == oc and (j == 1 or tr.get("catch_p"))]
            if not pts:
                continue
            xy = np.array([(tr.get("catch_p") or [tr["land_xy"][0], tr["land_xy"][1], 0.0]) for tr in pts], float)
            kw = dict(facecolors="none", edgecolors=col) if mk in "os^Dv" else dict(c=col)
            ax.scatter(xy[:, i], xy[:, j], s=9 if oc == "caught" else 14, marker=mk, linewidths=0.6,
                       label=f"{lab} ({len(pts)})", **kw)
        ax.set_aspect("equal", adjustable="datalim")
        ax.set_xlabel("X  M (TOWARD THROWER)", fontsize=6)
        ax.set_ylabel("Y  M" if j == 1 else "Z  M", fontsize=6)
        ax.set_title(name, fontsize=6.5, loc="left")
    axs[0].legend(fontsize=5.5, frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(out, transparent=True)
    plt.close(fig)
    return Path(out)


def hbars(rows: list[tuple[str, float]], out: Path, ref: float | None = None, ref_label: str = "",
          fmt="{:.2f}", size_mm=(120, 55), color="#1C1C1C") -> Path:
    plt = _plt()
    fig, ax = plt.subplots(figsize=(size_mm[0] / 25.4, size_mm[1] / 25.4))
    fig.patch.set_alpha(0)
    _axes_style(ax)
    names = [r[0].upper() for r in rows][::-1]
    vals = [r[1] for r in rows][::-1]
    cols = [color if ref is None or v >= ref else DANGER for v in vals]
    ax.barh(names, vals, height=0.45, color="none", edgecolor=cols, linewidth=0.7, hatch="////")
    for k, v in enumerate(vals):
        ax.text(v, k, " " + fmt.format(v), va="center", fontsize=6)
    if ref is not None:
        ax.axvline(ref, color=ACCENT_HEX, lw=0.7, ls=(0, (4, 4)))
        ax.text(ref, len(vals) - 0.4, " " + ref_label, color=ACCENT_HEX, fontsize=5.5, va="bottom")
    ax.set_xlim(0, max(vals + [ref or 0]) * 1.25 + 1e-9)
    fig.tight_layout()
    fig.savefig(out, transparent=True)
    plt.close(fig)
    return Path(out)


ACCENT_HEX = "#20A4F3"
