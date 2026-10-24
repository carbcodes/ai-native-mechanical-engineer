"""Derive every number the firmware and host need from params.yaml + hw/*.yaml (+ mass props).

Speed and acceleration caps follow the same model mechy_core uses to plan moves
(`min_move_time`): usable torque = safety (0.7) x pull-out torque curve, minus the joint's
static gravity torque reflected to the motor, accelerating rotor + reflected load inertia.
The firmware runs constant-acceleration trapezoids, so for each motor we pick the cruise speed
w and acceleration a = net_torque(w) / J that minimise the time of a reference 90-degree joint
move (net torque falls with speed, so a constant acceleration that is safe at w is safe below
it). Load inertia and gravity are the worst case over many in-limit poses, with a ball, seen by
each motor (with belt pass-through a motor carries C^-T tau, not its joint's torque).
"""

from __future__ import annotations

import math
import re

import numpy as np

from .boards import get_board
from .mapping import JOINTS, motor_mapping

SAFETY = 0.7                   # same default as mechy_core plan_move
REF_MOVE_RAD = math.pi / 2     # reference move for choosing cruise speed vs acceleration
TICKS_PER_UPDATE = 20          # profile update every 20 ticks (1 kHz at a 20 kHz tick)
SOFT_MARGIN_DEG = 2.0          # soft limits sit this far inside params limits
DEFAULT_MOTOR_CURRENT_A = 1.5  # estimate: typical NEMA 17 (e.g. 17HS4401 1.7 A); set rated_current_a
A4988_SENSE_RESISTORS = (0.050, 0.068, 0.100)   # R050 / R068 (Pololu) / R100 (many clones)
A4988_UNCOOLED_A = 1.0         # Pololu: ~1 A/phase without heat sink or extra cooling
A4988_COOLED_A = 1.5           # practical with heat sink + fan (2 A is the absolute max)
DEFAULT_HOME = {"base": "min", "shoulder": "max", "elbow": "min", "wrist": "min"}   # simple style
DEFAULT_HOME_ORDER = ("shoulder", "elbow", "wrist", "base")   # raise the arm clear before the base turns
HOME_WINDOW_DEG = 30.0         # widest sensor window the firmware crosses (hall + magnet ~5-15 deg)
HOME_MARGIN_DEG = 10.0         # index sweeps go this far past the computed bound
COORD_RE = re.compile(r"^\s*([qa])(\d)\b")
MICROSTEP_PINS = {1: "MS1 L, MS2 L, MS3 L (no jumpers)", 2: "MS1 H (jumper MS1)",
                  4: "MS2 H (jumper MS2 only)", 8: "MS1 H, MS2 H (jumpers MS1+MS2)",
                  16: "MS1 H, MS2 H, MS3 H (all three jumpers)"}


def torque_at(curve, rps: float, cap_rps: float) -> float:
    tc = np.asarray(curve, float)
    rps = abs(rps)
    if rps > cap_rps * (1 + 1e-12) or rps > tc[-1, 0]:
        return 0.0
    return float(np.interp(rps, tc[:, 0], tc[:, 1]))


def trapezoid_time(dist: float, v: float, a: float) -> float:
    if dist <= 0:
        return 0.0
    if dist >= v * v / a:
        return dist / v + v / a
    return 2.0 * math.sqrt(dist / a)


def derive_motor_caps(spec: dict, gear: float, load_inertia: float, load_torque: float,
                      cap_rps: float, safety: float = SAFETY, ref_rad: float = REF_MOVE_RAD) -> dict:
    """Constant-acceleration caps (motor side, rad/s and rad/s^2) for one motor."""
    J = float(spec.get("rotor_inertia_kgm2", 5.4e-6)) + load_inertia / gear ** 2
    tl = load_torque / gear
    w_cap = 2 * math.pi * cap_rps
    D = ref_rad * gear
    best = None
    for w in np.linspace(0.02, 1.0, 400) * w_cap:
        net = safety * torque_at(spec["torque_curve"], w / (2 * math.pi), cap_rps) - tl
        if net <= 0:
            continue
        a = net / J
        t = trapezoid_time(D, w, a)
        if best is None or t < best[0] - 1e-9:
            best = (t, w, a)
    if best is None:
        raise ValueError("motor cannot hold the static load at safety factor "
                         f"{safety} (gravity {load_torque:.3f} N m at the joint, gear {gear})")
    t, w, a = best
    return {"w": float(w), "a": float(a), "t_ref": float(t), "J_motor": J, "load_torque_motor": tl}


