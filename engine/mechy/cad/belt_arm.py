"""`style: belt_arm` generator: a conventional, printable 4-DOF belt-driven arm.

Built on common open-source practice (20sffactory Community Robot Arm, Thor, BCN3D Moveo):
every motor sits low, joints are driven by GT2 20T motor pulleys into large printed GT2
pulleys on closed belts, joints turn on real bearings.

Layout at q = 0 (arm stretched along +X, shoulder axis at (0, 0, base_height)), mm, y across
the arm. Everything below is computed from params.yaml (`links`, `joints[].gear_ratio`,
`catcher`, optional `belt_arm:` block):

* Base (fixed): round base plate, printed base shell whose top deck carries the base NEMA 17
  (shaft up) and a 51105 thrust bearing (25x42x11). The motor's 20T pulley drives a printed
  GT2 pulley ring (round(20*ratio) teeth) under the turntable on a closed belt; the motor
  centre distance is solved so the belt is a stock closed-loop length (slotted mount).
* Turntable (yaw): printed disc + pulley ring on the thrust bearing, centred by a 608-2RS on an
  8 mm shaft. It carries two tower plates and a central motor spine.
  - shoulder motor: on the -y tower plate, body outboard, belt plane y = -39;
  - elbow motor: on the spine's -y face, belt plane y = +14;
  - wrist motor: on the spine's +y face, belt plane y = -14.
  Each drives a printed pulley on the dead 8 mm shoulder shaft.
* Drive to elbow and wrist = belt pass-through (chosen over a parallelogram because the wrist
  is actuated and the 1:1 stages need no extra links): the elbow and wrist stage-1 pulleys are
  compound pulleys turning freely on the shoulder shaft; their 40T halves drive 1:1 closed
  belts along the upper arm (planes +23 / -23) to the forearm pulley and to a 40T+40T idler on
  the elbow shaft, which drives a 1:1 belt along the forearm (plane -14) to the hand pulley.
  Consequence: the elbow motor sets the forearm's absolute pitch (q1+q2) and the wrist motor
  the hand's absolute pitch (q1+q2+q3). The hand stays level when the wrist motor holds,
  exactly like the parallelogram of the 20sffactory arm. Firmware maps joint angles to motor
  angles with that coupling (see summary.md).
* Upper arm: twin printed side plates (+-28..32) joined by printed spacers, lightening holes,
  608-2RS at the shoulder, clamped 8 mm elbow shaft. Forearm: hollow printed box beam
  (20 x 30, wall >= 2.4) with lightening holes, 608-2RS pair at the elbow. Hand: printed fork
  on 608-2RS at the wrist, carrying the cup.
* Cup: printed shell + EVA foam liner (inner ring); the foam's inner surface is the
  catcher diameter/depth used by the sim.
* Sprung cup (`catcher.compliance: spring`): the cup rides back along the hand axis on two 4 mm
  hardened rods through LM4UU linear bearings pressed into lugs on the cup shell. The rods are
  cantilevered from bosses on the hand's slide plate; one stock compression spring (RS PRO 821-352)
  sits on each rod in a pocket of the boss and pushes the cup forward against a shaft collar
  (NBR O-ring cushion). A rubber bumper on the plate is the rear travel stop. The cup parts form
  their own body (`cup`, the MJCF slide joint `cup_slide`; GLB node `cup_slide`).

Every part has a body (base, turntable, upper_arm, forearm, hand, cup), a material and a mass
(volume x density x infill factor for printed parts, catalogue mass for purchased ones), so
mass properties for MuJoCo come from the actual solids.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from build123d import Box, Circle, Color, Compound, Cylinder, Location, Polygon, Pos, Rot, Shape, extrude

# ------------------------------------------------------------------ catalogue
NEMA_SIDE = 42.3          # 17HS4401 datasheet: 42.3 mm square, 40 mm body, 31 mm hole pattern
NEMA_LEN = 40.0
NEMA_HOLE = 31.0
NEMA_BOSS_D = 22.0
NEMA_SHAFT = (5.0, 24.0)
B608 = (22.0, 8.0, 7.0)   # OD, ID, width
B688 = (16.0, 8.0, 5.0)
B51105 = (42.0, 25.0, 11.0)
GT2_PITCH = 2.0
BELT_T = 1.4              # drawn belt thickness
# Stock GT2-6mm closed loops sold by the usual Amazon/AliExpress vendors (mm)
GT2_LOOPS = [110, 122, 140, 152, 158, 160, 180, 188, 200, 202, 210, 220, 232, 240, 250, 260, 270,
             280, 286, 300, 310, 320, 330, 350, 360, 376, 380, 400, 420, 440, 460, 480, 500, 520,
             550, 560, 580, 600, 610, 630, 640, 660, 700, 750, 760, 800, 852, 900, 1000]
DENSITY = {"PETG": 1.27e-6, "PLA": 1.24e-6, "steel": 7.85e-6, "aluminium": 2.70e-6,
           "rubber": 1.25e-6, "EVA foam": 0.10e-6}          # kg/mm^3
CATALOG_MASS = {"motor": 0.28, "608": 0.012, "688": 0.0035, "51105": 0.022, "gt2_20t": 0.008,
                "KW12-3": 0.0015, "A3144": 0.0003, "magnet_5x2": 0.0003,
                "LM4UU": 0.0025,          # estimate (steel sleeve 8x4x12 is 3.5 g solid; balls + cage less)
                "spring": 0.0007}         # computed: 0.5 mm wire, ~22 coils of 6.3 mm mean diameter
# Sprung-cup slide hardware (catcher.compliance: spring)
LM4UU = (8.0, 4.0, 12.0)          # OD, ID, length (mm), Misumi/THK LM4UU catalogue dimensions
ROD_D = 4.0                       # hardened chrome rod, h6
COLLAR_4 = (10.0, 5.0)            # 4 mm bore set-screw shaft collar, OD x width (mm), generic
ORING_4 = (4.0, 1.5)              # NBR O-ring ID x cross-section (mm)
BUMPER = (12.7, 3.5)              # self-adhesive rubber bumper foot, D x H (mm)
FELT = (5.0, 3.0)                 # wool felt brake pad D x H (mm), punched from 3 mm felt sheet
BRAKE_LEN = 6.0                   # brake block at the rear of each lug (felt pad + M3 set screw)
DEFAULT_SLIDE_FRICTION_N = 3.0    # total felt-brake drag (both rods) the sim found best; tune on the bench
# Stock compression springs that fit over a 4 mm rod. Datasheet values (RS Components product page):
# rate, free length, minimum working length and the load there.
SPRINGS = [
    {"id": "RS PRO 821-352", "ref": "spring_rs821352", "material": "stainless steel 302", "wire_mm": 0.5,
     "od_mm": 6.8, "free_mm": 65.0, "rate_n_per_mm": 0.11, "min_work_mm": 17.4, "load_at_min_n": 5.47,
     "source": "https://uk.rs-online.com/web/p/compression-springs/0821352"},
]

PRINTED, MOTOR, BEARING, SHAFT, BELT, PULLEY, FASTENER, FOAM, SENSOR, MAGNET, SPRING, RUBBER = (
    "printed", "motor", "bearing", "shaft", "belt", "pulley", "fastener", "foam", "sensor", "magnet", "spring",
    "rubber")
KW12_3 = (12.8, 6.5, 5.8)       # KW12-3 microswitch body L x H x W (mm), M2 holes 6.5 mm apart
A3144 = (4.0, 3.0, 1.5)         # A3144 unipolar hall sensor, TO-92S body (mm)
MAG = (5.0, 2.0)                # N52 disc magnet D x H (mm)
COLORS = {
    PRINTED: (0.80, 0.81, 0.83), MOTOR: (0.09, 0.09, 0.10), BEARING: (0.70, 0.72, 0.76),
    SHAFT: (0.58, 0.60, 0.64), BELT: (0.16, 0.16, 0.18), PULLEY: (0.78, 0.79, 0.82),
    FASTENER: (0.25, 0.25, 0.27), FOAM: (0.20, 0.22, 0.26), "cup": (0.95, 0.45, 0.12),
    SENSOR: (0.10, 0.32, 0.62), MAGNET: (0.62, 0.62, 0.68), SPRING: (0.85, 0.70, 0.20),
    RUBBER: (0.12, 0.12, 0.12),
}
BODIES = ("base", "turntable", "upper_arm", "forearm", "hand", "cup")


def pitch_r(teeth: int) -> float:
    return teeth * GT2_PITCH / math.pi / 2


def belt_length(c: float, r1: float, r2: float) -> float:
    """Exact pitch length of an open belt on two pulleys (mm)."""
    d = abs(r1 - r2)
    return 2 * math.sqrt(max(c * c - d * d, 0.0)) + math.pi * (r1 + r2) + 2 * d * math.asin(min(d / c, 1.0))


def centre_for_length(length: float, r1: float, r2: float) -> float:
    lo, hi = abs(r1 - r2) + 1e-6, length
    for _ in range(80):
        mid = (lo + hi) / 2
        if belt_length(mid, r1, r2) < length:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ------------------------------------------------------------------ parts
@dataclass
class Part:
    name: str                   # unique instance label (GLB node name)
    ref: str                    # part number: STL name for printed parts, BOM key otherwise
    kind: str
    body: str
    shape: Shape                # world placement at q = 0, mm
    material: str
    mass_kg: float | None = None
    print_rot: tuple = (0, 0, 0)
    orientation: str = ""
    color: tuple | None = None


@dataclass
class Design:
    params: dict
    parts: list[Part] = field(default_factory=list)
    belts: list[dict] = field(default_factory=list)
    origins: dict = field(default_factory=dict)      # body frame origins at q = 0 (mm)
    warnings: list[str] = field(default_factory=list)
    infill: float = 0.25
    shell_mm: float = 0.8
    material: str = "PETG"
    info: dict = field(default_factory=dict)

    def add(self, name, ref, kind, body, shape, material=None, mass_kg=None, print_rot=(0, 0, 0),
            orientation="", color=None):
        mat = material or (self.material if kind == PRINTED else "steel")
        self.parts.append(Part(name, ref, kind, body, shape, mat, mass_kg, print_rot, orientation, color))

    # ---------------------------------------------------------- masses
    def part_mass(self, p: Part) -> float:
        if p.mass_kg is not None:
            return p.mass_kg
        v = p.shape.volume
        if p.kind == PRINTED:
            return v * DENSITY[p.material] * self.fill_factor(p)
        return v * DENSITY[p.material]

    def fill_factor(self, p: Part) -> float:
        """Printed solid fraction: perimeters/top/bottom (shell_mm per face) plus sparse infill."""
        v = p.shape.volume
        shell = min(1.0, p.shape.area * self.shell_mm / max(v, 1e-9))
        return shell + self.infill * (1 - shell)

    def mass_props(self) -> dict:
        """Per body: mass (kg), com (m, from the body origin) and inertia about the com (kg m^2),
        in axes aligned with the world at q = 0."""
        from OCP.BRepGProp import BRepGProp
        from OCP.GProp import GProp_GProps
        acc = {b: [] for b in BODIES}
        for p in self.parts:
            gp = GProp_GProps()
            BRepGProp.VolumeProperties_s(p.shape.wrapped, gp)
            vol = gp.Mass()
            if vol <= 0:
                continue
            m = self.part_mass(p)
            rho = m / vol
            c = gp.CentreOfMass()
            M = gp.MatrixOfInertia()
            I = np.array([[M.Value(i, j) for j in (1, 2, 3)] for i in (1, 2, 3)]) * rho
            acc[p.body].append((m, np.array([c.X(), c.Y(), c.Z()]), I))
        out = {}
        for b, items in acc.items():
            if not items:
                continue
            mt = sum(i[0] for i in items)
            com = sum(i[0] * i[1] for i in items) / mt
            I = np.zeros((3, 3))
            for m, c, Ii in items:
                d = c - com
                I += Ii + m * (d @ d * np.eye(3) - np.outer(d, d))
            o = np.asarray(self.origins[b], float)
            out[b] = {"mass": round(float(mt), 6), "com": ((com - o) / 1000).round(6).tolist(),
                      "inertia": (I / 1e6).round(9).tolist(), "parts": len(items)}
        return {"units": "kg, m, kg m^2; body axes = world axes at q = 0", "bodies": out,
                "origins_m": {b: (np.asarray(v, float) / 1000).round(6).tolist() for b, v in self.origins.items()},
                "motor_xz_m": {k: [round(v[0] / 1000, 4), round(v[1] / 1000, 4)]
                               for k, v in self.info.get("motor_xz_mm", {}).items()},
                "geom": {"upper_arm_half_width_m": round(self.info.get("ua_half_width_mm", 32) / 1000, 4)},
                **({"slide": self.info["slide"]} if "slide" in self.info else {}),
                "params_hash": params_hash(self.params)}

    # ---------------------------------------------------------- posing
    def body_locations(self, q) -> dict:
        deg = np.degrees(np.asarray(q, float))
        S, E, W = (self.origins[b] for b in ("upper_arm", "forearm", "hand"))

        def pitch(P, a):          # +a = up: rotation about -y through P
            return Location(tuple(P)) * Rot(0, -a, 0) * Location(tuple(-np.asarray(P)))

        yaw = Location((0, 0, 0)) * Rot(0, 0, deg[0])
        up = yaw * pitch(S, deg[1])
        fo = up * pitch(E, deg[2])
        ha = fo * pitch(W, deg[3])
        return {"base": Location((0, 0, 0)), "turntable": yaw, "upper_arm": up, "forearm": fo,
                "hand": ha, "cup": ha}

    def posed(self, q) -> tuple[Compound, list[Shape]]:
        locs = self.body_locations(q)
        shapes = []
        for p in self.parts:
            s = p.shape.moved(locs[p.body])
            s.label = p.name
            s.color = Color(*(p.color or COLORS[p.kind]))
            shapes.append(s)
        asm = Compound(children=shapes)
        asm.label = f"arm_{self.params.get('name', 'v')}"
        return asm, shapes

    # ---------------------------------------------------------- exports
    def printed_refs(self) -> dict[str, list[Part]]:
        refs: dict[str, list[Part]] = {}
        for p in self.parts:
            if p.kind == PRINTED:
                refs.setdefault(p.ref, []).append(p)
        return refs

    def export_stls(self, out_dir: Path) -> list[Path]:
        from build123d import export_stl
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("*.stl"):
            old.unlink()
        files = []
        for ref, ps in self.printed_refs().items():
            p = ps[0]
            s = p.shape.moved(Location((0, 0, 0)) * Rot(*p.print_rot))
            bb = s.bounding_box()
            s = s.moved(Location((-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z)))
            f = out_dir / f"{ref}.stl"
            export_stl(s, f, tolerance=0.05, angular_tolerance=0.2)
            files.append(f)
        return files

    def print_rows(self) -> list[dict]:
        rows = []
        for ref, ps in self.printed_refs().items():
            p = ps[0]
            g = self.part_mass(p) * 1000
            rows.append({"part": ref, "qty": len(ps), "material": p.material, "orientation": p.orientation,
                         "est_grams": round(g, 1), "est_grams_total": round(g * len(ps), 1),
                         "infill": f"{self.infill:.0%}", "volume_cm3": round(p.shape.volume / 1000, 1),
                         "stl": f"stl/{ref}.stl"})
        return rows

    def write_print_list(self, path: Path) -> list[dict]:
        rows = self.print_rows()
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        return rows

    def bom_rows(self) -> list[dict]:
        return bom_rows(self)

    def write_bom(self, path: Path) -> list[dict]:
        rows = self.bom_rows()
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        return rows


# compliance / spring_k / spring_travel are drawn (the sprung-cup slide), so they are not sim-only
SIM_ONLY_CATCHER_KEYS = ("give_m", "give_runup_m", "spring_damping_ratio", "spring_friction_n", "restitution",
                         "entry_offset_deg")


def params_hash(params: dict) -> str:
    """Hash of the params that change the solids (sim-only catcher settings excluded)."""
    keep = {k: params.get(k) for k in ("style", "joints", "links", "catcher", "belt_arm")}
    if isinstance(keep["catcher"], dict):
        keep["catcher"] = {k: v for k, v in keep["catcher"].items() if k not in SIM_ONLY_CATCHER_KEYS}
    return hashlib.sha1(json.dumps(keep, sort_keys=True, default=str).encode()).hexdigest()[:12]


# ------------------------------------------------------------------ 2D helpers (x, z plane)
def _circle_pts(cx, cz, r, n=40):
    return [(cx + r * math.cos(2 * math.pi * k / n), cz + r * math.sin(2 * math.pi * k / n)) for k in range(n)]


def _rect_pts(cx, cz, hx, hz):
    return [(cx - hx, cz - hz), (cx + hx, cz - hz), (cx + hx, cz + hz), (cx - hx, cz + hz)]


def _hull(pts):
    pts = sorted(set((round(x, 4), round(y, 4)) for x, y in pts))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def _edge_dist(poly, x, z):
    """Signed distance to a convex CCW polygon's boundary (positive inside)."""
    d = float("inf")
    n = len(poly)
    for i in range(n):
        (ax, az), (bx, bz) = poly[i], poly[(i + 1) % n]
        ex, ez = bx - ax, bz - az
        L = math.hypot(ex, ez)
        if L < 1e-9:
            continue
        d = min(d, (ex * (z - az) - ez * (x - ax)) / L)
    return d


