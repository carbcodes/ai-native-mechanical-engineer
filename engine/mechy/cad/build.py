"""`mechy cad build <variant>`: params.yaml -> arm.step, arm.stl, arm.glb, arm.xml, thumb.png."""

from __future__ import annotations

import json
import math
import runpy
import time
from pathlib import Path

import numpy as np

from ..arm_model import ArmModel
from ..events import Events
from ..project import Project


def _custom_model(vdir: Path, params: dict):
    """design/vN/model.py may define build(params) -> build123d Shape or list of Shapes."""
    mp = vdir / "model.py"
    if not mp.exists():
        return None
    ns = runpy.run_path(str(mp), run_name="mechy_model")
    fn = ns.get("build")
    if fn is None:
        raise RuntimeError(f"{mp} must define build(params) returning a build123d shape")
    res = fn(params)
    from build123d import Compound
    if isinstance(res, (list, tuple)):
        return Compound(children=list(res)), list(res)
    return res, [res]


def cad_build(project: Project, variant: str, events: Events | None = None) -> dict:
    from build123d import export_gltf, export_step, export_stl   # noqa: F401 (unused for ref_arm)

    from .geometry import build_arm
    from .glb import write_glb
    from .mjcf import build_mjcf
    from .render import render_parts_png, tessellate_parts

    ev = events or Events(project.root, quiet=True)
    if (project.params(variant) or {}).get("style") == "quad_frame":
        from .quad_frame import build_quad_frame
        return build_quad_frame(project, variant, ev)
    task = f"cad-{variant}"
    t0 = time.time()
    vdir = project.variant_dir(variant)
    hw = project.hardware()
    arm = ArmModel(project.params(variant), hw["motors"], hw["drivers"])   # mass props come from this build
    req = project.requirements().get("catch", {})
    ev.emit("task.started", task=task)

    ev.progress(task, "building solid model", 0.1)
    custom = _custom_model(vdir, arm.params)
    design = None
    files: dict[str, str] = {}
    if custom is not None:
        asm, parts = custom
    elif arm.style == "belt_arm":
        from .belt_arm import build_design
        design = build_design(arm)
        mp = design.mass_props()
        mp["motor_map"] = arm.motor_map()           # joint <-> motor angles and step counts for firmware
        mp["homing"] = design.info.get("homing", [])
        mp["homing_order"] = design.info.get("homing_order")
        (vdir / "mass_props.json").write_text(json.dumps(mp, indent=1))
        files["mass_props"] = "mass_props.json"
        arm.mass_props = mp
        asm, parts = design.posed(arm.ready_pose())
        ev.progress(task, "exporting printable STLs, print_list.csv, bom.csv", 0.25)
        design.export_stls(vdir / "stl")
        files["stl_dir"] = "stl"
        design.write_print_list(vdir / "print_list.csv")
        files["print_list"] = "print_list.csv"
        design.write_bom(vdir / "bom.csv")
        files["bom"] = "bom.csv"
    elif arm.style == "ref_arm":
        from .ref_arm import build_design as build_ref, glb_spec as ref_glb_spec, \
            posed_world_meshes as ref_posed, write_stl as write_binary_stl
        design = build_ref(arm)
        mp = design.mass_props()
        mp["motor_map"] = arm.motor_map()
        (vdir / "mass_props.json").write_text(json.dumps(mp, indent=1))
        files["mass_props"] = "mass_props.json"
        arm.mass_props = mp
        asm, parts = None, None
        ev.progress(task, "exporting vendor STLs, print_list.csv, bom.csv", 0.25)
        design.export_stls(vdir / "stl")
        files["stl_dir"] = "stl"
        design.write_print_list(vdir / "print_list.csv")
        files["print_list"] = "print_list.csv"
        design.write_bom(vdir / "bom.csv")
        files["bom"] = "bom.csv"
    else:
        asm, parts = build_arm(arm)
        if custom is None:
            from . import outputs
            ev.progress(task, "exporting printable STLs, print_list.csv, bom.csv", 0.25)
            outputs.export_stls(parts, vdir / "stl")
            files["stl_dir"] = "stl"
            outputs.write_csv(vdir / "print_list.csv", outputs.print_rows(parts))
            files["print_list"] = "print_list.csv"
            outputs.write_csv(vdir / "bom.csv", outputs.bom_rows(arm, dict(hw, drivers_doc=project.drivers_doc()), parts))
            files["bom"] = "bom.csv"
    ev.progress(task, "exporting STEP/STL/GLB", 0.4)
    glb_meshes = None
    if arm.style == "ref_arm" and custom is None:
        # vendor solids are meshes only — no STEP; arm.stl = the assembly posed at the ready pose
        glb_parts, glb_tree = ref_glb_spec(design)
        v_all, t_all, off = [], [], 0
        for v, t, rgba in ref_posed(design, arm.ready_pose()):
            v_all.append(v * 1000)
            t_all.append(t + off)
            off += len(v)
        write_binary_stl(vdir / "arm.stl", np.vstack(v_all), np.vstack(t_all))
        files["stl"] = "arm.stl"
        glb_info = write_glb(vdir / "arm.glb", glb_parts, design.origins, design.rest_q(),
                             meta={"variant": variant, "style": arm.style, "kinematics": arm.kinematics},
                             tree=glb_tree)
        glb_meshes = ref_posed(design, arm.ready_pose())
    else:
        export_step(asm, vdir / "arm.step")
        files["step"] = "arm.step"
        export_stl(asm, vdir / "arm.stl", tolerance=0.2, angular_tolerance=0.3)
        files["stl"] = "arm.stl"
        if custom is None:
            # animatable GLB (contracts section 11): one node per moving body, origins on the axes
            glb_parts, origins_m = _glb_parts(arm, design)
            slide = design.info.get("slide") if design is not None else None
            glb_info = write_glb(vdir / "arm.glb", glb_parts, origins_m, arm.ready_pose(),
                                 meta={"variant": variant, "style": arm.style}, slide=slide)
            glb_meshes = _posed_meshes(glb_parts, origins_m, arm.ready_pose())
        else:
            export_gltf(asm, vdir / "arm.glb", binary=True, linear_deflection=0.3,
                        angular_deflection=0.3)
            glb_info = {"animatable": False}
    files["glb"] = "arm.glb"

    ev.progress(task, "writing MJCF", 0.7)
    xml = build_mjcf(arm, ball_diameter=float(req.get("ball_diameter_m", 0.067)),
                     ball_mass=float(req.get("ball_mass_kg", 0.057)))
    (vdir / "arm.xml").write_text(xml)
    files["mjcf"] = "arm.xml"
    import mujoco
    model = mujoco.MjModel.from_xml_path(str(vdir / "arm.xml"))  # validate

    ev.progress(task, "rendering thumbnail", 0.85)
    meshes = glb_meshes or tessellate_parts(parts, tol_mm=0.4, angular=0.15)
    render_parts_png(meshes, vdir / "thumb.png", "hero" if design is not None else "iso",
                     size_px=900 if design is not None else 640)
    files["thumb"] = "thumb.png"

    if asm is not None:
        bb = asm.bounding_box()
        bbox_max_z, bbox_xy = bb.max.Z / 1000, [(bb.max.X - bb.min.X) / 1000, (bb.max.Y - bb.min.Y) / 1000]
    else:
        vv = np.vstack([v for v, _, _ in ref_posed(design, arm.ready_pose())])
        bbox_max_z, bbox_xy = float(vv[:, 2].max()), [float(np.ptp(vv[:, 0])), float(np.ptp(vv[:, 1]))]
    moving_mass = float(sum(model.body_mass[model.body(n).id] for n in ("upper_arm", "forearm", "hand", "cup")))
    stats = {
        "reach_m": round(arm.reach, 3),
        "height_ready_m": round(bbox_max_z, 3),
        "footprint_m": [round(x, 3) for x in bbox_xy],
        "moving_mass_kg": round(moving_mass, 3),
        "total_mass_kg": round(float(model.body_subtreemass[0]) - float(req.get("ball_mass_kg", 0.057)), 3),
        "load_inertia_kgm2": [round(float(x), 5) for x in arm.load_inertia()],
        "gravity_torque_max_nm": [round(float(x), 3) for x in arm.gravity_torque_max()],
        "custom_model": custom is not None,
        "glb": glb_info,
        "style": "custom" if custom is not None else arm.style,
    }
    if design is not None:
        stats.update(_belt_stats(design, arm, model))
    if custom is None:
        from .outputs import write_loads
        write_loads(vdir / "loads.json", arm, float(req.get("ball_mass_kg", 0.057)))
        files["loads"] = "loads.json"
    summary = _ref_summary(variant, arm, stats, design) if arm.style == "ref_arm" else \
        (_belt_summary(variant, arm, stats, design) if design is not None else _summary(variant, arm, stats))
    (vdir / "summary.md").write_text(summary)
    files["summary"] = "summary.md"
    for f in files.values():
        if (vdir / f).is_file():
            ev.file_written(vdir / f)
    out = {"variant": variant, "dir": ev.rel(vdir), "files": {k: ev.rel(vdir / v) for k, v in files.items()},
           "stats": stats, "duration_s": round(time.time() - t0, 2)}
    ev.emit("task.done", task=task, summary=ev.rel(vdir / "summary.md"))
    return out


