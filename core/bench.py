"""Tiny benchmark for mechy_core. Run: python core/bench.py"""
import os
import time

import numpy as np

import mechy_core as mc


def rate(fn, n, reps=3):
    best = float("inf")
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t)
    return n / best


def main():
    rng = np.random.default_rng(0)
    arm = mc.default_arm()
    motors = mc.default_motors()
    J = np.array([0.012, 0.010, 0.004, 0.0005])

    targets = np.c_[rng.uniform(0.1, 0.45, 2000), rng.uniform(-0.3, 0.3, 2000), rng.uniform(0.0, 0.6, 2000)]
    print(f"ik (python loop)           {rate(lambda: [arm.ik(p, 0.0) for p in targets], len(targets)):12,.0f} solves/s")

    traj = mc.ball_predict([1.8, 0.0, 1.0], [-4.5, 0.0, 3.0], t_max=1.0)
    print(f"ball_predict (1 s, 2 ms)   {rate(lambda: [mc.ball_predict([1.8, 0, 1], [-4.5, 0, 3], t_max=1.0) for _ in range(200)], 200):12,.0f} traj/s")
    pts = traj[::8][:15]  # 15 samples at ~60 Hz
    print(f"ball_fit (15 samples)      {rate(lambda: [mc.ball_fit(pts) for _ in range(100)], 100):12,.0f} fits/s")

    q0 = np.zeros(4)
    Q1 = rng.uniform(-1.5, 1.5, (20000, 4))
    T = rng.uniform(0.1, 0.6, len(Q1))
    print(f"plan_move (python loop)    {rate(lambda: [mc.plan_move(q0, Q1[i], motors, J, T[i]) for i in range(2000)], 2000):12,.0f} solves/s")
    print(f"plan_batch threads=1       {rate(lambda: mc.plan_batch(q0, Q1, motors, J, T, threads=1), len(Q1)):12,.0f} solves/s")
    print(f"plan_batch threads=all({os.cpu_count()}) {rate(lambda: mc.plan_batch(q0, Q1, motors, J, T), len(Q1)):12,.0f} solves/s")


if __name__ == "__main__":
    main()