def _lightening(poly, avoid, r, margin=4.0, step=None):
    """Circle holes of radius r on a grid inside a convex outline, clear of `avoid` circles."""
    step = step or (2 * r + margin + 1)
    xs = [p[0] for p in poly]
    zs = [p[1] for p in poly]
    holes = []
    z = min(zs) + r + margin
    row = 0
    while z < max(zs):
        x = min(xs) + r + margin + (step / 2 if row % 2 else 0)
        while x < max(xs):
            ok = _edge_dist(poly, x, z) >= r + margin
            ok = ok and all(math.hypot(x - ax, z - az) >= r + ar + margin for ax, az, ar in avoid)
            ok = ok and all(math.hypot(x - hx, z - hz) >= 2 * r + margin for hx, hz, _ in holes)
            if ok:
                holes.append((x, z, r))
            x += step
        z += step * 0.87
        row += 1
    return holes


def _xz_prism(outline, y0, y1, holes=()):
    """Extrude a 2D (x, z) outline across y0..y1. Holes are (x, z, r)."""
    f = Polygon(*outline, align=None)
    for x, z, r in holes:
        f = f - Pos(x, z) * Circle(r)
    s = extrude(f, y1 - y0)
    return s.moved(Location((0, y1, 0)) * Rot(90, 0, 0))


def _ycyl(x, yc, z, r, w, r_in=0.0):
    s = Cylinder(r, w)
    if r_in > 0:
        s = s - Cylinder(r_in, w + 2)
    return s.moved(Location((x, yc, z)) * Rot(90, 0, 0))


def _xcyl(x0, y, z, r, L, r_in=0.0):
    """Cylinder (tube when r_in > 0) along +x from x0 to x0 + L."""
    s = Cylinder(r, L)
    if r_in > 0:
        s = s - Cylinder(r_in, L + 2)
    return s.moved(Location((x0 + L / 2, y, z)) * Rot(0, 90, 0))


def _zcyl(x, y, z0, r, h, r_in=0.0):
    s = Cylinder(r, h)
    if r_in > 0:
        s = s - Cylinder(r_in, h + 2)
    return s.moved(Location((x, y, z0 + h / 2)))


def _pulley_y(x, yc, z, teeth, w=8.0, bore=4.3, flange=1.0, lighten=True):
    """Printed GT2 pulley (teeth implied by a plain rim at the pitch radius) about the y axis."""
    R = pitch_r(teeth) - 0.4
    s = Cylinder(R, w) + Pos(0, 0, w / 2 - flange / 2) * Cylinder(R + 1.5, flange) \
        + Pos(0, 0, -w / 2 + flange / 2) * Cylinder(R + 1.5, flange)
    s = s - Cylinder(bore, w + 2)
    if lighten and R > 22:
        rr = (R - 6 - (bore + 5)) / 2
        rc = bore + 5 + rr
        n = max(4, int(2 * math.pi * rc / (2 * rr + 4)))
        for k in range(n):
            a = 2 * math.pi * k / n
            s = s - Pos(rc * math.cos(a), rc * math.sin(a), 0) * Cylinder(rr * 0.85, w + 2)
    return s.moved(Location((x, yc, z)) * Rot(90, 0, 0))


def _belt_face(c1, r1, c2, r2):
    outer = _hull(_circle_pts(*c1, r1 + BELT_T / 2, 64) + _circle_pts(*c2, r2 + BELT_T / 2, 64))
    inner = _hull(_circle_pts(*c1, r1 - BELT_T / 2, 64) + _circle_pts(*c2, r2 - BELT_T / 2, 64))
    return Polygon(*outer, align=None) - Polygon(*inner, align=None)


def _belt_y(c1, r1, c2, r2, yc, w=6.0):
    """Closed belt in the (x, z) plane, centred on plane y = yc."""
    s = extrude(_belt_face(c1, r1, c2, r2), w)
    return s.moved(Location((0, yc + w / 2, 0)) * Rot(90, 0, 0))


def _nema17(shaft_dir: str, x, y_face, z):
    """NEMA 17 (17HS4401) with its face centre at (x, y_face, z), shaft along shaft_dir."""
    body = Box(NEMA_SIDE, NEMA_SIDE, NEMA_LEN).moved(Location((0, 0, -NEMA_LEN / 2)))
    s = body + Pos(0, 0, 1) * Cylinder(NEMA_BOSS_D / 2, 2) + Pos(0, 0, NEMA_SHAFT[1] / 2) * Cylinder(
        NEMA_SHAFT[0] / 2, NEMA_SHAFT[1])
    rot = {"+y": Rot(-90, 0, 0), "-y": Rot(90, 0, 0), "up": Rot(0, 0, 0)}[shaft_dir]
    return s.moved(Location((x, y_face, z)) * rot)


def _motor_holes(x, z):
    h = NEMA_HOLE / 2
    return [(x, z, NEMA_BOSS_D / 2 + 0.5)] + [(x + sx * h, z + sz * h, 1.7) for sx in (-1, 1) for sz in (-1, 1)]