def _glb_parts(arm: ArmModel, design=None) -> tuple[list[dict], dict]:
    """Tessellated parts in their body frames (m) and the body origins (m) at q = 0."""
    from .glb import BODY_ALIAS, tessellate_local
    if design is not None:
        from .belt_arm import COLORS
        origins = {b: np.asarray(o, float) for b, o in design.origins.items()}
        items = [(p.name, p.body, p.shape, tuple(p.color or COLORS[p.kind]) + (1.0,)) for p in design.parts]
        if "slide" in design.info:             # sprung cup: cup parts ride on their own node
            alias = {"cup": "cup_slide"}
            origins["cup_slide"] = origins["cup"]
    else:
        from .geometry import build_arm
        groups: dict = {}
        build_arm(arm, np.zeros(4), bodies=groups)
        h, L1, L2, L3 = (x * 1000 for x in (arm.base_height, arm.upper, arm.fore, arm.hand))
        origins = {"base": np.zeros(3), "turntable": np.zeros(3), "upper_arm": np.array([0, 0, h]),
                   "forearm": np.array([L1, 0, h]), "hand": np.array([L1 + L2, 0, h]),
                   "cup": np.array([L1 + L2 + L3, 0, h])}
        items = []
        for body, shapes in groups.items():
            for k, s in enumerate(shapes):
                c = s.color
                rgba = tuple(c) if c is not None else (0.8, 0.8, 0.8, 1.0)
                items.append((s.label or f"{body}_{k}", body, s, rgba))
    if design is None or "slide" not in design.info:
        alias = BODY_ALIAS
    parts, seen = [], set()
    for name, body, shape, rgba in items:
        b = alias.get(body, body)
        mesh = tessellate_local(shape, origins[b])
        if mesh is None:
            continue
        while name in seen:
            name += "_"
        seen.add(name)
        parts.append({"name": name, "body": b, "v": mesh[0], "t": mesh[1], "rgba": rgba})
    return parts, {b: o / 1000 for b, o in origins.items() if b != "cup_slide"}


