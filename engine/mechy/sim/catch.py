"""`mechy sim catch <variant>`: Monte-Carlo catch sweep.

For each throw:
 1. sample a gentle toss from ~throw_distance_m away toward the arm's workspace;
 2. a simulated camera sees the ball at vision.fps with noise, for vision.observe_s;
 3. after vision.latency_s the host fits the flight (ball_fit), predicts it (ball_predict),
    and searches the predicted path for a catch point the arm can reach (Arm.ik) with the
    cup facing the ball, and get to in time with its steppers (plan_batch, gravity included);
 4. MuJoCo runs the arm (stepper model below) along a trapezoidal joint trajectory to that
    pose while the ball flies as a free body with quadratic drag. A catch is counted when
    the ball is inside the cup 0.5 s after it first touches it.

Stepper model (per joint, motor side): torque = T_po(w) * sin(50 * e) + c * (w_ref - w),
limited to +-T_po(w), where e is the rotor lag behind the commanded angle, T_po the pull-out
torque curve and 50 the rotor tooth count of a 1.8 deg motor. A lag beyond 2 full steps
(|50 e| > pi) is a skipped step. Commanded speed is capped by the driver step rate.
"""

from __future__ import annotations

import math
import multiprocessing as mp
import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..arm_model import ArmModel, load_arm
from ..core import core_name, get_core
from ..events import Events
from ..project import Project, write_json

STEPPER_TEETH = 50
SKIP_LAG_RAD_ELEC = math.pi        # 2 full steps
STEPPER_DAMPING_RATIO = 0.3
SIM_DT = 0.0005
COMPUTE_S = 0.005                  # host compute time after the last frame arrives
MIN_LEAD_S = 0.03                  # arrive at least this early (planning)
ALIGN_MAX_DEG = 60.0               # cup axis vs. incoming ball direction
PITCH_OFFSETS = np.radians([0, 10, -10, 20, -20, 30, -30, 45, -45])
HOLD_AFTER_CONTACT_S = 0.5
FAILURE_KEYS = ("out_of_reach", "too_slow", "skipped_steps", "missed", "bounced_out")
GIVE_RESERVE_S = 0.08              # time kept free before the ball for the soft-catch run-up
REPLAY_DT = 0.01                   # replay.json sample period (100 Hz)
REPLAY_EVERY = int(round(REPLAY_DT / SIM_DT))


# ---------------------------------------------------------------- settings
@dataclass
class SimConfig:
    ball_d: float
    ball_m: float
    throw_distance: float
    max_launch_speed: float
    fps: float
    latency: float
    noise: float
    observe_s: float
    launch_height: float
    flight_time: tuple
    aim_center: np.ndarray
    aim_spread: np.ndarray

    @classmethod
    def from_requirements(cls, req: dict) -> "SimConfig":
        c, v, t = req.get("catch", {}), req.get("vision", {}), req.get("throw", {})
        return cls(
            ball_d=float(c.get("ball_diameter_m", 0.067)),
            ball_m=float(c.get("ball_mass_kg", 0.057)),
            throw_distance=float(c.get("throw_distance_m", 1.8)),
            max_launch_speed=float(c.get("max_launch_speed_mps", 6.0)),
            fps=float(v.get("fps", 60)),
            latency=float(v.get("latency_s", 0.05)),
            noise=float(v.get("noise_m", 0.004)),
            observe_s=float(v.get("observe_s", 0.20)),
            launch_height=float(t.get("launch_height_m", 1.0)),
            flight_time=tuple(t.get("flight_time_s", [0.65, 0.95])),
            aim_center=np.asarray(t.get("aim_center_m", [0.25, 0.0, 0.35]), float),
            aim_spread=np.asarray(t.get("aim_spread_m", [0.15, 0.20, 0.12]), float),
        )


# ---------------------------------------------------------------- throws
def sample_throw(cfg: SimConfig, rng: np.random.Generator) -> dict:
    mc = get_core()
    for _ in range(50):
        az = rng.uniform(-math.radians(10), math.radians(10))
        dist = cfg.throw_distance + rng.normal(0, 0.08)
        p0 = np.array([dist * math.cos(az), dist * math.sin(az), cfg.launch_height + rng.normal(0, 0.08)])
        aim = cfg.aim_center + rng.normal(0, 1, 3) * cfg.aim_spread
        aim[2] = max(aim[2], 0.05)
        T = rng.uniform(*cfg.flight_time)
        v0 = (aim - p0) / T + np.array([0, 0, 0.5 * 9.81 * T])
        for _ in range(3):   # correct for drag: shoot and fix the miss
            tr = mc.ball_predict(p0, v0, dt=0.002, t_max=T, mass=cfg.ball_m, diameter=cfg.ball_d)
            v0 = v0 + (aim - tr[-1, 1:]) / T
        if np.linalg.norm(v0) <= cfg.max_launch_speed:
            return {"p0": p0, "v0": v0, "aim": aim, "T": T}
    raise RuntimeError("could not sample a throw under max_launch_speed")