def _screw_y(x, y_face, z, length, direction, d=3.0):
    """Socket head cap screw along y: head outside y_face, shank going `direction` (+1/-1)."""
    head = Cylinder(d * 0.9, d).moved(Location((0, 0, -d / 2)))
    shank = Cylinder(d / 2, length).moved(Location((0, 0, length / 2)))
    rot = Rot(-90, 0, 0) if direction > 0 else Rot(90, 0, 0)
    return (head + shank).moved(Location((x, y_face, z)) * rot)


def _screw_z(x, y, z_face, length, direction, d=3.0):
    head = Cylinder(d * 0.9, d).moved(Location((0, 0, -d / 2)))
    shank = Cylinder(d / 2, length).moved(Location((0, 0, length / 2)))
    rot = Rot(0, 0, 0) if direction > 0 else Rot(180, 0, 0)
    return (head + shank).moved(Location((x, y, z_face)) * rot)


def _square_dist(cx, cz, half, px=0.0, pz=0.0):
    """Distance from point (px, pz) to an axis-aligned square (0 if inside)."""
    dx = max(abs(px - cx) - half, 0.0)
    dz = max(abs(pz - cz) - half, 0.0)
    return math.hypot(dx, dz)


# ------------------------------------------------------------------ the generator
def default_belt_arm_params() -> dict:
    return {
        "material": "PETG", "infill": 0.25, "shell_mm": 0.8,
        "motor_pulley_teeth": 20, "passthrough_teeth": 40, "belt_width_mm": 6,
        "base_diameter_mm": 180, "base_height_mm": 52,
        "tower_gap_mm": 92, "tower_plate_mm": 6,
        "upper_arm_gap_mm": 56, "upper_arm_plate_mm": 4,
        "forearm_width_mm": 20, "forearm_height_mm": 30, "wall_mm": 2.4,
        "cup_wall_mm": 1.6, "foam_mm": 4.0, "cup_windows": 6,
        "motor_angles_deg": {"shoulder": -45, "elbow": -95, "wrist": -160},
    }


