import json

from conftest import mechy

CONTRACT_KEYS = {"variant", "throws", "catch_rate", "reach_rate", "skipped_step_rate", "mean_margin_s",
                 "failures", "worst_joint", "plots", "video"}


def test_sim_catch_small(built_project):
    code, events, res = mechy("sim", "catch", "v1", "--throws", "10", "--seed", "3", "--task", "T900-sim-test",
                              "--project", str(built_project.root))
    assert code == 0 and res["ok"], res
    out = built_project.path("sim", "T900-sim-test")
    rep = json.loads((out / "report.json").read_text())
    assert CONTRACT_KEYS <= set(rep)
    assert rep["variant"] == "v1" and rep["throws"] == 10
    assert 0 <= rep["catch_rate"] <= rep["reach_rate"] <= 1
    for k in ("out_of_reach", "too_slow", "skipped_steps", "bounced_out"):
        assert k in rep["failures"]
    assert round(rep["catch_rate"] * 10) + sum(rep["failures"].values()) == 10
    for p in rep["plots"]:
        assert (out / p).stat().st_size > 1000
    assert (out / "summary.md").exists() and len((out / "summary.md").read_text().split()) <= 300
    assert any(e["type"] == "task.done" for e in events)
    assert rep["meta"]["microsteps"] == 4
    assert rep["meta"]["style"] == "belt_arm" and rep["meta"]["masses_from_cad"]
    for k in ("skip_on_impact_rate", "skip_before_contact_rate", "give_rate"):
        assert 0 <= rep[k] <= 1, k
    assert rep["meta"]["motor_map"]["coupling"] == "passthrough"
    assert rep["meta"]["soft_catch"]["compliance"] == "none"

    # replay.json (contracts 11)
    rp = json.loads((out / "replay.json").read_text())
    assert rp["variant"] == "v1" and rp["dt"] == 0.01
    assert rp["joint_names"] == ["base", "shoulder", "elbow", "wrist"]
    assert rp["joint_axes"] == {"turntable": [0, 0, 1], "upper_arm": [0, -1, 0], "forearm": [0, -1, 0],
                                "hand": [0, -1, 0]}
    assert 1 <= len(rp["throws"]) <= 5
    outcomes = [t["outcome"] for t in rp["throws"]]
    assert "caught" in outcomes
    if rep["catch_rate"] < 1:
        assert any(o != "caught" for o in outcomes)
    import numpy as np
    from mechy.arm_model import load_arm
    arm = load_arm(built_project, "v1")
    ca = arm.core_arm()
    for t in rp["throws"]:
        n = len(t["t"])
        assert n > 30 and len(t["q"]) == n and len(t["ball"]) == n
        assert all(len(q) == 4 for q in t["q"]) and all(len(b) == 3 for b in t["ball"])
        assert np.allclose(np.diff(t["t"])[:-1], 0.01, atol=1e-6)        # 100 Hz (last row = end of sim)
        assert len(t["predicted"]) > 10 and all(len(p) == 3 for p in t["predicted"])
        if t["outcome"] == "caught":
            # at the planned catch time the arm's cup centre is near the catch point and the ball
            k = int(np.argmin(np.abs(np.array(t["t"]) - t["t_catch"])))
            p, _ = ca.fk(np.array(t["q"][k]))
            assert np.linalg.norm(p - np.array(t["catch_point"])) < 0.03
            end = np.array(t["ball"][-1])
            pe, _ = ca.fk(np.array(t["q"][-1]))
            assert np.linalg.norm(end - pe) < 0.08                       # ball ends in the cup


def test_give_path_and_spring_option():
    """plan_give: a straight cup path along the ball's velocity through the catch point, at the catch
    pitch, within the motor speed cap. compliance: spring adds a sprung cup slide to the MJCF."""
    import mujoco
    import numpy as np
    import yaml
    from mechy.arm_model import ArmModel
    from mechy.cad.mjcf import build_mjcf
    from mechy.sim.catch import give_profile, plan_give
    params = yaml.safe_load(open(__import__("mechy").__path__[0] + "/examples/tennis_catcher/design/v1/params.yaml"))
    params["catcher"].update(give_m=0.06, give_runup_m=0.03)
    arm = ArmModel(params)
    ca, motors = arm.core_arm(), arm.core_motors()
    q = np.radians([10, 45, -50, 40])
    p, pitch = ca.fk(q)
    v = -3.0 * np.array([np.cos(pitch) * np.cos(q[0]), np.cos(pitch) * np.sin(q[0]), np.sin(pitch)])  # straight in
    g = plan_give(arm, ca, motors, {"p": np.asarray(p), "q": q, "pitch": pitch, "v": v}, 0.057)
    assert g is not None and 0.1 < g["v_c"] <= 0.7 * 3.0
    f = give_profile(g)
    vmax = np.array([m.max_joint_speed for m in motors])
    dh = v / np.linalg.norm(v)
    for t in np.linspace(0, g["t1"] + g["t2"], 25):
        a, ad = f(t)
        qq = arm.from_motor(a)
        pp, pt = ca.fk(qq)
        off = np.asarray(pp) - np.asarray(p)
        assert np.linalg.norm(off - (off @ dh) * dh) < 2e-3          # on the line through the catch point
        assert abs(pt - pitch) < 1e-6
        assert np.all(np.abs(ad) <= vmax * 1.001)
    a_c, _ = f(g["t1"])                                                   # at the catch point at t1
    assert np.linalg.norm(np.asarray(ca.fk(arm.from_motor(a_c))[0]) - p) < 2e-3
    assert np.linalg.norm(np.asarray(ca.fk(g["q_end"])[0]) - (np.asarray(p) + 0.06 * dh)) < 1e-6
    params["catcher"].update(compliance="spring", spring_k_n_per_m=200, spring_travel_m=0.05)
    m = mujoco.MjModel.from_xml_string(build_mjcf(ArmModel(params)))
    j = m.joint("cup_slide")
    assert j.type[0] == mujoco.mjtJoint.mjJNT_SLIDE and abs(m.jnt_stiffness[j.id] - 200) < 1e-9
    assert np.allclose(m.jnt_range[j.id], [-0.05, 0])