def observe(cfg: SimConfig, true_traj: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Camera frames [t, x, y, z] (noisy) seen up to observe_s after release."""
    phase = rng.uniform(0, 1 / cfg.fps)
    tk = np.arange(phase, cfg.observe_s + 1e-9, 1 / cfg.fps)
    pos = np.stack([np.interp(tk, true_traj[:, 0], true_traj[:, j]) for j in (1, 2, 3)], axis=1)
    return np.column_stack([tk, pos + rng.normal(0, cfg.noise, pos.shape)])


# ---------------------------------------------------------------- planning
def pitch_offsets(arm: ArmModel) -> np.ndarray:
    """Cup pitch offsets from the ideal (axis along the incoming ball), in the order tried.
    params catcher.entry_offset_deg > 0 aims the cup that far off the ball's path so it strikes the
    foam wall before the floor (a straight-in ball rebounds off the floor and out of the cup).
    parallel_level (ref_arm): the linkage holds the cup level — the only pitch is straight up."""
    if arm.kinematics == "parallel_level":
        return np.array([math.pi / 2])
    e = float((arm.params.get("catcher") or {}).get("entry_offset_deg", 0.0) or 0.0)
    if e <= 0:
        return PITCH_OFFSETS
    cand = np.radians(np.arange(-45, 46, 5.0))
    return np.array(sorted(cand, key=lambda o: (abs(abs(math.degrees(o)) - e), -o)))


def plan_motor_batch(arm: ArmModel, motors, q0, Q, Tav, safety: float = 0.7) -> dict:
    """plan_batch in motor-side coordinates a = C q (contracts 7.1 Stepper per motor): with belt
    pass-through the elbow and wrist motors move the absolute link pitch, so their speed limits,
    load inertia (diag of C^-T M C^-1) and gravity load (C^-T tau) are those of a, not of q."""
    mc = get_core()
    Q = np.atleast_2d(np.asarray(Q, float))
    a0 = arm.to_motor(q0)
    A = arm.to_motor(Q)
    J0, T0 = arm.motor_load_inertia(q0, 0.0), arm.motor_gravity_torque(q0, 0.0)
    J = np.array([np.maximum(J0, arm.motor_load_inertia(q, 0.0)) for q in Q])
    TL = np.array([np.maximum(T0, arm.motor_gravity_torque(q, 0.0)) for q in Q])
    return mc.plan_batch(a0, A, motors, J, np.asarray(Tav, float), safety=safety, load_torque=TL)


def _give_path_ok(arm: ArmModel, core_arm, p, v, pitch: float, q) -> bool:
    """The soft-catch path (run-up and give along the ball's velocity, same pitch) stays reachable."""
    dh = np.asarray(v, float) / max(float(np.linalg.norm(v)), 1e-9)
    for s in (-arm.give_runup_m, -arm.give_runup_m / 2, arm.give_m / 2, arm.give_m):
        if abs(s) > 1e-6 and core_arm.ik(p + s * dh, pitch, seed=q) is None:
            return False
    return True


def choose_catch(arm: ArmModel, motors, core_arm, q0, pred: np.ndarray, t_dec: float, ball_m: float,
                 t_reserve: float = 0.0):
    """Search the predicted path for the best reachable, in-time catch pose. t_reserve: time kept
    free before the ball arrives (the soft-catch run-up)."""
    mc = get_core()
    shoulder = np.array([0, 0, arm.base_height])
    offsets = pitch_offsets(arm)
    vel = np.gradient(pred[:, 1:], pred[:, 0], axis=0)
    cands = []
    for i in range(len(pred)):
        t, p = pred[i, 0], pred[i, 1:]
        if t < t_dec + 0.08 or p[2] < 0.06:
            continue
        if np.linalg.norm(p - shoulder) > arm.reach + 1e-3:
            continue
        v = vel[i]
        rh = np.array([p[0], p[1], 0.0])
        nr = np.linalg.norm(rh)
        if nr < 1e-6:
            continue
        rh /= nr
        ideal = math.atan2(-v[2], -(v @ rh))
        for off in offsets:
            pitch = off if arm.kinematics == "parallel_level" else ideal + off
            q = core_arm.ik(p, pitch, seed=q0)
            if q is None:
                continue
            if t_reserve > 0 and not _give_path_ok(arm, core_arm, p, v, pitch, q):
                continue
            axis = math.cos(pitch) * rh + np.array([0, 0, math.sin(pitch)])
            align = math.degrees(math.acos(np.clip(axis @ (-v / np.linalg.norm(v)), -1, 1)))
            if align <= ALIGN_MAX_DEG:
                cands.append((t, p, np.asarray(q, float), align, pitch, i))
                break
    if not cands:
        return None, {"reachable": False}
    Q = np.array([c[2] for c in cands])
    Tav = np.array([c[0] - t_dec - MIN_LEAD_S - t_reserve for c in cands])
    res = plan_motor_batch(arm, motors, q0, Q, Tav)
    feas = np.asarray(res["feasible"], bool)
    t_need = np.asarray(res["t_needed"], float)
    if not feas.any():
        return None, {"reachable": True, "feasible": False,
                      "best_shortfall_s": float(np.min(t_need - Tav))}
    margin = Tav + MIN_LEAD_S - t_need          # spare time before the move (or the run-up) must start
    align = np.array([c[3] for c in cands])
    score = align + 400.0 * np.maximum(0.0, 0.12 - margin)
    score[~feas] = np.inf
    k = int(np.argmin(score))
    t, p, q, al, pitch, _ = cands[k]
    return {"t": float(t), "p": p, "q": q, "align_deg": float(al), "pitch": float(pitch), "v": vel[cands[k][5]],
            "t_needed": float(t_need[k]), "t_avail": float(t - t_dec), "margin": float(margin[k]),
            "plan_torque_frac": np.asarray(res["peak_torque_frac"][k], float)}, {"reachable": True, "feasible": True}


def plan_give(arm: ArmModel, core_arm, motors, plan: dict, ball_m: float, give_m: float | None = None,
              runup_m: float | None = None, n: int = 41, safety: float = 0.6) -> dict | None:
    """Soft catch: a straight cup path through the catch point along the ball's incoming velocity,
    from runup_m before it to give_m past it, at the catch pitch. The cup accelerates uniformly over
    the run-up, passes the catch point at v_c and decelerates uniformly to rest over the give.
    v_c and the two accelerations are the largest the steppers allow (motor-side speed under the
    step-rate cap, torque = safety x pull-out at that speed minus gravity), and v_c is capped at
    70 % of the ball's speed so the ball still arrives. Returns None when the path leaves the
    workspace or the motors can't move usefully."""
    give = arm.give_m if give_m is None else give_m
    run = arm.give_runup_m if runup_m is None else runup_m
    if give <= 1e-4 or run <= 1e-4:
        return None
    vb = np.asarray(plan["v"], float)
    sb = float(np.linalg.norm(vb))
    if sb < 1e-6:
        return None
    dhat = vb / sb
    s = np.linspace(-run, give, n)
    k0 = int(np.argmin(np.abs(s)))
    order = list(range(k0, n)) + list(range(k0 - 1, -1, -1))
    qs = [None] * n
    for k in order:
        sd = qs[k - 1] if k > k0 else (qs[k + 1] if k < k0 else plan["q"])
        q = core_arm.ik(plan["p"] + s[k] * dhat, plan["pitch"], seed=sd)
        if q is None:
            return None
        qs[k] = np.asarray(q, float)
    Q = np.array(qs)
    if np.abs(np.diff(Q, axis=0)).max() > 0.2:          # IK branch flip along the path
        return None
    A = arm.to_motor(Q)
    dA = np.gradient(A, s, axis=0)                       # rad per metre of cup travel
    ddA = np.gradient(dA, s, axis=0)
    vmax = np.array([m.max_joint_speed for m in motors])  # motor-side rad/s (rps cap / gear)
    G = arm.gear
    rotor = np.array([float(m["rotor_inertia_kgm2"]) for m in arm.motor_specs])
    curves = [np.asarray(m["torque_curve"], float) for m in arm.motor_specs]
    J = np.array([arm.motor_load_inertia(q, ball_m) for q in Q[::5]]).max(0) + rotor * G ** 2
    TL = np.array([arm.motor_gravity_torque(q, ball_m) for q in Q[::5]]).max(0)
    v_c = min(0.7 * sb, 0.85 * float(np.min(vmax / np.maximum(np.abs(dA).max(0), 1e-9))))

    def ok(v):
        a1 = v * v / (2 * run)
        a2 = v * v / (2 * give)
        w_mot = np.abs(dA).max(0) * v * G / (2 * math.pi)            # motor rev/s at the peak
        t_po = np.array([np.interp(w_mot[i], curves[i][:, 0], curves[i][:, 1]) for i in range(4)]) * G
        acc = np.abs(dA).max(0) * max(a1, a2) + np.abs(ddA).max(0) * v * v
        return bool(np.all(J * acc + TL <= safety * t_po)), a1, a2
    for _ in range(40):
        good, a1, a2 = ok(v_c)
        if good:
            break
        v_c *= 0.9
    else:
        return None
    if v_c < 0.1:
        return None
    t1 = 2 * run / v_c
    t2 = 2 * give / v_c
    return {"s": s, "A": A, "dA": dA, "v_c": float(v_c), "a1": float(a1), "a2": float(a2), "t1": float(t1),
            "t2": float(t2), "q_pre": Q[0], "q_end": Q[-1], "dhat": dhat, "give_m": float(give),
            "runup_m": float(run)}


def give_profile(g: dict):
    """f(t) -> (a, adot) along the give path, t = 0 at the start of the run-up."""
    s_arr, A, dA = g["s"], g["A"], g["dA"]
    t1, t2, v, a1, a2, run = g["t1"], g["t2"], g["v_c"], g["a1"], g["a2"], g["runup_m"]

    def f(t: float):
        if t <= 0:
            sv, sd = s_arr[0], 0.0
        elif t < t1:
            sv, sd = -run + 0.5 * a1 * t * t, a1 * t
        elif t < t1 + t2:
            tau = t - t1
            sv, sd = v * tau - 0.5 * a2 * tau * tau, v - a2 * tau
        else:
            sv, sd = s_arr[-1], 0.0
        a = np.array([np.interp(sv, s_arr, A[:, j]) for j in range(4)])
        ad = np.array([np.interp(sv, s_arr, dA[:, j]) for j in range(4)]) * sd
        return a, ad
    return f


def trapezoid(q0, q1, T: float, vmax):
    """Per-joint trapezoids, all of duration T. Returns f(t) -> (q, qdot) for t in [0, inf)."""
    q0 = np.asarray(q0, float)
    D = np.asarray(q1, float) - q0
    A = np.abs(D)
    sgn = np.sign(D)
    v = np.minimum(1.5 * A / T, 0.97 * np.asarray(vmax))
    v = np.maximum(v, A / T * 1.02)
    ta = np.where(A > 1e-12, T - A / np.maximum(v, 1e-12), T / 3)
    ta = np.clip(ta, 1e-3, T / 2)
    v = np.where(A > 1e-12, A / (T - ta), 0.0)
    a = v / ta

    def f(t: float):
        t = min(max(t, 0.0), T)
        s = np.where(t < ta, 0.5 * a * t * t,
                     np.where(t < T - ta, 0.5 * a * ta * ta + v * (t - ta),
                              A - 0.5 * a * (T - t) ** 2))
        sd = np.where(t < ta, a * t, np.where(t < T - ta, v, a * (T - t)))
        return q0 + sgn * s, sgn * sd
    return f


# ---------------------------------------------------------------- mujoco
_WORKER: dict = {}


def _worker_init(xml: str, params: dict, motors_hw: list, drivers_hw: list, microsteps, cfg: SimConfig,
                 mass_props: dict | None = None):
    import mujoco
    m = mujoco.MjModel.from_xml_string(xml)
    m.opt.timestep = SIM_DT
    # torques come from the stepper model via qfrc_applied: disable the MJCF position servos
    m.actuator_gainprm[:] = 0
    m.actuator_biasprm[:] = 0
    arm = ArmModel(params, motors_hw, drivers_hw, microsteps, mass_props)
    cup_geoms = {m.geom(i).id for i in range(m.ngeom) if m.geom(i).name.startswith("cup_")}
    _WORKER.update(model=m, arm=arm, cfg=cfg, core_arm=arm.core_arm(), motors=arm.core_motors(),
                   ball_geom=m.geom("ball").id, cup_geoms=cup_geoms, cup_body=m.body("cup").id,
                   ball_body=m.body("ball").id,
                   dofs=[m.joint(n).dofadr[0] for n in arm.joint_names],
                   qadr=[m.joint(n).qposadr[0] for n in arm.joint_names],
                   ball_q=m.joint("ball").qposadr[0], ball_v=m.joint("ball").dofadr[0])


def _replay_rows(rows) -> dict:
    a = np.array(rows, float) if rows else np.zeros((0, 8))
    return {"t": a[:, 0].round(3).tolist(), "q": a[:, 1:5].round(5).tolist(), "ball": a[:, 5:8].round(4).tolist()}


def _flight_only_replay(true: np.ndarray, q0, cfg: SimConfig) -> dict:
    """Replay rows for a throw the arm never moved for: the ball's true flight, arm at q0."""
    tk = np.arange(0.0, true[-1, 0], REPLAY_DT)
    pos = np.stack([np.interp(tk, true[:, 0], true[:, j]) for j in (1, 2, 3)], axis=1)
    keep = pos[:, 2] >= cfg.ball_d / 2 - 1e-9
    stop = int(np.argmin(keep)) + 1 if not keep.all() else len(tk)
    return _replay_rows([(t, *q0, *p) for t, p in zip(tk[:stop], pos[:stop])])


def simulate_throw(args) -> dict:
    import mujoco
    idx, seed = args
    W = _WORKER
    m, arm, cfg = W["model"], W["arm"], W["cfg"]
    mc = get_core()
    rng = np.random.default_rng(seed)
    throw = sample_throw(cfg, rng)
    true = mc.ball_predict(throw["p0"], throw["v0"], dt=0.002, t_max=2.0, mass=cfg.ball_m, diameter=cfg.ball_d)
    ground = np.where(true[:, 3] <= cfg.ball_d / 2)[0]
    land = true[ground[0], 1:3] if len(ground) else true[-1, 1:3]
    rec = {"i": idx, "seed": int(seed), "launch": throw["p0"].round(3).tolist(),
           "v0": throw["v0"].round(3).tolist(), "land_xy": land.round(3).tolist(), "outcome": None}

    obs = observe(cfg, true, rng)
    t_dec = float(obs[-1, 0] + cfg.latency + COMPUTE_S)
    fit = mc.ball_fit(obs, mass=cfg.ball_m, diameter=cfg.ball_d)
    pred = mc.ball_predict(fit["p0"], fit["v0"], dt=0.005, t_max=1.8, mass=cfg.ball_m, diameter=cfg.ball_d,
                           t0=fit["t0"])
    pk = pred[::2]
    above = pk[:, 3] >= 0
    rec["predicted"] = {"t0": round(float(pk[0, 0]), 4), "dt": 0.01, "t_decide": round(t_dec, 4),
                        "p": pk[above, 1:].round(4).tolist()}
    q0 = arm.ready_pose()
    motors = W["motors"]
    use_give = arm.give_m > 1e-4 and W.get("give", True)
    plan, info = None, {"reachable": False}
    if use_give:
        plan, info = choose_catch(arm, motors, W["core_arm"], q0, pred, t_dec, cfg.ball_m, t_reserve=GIVE_RESERVE_S)
    if plan is None:
        plan, info = choose_catch(arm, motors, W["core_arm"], q0, pred, t_dec, cfg.ball_m)
    rec["reachable"] = info["reachable"]
    if plan is None:
        rec["outcome"] = "out_of_reach" if not info["reachable"] else "too_slow"
        if "best_shortfall_s" in info:
            rec["shortfall_s"] = round(info["best_shortfall_s"], 3)
        rec["replay"] = _flight_only_replay(true, q0, cfg)
        return rec
    rec.update(t_catch=round(plan["t"], 3), catch_p=plan["p"].round(4).tolist(), margin_s=round(plan["margin"], 3),
               align_deg=round(plan["align_deg"], 1), plan_torque_frac=np.round(plan["plan_torque_frac"], 3).tolist())
    err = np.interp(plan["t"], true[:, 0], true[:, 1]), np.interp(plan["t"], true[:, 0], true[:, 2]), \
        np.interp(plan["t"], true[:, 0], true[:, 3])
    rec["pred_err_m"] = round(float(np.linalg.norm(np.array(err) - plan["p"])), 4)

    # soft catch: run-up + give along the ball's path, if the motors allow it and there is time
    give = plan_give(arm, W["core_arm"], motors, plan, cfg.ball_m) if use_give else None
    q_target = plan["q"]
    t_move_end = plan["t"] - t_dec           # latest end of the approach (relative to t_dec)
    if give is not None:
        res = plan_motor_batch(arm, motors, q0, give["q_pre"][None, :],
                               [plan["t_avail"] - give["t1"] - MIN_LEAD_S])
        if bool(np.asarray(res["feasible"])[0]):
            q_target = give["q_pre"]
            t_need = float(np.asarray(res["t_needed"])[0])
            t_move_end -= give["t1"]
        else:
            give = None
    if give is None:
        t_need = plan["t_needed"]
    rec["give"] = bool(give is not None)
    if give is not None:
        rec.update(give_v_mps=round(give["v_c"], 3), give_m=round(give["give_m"], 3),
                   ball_speed_mps=round(float(np.linalg.norm(plan["v"])), 3))

    # approach in motor coordinates (a = C q): use spare time to move gently, but arrive >= ~MIN_LEAD_S early
    a0, a_t = arm.to_motor(q0), arm.to_motor(q_target)
    T_move = max(t_need, min(t_move_end - 0.06, 1.4 * t_need))
    vmax = np.array([mot.max_joint_speed for mot in motors])
    approach = trapezoid(a0, a_t, T_move, vmax)
    gprof = give_profile(give) if give is not None else None
    t_give0 = plan["t"] - give["t1"] if give is not None else None     # absolute time the run-up starts

    def ref(t: float):
        if gprof is not None and t >= t_give0:
            return gprof(t - t_give0)
        tr = t - t_dec
        if tr <= 0:
            return a0, np.zeros(4)
        return approach(tr)

    d = mujoco.MjData(m)
    qa, dofs = W["qadr"], W["dofs"]
    d.qpos[qa] = q0
    d.qpos[W["ball_q"]:W["ball_q"] + 3] = throw["p0"]
    d.qpos[W["ball_q"] + 3:W["ball_q"] + 7] = [1, 0, 0, 0]
    d.qvel[W["ball_v"]:W["ball_v"] + 3] = throw["v0"]
    mujoco.mj_forward(m, d)

    C = arm.coupling_matrix
    G = arm.gear
    specs = arm.motor_specs
    hold = np.array([float(s["torque_curve"][0][1]) for s in specs])
    curves = [np.asarray(s["torque_curve"], float) for s in specs]
    Jm = arm.motor_load_inertia(q0, 0) / G ** 2 + np.array([float(s["rotor_inertia_kgm2"]) for s in specs])
    c_m = 2 * STEPPER_DAMPING_RATIO * np.sqrt(hold * STEPPER_TEETH * Jm)
    k_drag = mc.ball_drag_k(cfg.ball_m, cfg.ball_d) if hasattr(mc, "ball_drag_k") else \
        1.2 * 0.55 * math.pi * (cfg.ball_d / 2) ** 2 / (2 * cfg.ball_m)
    bb = W["ball_body"]
    t_contact = None
    skip_t, skip_joint = None, None
    peak_frac = np.zeros(4)
    peak_impact_lag = np.zeros(4)
    t_end = plan["t"] + 0.4
    n_rec = 0
    log, rows = [], []
    impact = None
    trace = [] if os.environ.get("MECHY_SIM_TRACE") else None
    cvel = np.zeros(6)
    while True:
        t = d.time
        a_ref, ad_ref = ref(t)
        q = d.qpos[qa]
        qd = d.qvel[dofs]
        a = C @ q
        w_m = G * (C @ qd)
        lag = G * (a_ref - a)
        rps = np.abs(w_m) / (2 * math.pi)
        t_po = np.array([np.interp(rps[i], curves[i][:, 0], curves[i][:, 1]) for i in range(4)])
        tau_m = t_po * np.sin(STEPPER_TEETH * lag) + c_m * (G * ad_ref - w_m)
        tau_m = np.clip(tau_m, -t_po, t_po)
        if t_contact is None:
            peak_frac = np.maximum(peak_frac, np.where(np.abs(STEPPER_TEETH * lag) < math.pi / 2,
                                                       np.abs(np.sin(STEPPER_TEETH * lag)), 1.0))
        else:
            peak_impact_lag = np.maximum(peak_impact_lag, np.abs(STEPPER_TEETH * lag) / SKIP_LAG_RAD_ELEC)
        if skip_t is None:
            bad = np.abs(STEPPER_TEETH * lag) > SKIP_LAG_RAD_ELEC
            if bad.any():
                skip_t, skip_joint = t, int(np.argmax(np.abs(lag) * bad))
        d.qfrc_applied[dofs] = C.T @ (G * tau_m)        # motor torques -> joint torques (power balance)
        v = d.qvel[W["ball_v"]:W["ball_v"] + 3]
        d.xfrc_applied[bb, :3] = -k_drag * cfg.ball_m * np.linalg.norm(v) * v
        if n_rec % 10 == 0:
            log.append((t, *(tau_m / np.maximum(hold, 1e-9))))
            if trace is not None:
                Rc = d.xmat[W["cup_body"]].reshape(3, 3)
                trace.append((round(t, 4), *np.round(Rc.T @ (d.xpos[bb] - d.xpos[W["cup_body"]]), 4),
                              *np.round(np.degrees(q - plan["q"]), 2)))
        if n_rec % REPLAY_EVERY == 0:
            rows.append((t, *q, *d.qpos[W["ball_q"]:W["ball_q"] + 3]))
        n_rec += 1
        mujoco.mj_step(m, d)
        if t_contact is None:
            for c in d.contact[:d.ncon]:
                gs = {c.geom1, c.geom2}
                if W["ball_geom"] in gs and gs & W["cup_geoms"]:
                    t_contact = d.time
                    t_end = t_contact + HOLD_AFTER_CONTACT_S
                    mujoco.mj_objectVelocity(m, d, mujoco.mjtObj.mjOBJ_BODY, W["cup_body"], cvel, 0)
                    Rc = d.xmat[W["cup_body"]].reshape(3, 3)
                    vb = d.qvel[W["ball_v"]:W["ball_v"] + 3]
                    impact = {"ball_mps": float(np.linalg.norm(vb)),
                              "rel_axial_mps": float(-(vb - cvel[3:]) @ Rc[:, 2]),
                              "cup_mps": float(np.linalg.norm(cvel[3:]))}
                    break
            if t_contact is None and d.qpos[W["ball_q"] + 2] < cfg.ball_d / 2 + 0.003:
                break  # ball on the floor without touching the cup
        if d.time >= t_end:
            break
    rows.append((d.time, *d.qpos[qa], *d.qpos[W["ball_q"]:W["ball_q"] + 3]))
    rec["replay"] = _replay_rows(rows)

    # in the cup? express ball centre in the cup frame
    R = d.xmat[W["cup_body"]].reshape(3, 3)
    rel = R.T @ (d.xpos[bb] - d.xpos[W["cup_body"]])
    inside = (math.hypot(rel[0], rel[1]) <= arm.cup_d / 2) and (-arm.cup_depth / 2 - 0.01 <= rel[2] <= arm.cup_depth / 2 + cfg.ball_d / 4)
    caught = bool(t_contact is not None and inside)
    skip_before = bool(skip_t is not None and (t_contact is None or skip_t < t_contact))
    rec.update(contact=t_contact is not None, skipped=skip_t is not None,
               skip_joint=arm.joint_names[skip_joint] if skip_joint is not None else None,
               skip_before_contact=skip_before,
               skip_on_impact=bool(skip_t is not None and not skip_before),
               peak_torque_frac=np.round(peak_frac, 3).tolist())
    if t_contact is not None:
        rec["impact_peak_lag_frac"] = np.round(peak_impact_lag, 3).tolist()   # 1.0 = skip threshold
    if impact is not None:
        rec["impact"] = {k: round(v, 3) for k, v in impact.items()}
    if caught:
        rec["outcome"] = "caught"
    elif skip_before:
        rec["outcome"] = "skipped_steps"
    elif t_contact is None:
        rec["outcome"] = "missed"
    else:
        rec["outcome"] = "bounced_out"
    rec["torque_log"] = np.round(np.array(log), 4).tolist() if idx < 40 else None
    if trace is not None:
        rec["trace"] = trace
    return rec


# ---------------------------------------------------------------- driver
def run_catch(project: Project, variant: str, throws: int = 200, seed: int = 0, task_id: str | None = None,
              workers: int | None = None, video: bool = False, events: Events | None = None,
              microsteps: int | None = None) -> dict:
    from ..cad.mjcf import build_mjcf
    from ..project import check_variant_style

    check_variant_style(project, variant, "sim catch")
    ev = events or Events(project.root, quiet=True)
    task = task_id or f"catch-{variant}"
    out = project.path("sim", task)
    (out / "plots").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    ev.emit("task.started", task=task)
    arm = load_arm(project, variant, microsteps)
    cfg = SimConfig.from_requirements(project.requirements())
    # always regenerated from the current params (sim-only catcher settings such as compliance
    # change the MJCF without a CAD rebuild); masses still come from the CAD mass_props.json
    xml = build_mjcf(arm, cfg.ball_d, cfg.ball_m)
    hw = project.hardware()
    import mujoco
    mujoco.MjModel.from_xml_string(xml)  # fail here, not inside the worker pool
    seeds = np.random.SeedSequence(seed).generate_state(throws)
    jobs = list(enumerate(int(s) for s in seeds))
    workers = max(1, min(workers or os.cpu_count() or 1, throws))
    init = (xml, arm.params, hw["motors"], hw["drivers"], microsteps, cfg, arm.mass_props)
    results: list[dict] = []
    ev.progress(task, f"simulating {throws} throws on {workers} processes (core: {core_name()})", 0.0)
    if workers == 1:
        _worker_init(*init)
        it = map(simulate_throw, jobs)
        for r in it:
            results.append(r)
            if len(results) % max(1, throws // 10) == 0:
                ev.progress(task, f"{len(results)}/{throws} throws", len(results) / throws)
    else:
        ctx = mp.get_context("fork" if hasattr(os, "fork") and os.uname().sysname == "Linux" else "spawn")
        with ctx.Pool(workers, initializer=_worker_init, initargs=init) as pool:
            for r in pool.imap_unordered(simulate_throw, jobs, chunksize=2):
                results.append(r)
                if len(results) % max(1, throws // 10) == 0:
                    ev.progress(task, f"{len(results)}/{throws} throws", len(results) / throws)
    results.sort(key=lambda r: r["i"])
    replay = make_replay(variant, results, arm)
    write_json(out / "replay.json", replay)
    for r in results:
        r.pop("replay", None)
        r.pop("predicted", None)
    report = make_report(variant, results, arm)
    report["video"] = None  # video needs a headless GL backend (see README)
    plots = make_plots(out / "plots", results, arm, cfg)
    report["plots"] = [f"plots/{p.name}" for p in plots]
    report["meta"] = {
        "core": core_name(), "seed": seed, "microsteps": arm.microsteps,
        "max_motor_rps": [round(arm.max_speed_rps(i), 3) for i in range(4)],
        "step_rate_hz": arm.step_rate_hz, "duration_s": round(time.time() - t0, 1),
        "style": arm.style, "liner": arm.liner, "cup_restitution": arm.cup_restitution,
        "masses_from_cad": bool(arm.mass_props),
        "motor_map": arm.motor_map(),
        "soft_catch": {"give_m": arm.give_m, "give_runup_m": arm.give_runup_m,
                       "compliance": arm.compliance,
                       **({"spring_k_n_per_m": arm.spring_k, "spring_travel_m": arm.spring_travel,
                           "spring_damping_ratio": arm.spring_zeta} if arm.compliance == "spring" else {})},
        "replay": "replay.json",
        "vision": {"fps": cfg.fps, "latency_s": cfg.latency, "noise_m": cfg.noise, "observe_s": cfg.observe_s},
    }
    write_json(out / "report.json", report)
    with open(out / "throws.jsonl", "w") as f:
        import json
        for r in results:
            f.write(json.dumps({k: v for k, v in r.items() if k != "torque_log"}) + "\n")
    (out / "summary.md").write_text(make_summary(task, report, results, arm))
    for p in [out / "report.json", out / "throws.jsonl", out / "replay.json", out / "summary.md", *plots]:
        ev.file_written(p)
    ev.emit("task.done", task=task, summary=ev.rel(out / "summary.md"))
    return {"task": task, "dir": ev.rel(out), "report": ev.rel(out / "report.json"),
            **{k: report[k] for k in ("catch_rate", "reach_rate", "skipped_step_rate", "mean_margin_s",
                                      "failures", "worst_joint")}, "duration_s": report["meta"]["duration_s"]}


def make_report(variant: str, results: list[dict], arm: ArmModel) -> dict:
    n = len(results)
    out = {k: 0 for k in FAILURE_KEYS}
    caught = 0
    for r in results:
        if r["outcome"] == "caught":
            caught += 1
        else:
            out[r["outcome"]] += 1
    executed = [r for r in results if "peak_torque_frac" in r]
    margins = [r["margin_s"] for r in results if "margin_s" in r]
    if executed:
        pk = np.array([r["peak_torque_frac"] for r in executed])
        worst = arm.joint_names[int(np.argmax(pk.mean(0)))]
    else:
        pk, worst = None, None
    return {
        "variant": variant,
        "throws": n,
        "catch_rate": round(caught / n, 3) if n else 0.0,
        "reach_rate": round(sum(1 for r in results if r["reachable"]) / n, 3) if n else 0.0,
        "skipped_step_rate": round(sum(1 for r in results if r.get("skipped")) / n, 3) if n else 0.0,
        "mean_margin_s": round(float(np.mean(margins)), 3) if margins else None,
        "failures": out,
        "worst_joint": worst,
        "plots": [],
        "video": None,
        "skip_before_contact_rate": round(sum(1 for r in results if r.get("skip_before_contact")) / n, 3) if n else 0.0,
        # steppers losing position when the ball hits the cup (they need re-homing after such a catch)
        "skip_on_impact_rate": round(sum(1 for r in results if r.get("skip_on_impact")) / n, 3) if n else 0.0,
        "skip_on_impact_rate_of_contacts": round(sum(1 for r in results if r.get("skip_on_impact")) /
                                                 max(1, sum(1 for r in results if r.get("contact"))), 3),
        "skip_on_impact_by_joint": {j: sum(1 for r in results if r.get("skip_on_impact") and r.get("skip_joint") == j)
                                    for j in arm.joint_names},
        "give_rate": round(sum(1 for r in results if r.get("give")) / n, 3) if n else 0.0,
        "mean_give_speed_mps": round(float(np.mean([r["give_v_mps"] for r in results if r.get("give")])), 3)
        if any(r.get("give") for r in results) else None,
        "mean_impact_rel_speed_mps": round(float(np.mean([r["impact"]["rel_axial_mps"] for r in results
                                                          if "impact" in r])), 3)
        if any("impact" in r for r in results) else None,
        "mean_peak_torque_frac": {arm.joint_names[i]: round(float(pk[:, i].mean()), 3) for i in range(4)} if pk is not None else None,
        "mean_pred_err_m": round(float(np.mean([r["pred_err_m"] for r in results if "pred_err_m" in r])), 4)
        if any("pred_err_m" in r for r in results) else None,
    }


REPLAY_ORDER = ("caught", "bounced_out", "too_slow", "out_of_reach", "missed", "skipped_steps")


def pick_replay_throws(results: list[dict], k: int = 5) -> list[dict]:
    """3-5 representative throws: a typical catch, a catch that skipped on impact (if any), then one
    of each failure kind present, most common first."""
    by: dict[str, list] = {}
    for r in results:
        if r.get("replay"):
            by.setdefault(r["outcome"], []).append(r)
    picks: list[dict] = []
    caught = by.get("caught", [])
    if caught:
        clean = [r for r in caught if not r.get("skipped")] or caught
        picks.append(clean[0])
        skip = [r for r in caught if r.get("skip_on_impact") and r is not clean[0]]
        if skip:
            picks.append(skip[0])
    fails = sorted((o for o in by if o != "caught"), key=lambda o: (-len(by[o]), REPLAY_ORDER.index(o)))
    for o in fails:
        if len(picks) >= k:
            break
        picks.append(by[o][0])
    for r in caught[1:]:
        if len(picks) >= min(3, len(results)):
            break
        if r not in picks:
            picks.append(r)
    return picks[:k]


def make_replay(variant: str, results: list[dict], arm: ArmModel) -> dict:
    """sim/<task>/replay.json (contracts section 11)."""
    from ..cad.glb import JOINT_AXES
    throws = []
    for r in pick_replay_throws(results):
        rp = r["replay"]
        throws.append({"id": r["i"], "outcome": r["outcome"], "t": rp["t"], "q": rp["q"], "ball": rp["ball"],
                       "predicted": r["predicted"]["p"], "predicted_t0": r["predicted"]["t0"],
                       "t_decide": r["predicted"]["t_decide"],
                       "catch_point": r.get("catch_p"), "t_catch": r.get("t_catch"),
                       "give": r.get("give", False), "skip_on_impact": r.get("skip_on_impact", False)})
    return {"variant": variant, "dt": REPLAY_DT, "joint_names": list(arm.joint_names),
            "joint_axes": {k: list(v) for k, v in JOINT_AXES.items()},
            "units": "s, rad, m; world = arm base frame (z up, +x toward the thrower)",
            "rest_q": [round(float(x), 5) for x in arm.ready_pose()], "throws": throws}


def make_plots(d: Path, results: list[dict], arm: ArmModel, cfg: SimConfig) -> list[Path]:
    from . import style
    plt = style.apply()
    colors = {"caught": style.GOOD, "out_of_reach": "#A8A8A4", "too_slow": style.WARN,
              "skipped_steps": style.DANGER, "missed": "#7B4FD6", "bounced_out": style.ACCENT}
    fig, ax = plt.subplots(figsize=(6.8, 5.8))
    for oc, col in colors.items():
        sel = [r for r in results if r["outcome"] == oc]
        if oc == "caught":
            skip = np.array([r["land_xy"] for r in sel if r.get("skip_on_impact")]).reshape(-1, 2)
            sel = [r for r in sel if not r.get("skip_on_impact")]
            if len(skip):
                ax.scatter(skip[:, 0], skip[:, 1], s=18, facecolors="none", edgecolors=col, linewidths=1.0,
                           label=f"caught, steps lost on impact ({len(skip)})", alpha=0.9)
        pts = np.array([r["land_xy"] for r in sel]).reshape(-1, 2)
        if len(pts):
            ax.scatter(pts[:, 0], pts[:, 1], s=16, c=col, label=f"{oc.replace('_', ' ')} ({len(pts)})",
                       edgecolors="none", alpha=0.85)
    th = np.linspace(-math.pi, math.pi, 200)
    ax.plot(arm.reach * np.cos(th), arm.reach * np.sin(th), "--", c=style.INK, lw=0.9, label="reach")
    ax.scatter([0], [0], marker="s", c=style.INK, s=40, label="arm base")
    ax.set_aspect("equal")
    ax.set_xlabel("x (m, toward thrower)")
    ax.set_ylabel("y (m)")
    ax.set_title(f"Where the ball would land (no arm) - {arm.name}")
    ax.legend(loc="upper left")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    style.title_block(fig, "Landing points of the simulated throws", f"{arm.name} / sheet 1")
    p1 = d / "catch_map.png"
    fig.savefig(p1)
    plt.close(fig)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4.2))
    ex = [r for r in results if "peak_torque_frac" in r]
    if ex:
        pk = np.array([r["peak_torque_frac"] for r in ex])
        a1.boxplot([pk[:, i] for i in range(4)], tick_labels=arm.joint_names, widths=0.5,
                   boxprops=dict(color=style.INK, linewidth=0.9), medianprops=dict(color=style.ACCENT, linewidth=1.4),
                   whiskerprops=dict(color=style.INK, linewidth=0.8), capprops=dict(color=style.INK, linewidth=0.8),
                   flierprops=dict(marker="o", markersize=3, markeredgecolor=style.MUTED, markerfacecolor="none"))
        a1.axhline(1.0, c=style.DANGER, lw=0.9, ls=(0, (4, 3)))
        a1.set_ylabel("peak torque / pull-out torque (motor)")
        a1.set_title("Peak stepper load before contact")
    logs = [r for r in results if r.get("torque_log")]
    pick = next((r for r in logs if r["outcome"] == "caught"), logs[0] if logs else None)
    if pick:
        L = np.array(pick["torque_log"])
        for i in range(4):
            a2.plot(L[:, 0], L[:, 1 + i], lw=1.2, color=style.JOINT_COLORS.get(arm.joint_names[i]), label=arm.joint_names[i])
        a2.set_xlabel("time since release (s)")
        a2.set_ylabel("motor torque / holding torque")
        a2.set_title(f"Throw {pick['i']} ({pick['outcome']})")
        a2.legend()
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    style.title_block(fig, "Stepper load: peak before contact, and one throw in time", f"{arm.name} / sheet 2")
    p2 = d / "joint_torque.png"
    fig.savefig(p2)
    plt.close(fig)
    return [p1, p2]


def make_summary(task: str, rep: dict, results: list[dict], arm: ArmModel) -> str:
    f = rep["failures"]
    meta = rep["meta"]
    return f"""# Catch sim {rep['variant']} ({task})

{rep['throws']} simulated tosses from ~1.8 m, camera {meta['vision']['fps']:g} fps, {meta['vision']['latency_s']*1000:.0f} ms
latency, {meta['vision']['noise_m']*1000:.0f} mm noise, arm commits after {meta['vision']['observe_s']:.2f} s of tracking.
Steppers at {arm.microsteps} microsteps, step rate cap {meta['step_rate_hz']:g} Hz -> max motor speed
{max(meta['max_motor_rps']):.2f} rev/s. Math core: {meta['core']}.

- Catch rate: **{rep['catch_rate']:.0%}** (reach rate {rep['reach_rate']:.0%}).
- Failures: out of reach {f['out_of_reach']}, too slow {f['too_slow']}, skipped steps {f['skipped_steps']},
  missed (prediction/contact) {f['missed']}, bounced out {f['bounced_out']}.
- Skipped-step rate (any joint, any time incl. ball impact): {rep['skipped_step_rate']:.0%};
  before contact (during the move): {rep['skip_before_contact_rate']:.0%}; on impact: {rep['skip_on_impact_rate']:.0%}
  (by motor {rep['skip_on_impact_by_joint']}): re-home after those catches.
- Soft catch: give {arm.give_m:g} m (used in {rep['give_rate']:.0%} of throws), compliance {arm.compliance};
  mean ball-vs-cup speed at impact {rep['mean_impact_rel_speed_mps']} m/s.
- Motors: {arm.coupling} coupling (motor angle = ratio x C q, see report meta motor_map).
- Mean planned margin: {rep['mean_margin_s']} s; mean prediction error at catch: {rep['mean_pred_err_m']} m.
- Worst joint: {rep['worst_joint']} (mean peak load {rep['mean_peak_torque_frac']}).

- Arm: style {arm.style}, masses {"from the CAD solids" if arm.mass_props else "from link_mass_kg_per_m (estimate)"};
  cup liner {arm.liner} with ball restitution {arm.cup_restitution:.2f} (estimate). Most balls that
  reach the cup in time and still fail bounce off its floor, so the catch rate follows this number.

Replay: replay.json (3-5 throws at 100 Hz for the app viewer).

Open issues: one-shot plan (no re-planning); stepper model is a sinusoidal-torque
approximation; liner restitution is an estimate; rotor inertia is lumped per joint (the
coupling's off-diagonal rotor terms are ignored); belt stretch and backlash are not modelled.
"""