def worst_case_loads(arm, M: np.ndarray, limits: np.ndarray, n_poses: int = 300, seed: int = 0):
    """Per-motor load inertia and static gravity torque about the motor-side coordinate
    theta = M q (the output pulley), worst case over the stretched pose, the ready pose and random
    in-limit poses. With pass-through belts each motor carries C^-T tau (ArmModel's
    motor_load_inertia / gravity_torque_signed when available); otherwise joint-side values."""
    rng = np.random.default_rng(seed)
    poses = [np.zeros(4), np.asarray(arm.ready_pose(), float)]
    poses += list(rng.uniform(limits[:, 0], limits[:, 1], (n_poses, 4)))
    Minv_T = np.linalg.inv(M).T
    identity = np.allclose(M, np.eye(4))
    has_motor_side = hasattr(arm, "motor_load_inertia") and hasattr(arm, "gravity_torque_signed") and \
        np.allclose(getattr(arm, "coupling_matrix", np.eye(4)), M)
    J = np.zeros(4)
    tl = np.zeros(4)
    for q in poses:
        if identity or not has_motor_side:
            J = np.maximum(J, arm.load_inertia(q))
            tl = np.maximum(tl, arm.gravity_torque(q))
        else:
            J = np.maximum(J, arm.motor_load_inertia(q))
            tl = np.maximum(tl, np.abs(Minv_T @ arm.gravity_torque_signed(q)))
    src = ("motor side (C^-T tau), max over %d poses" % len(poses)) if (has_motor_side and not identity) else \
        ("joint side, max over %d poses" % len(poses))
    return J, tl, src


def _joint_by_name(params: dict) -> dict:
    return {j["name"]: i for i, j in enumerate(params["joints"])}


