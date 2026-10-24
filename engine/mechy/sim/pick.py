"""`mechy sim pick <variant>`: pick-and-place study for the parallel-linkage arm.

Three questions, answered from the CAD masses and the motor curves (no MuJoCo, runs in seconds):
 1. Where can the tool go, and how much can each point carry? (static, gravity only, against the
    usable fraction of each motor's holding torque, like BAM's sizing.py / Arm Lab "Loads" tab.)
 2. How long does one pick -> place -> back cycle take with the design payload, and how close to
    the motor's pull-out torque does it run? (min-jerk joint moves limited by the stepper speed cap
    and by the torque left after gravity.)
 3. What does it look like? replay.json drives the CAD panel's motion sim; plots go in the Sim panel.

Output: sim/<task>/report.json, summary.md, plots/*.png, replay.json. Estimates are labelled."""

from __future__ import annotations

import math
import time
from pathlib import Path

import numpy as np

from ..arm_model import ArmModel, load_arm, torque_curve_at
from ..events import Events
from ..project import Project, write_json
from . import style

REPLAY_DT = 0.01
GRIPPER_DWELL_S = 0.15            # MG90S closing / opening (estimate)
MOTORS = (0, 1, 2)                # base, shoulder (a1), elbow (a2); the wrist has no motor
MAX_PAYLOAD_KG = 1.0


# ----------------------------------------------------------------------------- settings
def settings(project: Project) -> dict:
    p = dict((project.requirements().get("pick") or {}))
    return {
        "payload": float(p.get("payload_kg", 0.2)),
        "pick": np.array(p.get("pick_xyz_m", [0.20, -0.10, 0.02]), float),
        "place": np.array(p.get("place_xyz_m", [0.20, 0.12, 0.04]), float),
        "lift": float(p.get("lift_m", 0.06)),
        "target_cycle": float(p["target_cycle_s"]) if p.get("target_cycle_s") else None,
        "target_payload": float(p["target_payload_kg"]) if p.get("target_payload_kg") else None,
        "usable": float(p.get("usable_torque_fraction", 0.5)),
    }


# ----------------------------------------------------------------------------- statics
def budgets(arm: ArmModel, usable: float) -> np.ndarray:
    """Torque each motor may hold at its output pulley (N m) = usable x holding x gear ratio."""
    return np.array([usable * float(arm.motor_specs[i].get("holding_torque_nm", 0.3)) * arm.gear[i]
                     for i in range(4)])


def static_load(arm: ArmModel, q, payload: float) -> np.ndarray:
    return arm.motor_gravity_torque(q, payload)


def capacity_kg(arm: ArmModel, q, bud: np.ndarray) -> tuple[float, int]:
    """Largest payload the usable budget lets this pose hold, and which motor runs out first.
    The signed holding torque is linear in payload mass, so two evaluations are exact."""
    s0 = signed_motor(arm, q, 0.0)
    s1 = signed_motor(arm, q, 1.0)
    best, who = MAX_PAYLOAD_KG, -1
    for i in MOTORS:
        if abs(s0[i]) > bud[i]:
            return 0.0, i                              # the empty arm already exceeds the budget
        slope = s1[i] - s0[i]
        if abs(slope) < 1e-12:
            continue
        # smallest p >= 0 where |s0 + slope p| reaches the budget (the load may shrink first)
        p = min(p for p in ((sg * bud[i] - s0[i]) / slope for sg in (1.0, -1.0)) if p >= 0)
        if p < best:
            best, who = p, i
    return float(best), who


def signed_motor(arm: ArmModel, q, payload: float) -> np.ndarray:
    """tau_a = C^-T tau_q: the signed torque each motor's output pulley must hold against."""
    tq = arm.gravity_torque_signed(q, payload)
    return np.linalg.inv(arm.coupling_matrix).T @ tq


def workspace_grid(arm: ArmModel, bud: np.ndarray, r_max: float, z_lo: float, z_hi: float, step: float = 0.005):
    rs = np.arange(0.0, r_max + 1e-9, step)
    zs = np.arange(z_lo, z_hi + 1e-9, step)
    cap = np.full((len(zs), len(rs)), np.nan)
    who = np.full((len(zs), len(rs)), -1, dtype=int)
    ik = arm.core_arm()
    for iz, z in enumerate(zs):
        for ir, r in enumerate(rs):
            q = ik.ik([r, 0.0, z])
            if q is None:
                continue
            cap[iz, ir], who[iz, ir] = capacity_kg(arm, q, bud)
    return rs, zs, cap, who