def build_design(arm, q=None) -> Design:
    """Build every part at q = 0 (world, mm). `arm` is an ArmModel."""
    P = dict(default_belt_arm_params())
    user = arm.params.get("belt_arm") or {}
    P.update({k: v for k, v in user.items() if k != "motor_angles_deg"})
    P["motor_angles_deg"] = {**P["motor_angles_deg"], **(user.get("motor_angles_deg") or {})}
    D = Design(params=arm.params, infill=float(P["infill"]), shell_mm=float(P["shell_mm"]),
               material=str(P["material"]))
    wall = float(P["wall_mm"])
    if wall < 2.0:
        D.warnings.append(f"wall_mm {wall} < 2 mm minimum; using 2.0")
        wall = 2.0
    mt = int(P["motor_pulley_teeth"])
    t2 = int(P["passthrough_teeth"])
    bw = float(P["belt_width_mm"])
    pw = bw + 2.0                                   # pulley width incl. flanges
    teeth = [int(round(g * mt)) for g in arm.gear]
    for i, (g, t) in enumerate(zip(arm.gear, teeth)):
        if abs(t / mt - g) / g > 0.01:
            D.warnings.append(f"{arm.joint_names[i]} ratio {g:g} rounded to {t}T/{mt}T = {t / mt:.3f}")
    r_m = pitch_r(mt)
    R = [pitch_r(t) for t in teeth]
    R2 = pitch_r(t2)
    h = arm.base_height * 1000
    L1, L2, L3 = arm.upper * 1000, arm.fore * 1000, arm.hand * 1000
    S = np.array([0.0, 0.0, h])
    E = S + [L1, 0, 0]
    W = E + [L2, 0, 0]
    T = W + [L3, 0, 0]
    D.origins = {"base": (0, 0, 0), "turntable": (0, 0, 0), "upper_arm": tuple(S), "forearm": tuple(E),
                 "hand": tuple(W), "cup": tuple(T)}
    D.info.update(teeth=teeth, motor_teeth=mt, passthrough_teeth=t2)
    D.belts += [link_belt(L1, t2, "elbow_upper"), link_belt(L1, t2, "wrist_upper"), link_belt(L2, t2, "wrist_fore")]
    add = D.add

    # ---------------------------------------------------------------- base (fixed)
    base_r = float(P["base_diameter_mm"]) / 2
    base_h = float(P["base_height_mm"])
    plate_t, deck_t = 5.0, 5.0
    deck_top, deck_bot = base_h, base_h - deck_t
    if deck_bot - NEMA_LEN < plate_t + 1:
        D.warnings.append("base_height_mm too small for the base motor; raised")
        deck_bot = plate_t + 1 + NEMA_LEN
        deck_top = deck_bot + deck_t
    brg_top = deck_top + B51105[2]
    zb = brg_top + 4.5                      # base belt plane
    tt_bot, tt_top = zb + 4.5, zb + 10.5
    D.info["turntable_top_mm"] = tt_top

    # base belt: solve motor centre distance for a stock loop
    cmin = R[0] + r_m + 8
    cmax = base_r - 4 - NEMA_SIDE / math.sqrt(2)
    C0, belt0 = _pick_belt(cmin, cmax, r_m, R[0], D, "base")
    D.belts.append(belt0)

    bp = Cylinder(base_r, plate_t).moved(Location((0, 0, plate_t / 2)))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        bp = bp - Pos((base_r - 10) * math.cos(a), (base_r - 10) * math.sin(a), plate_t / 2) * Cylinder(2.2, plate_t + 2)
    for k in range(6):                       # lightening
        a = k * math.pi / 3 + math.pi / 6
        bp = bp - Pos(base_r * 0.5 * math.cos(a), base_r * 0.5 * math.sin(a), plate_t / 2) * Cylinder(base_r * 0.17, plate_t + 2)
    add("base_plate", "base_plate", PRINTED, "base", bp, orientation="flat, as installed")

    shell = Cylinder(base_r, deck_top - plate_t).moved(Location((0, 0, (deck_top + plate_t) / 2)))
    shell = shell - Cylinder(base_r - 3, deck_bot - plate_t).moved(Location((0, 0, (deck_bot + plate_t) / 2 - 0.01)))
    for x, y, r in _motor_holes(C0, 0):
        shell = shell - Pos(x, y, deck_top - deck_t / 2) * Cylinder(r, deck_t + 2)
    shell = shell - Pos(0, 0, deck_top - deck_t / 2) * Cylinder(4.1, deck_t + 2)
    shell = shell - Pos(-base_r + 1.5, 0, plate_t + 12) * Box(6, 24, 14)        # cable exit
    add("base_shell", "base_shell", PRINTED, "base", shell, print_rot=(180, 0, 0),
        orientation="upside down (deck on the bed)")
    add("motor_base", "nema17", MOTOR, "base", _nema17("up", C0, 0, deck_bot), mass_kg=CATALOG_MASS["motor"])
    add("pulley_motor_base", "gt2_20t", PULLEY, "base", _zcyl(C0, 0, zb - 7, r_m - 0.4, 11.5) +
        _zcyl(C0, 0, zb - 7, r_m + 2.5, 3), material="aluminium", mass_kg=CATALOG_MASS["gt2_20t"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            add(f"screw_base_motor_{sx}{sy}", "M3x10", FASTENER, "base",
                _screw_z(C0 + sx * NEMA_HOLE / 2, sy * NEMA_HOLE / 2, deck_top, 10, -1))
    belt = extrude(_belt_face((C0, 0), r_m, (0, 0), R[0]), bw).moved(Location((0, 0, zb - bw / 2)))
    add("belt_base", f"gt2_loop_{belt0['standard_mm']}", BELT, "base", belt, material="rubber")
    add("bearing_51105", "51105", BEARING, "base", _zcyl(0, 0, deck_top, B51105[0] / 2, B51105[2], B51105[1] / 2),
        mass_kg=CATALOG_MASS["51105"])
    Lsh = tt_top - deck_bot + 4
    add("shaft_base", f"shaft_8x{Lsh:.0f}", SHAFT, "base", _zcyl(0, 0, deck_bot - 6, 4, Lsh))
    for k in range(4):
        a = k * math.pi / 2
        add(f"screw_base_plate_{k}", "M3x10", FASTENER, "base",
            _screw_z((base_r - 6) * math.cos(a), (base_r - 6) * math.sin(a), 0, 10, 1))

    # ---------------------------------------------------------------- turntable
    tt_r = base_r - 5
    tt = Cylinder(tt_r, tt_top - tt_bot).moved(Location((0, 0, (tt_top + tt_bot) / 2)))
    ring_h = tt_bot - (zb - bw / 2 - 1.0)
    tt = tt + _zcyl(0, 0, tt_bot - ring_h, R[0] - 0.4, ring_h, R[0] - 6) + \
        _zcyl(0, 0, tt_bot - ring_h - 1, R[0] + 1.5, 1, R[0] - 6)
    tt = tt + _zcyl(0, 0, brg_top, B51105[1] / 2 + 3.5, tt_bot - brg_top, B608[0] / 2)
    tt = tt - Pos(0, 0, tt_top - 3) * Cylinder(B608[0] / 2, 12)
    add("turntable", "turntable", PRINTED, "turntable", tt, print_rot=(180, 0, 0),
        orientation="upside down (disc on the bed, pulley ring up)")
    add("bearing_turntable", "608-2RS", BEARING, "turntable",
        _zcyl(0, 0, tt_top - B608[2], B608[0] / 2, B608[2], B608[1] / 2), mass_kg=CATALOG_MASS["608"])

    # motor positions around the shoulder axis (x, z) with stock belts
    ty_in = float(P["tower_gap_mm"]) / 2
    ty_t = float(P["tower_plate_mm"])
    ua_in = float(P["upper_arm_gap_mm"]) / 2
    ua_t = float(P["upper_arm_plate_mm"])
    y_sh = -(ty_in - 1.5 - pw / 2)          # shoulder belt plane, just inside the -y tower plate
    y_e1, y_e2 = 14.0, ua_in - 1 - pw / 2   # elbow stage 1 / stage 2 planes
    y_w1, y_w2 = -14.0, -(ua_in - 1 - pw / 2)
    spine_half = 6.0
    angles = P["motor_angles_deg"]
    floor = tt_top + 3
    half = NEMA_SIDE / 2
    motors = {}
    R_sh_side = max(R[1], R[3], R2) + 4      # pulleys on the -y side the elbow motor body must clear
    R_e_side = max(R[2], R2) + 4             # pulleys on the +y side the wrist motor body must clear
    for name, ji, need in (("shoulder", 1, 0.0), ("elbow", 2, R_sh_side), ("wrist", 3, R_e_side)):
        a = math.radians(float(angles[name]))
        ux, uz = math.cos(a), math.sin(a)
        cmin = R[ji] + r_m + 8
        c = cmin
        while _square_dist(c * ux, c * uz, half) < max(need, ua_in * 0 + 31.0) and c < 400:
            c += 1.0
        cmin = c
        # floor: motor body above the turntable
        cmax = (h - floor - half) / max(-uz, 1e-6) if uz < 0 else 400.0
        if cmax < cmin:
            D.warnings.append(f"{name} motor does not fit above the turntable (base_height_m too small "
                              f"for its {teeth[ji]}T pulley); placed at the minimum distance")
            cmax = cmin
        c, b = _pick_belt(cmin, cmax, r_m, R[ji], D, name)
        D.belts.append(b)
        motors[name] = (S[0] + c * ux, S[2] + c * uz)
    D.info["motor_xz_mm"] = {k: [round(float(v[0]), 1), round(float(v[1]), 1)] for k, v in motors.items()}
    D.info["ua_half_width_mm"] = ua_in + ua_t

    Ms, Me, Mw = motors["shoulder"], motors["elbow"], motors["wrist"]
    # homing sensor positions (x, z) around the shoulder axis (see _add_homing)
    home = _homing_layout(arm, S, R, motors, half)
    xf0 = min(Ms[0], Me[0], Mw[0]) - half - 4
    xf1 = max(Ms[0] + half + 4, 30.0)
    foot = _rect_pts((xf0 + xf1) / 2, tt_top + 6, (xf1 - xf0) / 2, 6)
    # tower plates (identical pair; the +y one's motor holes are unused)
    outline = _hull(_circle_pts(S[0], S[2], 22) + _rect_pts(*Ms, half + 3, half + 3) + foot +
                    _rect_pts(*Me, half + 2, half + 2) + _rect_pts(*Mw, half + 2, half + 2))
    holes = [(S[0], S[2], 4.1)] + _motor_holes(*Ms)
    sw = home["shoulder_switch"]
    holes += [(sw[0] + dx, sw[1] + dz, 1.0) for dx, dz in home["shoulder_screw_offsets"]]   # M2 pilot holes
    holes += _lightening(outline, [(S[0], S[2], 22), (Ms[0], Ms[1], half * 1.42 + 2), (sw[0], sw[1], 12),
                                   (0, tt_top, 14)] + [(x, tt_top + 6, 8) for x in np.linspace(xf0, xf1, 8)],
                         r=10, margin=4)
    for side, (y0, y1) in (("l", (ty_in, ty_in + ty_t)), ("r", (-ty_in - ty_t, -ty_in))):
        add(f"tower_plate_{side}", "tower_plate", PRINTED, "turntable", _xz_prism(outline, y0, y1, holes),
            print_rot=(90, 0, 0), orientation="flat on its side face")
    # motor spine between the plates, carrying the elbow and wrist motors
    ep = home["elbow_hall"]
    outline_sp = _hull(_circle_pts(ep[0], ep[1], 7) + _rect_pts(*Me, half + 3, half + 3) + _rect_pts(*Mw, half + 3, half + 3) +
                       _rect_pts((min(Me[0], Mw[0]) - half + max(Me[0], Mw[0]) + half) / 2, tt_top + 6,
                                 (max(Me[0], Mw[0]) - min(Me[0], Mw[0])) / 2 + half, 6))
    holes_sp = _motor_holes(*Me) + _motor_holes(*Mw)
    holes_sp += _lightening(outline_sp, [(Me[0], Me[1], half * 1.42 + 2), (Mw[0], Mw[1], half * 1.42 + 2),
                                         (ep[0], ep[1], 8)], r=7, margin=4)
    add("motor_spine", "motor_spine", PRINTED, "turntable", _xz_prism(outline_sp, -spine_half, spine_half, holes_sp),
        print_rot=(90, 0, 0), orientation="flat on its side face")
    for k, x in enumerate(np.linspace(xf0 + 8, xf1 - 8, 3)):
        for y in (ty_in + ty_t / 2, -ty_in - ty_t / 2):
            add(f"screw_tower_{k}_{'l' if y > 0 else 'r'}", "M3x16", FASTENER, "turntable",
                _screw_z(x, y, tt_bot, 16, 1))
    for k, x in enumerate(np.linspace(min(Me[0], Mw[0]) - half + 6, max(Me[0], Mw[0]) + half - 6, 2)):
        add(f"screw_spine_{k}", "M3x16", FASTENER, "turntable", _screw_z(x, 0, tt_bot, 16, 1))

    # motors, motor pulleys, stage-1 belts
    ms = [("shoulder", Ms, "+y", -ty_in - ty_t, y_sh, 1),
          ("elbow", Me, "+y", -spine_half, y_e1, 2),
          ("wrist", Mw, "-y", spine_half, y_w1, 3)]
    for name, (mx, mz), sd, yf, yb, ji in ms:
        add(f"motor_{name}", "nema17", MOTOR, "turntable", _nema17(sd, mx, yf, mz), mass_kg=CATALOG_MASS["motor"])
        add(f"pulley_motor_{name}", "gt2_20t", PULLEY, "turntable",
            _ycyl(mx, yb, mz, r_m - 0.4, pw) + _ycyl(mx, yb + (pw / 2 + 3) * (1 if sd == "-y" else -1), mz, r_m + 2.5, 6),
            material="aluminium", mass_kg=CATALOG_MASS["gt2_20t"])
        bl = next(b for b in D.belts if b["joint"] == name)
        add(f"belt_{name}_motor", f"gt2_loop_{bl['standard_mm']}", BELT, "turntable",
            _belt_y((mx, mz), r_m, (S[0], S[2]), R[ji], yb, bw), material="rubber")
        # mount screws: heads on the far side of the plate the motor face sits on
        head_y = yf + (ty_t if name == "shoulder" else (2 * spine_half if sd == "+y" else -2 * spine_half))
        hdir = -1 if sd == "+y" else 1
        for sx in (-1, 1):
            for sz in (-1, 1):
                add(f"screw_motor_{name}_{sx}{sz}", "M3x10" if name == "shoulder" else "M3x16", FASTENER, "turntable",
                    _screw_y(mx + sx * NEMA_HOLE / 2, head_y, mz + sz * NEMA_HOLE / 2,
                             10 if name == "shoulder" else 16, hdir))

    # shoulder shaft and compound pulleys (free on the shaft, turntable body for mass)
    Lsh = 2 * (ty_in + ty_t) + 6
    add("shaft_shoulder", f"shaft_8x{Lsh:.0f}", SHAFT, "turntable", _ycyl(S[0], 0, S[2], 4, Lsh))
    for name, y1, y2, ji in (("elbow", y_e1, y_e2, 2), ("wrist", y_w1, y_w2, 3)):
        sgn = 1 if y1 > 0 else -1
        big = _pulley_y(S[0], y1, S[2], teeth[ji], pw, bore=4.3)
        small = _pulley_y(S[0], y2, S[2], t2, pw, bore=4.3, lighten=False)
        hub = _ycyl(S[0], (y1 + y2) / 2, S[2], min(R2, R[ji]) - 2, abs(y2 - y1), 4.3)
        cp = big + small + hub
        brg, bspec = _bearing_for(min(R[ji], R2) - 0.4)
        cp = cp - _ycyl(S[0], y1, S[2], brg[0] / 2, brg[2] * 2 + 0.1) - _ycyl(S[0], y2, S[2], brg[0] / 2, brg[2] * 2 + 0.1)
        add(f"{name}_drive_pulley", f"{name}_drive_pulley", PRINTED, "turntable", cp, print_rot=(90, 0, 0),
            orientation="axis vertical, large pulley down")
        for k, yy in enumerate((y1, y2)):
            yy2 = yy + sgn * (pw / 2 - brg[2] / 2) * (1 if k else -1)
            add(f"bearing_{name}_drive_{k}", bspec, BEARING, "turntable", _ycyl(S[0], yy2, S[2], brg[0] / 2, brg[2], 4),
                mass_kg=CATALOG_MASS[bspec[:3]])
    for sgn in (1, -1):
        add(f"collar_shoulder_{'l' if sgn > 0 else 'r'}", "shaft_collar_8", SHAFT, "turntable",
            _ycyl(S[0], sgn * (ty_in + ty_t + 3), S[2], 7.5, 5, 4))

    # ---------------------------------------------------------------- upper arm
    r_hub_s, r_hub_e = 29.0, 27.0
    outline_ua = _hull(_circle_pts(S[0], S[2], r_hub_s) + _circle_pts(E[0], E[2], r_hub_e))
    zsp = R2 + BELT_T / 2 + 5 + 1.5         # spacer (r = 5) offset from the link axis, clear of the belts
    rmax = max(R[2], R[3], R2) + 2
    x_first = math.sqrt(max((rmax + 9) ** 2 - zsp ** 2, 0)) + 2
    xs_sp = sorted({round(S[0] + x_first, 1), round(S[0] + L1 / 2, 1), round(E[0] - 30, 1)})
    xs_sp = [x for x in xs_sp if S[0] + x_first - 0.5 <= x <= E[0] - 25]
    spacers = [(x, S[2] + s * zsp) for x in xs_sp for s in (1, -1)]
    holes_ua = [(S[0], S[2], B608[0] / 2), (E[0], E[2], 4.1)] + [(x, z, 1.7) for x, z in spacers]
    holes_ua += _lightening(outline_ua, [(S[0], S[2], B608[0] / 2 + 3), (E[0], E[2], 9)] +
                            [(x, z, 5) for x, z in spacers], r=min(13.0, zsp + 5 - 7), margin=3.5)
    if not (zsp + 5 < r_hub_e - 1):
        D.warnings.append("upper-arm spacers stick out of the side plates (passthrough pulley too big)")
    for side, (y0, y1) in (("l", (ua_in, ua_in + ua_t)), ("r", (-ua_in - ua_t, -ua_in))):
        add(f"upper_arm_plate_{side}", "upper_arm_plate", PRINTED, "upper_arm", _xz_prism(outline_ua, y0, y1, holes_ua),
            print_rot=(90, 0, 0), orientation="flat on its side face")
        add(f"bearing_shoulder_{side}", "608-2RS", BEARING, "upper_arm",
            _ycyl(S[0], (y0 + y1) / 2 + (1.5 if y0 > 0 else -1.5), S[2], B608[0] / 2, B608[2], 4),
            mass_kg=CATALOG_MASS["608"])
    for k, (x, z) in enumerate(spacers):
        add(f"arm_spacer_{k}", "arm_spacer", PRINTED, "upper_arm", _ycyl(x, 0, z, 5, 2 * ua_in, 1.7),
            print_rot=(90, 0, 0), orientation="standing on its end")
        for s in (1, -1):
            add(f"screw_spacer_{k}_{s}", "M3x10", FASTENER, "upper_arm",
                _screw_y(x, s * (ua_in + ua_t), z, 10, -s))
    # shoulder pulley bolted to the -y plate (outside it)
    ysh_hub0 = -ua_in - ua_t
    shp = _pulley_y(S[0], y_sh, S[2], teeth[1], pw, bore=4.3) + \
        _ycyl(S[0], (ysh_hub0 + y_sh + pw / 2) / 2, S[2], 13, abs(ysh_hub0 - (y_sh + pw / 2)), 4.3)
    add("shoulder_pulley", "shoulder_pulley", PRINTED, "upper_arm", shp, print_rot=(90, 0, 0),
        orientation="axis vertical, hub up")
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        add(f"screw_shoulder_pulley_{k}", "M3x16", FASTENER, "upper_arm",
            _screw_y(S[0] + 9 * math.cos(a), y_sh - pw / 2, S[2] + 9 * math.sin(a), 16, 1))
    Lsh = 2 * (ua_in + ua_t) + 6
    add("shaft_elbow", f"shaft_8x{Lsh:.0f}", SHAFT, "upper_arm", _ycyl(E[0], 0, E[2], 4, Lsh))
    for yy, nm in ((y_e2, "elbow"), (y_w2, "wrist")):
        bl = next(b for b in D.belts if b["joint"] == f"{nm}_upper")
        add(f"belt_{nm}_upper_arm", f"gt2_loop_{bl['standard_mm']}", BELT, "upper_arm",
            _belt_y((S[0], S[2]), R2, (E[0], E[2]), R2, yy, bw), material="rubber")
    # 40T+40T wrist idler on the elbow shaft
    fw = float(P["forearm_width_mm"]) / 2
    y_w3 = -(fw + 1 + pw / 2)               # forearm belt plane, just outside the forearm
    idl = _pulley_y(E[0], y_w2, E[2], t2, pw, 4.3, lighten=False) + _pulley_y(E[0], y_w3, E[2], t2, pw, 4.3, lighten=False) \
        + _ycyl(E[0], (y_w2 + y_w3) / 2, E[2], R2 - 2, abs(y_w2 - y_w3), 4.3)
    brg, bspec = _bearing_for(R2 - 0.4)
    for k, yy in enumerate((y_w2, y_w3)):
        idl = idl - _ycyl(E[0], yy, E[2], brg[0] / 2, brg[2] + 0.1)
    add("wrist_idler_pulley", "wrist_idler_pulley", PRINTED, "upper_arm", idl, print_rot=(90, 0, 0),
        orientation="axis vertical")
    for k, yy in enumerate((y_w2, y_w3)):
        add(f"bearing_wrist_idler_{k}", bspec, BEARING, "upper_arm", _ycyl(E[0], yy, E[2], brg[0] / 2, brg[2], 4),
            mass_kg=CATALOG_MASS[bspec[:3]])
    for sgn in (1, -1):
        add(f"collar_elbow_{'l' if sgn > 0 else 'r'}", "shaft_collar_8", SHAFT, "upper_arm",
            _ycyl(E[0], sgn * (ua_in + ua_t + 3), E[2], 7.5, 5, 4))

    # ---------------------------------------------------------------- forearm
    fh = float(P["forearm_height_mm"]) / 2
    r_end = fh
    outline_fa = _hull(_circle_pts(E[0], E[2], r_end) + _circle_pts(W[0], W[2], r_end))
    fa = _xz_prism(outline_fa, -fw, fw)
    x_in0, x_in1 = E[0] + r_end + 4, W[0] - r_end - 4
    if x_in1 - x_in0 > 10:
        cav = Box(x_in1 - x_in0, 2 * (fw - wall), 2 * (fh - wall)).moved(
            Location(((x_in0 + x_in1) / 2, 0, E[2])))
        fa = fa - cav
        n_h = max(1, int((x_in1 - x_in0 - 6) // (2 * (fh - wall - 3) + 8)))
        rr = min(fh - wall - 3, (x_in1 - x_in0 - 6) / n_h / 2 - 4)
        for k in range(n_h):
            x = x_in0 + (k + 0.5) * (x_in1 - x_in0) / n_h
            fa = fa - _ycyl(x, 0, E[2], rr, 2 * fw + 2)
            fa = fa - Box(min(2 * rr, 24), 2 * fw - 2 * wall, 2 * fh + 2).moved(Location((x, 0, E[2])))
    fa = fa - _ycyl(E[0], 0, E[2], B608[0] / 2, 2 * fw + 2) - _ycyl(W[0], 0, W[2], 4.1, 2 * fw + 2)
    add("forearm", "forearm", PRINTED, "forearm", fa, print_rot=(90, 0, 0), orientation="on its side face")
    for s in (1, -1):
        add(f"bearing_elbow_{'l' if s > 0 else 'r'}", "608-2RS", BEARING, "forearm",
            _ycyl(E[0], s * (fw - B608[2] / 2), E[2], B608[0] / 2, B608[2], 4), mass_kg=CATALOG_MASS["608"])
    fpu = _pulley_y(E[0], y_e2, E[2], t2, pw, 4.3, lighten=False) + \
        _ycyl(E[0], (fw + y_e2 - pw / 2) / 2, E[2], R2 - 2, y_e2 - pw / 2 - fw + 0.01, 4.3)
    add("forearm_pulley", "forearm_pulley", PRINTED, "forearm", fpu, print_rot=(90, 0, 0),
        orientation="axis vertical, hub up")
    for k in range(3):
        a = 2 * math.pi * k / 3
        add(f"screw_forearm_pulley_{k}", "M3x16", FASTENER, "forearm",
            _screw_y(E[0] + 8 * math.cos(a), y_e2 + pw / 2, E[2] + 8 * math.sin(a), 16, -1))
    bl = next(b for b in D.belts if b["joint"] == "wrist_fore")
    add("belt_wrist_forearm", f"gt2_loop_{bl['standard_mm']}", BELT, "forearm",
        _belt_y((E[0], E[2]), R2, (W[0], W[2]), R2, y_w3, bw), material="rubber")
    hy0 = abs(y_w3) + pw / 2 + 0.5              # hand fork cheeks start here
    Lsh = 2 * (hy0 + B608[2] + 1) + 6
    add("shaft_wrist", f"shaft_8x{Lsh:.0f}", SHAFT, "forearm", _ycyl(W[0], 0, W[2], 4, Lsh))

    # ---------------------------------------------------------------- hand + cup
    cup_r = arm.cup_d * 1000 / 2
    depth = arm.cup_depth * 1000
    foam = float(P["foam_mm"])
    cw = float(P["cup_wall_mm"])
    x_back = T[0] - depth / 2 - foam - cw        # outer bottom of the cup
    hub_r = 15.0
    cheek_t = B608[2] + 1
    cross_t = 5.0
    ro = cup_r + foam + cw
    sl = _slide_layout(D, arm, x_back=x_back, ro=ro, W=W) if arm.compliance == "spring" else None
    x_plate = sl["x_plate"] if sl else x_back      # front face of the hand's cross plate
    if x_plate - cross_t - W[0] < hub_r + 3:
        need = (hub_r + 3 + cross_t - (x_plate - W[0])) / 1000 + arm.hand
        D.warnings.append(f"hand_m too short for a {depth:.0f} mm deep cup"
                          f"{' plus the slide travel' if sl else ''}: the cross plate is {x_plate - W[0]:.0f} mm "
                          f"from the wrist axis (need {hub_r + 3 + cross_t:.0f}); set hand_m >= {need:.3f}")
    xc = max(x_plate, W[0] + hub_r + 3 + cross_t)
    ch_out = _hull(_circle_pts(W[0], W[2], hub_r) + _rect_pts(xc - cross_t / 2, W[2], cross_t / 2, hub_r))
    hand = _xz_prism(ch_out, hy0, hy0 + cheek_t) + _xz_prism(ch_out, -hy0 - cheek_t, -hy0)
    hand = hand + Box(cross_t, 2 * (hy0 + cheek_t), 2 * hub_r).moved(Location((xc - cross_t / 2, 0, W[2])))
    if sl:
        hand = _slide_plate(hand, sl, xc, cross_t, W)
    hand = hand - _ycyl(W[0], hy0 + cheek_t / 2, W[2], B608[0] / 2, cheek_t + 1) \
        - _ycyl(W[0], -hy0 - cheek_t / 2, W[2], B608[0] / 2, cheek_t + 1)
    add("hand_fork", "hand_fork", PRINTED, "hand", hand, print_rot=(0, 90, 0),
        orientation="cross plate on the bed, cheeks up")
    for s in (1, -1):
        add(f"bearing_wrist_{'l' if s > 0 else 'r'}", "608-2RS", BEARING, "hand",
            _ycyl(W[0], s * (hy0 + cheek_t / 2), W[2], B608[0] / 2, B608[2], 4), mass_kg=CATALOG_MASS["608"])
    hp = _pulley_y(W[0], y_w3, W[2], t2, pw, 4.3, lighten=False) + \
        _ycyl(W[0], (y_w3 - pw / 2 - hy0) / 2, W[2], R2 - 2, abs(-hy0 - (y_w3 - pw / 2)) + 0.01, 4.3)
    add("hand_pulley", "hand_pulley", PRINTED, "hand", hp, print_rot=(90, 0, 0), orientation="axis vertical, hub up")
    for k in range(3):
        a = 2 * math.pi * k / 3 + 0.5
        add(f"screw_hand_pulley_{k}", "M3x16", FASTENER, "hand",
            _screw_y(W[0] + 8 * math.cos(a), y_w3 + pw / 2, W[2] + 8 * math.sin(a), 16, -1))
    for s in ((1, -1) if sl is None else ()):        # fixed cup: screwed to the cross plate, along +x
        add(f"screw_cup_{'l' if s > 0 else 'r'}", "M3x10", FASTENER, "hand",
            Cylinder(2.7, 3).moved(Location((xc - cross_t - 1.5, s * 12, W[2])) * Rot(0, 90, 0)) +
            Cylinder(1.5, 10).moved(Location((xc - cross_t + 5, s * 12, W[2])) * Rot(0, 90, 0)))

    # cup shell: opening along +x, outer bottom at x_back
    L_shell = T[0] + depth / 2 - x_back
    shell_c = Cylinder(ro, L_shell) - Pos(0, 0, cw / 2 + 0.01) * Cylinder(ro - cw, L_shell - cw + 0.02)
    n_win = int(P["cup_windows"])
    if n_win > 0:                            # windows behind the foam: the liner carries the ball, the ribs the liner
        rib = 8.0
        wwin = 2 * math.pi * ro / n_win - rib
        hwin = L_shell - 2 * cw - 14
        if wwin > 6 and hwin > 10:
            for k in range(n_win):
                # sprung cup: a rib (not a window) faces each slide lug at +-y
                a = 2 * math.pi * (k + 0.5) / n_win + (math.pi / 2 if sl else 0.0)
                cut = Box(3 * cw + 4, wwin, hwin).moved(Location((ro * math.cos(a), ro * math.sin(a), 0)) *
                                                       Rot(0, 0, math.degrees(a)))
                shell_c = shell_c - cut
    shell_c = shell_c.moved(Location((x_back + L_shell / 2, 0, T[2])) * Rot(0, 90, 0))
    if sl:
        shell_c = _cup_lugs(shell_c, sl, ro, cw, T)
    add("cup_shell", "cup_shell", PRINTED, "cup", shell_c, print_rot=(0, -90, 0),
        orientation="opening up" + (" (slide lugs on the bed, bores vertical)" if sl else ""), color=COLORS["cup"])
    L_foam = depth + foam
    foam_s = Cylinder(cup_r + foam, L_foam) - Pos(0, 0, foam / 2 + 0.01) * Cylinder(cup_r, L_foam - foam + 0.02)
    foam_s = foam_s.moved(Location((x_back + cw + L_foam / 2, 0, T[2])) * Rot(0, 90, 0))
    if arm.liner == "net_pocket":       # slack nylon net pocket on the ribs (estimate 12 g); drawn as the liner ring
        add("cup_liner", "net_pocket", FOAM, "cup", foam_s, material="EVA foam", mass_kg=0.012)
    else:
        add("cup_liner", "eva_foam_liner", FOAM, "cup", foam_s, material="EVA foam")

    if sl:
        _add_slide_hardware(D, sl, T)
    D.info.update(cup_outer_d_mm=round(2 * ro, 1), planes_mm={"shoulder": y_sh, "elbow": [y_e1, y_e2],
                                                              "wrist": [y_w1, y_w2, y_w3]})
    _add_homing(D, arm, home, S=S, W=W, R=R, pw=pw, y_e1=y_e1, spine_half=spine_half, ty_in=ty_in, ty_t=ty_t,
                ua_out=ua_in + ua_t, deck_top=deck_top, tt_bot=tt_bot, fw=fw, hy0=hy0, half=half)
    _check_clearances(D, S, motors, R, R2, r_m, y_sh, y_e1, y_w1, spine_half, ty_in, ty_t, h)
    return D


# ------------------------------------------------------------------ sprung cup slide
def pick_spring(k_total_n_per_m: float, n_parallel: int = 2) -> dict:
    """Stock spring whose rate x n_parallel is closest to the requested slide stiffness."""
    return min(SPRINGS, key=lambda sp: abs(sp["rate_n_per_mm"] * 1000 * n_parallel - k_total_n_per_m))


def _slide_layout(D: Design, arm, *, x_back: float, ro: float, W) -> dict:
    """Positions (world x at q = 0, mm) of the sprung-cup slide. The cup's outer bottom sits at x_back at
    rest (slide = 0) and moves back by up to `travel` onto the rubber bumper on the plate face.

        plate face   bumper     cup bottom (rest)   lug: brake | LM4UU      O-ring  collar
        x_plate  ->  +BUMPER_H  ... travel ...      x_back   +6     +18.5   +1.5    +5

    Each spring sits on its rod between the bottom of a pocket in the plate boss (x_seat) and the
    lug's rear face (x_back). The lug's rear block is a friction brake: an M3 set screw presses a felt
    pad on the rod (the slide's damper; an undamped spring throws the ball back out). Rest length L_rest leaves the catalogue minimum working length at full
    travel; free length - L_rest is the preload."""
    sp = pick_spring(arm.spring_k)
    n_par = 2
    k_hw = sp["rate_n_per_mm"] * 1000 * n_par
    if abs(k_hw - arm.spring_k) / arm.spring_k > 0.15:
        D.warnings.append(f"spring_k_n_per_m {arm.spring_k:g}: the closest stock spring pair ({sp['id']}) gives "
                          f"{k_hw:.0f} N/m; set spring_k_n_per_m to {k_hw:.0f} so the sim matches the hardware")
    travel = arm.spring_travel * 1000
    max_travel = sp["free_mm"] - 0.5 - sp["min_work_mm"] - 0.5          # >= 0.5 mm preload and margin
    if travel > max_travel:
        D.warnings.append(f"spring_travel_m {travel / 1000:.3f}: {sp['id']} allows at most {max_travel:.1f} mm "
                          f"(free {sp['free_mm']:g} mm, min working {sp['min_work_mm']:g} mm); drawn at that")
        travel = max_travel
    L_rest = min(sp["free_mm"] - 0.5, sp["min_work_mm"] + 0.5 + travel)
    preload = sp["free_mm"] - L_rest
    x_plate = x_back - travel - BUMPER[1]
    x_seat = x_back - L_rest
    pocket = x_plate - x_seat
    clamp = 10.0
    lug_len = BRAKE_LEN + LM4UU[2] + 0.5
    yr = ro + COLLAR_4[0] / 2 + 1.5                 # rods (and collars) clear the cup shell
    rod0 = x_seat - clamp + 1.0
    rod1 = x_back + lug_len + ORING_4[1] + COLLAR_4[1] + 1.0
    rod_len = math.ceil(rod1 - rod0)
    f_max = sp["rate_n_per_mm"] * (sp["free_mm"] - (L_rest - travel))
    out = {"spring": sp, "n_springs": n_par, "k_hw_n_per_m": round(k_hw, 1), "travel_mm": round(travel, 2),
           "L_rest_mm": round(L_rest, 2), "preload_mm": round(preload, 2),
           "preload_n": round(n_par * sp["rate_n_per_mm"] * preload, 3),
           "max_force_n": round(n_par * f_max, 2), "x_plate": x_plate, "x_seat": x_seat, "x_back": x_back,
           "pocket_mm": round(pocket, 2), "clamp_mm": clamp, "boss_r": 7.0, "lug_len": lug_len, "lug_r": 6.5,
           "yr": yr, "rod0": rod0, "rod_len_mm": rod_len, "z": W[2]}
    if pocket < 2:
        D.warnings.append("slide spring pocket is shallower than 2 mm; the spring seat is outside the boss")
    return out


def _slide_plate(hand, sl: dict, xc: float, cross_t: float, W) -> Shape:
    """Widen the hand's cross plate into a bar carrying the two rod bosses (spring pocket + rod clamp)."""
    yr, br, z = sl["yr"], sl["boss_r"], sl["z"]
    boss_len = sl["pocket_mm"] + sl["clamp_mm"]
    hand = hand + Box(cross_t, 2 * yr, 2 * br).moved(Location((xc - cross_t / 2, 0, z)))
    for s in (1, -1):
        hand = hand + _xcyl(xc - boss_len, s * yr, z, br, boss_len)
        hand = hand - _xcyl(xc - boss_len - 1, s * yr, z, ROD_D / 2 + 0.05, boss_len + 2)    # rod bore
        hand = hand - _xcyl(xc - sl["pocket_mm"], s * yr, z, sl["spring"]["od_mm"] / 2 + 0.4, sl["pocket_mm"] + 0.5)
        hand = hand - _zcyl(xc - boss_len + sl["clamp_mm"] / 2, s * yr, z + 1.0, 2.0, br)   # M3 insert for the grub
    return hand


def _cup_lugs(shell, sl: dict, ro: float, cw: float, T) -> Shape:
    """Two bearing lugs on the cup shell's rear end at +-yr: a brake block (rear face = spring seat,
    felt pad pocket + M3 insert boss on top) and the LM4UU bore, pressed in from the front."""
    yr, z, L, r = sl["yr"], T[2], sl["lug_len"], sl["lug_r"]
    x0 = sl["x_back"]
    xb = x0 + BRAKE_LEN / 2
    for s in (1, -1):
        web = Box(L, yr - (ro - cw), 2 * ROD_D).moved(Location((x0 + L / 2, s * (yr + ro - cw) / 2, z)))
        boss = Box(BRAKE_LEN, 8.0, 4.0).moved(Location((xb, s * yr, z + r + 1.0)))
        shell = shell + web + _xcyl(x0, s * yr, z, r, L) + boss
        shell = shell - _xcyl(x0 + BRAKE_LEN, s * yr, z, LM4UU[0] / 2, L)            # LM4UU press fit from the front
        shell = shell - _xcyl(x0 - 1, s * yr, z, ROD_D / 2 + 0.6, BRAKE_LEN + 2)     # rod clearance in the brake block
        shell = shell - _zcyl(xb, s * yr, z, FELT[0] / 2 + 0.1, ROD_D / 2 + FELT[1] + 0.2)   # felt pad pocket
        shell = shell - _zcyl(xb, s * yr, z + ROD_D / 2 + FELT[1], 2.0, r + 4)               # M3 heat-set insert
    return shell


def _spring_coils(x0: float, x1: float, y: float, z: float, sp: dict, n: int = 20) -> Compound:
    """A compression spring drawn as a stack of wire rings (no sweep), from x0 to x1."""
    ro, ri = sp["od_mm"] / 2, sp["od_mm"] / 2 - sp["wire_mm"]
    w = sp["wire_mm"]
    rings = []
    for k in range(n):
        xk = x0 + (x1 - x0 - w) * k / (n - 1)
        rings.append(_xcyl(xk, y, z, ro, w, ri))
    return Compound(children=rings)


def _add_slide_hardware(D: Design, sl: dict, T) -> None:
    add = D.add
    z, yr, sp = sl["z"], sl["yr"], sl["spring"]
    x_back, lug_len = sl["x_back"], sl["lug_len"]
    for s, side in ((1, "l"), (-1, "r")):
        add(f"slide_rod_{side}", f"rod_4x{sl['rod_len_mm']}", SHAFT, "hand",
            _xcyl(sl["rod0"], s * yr, z, ROD_D / 2, sl["rod_len_mm"]))
        add(f"slide_bearing_{side}", "LM4UU", BEARING, "cup",
            _xcyl(x_back + BRAKE_LEN, s * yr, z, LM4UU[0] / 2, LM4UU[2], LM4UU[1] / 2), mass_kg=CATALOG_MASS["LM4UU"])
        xbk = x_back + BRAKE_LEN / 2
        add(f"slide_brake_felt_{side}", "felt_pad_5x3", RUBBER, "cup",
            _zcyl(xbk, s * yr, z + ROD_D / 2, FELT[0] / 2, FELT[1]), material="rubber", mass_kg=0.00005,
            color=(0.55, 0.50, 0.42))
        add(f"brake_screw_{side}", "M3x6_grub", FASTENER, "cup", _zcyl(xbk, s * yr, z + ROD_D / 2 + FELT[1], 1.5, 6))
        add(f"slide_spring_{side}", sp["ref"], SPRING, "hand", _spring_coils(sl["x_seat"], x_back, s * yr, z, sp),
            mass_kg=CATALOG_MASS["spring"])
        xo = x_back + lug_len
        add(f"slide_oring_{side}", "oring_4x1.5", RUBBER, "hand",
            _xcyl(xo, s * yr, z, ORING_4[0] / 2 + ORING_4[1], ORING_4[1], ORING_4[0] / 2), material="rubber")
        add(f"slide_collar_{side}", "shaft_collar_4", SHAFT, "hand",
            _xcyl(xo + ORING_4[1], s * yr, z, COLLAR_4[0] / 2, COLLAR_4[1], ROD_D / 2), material="aluminium")
        xb = sl["x_plate"] - sl["pocket_mm"] - sl["clamp_mm"] / 2
        add(f"grub_slide_{side}", "M3x6_grub", FASTENER, "hand", _zcyl(xb, s * yr, z + ROD_D / 2, 1.5, 6))
    add("slide_bumper", "bumper_12x3.5", RUBBER, "hand",
        _xcyl(sl["x_plate"], 0, z, BUMPER[0] / 2, BUMPER[1]), material="rubber")
    D.info["slide"] = {
        "type": "linear slide along the hand axis (cup moves toward the wrist when hit)",
        "axis_body": "hand", "axis": [1.0, 0.0, 0.0], "range_m": [-sl["travel_mm"] / 1000, 0.0],
        "rods": f"2 x 4 mm hardened rod, {sl['rod_len_mm']} mm, cantilevered from the hand bosses",
        "bearings": "2 x LM4UU (4x8x12) in lugs on the cup shell",
        "spring": {k: sp[k] for k in ("id", "material", "wire_mm", "od_mm", "free_mm", "rate_n_per_mm",
                                      "min_work_mm", "load_at_min_n", "source")},
        "n_springs": sl["n_springs"], "k_hw_n_per_m": sl["k_hw_n_per_m"], "travel_m": sl["travel_mm"] / 1000,
        "rest_length_mm": sl["L_rest_mm"], "preload_m": sl["preload_mm"] / 1000, "preload_n": sl["preload_n"],
        "max_force_n": sl["max_force_n"], "rod_pitch_mm": round(2 * yr, 1),
        "end_stops": "rear: rubber bumper 12.7 x 3.5 on the plate face; front: shaft collar + NBR O-ring per rod",
        "damper": "friction brake: felt pad pressed on each rod by an M3 set screw in the lug (Coulomb drag, "
                  "set on the bench; the sim uses catcher.spring_friction_n)",
        "brake_drag_target_n": DEFAULT_SLIDE_FRICTION_N,
        "rest_offset_max_mm": round(max(DEFAULT_SLIDE_FRICTION_N - sl["preload_n"], 0) / sl["k_hw_n_per_m"] * 1000, 1),
    }


def _polar(c, r, deg):
    a = math.radians(deg)
    return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))


def _homing_layout(arm, S, R, motors, half) -> dict:
    """Where the homing sensors sit (x, z in mm at q = 0). Angles are in the arm plane, measured
    from +x toward +z (positive pitch turns a link that way)."""
    sh_hi = math.degrees(float(arm.limits[1, 1]))
    th_sw = -120.0                                   # shoulder switch: behind/below the shoulder axis
    r_tab = 22.0
    r_mag_e = R[2] - 3.5                             # magnet in the elbow drive pulley's rim
    th_e = -120.0
    out = {"shoulder_q_home_deg": sh_hi, "shoulder_tab_deg": th_sw - sh_hi, "shoulder_th_deg": th_sw,
           "shoulder_r": r_tab,
           "shoulder_switch": _polar((S[0], S[2]), r_tab + 2, th_sw + 10),
           "shoulder_lever": _polar((S[0], S[2]), r_tab, th_sw + 2),
           "shoulder_screw_offsets": [(-3.25 * math.sin(math.radians(th_sw + 10)), 3.25 * math.cos(math.radians(th_sw + 10))),
                                      (3.25 * math.sin(math.radians(th_sw + 10)), -3.25 * math.cos(math.radians(th_sw + 10)))],
           "elbow_r": r_mag_e, "elbow_th_deg": th_e, "elbow_hall": _polar((S[0], S[2]), r_mag_e, th_e),
           "elbow_ok": r_mag_e - MAG[0] / 2 >= B608[0] / 2 + 3}
    return out


def _add_homing(D, arm, home, *, S, W, R, pw, y_e1, spine_half, ty_in, ty_t, ua_out, deck_top, tt_bot, fw, hy0, half):
    """Homing sensors (standards rule 4), all wired on the base/turntable except the wrist switch:
    base   A3144 hall on a post on the base deck, magnet in the turntable underside: q0 = 0;
    shoulder  KW12-3 on the +y tower plate, tripped by a tab on the upper arm near q1 = upper limit;
    elbow  A3144 in a pocket of the motor spine, magnet in the elbow drive pulley: with belt
           pass-through that pulley turns with the forearm's absolute pitch, so it homes a2 = q1+q2 = 0;
    wrist  KW12-3 on the forearm's +y face, tripped by a tab on the hand fork near q3 = lower limit.
    """
    add = D.add
    rows = []
    # base: post + hall on the deck, magnet in the turntable underside (q0 = 0 at the magnet)
    r_b = R[0] + 12.0
    bx, by = -r_b, 0.0
    post_h = tt_bot - 2.5 - deck_top - A3144[2]
    add("hall_post_base", "hall_post_base", PRINTED, "base", _zcyl(bx, by, deck_top, 5.0, post_h) +
        Box(12, 10, 3).moved(Location((bx + 2, by, deck_top + 1.5))), orientation="standing, foot on the bed")
    add("hall_base", "A3144", SENSOR, "base", Box(A3144[1], A3144[0], A3144[2]).moved(
        Location((bx, by, deck_top + post_h + A3144[2] / 2))), mass_kg=CATALOG_MASS["A3144"])
    add("magnet_base", "magnet_5x2", MAGNET, "turntable", _zcyl(bx, by, tt_bot - 0.01, MAG[0] / 2, MAG[1]),
        mass_kg=CATALOG_MASS["magnet_5x2"])
    rows.append({"joint": "base", "sensor": "A3144 hall + 5x2 magnet", "mount": "post on the base deck",
                 "trigger": "magnet in the turntable underside", "homes": "q0 = 0 (index, sweep +-)",
                 "home_deg": 0.0, "coordinate": "q0"})
    # shoulder: KW12-3 on the +y tower plate inner face, tab on the upper arm's +y plate
    sx, sz = home["shoulder_switch"]
    th = home["shoulder_th_deg"] + 10
    y0 = ty_in - KW12_3[2]
    body = Box(KW12_3[0], KW12_3[2], KW12_3[1]).moved(Location((sx, (y0 + ty_in) / 2, sz)) * Rot(0, -th - 90, 0))
    add("switch_shoulder", "KW12-3", SENSOR, "turntable", body, mass_kg=CATALOG_MASS["KW12-3"])
    lx, lz = home["shoulder_lever"]
    add("switch_shoulder_lever", "KW12-3_lever", SENSOR, "turntable",
        Box(2.0, y0 - (ua_out + 4), 2.0).moved(Location((lx, (y0 + ua_out + 4) / 2, lz))), mass_kg=0.0)
    for k, (dx, dz) in enumerate(home["shoulder_screw_offsets"]):
        add(f"screw_switch_shoulder_{k}", "M2x10", FASTENER, "turntable",
            _screw_y(sx + dx, ty_in + ty_t, sz + dz, 10, -1, d=2.0))
    tx, tz = _polar((S[0], S[2]), home["shoulder_r"], home["shoulder_tab_deg"])
    add("home_tab_shoulder", "home_tab_shoulder", PRINTED, "upper_arm",
        _ycyl(tx, ua_out + 3, tz, 4.0, 6.0, 1.1), orientation="flat on its end (M2 screw into the plate)")
    rows.append({"joint": "shoulder", "sensor": "KW12-3 microswitch", "mount": "+y tower plate, inner face",
                 "trigger": "tab on the upper arm +y plate",
                 "homes": f"q1 = {home['shoulder_q_home_deg']:.0f} deg (upper limit; trips a few deg before)",
                 "home_deg": round(home["shoulder_q_home_deg"], 1), "coordinate": "q1 = a1"})
    # elbow: hall in the spine's +y face, magnet in the elbow drive pulley's inner face
    ex, ez = home["elbow_hall"]
    if not home["elbow_ok"]:
        D.warnings.append("elbow drive pulley too small for the 5x2 homing magnet; move the elbow hall sensor")
    add("hall_elbow", "A3144", SENSOR, "turntable", Box(A3144[0], A3144[2], A3144[1]).moved(
        Location((ex, spine_half + A3144[2] / 2, ez))), mass_kg=CATALOG_MASS["A3144"])
    add("magnet_elbow", "magnet_5x2", MAGNET, "turntable",
        _ycyl(ex, y_e1 - pw / 2 + MAG[1] / 2 - 0.01, ez, MAG[0] / 2, MAG[1]), mass_kg=CATALOG_MASS["magnet_5x2"])
    rows.append({"joint": "elbow", "sensor": "A3144 hall + 5x2 magnet", "mount": "pocket in the motor spine (+y face)",
                 "trigger": "magnet in the elbow drive pulley (turns with the forearm's absolute pitch)",
                 "homes": "a2 = q1 + q2 = 0 (forearm level)", "home_deg": 0.0, "coordinate": "a2 = q1+q2"})
    # wrist: KW12-3 on the forearm's +y face near the wrist, tab on the hand fork's +y cheek
    q3_lo = math.degrees(float(arm.limits[3, 0]))
    th_w = 150.0
    wl = _polar((W[0], W[2]), 12.0, th_w)
    add("switch_wrist", "KW12-3", SENSOR, "forearm", Box(KW12_3[0], KW12_3[2], KW12_3[1]).moved(
        Location((W[0] - 19.0, fw + KW12_3[2] / 2, W[2] + 7.0))), mass_kg=CATALOG_MASS["KW12-3"])
    add("switch_wrist_lever", "KW12-3_lever", SENSOR, "forearm",
        Box(2.0, 2.0, 2.0).moved(Location((wl[0], fw + KW12_3[2] + 1.0, wl[1]))), mass_kg=0.0)
    for k, dx in enumerate((-3.25, 3.25)):
        add(f"screw_switch_wrist_{k}", "M2x10", FASTENER, "forearm",
            _screw_y(W[0] - 19.0 + dx, fw + KW12_3[2], W[2] + 7.0, 10, -1, d=2.0))
    wt = _polar((W[0], W[2]), 12.0, th_w - q3_lo)
    add("home_tab_wrist", "home_tab_wrist", PRINTED, "hand", _ycyl(wt[0], hy0 - 1.75, wt[1], 3.5, 3.5, 1.1),
        orientation="flat on its end (M2 screw into the cheek)")
    rows.append({"joint": "wrist", "sensor": "KW12-3 microswitch", "mount": "forearm +y face, at the wrist",
                 "trigger": "tab on the hand fork +y cheek",
                 "homes": f"q3 = {q3_lo:.0f} deg (lower limit; home after the elbow, a3 = a2 + q3)",
                 "home_deg": round(q3_lo, 1), "coordinate": "q3 (then a3 = a2 + q3)"})
    D.info["homing"] = rows
    # shoulder first lifts the arm clear; the elbow index reads a2 = q1 + q2, so it needs the shoulder homed
    D.info["homing_order"] = ["shoulder", "elbow", "wrist", "base"]


def _bearing_for(r_body: float):
    """Largest stock bearing that leaves >= 3 mm of plastic in a pulley of body radius r_body."""
    if r_body - B608[0] / 2 >= 3:
        return B608, "608-2RS"
    return B688, "688-2RS"


def _pick_belt(cmin: float, cmax: float, r1: float, r2: float, D: Design, joint: str):
    """Smallest stock closed loop whose centre distance lands in [cmin, cmax]."""
    lmin = belt_length(cmin, r1, r2)
    lmax = belt_length(cmax, r1, r2) if cmax > cmin else lmin
    for L in GT2_LOOPS:
        if lmin <= L <= lmax:
            c = centre_for_length(L, r1, r2)
            return c, {"joint": joint, "teeth": [round(r1 * math.pi), round(r2 * math.pi)],
                       "centre_mm": round(c, 1), "computed_mm": round(belt_length(c, r1, r2), 1),
                       "standard_mm": L, "note": "stock loop; tension by slotting the motor mount"}
    L = next((x for x in GT2_LOOPS if x >= lmin), GT2_LOOPS[-1])
    D.warnings.append(f"{joint}: no stock GT2 loop fits {lmin:.0f}-{lmax:.0f} mm; using {L} mm with an idler")
    return cmin, {"joint": joint, "teeth": [round(r1 * math.pi), round(r2 * math.pi)], "centre_mm": round(cmin, 1),
                  "computed_mm": round(lmin, 1), "standard_mm": L, "note": "needs an F624ZZ idler tensioner"}


def _check_clearances(D, S, motors, R, R2, r_m, y_sh, y_e1, y_w1, spine_half, ty_in, ty_t, h):
    """Belt runs must not pass through another motor's body in the same y band."""
    half = NEMA_SIDE / 2
    bodies = {"shoulder": (motors["shoulder"], (-1e9, -ty_in - ty_t)),
              "elbow": (motors["elbow"], (-ty_in, -spine_half)),
              "wrist": (motors["wrist"], (spine_half, ty_in))}
    runs = {"shoulder": (y_sh, R[1]), "elbow": (y_e1, R[2]), "wrist": (y_w1, R[3])}
    for name, (yb, Rb) in runs.items():
        (mx, mz) = motors[name]
        pts = _hull(_circle_pts(mx, mz, r_m + 1, 24) + _circle_pts(S[0], S[2], Rb + 1, 48))
        for other, ((ox, oz), (ya, yb2)) in bodies.items():
            if other == name or not (ya <= yb <= yb2):
                continue
            # sample the belt outline and a coarse interior grid
            inside = [p for p in pts if abs(p[0] - ox) < half and abs(p[1] - oz) < half]
            if inside:
                D.warnings.append(f"{name} belt passes through the {other} motor body")


# ------------------------------------------------------------------ link belts + BOM
def link_belt(c_mm: float, teeth: int, joint: str) -> dict:
    r = pitch_r(teeth)
    L = belt_length(c_mm, r, r)
    std = min(GT2_LOOPS, key=lambda x: abs(x - L))
    c_std = centre_for_length(std, r, r)
    return {"joint": joint, "teeth": [teeth, teeth], "centre_mm": round(c_mm, 1), "computed_mm": round(L, 1),
            "standard_mm": std, "centre_for_standard_mm": round(c_std, 1),
            "note": ("stock loop; tension with the slotted shaft holes (+-3 mm)" if abs(c_std - c_mm) <= 3 else
                     f"no stock loop within slot range: set the link to {c_std / 1000:.3f} m or use an "
                     "F624ZZ idler tensioner")}


BOM_SPECS = {
    "nema17": ("NEMA 17 stepper 17HS4401", "1.7 A, ~0.40-0.45 N m holding, 42.3x42.3x40 mm, 5 mm shaft", 9.0),
    "gt2_20t": ("GT2 20T pulley", "5 mm bore, 6 mm belt, aluminium", 1.0),
    "608-2RS": ("608-2RS ball bearing", "8x22x7 mm, sealed", 0.4),
    "688-2RS": ("688-2RS ball bearing", "8x16x5 mm, sealed", 0.5),
    "51105": ("51105 thrust ball bearing", "25x42x11 mm", 2.0),
    "shaft_collar_8": ("Shaft collar 8 mm", "set-screw collar, 8 mm bore", 0.5),
    "M3x10": ("M3x10 socket head cap screw", "ISO 4762 / DIN 912, steel", 0.04),
    "M3x16": ("M3x16 socket head cap screw", "ISO 4762 / DIN 912, steel", 0.05),
    "eva_foam_liner": ("EVA foam sheet 4 mm", "self-adhesive, cut to the cup liner (inner ring + disc)", 3.0),
    "KW12-3": ("KW12-3 micro switch (homing)", "12.8x5.8x6.5 mm, roller-less lever, 2x M2 holes 6.5 mm apart, "
               "wire NO to the endstop pin (INPUT_PULLUP)", 0.3),
    "A3144": ("A3144 hall sensor (homing)", "unipolar, open collector (use INPUT_PULLUP), 4.5-24 V, TO-92S", 0.3),
    "magnet_5x2": ("Neodymium disc magnet 5x2 mm", "N52, glued into a 5.2 mm pocket, south pole facing the A3144", 0.1),
    "M2x10": ("M2x10 screw", "self-tapping into the printed part, for the KW12-3 switches", 0.03),
    "LM4UU": ("LM4UU linear ball bearing", "4x8x12 mm, pressed into the cup-shell lugs (sprung cup slide)", 0.6),
    "shaft_collar_4": ("Shaft collar 4 mm", "set-screw collar, 4 mm bore, ~10 mm OD x 5 mm; slide front stop", 0.6),
    "oring_4x1.5": ("NBR O-ring 4 x 1.5 mm", "on each slide rod between lug and collar: front-stop cushion", 0.05),
    "bumper_12x3.5": ("Rubber bumper foot 12.7 x 3.5 mm", "self-adhesive, cylindrical (3M Bumpon-style); slide rear "
                      "travel stop, stuck to the hand plate under the cup bottom", 0.1),
    "M3x6_grub": ("M3x6 set screw", "ISO 4026 cup point, into a heat-set insert; 2 clamp the slide rods in the hand "
                  "bosses, 2 press the felt brake pads in the cup lugs", 0.05),
    "felt_pad_5x3": ("Wool felt sheet 3 mm", "punch 5 mm pads (2 + spares) for the slide friction brake; "
                     "drag about 1.5 N per rod, set by the M3 screw (estimate, measure with a scale)", 1.0),
    "net_pocket": ("Soft nylon net / mesh fabric", "~300x300 mm, 2-5 mm mesh (ball-return or laundry net); "
                   "sewn as a slack pocket, zip-tied to the cup ribs; restitution 0.15 is an estimate - drop-test it", 4.0),
}


INSERT_SCREWS = ("screw_tower", "screw_spine", "screw_spacer", "screw_shoulder_pulley", "screw_forearm_pulley",
                 "screw_hand_pulley", "screw_cup", "screw_base_plate", "grub_slide", "brake_screw")


def bom_rows(D: Design) -> list[dict]:
    counts: dict[str, int] = {}
    shafts: dict[str, int] = {}
    belts: dict[str, int] = {}
    used: dict[str, set] = {}
    for p in D.parts:
        if p.kind == PRINTED or p.ref == "KW12-3_lever":
            continue
        key = p.ref
        if key.startswith(("shaft_8x", "rod_4x")):
            shafts[key] = shafts.get(key, 0) + 1
        elif key.startswith("gt2_loop_"):
            belts[key] = belts.get(key, 0) + 1
        else:
            counts[key] = counts.get(key, 0) + 1
        used.setdefault(key, set()).add(p.body)
    src = "Amazon/AliExpress"
    rows = []

    def row(item, qty, spec, used_for, cost, source=src):
        rows.append({"item": item, "qty": qty, "spec": spec, "used_for": used_for, "source": source,
                     "est_unit_usd": cost})

    for key in ("nema17", "gt2_20t", "51105", "608-2RS", "688-2RS", "shaft_collar_8"):
        if key in counts:
            n, s, c = BOM_SPECS[key]
            row(n, counts[key], s, ", ".join(sorted(used[key])), c)
    for key, n in sorted(belts.items()):
        L = key.split("_")[-1]
        b = [x for x in D.belts if str(x["standard_mm"]) == L]
        row(f"GT2 closed-loop belt {L} mm", n, f"6 mm wide, 2 mm pitch, {L} mm loop (computed "
            f"{', '.join(str(x['computed_mm']) for x in b)} mm)", ", ".join(x["joint"] for x in b), 2.0)
    for key, n in sorted(shafts.items()):
        L = key.split("x")[-1]
        if key.startswith("rod_4x"):
            row(f"Steel rod 4 mm x {L} mm", n, f"hardened chrome linear rod h6, cut from 4 x {100 if int(L) <= 100 else 200} "
                "mm stock; sprung-cup slide", ", ".join(sorted(used[key])), 1.5)
            continue
        row(f"Steel shaft 8 mm x {L} mm", n, "h8 linear rod, cut from a 330 mm rod", ", ".join(sorted(used[key])), 2.0)
    for key in ("M3x10", "M3x16"):
        if key in counts:
            n, s, c = BOM_SPECS[key]
            row(n, counts[key] + 4, s + " (+4 spare)", "motor mounts, spacers, pulleys, tower", c)
    n_ins = sum(1 for p in D.parts if p.name.startswith(INSERT_SCREWS))
    row("M3 brass heat-set insert", n_ins + 4, "M3 x 5.7 mm, for printed parts (+4 spare)", "printed screw bosses", 0.05)
    row("M4x12 screw + washer", 4, "table mounting through the base plate", "base", 0.08)
    for key in ("eva_foam_liner", "net_pocket"):
        if key in counts:
            n, s, c = BOM_SPECS[key]
            row(n, 1, s, "cup liner", c)
    if "net_pocket" in counts:
        row("Zip ties 2.5x100 mm", 20, "nylon", "net pocket to cup ribs", 0.02)
    sl = D.info.get("slide")
    if sl:
        sp = sl["spring"]
        ref = next(x["ref"] for x in SPRINGS if x["id"] == sp["id"])
        row(f"Compression spring {sp['id']}", counts.get(ref, 0) + 1,
            f"{sp['material']}, wire {sp['wire_mm']} mm, OD {sp['od_mm']} mm, free length {sp['free_mm']:g} mm, "
            f"{sp['rate_n_per_mm']} N/mm, min working length {sp['min_work_mm']} mm ({sp['load_at_min_n']} N); one per "
            f"rod, {sl['n_springs']} in parallel = {sl['k_hw_n_per_m']:.0f} N/m (+1 spare)", "sprung cup slide", 1.2,
            source=f"RS Components ({sp['source']})")
        for key in ("LM4UU", "shaft_collar_4", "oring_4x1.5", "bumper_12x3.5", "M3x6_grub", "felt_pad_5x3"):
            if key in counts:
                n, spec, c = BOM_SPECS[key]
                extra = 2 if key in ("oring_4x1.5", "bumper_12x3.5") else 0
                if key == "felt_pad_5x3":
                    row(n, 1, spec, "sprung cup slide (friction brake)", c)
                    continue
                row(n, counts[key] + extra, spec + (f" (+{extra} spare)" if extra else ""), "sprung cup slide", c)
    row("A4988 stepper driver", 4, "with heatsink; set Vref for 1.2-1.5 A", "electronics", 1.5)
    row("Arduino Uno + CNC Shield V3", 1, "GRBL-style shield, 4 driver sockets", "electronics", 12.0)
    row("12 V 5 A power supply", 1, "barrel or screw terminal", "electronics", 10.0)
    for key, extra in (("KW12-3", 0), ("A3144", 1), ("magnet_5x2", 2), ("M2x10", 2)):
        if key in counts:
            n, sp, c = BOM_SPECS[key]
            row(n, counts[key] + extra, sp + (f" (+{extra} spare)" if extra else ""), ", ".join(sorted(used[key])), c)
    if "KW12-3" in counts or "A3144" in counts:
        row("3-core sensor cable 26 AWG", 3, "metres; Dupont ends; the wrist switch lead runs along the arm", "homing", 0.5)
    row("Stepper cable 4-pin 1 m", 4, "JST-XH / Dupont", "electronics", 1.0)
    return rows
