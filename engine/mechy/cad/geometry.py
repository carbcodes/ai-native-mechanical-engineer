"""`style: simple` build123d generator for the 4-DOF catching arm (primitive blocks).

Geometry is built in millimetres (build123d's default), posed at the arm's ready pose.
Each part keeps a label and colour so the GLB shows them separately in the app.
"""

from __future__ import annotations

import numpy as np
from build123d import Box, Color, Compound, Cylinder, Location, Rot, Shape

from ..arm_model import NEMA17_LEN_M, NEMA17_SIDE_M, ArmModel

MM = 1000.0
COLORS = {
    "frame": Color(0.85, 0.86, 0.88),
    "link": Color(0.95, 0.55, 0.15),
    "motor": Color(0.15, 0.15, 0.17),
    "pulley": Color(0.65, 0.68, 0.72),
    "cup": Color(0.20, 0.55, 0.85),
}
PULLEY_R_MOTOR_MM = 6.4          # GT2 20T pulley pitch radius


def _tag(shape: Shape, label: str, kind: str) -> Shape:
    shape.label = label
    shape.color = COLORS[kind]
    return shape


def nema17(label: str) -> Shape:
    """NEMA 17 block, 42.3 mm square, 40 mm long, shaft along +Z from the face at z=0."""
    s = NEMA17_SIDE_M * MM
    body = Box(s, s, NEMA17_LEN_M * MM).moved(Location((0, 0, -NEMA17_LEN_M * MM / 2)))
    shaft = Cylinder(2.5, 22).moved(Location((0, 0, 11)))
    boss = Cylinder(11, 2).moved(Location((0, 0, 1)))
    return _tag(body.fuse(shaft).fuse(boss), label, "motor")


def pulley(radius_mm: float, width_mm: float, label: str) -> Shape:
    return _tag(Cylinder(radius_mm, width_mm), label, "pulley")


def cup(diameter_m: float, depth_m: float, wall_mm: float = 2.0) -> Shape:
    """Cup with its opening along +Z, centred on the origin (bottom at -depth/2)."""
    r = diameter_m / 2 * MM
    d = depth_m * MM
    outer = Cylinder(r + wall_mm, d + wall_mm).moved(Location((0, 0, -wall_mm / 2)))
    inner = Cylinder(r, d + 1).moved(Location((0, 0, 0.5 + wall_mm / 2)))
    shell = outer - inner
    return shell.moved(Location((0, 0, 0)))


