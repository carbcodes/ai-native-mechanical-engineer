"""style: quad_frame — 3D-printed true-X quadcopter frame (the `drone` example).

Parts: 4 arms (one printed ref, qty 4) sandwiched into edge slots of the bottom plate,
bottom plate (arm sockets, stack holes, battery strap slots), top plate, purchased
standoffs/screws and the electronics from hw/propulsion.yaml. Outputs mirror `cad build`
(model.step/stl/glb, stl/, print_list.csv, bom.csv, mass_props.json, thumb.png, summary.md).
All masses and thrust numbers are estimates until a datasheet replaces them."""

from __future__ import annotations

import csv
import json
import math
import time
from pathlib import Path

from ..events import Events
from ..project import Project, load_yaml

PRINTED, PURCHASED = "printed", "purchased"
DENSITY_KG_PER_MM3 = {"PETG": 1.27e-6, "PLA": 1.24e-6, "ABS": 1.05e-6, "nylon": 1.15e-6}
PETG_YIELD_MPA = 50.0        # printed-PETG yield, estimate class value
MIN_GAP_MM = 5.0
G = 9.81

COLORS = {
    "arm": (0.30, 0.55, 0.85, 1.0), "plate": (0.22, 0.24, 0.28, 1.0),
    "standoff": (0.75, 0.65, 0.25, 1.0), "screw": (0.60, 0.60, 0.65, 1.0),
    "motor": (0.10, 0.10, 0.12, 1.0), "prop": (0.85, 0.45, 0.10, 1.0),
    "electronics": (0.15, 0.45, 0.25, 1.0), "battery": (0.55, 0.15, 0.15, 1.0),
    "other": (0.7, 0.7, 0.72, 1.0),
}

DEFAULTS = {
    "wheelbase_mm": 220,
    "arm": {"width_mm": 14, "thickness_mm": 6},
    "plates": {"bottom_mm": 3, "top_mm": 2, "standoff_mm": 25},
    "stack_mm": 30.5, "motor_mount_mm": 16, "prop_in": 5,
    "material": "PETG", "infill": 0.4,
}
# where arm tabs plug in, and where the visible arm starts (radial mm along each diagonal)
SOCKET_R = (20, 46)
ARM_R = (38, None)          # outer end = motor radius + pad
PLATE_HALF, PLATE_CHAMFER, TOP_HALF, TOP_CHAMFER = 34, 16, 30, 12
STRAP_SLOTS = (22.0, 2.5)   # battery strap slots: length x width


def _params(project: Project, variant: str) -> dict:
    p = dict(DEFAULTS)
    raw = project.params(variant) or {}
    for k, v in raw.items():
        if isinstance(v, dict) and isinstance(p.get(k), dict):
            p[k] = {**p[k], **v}
        else:
            p[k] = v
    return p


def _octagon(half: float, chamfer: float):
    h, c = half, chamfer
    return [(h, h - c), (h - c, h), (-(h - c), h), (-h, h - c), (-h, -(h - c)),
            (-(h - c), -h), (h - c, -h), (h, -(h - c))]


def _plate(half, chamfer, z0, t):
    from build123d import Location, Polygon, extrude
    return extrude(Polygon(*_octagon(half, chamfer)), amount=t).move(Location((0, 0, z0)))


def _diag_slot(r0, r1, w, z0, t, angle):
    """Box slot along diagonal `angle` (deg) from radius r0 to r1."""
    from build123d import Box, Pos, Rot
    L = r1 - r0
    s = Box(L, w, t)
    return Rot(0, 0, angle) * Pos(((r0 + r1) / 2, 0, z0 + t / 2)) * s


def _arm_shape(p, angle, motor_r):
    """One arm: a 6 mm main beam plus a thin root tab that plugs into the bottom plate slot."""
    from build123d import Box, Cylinder, Pos, Rot
    w, t = p["arm"]["width_mm"], p["arm"]["thickness_mm"]
    bt = p["plates"]["bottom_mm"]
    r0, r1 = ARM_R[0], motor_r + 8
    main = Rot(0, 0, angle) * Pos(((r0 + r1) / 2, 0, bt + t / 2)) * Box(r1 - r0, w, t)
    tab = Rot(0, 0, angle) * Pos(((SOCKET_R[0] + SOCKET_R[1]) / 2, 0, 0.25 + (bt - 0.5) / 2)) \
        * Box(SOCKET_R[1] - SOCKET_R[0], w - 0.2, bt - 0.5)
    arm = main + tab
    # motor mount: centre shaft clearance + 4x M3 on a motor_mount_mm square
    m = p["motor_mount_mm"] / 2
    cuts = [Rot(0, 0, angle) * Pos((motor_r, 0, bt + t / 2)) * Cylinder(2.5, t + 2)]
    for dx in (-m, m):
        for dy in (-m, m):
            cuts.append(Rot(0, 0, angle) * Pos((motor_r + dx, dy, bt + t / 2)) * Cylinder(1.6, t + 2))
    for cx in cuts:
        arm -= cx
    return arm