# ----------------------------------------------------------------------------- motion
def min_jerk(tau):
    return 10 * tau ** 3 - 15 * tau ** 4 + 6 * tau ** 5


def min_jerk_d(tau):
    return 30 * tau ** 2 - 60 * tau ** 3 + 30 * tau ** 4


def min_jerk_dd(tau):
    return 60 * tau - 180 * tau ** 2 + 120 * tau ** 3


class Limits:
    """Per-motor speed and acceleration caps in output-pulley coordinates a (rad/s, rad/s^2)."""

    def __init__(self, arm: ArmModel, waypoints_q: list, payload: float, bud: np.ndarray):
        self.arm = arm
        self.vmax = np.array([arm.max_speed_rps(i) * 2 * math.pi / arm.gear[i] for i in range(4)])
        self.amax = np.zeros(4)
        for i in MOTORS:
            spec = arm.motor_specs[i]
            hold = max(abs(signed_motor(arm, q, payload)[i]) for q in waypoints_q)
            j = max(arm.motor_load_inertia(q, payload)[i] for q in waypoints_q) \
                + float(spec["rotor_inertia_kgm2"]) * arm.gear[i] ** 2
            # half the pull-out torque at half speed is what acceleration may use on top of gravity
            avail = 0.5 * torque_curve_at(spec, 0.5 * self.vmax[i] * arm.gear[i]) * arm.gear[i]
            self.amax[i] = max(2.0, (avail - hold) / j)

    def duration(self, da: np.ndarray) -> float:
        t = 0.05
        for i in MOTORS:
            d = abs(da[i])
            if d < 1e-9:
                continue
            t = max(t, 1.875 * d / self.vmax[i], math.sqrt(5.7735 * d / self.amax[i]))
        return t


SEGMENTS = ("above pick to pick", "pick to lift", "lift to above place",
            "above place to place", "place to lift", "lift to above pick")
CARRYING = {"pick to lift", "lift to above place", "above place to place"}   # payload on the tool


def plan_cycle(arm: ArmModel, S: dict) -> dict:
    """Waypoints, per-segment durations and limits of one cycle: down to the pick, grasp, up, carry,
    down to the place, release, up, return above the pick (the loop closes there)."""
    ik = arm.core_arm()
    lift = np.array([0.0, 0.0, S["lift"]])
    A, B = S["pick"], S["place"]
    names = ["above pick", "pick", "lift", "above place", "place", "lift", "above pick"]
    pts = [A + lift, A, A + lift, B + lift, B, B + lift, A + lift]
    qs, seed = [], arm.ready_pose()
    for p in pts:
        q = ik.ik(p, seed=seed)
        if q is None:
            raise ValueError(f"point {np.round(p, 3).tolist()} m is out of reach "
                             f"(the shoulder stop keeps the fingertips above ~{min_tool_z(arm) * 1000:.0f} mm)")
        qs.append(q)
        seed = q
    lim = Limits(arm, qs, S["payload"], budgets(arm, S["usable"]))
    segs = []
    for k, name in enumerate(SEGMENTS):
        T = lim.duration(arm.to_motor(qs[k + 1]) - arm.to_motor(qs[k]))
        grip = name in ("above pick to pick", "above place to place")
        segs.append({"name": name, "q0": qs[k], "q1": qs[k + 1], "T": T,
                     "dwell": GRIPPER_DWELL_S if grip else 0.0, "carrying": name in CARRYING})
    return {"names": names, "points": pts, "q": qs, "segs": segs, "limits": lim,
            "cycle_s": sum(s["T"] + s["dwell"] for s in segs)}


def min_tool_z(arm: ArmModel, r: float = 0.19) -> float:
    ik = arm.core_arm()
    for z in np.arange(-0.05, 0.4, 0.0025):
        if ik.ik([r, 0.0, z]) is not None:
            return float(z)
    return float("nan")


