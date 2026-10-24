"""Pure-Python stand-in for the C++ `mechy_core` module (contracts sections 7 and 7.1).

Same API, same conventions, same numerics as core/src (ported, slower). `mechy.core.get_core()`
returns the real `mechy_core` when it imports and this module otherwise.

* Ball: a = (0,0,-g) - k|v|v, k = rho*Cd*A/(2m). RK4. `ball_fit` returns the state at
  t0 = the earliest sample. `ball_predict(..., t0=0.0)` rows are [t, x, y, z] from t0.
* Arm: q0 base yaw about +z (0 = +x); q1 shoulder elevation above horizontal; q2 elbow,
  q3 wrist relative to the previous link, positive = up. Hand pitch = q1+q2+q3, the hand
  elevation above horizontal, pointing away from the base axis. Tool point = end of hand.
  Positive elevation is a rotation about the arm-plane -y axis (MJCF +y hinges flip sign).
* Motors: per-joint time-optimal rest-to-rest move using `safety` x pull-out torque minus
  the static load torque; `peak_torque_frac` = smallest fraction that finishes in t_avail.
"""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np

__all__ = ["ball_drag_k", "ball_fit", "ball_predict", "ball_intercept", "Arm", "Stepper",
           "min_move_time", "plan_move", "plan_batch", "default_arm", "default_motors",
           "NEMA17_TORQUE_CURVE", "NEMA17_ROTOR_INERTIA", "V1_GEAR_RATIOS", "IS_FALLBACK"]

IS_FALLBACK = True
NEMA17_TORQUE_CURVE = np.array([[0.0, 0.45], [2.0, 0.40], [5.0, 0.28], [10.0, 0.12]])
NEMA17_ROTOR_INERTIA = 5.4e-6
V1_GEAR_RATIOS = (3.0, 4.0, 3.0, 2.0)
_FIT_STEP = 0.002
_TWO_PI = 2 * math.pi


# ---------------------------------------------------------------------- ball
def ball_drag_k(mass: float = 0.057, diameter: float = 0.067, cd: float = 0.55, rho: float = 1.2) -> float:
    return rho * cd * math.pi * (diameter / 2) ** 2 / (2 * mass)


def _accel(v: np.ndarray, k: float, g: float) -> np.ndarray:
    sp = np.linalg.norm(v, axis=-1, keepdims=True)
    a = -k * sp * v
    a[..., 2] -= g
    return a


def _rk4(p: np.ndarray, v: np.ndarray, h: float, k: float, g: float):
    k1v, k1a = v, _accel(v, k, g)
    k2v = v + k1a * (0.5 * h)
    k2a = _accel(k2v, k, g)
    k3v = v + k2a * (0.5 * h)
    k3a = _accel(k3v, k, g)
    k4v = v + k3a * h
    k4a = _accel(k4v, k, g)
    return (p + (k1v + 2 * k2v + 2 * k3v + k4v) * (h / 6),
            v + (k1a + 2 * k2a + 2 * k3a + k4a) * (h / 6))


def ball_predict(p0, v0, dt: float = 0.002, t_max: float = 2.0, mass: float = 0.057,
                 diameter: float = 0.067, cd: float = 0.55, rho: float = 1.2, g: float = 9.81,
                 t0: float = 0.0) -> np.ndarray:
    if dt <= 0:
        raise ValueError("dt must be > 0")
    k = ball_drag_k(mass, diameter, cd, rho)
    n = int(math.floor(t_max / dt + 1e-9))
    p, v = np.asarray(p0, float).copy(), np.asarray(v0, float).copy()
    rows = [(t0, *p)]
    t = 0.0
    for i in range(n):
        p, v = _rk4(p, v, dt, k, g)
        t = (i + 1) * dt
        rows.append((t0 + t, *p))
    rest = t_max - t
    if rest > 1e-9 * dt:
        p, v = _rk4(p, v, rest, k, g)
        rows.append((t0 + t_max, *p))
    return np.array(rows, float)


def _simulate_at(P: np.ndarray, tau: np.ndarray, k: float, g: float) -> np.ndarray:
    """P (B,6) states at tau=0 -> positions (len(tau), B, 3)."""
    p, v = P[:, :3].copy(), P[:, 3:].copy()
    out = np.empty((len(tau), len(P), 3))
    t = 0.0
    for j, tj in enumerate(tau):
        gap = tj - t
        if gap > 0:
            n = max(1, int(math.ceil(gap / _FIT_STEP)))
            h = gap / n
            for _ in range(n):
                p, v = _rk4(p, v, h, k, g)
            t = tj
        out[j] = p
    return out


