"""`style: ref_arm`: the arm is the 20sffactory Community Robot Arm (CC BY 4.0, original design
Florin Tobler), assembled from the tessellated vendor STEP solids in
mechy/data/reference_designs/cad/20sffactory/ (assembly.json from make_assembly_json.py, plus the
printable STLs). Part classification, the colour palette and the 120 -> 140 mm link stretch are
ported from BAM/Models/bam-arm/assembly/build_assembly.py.

Kinematics (params `kinematics: parallel_level`, Dobot-style): the lower motor drives the lower
shank about S (q1), the upper motor drives the lever+pleuel loop, i.e. the upper shank's absolute
pitch a2 = q1+q2, and the two "bend" links + triplate keep the manipulator level: q1+q2+q3 = 0.
Motor-side coordinates a = C q with the passthrough matrix (a3 = q123 is constant, the wrist is
unpowered). Vendor motor map on the CNC shield: X = upper (a2), Y = lower (a1), Z = yaw (q0),
A/E0 = spare (vendor rail).

This module is mesh-only (no build123d): the STEP/STL solids can't produce a STEP, so `cad build`
writes arm.stl from the posed meshes and skips arm.step. All geometry mm unless noted; world frame:
yaw axis through (0,0), z = 0 at the socket bottom, +x = the arm's reach direction.
"""

from __future__ import annotations

import base64
import csv
import json
import math
import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "reference_designs" / "cad" / "20sffactory"

# ----------------------------------------------------------- vendor geometry (STEP frame, mm, z up)
# Pivot points measured from the cylindrical faces of robot_arm.step (BAM step_parts.json).
S_ST = (100.0, 62.5)          # shoulder: lower shank + lever + both 90T gears on the main body
E_ST = (11.685, 143.744)      # elbow: lower shank + upper shank + triplate
W_ST = (119.541, 196.348)     # wrist: upper shank -> manipulator
L_ST = (64.048, 44.965)       # lever end -> pleuel
PU_ST = (-24.381, 126.084)    # pleuel -> upper shank
B0_ST = (70.0, 74.5)          # main body -> lower levelling link
TL_ST = (-18.315, 155.744)    # lower levelling link -> triplate
T2_ST = (26.685, 163.744)     # triplate -> upper levelling link
T3_ST = (134.53, 216.371)     # upper levelling link -> manipulator
YAW_ST = (99.989, -49.005)    # yaw axis (x, y), vertical
SOCKET_BOTTOM_ST = -27.2      # underside of the socket: what the arm stands on without the rail

GROW = 20.0                   # 120 -> 140 mm link stretch along each shank's rest direction

def _sub(a, b): return (a[0] - b[0], a[1] - b[1])
def _add(a, b): return (a[0] + b[0], a[1] + b[1])
def _mul(a, k): return (a[0] * k, a[1] * k)
def _len(a): return math.hypot(*a)
def _unit(a): l = _len(a); return (a[0] / l, a[1] / l)

U1 = _unit(_sub(E_ST, S_ST))
U2 = _unit(_sub(W_ST, E_ST))
TH1_REST = math.atan2(U1[1], U1[0])              # lower shank rest pitch (2.398 rad)
TH2_REST = math.atan2(U2[1], U2[0])              # upper shank rest pitch, absolute (0.454 rad)
REST_Q = np.array([0.0, TH1_REST, TH2_REST - TH1_REST, -TH2_REST])   # q0, q1, q2, q3 (level: q3 = -a2)

_D1, _D2 = _mul(U1, GROW), _mul(U2, GROW)

def _w(p):    # STEP (x, z) -> world (x, z): yaw axis x -> 0, socket bottom z -> 0
    return (p[0] - YAW_ST[0], p[1] - SOCKET_BOTTOM_ST)

# rest-pose pivots (x, z), world frame, after the 140 mm stretch (BAM's rigid shifts)
PIVOTS = {
    "S": _w(S_ST), "L": _w(L_ST), "B0": _w(B0_ST),
    "E": _w(_add(E_ST, _D1)), "TL": _w(_add(TL_ST, _D1)), "T2": _w(_add(T2_ST, _D1)),
    "PU": _w(_add(PU_ST, _D1)), "W": _w(_add(W_ST, _add(_D1, _D2))), "T3": _w(_add(T3_ST, _add(_D1, _D2))),
}
LEVER_LEN = _len(_sub(L_ST, S_ST))              # 40 mm
EPA_LEN = _len(_sub(PU_ST, E_ST))               # pleuel attachment radius on the upper shank ~40 mm
TRIP_OFF = _sub(T2_ST, E_ST)                    # (15, 20): rigid, E->T2 = W->T3
TL_OFF = _sub(TL_ST, E_ST)                      # = B0 - S (lower bend link keeps it exact)
MANIP_OFF = _sub(T3_ST, W_ST)
END_EFFECTOR_OFFSET = 54.0                      # vendor config.h, mm from W to the tool midpoint

COL = {
    "base": (70, 84, 102), "body": (79, 209, 197), "lower": (246, 173, 85), "upper": (236, 201, 75),
    "link": (214, 140, 72), "tool": (190, 120, 220), "motor": (46, 48, 54), "metal": (180, 184, 190),
    "bam": (255, 214, 10), "cup": (41, 128, 185), "foam": (60, 66, 76), "belt": (28, 28, 30),
}
RGBA = {k: tuple(c / 255 for c in v) + (1.0,) for k, v in COL.items()}

PLA = 1.24e-6                    # kg/mm^3 solid
INFILL, SHELL_MM = 0.25, 0.8
CATALOG_MASS = {"motor": 0.28, "servo": 0.0134, "51105": 0.022, "f624": 0.0034, "f686": 0.0055,
                "pulley20": 0.008, "screw": 0.0015, "endstop_sw": 0.003}