def sample_cycle(arm: ArmModel, plan: dict, payload: float, dt: float = REPLAY_DT) -> dict:
    """Walk the planned segments; per sample: q, tool point, payload mass, motor load / pull-out."""
    lim: Limits = plan["limits"]
    C = arm.coupling_matrix
    Ci_T = np.linalg.inv(C).T
    t_out, q_out, tool, load, mass, seg_of = [], [], [], [], [], []
    t = 0.0
    for si, s in enumerate(plan["segs"]):
        n = max(2, int(round(s["T"] / dt)))
        dq = s["q1"] - s["q0"]
        carrying = s["carrying"]
        m = payload if carrying else 0.0
        for k in range(n + 1):
            tau = k / n
            sp = min_jerk(tau)
            q = s["q0"] + dq * sp
            q[3] = arm.level_pitch - q[1] - q[2]
            a_dot = (C @ dq) * min_jerk_d(tau) / s["T"]
            a_dd = (C @ dq) * min_jerk_dd(tau) / s["T"] ** 2
            J = arm.motor_load_inertia(q, m)
            tau_hold = signed_motor(arm, q, m)
            row = np.zeros(4)
            for i in MOTORS:
                spec = arm.motor_specs[i]
                inertia = J[i] + float(spec["rotor_inertia_kgm2"]) * arm.gear[i] ** 2
                need = abs(inertia * a_dd[i] - tau_hold[i])            # N m at the output pulley
                avail = torque_curve_at(spec, abs(a_dot[i]) * arm.gear[i]) * arm.gear[i]
                row[i] = need / max(avail, 1e-6)
            t_out.append(t + tau * s["T"])
            q_out.append(q)
            tool.append(arm.points(q)[4])
            load.append(row)
            mass.append(m)
            seg_of.append(si)
        t += s["T"]
        if s["dwell"] > 0:
            for _ in range(int(round(s["dwell"] / dt))):
                t += dt
                t_out.append(t)
                q_out.append(q_out[-1])
                tool.append(tool[-1])
                load.append(load[-1])
                mass.append(m)
                seg_of.append(si)
    return {"t": np.array(t_out), "q": np.array(q_out), "tool": np.array(tool), "load": np.array(load),
            "mass": np.array(mass), "seg": np.array(seg_of)}


# ----------------------------------------------------------------------------- plots
def draw_arm(ax, arm: ArmModel, q, color=style.INK, lw=1.6, alpha=1.0, payload_at=None):
    P = arm.points(q) * 1000
    r, z = np.hypot(P[:, 0], P[:, 1]), P[:, 2]            # side view in the arm's own plane, mm
    ax.plot(r, z, "-", color=color, lw=lw, alpha=alpha, solid_capstyle="round", zorder=5)
    ax.plot(r[1:4], z[1:4], "o", ms=4, mfc=style.SURFACE, mec=color, mew=1.1, alpha=alpha, zorder=6)
    ax.plot([r[4]], [z[4]], "D", ms=4, color=color, alpha=alpha, zorder=6)
    ax.plot([r[0]], [z[0]], "s", ms=5, color=color, alpha=alpha, zorder=6)


