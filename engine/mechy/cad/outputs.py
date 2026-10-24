"""Make-it outputs for the `simple` arm style (belt_arm.py writes its own): printable STLs,
print_list.csv and bom.csv (contracts section 10), plus loads.json for every style.

The simple style is a concept model, so these lists are estimates: purchased parts come from
hw/*.yaml and the part names, printed masses from solid volumes at a typical fill.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from ..arm_model import ArmModel

PLA_DENSITY_G_CM3 = 1.24
# Slicer model: a 1.2 mm skin (3 x 0.4 mm walls, matching top/bottom) is solid, the rest is 20 % infill.
SKIN_MM = 1.2
INFILL = 0.20
BELT_EFFICIENCY = 0.9

# label -> (material, orientation) for printed parts of the simple model
PRINT_HINTS = {
    "base_housing": ("PETG", "open side up, no supports"),
    "turntable": ("PETG", "flat, bearing face down"),
    "tower_l": ("PLA", "on its long side, no supports"),
    "tower_r": ("PLA", "on its long side, no supports"),
    "upper_arm": ("PLA", "on its long side, no supports"),
    "forearm": ("PLA", "on its long side, no supports"),
    "hand": ("PLA", "on its long side, no supports"),
    "cup": ("PLA", "opening up, no supports"),
}


def _is_bought(label: str) -> bool:
    # NEMA 17s and the GT2 20T motor pulleys are bought; the big joint pulleys are printed.
    return label.startswith("motor_") or (label.startswith("pulley_") and label.endswith("_motor"))


def printed_parts(parts: list) -> dict[str, object]:
    out: dict[str, object] = {}
    for p in parts:
        label = getattr(p, "label", "") or ""
        if label and not _is_bought(label) and label not in out:
            out[label] = p
    return out


def export_stls(parts: list, out_dir: Path) -> list[Path]:
    """One STL per printed part, sitting on the bed (z = 0) and centred."""
    from build123d import Location, export_stl
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.stl"):
        old.unlink()
    files = []
    for label, p in printed_parts(parts).items():
        bb = p.bounding_box()
        s = p.moved(Location((-(bb.min.X + bb.max.X) / 2, -(bb.min.Y + bb.max.Y) / 2, -bb.min.Z)))
        f = out_dir / f"{label}.stl"
        export_stl(s, f, tolerance=0.05, angular_tolerance=0.2)
        files.append(f)
    return files


def print_rows(parts: list) -> list[dict]:
    rows = []
    for label, p in printed_parts(parts).items():
        vol = float(p.volume) / 1000            # mm3 -> cm3
        material, orientation = PRINT_HINTS.get(label, ("PLA" if not label.startswith("pulley_") else "PETG",
                                                        "flat face down"))
        skin = min(float(p.area) * SKIN_MM / 1000, vol)       # mm3 -> cm3
        g = (skin + INFILL * (vol - skin)) * PLA_DENSITY_G_CM3
        rows.append({"part": label, "qty": 1, "material": material, "orientation": orientation,
                     "est_grams": round(g, 1), "est_grams_total": round(g, 1), "infill": f"{INFILL:.0%}",
                     "volume_cm3": round(vol, 1), "stl": f"stl/{label}.stl"})
    return rows


def bom_rows(arm: ArmModel, hw: dict, parts: list) -> list[dict]:
    labels = [getattr(p, "label", "") or "" for p in parts]
    motors = (hw.get("motors") or [{}])[0]
    drivers_doc = hw.get("drivers_doc") or {}
    drv = (hw.get("drivers") or [{}])[0]
    n_motor = sum(1 for x in labels if x.startswith("motor_")) or int(motors.get("count", 4))
    n_motor_pulley = sum(1 for x in labels if x.startswith("pulley_") and x.endswith("_motor"))
    src = "Amazon/AliExpress"
    rows = []

    def row(item, qty, spec, used_for, cost, source=src):
        rows.append({"item": item, "qty": qty, "spec": spec, "used_for": used_for, "source": source,
                     "est_unit_usd": cost})

    model = motors.get("model")
    cur = motors.get("rated_current_a")
    row(f"NEMA 17 stepper{f' {model}' if model else ''}", n_motor,
        "1.8 deg, bipolar 4-wire" + (f", {cur} A/phase" if cur else ""), ", ".join(arm.joint_names), 12.0)
    row(f"{str(drv.get('id', 'a4988')).upper()} stepper driver", int(drv.get("count", n_motor)),
        "with heatsink" + (f", {drv.get('microsteps')} microsteps" if drv.get("microsteps") else ""), "one per motor", 2.0)
    row("Arduino Uno R3", 1, "ATmega328P, USB-B", "controller", 12.0)
    if str(drivers_doc.get("controller", "arduino-uno")).startswith(("arduino-uno", "uno")) or drivers_doc.get("shield"):
        row("CNC Shield V3", 1, "4 driver sockets X/Y/Z/A, 12-36 V motor input", "controller", 5.0)
    psu = drivers_doc.get("power_supply") or {}
    row("DC power supply", 1, f"{psu.get('voltage_v', 24)} V, {psu.get('current_a', 6)} A"
        + (f", {psu['connector']}" if psu.get("connector") else ""), "motor power", 18.0)
    cap = drivers_doc.get("bulk_capacitor") or {}
    row("Electrolytic capacitor", 1, f"{cap.get('capacitance_uf', 100)} uF, {cap.get('voltage_v', 50)} V",
        "across motor power input", 0.3)
    if n_motor_pulley:
        row("GT2 20T pulley, 5 mm bore", n_motor_pulley, "6 mm belt width, with grub screws", "motor shafts", 1.5)
        row("GT2 closed-loop belt", n_motor_pulley, "6 mm wide, length to suit (measure on the printed parts)",
            "motor to joint pulleys", 2.0)
    row("608-2RS bearing", 6, "8 x 22 x 7 mm", "shoulder, elbow, wrist pivots (2 each)", 0.6)
    row("51105 thrust bearing", 1, "25 x 42 x 11 mm", "turntable", 3.0)
    row("Steel shaft 8 mm", 3, "h8 rod, cut to the joint width", "pitch joints", 2.0)
    row("M3 socket head screw assortment", 1, "M3 x 8/10/16 mm, about 60 pcs", "motor mounts, frame", 6.0)
    row("M3 brass heat-set insert", 30, "M3 x 5.7 mm", "printed screw bosses", 0.05)
    row("Limit switch (micro switch)", 4, "NO contact, with lever", "homing, one per joint", 0.5)
    row("Stepper cable", n_motor, "4-wire, 1 m, JST-XH / Dupont to shield header", "motor wiring", 1.5)
    row("Silicone wire 18 AWG", 2, "red and black, 1 m each", "supply to shield", 1.0)
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def _curve_torque(curve, rps: float) -> float:
    c = np.asarray(curve, float)
    return float(np.interp(rps, c[:, 0], c[:, 1]))


def loads(arm: ArmModel, ball_mass: float = 0.057) -> dict:
    """Per-joint static load check: worst-case gravity torque at the motor vs what the motor
    gives (holding torque, and pull-out torque at the usable speed)."""
    # Torque and inertia at each motor's output pulley (joint side of the belt reduction).
    need = np.asarray(arm.motor_gravity_torque_max(ball_mass), float)
    joint_need = np.asarray(arm.gravity_torque_max(ball_mass), float)
    inertia = np.asarray(arm.motor_load_inertia(ball_mass=ball_mass), float)
    joints = []
    for i, name in enumerate(arm.joint_names):
        m = arm.motor_specs[i]
        hold = float(m.get("holding_torque_nm", 0.45))
        speed = arm.max_speed_rps(i)
        at_speed = _curve_torque(m.get("torque_curve", [[0, hold], [10, hold * 0.25]]), speed)
        g = float(arm.gear[i])
        req = float(need[i]) / (g * BELT_EFFICIENCY)          # at the motor shaft
        joints.append({
            "joint": name, "gear_ratio": g, "motor": m.get("model") or m.get("id", "nema17"),
            "gravity_torque_joint_nm": round(float(joint_need[i]), 4),
            "gravity_torque_pulley_nm": round(float(need[i]), 4),
            "gravity_torque_motor_nm": round(req, 4),
            "holding_torque_nm": hold,
            "torque_at_speed_nm": round(at_speed, 4), "usable_speed_rps": round(speed, 2),
            "joint_torque_available_nm": round(hold * g * BELT_EFFICIENCY, 3),
            "safety_factor_static": round(hold / req, 2) if req > 1e-9 else None,
            "safety_factor_at_speed": round(at_speed / req, 2) if req > 1e-9 else None,
            "load_inertia_motor_kgm2": float(f"{float(inertia[i]) / g ** 2:.4g}"),   # reflected to the shaft
            "rotor_inertia_kgm2": float(m.get("rotor_inertia_kgm2", 5.4e-6)),
        })
    return {
        "schema": 1, "variant": arm.name, "ball_mass_kg": ball_mass, "belt_efficiency": BELT_EFFICIENCY,
        "note": "Static: worst-case gravity over the joint range, ball in the cup. Accelerating the arm "
                "needs more; the catch sim checks that.",
        "joints": joints,
    }


def write_loads(path: Path, arm: ArmModel, ball_mass: float = 0.057) -> dict:
    d = loads(arm, ball_mass)
    path.write_text(json.dumps(d, indent=1))
    return d