def derive(arm, params: dict, hw: dict, board: str, requirements: dict | None = None,
           mass_props: dict | None = None) -> dict:
    """Everything control needs, as plain JSON-able data. `arm` is an ArmModel."""
    from ..core import get_core
    mc = get_core()
    b = get_board(board)
    names = [j["name"] for j in params["joints"]]
    if tuple(names) != JOINTS:
        raise ValueError(f"joints must be {JOINTS}, got {names}")
    ctl = params.get("control") or {}
    M, map_src = motor_mapping(params, mass_props)
    Minv = np.linalg.inv(M)

    gear_param = np.array([float(j.get("gear_ratio", 1.0)) for j in params["joints"]])
    teeth = np.array([int(round(20 * g)) for g in gear_param])
    gear = teeth / 20.0                                            # what the printed pulleys give
    drv = (hw.get("drivers") or [{}])[0]
    microsteps = int(arm.microsteps)
    step_rate = float(arm.step_rate_hz or 4000.0)
    steps_rev = np.array([360.0 / float(m.get("step_angle_deg", 1.8)) * microsteps for m in arm.motor_specs])
    spr = steps_rev * gear / (2 * math.pi)                         # motor steps per joint-side rad

    limits = np.asarray(arm.limits, float)
    margin = math.radians(float(ctl.get("soft_margin_deg", SOFT_MARGIN_DEG)))
    soft = limits + np.array([margin, -margin])

    J_load, tl, load_src = worst_case_loads(arm, M, limits)
    caps, t90_core = [], []
    for i in range(4):
        cap_rps = arm.max_speed_rps(i)
        c = derive_motor_caps(arm.motor_specs[i], gear[i], J_load[i], tl[i], cap_rps)
        caps.append(c)
        st = mc.Stepper(np.asarray(arm.motor_specs[i]["torque_curve"], float), float(gear[i]),
                        float(arm.motor_specs[i]["rotor_inertia_kgm2"]), cap_rps)
        t90_core.append(float(mc.min_move_time(st, float(J_load[i]), REF_MOVE_RAD, SAFETY, float(tl[i]))))
    v_steps = np.array([c["w"] / (2 * math.pi) * steps_rev[i] for i, c in enumerate(caps)])
    a_steps = np.array([c["a"] / (2 * math.pi) * steps_rev[i] for i, c in enumerate(caps)])
    v_steps = np.minimum(v_steps, step_rate)

    tick_hz = int(b["tick_hz"])
    warnings = []
    if step_rate > tick_hz / 2:
        warnings.append(f"max_step_rate_hz {step_rate:.0f} is above half the firmware tick ({tick_hz} Hz); "
                        "step timing jitter grows and an Uno will not keep up with 4 motors")
    if not np.allclose(gear, gear_param):
        warnings.append("gear ratios rounded to whole pulley teeth (20T motor pulley): "
                        + ", ".join(f"{n} {g:g}->{e:g}" for n, g, e in zip(names, gear_param, gear) if g != e))

    # homing (sensor table: params `control:` overrides > mass_props.json `homing` > style default)
    homing, home_warn = derive_homing(params, limits, M, mass_props)
    warnings += home_warn
    inv = ctl.get("dir_invert") or {}
    dir_invert = [bool(inv.get(n, False)) for n in names]

    ready = np.clip(np.asarray(arm.ready_pose(), float), soft[:, 0], soft[:, 1])

    # driver current / Vref
    rated = [float(m.get("rated_current_a") or ctl.get("motor_current_a") or DEFAULT_MOTOR_CURRENT_A)
             for m in arm.motor_specs]
    rated_known = any(m.get("rated_current_a") for m in arm.motor_specs) or bool(ctl.get("motor_current_a"))
    drv_max = float(drv.get("max_current_a", 2.0))
    i_set = min(rated[0], A4988_COOLED_A, drv_max)
    vref = {f"{rs:.3f}": round(i_set * 8 * rs, 3) for rs in A4988_SENSE_RESISTORS}

    req = requirements or {}
    slots = b["slots"]
    # ref_arm: vendor pinout_uno.h on the CNC shield — X=upper arm (a2), Y=lower arm (a1),
    # Z=yaw (q0), A/E0 = spare (vendor rail); each endstop sits at its socket's limit header.
    slot_order = [2, 1, 0, 3] if arm.style == "ref_arm" else [0, 1, 2, 3]
    motors = []
    for i, n in enumerate(names):
        si = slot_order[i]
        motors.append({
            "name": n, "socket": slots[si]["socket"], "step_pin": slots[si]["step"],
            "dir_pin": slots[si]["dir"],
            "enable_pin": slots[si]["enable"], "step_port": slots[si]["step_port"],
            "step_bit": slots[si]["step_bit"],
            "switch_pin": b["switches"][si]["pin"], "switch_label": b["switches"][si]["label"],
            "slot_note": slots[si].get("note"),
            "gear_ratio_param": float(gear_param[i]), "pulley_teeth": int(teeth[i]), "gear_ratio": float(gear[i]),
            "steps_per_rev_motor": float(steps_rev[i]), "steps_per_rad": float(spr[i]),
            "v_max_steps": float(v_steps[i]), "a_max_steps": float(a_steps[i]),
            "v_max_motor_rps": float(v_steps[i] / steps_rev[i]),
            "a_max_motor_rad_s2": float(caps[i]["a"]),
            "load_inertia_kgm2": float(J_load[i]), "gravity_torque_nm": float(tl[i]),
            "t90_firmware_s": float(trapezoid_time(REF_MOVE_RAD * spr[i], v_steps[i], a_steps[i])),
            "t90_core_s": t90_core[i],
            "drives": " + ".join(names[j] for j in range(4) if abs(M[i, j]) > 1e-12),
        })

    return {
        "schema": 1,
        "variant": arm.name, "style": arm.style, "board": board, "board_title": b["title"], "mcu": b["mcu"],
        "fqbn": b["fqbn"], "board_define": b["define"], "serial_baud": b["serial_baud"],
        "tick_hz": tick_hz, "ticks_per_update": TICKS_PER_UPDATE, "update_hz": tick_hz / TICKS_PER_UPDATE,
        "enable_shared": b["enable_shared"], "estop_pin": b["estop"]["pin"], "estop_label": b["estop"]["label"],
        "joint_names": names,
        "limits_rad": limits.tolist(), "soft_limits_rad": soft.tolist(),
        "mapping": M.tolist(), "mapping_inv": Minv.tolist(), "mapping_source": map_src, "load_source": load_src,
        "microsteps": microsteps, "microstep_jumpers": MICROSTEP_PINS.get(microsteps, "see A4988 datasheet"),
        "max_step_rate_hz": step_rate, "safety": SAFETY,
        "motors": motors,
        "homing": homing,
        "dir_invert": dir_invert,
        "ready_pose_rad": ready.tolist(),
        "links": {"base_height_m": arm.base_height, "upper_arm_m": arm.upper, "forearm_m": arm.fore,
                  "hand_m": arm.hand},
        "motor_specs": [{"torque_curve": m["torque_curve"], "rotor_inertia_kgm2": float(m["rotor_inertia_kgm2"]),
                         "max_speed_rps": float(arm.max_speed_rps(i))} for i, m in enumerate(arm.motor_specs)],
        "current": {"motor_rated_a": rated[0], "rated_known": rated_known, "set_a": i_set,
                    "vref_by_rs": vref, "uncooled_a": A4988_UNCOOLED_A},
        "catch": {"ball_diameter_m": float(req.get("catch", {}).get("ball_diameter_m", 0.067)),
                  "ball_mass_kg": float(req.get("catch", {}).get("ball_mass_kg", 0.057)),
                  "cup_diameter_m": arm.cup_d},
        "vision": {"fps": float(req.get("vision", {}).get("fps", 60)),
                   "latency_s": float(req.get("vision", {}).get("latency_s", 0.05)),
                   "noise_m": float(req.get("vision", {}).get("noise_m", 0.004)),
                   "observe_s": float(req.get("vision", {}).get("observe_s", 0.20))},
        "warnings": warnings,
    }