# printed parts (published name, qty, file in DATA/stl, group, print orientation note)
PRINT_PARTS = [
    ("arm_socket", 1, "robot_belt_arm socket_v2.stl", "base", "open side up"),
    ("arm_rotategear", 1, "robot_belt_arm rotategear.stl", "turntable", "gear face down"),
    ("arm_main_body", 1, "robot_belt_arm main_body_v2.stl", "turntable", "flat on the bed"),
    ("arm_gear_body", 2, "robot_belt_arm gear_body.stl", "arm", "flat on the bed"),
    ("arm_endstop_bracket", 1, "robot_belt_arm endstop.stl", "turntable", "flat on the bed"),
    ("arm_stabilizer", 1, "robot_belt_arm stabilizer.stl", "turntable", "flat on the bed"),
    ("arm_lever", 1, "robot_belt_arm lever.stl", "arm", "flat on the bed"),
    ("arm_lower_shank_140", 1, "lower_shank_140.stl", "arm", "flat, 140 mm"),
    ("arm_upper_shank_140", 1, "upper_shank_140.stl", "arm", "flat, 140 mm"),
    ("arm_pleuel_140", 1, "pleuel_140.stl", "arm", "flat"),
    ("arm_pleuel_bend_lower_140", 1, "pleuel_bend_140.stl", "arm", "flat"),
    ("arm_pleuel_bend_upper_140", 1, "pleuel_bend_upper_140.stl", "arm",
     "flat; BAM-made part (CC BY 4.0): the vendor 140 mm kit has no upper levelling link"),
    ("arm_triplate", 1, "robot_belt_arm triplate.stl", "arm", "flat"),
    ("arm_manipulator", 1, "robot_belt_arm manipulator.stl", "arm", "flat"),
    ("tool_shank_calibrator_140", 1, "shank_calibrator_140mm.stl", "tool", "flat; homing aid"),
]
GRIPPER_PARTS = [
    ("grip_base", 1, "servo_gripperBase.stl", "gripper", "for the MG90S / 9 g servo"),
    ("grip_finger", 2, "gripperFinger_by_ftobler.stl", "gripper", ""),
    ("grip_shaft", 1, "servo_gripper_shaft.stl", "gripper", ""),
    ("grip_screw_secure", 1, "gripper_screw_secure.stl", "gripper", ""),
]

# GLB node tree for the parallel linkage. Local rotation about `axis` =
# rest + sum(coeff * (q[j] - rest_q[j])). Parents: pitch axes are -y, yaw +z, world = m.
NODE_SPEC = {
    "base": {"parent": "arm", "pivot": None, "axis": (0, 0, 1), "static": True},
    "turntable": {"parent": "base", "pivot": (0.0, 0.0), "axis": (0, 0, 1), "joint": 0},
    "upper_arm": {"parent": "turntable", "pivot": "S", "axis": (0, -1, 0), "joint": 1},
    "lever": {"parent": "turntable", "pivot": "S", "axis": (0, -1, 0),
              "coupled": [(1, 1.0), (2, 1.0)]},                        # absolute pitch a2
    "pleuel": {"parent": "lever", "pivot": "L", "axis": (0, -1, 0),
               "coupled": [(2, -1.0)]},                               # stays parallel to the lower shank
    "bend_lower": {"parent": "turntable", "pivot": "B0", "axis": (0, -1, 0),
                   "coupled": [(1, 1.0)]},                            # absolute pitch q1
    "forearm": {"parent": "upper_arm", "pivot": "E", "axis": (0, -1, 0), "joint": 2},
    "triplate": {"parent": "upper_arm", "pivot": "E", "axis": (0, -1, 0),
                 "coupled": [(1, -1.0)]},                             # fixed orientation
    "bend_upper": {"parent": "triplate", "pivot": "T2", "axis": (0, -1, 0),
                   "coupled": [(1, 1.0), (2, 1.0)]},                  # absolute pitch a2
    "hand": {"parent": "forearm", "pivot": "W", "axis": (0, -1, 0), "joint": 3},
}
# node-local rotation angle at the rest pose (rad) — the GLB node's rest rotation
REST_NODE = {
    "turntable": 0.0, "upper_arm": TH1_REST, "lever": TH2_REST, "pleuel": TH1_REST - TH2_REST,
    "bend_lower": TH1_REST, "forearm": TH2_REST - TH1_REST, "triplate": -TH1_REST,
    "bend_upper": TH2_REST, "hand": -TH2_REST, "base": 0.0,
}
# absolute pitch of each node's frame at the rest pose (for un-rotating the meshes to local space)
ABS_REST = {"turntable": 0.0, "upper_arm": TH1_REST, "lever": TH2_REST, "pleuel": TH1_REST,
            "bend_lower": TH1_REST, "forearm": TH2_REST, "triplate": 0.0, "bend_upper": TH2_REST,
            "hand": 0.0, "base": 0.0}
# which lumped contract body each node's mass joins (matches ArmModel's parallel_level model and
# BAM sizing's lumping: pleuel/lower bend link ride with the lower shank, lever/upper bend link
# with the upper shank drive, triplate with the hand)
LUMP = {"base": "base", "turntable": "turntable", "upper_arm": "upper_arm", "pleuel": "upper_arm",
        "bend_lower": "upper_arm", "forearm": "forearm", "lever": "forearm", "bend_upper": "forearm",
        "triplate": "hand", "hand": "hand"}
# motion of each lumped body in motor coordinates (see ArmModel._parallel_*)
BODY_MOTION = {"upper_arm": ("pitch", 1), "forearm": ("pitch2", 2), "hand": ("level", None),
               "cup": ("level", None)}

KIND_FOR_CLASS = {"motor": "motor", "metal": "bearing"}
KIND_COLOR_KIND = {"printed": None, "motor": "motor", "bearing": "metal", "foam": "foam"}


def _ry(ang):
    """Rotation about -y by +ang (the arm's pitch sense: +x swings up to +z)."""
    c, s = math.cos(ang), math.sin(ang)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def riser_mesh(h: float, side: float = 110.0, wall: float = 2.4):
    """Hollow square column under the socket, spanning z in [-h, 0] in the arm frame: outer shell
    walls, a closed top plate the socket stands on, 4 internal ribs for stiffness."""
    v, t = [], []
    def box(cx, cy, cz, sx, sy, sz):
        i0 = len(v)
        x0, y0, z0 = cx - sx / 2, cy - sy / 2, cz - sz / 2
        v.extend([(x0, y0, z0), (x0 + sx, y0, z0), (x0 + sx, y0 + sy, z0), (x0, y0 + sy, z0),
                  (x0, y0, z0 + sz), (x0 + sx, y0, z0 + sz), (x0 + sx, y0 + sy, z0 + sz),
                  (x0, y0 + sy, z0 + sz)])
        t.extend([(i0 + a, i0 + b, i0 + c) for a, b, c in
                  [(0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4),
                   (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)]])
    o = side / 2
    for sx, sy, cx, cy in ((side, wall, 0.0, -o + wall / 2), (side, wall, 0.0, o - wall / 2),
                           (wall, side - 2 * wall, -o + wall / 2, 0.0), (wall, side - 2 * wall, o - wall / 2, 0.0)):
        box(cx, cy, -h / 2, sx, sy, h)
    box(0.0, 0.0, -1.0, side, side, 2.0)                       # top plate the socket bolts to
    for cx, cy in ((-o + wall + 4, 0), (o - wall - 4, 0), (0, -o + wall + 4), (0, o - wall - 4)):
        box(cx, cy, -h / 2, wall if cx else 8.0, 8.0 if cx else wall, h)   # inner ribs
    return np.array(v), np.array(t, np.uint32)