def ball_fit(points, mass: float = 0.057, diameter: float = 0.067, cd: float = 0.55,
             rho: float = 1.2, g: float = 9.81) -> dict:
    pts = np.asarray(points, float)
    if pts.ndim != 2 or pts.shape[1] != 4 or len(pts) < 3:
        raise ValueError("ball_fit needs (N,4) [t,x,y,z] with N >= 3")
    pts = pts[np.argsort(pts[:, 0], kind="stable")]
    t0 = float(pts[0, 0])
    tau = pts[:, 0] - t0
    if tau[-1] <= 0:
        raise ValueError("ball_fit needs samples spread in time")
    xyz = pts[:, 1:]
    A = np.stack([np.ones_like(tau), tau], axis=1)
    x = np.zeros(6)
    for j in range(3):
        rhs = xyz[:, j] + (0.5 * g * tau ** 2 if j == 2 else 0.0)
        sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
        x[j], x[3 + j] = sol
    k = ball_drag_k(mass, diameter, cd, rho)
    eps = np.full(6, 1e-6)
    lam = 1e-3
    cost = float(np.sum((_simulate_at(x[None], tau, k, g)[:, 0] - xyz) ** 2))
    it = 0
    for it in range(30):
        cand = np.vstack([x, x + np.diag(eps)])
        pred = _simulate_at(cand, tau, k, g)                       # (N,7,3)
        r = (xyz - pred[:, 0]).reshape(-1)
        J = ((pred[:, 1:] - pred[:, :1]) / eps[None, :, None]).transpose(0, 2, 1).reshape(-1, 6)
        H = J.T @ J
        b = J.T @ r
        improved = False
        dx = np.zeros(6)
        for _ in range(8):
            dx = np.linalg.solve(H + lam * np.diag(np.diag(H) + 1e-12), b)
            xn = x + dx
            cn = float(np.sum((_simulate_at(xn[None], tau, k, g)[:, 0] - xyz) ** 2))
            if cn <= cost:
                x, cost, lam, improved = xn, cn, max(lam * 0.3, 1e-9), True
                break
            lam *= 10
        if not improved or np.max(np.abs(dx)) < 1e-9:
            break
    return {"p0": x[:3].copy(), "v0": x[3:].copy(), "t0": t0,
            "residual": math.sqrt(cost / len(pts)), "iterations": it + 1}


def ball_intercept(traj, center, radius: float):
    traj = np.asarray(traj, float)
    c = np.asarray(center, float)
    if len(traj) == 0 or radius < 0:
        return None

    def seg_v(i):
        dt = traj[i + 1, 0] - traj[i, 0]
        return (traj[i + 1, 1:4] - traj[i, 1:4]) / dt if dt > 0 else np.zeros(3)

    prev = traj[0, 1:4]
    if np.dot(prev - c, prev - c) <= radius * radius:
        return {"t": float(traj[0, 0]), "p": prev.copy(), "v": seg_v(0) if len(traj) > 1 else np.zeros(3)}
    for i in range(1, len(traj)):
        cur = traj[i, 1:4]
        d = cur - prev
        f = prev - c
        A, B, C = d @ d, 2 * f @ d, f @ f - radius * radius
        disc = B * B - 4 * A * C
        if A > 0 and disc >= 0:
            s = (-B - math.sqrt(disc)) / (2 * A)
            if 0 <= s <= 1:
                ta, tb = traj[i - 1, 0], traj[i, 0]
                return {"t": float(ta + s * (tb - ta)), "p": prev + d * s, "v": seg_v(i - 1)}
        prev = cur
    return None


# ----------------------------------------------------------------------- arm
def _wrap(a: float) -> float:
    a = math.fmod(a + math.pi, _TWO_PI)
    if a < 0:
        a += _TWO_PI
    return a - math.pi


_DEFAULT_LIMITS = np.radians([[-150, 150], [-10, 120], [-135, 135], [-90, 90]])


