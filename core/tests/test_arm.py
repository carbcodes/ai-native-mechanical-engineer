import numpy as np
import pytest

import mechy_core as mc


def random_q(rng, limits, n):
    return rng.uniform(limits[:, 0], limits[:, 1], size=(n, 4))


def planar_reach(arm, q):
    """Signed radial distance of the tool in the arm's own plane. IK only
    returns poses that reach forward (> 0); poses that lean back over the
    base (shoulder > 90 deg and tool behind the base axis) are excluded."""
    return (arm.upper * np.cos(q[1]) + arm.fore * np.cos(q[1] + q[2])
            + arm.hand * np.cos(q[1] + q[2] + q[3]))


def test_ik_round_trips_fk(arm, rng):
    lim = arm.limits
    n_ok = 0
    for q in random_q(rng, lim, 2000):
        p, pitch = arm.fk(q)
        if planar_reach(arm, q) < 1e-3:
            continue  # behind / on the base axis: not an IK pose by convention
        sol = arm.ik(p, pitch)
        # The pose q itself is a valid solution, so IK must find one.
        assert sol is not None
        assert arm.within_limits(sol)
        p2, pitch2 = arm.fk(sol)
        np.testing.assert_allclose(p2, p, atol=1e-9)
        assert np.angle(np.exp(1j * (pitch2 - pitch))) == pytest.approx(0.0, abs=1e-9)
        n_ok += 1
    assert n_ok > 1200


def test_ik_seed_picks_matching_branch(arm, rng):
    for q in random_q(rng, arm.limits, 300):
        p, pitch = arm.fk(q)
        if planar_reach(arm, q) < 0.02 or abs(q[2]) < 1e-3:
            continue
        sol = arm.ik(p, pitch, seed=q)
        np.testing.assert_allclose(sol, q, atol=1e-7)


def test_unreachable_targets_return_none(arm):
    assert arm.ik([1.0, 0.0, 0.3], 0.0) is None          # beyond reach (0.48 m)
    assert arm.ik([0.0, 0.0, 0.12], 0.0) is None         # wrist inside the shoulder
    assert not arm.reachable([1.0, 0.0, 0.3], 0.0)
    assert arm.ik([-0.3, -0.01, 0.2], 0.0) is None       # yaw ~ -178 deg, past +-150
    assert arm.ik([0.3, 0.0, -0.3], -1.4) is None        # needs shoulder far below -10 deg
    assert arm.ik([np.nan, 0, 0], 0.0) is None
    assert arm.reachable([0.3, 0.1, 0.3], 0.0)


def test_full_stretch_is_reachable(arm):
    reach = arm.upper + arm.fore + arm.hand
    q = arm.ik([reach, 0.0, arm.base_height], 0.0)
    assert q is not None
    np.testing.assert_allclose(q, 0.0, atol=1e-6)


def test_limits_and_pickle(arm):
    import pickle

    lim = np.deg2rad([[-150, 150], [-10, 120], [-135, 135], [-90, 90]])
    np.testing.assert_allclose(arm.limits, lim)
    arm2 = pickle.loads(pickle.dumps(arm))
    np.testing.assert_allclose(arm2.limits, lim)
    tight = mc.Arm(0.12, 0.22, 0.20, 0.06, limits=np.zeros((4, 2)))
    assert tight.ik([0.3, 0.1, 0.3], 0.0) is None
    with pytest.raises(ValueError):
        mc.Arm(0.12, 0.22, 0.20, 0.06, limits=np.zeros((3, 2)))