def _yaw(ang):
    c, s = math.cos(ang), math.sin(ang)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def load_solids() -> list[dict]:
    """The vendor STEP tessellation: solids in the STEP frame (mm)."""
    d = json.loads((DATA_DIR / "assembly.json").read_text())
    out = []
    for p in d["solids"]:
        lo = np.asarray(p["min"], float)
        v = np.frombuffer(base64.b64decode(p["v"]), np.uint16).reshape(-1, 3) * 0.02 + lo
        t = np.frombuffer(base64.b64decode(p["t"]), np.uint32).reshape(-1, 3)
        out.append({"name": p["name"], "vol": p["vol"], "center": p["center"], "v": v, "t": t,
                    "cyl": p.get("cyl", [])})
    return out


def _classify(p: dict):
    """(node group, colour key, label) per solid — BAM's classifier on the STEP frame."""
    n, c, vol = p["name"] or "", p["center"], p["vol"]
    x, y, z = c
    d = lambda q: math.hypot(x - q[0], z - q[1])
    if any(k in n for k in ("leg.stl", "basering", "case_", "rail_", "dual_manipulator")):
        return None
    if "socket" in n:
        return "base", "base", "socket"
    if vol > 60:
        return ("base" if z < 0 else "turntable"), "motor", "NEMA 17" + (" (yaw)" if z < 0 else "")
    if 2 < vol < 2.3:
        return ("base" if z < 0 else "turntable"), "metal", "GT2 20T pulley"
    if 0.4 < vol < 0.45:
        return "base", "metal", "yaw endstop"
    for k, g, ckey, label in (
            ("rotategear", "turntable", "body", "yaw 90T gear"), ("main_body", "turntable", "body", "main body"),
            ("endstop.stl", "turntable", "body", "endstop bracket"),
            ("stabilizer", "turntable", "body", "stabilizer"),
            ("lower_shank", "upper_arm", "lower", "lower shank 140"),
            ("upper_shank", "forearm", "upper", "upper shank 140"),
            ("pleuel_bend_lower", "bend_lower", "link", "lower levelling link 140"),
            ("pleuel_bend_upper", "bend_upper", "bam", "upper levelling link 140 (BAM-made)"),
            ("pleuel", "pleuel", "link", "pleuel 140"), ("triplate", "triplate", "link", "triplate"),
            ("lever", "lever", "body", "lever"), ("manipulator", "hand", "tool", "manipulator")):
        if k in n:
            return g, ckey, label
    if "gear_body" in n:
        return ("upper_arm" if y < -49 else "lever"), "body", "90T gear (" + ("lower" if y < -49 else "upper") + ")"
    if x > 110 and z > 180:
        return "hand", ("motor" if vol > 10 else "tool"), \
            "gripper" + (" motor (28BYJ; ref_arm uses a servo)" if vol > 10 else "")
    if vol < 0.1:
        return ("upper_arm" if y < -49 else "lever"), "metal", "screw"
    if d(L_ST) < 3:
        return "lever", "metal", "bearing F624ZZ"
    if d(E_ST) < 3 or d(TL_ST) < 3:
        return "triplate", "metal", "bearing F686ZZ"
    if d(W_ST) < 3 or d(T3_ST) < 3:
        return "hand", "metal", "bearing F686ZZ"
    if d(S_ST) < 3 or d(B0_ST) < 3:
        return "turntable", "metal", "bearing F624ZZ"
    if vol < 0.5:
        return "turntable", "metal", "washer"
    return None


def _stretch(v: np.ndarray, p0, u):
    """Cut where the link is a plain bar and move the far side GROW mm along u (BAM's method)."""
    proj = (v[:, 0] - p0[0]) * u[0] + (v[:, 2] - p0[1]) * u[1]
    best = None
    for s in np.arange(35.0, 85.0, 0.5):
        near = int((np.abs(proj - s) < 4).sum())
        if best is None or near < best[0] or (near == best[0] and abs(s - 60) < abs(best[1] - 60)):
            best = (near, s)
    _, cut = best
    out = v.copy()
    m = proj > cut
    out[m, 0] += u[0] * GROW
    out[m, 2] += u[1] * GROW
    return out


# mesh mass properties (divergence-theorem sums; mm -> mm^3/mm^4/mm^5)
def mesh_metrics(v: np.ndarray, t: np.ndarray):
    """(volume mm^3, com mm, inertia mm^5 about com, area mm^2): divergence-theorem sums over the
    tetrahedra (origin, a, b, c); winding must be outward, else |volume| still holds and the com
    falls back to the vertex mean for open/degenerate meshes."""
    a, b, c = v[t[:, 0]].astype(float), v[t[:, 1]].astype(float), v[t[:, 2]].astype(float)
    det = np.einsum("ij,ij->i", a, np.cross(b, c))      # 6 * signed volume of tet (0, a, b, c)
    vsum = float(det.sum())
    vol = abs(vsum) / 6.0
    area = float(np.linalg.norm(np.cross(b - a, c - a), axis=1).sum() / 2)
    if vol < area * 0.05 or vol <= 0 or not np.isfinite(vol):   # open shell -> 2 mm shell estimate
        span = float(np.ptp(v, axis=0).mean())
        return max(area * 2.0, 1.0), v.mean(0), np.eye(3) * (area * 2.0) * (span ** 2 / 12), area
    det = det if vsum > 0 else -det
    com = np.einsum("ij,i->j", (a + b + c) / 4.0, det) / vsum
    # Second moment M_ij = ∫ x_i x_j dV of tet(0,a,b,c): |det|/120 * (a.a' + b.b' + c.c' +
    # (a+b+c).(a+b+c)') terms (n-simplex formula, n=3). Sign follows det; sums stay consistent.
    M = np.zeros((3, 3))
    S = a + b + c
    for i in range(3):
        for j in range(i, 3):
            M[i, j] = M[j, i] = np.einsum(
                "i,i", det, a[:, i] * a[:, j] + b[:, i] * b[:, j] + c[:, i] * c[:, j]
                + S[:, i] * S[:, j]) / 120.0
    I = np.trace(M) * np.eye(3) - M
    I -= abs(vsum) / 6.0 * ((com @ com) * np.eye(3) - np.outer(com, com))   # -> about com
    return vol, com, I, area


def print_mass_g(vol_mm3: float, area_mm2: float) -> float:
    shell = min(1.0, area_mm2 * SHELL_MM / max(vol_mm3, 1e-9))
    return (shell + INFILL * (1 - shell)) * vol_mm3 * PLA * 1e3