def plot_workspace(path: Path, arm: ArmModel, S: dict, rs, zs, cap, who, plan, variant: str):
    plt = style.apply()
    from matplotlib.colors import BoundaryNorm, ListedColormap
    fig, ax = plt.subplots(figsize=(7.2, 5.4))
    fig.subplots_adjust(left=0.09, right=0.93, top=0.92, bottom=0.14)
    levels = [0, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 1.01]
    cols = ["#E8C9C9", "#EBD7B5", "#E7E2B8", "#CFE3C8", "#B6DAC4", "#9ACFC4", "#7DC3CF"]
    cmap = ListedColormap(cols)
    norm = BoundaryNorm(levels, cmap.N)
    im = ax.pcolormesh(rs * 1000, zs * 1000, cap, cmap=cmap, norm=norm, shading="auto", zorder=1)
    ax.grid(False)
    cs = ax.contour(rs * 1000, zs * 1000, np.nan_to_num(cap, nan=-1), levels=[0.2, 0.4, 0.6], colors=style.INK,
                    linewidths=0.5, alpha=0.5, zorder=2)
    ax.clabel(cs, fmt=lambda v: f"{v * 1000:.0f} g", fontsize=6.5, inline=True)
    ax.contour(rs * 1000, zs * 1000, np.where(np.isnan(cap), 0.0, 1.0), levels=[0.5], colors=style.INK,
               linewidths=1.0, zorder=3)
    ax.axhline(0, color=style.INK, lw=1.2, zorder=3)
    # arm at the pick, at the place, and ghosted at the start of the lift
    for q, a in ((plan["q"][1], 1.0), (plan["q"][4], 0.55)):
        draw_arm(ax, arm, q, alpha=a)
    for lbl, p, dx in (("PICK", S["pick"], -14), ("PLACE", S["place"], 14)):
        ax.plot([np.hypot(p[0], p[1]) * 1000], [p[2] * 1000], "o", ms=7, mfc=style.ACCENT, mec=style.INK, mew=1.0, zorder=8)
        ax.annotate(lbl, (np.hypot(p[0], p[1]) * 1000, p[2] * 1000), xytext=(dx, -17), textcoords="offset points",
                    ha="center", fontsize=7, color=style.INK, zorder=9,
                    bbox=dict(boxstyle="square,pad=0.25", fc=style.SURFACE, ec=style.INK, lw=0.7))
    # design payload isoline
    ax.set_xlim(-60, rs[-1] * 1000)
    ax.set_ylim(zs[0] * 1000, zs[-1] * 1000)
    ax.set_aspect("equal")
    ax.set_xlabel("radial reach from the yaw axis (mm)")
    ax.set_ylabel("height above the table (mm)")
    ax.set_title("Where the tool can go, and what it can carry")
    ax.text(rs[-1] * 1000 - 4, zs[0] * 1000 + 6, "outline = reachable (joint stops included)", ha="right", fontsize=6.5, color=style.MUTED)
    cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.03, ticks=[0.1, 0.25, 0.35, 0.45, 0.55, 0.65, 0.85])
    cb.ax.set_yticklabels(["<200", "200", "300", "400", "500", "600", ">700"], fontsize=6.5)
    cb.set_label("max payload (g)", fontsize=7)
    cb.outline.set_linewidth(0.6)
    style.title_block(fig, f"Static payload map, usable torque {S['usable'] * 100:.0f}% of holding", f"{variant} / sheet 1")
    fig.savefig(path)
    plt.close(fig)


def plot_cycle(path: Path, arm: ArmModel, S: dict, plan: dict, tr: dict, variant: str):
    plt = style.apply()
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(7.2, 5.4), height_ratios=[3, 1.1], sharex=True)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.92, bottom=0.14, hspace=0.12)
    t = tr["t"]
    # phase shading: payload on the tool
    carry = tr["mass"] > 0
    if carry.any():
        idx = np.where(carry)[0]
        ax.axvspan(t[idx[0]], t[idx[-1]], color=style.ACCENT, alpha=0.10, lw=0, zorder=0)
        ax.text((t[idx[0]] + t[idx[-1]]) / 2, 1.075, f"carrying {S['payload'] * 1000:.0f} g", ha="center",
                fontsize=7, color=style.ACCENT)
    for i in MOTORS:
        n = arm.joint_names[i]
        ax.plot(t, tr["load"][:, i] * 100, color=style.JOINT_COLORS[n], lw=1.5, label=n)
    ax.axhline(100, color=style.DANGER, lw=0.9, ls=(0, (4, 3)))
    ax.text(t[-1], 102, "pull-out torque: motor skips steps above this", ha="right", va="bottom", fontsize=6.5, color=style.DANGER)
    ax.set_ylim(0, 118)
    ax.set_ylabel("motor load (% of pull-out)")
    ax.set_title("One pick-and-place cycle")
    ax.legend(loc="upper left", ncol=3)
    # segment strip
    t0 = 0.0
    names = {"above pick to pick": "down", "pick to lift": "up", "lift to above place": "carry",
             "above place to place": "down", "place to lift": "up", "lift to above pick": "return"}
    for s in plan["segs"]:
        bx.axvspan(t0, t0 + s["T"], ymin=0.15, ymax=0.85, fc=style.SURFACE, ec=style.INK, lw=0.7)
        bx.text(t0 + s["T"] / 2, 0.5, names.get(s["name"], s["name"]), ha="center", va="center", fontsize=6.5, transform=bx.get_xaxis_transform())
        if s["dwell"]:
            bx.axvspan(t0 + s["T"], t0 + s["T"] + s["dwell"], ymin=0.15, ymax=0.85, fc=style.INK, ec=style.INK, lw=0.7)
        t0 += s["T"] + s["dwell"]
    bx.set_yticks([])
    bx.grid(False)
    bx.spines["left"].set_visible(False)
    bx.set_xlim(0, t[-1])
    bx.set_xlabel("time (s)   black = gripper closes / opens")
    style.title_block(fig, "Min-jerk joint moves, speed and torque limited by the stepper curve", f"{variant} / sheet 2")
    fig.savefig(path)
    plt.close(fig)


