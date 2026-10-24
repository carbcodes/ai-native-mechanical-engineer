"""Python model of the firmware's synchronised trapezoid (must match mechy_arm.ino `plan_segment`).

All four motors follow one normalised profile s(t) in [0, 1] (accelerate, cruise, decelerate),
so motor i moves D_i * s(t) steps and every motor arrives at the same time. The firmware runs the
profile at UPDATE_HZ = TICK_HZ / TICKS_PER_UPDATE (rate updates) and steps a virtual master axis
of max|D_i| steps from a TICK_HZ timer interrupt; real motors follow it by Bresenham.

Given a requested duration T, the move is stretched to the shortest feasible duration when the
per-motor speed (V_MAX steps/s) or acceleration (A_MAX steps/s^2) caps would be exceeded.
"""

from __future__ import annotations

import math

import numpy as np

PREFERRED_ACC_FRAC = 1.0 / 3.0       # accelerate for T/3, cruise T/3, brake T/3 when possible
MAX_STRETCH_ITERS = 2000
CAP_TOL = 1e-4             # float32 slack in the firmware's own check


def min_duration(D, vmax, amax) -> float:
    """Shortest duration (s) for steps D (4,) under per-motor caps (continuous profile)."""
    A = np.abs(np.asarray(D, float))
    mv = A > 0
    if not mv.any():
        return 0.0
    Vs = float(np.min(np.asarray(vmax, float)[mv] / A[mv]))
    As = float(np.min(np.asarray(amax, float)[mv] / A[mv]))
    if math.sqrt(As) <= Vs:
        return 2.0 / math.sqrt(As)
    return 1.0 / Vs + Vs / As


def plan(D, T_req: float, vmax, amax, tick_hz: float, ticks_per_update: int) -> dict:
    """Mirror of the firmware planner. Returns T (actual duration, s), stretched flag, the
    discrete profile (n_total, n_acc updates) and each motor's peak step rate and acceleration."""
    D = np.asarray(np.round(D), np.int64)
    A = np.abs(D).astype(float)
    dmax = float(A.max()) if len(A) else 0.0
    U = tick_hz / ticks_per_update
    if dmax == 0:
        return {"T": 0.0, "T_req": float(T_req), "stretched": False, "n_total": 0, "n_acc": 0,
                "peak_rate_hz": np.zeros(len(A)), "peak_acc": np.zeros(len(A)), "dmax": 0}
    vmax = np.asarray(vmax, float)
    amax = np.asarray(amax, float)
    mv = A > 0
    Vs = float(np.min(vmax[mv] / A[mv]))
    As = float(np.min(amax[mv] / A[mv]))
    Tmin = max(min_duration(D, vmax, amax), 2.0 / U)
    T = max(float(T_req), Tmin)
    n_total = max(2, int(math.ceil(T * U - 1e-6)))
    n_acc, peak_hz, acc = 1, None, None
    for _ in range(MAX_STRETCH_ITERS):
        nt = float(n_total)
        # accel updates n_acc must keep the cruise rate under Vs and the acceleration under As:
        #   n_total - n_acc >= U / Vs   and   n_acc * (n_total - n_acc) >= U^2 / As
        hi_n = int(math.floor(min(nt / 2.0, nt - U / Vs) + 1e-4))
        disc = nt * nt - 4.0 * U * U / As
        if disc >= 0 and hi_n >= 1:
            lo_n = max(1, int(math.ceil(0.5 * (nt - math.sqrt(disc)) - 1e-4)))
            if lo_n <= hi_n:
                n_acc = min(max(int(round(nt * PREFERRED_ACC_FRAC)), lo_n), hi_n)
                peak_tick = dmax / ((n_total - n_acc) * ticks_per_update)      # master steps per tick
                drate_tick = peak_tick / n_acc                                    # per update
                peak_hz = A / dmax * peak_tick * tick_hz
                acc = A / dmax * drate_tick * tick_hz * U
                if np.all(peak_hz <= vmax * (1 + CAP_TOL)) and np.all(acc <= amax * (1 + CAP_TOL)) \
                        and peak_tick <= 1.0:
                    break
        n_total += 1
    T_act = n_total / U
    return {"T": T_act, "T_req": float(T_req), "stretched": bool(T_act > float(T_req) + 1.0 / U + 1e-6),   # > rounding up to a whole update
            "n_total": n_total, "n_acc": n_acc, "peak_rate_hz": peak_hz, "peak_acc": acc, "dmax": int(dmax)}


def sample(pl: dict, D, t: float) -> np.ndarray:
    """Continuous position (steps, (4,)) at time t of a plan from `plan` (for previews/dry runs)."""
    D = np.asarray(D, float)
    if pl["n_total"] == 0:
        return np.zeros_like(D)
    T = pl["T"]
    U = pl["n_total"] / T
    ta = pl["n_acc"] / U
    t = min(max(t, 0.0), T)
    v = 1.0 / (T - ta)
    a = v / ta
    if t < ta:
        s = 0.5 * a * t * t
    elif t < T - ta:
        s = 0.5 * a * ta * ta + v * (t - ta)
    else:
        s = 1.0 - 0.5 * a * (T - t) ** 2
    return D * s