class Arm:
    def __init__(self, base_height: float = 0.12, upper: float = 0.22, fore: float = 0.20,
                 hand: float = 0.06, limits=None):
        if not (upper > 0 and fore > 0 and hand >= 0):
            raise ValueError("Arm: link lengths must be positive (hand >= 0)")
        self.base_height, self.upper, self.fore, self.hand = map(float, (base_height, upper, fore, hand))
        lim = _DEFAULT_LIMITS if limits is None else np.asarray(limits, float).reshape(4, 2)
        if np.any(lim[:, 0] > lim[:, 1]):
            raise ValueError("Arm: limit lower > upper")
        self._lim = lim.copy()

    @property
    def limits(self) -> np.ndarray:
        return self._lim.copy()

    def within_limits(self, q, tol: float = 1e-9) -> bool:
        q = np.asarray(q, float)
        return bool(np.all(q >= self._lim[:, 0] - tol) and np.all(q <= self._lim[:, 1] + tol))

    def fk(self, q):
        q = np.asarray(q, float)
        s1, s12, s123 = q[1], q[1] + q[2], q[1] + q[2] + q[3]
        r = self.upper * math.cos(s1) + self.fore * math.cos(s12) + self.hand * math.cos(s123)
        z = self.base_height + self.upper * math.sin(s1) + self.fore * math.sin(s12) + self.hand * math.sin(s123)
        return np.array([r * math.cos(q[0]), r * math.sin(q[0]), z]), _wrap(s123)

    def ik(self, target_xyz, hand_pitch: float, seed=None):
        x, y, z = (float(v) for v in target_xyz)
        if not all(math.isfinite(v) for v in (x, y, z, hand_pitch)):
            return None
        r = math.hypot(x, y)
        yaw = (float(seed[0]) if seed is not None else 0.0) if r < 1e-9 else math.atan2(y, x)
        rw = r - self.hand * math.cos(hand_pitch)
        zw = z - self.base_height - self.hand * math.sin(hand_pitch)
        a, b = self.upper, self.fore
        c2 = (rw * rw + zw * zw - a * a - b * b) / (2 * a * b)
        if c2 > 1 + 1e-9 or c2 < -1 - 1e-9:
            return None
        q2abs = math.acos(min(1.0, max(-1.0, c2)))
        ref = np.asarray(seed, float) if seed is not None else np.array([yaw, 0, 0, 0.0])
        best, out = math.inf, None
        for sgn in (1.0, -1.0):
            q2 = sgn * q2abs
            q1 = math.atan2(zw, rw) - math.atan2(b * math.sin(q2), a + b * math.cos(q2))
            q = np.array([yaw, _wrap(q1), q2, 0.0])
            q[3] = _wrap(hand_pitch - q[1] - q[2])
            if self.within_limits(q):
                cost = float(np.sum((q - ref) ** 2))
                if cost < best:
                    best, out = cost, q
            if q2abs == 0.0:
                break
        if out is not None:
            out = np.clip(out, self._lim[:, 0], self._lim[:, 1])
        return out

    def reachable(self, target_xyz, hand_pitch: float) -> bool:
        return self.ik(target_xyz, hand_pitch) is not None

    def __reduce__(self):
        return (Arm, (self.base_height, self.upper, self.fore, self.hand, self._lim))


def default_arm() -> Arm:
    return Arm(0.12, 0.22, 0.20, 0.06)


# ------------------------------------------------------------------ steppers
class Stepper:
    def __init__(self, torque_curve, gear_ratio: float = 1.0, rotor_inertia: float = 5.4e-6,
                 max_speed_rps: float = -1.0):
        tc = np.asarray(torque_curve, float).reshape(-1, 2)
        if len(tc) == 0 or np.any(tc < 0) or np.any(np.diff(tc[:, 0]) <= 0):
            raise ValueError("Stepper: bad torque curve")
        if gear_ratio <= 0 or rotor_inertia < 0:
            raise ValueError("Stepper: bad gear ratio or inertia")
        self.torque_curve = tc
        self.gear_ratio = float(gear_ratio)
        self.rotor_inertia = float(rotor_inertia)
        self.max_speed_rps = float(max_speed_rps) if max_speed_rps and max_speed_rps > 0 else float(tc[-1, 0])

    def torque_at(self, rps: float) -> float:
        rps = abs(float(rps))
        if rps > self.max_speed_rps * (1 + 1e-12):
            return 0.0
        tc = self.torque_curve
        return float(np.interp(rps, tc[:, 0], tc[:, 1]))

    @property
    def max_joint_speed(self) -> float:
        return _TWO_PI * self.max_speed_rps / self.gear_ratio

    def __reduce__(self):
        return (Stepper, (self.torque_curve, self.gear_ratio, self.rotor_inertia, self.max_speed_rps))


def default_motors(gear_ratios=V1_GEAR_RATIOS) -> list:
    return [Stepper(NEMA17_TORQUE_CURVE, float(n), NEMA17_ROTOR_INERTIA) for n in gear_ratios]