# ------------------------------------------------------------------ cup toolhead
def cup_mesh(d_in: float, depth: float, wall: float = 1.6, flange_r: float = 16.0,
             flange_t: float = 3.0, foam: float = 4.0, n: int = 48, n_ribs: int = 10):
    """Printable catching cup opening along +z, origin at the cup's mid-depth (the cup centre used
    by fk/IK). Thin 1.6 mm wall opened by windows (ribs only) — light enough for the small arm's
    wrist. Returns {name: (v, t, rgba, kind)}; flange mounts to the manipulator's bolt holes."""
    ro, ri = d_in / 2 + wall, d_in / 2
    z0, zf, z1 = -depth / 2 - wall, -depth / 2, depth / 2   # bottom outside, floor inside, rim
    v = []

    def ring(r_, z):
        i0 = len(v)
        for k in range(n):
            a = 2 * math.pi * k / n
            v.append((r_ * math.cos(a), r_ * math.sin(a), z))
        return i0

    o0, ol = ring(ro, z0), ring(ro, z0 + 5.0)        # bottom outside edge + 5 mm lip
    i0 = ring(ri, zf)                                # inner floor edge
    rim_o0, rim_o1 = ring(ro, z1 - 3.0), ring(ro, z1)   # rim band (3 mm deep)
    rim_i0, rim_i1 = ring(ri, z1 - 3.0), ring(ri, z1)
    c0, cf = len(v), len(v) + 1
    v += [(0.0, 0.0, z0), (0.0, 0.0, zf)]
    t = []
    for k in range(n):
        k1 = (k + 1) % n
        t += [(o0 + k, ol + k, ol + k1), (o0 + k, ol + k1, o0 + k1)]            # outer lip
        t += [(rim_o0 + k, rim_o1 + k, rim_o1 + k1), (rim_o0 + k, rim_o1 + k1, rim_o0 + k1)]  # rim outer
        t += [(rim_o1 + k, rim_i1 + k, rim_i1 + k1), (rim_o1 + k, rim_i1 + k1, rim_o1 + k1)]  # rim top
        t += [(rim_i0 + k, rim_i0 + k1, rim_i1 + k1), (rim_i0 + k, rim_i1 + k1, rim_i1 + k)]  # rim inner
        t += [(rim_o0 + k, rim_i0 + k, rim_i0 + k1), (rim_o0 + k, rim_i0 + k1, rim_o0 + k1)]  # rim bottom
        t += [(o0 + k, i0 + k, i0 + k1), (o0 + k, i0 + k1, o0 + k1)]              # floor annulus
        t += [(cf, i0 + k1, i0 + k)]                                            # inner floor disc
        t += [(c0, o0 + k, o0 + k1)]                                            # bottom disc
    # windowed wall: n_ribs ribs (closed wedges) between the lip top (z0+5) and the rim (z1-3)
    rib_half = math.pi / n_ribs * 0.45              # ~45% of each cell is a rib -> ~55% open
    zr0, zr1 = z0 + 5.0, z1 - 3.0
    for k in range(n_ribs):
        a = 2 * math.pi * k / n_ribs
        r0i = len(v)
        for r_ in (ri, ro):
            for aa in (a - rib_half, a + rib_half):
                v.append((r_ * math.cos(aa), r_ * math.sin(aa), zr0))
                v.append((r_ * math.cos(aa), r_ * math.sin(aa), zr1))
        r0o = r0i + 4
        t += [(r0i, r0i + 1, r0i + 3), (r0i, r0i + 3, r0i + 2),          # inner face (outward -r)
              (r0o, r0o + 2, r0o + 1), (r0o + 1, r0o + 2, r0o + 3),      # outer face (+r)
              (r0i, r0o, r0o + 1), (r0i, r0o + 1, r0i + 1),              # leading edge
              (r0i + 2, r0i + 3, r0o + 3), (r0i + 2, r0o + 3, r0o + 2),  # trailing edge
              (r0i + 1, r0o + 1, r0o + 3), (r0i + 1, r0o + 3, r0i + 3),  # top
              (r0i, r0i + 2, r0o), (r0o, r0i + 2, r0o + 2)]              # bottom
    shell = (np.array(v), np.array(t, np.uint32), RGBA["cup"], "printed")

    fv, ft = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        fv += [(flange_r * math.cos(a), flange_r * math.sin(a), z0 - flange_t),
               (ro * math.cos(a), ro * math.sin(a), z0)]
    for k in range(n):
        a_, b_ = 2 * k, 2 * ((k + 1) % n)
        ft += [(a_, b_, a_ + 1), (b_, b_ + 1, a_ + 1)]
    flange = (np.array(fv), np.array(ft, np.uint32), RGBA["cup"], "printed")

    lv, lt = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        lv += [(ri * math.cos(a), ri * math.sin(a), z0 + wall), (ri * math.cos(a), ri * math.sin(a), z1),
               ((ri - foam) * math.cos(a), (ri - foam) * math.sin(a), z0 + wall),
               ((ri - foam) * math.cos(a), (ri - foam) * math.sin(a), z1)]
    for k in range(n):
        a_, b_ = 4 * k, 4 * ((k + 1) % n)
        lt += [(a_, b_, a_ + 2), (b_, b_ + 2, a_ + 2), (a_ + 1, a_ + 3, b_ + 1), (b_ + 1, a_ + 3, b_ + 3),
               (a_, a_ + 1, b_), (b_, a_ + 1, b_ + 1), (a_ + 2, a_ + 3, b_ + 2), (b_ + 2, a_ + 3, b_ + 3)]
    liner = (np.array(lv), np.array(lt, np.uint32), RGBA["foam"], "foam")
    return {"cup_shell": shell, "cup_flange": flange, "cup_liner": liner}


# ------------------------------------------------------------------ design
@dataclass
class RefPart:
    name: str
    ref: str                  # stl name for printed parts, else a BOM/spec key
    kind: str                 # printed | motor | bearing | fastener | belt | pulley | foam | sensor
    node: str                 # GLB node it moves with
    v: np.ndarray             # node-local vertices (mm, node's q=0 frame)
    t: np.ndarray
    color: tuple
    label: str
    step: str = "arm"         # assembly step id (docgen)
    bom_item: str | None = None
    mass_kg: float | None = None
    printed_ref: str | None = None     # entry in PRINT_PARTS / generated print files
    bores: list = field(default_factory=list)   # node-local pivot-bore centres (mm) for tests


