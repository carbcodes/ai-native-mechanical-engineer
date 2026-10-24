import math
import os

import numpy as np
import pytest

from mechy import fallback_core as fc
from mechy.arm_model import ArmModel


def test_fallback_ik_fk_roundtrip():
    arm = fc.default_arm()
    rng = np.random.default_rng(0)
    n = 0
    for _ in range(500):
        q = rng.uniform(arm.limits[:, 0], arm.limits[:, 1])
        p, pitch = arm.fk(q)
        s = arm.ik(p, pitch, seed=q)
        if s is None:   # pose leaning back over the base: IK never returns those
            continue
        p2, pitch2 = arm.fk(s)
        assert np.allclose(p2, p, atol=1e-9) and abs(math.remainder(pitch2 - pitch, 2 * math.pi)) < 1e-9
        n += 1
    assert n > 300


def test_fallback_ball_and_motion():
    tr = fc.ball_predict([1.8, 0, 1.0], [-2.2, 0, 3.0], t_max=0.3, t0=1.0)
    assert tr[0, 0] == 1.0 and abs(tr[-1, 0] - 1.3) < 1e-9
    fit = fc.ball_fit(tr[::10])
    assert np.allclose(fit["v0"], [-2.2, 0, 3.0], atol=1e-4) and fit["t0"] == 1.0
    m = fc.default_motors()
    r = fc.plan_move(np.zeros(4), np.array([0.5, 0.5, 0.5, 0.5]), m, [0.02] * 4, 0.5)
    assert set(r) >= {"feasible", "t_needed", "t_per_joint", "peak_torque_frac", "limiting_joint"}


def test_fallback_matches_mechy_core():
    mc = pytest.importorskip("mechy_core")
    rng = np.random.default_rng(1)
    A, B = mc.default_arm(), fc.default_arm()
    for _ in range(300):
        q = rng.uniform(A.limits[:, 0], A.limits[:, 1])
        pa, ta = A.fk(q)
        pb, tb = B.fk(q)
        assert np.allclose(pa, pb) and abs(ta - tb) < 1e-12
        a, b = A.ik(pa, ta, seed=q), B.ik(pa, ta, seed=q)
        assert (a is None) == (b is None)
        if a is not None:
            assert np.allclose(a, b, atol=1e-9)
    pts = np.c_[np.arange(10) / 60, rng.normal(0, 0.003, (10, 3)) + [1.8, 0, 1.0]]
    pts[:, 1] -= 2.0 * pts[:, 0]
    fa, fb = mc.ball_fit(pts), fc.ball_fit(pts)
    assert np.allclose(fa["p0"], fb["p0"], atol=1e-6) and np.allclose(fa["v0"], fb["v0"], atol=1e-5)
    Ma, Mb = mc.default_motors(), fc.default_motors()
    for _ in range(10):
        q0, q1 = rng.uniform(-1, 1, 4), rng.uniform(-1, 1, 4)
        J, L = rng.uniform(0.001, 0.04, 4), rng.uniform(0, 0.8, 4)
        ra = mc.plan_move(q0, q1, Ma, J, 0.4, load_torque=L)
        rb = fc.plan_move(q0, q1, Mb, J, 0.4, load_torque=L)
        assert np.allclose(ra["t_per_joint"], rb["t_per_joint"], rtol=1e-9)
        assert np.allclose(ra["peak_torque_frac"], rb["peak_torque_frac"], rtol=1e-4)
        assert ra["feasible"] == rb["feasible"] and ra["limiting_joint"] == rb["limiting_joint"]


def test_engine_uses_real_core_when_present():
    pytest.importorskip("mechy_core")
    if os.environ.get("MECHY_FORCE_FALLBACK"):
        pytest.skip("fallback forced")
    from mechy.core import core_name
    assert core_name() == "mechy_core"


def test_step_rate_cap(project):
    from mechy.arm_model import load_arm
    a4, a16 = load_arm(project, "v1"), load_arm(project, "v1", microsteps=16)   # example drivers: 4 microsteps
    assert a4.microsteps == 4
    assert abs(a4.max_speed_rps(1) - 5.0) < 1e-9 and abs(a16.max_speed_rps(1) - 1.25) < 1e-9
    assert abs(a16.core_motors()[1].max_joint_speed - 2 * math.pi * 1.25 / a16.gear[1]) < 1e-9
