"""Technical-illustration renderer for the documents: orthographic or perspective z-buffer with flat
light surfaces and ink outlines (part boundaries, depth steps and creases), per ui-style.md.

Meshes are (v (K,3), t (M,3), style) with style = {"fill": rgb, "ink": rgb}. Units are whatever the
caller uses (mm for STLs, m for posed assemblies); an orthographic `frame` maps those units onto the
image exactly, which the part drawings rely on for true-scale views.
"""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

PAPER = (0.961, 0.961, 0.953)        # ui-style surface #F5F5F3
PAPERS = {"sheet": ((0.961, 0.961, 0.953), "#F5F5F3"),    # drawing-sheet look (screen)
          "white": ((1.0, 1.0, 1.0), "#FFFFFF")}          # `mechy doc build --print`
_paper = [PAPER]


def set_paper(name: str) -> str:
    """Pick the background for renders and the PDF pages; returns the hex colour for the templates."""
    if name not in PAPERS:
        raise ValueError(f"paper must be one of {sorted(PAPERS)}")
    _paper[0] = PAPERS[name][0]
    return PAPERS[name][1]


def paper() -> tuple:
    return _paper[0]
INK = (0.110, 0.110, 0.110)          # #1C1C1C
INK_MUTED = (0.42, 0.42, 0.42)       # #6B6B6B
ACCENT = (0.125, 0.643, 0.953)       # #20A4F3

STYLE = {
    "printed": {"fill": (0.90, 0.90, 0.88), "ink": INK},
    "hardware": {"fill": (0.74, 0.75, 0.77), "ink": INK},
    "dark": {"fill": (0.36, 0.36, 0.38), "ink": INK},
    "context": {"fill": (0.94, 0.94, 0.925), "ink": (0.62, 0.62, 0.62)},
    "new": {"fill": (0.66, 0.85, 0.98), "ink": (0.02, 0.27, 0.45)},
}

# camera: (direction target -> eye, right, up). Third-angle views of a part in its print orientation.
NAMED = {
    "front": ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    "top": ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    "right": ((1, 0, 0), (0, 1, 0), (0, 0, 1)),
}