@dataclass
class RefDesign:
    params: dict
    parts: list = field(default_factory=list)
    origins: dict = field(default_factory=dict)     # node origins (mm, world) at q = 0
    info: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    material: str = "PLA"
    infill: float = INFILL
    shell_mm: float = SHELL_MM
    style_key: str = "ref_arm"
    tool_xz: tuple = (END_EFFECTOR_OFFSET, 0.0)     # cup centre rel W, (radial, up) mm
    belts: list = field(default_factory=list)

    # ---------------------------------------------------------- masses
    def part_mass(self, p: RefPart) -> float:
        if p.mass_kg is not None:
            return p.mass_kg
        vol, _, _, area = mesh_metrics(p.v, p.t)
        if p.kind == "printed":
            return print_mass_g(vol, area) / 1000
        if p.kind == "foam":
            return vol * 0.10e-6
        return vol * 7.85e-6                        # steel hardware (estimate)

    def node_origin(self, node: str) -> np.ndarray:
        return np.asarray(self.origins[node], float)

    def com_q0(self, p: RefPart, com_local: np.ndarray) -> np.ndarray:
        """Node-local com -> world com at q = 0 (node-local axes are world-aligned at q=0)."""
        return self.node_origin(p.node) + com_local

    def mass_props(self) -> dict:
        """Per contract body (base, turntable, upper_arm, forearm, hand, cup): mass, com (m, from the
        body origin at q = 0), inertia about the com (kg m^2, world axes at q=0). Passive links are
        lumped into the nearest driven body (see LUMP) — the same approximation MJCF uses."""
        acc = {"base": [], "turntable": [], "upper_arm": [], "forearm": [], "hand": [], "cup": []}
        for p in self.parts:
            b = "cup" if p.ref.startswith("cup_") or (p.node == "hand" and p.step == "toolhead") else LUMP.get(p.node)
            if b in acc:
                acc[b].append(p)
        out = {}
        for b, items in acc.items():
            if not items:
                continue
            o0 = np.asarray(self.origins[b], float)
            mt, cs, Icom = 0.0, np.zeros(3), np.zeros((3, 3))
            mets = []
            for p in items:
                vol, com_l, I_, area = mesh_metrics(p.v, p.t)
                m = self.part_mass(p)
                cw = self.com_q0(p, com_l)
                mets.append((m, cw, I_ * (m / vol)))
                mt += m
                cs += m * cw
            com = cs / mt
            for m, cw, Ii in mets:
                d = cw - com
                Icom += Ii + m * (d @ d * np.eye(3) - np.outer(d, d))
            out[b] = {"mass": round(mt, 6), "com": ((com - o0) / 1000).round(6).tolist(),
                      "inertia": (Icom / 1e6).round(9).tolist(), "parts": len(items)}
        return {"units": "kg, m, kg m^2; body axes = world axes at q = 0", "bodies": out,
                "origins_m": {b: (np.asarray(v, float) / 1000).round(6).tolist()
                              for b, v in self.origins.items()
                              if b in ("base", "turntable", "upper_arm", "forearm", "hand", "cup")},
                "kinematics": "parallel_level",
                "tool_offset_m": {"radial": self.tool_xz[0] / 1000, "z": self.tool_xz[1] / 1000},
                "homing": self.info.get("homing", []),
                "homing_order": self.info.get("homing_order"),
                "motor_map_note": "a = (q0, q1, q1+q2, q123=const); 4.5:1 on the three driven joints",
                "params_hash": params_hash(self.params)}

    # ---------------------------------------------------------- posing
    def node_angle(self, node: str, q) -> float:
        """Absolute pitch of the node's frame at q (world, level = 0)."""
        q = np.asarray(q, float)
        a2 = q[1] + q[2]
        return {"turntable": 0.0, "upper_arm": q[1], "lever": a2, "pleuel": q[1],
                "bend_lower": q[1], "forearm": a2, "triplate": 0.0, "bend_upper": a2,
                "hand": self_level(q), "base": 0.0}[node]

    def node_origin_at(self, node: str, q) -> np.ndarray:
        """World position (mm) of the node's pivot at joint angles q."""
        q = np.asarray(q, float)
        cy, sy = math.cos(q[0]), math.sin(q[0])
        a2 = q[1] + q[2]
        S = self.origins["S_xz"] if False else None
        Sx, Sz = PIVOTS["S"]
        def plane(x, z):
            return np.array([x * cy, x * sy, z])
        S = np.array([Sx * cy, Sx * sy, Sz])
        E = S + self.L1 * np.array([math.cos(q[1]) * cy, math.cos(q[1]) * sy, math.sin(q[1])])
        W = E + self.L2 * np.array([math.cos(a2) * cy, math.cos(a2) * sy, math.sin(a2)])
        T3 = W + np.array([MANIP_OFF[0] * cy, MANIP_OFF[0] * sy, MANIP_OFF[1]])
        tool = W + np.array([self.tool_xz[0] * cy, self.tool_xz[0] * sy, self.tool_xz[1]])
        org = {"base": np.zeros(3), "turntable": np.zeros(3), "upper_arm": S, "lever": S,
               "bend_lower": plane(*PIVOTS["B0"]), "pleuel": S - LEVER_LEN * np.array(
                   [math.cos(a2) * cy, math.cos(a2) * sy, math.sin(a2)]),
               "forearm": E, "triplate": E, "hand": W, "cup": tool,
               "bend_upper": E + np.array([TRIP_OFF[0] * cy, TRIP_OFF[0] * sy, TRIP_OFF[1]])}
        return org[node]

    def posed_meshes(self, q) -> list:
        """(v world m, t, rgba, name) of every part at joint angles q (for render/thumb/GLB check)."""
        out = []
        for p in self.parts:
            org = self.node_origin_at(p.node, q)
            # node-local verts are level (see build_design); _ry(a) maps angle b to b - a, so
            # posing at the node's absolute pitch needs _ry(-pitch).
            ang = self.node_angle(p.node, q)
            R = _yaw(q[0]) @ _ry(-ang)
            v = (p.v @ R.T + org) / 1000.0
            out.append((v, p.t, p.color, p.name))
        return out

    def rest_q(self):
        return REST_Q

    # ---------------------------------------------------------- outputs
    def print_part_list(self):
        """(name, qty, stl file in DATA/stl or None for generated, group, note)."""
        out = list(PRINT_PARTS)
        if self.info.get("toolhead") == "gripper":
            out += GRIPPER_PARTS
        else:
            out.append(("cup", 1, None, "toolhead", "opening up; parametric cup (mechy)"))
        if self.info.get("mount_mm"):
            out.append(("arm_riser", 1, None, "base",
                        f"riser column, {self.info['mount_mm']:.0f} mm, open side down"))
        return out

    def print_rows(self) -> list[dict]:
        rows = []
        for name, qty, src, group, note in self.print_part_list():
            if src:
                vol, _, _, area = mesh_metrics(*read_stl(DATA_DIR / "stl" / src))
            else:
                ps = [p for p in self.parts if p.printed_ref == name]
                vol = sum(mesh_metrics(p.v, p.t)[0] for p in ps)
                area = sum(mesh_metrics(p.v, p.t)[3] for p in ps)
            g = print_mass_g(vol, area)
            rows.append({"part": name, "qty": qty, "material": self.material,
                         "orientation": note or "flat", "est_grams": round(g, 1),
                         "est_grams_total": round(g * qty, 1), "infill": f"{INFILL:.0%}",
                         "volume_cm3": round(vol / 1000, 1), "stl": f"stl/{name}.stl",
                         "source": "BAM (CC BY 4.0)" if "bend_upper" in name
                                   else ("mechy (parametric)" if src is None
                                         else "20sffactory Community Robot Arm (CC BY 4.0)")})
        return rows

    def write_print_list(self, path: Path) -> list[dict]:
        rows = self.print_rows()
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        return rows

    def export_stls(self, out_dir: Path) -> list:
        """stl/: the vendor print files (renamed to the published names) plus the generated cup."""
        import shutil
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("*.stl"):
            old.unlink()
        files = []
        for name, qty, src, group, note in self.print_part_list():
            dst = out_dir / f"{name}.stl"
            if src:
                shutil.copyfile(DATA_DIR / "stl" / src, dst)
            else:
                ps = [p for p in self.parts if p.printed_ref == name]
                v = np.vstack([p.v for p in ps])
                t = np.vstack([p.t + off for p, off in zip(ps, np.cumsum([0] + [len(p.v) for p in ps])[:-1])])
                write_stl(dst, v - v.min(0), t.astype(np.uint32))
            files.append(dst)
        return files

    BOM = [  # (item, qty, spec, used_for, est_unit_usd) — user's actual hardware + BAM's bom minus the rail
        ("Arduino Uno R3", 1, "ATmega328P, USB-B (user's)", "controller", 12.0),
        ("CNC Shield V3", 1, "Protoneer-style, 4 driver sockets X/Y/Z/A (user's)", "controller", 5.0),
        ("A4988 stepper driver", 3, "with heatsink; Vref for ~0.8 A (user's)",
         "X=upper, Y=lower, Z=yaw motors (vendor pinout_uno.h)", 2.0),
        ("A4988 stepper driver (spare)", 1, "A socket", "open decision: vendor rail module or wrist servo", 2.0),
        ("NEMA 17 stepper 42SHDC3026-15B", 3, "bipolar 4-wire, 0.9 A/phase, ~0.30 N·m holding (ASSUMED)",
         "base yaw, lower arm, upper arm", 12.0),
        ("NEMA 17 stepper 42SHDC3026-15B (spare)", 1, "4th motor owned", "open decision: rail or wrist servo", 12.0),
        ("Power supply 24 V 6 A", 1, "user's; A4988 VMOT <= 35 V so 24 V is fine", "motor power", 18.0),
        ("Electrolytic capacitor 100 uF 50 V", 1, "across the shield's motor power input (user's)", "", 0.3),
        ("GT2 pulley 20T", 3, "6 mm belt, 5 mm bore", "one per driven motor", 1.5),
        ("GT2 closed belt 200 mm", 3, "6 mm wide closed loop", "arm joints (vendor)", 2.0),
        ("51105 thrust bearing", 1, "25x42x11", "base socket", 3.0),
        ("F624ZZ flanged bearing", 6, "4x13x5", "lever, main body pivots", 0.4),
        ("F686ZZ flanged bearing", 12, "6x13x5", "shank, triplate, manipulator pivots", 0.4),
        ("Endstop microswitch", 3, "NO to GND", "X/Y/Z homing (vendor)", 0.5),
        ("Servo MG90S (gripper toolhead)", 1, "9 g metal gear; only with toolhead: gripper", "gripper", 3.0),
        ("M2x10 screw + nut", 6, "", "endstops", 0.1),
        ("M3x6 screw", 36, "", "arm fasteners", 0.1),
        ("M3 nut", 8, "", "", 0.05),
        ("M4x10 screw", 6, "", "arm", 0.1),
        ("M4x16 screw", 8, "", "arm", 0.1),
        ("M4x20 screw", 6, "", "arm", 0.1),
        ("M4 nut", 14, "", "arm", 0.05),
        ("M6x20 screw", 1, "", "arm", 0.2),
        ("M6x40 screw", 2, "", "arm", 0.2),
        ("M6x50 screw", 1, "", "arm", 0.2),
        ("M6 nut", 4, "", "arm", 0.05),
        ("Stepper cable", 3, "4-wire, 1 m", "motor wiring", 1.5),
        ("Silicone wire 18 AWG", 2, "red/black, 1 m", "supply to shield", 1.0),
    ]

    def bom_rows(self) -> list[dict]:
        rows = []
        for item, qty, spec, used, cost in self.BOM:
            if "gripper" in item.lower() and self.info.get("toolhead") != "gripper":
                continue
            rows.append({"item": item, "qty": qty, "spec": spec, "used_for": used,
                         "source": "user's stock / BAM bom", "est_unit_usd": cost})
        return rows

    def write_bom(self, path: Path) -> list[dict]:
        rows = self.bom_rows()
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        return rows