def _posed_meshes(parts: list[dict], origins_m: dict, q) -> list:
    """GLB part meshes moved to pose q (world, m), for the thumbnail renderer."""
    from .glb import body_transforms
    T = body_transforms(q, origins_m)
    return [(p["v"] @ T[p["body"]][:3, :3].T + T[p["body"]][:3, 3], p["t"], p["rgba"]) for p in parts]


def _summary(variant: str, arm: ArmModel, s: dict) -> str:
    g = arm.gear
    hold = [float(m["torque_curve"][0][1]) for m in arm.motor_specs]
    grav_motor = [s["gravity_torque_max_nm"][i] / g[i] / hold[i] for i in range(4)]
    return f"""# CAD {variant}

Built the 4-DOF catching arm from `design/{variant}/params.yaml`
({"custom model.py" if s["custom_model"] else "default generator"}).

- Reach (shoulder to cup centre): {s["reach_m"]} m; base height {arm.base_height} m.
- Links {arm.upper}/{arm.fore}/{arm.hand} m at {arm.lin_mass} kg/m; cup {arm.cup_d * 1000:.0f} mm x {arm.cup_depth * 1000:.0f} mm.
- Moving mass (links, pulleys, cup): {s["moving_mass_kg"]} kg; total {s["total_mass_kg"]} kg.
- Gear ratios {", ".join(f"{x:g}" for x in g)}; motors at base: {arm.motors_at_base}.
- Load inertia, arm stretched (kg m^2): {s["load_inertia_kgm2"]}.
- Gravity torque, arm stretched, as a fraction of holding torque at the motor:
  shoulder {grav_motor[1]:.2f}, elbow {grav_motor[2]:.2f}, wrist {grav_motor[3]:.2f}.

Files: arm.step, arm.stl (mm), arm.glb (m), arm.xml (MuJoCo, m), thumb.png.

Open issues: belt paths, bearings and fasteners are not modelled; motor blocks and
pulleys are placeholders; MJCF masses are estimates from link_mass_kg_per_m.
"""