def read_stl(path: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Binary or ASCII STL -> (vertices (3M,3), triangles (M,3))."""
    data = Path(path).read_bytes()
    if len(data) >= 84:
        n = struct.unpack_from("<I", data, 80)[0]
        if 84 + 50 * n == len(data):
            rec = np.frombuffer(data, dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]),
                                count=n, offset=84)
            v = rec["v"].reshape(-1, 3).astype(float)
            return v, np.arange(len(v)).reshape(-1, 3)
    txt = data.decode("ascii", "replace")
    pts = [list(map(float, ln.split()[1:4])) for ln in txt.splitlines() if ln.strip().startswith("vertex")]
    v = np.asarray(pts, float).reshape(-1, 3)
    return v, np.arange(len(v)).reshape(-1, 3)


def camera(view) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """view: a NAMED key, "iso" (30 deg up, from the front-left), or (elevation_deg, azimuth_deg)."""
    if isinstance(view, str) and view in NAMED:
        d, r, u = (np.asarray(x, float) for x in NAMED[view])
        return d, r, u
    el, az = (30.0, -60.0) if view == "iso" else view
    el, az = np.radians(el), np.radians(az)
    d = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])
    r = np.cross([0.0, 0.0, 1.0], d)
    r = r / np.linalg.norm(r) if np.linalg.norm(r) > 1e-9 else np.array([1.0, 0, 0])
    return d, r, np.cross(d, r)


def render(meshes, view="iso", size=(800, 600), frame=None, ortho=True, ss=3, bg=None,
           crease_deg=32.0, margin=0.04):
    """Rasterise meshes. frame = (u0, u1, v0, v1) in mesh units along the camera's right/up axes
    (orthographic only); without it the view is fitted with `margin`. Returns (H, W, 3) floats and
    the frame used. bg defaults to the current paper (set_paper)."""
    if bg is None:
        bg = paper()
    d, right, up = camera(view)
    allv = np.vstack([m[0] for m in meshes])
    lo, hi = allv.min(0), allv.max(0)
    centre = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo) / 2) or 1.0
    eye = centre + d * radius * (50.0 if ortho else 4.5)
    W, H = int(size[0]) * ss, int(size[1]) * ss

    def proj(v):
        rel = v - eye
        zc = -(rel @ d)
        if ortho:
            return np.stack([rel @ right, rel @ up], axis=1), zc
        return np.stack([(rel @ right) / zc, (rel @ up) / zc], axis=1), zc

    if frame is None:
        p_all, _ = proj(allv)
        plo, phi = p_all.min(0), p_all.max(0)
        span = phi - plo
        sc = min(W / (span[0] * (1 + 2 * margin) + 1e-12), H / (span[1] * (1 + 2 * margin) + 1e-12))
        pc = (plo + phi) / 2
        u0, u1 = pc[0] - W / sc / 2, pc[0] + W / sc / 2
        v0, v1 = pc[1] - H / sc / 2, pc[1] + H / sc / 2
    else:
        # frame is given in world coordinates along right/up; shift into eye-relative coordinates
        cu, cv = float(eye @ right), float(eye @ up)
        u0, u1, v0, v1 = frame[0] - cu, frame[1] - cu, frame[2] - cv, frame[3] - cv
    sx_k, sy_k = W / (u1 - u0), H / (v1 - v0)

    key = -0.35 * right + 0.55 * up + 0.75 * d
    key /= np.linalg.norm(key)
    inks, XS, YS, ZS, COLS, NS, PIDS = [], [], [], [], [], [], []
    for pid, (v, t, style) in enumerate(meshes):
        inks.append(np.asarray(style.get("ink", INK), float))
        if len(t) == 0:
            continue
        p2, zc = proj(v)
        sx = (p2[:, 0] - u0) * sx_k
        sy = (v1 - p2[:, 1]) * sy_k
        tri = v[t]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-15
        to_eye = d[None, :] if ortho else (eye - tri.mean(1))
        n *= np.sign(np.sum(n * to_eye, axis=1, keepdims=True) + 1e-15)
        shade = 0.80 + 0.20 * np.clip(n @ key, 0, 1)
        COLS.append(np.clip(np.asarray(style.get("fill", (0.9, 0.9, 0.9)), float)[None, :] * shade[:, None], 0, 1))
        XS.append(sx[t]), YS.append(sy[t]), ZS.append(zc[t]), NS.append(n)
        PIDS.append(np.full(len(t), pid, np.int32))
    X, Y, Z = (np.vstack(a) for a in (XS, YS, ZS))
    tid, zbuf = _scanline(X, Y, Z, W, H)
    hit = tid >= 0
    cols, nrm, pids = np.vstack(COLS), np.vstack(NS), np.concatenate(PIDS)
    img = np.empty((H, W, 3))
    img[:] = bg
    img[hit] = cols[tid[hit]]
    ids = np.where(hit, pids[np.maximum(tid, 0)], -1)
    nbuf = np.where(hit[..., None], nrm.astype(np.float32)[np.maximum(tid, 0)], np.float32(0))
    # ink: part boundaries, depth steps and creases (both sides of each discontinuity)
    edge = np.zeros((H, W), bool)
    zf = np.where(np.isfinite(zbuf), zbuf, 1e12)
    thr = radius * 0.015
    cos_c = np.cos(np.radians(crease_deg))
    for dy, dx in ((0, 1), (1, 0)):
        a = (slice(0, H - dy), slice(0, W - dx))
        b = (slice(dy, H), slice(dx, W))
        both = (ids[a] >= 0) & (ids[b] >= 0)
        e = (ids[a] != ids[b]) | (np.abs(zf[a] - zf[b]) > thr) | (both & (np.sum(nbuf[a] * nbuf[b], axis=-1) < cos_c))
        edge[a] |= e
        edge[b] |= e
    ink_tab = np.vstack(inks + [np.asarray(INK, float)])
    img[edge] = ink_tab[ids[edge]]
    if ss > 1:
        img = img.reshape(H // ss, ss, W // ss, ss, 3).mean((1, 3))
    cu, cv = float(eye @ right), float(eye @ up)
    return img, (u0 + cu, u1 + cu, v0 + cv, v1 + cv)


def _scanline(X, Y, Z, W, H, budget: int = 3_000_000) -> tuple[np.ndarray, np.ndarray]:
    """Z-buffer by scanline spans, vectorised over triangles. Returns the (H, W) index of the nearest
    triangle per pixel (-1 = empty) and the depth buffer. Pixel centres are at +0.5."""
    tid = np.full((H, W), -1, np.int64)
    zbuf = np.full((H, W), np.inf)
    area = (X[:, 1] - X[:, 0]) * (Y[:, 2] - Y[:, 0]) - (X[:, 2] - X[:, 0]) * (Y[:, 1] - Y[:, 0])
    ry0 = np.clip(np.ceil(Y.min(1) - 0.5), 0, H).astype(np.int64)
    ry1 = np.clip(np.floor(Y.max(1) - 0.5), -1, H - 1).astype(np.int64)
    rows = np.where(np.abs(area) > 1e-12, np.maximum(ry1 - ry0 + 1, 0), 0)
    cost = rows * (np.ceil(X.max(1) - X.min(1)) + 2)
    sel = np.nonzero(rows > 0)[0]
    csum = np.cumsum(cost[sel])
    start = 0
    while start < len(sel):
        stop = max(start + 1, int(np.searchsorted(csum, (csum[start - 1] if start else 0) + budget)))
        ks = sel[start:stop]
        start = stop
        ti = np.repeat(ks, rows[ks])
        first = np.repeat(np.cumsum(rows[ks]) - rows[ks], rows[ks])
        yrow = ry0[ti] + (np.arange(len(ti)) - first)
        yc = yrow + 0.5
        xmin = np.full(len(ti), np.inf)
        xmax = np.full(len(ti), -np.inf)
        for i, j in ((0, 1), (1, 2), (2, 0)):
            ya, yb, xa, xb = Y[ti, i], Y[ti, j], X[ti, i], X[ti, j]
            dy = yb - ya
            with np.errstate(divide="ignore", invalid="ignore"):
                tt = (yc - ya) / dy
            ok = (dy != 0) & (tt >= 0) & (tt <= 1)
            xx = xa + np.where(ok, tt, 0) * (xb - xa)
            xmin = np.where(ok, np.minimum(xmin, xx), xmin)
            xmax = np.where(ok, np.maximum(xmax, xx), xmax)
        good = np.isfinite(xmin)
        rx0 = np.clip(np.ceil(np.where(good, xmin, 0) - 0.5), 0, W).astype(np.int64)
        rx1 = np.clip(np.floor(np.where(good, xmax, -1) - 0.5), -1, W - 1).astype(np.int64)
        cnt = np.where(good, np.maximum(rx1 - rx0 + 1, 0), 0)
        if cnt.sum() == 0:
            continue
        pt = np.repeat(ti, cnt)
        py = np.repeat(yrow, cnt)
        px = np.repeat(rx0, cnt) + (np.arange(cnt.sum()) - np.repeat(np.cumsum(cnt) - cnt, cnt))
        pz = _bary_z(X, Y, Z, pt, px + 0.5, py + 0.5)
        keep = pz < zbuf[py, px]
        py, px, pz, pt = py[keep], px[keep], pz[keep], pt[keep]
        order = np.argsort(-pz, kind="stable")                    # the nearest is written last
        py, px, pz, pt = py[order], px[order], pz[order], pt[order]
        zbuf[py, px] = pz
        tid[py, px] = pt
    return tid, zbuf


def _bary_z(X, Y, Z, k, cx, cy):
    xa, ya = X[k], Y[k]
    ar = (xa[:, 1] - xa[:, 0]) * (ya[:, 2] - ya[:, 0]) - (xa[:, 2] - xa[:, 0]) * (ya[:, 1] - ya[:, 0])
    w0 = ((xa[:, 1] - cx) * (ya[:, 2] - cy) - (xa[:, 2] - cx) * (ya[:, 1] - cy)) / ar
    w1 = ((xa[:, 2] - cx) * (ya[:, 0] - cy) - (xa[:, 0] - cx) * (ya[:, 2] - cy)) / ar
    return w0 * Z[k, 0] + w1 * Z[k, 1] + (1 - w0 - w1) * Z[k, 2]


def save_png(img: np.ndarray, path: str | Path) -> Path:
    from PIL import Image
    path = Path(path)
    Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(path, optimize=True)
    return path