# ------------------------------------------------------------------ homing
def belt_arm_homing_rows(limits_deg) -> list[dict]:
    """The homing sensors cad/belt_arm.py `_add_homing` draws, for when mass_props.json is missing or
    stale (same rows, same `coordinate` strings). limits_deg: 4 x [lo, hi]."""
    return [
        {"joint": "base", "sensor": "A3144 hall + 5x2 magnet", "homes": "q0 = 0 (index, sweep +-)",
         "home_deg": 0.0, "coordinate": "q0"},
        {"joint": "shoulder", "sensor": "KW12-3 microswitch", "homes": f"q1 = {limits_deg[1][1]:.0f} deg (upper limit)",
         "home_deg": round(float(limits_deg[1][1]), 1), "coordinate": "q1 = a1"},
        {"joint": "elbow", "sensor": "A3144 hall + 5x2 magnet", "homes": "a2 = q1 + q2 = 0 (forearm level)",
         "home_deg": 0.0, "coordinate": "a2 = q1+q2"},
        {"joint": "wrist", "sensor": "KW12-3 microswitch", "homes": f"q3 = {limits_deg[3][0]:.0f} deg (lower limit)",
         "home_deg": round(float(limits_deg[3][0]), 1), "coordinate": "q3 (then a3 = a2 + q3)"},
    ]


def coord_label(M: np.ndarray, j: int, k: int | None) -> str:
    """'q2' for a joint-space sensor, 'a2 = q1+q2' for one that reads motor k's angle."""
    if k is None:
        return f"q{j}"
    terms = [("" if abs(c - 1) < 1e-9 else f"{c:g}*") + f"q{i}" for i, c in enumerate(M[k]) if abs(c) > 1e-12]
    return f"a{k} = " + "+".join(terms)


