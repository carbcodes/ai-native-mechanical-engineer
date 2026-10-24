import numpy as np
import pytest

import mechy_core as mc

G = 9.81


def test_predict_matches_analytic_without_drag():
    p0, v0 = np.array([0.1, -0.2, 1.0]), np.array([3.0, 0.5, 3.5])
    traj = mc.ball_predict(p0, v0, dt=0.002, t_max=1.0, cd=0.0)
    t = traj[:, 0]
    expect = p0 + np.outer(t, v0) + np.outer(0.5 * t**2, [0, 0, -G])
    assert traj.shape == (501, 4)
    assert t[0] == 0.0 and t[-1] == pytest.approx(1.0)
    np.testing.assert_allclose(traj[:, 1:], expect, atol=1e-10)


def test_predict_t0_offset_and_partial_last_step():
    traj = mc.ball_predict([0, 0, 1], [1, 0, 0], dt=0.003, t_max=0.01, t0=5.0)
    assert traj[0, 0] == 5.0
    assert traj[-1, 0] == pytest.approx(5.01)


def test_drag_shortens_flight():
    v0 = [4.0, 0.0, 4.0]
    no_drag = mc.ball_predict([0, 0, 1], v0, t_max=0.8, cd=0.0)
    drag = mc.ball_predict([0, 0, 1], v0, t_max=0.8)
    assert drag[-1, 1] < no_drag[-1, 1]
    # Tennis ball drag constant ~0.02 1/m.
    assert mc.ball_drag_k() == pytest.approx(0.5 * 1.2 * 0.55 * np.pi * 0.0335**2 / 0.057)


def test_fit_recovers_state_with_noise(rng):
    p0, v0 = np.array([1.8, 0.2, 1.1]), np.array([-4.5, -0.3, 3.2])
    traj = mc.ball_predict(p0, v0, dt=1 / 60, t_max=0.3, t0=10.0)
    pts = traj.copy()
    pts[:, 1:] += rng.normal(0, 0.003, pts[:, 1:].shape)  # 3 mm vision noise
    fit = mc.ball_fit(pts)
    assert fit["t0"] == pytest.approx(10.0)
    np.testing.assert_allclose(fit["p0"], p0, atol=0.01)
    np.testing.assert_allclose(fit["v0"], v0, atol=0.1)
    assert fit["residual"] < 0.005


def test_fit_exact_and_unsorted():
    p0, v0 = np.array([0.0, 0.0, 1.0]), np.array([2.0, 1.0, 3.0])
    traj = mc.ball_predict(p0, v0, dt=0.05, t_max=0.4)
    fit = mc.ball_fit(traj[::-1])
    np.testing.assert_allclose(fit["p0"], p0, atol=1e-7)
    np.testing.assert_allclose(fit["v0"], v0, atol=1e-6)
    # Three points are enough.
    fit3 = mc.ball_fit(traj[[0, 3, 6]])
    np.testing.assert_allclose(fit3["v0"], v0, atol=1e-5)


def test_fit_rejects_bad_input():
    with pytest.raises(ValueError):
        mc.ball_fit(np.zeros((2, 4)))
    with pytest.raises(ValueError):
        mc.ball_fit(np.zeros((5, 4)))  # all samples at the same time
    with pytest.raises(ValueError):
        mc.ball_fit(np.zeros((5, 3)))


def test_intercept_hit_on_surface_and_miss():
    traj = mc.ball_predict([0, 0, 1], [3, 0, 3], t_max=1.0)
    c, r = np.array([0.9, 0.0, 1.5]), 0.05
    hit = mc.ball_intercept(traj, c, r)
    assert hit is not None
    assert np.linalg.norm(hit["p"] - c) == pytest.approx(r, abs=1e-6)
    i = np.searchsorted(traj[:, 0], hit["t"])
    assert np.all(np.linalg.norm(traj[:i, 1:] - c, axis=1) > r)
    assert hit["v"][0] == pytest.approx(3.0, rel=0.05)
    assert mc.ball_intercept(traj, [5.0, 5.0, 5.0], 0.1) is None


def test_intercept_catches_fast_pass_between_samples():
    # Coarse samples straddle a small sphere; the segment test must catch it.
    traj = np.array([[0.0, -1.0, 0.0, 0.0], [0.1, 1.0, 0.0, 0.0]])
    hit = mc.ball_intercept(traj, [0.0, 0.0, 0.0], 0.01)
    assert hit is not None and hit["t"] == pytest.approx(0.0495)