def torque_budget(arm: ArmModel, ball_mass: float = 0.057, safety: float = 0.5) -> list[dict]:
    """Per motor: static gravity torque at its output pulley (arm stretched horizontally, ball in the
    cup; with belt pass-through that is C^-T tau, see ArmModel.motor_map) against holding torque x
    ratio x safety (standards rule 4), plus the speed-limited torque."""
    g = arm.gear
    grav = arm.motor_gravity_torque_max(ball_mass)
    grav_joint = arm.gravity_torque_max(ball_mass)
    rows = []
    for i, nm in enumerate(arm.joint_names):
        hold = float(arm.motor_specs[i]["torque_curve"][0][1])
        rps = arm.max_speed_rps(i)
        tc = np.asarray(arm.motor_specs[i]["torque_curve"], float)
        t_fast = float(np.interp(rps, tc[:, 0], tc[:, 1]))
        avail = hold * g[i] * safety
        rows.append({"joint": nm, "ratio": float(g[i]), "gravity_nm": round(float(grav[i]), 3),
                     "joint_gravity_nm": round(float(grav_joint[i]), 3),
                     "holding_x_ratio_nm": round(hold * g[i], 3), "budget_50pct_nm": round(avail, 3),
                     "margin": round(avail / grav[i], 2) if grav[i] > 1e-6 else None,
                     "pullout_at_max_speed_nm": round(t_fast * g[i], 3),
                     "max_joint_speed_dps": round(rps / g[i] * 360, 1)})
    return rows


def _belt_stats(design, arm: ArmModel, model) -> dict:
    rows = design.print_rows()
    bom = design.bom_rows()
    return {
        "printed_parts": sum(r["qty"] for r in rows),
        "printed_stls": len(rows),
        "print_grams": round(sum(r["est_grams_total"] for r in rows), 0),
        "purchased_lines": len(bom),
        "est_purchased_usd": round(sum(r["qty"] * r["est_unit_usd"] for r in bom), 0),
        "belts": design.belts,
        "body_masses_kg": {b: v["mass"] for b, v in arm.mass_props["bodies"].items()},
        "torque_budget": torque_budget(arm),
        "warnings": design.warnings,
    }