def plot_budget(path: Path, arm: ArmModel, S: dict, bud: np.ndarray, rs, zs, cap, plan, variant: str):
    """Payload vs radial reach at three heights, and each motor's holding load at the key poses
    against its budget (the Arm Lab 'Loads' view)."""
    plt = style.apply()
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(9.6, 4.2), width_ratios=[1.35, 1])
    fig.subplots_adjust(left=0.07, right=0.98, top=0.9, bottom=0.17, wspace=0.26)
    for z, col in ((0.03, style.INK), (0.08, style.ACCENT), (0.15, style.WARN)):
        iz = int(np.argmin(np.abs(zs - z)))
        ax.plot(rs * 1000, np.where(np.isnan(cap[iz]), np.nan, cap[iz] * 1000), color=col, label=f"{z * 1000:.0f} mm above the table")
    ax.axhline(S["payload"] * 1000, color=style.DANGER, lw=0.9, ls=(0, (4, 3)))
    ax.text(rs[0] * 1000 + 4, S["payload"] * 1000 + 14, f"design payload {S['payload'] * 1000:.0f} g", fontsize=6.5, color=style.DANGER)
    ax.set_xlabel("radial reach (mm)")
    ax.set_ylabel("max payload (g)")
    ax.set_title("Payload against reach")
    ax.set_xlim(rs[0] * 1000, rs[-1] * 1000)
    ax.set_ylim(0, 1050)
    ax.legend(loc="upper right")
    # holding load at the key poses, with the design payload on the tool
    poses = [("at the pick", plan["q"][1]), ("lifted", plan["q"][2]), ("at the place", plan["q"][4])]
    cols = [style.ACCENT, style.INK, style.WARN]
    w = 0.26
    held = (1, 2)
    for k, (lbl, q) in enumerate(poses):
        util = [abs(signed_motor(arm, q, S["payload"])[i]) / bud[i] * 100 for i in held]
        xs = np.arange(len(held)) + (k - 1) * w
        bx.bar(xs, util, w * 0.9, color=cols[k], label=lbl)
        for x, u in zip(xs, util):
            bx.text(x, u + 1.5, f"{u:.0f}", ha="center", fontsize=6.5)
    bx.axhline(100, color=style.DANGER, lw=0.9, ls=(0, (4, 3)))
    bx.set_xticks(np.arange(len(held)))
    bx.set_xticklabels([arm.joint_names[i] for i in held])
    bx.set_ylim(0, 135)
    bx.set_ylabel("% of usable torque budget")
    bx.set_title(f"Holding {S['payload'] * 1000:.0f} g")
    bx.legend(loc="upper right", ncol=3)
    style.title_block(fig, f"Budget = {S['usable'] * 100:.0f}% of holding torque x gear ratio (ESTIMATE: motor datasheet)", f"{variant} / sheet 3")
    fig.savefig(path)
    plt.close(fig)