def build_arm(arm: ArmModel, q=None, bodies: dict | None = None) -> tuple[Compound, list[Shape]]:
    """Return (assembly compound, list of labelled parts) posed at joint angles q (rad).
    Dispatches on params `style`: "simple" (this module) or "belt_arm" (belt_arm.py).
    `bodies` (simple style), if given, is filled with {body name: [posed parts]} for the
    animatable GLB (contracts section 11)."""
    q = arm.ready_pose() if q is None else np.asarray(q, float)
    if getattr(arm, "style", "simple") == "belt_arm":
        from .belt_arm import build_design
        return build_design(arm).posed(q)
    deg = np.degrees(q)
    h = arm.base_height * MM
    L1, L2, L3 = arm.upper * MM, arm.fore * MM, arm.hand * MM
    parts: list[Shape] = []
    groups = bodies if bodies is not None else {}

    # --- fixed base: housing with the yaw motor inside, hanging below the turntable
    base_r = 80.0
    housing_h = 45.0
    parts.append(_tag(Cylinder(base_r, housing_h).moved(Location((0, 0, housing_h / 2))),
                      "base_housing", "frame"))
    # base motor sits beside the axis, shaft up, driving the turntable with a belt
    parts.append(nema17("motor_base").moved(Location((48, 0, housing_h - 2))))
    parts.append(pulley(PULLEY_R_MOTOR_MM, 8, "pulley_base_motor").moved(Location((48, 0, housing_h + 14))))

    # --- turntable (rotates with yaw)
    yaw = Location((0, 0, 0)) * Rot(0, 0, deg[0])
    tt_z = housing_h + 2
    tt_th = 8.0
    tt = []
    tt.append(_tag(Cylinder(72, tt_th).moved(Location((0, 0, tt_z + tt_th / 2))), "turntable", "frame"))
    tt.append(pulley(PULLEY_R_MOTOR_MM * arm.gear[0], 8, "pulley_base_joint").moved(Location((0, 0, tt_z - 4))))
    # shoulder tower: two cheek plates holding the shoulder axle at base_height
    tower_h = h - (tt_z + tt_th)
    for side, y in (("l", 26.0), ("r", -26.0)):
        tt.append(_tag(Box(40, 6, tower_h + 20).moved(
            Location((0, y, tt_z + tt_th + (tower_h + 20) / 2))), f"tower_{side}", "frame"))
    # shoulder / elbow / wrist motors at the base, shafts along Y, behind the tower
    if arm.motors_at_base:
        for i, name in enumerate(("shoulder", "elbow", "wrist")):
            mz = tt_z + tt_th + NEMA17_SIDE_M * MM / 2 + 1
            mx = -50.0
            my = (i - 1) * 45.0
            m = nema17(f"motor_{name}").moved(Location((mx, my, mz)) * Rot(90, 0, 0))
            tt.append(m)
            tt.append(pulley(PULLEY_R_MOTOR_MM, 7, f"pulley_{name}_motor").moved(
                Location((mx, my - 15, mz)) * Rot(90, 0, 0)))
    parts.extend(p.moved(yaw) for p in tt)
    groups["base"] = list(parts[:3])
    groups["turntable"] = list(parts[3:])

    # --- moving chain. Links are modelled along local +Z; contracts 7.1 angles are
    # elevation above horizontal (q1) and relative pitch (q2, q3), positive = up, so the
    # shoulder frame is tilted by 90 - q1 about +Y and later joints by -q about +Y.
    sh = yaw * Location((0, 0, h)) * Rot(0, 90 - deg[1], 0)
    beam_w, beam_t = 30.0, 18.0
    up = [
        _tag(Box(beam_t, beam_w, L1).moved(Location((0, 0, L1 / 2))), "upper_arm", "link"),
        pulley(PULLEY_R_MOTOR_MM * arm.gear[1], 8, "pulley_shoulder").moved(Rot(90, 0, 0)),
    ]
    parts.extend(p.moved(sh) for p in up)
    groups["upper_arm"] = list(parts[-len(up):])
    el = sh * Location((0, 0, L1)) * Rot(0, -deg[2], 0)
    fo = [
        _tag(Box(beam_t * 0.9, beam_w * 0.9, L2).moved(Location((0, 0, L2 / 2))), "forearm", "link"),
        pulley(PULLEY_R_MOTOR_MM * arm.gear[2], 7, "pulley_elbow").moved(Rot(90, 0, 0)),
    ]
    parts.extend(p.moved(el) for p in fo)
    groups["forearm"] = list(parts[-len(fo):])
    wr = el * Location((0, 0, L2)) * Rot(0, -deg[3], 0)
    cup_bottom = L3 - arm.cup_depth * MM / 2
    ha = [
        _tag(Box(beam_t * 0.8, beam_w * 0.8, max(cup_bottom, 5.0)).moved(
            Location((0, 0, max(cup_bottom, 5.0) / 2))), "hand", "link"),
        pulley(PULLEY_R_MOTOR_MM * arm.gear[3], 6, "pulley_wrist").moved(Rot(90, 0, 0)),
        _tag(cup(arm.cup_d, arm.cup_depth).moved(Location((0, 0, L3))), "cup", "cup"),
    ]
    parts.extend(p.moved(wr) for p in ha)
    groups["hand"] = list(parts[-len(ha):])
    for p in parts:
        if p.color is None:
            p.color = COLORS["frame"]
    asm = Compound(children=parts)
    asm.label = f"arm_{arm.name}"
    return asm, parts