def min_move_time(motor: Stepper, load_inertia: float, dist: float, safety: float = 0.7,
                  load_torque: float = 0.0) -> float:
    N = motor.gear_ratio
    D = abs(dist) * N
    if D == 0:
        return 0.0
    J = motor.rotor_inertia + max(0.0, load_inertia) / (N * N)
    tl = abs(load_torque) / N

    def net(w):
        return safety * motor.torque_at(w / _TWO_PI) - tl

    if not net(0.0) > 0:
        return math.inf
    w_max = _TWO_PI * motor.max_speed_rps
    w_c = w_max
    knots = [0.0] + [p * _TWO_PI for p in motor.torque_curve[:, 0] if p > 0 and p * _TWO_PI < w_max] + [w_max]
    for i in range(1, len(knots)):
        fb = net(knots[i] * (1 - 1e-12))
        if fb <= 0:
            fa = net(knots[i - 1])
            w_c = 0.95 * (knots[i - 1] + (knots[i] - knots[i - 1]) * fa / (fa - fb))
            break
    grid = 48
    dw = w_c / grid
    t_acc = d_acc = 0.0
    half = 0.5 * D
    for k in range(grid):
        wa = k * dw
        wb = wa + dw
        alpha = net(wa + 0.5 * dw) / J
        dd = (wb * wb - wa * wa) / (2 * alpha)
        if d_acc + dd >= half:
            wp = math.sqrt(wa * wa + 2 * alpha * (half - d_acc))
            return 2 * (t_acc + (wp - wa) / alpha)
        d_acc += dd
        t_acc += dw / alpha
    return 2 * t_acc + (D - 2 * d_acc) / w_c


def _required_frac(m: Stepper, J: float, tl: float, d: float, t_avail: float, s_max: float,
                   s_known: float, t_known: float) -> float:
    if d == 0:
        return 0.0
    if not t_avail > 0:
        return math.inf
    t0 = m.torque_at(0.0)
    lo = abs(tl) / m.gear_ratio / t0 if t0 > 0 else 0.0
    hi = s_max
    if 0 < s_known < s_max:
        if t_known <= t_avail:
            hi = s_known
        else:
            lo = max(lo, s_known)
    if hi == s_max and min_move_time(m, J, d, s_max, tl) > t_avail:
        return math.inf
    while hi - lo > 1e-5:
        mid = 0.5 * (lo + hi)
        if min_move_time(m, J, d, mid, tl) <= t_avail:
            hi = mid
        else:
            lo = mid
    return hi


def plan_move(q0, q1, motors: Sequence[Stepper], load_inertia, t_avail: float, safety: float = 0.7,
              load_torque=None) -> dict:
    n = len(motors)
    q0 = np.asarray(q0, float).reshape(n)
    q1 = np.asarray(q1, float).reshape(n)
    Jl = np.asarray(load_inertia, float).reshape(n)
    tl = np.zeros(n) if load_torque is None else np.asarray(load_torque, float).reshape(n)
    t_per = np.zeros(n)
    frac = np.zeros(n)
    t_needed, limiting = 0.0, -1
    for i in range(n):
        d = q1[i] - q0[i]
        t_per[i] = min_move_time(motors[i], Jl[i], d, safety, tl[i])
        frac[i] = _required_frac(motors[i], Jl[i], tl[i], d, t_avail, 4.0, safety, t_per[i])
        if limiting < 0 or t_per[i] > t_needed:
            t_needed, limiting = t_per[i], i
    return {"feasible": bool(math.isfinite(t_needed) and t_needed <= t_avail), "t_needed": float(t_needed),
            "t_per_joint": t_per, "peak_torque_frac": frac, "limiting_joint": limiting}


def plan_batch(q0, Q1, motors, load_inertia, T_avail, safety: float = 0.7, load_torque=None,
               threads: int = 0) -> dict:
    n = len(motors)
    Q1 = np.asarray(Q1, float).reshape(-1, n)
    N = len(Q1)
    Q0 = np.broadcast_to(np.asarray(q0, float), (N, n))
    JL = np.broadcast_to(np.asarray(load_inertia, float), (N, n))
    TL = None if load_torque is None else np.broadcast_to(np.asarray(load_torque, float), (N, n))
    TA = np.broadcast_to(np.asarray(T_avail, float), (N,))
    res = [plan_move(Q0[i], Q1[i], motors, JL[i], float(TA[i]), safety, None if TL is None else TL[i])
           for i in range(N)]
    return {
        "feasible": np.array([r["feasible"] for r in res], bool),
        "t_needed": np.array([r["t_needed"] for r in res], float),
        "t_per_joint": np.array([r["t_per_joint"] for r in res], float).reshape(N, n),
        "peak_torque_frac": np.array([r["peak_torque_frac"] for r in res], float).reshape(N, n),
        "limiting_joint": np.array([r["limiting_joint"] for r in res], int),
    }