# ----------------------------------------------------------------------------- run
def run_pick(project: Project, variant: str, task_id: str | None = None, events: Events | None = None,
             microsteps: int | None = None, payload_kg: float | None = None) -> dict:
    from ..project import check_variant_style

    check_variant_style(project, variant, "sim pick")
    ev = events or Events(project.root, quiet=True)
    task = task_id or f"pick-{variant}"
    out = project.path("sim", task)
    (out / "plots").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ev.emit("task.started", task=task)
    arm = load_arm(project, variant, microsteps)
    if arm.kinematics != "parallel_level":
        raise ValueError("sim pick needs a parallel_level (ref_arm) design")
    S = settings(project)
    if payload_kg is not None:
        S["payload"] = payload_kg
    bud = budgets(arm, S["usable"])

    ev.progress(task, "mapping payload capacity over the workspace", 0.1)
    r_max = arm.reach + 0.02
    rs, zs, cap, who = workspace_grid(arm, bud, r_max, -0.03, 0.34)

    ev.progress(task, "planning the pick-and-place cycle", 0.5)
    plan = plan_cycle(arm, S)
    tr = sample_cycle(arm, plan, S["payload"])

    ev.progress(task, "drawing plots", 0.8)
    plots = [("workspace.png", plot_workspace, (arm, S, rs, zs, cap, who, plan)),
             ("cycle.png", plot_cycle, (arm, S, plan, tr)),
             ("payload_budget.png", plot_budget, (arm, S, bud, rs, zs, cap, plan))]
    for fn, f, args in plots:
        f(out / "plots" / fn, *args, variant)

    # ---- numbers
    zone_q = [plan["q"][k] for k in range(len(plan["q"]))]
    zone_cap = [capacity_kg(arm, q, bud) for q in zone_q]
    pose_cap = min(c for c, _ in zone_cap)
    weakest = int(zone_cap[int(np.argmin([c for c, _ in zone_cap]))][1])
    peak = tr["load"].max(0)[list(MOTORS)]
    worst = arm.joint_names[MOTORS[int(np.argmax(peak))]]
    ik = arm.core_arm()
    reach_table = max((r for r in rs if ik.ik([r, 0.0, 0.0]) is not None), default=0.0)
    envelope = float(np.nanmean(~np.isnan(cap)) * (rs[-1] * (zs[-1] - zs[0])))
    cycle = float(tr["t"][-1])
    held_mass = plan["limits"]
    headline = {"label": "Payload", "value": round(pose_cap * 1000, 0), "unit": "g",
                "target": round(S["target_payload"] * 1000, 0) if S["target_payload"] else None,
                "meets": (S["target_payload"] is None) or pose_cap >= S["target_payload"] - 1e-9}
    metrics = [
        {"label": "Cycle", "value": f"{cycle:.2f} s", "target": f"{S['target_cycle']:.1f} s" if S["target_cycle"] else None,
         "meets": S["target_cycle"] is None or cycle <= S["target_cycle"]},
        {"label": "Picks / min", "value": f"{60.0 / cycle:.0f}"},
        {"label": "Peak load", "value": f"{peak.max() * 100:.0f}% of pull-out"},
        {"label": "Reach", "value": f"{reach_table * 1000:.0f} mm at table height"},
        {"label": "Design payload", "value": f"{S['payload'] * 1000:.0f} g"},
        {"label": "Weakest motor", "value": arm.joint_names[weakest]},
    ]
    report = {
        "variant": variant, "kind": "pick", "throws": None,
        "headline": headline, "metrics": metrics,
        "payload_capacity_g": round(pose_cap * 1000, 1), "design_payload_g": round(S["payload"] * 1000, 1),
        "cycle_s": round(cycle, 3), "picks_per_min": round(60.0 / cycle, 1),
        "peak_motor_load": {arm.joint_names[i]: round(float(peak[k]), 3) for k, i in enumerate(MOTORS)},
        "static_budget_nm": {arm.joint_names[i]: round(float(bud[i]), 3) for i in MOTORS},
        "reach_table_m": round(float(reach_table), 3),
        "capacity_at_waypoints_g": {n: round(c * 1000, 1) for n, (c, _) in zip(plan["names"], zone_cap)},
        "segments": [{"name": s["name"], "s": round(s["T"], 3), "dwell_s": s["dwell"], "carrying": s["carrying"]}
                     for s in plan["segs"]],
        "failures": {}, "worst_joint": worst, "plots": [f"plots/{fn}" for fn, _, _ in plots], "video": None,
        "replay": "replay.json",
        "meta": {"duration_s": round(time.time() - t0, 2), "usable_torque_fraction": S["usable"],
                 "pick_xyz_m": S["pick"].tolist(), "place_xyz_m": S["place"].tolist(), "lift_m": S["lift"],
                 "estimates": ["motor holding torque and pull-out curve (hw/motors.yaml, datasheet-typical)",
                               "part masses (solid-PLA-derived print mass from the CAD solids)",
                               "gripper dwell 0.15 s", "no belt stretch, backlash or arm flex"]},
    }
    write_json(out / "report.json", report)
    write_json(out / "replay.json", make_replay(arm, S, plan, tr, variant))
    (out / "summary.md").write_text(make_summary(task, report, arm, S))
    for p in [out / "report.json", out / "replay.json", out / "summary.md", *(out / "plots" / fn for fn, _, _ in plots)]:
        ev.file_written(p)
    ev.emit("task.done", task=task, summary=ev.rel(out / "summary.md"))
    return {"task": task, "dir": ev.rel(out), "report": ev.rel(out / "report.json"),
            "payload_capacity_g": report["payload_capacity_g"], "cycle_s": report["cycle_s"],
            "picks_per_min": report["picks_per_min"], "peak_motor_load": report["peak_motor_load"],
            "worst_joint": worst, "duration_s": report["meta"]["duration_s"]}


