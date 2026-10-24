"""`mechy sim pick` on the bam-arm example: statics against BAM's closed form, cycle, outputs."""
import json
import os
import math
import sys
from pathlib import Path

import numpy as np
import pytest

from conftest import mechy
from mechy.arm_model import load_arm
from mechy.project import init_project
from mechy.sim import pick

BAM_ANALYSIS = Path(os.environ.get("MECHY_BAM_ANALYSIS", "/nonexistent"))


@pytest.fixture(scope="session")
def bam(tmp_path_factory):
    root = tmp_path_factory.mktemp("bam") / "proj"
    proj = init_project(root, example="bam-arm", git=False)
    code, _, res = mechy("cad", "build", "v1", "--project", str(root))
    assert code == 0 and res["ok"], res
    code, _, res = mechy("sim", "pick", "v1", "--project", str(root))
    assert code == 0 and res["ok"], res
    return proj


def test_payload_slope_matches_closed_form(bam):
    """d tau / d payload at the tip is g * L: BAM sizing.py's '+0.1 kg at tip' check
    (upper motor m g L = 0.1373 N m for 0.1 kg), any pose, 140 mm shanks. The levelling links carry
    the tool's offset moment into the base, so each motor sees g L cos(its own shank pitch)."""
    arm = load_arm(bam, "v1")
    for q1, q2 in ((0.7, -1.2), (1.1, -1.5), (0.4, -0.9)):
        q = np.array([0.0, q1, q2, -(q1 + q2)])
        s0, s1 = pick.signed_motor(arm, q, 0.0), pick.signed_motor(arm, q, 0.1)
        a2 = q1 + q2
        assert abs(abs(s1[2] - s0[2]) - 0.1 * 9.81 * 0.14 * math.cos(a2)) < 1e-4
        assert abs(abs(s1[1] - s0[1]) - 0.1 * 9.81 * 0.14 * math.cos(q1)) < 1e-4
    # sizing.py budget: 0.40 x 4.5 x 0.5 = 0.90 N m, the same number the sim uses
    assert abs(pick.budgets(arm, 0.5)[1] - 0.9) < 1e-9


@pytest.mark.skipif(not BAM_ANALYSIS.exists(), reason="BAM workspace not on this machine")
def test_static_torque_close_to_bam_sizing(bam):
    """Same pose, same payload: our torques follow BAM's within the mass-model difference. BAM
    counts solid PLA (an upper bound); the CAD model uses real shell + 25 % infill masses, so ours
    must come out lower, by less than 20 %."""
    sys.path.insert(0, str(BAM_ANALYSIS))
    try:
        import sizing
    finally:
        sys.path.pop(0)
    arm = load_arm(bam, "v1")
    th1, th2 = 0.6, 0.05                      # shank pitches, rad
    q = np.array([0.0, th1, th2 - th1, -th2])
    t_lo, t_up = sizing.torques(140, th1, th2, payload=0.2)
    s = pick.signed_motor(arm, q, 0.2)
    for ours, theirs in ((abs(s[1]), t_lo), (abs(s[2]), t_up)):
        assert ours <= theirs * 1.02 and (theirs - ours) / theirs < 0.20


def test_capacity_inverts_budget(bam):
    arm = load_arm(bam, "v1")
    bud = pick.budgets(arm, 0.5)
    q = pick.plan_cycle(arm, pick.settings(bam))["q"][1]
    cap, who = pick.capacity_kg(arm, q, bud)
    assert 0.2 < cap < pick.MAX_PAYLOAD_KG and who in (1, 2)
    load = np.abs(pick.signed_motor(arm, q, cap))[who]
    assert abs(load - bud[who]) < 1e-6
    assert (np.abs(pick.signed_motor(arm, q, cap * 0.99)) <= bud + 1e-9)[[1, 2]].all()


def test_pick_outputs(bam):
    d = bam.path("sim", "pick-v1")
    rep = json.loads((d / "report.json").read_text())
    assert rep["kind"] == "pick" and rep["headline"]["label"] == "Payload"
    assert rep["headline"]["meets"] and rep["payload_capacity_g"] >= 200
    assert 0.5 < rep["cycle_s"] < 3.0 and max(rep["peak_motor_load"].values()) < 1.0
    for p in rep["plots"]:
        assert (d / p).stat().st_size > 5000
    rp = json.loads((d / "replay.json").read_text())
    th = rp["throws"][0]
    assert th["outcome"] == "placed" and len(th["q"]) == len(th["t"]) == len(th["ball"]) > 100
    # the payload starts on the tray, rides on the tool, ends in the bin
    assert np.allclose(th["ball"][0], [0.17, -0.10, 0.05], atol=1e-3)
    assert np.allclose(th["ball"][-1], [0.17, 0.11, 0.07], atol=1e-3)


def test_unreachable_point_is_a_clear_error(bam, tmp_path):
    import yaml
    req = bam.path("requirements.yaml")
    data = yaml.safe_load(req.read_text())
    data["pick"]["pick_xyz_m"] = [0.5, 0.0, 0.05]
    req.write_text(yaml.safe_dump(data))
    try:
        code, _, res = mechy("sim", "pick", "v1", "--task", "pick-far", "--project", str(bam.root))
        assert code != 0 and "out of reach" in res["error"]
    finally:
        data["pick"]["pick_xyz_m"] = [0.17, -0.10, 0.05]
        req.write_text(yaml.safe_dump(data))
