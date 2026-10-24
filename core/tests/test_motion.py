import numpy as np
import pytest

import mechy_core as mc

J_LOAD = np.array([0.012, 0.010, 0.004, 0.0005])


def test_stepper_torque_curve():
    m = mc.Stepper(mc.NEMA17_TORQUE_CURVE, 3.0, 5.4e-6)
    assert m.torque_at(0) == pytest.approx(0.45)
    assert m.torque_at(1) == pytest.approx(0.425)
    assert m.torque_at(7.5) == pytest.approx(0.20)
    assert m.torque_at(10) == pytest.approx(0.12)
    assert m.torque_at(10.5) == 0.0
    assert m.max_speed_rps == 10
    assert m.max_joint_speed == pytest.approx(2 * np.pi * 10 / 3)
    with pytest.raises(ValueError):
        mc.Stepper([[0, 0.4], [0, 0.3]], 1.0, 1e-6)


def test_constant_torque_matches_closed_form():
    # Flat torque curve -> constant acceleration, exact trapezoid formulas.
    T, Jr, N, Jl, s = 0.4, 5e-6, 4.0, 0.02, 0.7
    m = mc.Stepper([[0, T], [50, T]], N, Jr)
    alpha = s * T / (Jr + Jl / N**2)        # motor rad/s^2
    w = 2 * np.pi * 50                      # motor rad/s
    short = 0.05                            # joint rad
    D = short * N
    assert mc.min_move_time(m, Jl, short, s) == pytest.approx(2 * np.sqrt(D / alpha), rel=1e-12)
    long_ = 200.0
    D = long_ * N
    assert D > w**2 / alpha
    assert mc.min_move_time(m, Jl, long_, s) == pytest.approx(D / w + w / alpha, rel=1e-12)


def test_plan_move_monotonic_in_t_avail(motors, rng):
    for _ in range(30):
        q0 = rng.uniform(-1, 1, 4)
        q1 = rng.uniform(-1, 1, 4)
        ts = np.linspace(0.02, 1.0, 60)
        res = [mc.plan_move(q0, q1, motors, J_LOAD, t) for t in ts]
        feas = np.array([r["feasible"] for r in res])
        tneed = np.array([r["t_needed"] for r in res])
        frac = np.array([r["peak_torque_frac"] for r in res])
        assert np.all(tneed == tneed[0])            # t_needed doesn't depend on t_avail
        assert np.all(np.diff(feas.astype(int)) >= 0)  # once feasible, stays feasible
        assert np.all(feas == (ts >= tneed[0]))
        assert np.all(frac[1:] <= frac[:-1])  # more time -> less torque (inf allowed)
        # Feasible exactly when every joint fits under the 70 % safety fraction.
        assert np.all(feas == np.all(frac <= 0.7, axis=1))


def test_plan_move_physics_sanity(motors):
    q0 = np.zeros(4)
    r0 = mc.plan_move(q0, q0, motors, J_LOAD, 0.1)
    assert r0["feasible"] and r0["t_needed"] == 0.0
    np.testing.assert_array_equal(r0["peak_torque_frac"], 0.0)
    small = mc.plan_move(q0, [0.5, 0, 0, 0], motors, J_LOAD, 1.0)
    big = mc.plan_move(q0, [0.5, 0, 0, 0], motors, J_LOAD * 10, 1.0)
    assert big["t_needed"] > small["t_needed"]
    # Gravity load the motor cannot hold even at standstill.
    held = mc.plan_move(q0, [0, 0.5, 0, 0], motors, J_LOAD, 1.0, load_torque=[0, 10.0, 0, 0])
    assert not held["feasible"] and np.isinf(held["t_needed"])
    assert held["limiting_joint"] == 1
    # A move that respects max speed: 3 rad at the base can't beat max speed.
    far = mc.plan_move(q0, [3.0, 0, 0, 0], motors, J_LOAD, 5.0)
    assert far["t_needed"] > 3.0 / motors[0].max_joint_speed


def test_batch_equals_loop(motors, rng):
    n = 500
    q0 = rng.uniform(-1, 1, 4)
    Q1 = rng.uniform(-1.5, 1.5, (n, 4))
    T = rng.uniform(0.05, 0.6, n)
    tl = np.array([0.0, 0.3, 0.1, 0.01])
    batch = mc.plan_batch(q0, Q1, motors, J_LOAD, T, load_torque=tl)
    single = mc.plan_batch(q0, Q1, motors, J_LOAD, T, load_torque=tl, threads=1)
    for k in batch:
        np.testing.assert_array_equal(batch[k], single[k])
    for i in range(n):
        r = mc.plan_move(q0, Q1[i], motors, J_LOAD, T[i], load_torque=tl)
        assert batch["feasible"][i] == r["feasible"]
        assert batch["t_needed"][i] == r["t_needed"]
        np.testing.assert_array_equal(batch["t_per_joint"][i], r["t_per_joint"])
        np.testing.assert_array_equal(batch["peak_torque_frac"][i], r["peak_torque_frac"])
        assert batch["limiting_joint"][i] == r["limiting_joint"]
    assert batch["feasible"].dtype == bool
    assert 0 < batch["feasible"].sum() < n  # the sample hits both cases


def test_batch_broadcasting(motors):
    Q1 = np.array([[0.2, 0.1, 0, 0], [1.0, 1.0, 1.0, 1.0]])
    a = mc.plan_batch(np.zeros(4), Q1, motors, J_LOAD, 0.2)
    b = mc.plan_batch(np.zeros((2, 4)), Q1, motors, np.tile(J_LOAD, (2, 1)), [0.2, 0.2])
    for k in a:
        np.testing.assert_array_equal(a[k], b[k])
    with pytest.raises(ValueError):
        mc.plan_batch(np.zeros(4), Q1, motors, J_LOAD, [0.2, 0.2, 0.2])


def test_stepper_pickle(motors):
    import pickle

    m2 = pickle.loads(pickle.dumps(motors[1]))
    assert m2.gear_ratio == 4.0
    np.testing.assert_array_equal(m2.torque_curve, mc.NEMA17_TORQUE_CURVE)