def _electronics(path: Path) -> dict:
    """Propulsion/electronics table from hw/propulsion.yaml; all numbers are `value_type: estimate`."""
    hw = load_yaml(path) if path.exists() else {}
    return {k: (v or {}) for k, v in (hw or {}).items() if isinstance(v, dict)}


def build_quad_frame(project: Project, variant: str, ev: Events) -> dict:
    from build123d import Box, Color, Compound, Cylinder, Pos, Rot, export_gltf, export_step, export_stl

    from .render import render_parts_png, tessellate_parts

    task = f"cad-{variant}"
    t0 = time.time()
    vdir = project.variant_dir(variant)
    p = _params(project, variant)
    ev.emit("task.started", task=task)

    wb = p["wheelbase_mm"]
    motor_r = wb / 2
    a = motor_r / math.sqrt(2)
    motors_xy = [(a, a), (-a, a), (-a, -a), (a, -a)]   # arm_i = 45 + 90*i degrees
    prop_r = p["prop_in"] * 25.4 / 2
    prop = _electronics(project.path("hw", "propulsion.yaml"))
    mat = p["material"]
    rho = DENSITY_KG_PER_MM3.get(mat, DENSITY_KG_PER_MM3["PETG"])
    bt, tt, so = p["plates"]["bottom_mm"], p["plates"]["top_mm"], p["plates"]["standoff_mm"]
    stack = p["stack_mm"] / 2

    ev.progress(task, "building frame solids", 0.1)

    # parts: (name, ref, kind, color_key, shape, mass_kg | None)
    parts = []
    arm_shape = _arm_shape(p, 45, motor_r)
    for i in range(4):
        s = Rot(0, 0, 90 * i) * arm_shape
        s.label, s.color = f"arm_{i + 1}", Color(*COLORS["arm"])
        parts.append(dict(name=f"arm_{i + 1}", ref="arm", kind=PRINTED, color="arm", shape=s))

    bottom = _plate(PLATE_HALF, PLATE_CHAMFER, 0, bt)
    for i in range(4):
        bottom -= _diag_slot(SOCKET_R[0], SOCKET_R[1] + 4, p["arm"]["width_mm"] + 0.4, -0.5, bt + 1, 45 + 90 * i)
    for sx in (-1, 1):                      # battery strap slots along the battery (x) axis
        bottom -= Pos((18 * sx, 0, bt / 2)) * Box(STRAP_SLOTS[1], STRAP_SLOTS[0], bt + 1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            bottom -= Pos((stack * sx, stack * sy, bt / 2)) * Cylinder(1.6, bt + 1)
    bottom.label, bottom.color = "bottom_plate", Color(*COLORS["plate"])
    parts.append(dict(name="bottom_plate", ref="bottom_plate", kind=PRINTED, color="plate", shape=bottom))

    top = _plate(TOP_HALF, TOP_CHAMFER, bt + so, tt)
    for sx in (-1, 1):
        for sy in (-1, 1):
            top -= Pos((stack * sx, stack * sy, bt + so + tt / 2)) * Cylinder(1.6, tt + 1)
    top.label, top.color = "top_plate", Color(*COLORS["plate"])
    parts.append(dict(name="top_plate", ref="top_plate", kind=PRINTED, color="plate", shape=top))

    def buy(name, ref, shape, mass_g, color):
        shape.label, shape.color = name, Color(*COLORS.get(color, COLORS["other"]))
        parts.append(dict(name=name, ref=ref, kind=PURCHASED, color=color, shape=shape,
                          mass_kg=mass_g / 1000 if mass_g else None))

    for i, (sx, sy) in enumerate([(1, 1), (1, -1), (-1, 1), (-1, -1)]):
        buy(f"standoff_{i + 1}", "m3x25_standoff",
            Pos((stack * sx, stack * sy, bt + so / 2)) * Cylinder(2.75, so), 1.5, "standoff")
        buy(f"stack_screw_{i + 1}", "M3x6",
            Pos((stack * sx, stack * sy, bt + so + tt + 1.5)) * Cylinder(1.5, 3), 0.5, "screw")
    mot_g = float(prop.get("motors", {}).get("mass_g", 31))
    prop_g = float(prop.get("props", {}).get("mass_g", 4.5))
    for i, (x, y) in enumerate(motors_xy):
        z = bt + p["arm"]["thickness_mm"]
        buy(f"motor_{i + 1}", "motor_2306",
            Pos((x, y, z + 2.5)) * Cylinder(11.5, 5) + Pos((x, y, z + 8)) * Cylinder(8.5, 6), mot_g, "motor")
        buy(f"prop_{i + 1}", "prop_5x4.3x3", Pos((x, y, z + 15)) * Cylinder(prop_r, 0.8), prop_g, "prop")
    esc_g = float(prop.get("esc", {}).get("mass_g", 12))
    fc_g = float(prop.get("fc", {}).get("mass_g", 8))
    rx_g = float(prop.get("receiver", {}).get("mass_g", 3))
    vtx = prop.get("camera_vtx", {})
    vtx_g = float(vtx.get("mass_g", 20))
    bat_g = float(prop.get("battery", {}).get("mass_g", 160))
    buy("esc", "esc_35a_4in1", Pos((0, 0, bt + 4)) * Box(36, 36, 6), esc_g, "electronics")
    buy("fc", "fc_f405", Pos((0, 0, bt + 12)) * Box(36, 36, 6), fc_g, "electronics")
    buy("receiver", "rx_nano", Pos((0, -TOP_HALF + 8, bt + 4)) * Box(11, 18, 5), rx_g, "electronics")
    if vtx:
        buy("camera_vtx", "cam_vtx", Pos((0, TOP_HALF - 12, bt + 8)) * Box(19, 19, 14), vtx_g, "electronics")
    buy("battery", "lipo_4s_1300", Pos((0, 0, -14)) * Box(72, 36, 26), bat_g, "battery")

    ev.progress(task, "exporting step/stl/glb", 0.4)
    asm = Compound(children=[x["shape"] for x in parts])
    asm.label = f"quad_{variant}"
    files: dict[str, str] = {}
    export_step(asm, vdir / "model.step")
    files["step"] = "model.step"
    export_stl(asm, vdir / "model.stl", tolerance=0.2, angular_tolerance=0.3)
    files["stl"] = "model.stl"
    export_gltf(asm, vdir / "model.glb", binary=True, linear_deflection=0.3, angular_deflection=0.3)
    files["glb"] = "model.glb"

    ev.progress(task, "exporting printable STLs, print_list.csv, bom.csv", 0.6)
    stl_dir = vdir / "stl"
    stl_dir.mkdir(exist_ok=True)
    for old in stl_dir.glob("*.stl"):
        old.unlink()
    printed_refs = {}
    for x in parts:
        if x["kind"] == PRINTED:
            printed_refs.setdefault(x["ref"], []).append(x)
    for ref, xs in printed_refs.items():
        s = xs[0]["shape"]
        bb = s.bounding_box()
        s = s.moved(Pos((-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z)))
        export_stl(s, stl_dir / f"{ref}.stl", tolerance=0.05, angular_tolerance=0.2)
    files["stl_dir"] = "stl"

    def mass(x):
        if x.get("mass_kg") is not None:
            return x["mass_kg"]
        return x["shape"].volume * rho * (0.35 + 0.65 * p["infill"] if x["kind"] == PRINTED else 1.0)

    rows = []
    for ref, xs in printed_refs.items():
        g = mass(xs[0]) * 1000
        rows.append({"part": ref, "qty": len(xs), "material": mat, "orientation": "flat, no supports",
                     "est_grams": round(g, 1), "est_grams_total": round(g * len(xs), 1),
                     "infill": f"{p['infill']:.0%}", "volume_cm3": round(xs[0]["shape"].volume / 1000, 1),
                     "stl": f"stl/{ref}.stl"})
    with open(vdir / "print_list.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    files["print_list"] = "print_list.csv"

    src = "estimate class spec (see hw/propulsion.yaml)"
    bom = [
        {"item": "Motor 2306 2400KV", "qty": 4, "spec": f"~{mot_g:g} g each, {prop.get('motors', {}).get('max_thrust_kgf', 1.1)} kgf max est. on 4S",
         "used_for": "arms", "source": src, "est_unit_usd": 13.0},
        {"item": "Prop 5x4.3x3 tri-blade", "qty": 8, "spec": f"~{prop_g:g} g each (+4 spare)", "used_for": "motors",
         "source": src, "est_unit_usd": 0.6},
        {"item": "4-in-1 ESC 35 A 30.5 mm", "qty": 1, "spec": f"~{esc_g:g} g", "used_for": "stack",
         "source": src, "est_unit_usd": 45.0},
        {"item": "F405 flight controller 30.5 mm", "qty": 1, "spec": f"~{fc_g:g} g", "used_for": "stack",
         "source": src, "est_unit_usd": 35.0},
        {"item": "4S 1300 mAh LiPo", "qty": 1, "spec": f"~{bat_g:g} g", "used_for": "battery",
         "source": src, "est_unit_usd": 22.0},
        {"item": "Nano receiver (ELRS)", "qty": 1, "spec": f"~{rx_g:g} g", "used_for": "stack",
         "source": src, "est_unit_usd": 14.0},
    ]
    if vtx:
        bom.append({"item": "Micro camera + VTX", "qty": 1, "spec": f"~{vtx_g:g} g (optional)",
                    "used_for": "front of stack", "source": src, "est_unit_usd": 40.0})
    bom += [
        {"item": "M3x25 standoff", "qty": 4, "spec": "aluminium or brass hex", "used_for": "plates",
         "source": "hardware", "est_unit_usd": 0.3},
        {"item": "M3 screw assortment", "qty": 20, "spec": "M3x6/M3x8 (+spares)", "used_for": "stack, motors",
         "source": "hardware", "est_unit_usd": 0.1},
        {"item": "Battery strap 20x250 mm", "qty": 2, "spec": "non-slip", "used_for": "battery",
         "source": "hardware", "est_unit_usd": 1.0},
    ]
    with open(vdir / "bom.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(bom[0]))
        w.writeheader()
        w.writerows(bom)
    files["bom"] = "bom.csv"

    ev.progress(task, "mass props and stats", 0.75)
    def center(x):
        bb = x["shape"].bounding_box()
        return [((bb.min.X + bb.max.X) / 2) / 1000, ((bb.min.Y + bb.max.Y) / 2) / 1000,
                ((bb.min.Z + bb.max.Z) / 2) / 1000]

    frame_kinds = {"arm", "plate", "standoff", "screw"}
    pm = [(mass(x), center(x), x["name"]) for x in parts]
    frame_mass = sum(m for (m, c, n), x in zip(pm, parts) if x["color"] in frame_kinds)
    auw = sum(m for m, _, _ in pm)
    cog = [sum(m * c[i] for m, c, _ in pm) / auw for i in range(3)]
    mp = {"frame_mass_kg": round(frame_mass, 4), "auw_kg": round(auw, 4),
          "cog_m": [round(c, 4) for c in cog],
          "parts": {x["name"]: round(mass(x), 4) for x in parts},
          "note": "all masses from estimates (printed: volume x density x infill; purchased: hw/propulsion.yaml)"}
    (vdir / "mass_props.json").write_text(json.dumps(mp, indent=1))
    files["mass_props"] = "mass_props.json"

    # gaps: prop circle vs the nearest *other* frame part's plan-view vertices
    def verts_xy(x):
        try:
            return [(v.X, v.Y) for v in x["shape"].vertices()]
        except Exception:  # noqa: BLE001
            return []

    frame_parts = [x for x in parts if x["kind"] == PRINTED]
    tip_gap = min(math.dist(motors_xy[i], motors_xy[j])
                  for i in range(4) for j in range(i + 1, 4)) - 2 * prop_r
    # prop circle (horizontal, at the motor) vs every printed part except that motor's own arm
    frame_gap = min(min(math.dist(m, v) for x in frame_parts if x["name"] != f"arm_{i + 1}"
                        for v in verts_xy(x)) for i, m in enumerate(motors_xy)) - prop_r
    warnings = []
    if frame_gap < MIN_GAP_MM or tip_gap < MIN_GAP_MM:
        warnings.append(f"prop clearance under {MIN_GAP_MM:g} mm (to frame {frame_gap:.1f}, "
                        f"tip-to-tip {tip_gap:.1f})")
    max_thrust_kgf = float(prop.get("motors", {}).get("max_thrust_kgf", 1.1)) * 4
    tw = max_thrust_kgf / auw
    root_r = (2 * PLATE_HALF - PLATE_CHAMFER) / math.sqrt(2)      # plate extent along a diagonal
    lever_m = (motor_r - root_r) / 1000
    w, t = p["arm"]["width_mm"], p["arm"]["thickness_mm"]
    S = w * t * t / 6 * 1e-9                                      # section modulus, m^3
    sigma = (max_thrust_kgf / 4 * G * lever_m) / S / 1e6          # MPa, per arm at full thrust
    stats = {
        "style": "quad_frame", "estimates": True,
        "note": "all values below are computed from estimates",
        "wheelbase_mm": wb,
        "prop_tip_gap_mm": round(tip_gap, 1),
        "prop_to_frame_gap_mm": round(frame_gap, 1),
        "frame_mass_kg": round(frame_mass, 3), "auw_kg": round(auw, 3),
        "max_thrust_kgf": round(max_thrust_kgf, 2),
        "thrust_to_weight": round(tw, 2),
        "hover_thrust_fraction": round(auw / max_thrust_kgf, 3),
        "arm_root_stress_mpa": round(sigma, 1),
        "arm_root_safety_factor": round(PETG_YIELD_MPA / sigma, 1),
        "printed_parts": sum(r["qty"] for r in rows), "printed_stls": len(rows),
        "print_grams": round(sum(r["est_grams_total"] for r in rows), 0),
        "purchased_lines": len(bom),
        "est_purchased_usd": round(sum(r["qty"] * r["est_unit_usd"] for r in bom), 0),
        "warnings": warnings,
    }

    ev.progress(task, "rendering thumbnail", 0.85)
    meshes = tessellate_parts([x["shape"] for x in parts], tol_mm=0.4, angular=0.15)
    render_parts_png(meshes, vdir / "thumb.png", "top", size_px=900)
    files["thumb"] = "thumb.png"

    summary = f"""# CAD {variant} (quad_frame)

3D-printed true-X quadcopter frame from `design/{variant}/params.yaml`. Every number here is
**computed from estimates** (see hw/propulsion.yaml).

| What | Where |
|---|---|
| Assembly | model.step, model.glb, model.stl |
| Printable parts | stl/*.stl ({len(rows)} files), print_list.csv |
| Purchased parts | bom.csv ({len(bom)} lines, about ${stats['est_purchased_usd']:.0f}, estimate) |

- Wheelbase {wb:g} mm diagonal; {p['prop_in']} inch props; {mat} at {p['infill']:.0%} infill.
- Prop tip-to-tip gap {stats['prop_tip_gap_mm']} mm; prop-to-frame gap {stats['prop_to_frame_gap_mm']} mm
  (warn below {MIN_GAP_MM:g} mm).
- Frame mass {frame_mass * 1000:.0f} g; AUW {auw * 1000:.0f} g (incl. battery{', camera/VTX' if vtx else ''}).
- Max thrust ~{max_thrust_kgf:.1f} kgf total -> thrust/weight {tw:.1f} (requirement:
  >= {project.requirements().get('flight', {}).get('thrust_to_weight_min', '?')}); hover at
  ~{auw / max_thrust_kgf:.0%} throttle.
- Arm root bending at full thrust (cantilever, estimate): {sigma:.1f} MPa vs PETG ~{PETG_YIELD_MPA:.0f} MPa
  -> safety factor {PETG_YIELD_MPA / sigma:.1f}.

Rebuild: `mechy cad build {variant}`.

Not verified: motor thrust, component masses, PETG strength and printed stiffness are all
estimates; check datasheets and weigh parts before flying.

Warnings / open decisions:
{chr(10).join('- ' + x for x in warnings) or '- none'}
"""
    (vdir / "summary.md").write_text(summary)
    files["summary"] = "summary.md"
    for f in files.values():
        if (vdir / f).is_file():
            ev.file_written(vdir / f)
    out = {"variant": variant, "dir": ev.rel(vdir), "files": {k: ev.rel(vdir / v) for k, v in files.items()},
           "stats": stats, "duration_s": round(time.time() - t0, 2)}
    ev.emit("task.done", task=task, summary=ev.rel(vdir / "summary.md"))
    return out