def self_level(q):
    return 0.0


def mesh_metrics_parts(p):
    _, _, _, area = mesh_metrics(p.v, p.t)
    return mesh_metrics(p.v, p.t)[0], area


def stl_volume(path: Path):
    v, t = read_stl(path)
    return mesh_metrics(v, t)[0], mesh_metrics(v, t)[3]


def read_stl(path: Path):
    b = path.read_bytes()
    n = struct.unpack("<I", b[80:84])[0]
    v = np.zeros((n * 3, 3))
    for i in range(n):
        f = struct.unpack("<12f", b[84 + 50 * i:84 + 50 * i + 48])
        v[3 * i:3 * i + 3] = np.array(f[3:12]).reshape(3, 3)
    _, idx = np.unique(v.round(4), axis=0, return_inverse=True)
    vu = np.unique(v.round(4), axis=0)
    return vu, idx.reshape(n, 3)


def write_stl(path: Path, v: np.ndarray, t: np.ndarray) -> Path:
    """Binary STL (mm) from vertices/faces."""
    tris = v[t.astype(np.int64)]
    n = len(tris)
    norm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    ln = np.linalg.norm(norm, axis=1, keepdims=True)
    norm = np.where(ln > 0, norm / np.maximum(ln, 1e-30), 0.0)
    with open(path, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", n))
        for i in range(n):
            f.write(struct.pack("<12fH", *norm[i], *tris[i].reshape(-1), 0))
    return path


def params_hash(params: dict) -> str:
    from .belt_arm import params_hash as ph
    return ph(params)


def build_design(arm) -> RefDesign:
    """Assemble the vendor solids into nodes/parts at the rest pose (meshes in node-local mm)."""
    P = arm.params.get("ref_arm") or {}
    shank = float(P.get("shank_mm", 140.0))
    toolhead = str(P.get("toolhead", "cup"))
    D = RefDesign(params=arm.params, material=str(P.get("material", "PLA")))
    if abs(shank - 140.0) > 1e-6:
        D.warnings.append(f"ref_arm is built from the vendor 140 mm kit; shank_mm {shank} ignored")
    D.info["toolhead"] = toolhead
    D.L1 = D.L2 = shank
    L1, L2 = shank, shank

    # link-frame helpers on (x, z)
    def dvec(a):
        return (math.cos(a), math.sin(a))

    # node origins at q = 0 (world mm); all pitch links horizontal along +x
    Sx, Sz = PIVOTS["S"]
    origins = {"base": (0.0, 0.0, 0.0), "turntable": (0.0, 0.0, 0.0),
               "upper_arm": (Sx, 0.0, Sz), "lever": (Sx, 0.0, Sz),
               "pleuel": (Sx - LEVER_LEN, 0.0, Sz),
               "forearm": (Sx + L1, 0.0, Sz),
               "triplate": (Sx + L1, 0.0, Sz),
               "bend_upper": (Sx + L1 + TRIP_OFF[0], 0.0, Sz + TRIP_OFF[1]),
               "hand": (Sx + L1 + L2, 0.0, Sz),
               "cup": (0.0, 0.0, 0.0)}
    # B0 is fixed to the main body: B0 = S + (B0_ST - S_ST)
    b0 = _add(PIVOTS["S"], (B0_ST[0] - S_ST[0], B0_ST[1] - S_ST[1]))
    origins["bend_lower"] = (b0[0], 0.0, b0[1])

    # ---- classify and stretch the vendor solids, then move each into its node's local frame
    stretch_axis = {"upper_arm": (S_ST, U1), "pleuel": (L_ST, U1), "bend_lower": (B0_ST, U1),
                    "forearm": (E_ST, U2), "bend_upper": (T2_ST, U2)}
    shift = {"triplate": _D1, "forearm": _D1, "bend_upper": _D1, "hand": _add(_D1, _D2)}
    for i, p in enumerate(load_solids()):
        cls = _classify(p)
        if not cls:
            continue
        g, ckey, label = cls
        v = np.asarray(p["v"], float)
        t = np.asarray(p["t"], np.uint32)
        if g in stretch_axis:
            v = _stretch(v, *stretch_axis[g])
        if g in shift:
            v = v + np.array([shift[g][0], 0.0, shift[g][1]])
        # STEP world -> mechy world (mm)
        vw = v - np.array([YAW_ST[0], YAW_ST[1], SOCKET_BOTTOM_ST])
        # rest-pose world -> node local: undo the node's rest absolute pitch about its pivot.
        # _ry(a) maps a world direction at angle b to angle b - a, so _ry(rest) levels the mesh.
        spec = NODE_SPEC[g]
        piv = PIVOTS.get(spec["pivot"], (0.0, 0.0)) if spec["pivot"] else (0.0, 0.0)
        piv3 = np.array([piv[0], 0.0, piv[1]])
        vl = (_ry(ABS_REST[g]) @ (vw - piv3).T).T
        # pivot-bore centres in node-local mm (same pipeline as the verts): cyls are {r, c, a} in
        # the STEP frame; keep the y-axis bores used by the pivots (3..15 mm radius)
        bores = []
        for cyl in p.get("cyl", []):
            ax = cyl.get("a") or [0, 0, 1]
            if abs(ax[1]) < 0.9 or not (3.0 <= cyl["r"] <= 15.0):
                continue
            cc = np.array(cyl["c"], float).reshape(1, 3)
            if g in stretch_axis:
                cc = _stretch(cc, *stretch_axis[g])
            if g in shift:
                cc = cc + np.array([shift[g][0], 0.0, shift[g][1]])
            cw = cc[0] - np.array([YAW_ST[0], YAW_ST[1], SOCKET_BOTTOM_ST])
            bores.append(list((_ry(ABS_REST[g]) @ (cw - piv3)).round(4)))
        kind = "motor" if ckey == "motor" else ("printed" if ckey in COL and "stl" in str(p["name"]).lower()
                                                or ckey in ("base", "body", "lower", "upper", "link",
                                                            "tool", "bam") else "bearing")
        mass_kg = None
        if "28BYJ" in label:
            mass_kg, kind = 0.030, "motor"              # 28BYJ-48 gripper motor (vendor BOM), ~30 g
        elif "NEMA 17" in label:
            mass_kg, kind = CATALOG_MASS["motor"], "motor"
        elif "pulley" in label:
            mass_kg, kind = CATALOG_MASS["pulley20"], "pulley"
        elif "bearing" in label:
            mass_kg, kind = (CATALOG_MASS["f624"] if "F624" in label else CATALOG_MASS["f686"]), "bearing"
        elif "screw" in label or "washer" in label:
            mass_kg, kind = CATALOG_MASS["screw"], "fastener"
        elif "endstop" in label:
            mass_kg, kind = CATALOG_MASS["endstop_sw"], "sensor"
        step = {"base": "base", "turntable": "turntable", "hand": "toolhead"}.get(g, "arm")
        D.parts.append(RefPart(name=label.replace(" ", "_") + ("" if label == p.get("name") else ""),
                               ref=(p["name"] or label), kind=kind, node=g, v=vl, t=t,
                               color=RGBA[ckey], label=label, step=step, mass_kg=mass_kg,
                               bores=bores,
                               bom_item=label if kind in ("motor", "bearing", "pulley", "sensor")
                               else None))
    # unique part names
    seen = {}
    for p in D.parts:
        p.name = p.name if p.name not in seen else p.name + "_2"
        seen[p.name] = True

    # ---- toolhead
    W0 = np.array(origins["hand"])
    manip_top = None
    for p in D.parts:
        if p.label == "manipulator":
            manip_top = p.v[:, 2].max()          # node-local; hand frame = world axes at level
    if toolhead == "cup":
        c = arm.params.get("catcher") or {}
        d_in = float(c.get("diameter_m", 0.095)) * 1000
        depth = float(c.get("depth_m", 0.07)) * 1000
        plate_top = (manip_top if manip_top is not None else 20.0)
        cup_z = plate_top + 2.4 + depth / 2                     # cup centre height above W level
        parts = cup_mesh(d_in, depth)
        for name, (v, t, rgba, kind) in parts.items():
            # flange/liner are thin open surfaces: their mesh_metrics volume is unreliable, so give
            # real masses (estimate): flange ~12 g printed, net pocket ~8 g of mesh fabric+rubber
            mk = {"cup_flange": 0.012, "cup_liner": 0.008}.get(name)
            D.parts.append(RefPart(name=name, ref=name, kind="printed" if kind == "printed" else "foam",
                                   node="hand", v=v + np.array([END_EFFECTOR_OFFSET, 0.0, cup_z]), t=t,
                                   color=rgba, label=name, step="toolhead", mass_kg=mk,
                                   printed_ref="cup" if name == "cup_shell" else None))
        D.tool_xz = (END_EFFECTOR_OFFSET, cup_z)
        D.info["cup"] = {"inner_d_mm": d_in, "depth_mm": depth}
    else:
        D.tool_xz = (END_EFFECTOR_OFFSET, 20.0)                # gripper midpoint (vendor offset)
        # The gripper solids are already in the STEP set. Name them as the servo gripper BAM
        # prints (BOM: MG90S, 13.4 g) and move them into the contract's tool body (step "toolhead").
        for p in D.parts:
            if not p.label.startswith("gripper"):
                continue
            if "gripperBase" in p.ref:
                p.kind, p.mass_kg, p.label = "printed", None, "gripper base"
            elif p.kind == "motor":
                p.mass_kg, p.label, p.color = CATALOG_MASS["servo"], "servo MG90S", RGBA["motor"]
            else:
                p.label = "gripper finger" if "Finger" in p.ref else "gripper part"
            p.step = "toolhead"
    D.origins = origins
    D.origins["cup"] = (origins["hand"][0] + D.tool_xz[0], 0.0, origins["hand"][2] + D.tool_xz[1])
    D.info["pivots_mm"] = {k: [round(a, 3), round(b, 3)] for k, (a, b) in PIVOTS.items()}
    D.info["rest_q_deg"] = [round(float(x), 3) for x in np.degrees(REST_Q)]
    D.info["shoulder_x_mm"] = Sx
    D.info["base_height_mm"] = Sz
    D.info["homing"] = [
        {"joint": "base", "sensor": "endstop microswitch (vendor, on the socket)",
         "mount": "socket", "trigger": "rotategear tab",
         "homes": "q0 at the Z endstop; calibrate with Z_HOME_STEPS", "home_deg": 0.0,
         "coordinate": "q0"},
        {"joint": "shoulder", "sensor": "endstop microswitch (vendor)",
         "mount": "main body", "trigger": "lower shank",
         "homes": "a1 = q1 at the Y endstop; recalibrate with tool_shank_calibrator_140",
         "home_deg": round(math.degrees(TH1_REST), 1), "coordinate": "a1 = q1"},
        {"joint": "elbow", "sensor": "endstop microswitch (vendor)",
         "mount": "main body", "trigger": "lever",
         "homes": "a2 = q1+q2 at the X endstop; recalibrate with the calibrator",
         "home_deg": round(math.degrees(TH2_REST), 1), "coordinate": "a2 = q1+q2"},
        {"joint": "wrist", "sensor": "none (passive joint: the linkage holds q3 = -(q1+q2))",
         "mount": "-", "trigger": "-",
         "homes": "not homed (no motor)", "home_deg": 0.0, "coordinate": "q3"},
    ]
    D.info["homing_order"] = ["shoulder", "elbow", "base", "wrist"]
    D.belts = [{"joint": "base", "teeth": [20, 90], "centre_mm": 0.0, "computed_mm": 200.0, "standard_mm": 200.0, "note": "vendor GT2 200 mm closed loop"},
               {"joint": "shoulder", "teeth": [20, 90], "centre_mm": 0.0, "computed_mm": 200.0, "standard_mm": 200.0, "note": "vendor"},
               {"joint": "elbow", "teeth": [20, 90], "centre_mm": 0.0, "computed_mm": 200.0, "standard_mm": 200.0, "note": "vendor"}]

    # ---- riser (ref_arm.mount_mm): a printed column under the socket raises the arm
    mount_mm = float(P.get("mount_mm", 0.0))
    if mount_mm > 0:
        v, t = riser_mesh(mount_mm)
        D.parts.append(RefPart(name="arm_riser", ref="arm_riser", kind="printed", node="base",
                               v=v, t=t, color=RGBA["base"], label="arm_riser", step="base",
                               printed_ref="arm_riser"))
        D.info["mount_mm"] = mount_mm
        D.info.setdefault("bom_extra", []).append(
            {"item": f"Riser column under the socket, {mount_mm:.0f} mm (printed, or a plywood/2020 "
                     "box of the same height)", "qty": 1, "usd": 0.0, "step": "base"})

    # ---- printed-part refs for print_list
    name_to_pub = {src: pub for pub, _, src, _, _ in PRINT_PARTS + GRIPPER_PARTS}
    for p in D.parts:
        if p.ref in name_to_pub:
            p.printed_ref = name_to_pub[p.ref]
        elif p.ref and "pleuel_bend_upper" in p.ref:
            p.printed_ref = "arm_pleuel_bend_upper_140"
    return D


# ------------------------------------------------------------------ GLB (contracts 11, extended)
def glb_spec(D: RefDesign):
    """(parts, tree) for glb.write_glb: each part's mesh in its node's local frame (m), and the
    node tree with coupled passive links. Node rotations = rest local angle about `axis`."""
    from .glb import quat_axis_angle
    rest_q = np.asarray(D.rest_q(), float)
    # node origins at q = 0 (m). For children: translation in the parent's frame.
    # parent abs pitch at q=0: turntable 0(yaw only), upper_arm 0, lever 0, triplate 0 — all level,
    # so every translation is the plain world difference of the q=0 origins.
    org = {k: np.asarray(v, float) / 1000.0 for k, v in D.origins.items()}
    parent_frame = {"base": None, "turntable": "base"}
    tree = []
    for name, spec in NODE_SPEC.items():
        par = spec["parent"]
        o = np.asarray(D.origins.get(name, D.origins.get(par, (0, 0, 0))), float) / 1000.0
        po = np.asarray(D.origins.get(par, (0, 0, 0)), float) / 1000.0
        ex = {"axis": list(spec["axis"])}
        if spec.get("static"):
            ex = None
        elif "joint" in spec:
            ex["joint"] = ["base", "shoulder", "elbow", "wrist"][spec["joint"]]
            ex["joint_index"] = spec["joint"]
        else:
            ex["coupled"] = [[j, c] for j, c in spec["coupled"]]
            ex["rest"] = REST_NODE[name]
            ex["note"] = "angle = rest + sum(coeff * (q[j] - rest_q[j]))"
        tree.append({"name": name, "parent": par,
                     "translation": [float(x) for x in (o - po)],
                     "rotation": quat_axis_angle(list(spec["axis"]), REST_NODE[name]),
                     "extras": ex})
    # cup centre marker (catch point), child of hand at the tool point
    o = np.asarray(D.origins["cup"], float) / 1000.0
    tree.append({"name": "cup_center", "parent": "hand",
                 "translation": [float(x) for x in (o - org["hand"])], "rotation": None,
                 "extras": {"note": "catch point"}})
    parts = [{"name": p.name, "node": p.node, "v": p.v / 1000.0, "t": p.t, "rgba": p.color}
             for p in D.parts]
    return parts, tree


def posed_world_meshes(D: RefDesign, q):
    """(v, t, rgba) world-frame (m) at pose q, for thumb.png and arm.stl."""
    return [(v, t, rgba) for (v, t, rgba, _name) in D.posed_meshes(q)]