def _belt_summary(variant: str, arm: ArmModel, s: dict, design) -> str:
    tb = s["torque_budget"]
    belts = "\n".join(f"| {b['joint']} | {b['teeth'][0]}T-{b['teeth'][1]}T | {b['centre_mm']} | {b['computed_mm']} | "
                      f"{b['standard_mm']} |" for b in s["belts"])
    torque = "\n".join(f"| {r['joint']} | {r['ratio']:g} | {r['joint_gravity_nm']} | {r['gravity_nm']} | "
                       f"{r['budget_50pct_nm']} | {r['margin'] if r['margin'] is not None else '-'} | "
                       f"{r['max_joint_speed_dps']} |" for r in tb)
    mm = arm.motor_map()
    homing = "\n".join(f"| {h['joint']} | {h['sensor']} | {h['mount']} | {h['trigger']} | {h['homes']} |"
                        for h in design.info.get("homing", [])) or "| - | not drawn | | | |"
    bm = s["body_masses_kg"]
    sl = design.info.get("slide")
    slide_txt = ""
    if sl:
        sp = sl["spring"]
        slide_txt = f"""
Sprung cup (`catcher.compliance: spring`): the cup (shell, liner, 2 LM4UU) is its own body that slides
back along the hand axis when the ball hits (MJCF joint `cup_slide`, GLB node `cup_slide`, range
{sl['range_m'][0] * 1000:.0f}..0 mm).

| Item | Value |
|---|---|
| Guide | {sl['rods']}, rod pitch {sl['rod_pitch_mm']} mm; {sl['bearings']} |
| Springs | {sl['n_springs']} x {sp['id']} ({sp['material']}, wire {sp['wire_mm']} mm, OD {sp['od_mm']} mm, free {sp['free_mm']:g} mm, {sp['rate_n_per_mm']} N/mm; datasheet), one on each rod |
| Stiffness | {sl['k_hw_n_per_m']:.0f} N/m (computed: 2 x datasheet rate); sim uses {arm.spring_k:g} N/m |
| Travel | {sl['travel_m'] * 1000:.1f} mm (rest length {sl['rest_length_mm']} mm, min working {sp['min_work_mm']} mm) |
| Preload | {sl['preload_m'] * 1000:.1f} mm = {sl['preload_n']:.2f} N; full-travel force {sl['max_force_n']:.1f} N (computed) |
| End stops | {sl['end_stops']} |
| Damping | {sl.get('damper', '-')}; target drag {sl.get('brake_drag_target_n', 0):g} N total; sim: friction {float((arm.params.get('catcher') or {}).get('spring_friction_n', 0) or 0):g} N, viscous ratio {arm.spring_zeta:g} (estimate) |
| Rest offset | the brake can hold the cup up to {sl.get('rest_offset_max_mm', 0):g} mm behind the front stop after a catch (drag minus preload, over k) |
| Moving mass | cup body {bm.get('cup', 0):.3f} kg (from the solids) |
"""
    warn = "\n".join(f"- {w}" for w in s["warnings"]) or "- none"
    return f"""# CAD {variant} (belt_arm)

| What | Where |
|---|---|
| Assembly | arm.step, arm.glb, arm.stl (ready pose) |
| Printable parts | stl/*.stl ({s['printed_stls']} files, {s['printed_parts']} pieces), print_list.csv |
| Purchased parts | bom.csv ({s['purchased_lines']} lines, about ${s['est_purchased_usd']:.0f} incl. motors and electronics, estimate) |
| Sim model | arm.xml (MuJoCo), mass_props.json (from the solids) |

Conventional 4-DOF arm after the 20sffactory / Thor pattern: all four NEMA 17 sit low (base
motor in the base, three on the turntable), GT2 20T pulleys drive printed pulleys on closed
belts, 51105 thrust bearing under the turntable, 608-2RS on 8 mm shafts at every joint. Elbow
and wrist are driven by belt pass-through (1:1 belts along the links), so the elbow motor sets
the forearm's absolute pitch (q1+q2) and the wrist motor the hand's (q1+q2+q3); firmware
converts joint angles to motor angles with that coupling, and the cup stays level when the
wrist motor holds.

- Links {arm.upper}/{arm.fore}/{arm.hand} m, shoulder height {arm.base_height} m, reach {s['reach_m']} m.
- Cup {arm.cup_d * 1000:.0f} mm x {arm.cup_depth * 1000:.0f} mm inside the liner ({arm.liner}, ball restitution
  {arm.cup_restitution:.2f}, an estimate used by the sim).
- Masses from the solids (computed: volume x density x infill factor; catalogue masses for purchased parts):
  upper arm {bm.get('upper_arm', 0):.3f} kg, forearm {bm.get('forearm', 0):.3f}, hand {bm.get('hand', 0):.3f},
  cup {bm.get('cup', 0):.3f}, turntable {bm.get('turntable', 0):.3f}, base {bm.get('base', 0):.3f}.
  Printed plastic about {s['print_grams']:.0f} g.

{slide_txt}
Belts (pitch lengths, mm):

| Stage | Pulleys | Centre | Computed | Stock loop |
|---|---|---|---|---|
{belts}

Torque budget per motor (computed; arm stretched horizontally with the ball, the worst static
case; budget = holding x ratio x 50 %). With belt pass-through each motor holds the motor-side
torque C^-T tau (shoulder: upper arm plus the distal weight at the elbow; elbow: forearm plus hand
at the wrist), not the joint torque:

| Motor | Ratio | Joint torque N m | Motor-side N m | Budget N m | Margin | Max speed deg/s |
|---|---|---|---|---|---|---|
{torque}

Motor mapping (`mass_props.json` -> `motor_map`, also in the sim report meta):
`motor_angle = gear_ratio * (C @ q)` with C = {mm['coupling_matrix']} ({mm['coupling']}),
steps per degree of the motor-side angle {mm['steps_per_deg']} at {mm['microsteps']} microsteps.
Inverse: q1 = a1, q2 = a2 - a1, q3 = a3 - a2.

Homing (one sensor per joint, wiring stays on the base/turntable except the wrist):

| Joint | Sensor | Where | Trigger | Homes |
|---|---|---|---|---|
{homing}

Rebuild: `mechy cad build {variant}`.

Not verified: belt stretch and tooth skipping, printed-pulley tooth accuracy, joint stiffness,
the joint-to-motor coupling in firmware (not written yet), infill-based masses (estimate,
weigh the parts).

Warnings / open decisions:
{warn}
"""