def make_replay(arm: ArmModel, S: dict, plan: dict, tr: dict, variant: str) -> dict:
    """One placed-payload throw for the CAD panel's sim theater (contracts 11; ball = the payload)."""
    from ..cad.glb import JOINT_AXES
    pick, place = S["pick"], S["place"]
    ball = []
    for tool, m, t in zip(tr["tool"], tr["mass"], tr["t"]):
        if m > 0:
            ball.append(tool)
        elif t < tr["t"][len(tr["t"]) // 2]:
            ball.append(pick)                      # waiting on the tray
        else:
            ball.append(place)                     # released in the bin
    # payload rests on its half height: it sits in the gripper, so follow the tool point as-is
    th = {"id": 1, "outcome": "placed", "t": [round(float(x), 4) for x in tr["t"]],
          "q": [[round(float(v), 5) for v in q] for q in tr["q"]],
          "ball": [[round(float(v), 5) for v in b] for b in ball],
          "predicted": [], "catch_point": [round(float(v), 4) for v in place]}
    return {"variant": variant, "dt": REPLAY_DT, "kind": "pick", "ball_diameter_m": 0.04,
            "joint_names": list(arm.joint_names), "joint_axes": {k: list(v) for k, v in JOINT_AXES.items()},
            "units": "s, rad, m; world = arm base frame (z up)",
            "rest_q": [round(float(x), 5) for x in arm.ready_pose()], "throws": [th]}


def make_summary(task: str, rep: dict, arm: ArmModel, S: dict) -> str:
    h = rep["headline"]
    peak = ", ".join(f"{k} {v * 100:.0f}%" for k, v in rep["peak_motor_load"].items())
    lines = [f"# Pick and place {task}", "",
             f"- **Payload capacity: {h['value']:.0f} g** (weakest of the cycle's poses, usable torque "
             f"{S['usable'] * 100:.0f}% of holding)"
             + (f"; target {h['target']:.0f} g, {'met' if h['meets'] else 'not met'}" if h["target"] else ""),
             f"- **Cycle: {rep['cycle_s']:.2f} s** with {rep['design_payload_g']:.0f} g, {rep['picks_per_min']:.0f} picks/min"
             + (f"; target {S['target_cycle']:.1f} s" if S["target_cycle"] else ""),
             f"- Peak motor load against pull-out torque: {peak}. Worst: {rep['worst_joint']}.",
             f"- Reach at table height: {rep['reach_table_m'] * 1000:.0f} mm from the yaw axis.", "",
             "| Segment | Time [s] | Payload |", "|---|---|---|"]
    for s in rep["segments"]:
        lines.append(f"| {s['name']} | {s['s']:.2f}" + (f" + {s['dwell_s']:.2f} gripper" if s["dwell_s"] else "")
                     + f" | {'yes' if s['carrying'] else '-'} |")
    lines += ["", "Capacity at each waypoint [g]: " + ", ".join(f"{k} {v:.0f}" for k, v in rep["capacity_at_waypoints_g"].items()),
              "", "Estimates, not measurements: " + "; ".join(rep["meta"]["estimates"]) + ".", ""]
    return "\n".join(lines)