def derive_homing(params: dict, limits: np.ndarray, M: np.ndarray, mass_props: dict | None) -> tuple[dict, list]:
    """Per-joint homing sensor: kind (limit switch at a joint limit, or an index sensor such as a hall
    + magnet anywhere in the range), the coordinate it reads (joint angle q_j, or motor k's angle
    a_k = M[k] . q), its position in that coordinate, the approach direction, and the order.

    Sources, strongest first: params `control:` (home_pos_deg, home_side, home_kind, homing_order),
    then design/<v>/mass_props.json `homing` (what the CAD draws), then the belt_arm default (same
    table as the CAD), then limit switches at DEFAULT_HOME for the simple style."""
    ctl = params.get("control") or {}
    names = [j["name"] for j in params["joints"]]
    lim_deg = np.degrees(limits)
    rows, src = None, None
    if mass_props and mass_props.get("homing"):
        rows, src = mass_props["homing"], "design mass_props.json homing (CAD sensors)"
    elif str(params.get("style", "simple")) == "belt_arm":
        rows, src = belt_arm_homing_rows(lim_deg.tolist()), "belt_arm default (same sensors as the CAD)"
    by_row = {r["joint"]: r for r in rows or []}
    warnings: list[str] = []
    joints = []
    for j, n in enumerate(names):
        r = by_row.get(n)
        if r is not None:
            m = COORD_RE.match(str(r.get("coordinate") or f"q{j}"))
            k = None
            if m and m.group(1) == "a":
                k = int(m.group(2))
                if np.allclose(M[k], np.eye(4)[j]):
                    k = None                          # motor k reads q_j directly (e.g. a1 = q1)
                elif abs(M[k][j]) < 1e-12:
                    raise ValueError(f"homing: {n} sensor reads a{k}, which joint {n} does not move")
            kind = "index" if "hall" in str(r.get("sensor", "")).lower() else "limit"
            pos = float(r.get("home_deg", 0.0))
            sensor = str(r.get("sensor", ""))
        else:
            k, kind, sensor = None, "limit", "limit switch"
            pos = None
        kind = str((ctl.get("home_kind") or {}).get(n, kind))
        if "none" in str(sensor).lower() and n not in (ctl.get("home_kind") or {}):
            kind = "none"                                   # no sensor on this joint (passive wrist)
        if kind not in ("limit", "index", "none"):
            raise ValueError(f"control.home_kind.{n} must be limit, index or none")
        side = (ctl.get("home_side") or {}).get(n)
        if kind == "none":
            side = side or "min"
            joints.append({"name": n, "kind": "none", "coord_motor": None, "coord": f"q{j}",
                           "pos_rad": 0.0, "dir": -1, "sensor": sensor or "none"})
            continue
        if side is None:
            if kind == "index":
                side = "max"                          # approach (and measure both edges) moving +
            elif pos is not None:
                side = "max" if abs(pos - lim_deg[j, 1]) < abs(pos - lim_deg[j, 0]) else "min"
            else:
                side = DEFAULT_HOME[n] if n in DEFAULT_HOME else "min"
        if side not in ("min", "max"):
            raise ValueError(f"control.home_side.{n} must be min or max")
        if pos is None or (kind == "limit" and r is None):
            pos = float(lim_deg[j, 1 if side == "max" else 0])
        if n in (ctl.get("home_pos_deg") or {}):
            pos = float(ctl["home_pos_deg"][n])
        joints.append({"name": n, "kind": kind, "coord_motor": k, "coord": coord_label(M, j, k),
                       "pos_rad": math.radians(pos), "dir": 1 if side == "max" else -1, "sensor": sensor})
    if ctl.get("homing_order"):
        order = list(ctl["homing_order"])
    elif mass_props and mass_props.get("homing_order"):
        order = list(mass_props["homing_order"])
    else:
        order = list(DEFAULT_HOME_ORDER) if tuple(names) == JOINTS else names
    if sorted(order) != sorted(names):
        raise ValueError(f"homing order must list each joint once: {order}")
    # a sensor on motor k's angle needs every other joint that motor k moves homed first
    for j, h in enumerate(joints):
        if h["coord_motor"] is None:
            continue
        need = [names[i] for i in range(4) if i != j and abs(M[h["coord_motor"]][i]) > 1e-12]
        late = [x for x in need if order.index(x) > order.index(h["name"])]
        if late:
            raise ValueError(f"homing order {order}: {h['name']} reads {h['coord']}, so "
                             f"{', '.join(late)} must home before it")
    fast = math.radians(float(ctl.get("home_speed_dps", 15.0)))
    slow = math.radians(float(ctl.get("home_slow_dps", 3.0)))
    backoff = math.radians(float(ctl.get("home_backoff_deg", 4.0)))
    window = math.radians(float(ctl.get("home_window_deg", HOME_WINDOW_DEG)))
    margin = math.radians(float(ctl.get("home_margin_deg", HOME_MARGIN_DEG)))
    travel = [float(limits[i, 1] - limits[i, 0]) + math.radians(10) for i in range(4)]
    by = {n: i for i, n in enumerate(names)}
    for h in joints:
        if h["kind"] == "index" and h["name"] == "base":
            warnings.append("base homes on a mid-range index sensor: before the first HOME after power-up turn "
                            "the base near q0 = 0 by hand (the first sweep can run up to "
                            f"{math.degrees(float(limits[0, 1]) + margin):.0f} deg past a limit)")
    return {"order": [by[n] for n in order], "order_names": order, "source": src or "params defaults",
            "kind": [h["kind"] for h in joints], "coord_motor": [h["coord_motor"] for h in joints],
            "coord": [h["coord"] for h in joints], "sensor": [h["sensor"] for h in joints],
            "dir": [h["dir"] for h in joints], "pos_rad": [h["pos_rad"] for h in joints],
            "fast_rad_s": fast, "slow_rad_s": slow, "backoff_rad": backoff, "window_rad": window,
            "margin_rad": margin, "travel_rad": travel,
            "switch_active_low": bool(ctl.get("switch_active_low", True))}, warnings