def build_variant(project_dir: str | Path, variant: str) -> dict:
    return cad_build(Project(project_dir).require(), variant)


def _ref_summary(variant: str, arm: ArmModel, s: dict, design) -> str:
    """summary.md for ref_arm: provenance, masses, the parallel-linkage motor map, homing,
    and the gravity-torque verification table (this model vs MuJoCo vs BAM's closed form)."""
    bm = s["body_masses_kg"]
    tb = s["torque_budget"]
    torque = "\n".join(f"| {r['joint']} | {r['ratio']:g} | {r['joint_gravity_nm']} | {r['gravity_nm']} | "
                       f"{r['budget_50pct_nm']} | {r['margin'] if r['margin'] is not None else '-'} | "
                       f"{r['max_joint_speed_dps']} |" for r in tb)
    ver = verification_table(arm)
    ver_rows = "\n".join(
        f"| {r['pose']} | {r['joint']} | {r['model']} | {r['mujoco']} | {r['closed']} | "
        f"{r['err_vs_mj_pct']} | {r['err_vs_cf_pct']} |" for r in ver)
    homing = "\n".join(f"| {h['joint']} | {h['sensor']} | {h['homes']} | {h['coordinate']} |"
                       for h in design.info.get("homing", []))
    warn = "\n".join(f"- {w}" for w in s["warnings"]) or "- none"
    return f"""# CAD {variant} (ref_arm — 20sffactory Community Robot Arm)

| What | Where |
|---|---|
| Assembly | arm.glb, arm.stl (ready pose). No arm.step: the vendor parts are meshes, not STEP solids. |
| Printable parts | stl/*.stl ({s['printed_stls']} files, {s['printed_parts']} pieces), print_list.csv |
| Purchased parts | bom.csv ({s['purchased_lines']} lines, about ${s['est_purchased_usd']:.0f}, estimate) |
| Sim model | arm.xml (MuJoCo), mass_props.json |

Provenance: 20sffactory Community Robot Arm (CC BY 4.0, original design Florin Tobler, vendored at
commit 6c2f573, `mechy/data/reference_designs/cad/20sffactory/`); `arm_pleuel_bend_upper_140` is a
BAM-made 140 mm levelling link (the vendor kit has none). Vendor Arduino firmware is GPL-3.0 — the
generated firmware here is mechy's own, not a copy.

This is a parallel-linkage arm (Dobot-style, `kinematics: parallel_level`): the lower motor drives
the lower shank about S, the upper motor drives the lever + pleuel loop so the upper shank's pitch
is a2 = q1+q2, and the two levelling links plus the triplate keep the manipulator level —
q1+q2+q3 = 0, the wrist is passive (no wrist motor). The cup opens straight up at every pose.
Shanks are the vendor 140 mm parts (the 120 -> 140 stretch plus the BAM-made upper levelling link).

- Links {arm.upper}/{arm.fore} m between pivots, shoulder height {arm.base_height} m,
  reach {s['reach_m']} m; cup centre {arm.hand} m radial + {arm.tool_z} m above the wrist axis.
- Cup {arm.cup_d * 1000:.0f} mm x {arm.cup_depth * 1000:.0f} mm ({arm.liner}, restitution
  {arm.cup_restitution:.2f} estimate).
- Masses from the solids (computed: mesh volume x PLA x shell/infill; catalogue masses for motors
  and bearings): upper arm {bm.get('upper_arm', 0):.3f} kg, forearm {bm.get('forearm', 0):.3f} kg,
  hand {bm.get('hand', 0):.3f} kg, cup {bm.get('cup', 0):.3f} kg, turntable {bm.get('turntable', 0):.3f} kg,
  base {bm.get('base', 0):.3f} kg. Passive links are lumped into the nearest driven body
  (pleuel + lower levelling link -> lower shank; lever + upper levelling link -> forearm;
  triplate -> hand) — the same lumping MJCF uses, so model and sim agree by construction.
- Printed plastic about {s['print_grams']:.0f} g.

Motor mapping (`mass_props.json` -> `motor_map`): `motor_angle = 4.5 * (C @ q)` with C the
passthrough matrix — motor a2 holds the upper shank's ABSOLUTE pitch (a2 = q1+q2), a3 = q123 is
constant (no wrist motor). Vendor CNC-shield socket order: X = upper arm, Y = lower arm, Z = yaw,
A = spare (vendor rail module — open decision).

Gravity-torque verification (computed; `g` = 9.81). Model = lumped-body gradient, MuJoCo =
qfrc_bias through the wrist constraint, closed form = BAM `sizing.py`
(tau_lower = g cos th1 L1 (m_ls/2 + m_us + m_tip), tau_upper = g cos th2 L2 (m_us/2 + m_tip)):
the closed form omits the passive links' lever arms, so small differences are expected — the
mujoco column is the ground truth for the lumped model.

| Pose | Motor-side torque | Model N m | MuJoCo N m | Closed form N m | vs MJ % | vs CF % |
|---|---|---|---|---|---|---|
{ver_rows}

Torque budget per motor (computed; arm stretched horizontally with the ball; budget = holding x
4.5 x 50 %):

| Motor | Ratio | Joint torque N m | Motor-side N m | Budget N m | Margin | Max speed deg/s |
|---|---|---|---|---|---|---|
{torque}

Homing (vendor 3-endstop scheme; sensor positions need calibration with tool_shank_calibrator_140
because the firmware constants below are estimates):

| Joint | Sensor | Homes | Coordinate |
|---|---|---|---|
{homing}

Rebuild: `mechy cad build {variant}`.

Not verified: belt tensioning and tooth skipping, printed-surface quality, joint stiffness/backlash,
infill-based masses (estimate — weigh the parts), home sensor positions (estimates, calibrate).
Open decisions: the 4th motor/driver — vendor rail module or a wrist servo (spare).

Warnings / open decisions:
{warn}
"""


