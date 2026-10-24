"""Preview renders. MuJoCo offscreen when a headless GL works, else matplotlib."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _split_long(v: np.ndarray, t: np.ndarray, max_edge: float, rounds: int = 6):
    """Split triangles whose longest edge exceeds max_edge (helps matplotlib's painter's sort)."""
    v = list(map(tuple, v))
    t = [tuple(x) for x in t]
    for _ in range(rounds):
        out, changed = [], False
        for a, b, c in t:
            pa, pb, pc = np.array(v[a]), np.array(v[b]), np.array(v[c])
            e = [np.linalg.norm(pb - pa), np.linalg.norm(pc - pb), np.linalg.norm(pa - pc)]
            k = int(np.argmax(e))
            if e[k] <= max_edge:
                out.append((a, b, c))
                continue
            changed = True
            i, j, o = [(a, b, c), (b, c, a), (c, a, b)][k]
            v.append(tuple((np.array(v[i]) + np.array(v[j])) / 2))
            m = len(v) - 1
            out += [(i, m, o), (m, j, o)]
        t = out
        if not changed:
            break
    return np.array(v), np.array(t)


def tessellate_parts(parts, tol_mm: float = 0.8, max_edge_mm: float | None = None, angular: float = 0.5):
    out = []
    for p in parts:
        verts, tris = p.tessellate(tol_mm, angular)
        if not tris:
            continue
        v = np.array([[x.X, x.Y, x.Z] for x in verts]) / 1000.0
        t = np.array(tris)
        if max_edge_mm:
            v, t = _split_long(v, t, max_edge_mm / 1000.0)
        c = p.color
        rgba = tuple(c) if c is not None else (0.8, 0.8, 0.8, 1.0)
        out.append((v, t, rgba))
    return out


_VIEWS = {"hero": (16, -62), "iso": (22, -55), "front": (5, -90), "side": (5, 0), "top": (88, -90)}


def _camera(view: str, lo, hi):
    el, az = (np.radians(a) for a in _VIEWS.get(view, _VIEWS["iso"]))
    d = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])   # target -> eye
    right = np.cross([0.0, 0.0, 1.0], d)
    if np.linalg.norm(right) < 1e-6:
        right = np.array([1.0, 0.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(d, right)
    centre = (lo + hi) / 2
    radius = np.linalg.norm(hi - lo) / 2
    eye = centre + d * radius * 4.5          # mild perspective
    return eye, d, right, up, centre, radius


def rasterize(meshes, view: str = "iso", size_px: int = 640, ss: int = 2, bg=(1.0, 1.0, 1.0)):
    """Software z-buffer render (flat shading, part outlines). Returns an (H, W, 3) float image."""
    allv = np.vstack([m[0] for m in meshes])
    lo, hi = allv.min(0), allv.max(0)
    eye, d, right, up, centre, radius = _camera(view, lo, hi)
    N = size_px * ss
    key = np.array([-0.35, 0.45, 0.82])
    key = key[0] * right + key[1] * up + key[2] * d
    key /= np.linalg.norm(key)
    fill = d.copy()
    # project everything once to size the frame
    def proj(v):
        rel = v - eye
        zc = -(rel @ d)
        return np.stack([(rel @ right) / zc, (rel @ up) / zc], axis=1), zc
    p_all, _ = proj(allv)
    plo, phi = p_all.min(0), p_all.max(0)
    span = (phi - plo).max() * 1.08
    pc = (plo + phi) / 2
    scale = N / span
    img = np.empty((N, N, 3))
    img[:] = bg
    zbuf = np.full((N, N), np.inf)
    ids = np.full((N, N), -1, np.int32)
    for pid, (v, t, rgba) in enumerate(meshes):
        p2, zc = proj(v)
        sx = (p2[:, 0] - pc[0]) * scale + N / 2
        sy = N / 2 - (p2[:, 1] - pc[1]) * scale
        tri = v[t]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-15
        to_eye = eye - tri.mean(1)
        n *= np.sign(np.sum(n * to_eye, axis=1, keepdims=True) + 1e-15)    # two-sided
        lam = np.clip(n @ key, 0, 1)
        shade = 0.30 + 0.55 * lam + 0.15 * np.clip(n @ fill, 0, 1)
        h = (key + to_eye / (np.linalg.norm(to_eye, axis=1, keepdims=True) + 1e-15))
        h /= np.linalg.norm(h, axis=1, keepdims=True)
        spec = 0.25 * np.clip(np.sum(n * h, axis=1), 0, 1) ** 24
        base = np.asarray(rgba[:3], float)
        cols = np.clip(base[None, :] * shade[:, None] + spec[:, None], 0, 1)
        X, Y, Z = sx[t], sy[t], zc[t]
        x0 = np.clip(np.floor(X.min(1)).astype(int), 0, N - 1)
        x1 = np.clip(np.ceil(X.max(1)).astype(int), 0, N - 1)
        y0 = np.clip(np.floor(Y.min(1)).astype(int), 0, N - 1)
        y1 = np.clip(np.ceil(Y.max(1)).astype(int), 0, N - 1)
        area = (X[:, 1] - X[:, 0]) * (Y[:, 2] - Y[:, 0]) - (X[:, 2] - X[:, 0]) * (Y[:, 1] - Y[:, 0])
        for k in np.nonzero(np.abs(area) > 1e-9)[0]:
            gx, gy = np.meshgrid(np.arange(x0[k], x1[k] + 1) + 0.5, np.arange(y0[k], y1[k] + 1) + 0.5)
            xa, ya = X[k], Y[k]
            w0 = ((xa[1] - gx) * (ya[2] - gy) - (xa[2] - gx) * (ya[1] - gy)) / area[k]
            w1 = ((xa[2] - gx) * (ya[0] - gy) - (xa[0] - gx) * (ya[2] - gy)) / area[k]
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not inside.any():
                continue
            z = w0 * Z[k, 0] + w1 * Z[k, 1] + w2 * Z[k, 2]
            sl = (slice(y0[k], y1[k] + 1), slice(x0[k], x1[k] + 1))
            zb = zbuf[sl]
            m = inside & (z < zb)
            if m.any():
                zb[m] = z[m]
                img[sl][m] = cols[k]
                ids[sl][m] = pid
    # outlines: part boundaries and depth steps
    edge = np.zeros((N, N), bool)
    zf = np.where(np.isfinite(zbuf), zbuf, 1e9)
    thr = radius * 0.02
    for dy, dx in ((0, 1), (1, 0)):
        a_id, b_id = ids[: N - dy, : N - dx], ids[dy:, dx:]
        a_z, b_z = zf[: N - dy, : N - dx], zf[dy:, dx:]
        e = (a_id != b_id) | (np.abs(a_z - b_z) > thr)
        edge[: N - dy, : N - dx] |= e
    img[edge] = img[edge] * 0.45
    if ss > 1:
        img = img.reshape(size_px, ss, size_px, ss, 3).mean((1, 3))
    return img


def render_parts_png(meshes, path: str | Path, view: str = "iso", size_px: int = 640,
                     title: str | None = None) -> Path:
    """Render tessellated parts with a z-buffer and save via matplotlib."""
    plt = _mpl()
    img = rasterize(meshes, view, size_px)
    fig = plt.figure(figsize=(size_px / 100, size_px / 100), dpi=100)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.imshow(img, interpolation="lanczos")
    ax.set_axis_off()
    if title:
        ax.text(0.03, 0.97, title, transform=ax.transAxes, fontsize=10, va="top", color="#333")
    path = Path(path)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def mujoco_gl_available() -> str | None:
    """Return a working MUJOCO_GL backend name, or None. Probed in a subprocess."""
    import subprocess
    import sys
    for gl in ("egl", "osmesa", "glfw"):
        code = ("import mujoco;m=mujoco.MjModel.from_xml_string('<mujoco><worldbody><geom size=\"0.1\"/>"
                "</worldbody></mujoco>');r=mujoco.Renderer(m,32,32);d=mujoco.MjData(m);"
                "r.update_scene(d);r.render()")
        try:
            r = subprocess.run([sys.executable, "-c", code], env={**os.environ, "MUJOCO_GL": gl},
                               capture_output=True, timeout=30)
        except Exception:
            continue
        if r.returncode == 0:
            return gl
    return None