def verification_table(arm: ArmModel) -> list[dict]:
    """ArmModel gravity torque vs MuJoCo (with the level constraint) vs BAM's closed form."""
    import mujoco
    from .mjcf import build_mjcf
    m_ls = arm.mass_props["bodies"]["upper_arm"]["mass"] if arm.mass_props else 0.1
    m_us = arm.mass_props["bodies"]["forearm"]["mass"] if arm.mass_props else 0.1
    m_tip = (arm.mass_props["bodies"].get("hand", {}).get("mass", 0.0)
             + arm.mass_props["bodies"].get("cup", {}).get("mass", 0.0))
    rows = []
    m = mujoco.MjModel.from_xml_string(build_mjcf(arm))
    d = mujoco.MjData(m)
    qadr = {n: m.jnt_qposadr[m.joint(n).id] for n in arm.joint_names}
    for tag, q in (("stretched", np.array([0, 0, 0, 0.0])),
                   ("folded", np.asarray(arm.ready_pose(), float)),
                   ("random", np.array([0.3, 0.9, -1.2, -0.3 - 0.9 + 1.2 + 0.3]))):
        q = q.copy()
        q[3] = arm.level_pitch - q[1] - q[2]
        d.qpos[qadr["base"]] = q[0]
        d.qpos[qadr["shoulder"]] = q[1]
        d.qpos[qadr["elbow"]] = q[2]
        d.qpos[qadr["wrist"]] = q[3]
        mujoco.mj_forward(m, d)
        # motor-side torque at (a1, a2) from bias through the constraint Jacobian row structure:
        # a1 = q1, a2 = q1+q2 -> tau_a = C^-T tau_q with wrist torque absorbed by the constraint
        tau_q = np.array([d.qfrc_bias[dof] for dof in
                          [m.jnt_dofadr[m.joint(n).id] for n in arm.joint_names]])
        tau_a = np.linalg.inv(arm.coupling_matrix).T @ tau_q
        model_tau = arm.motor_gravity_torque(q)
        th1, th2 = q[1], q[1] + q[2]
        cf = np.array([0.0,
                       9.81 * math.cos(th1) * arm.upper * (m_ls / 2 + m_us + m_tip),
                       9.81 * math.cos(th2) * arm.fore * (m_us / 2 + m_tip), 0.0])
        for j, nm in enumerate(arm.joint_names):
            if j == 3:
                continue
            mj, mo, cfv = abs(float(tau_a[j])), float(model_tau[j]), abs(float(cf[j]))
            rows.append({"pose": tag, "joint": nm, "model": round(mo, 4), "mujoco": round(mj, 4),
                         "closed": round(cfv, 4),
                         "err_vs_mj_pct": round(100 * abs(mo - mj) / max(mj, 1e-6), 1),
                         "err_vs_cf_pct": round(100 * abs(mo - cfv) / max(cfv, 1e-6), 1)})
    return rows
