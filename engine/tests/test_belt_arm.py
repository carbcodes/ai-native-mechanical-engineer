"""style: belt_arm - printable parts, purchased parts, CAD-derived masses, and the old style."""
import csv
import json

import mujoco
import numpy as np
import pytest
import yaml
from build123d import Vertex

from conftest import mechy
from mechy.arm_model import ArmModel, load_arm
from mechy.project import init_project

PRINTED = {"base_plate", "base_shell", "turntable", "tower_plate", "motor_spine", "upper_arm_plate", "arm_spacer",
           "shoulder_pulley", "elbow_drive_pulley", "wrist_drive_pulley", "wrist_idler_pulley", "forearm",
           "forearm_pulley", "hand_fork", "hand_pulley", "cup_shell"}


def _csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def test_belt_arm_printed_parts(built_project):
    d = built_project.variant_dir("v1")
    stls = {p.stem: p for p in (d / "stl").glob("*.stl")}
    assert PRINTED <= set(stls), PRINTED - set(stls)
    for p in stls.values():
        assert p.stat().st_size > (500 if p.stem.startswith("home_tab") else 1000), p
    rows = _csv(d / "print_list.csv")
    assert {r["part"] for r in rows} == set(stls)
    by = {r["part"]: r for r in rows}
    assert int(by["tower_plate"]["qty"]) == 2 and int(by["upper_arm_plate"]["qty"]) == 2
    for r in rows:
        assert r["material"] in ("PETG", "PLA") and r["orientation"] and float(r["est_grams"]) > 0
        assert (d / r["stl"]).exists()
    total = sum(float(r["est_grams_total"]) for r in rows)
    assert 300 < total < 2000, total


def test_belt_arm_bom(built_project):
    rows = _csv(built_project.variant_dir("v1") / "bom.csv")
    items = {r["item"]: r for r in rows}
    assert int(items["NEMA 17 stepper 17HS4401"]["qty"]) == 4
    assert int(items["GT2 20T pulley"]["qty"]) == 4
    assert int(items["51105 thrust ball bearing"]["qty"]) == 1
    assert int(items["608-2RS ball bearing"]["qty"]) >= 5
    assert int(items["M3x10 socket head cap screw"]["qty"]) >= 16
    belts = [r for r in rows if r["item"].startswith("GT2 closed-loop belt")]
    assert sum(int(r["qty"]) for r in belts) == 7          # base + 3 motor stages + 3 link belts
    from mechy.cad.belt_arm import GT2_LOOPS
    for r in belts:
        assert int(r["item"].split()[-2]) in GT2_LOOPS
    for r in rows:
        assert r["source"] and int(r["qty"]) > 0


def test_belt_arm_masses_match_mujoco(built_project):
    """MJCF inertials come from the solids, and ArmModel's gravity torque and joint inertia agree
    with MuJoCo's (qfrc_bias, mass-matrix diagonal minus armature) at random poses."""
    d = built_project.variant_dir("v1")
    mp = json.loads((d / "mass_props.json").read_text())
    m = mujoco.MjModel.from_xml_path(str(d / "arm.xml"))
    for b in ("turntable", "upper_arm", "forearm", "hand", "cup"):
        assert mp["bodies"][b]["mass"] > 0
        assert abs(m.body_mass[m.body(b).id] - mp["bodies"][b]["mass"]) < 1e-5
    assert 0.1 < mp["bodies"]["upper_arm"]["mass"] < 0.6 and mp["bodies"]["turntable"]["mass"] > 1.0
    arm = load_arm(built_project, "v1")
    assert arm.mass_props is not None and arm.mass_props["params_hash"] == mp["params_hash"]
    data = mujoco.MjData(m)
    rng = np.random.default_rng(1)
    for _ in range(25):
        q = rng.uniform(arm.limits[:, 0], arm.limits[:, 1])
        data.qpos[:4] = q
        data.qvel[:] = 0
        mujoco.mj_forward(m, data)
        g_mj = np.abs(data.qfrc_bias[:4])
        assert np.allclose(arm.gravity_torque(q, ball_mass=0.0)[1:], g_mj[1:], rtol=1e-4, atol=1e-6)
        J_mj = np.zeros(4)
        for i in range(4):                       # diagonal of the joint-space inertia via M @ e_i
            e, res = np.zeros(m.nv), np.zeros(m.nv)
            e[i] = 1
            mujoco.mj_mulM(m, data, res, e)
            J_mj[i] = res[i] - m.dof_armature[i]
        assert np.allclose(arm.load_inertia(q, ball_mass=0.0), J_mj, rtol=1e-4, atol=1e-8)


def test_belt_arm_pose_matches_kinematics(built_project):
    from mechy.cad.belt_arm import build_design
    arm = load_arm(built_project, "v1")
    D = build_design(arm)
    rng = np.random.default_rng(2)
    for _ in range(10):
        q = rng.uniform(arm.limits[:, 0], arm.limits[:, 1])
        loc = D.body_locations(q)["cup"]
        p = Vertex(*D.origins["cup"]).moved(loc).center()
        assert np.allclose([p.X / 1000, p.Y / 1000, p.Z / 1000], arm.points(q)[4], atol=1e-9)


def test_belt_arm_ratios_drive_pulleys():
    params = yaml.safe_load(open(__import__("mechy").__path__[0] + "/examples/tennis_catcher/design/v1/params.yaml"))
    params["joints"][1]["gear_ratio"] = 6.0
    from mechy.cad.belt_arm import build_design
    D = build_design(ArmModel(params))
    assert D.info["teeth"][1] == 120
    sh = next(b for b in D.belts if b["joint"] == "shoulder")
    assert sh["teeth"] == [20, 120] and abs(sh["computed_mm"] - sh["standard_mm"]) < 0.5
    assert not D.warnings, D.warnings


def test_simple_style_still_builds(tmp_path):
    proj = init_project(tmp_path / "p", example="tennis-catcher")
    pf = proj.variant_dir("v1") / "params.yaml"
    p = yaml.safe_load(pf.read_text())
    p["style"] = "simple"
    p.pop("drive", None)                     # simple style: independent joints (the default)
    p["links"]["link_mass_kg_per_m"] = 0.35
    pf.write_text(yaml.safe_dump(p, sort_keys=False))
    code, _, res = mechy("cad", "build", "v1", "--project", str(proj.root))
    assert code == 0 and res["ok"], res
    d = proj.variant_dir("v1")
    for f in ("arm.step", "arm.stl", "arm.glb", "arm.xml", "thumb.png"):
        assert (d / f).stat().st_size > 500
    # simple style: estimated make-it outputs, no belt_arm mass_props.json
    assert not (d / "mass_props.json").exists()
    for f in ("print_list.csv", "bom.csv", "loads.json", "stl/upper_arm.stl"):
        assert (d / f).stat().st_size > 100, f
    assert "motor_base" not in (d / "print_list.csv").read_text()      # bought, not printed
    assert "NEMA 17" in (d / "bom.csv").read_text()
    loads = json.loads((d / "loads.json").read_text())
    assert [j["joint"] for j in loads["joints"]] == ["base", "shoulder", "elbow", "wrist"]
    assert loads["joints"][1]["safety_factor_static"] > 0
    assert res["stats"]["style"] == "simple"
    arm = load_arm(proj, "v1")
    assert arm.mass_props is None and arm.style == "simple"
    from mechy.cad.glb import node_world, read_glb
    g = read_glb(d / "arm.glb")                                      # animatable GLB for simple too
    q = np.radians([20, 50, -40, 30])
    assert np.allclose(node_world(g, "hand", q)[:3, 3], arm.points(q)[3], atol=1e-6)
    assert np.allclose(node_world(g, "cup_center", q)[:3, 3], arm.core_arm().fk(q)[0], atol=1e-6)
    assert arm.coupling == "independent" and np.allclose(arm.motor_load_inertia(q), arm.load_inertia(q))


def test_unknown_style_rejected():
    params = {"style": "nope", "joints": [{"name": n, "limit_deg": [-90, 90]} for n in "abcd"],
              "links": {"base_height_m": 0.1, "upper_arm_m": 0.2, "forearm_m": 0.2, "hand_m": 0.05}}
    with pytest.raises(ValueError):
        ArmModel(params)


def test_belt_passthrough_motor_mapping(built_project):
    """Belt pass-through: a = C q (elbow motor = forearm absolute pitch, wrist motor = hand absolute
    pitch). Checks: closed-form angles and steps, the motor-side gravity torque against a
    hand-computed moment balance, and C^-T M C^-1 / C^-T tau against MuJoCo at random poses."""
    d = built_project.variant_dir("v1")
    mp = json.loads((d / "mass_props.json").read_text())
    arm = load_arm(built_project, "v1")
    mm = mp["motor_map"]
    assert mm["coupling"] == "passthrough" and mm == json.loads(json.dumps(arm.motor_map()))
    C = np.array(mm["coupling_matrix"])
    # closed form: shoulder up 30, elbow down 30 -> forearm level, elbow motor back at zero
    q = np.radians([10, 30, -30, 45])
    assert np.allclose(arm.to_motor(q), np.radians([10, 30, 0, 45]))
    assert np.allclose(arm.motor_angles(q), arm.gear * np.radians([10, 30, 0, 45]))
    assert np.allclose(arm.from_motor(arm.to_motor(q)), q)
    spd = 200 * arm.microsteps * arm.gear / 360            # steps per degree, 1.8 deg motors
    assert np.allclose(mm["steps_per_deg"], spd, rtol=1e-4)
    assert np.array_equal(arm.motor_steps(q), np.rint(spd * np.array([10, 30, 0, 45])).astype(int))
    # closed form at q = 0 (all links level): the shoulder motor holds the upper arm about the shoulder
    # plus everything distal as a point load at the elbow, the elbow motor the forearm plus the rest at the wrist
    b = mp["bodies"]
    g, ball = 9.81, 0.057
    m_dist2 = b["forearm"]["mass"] + b["hand"]["mass"] + b["cup"]["mass"] + ball
    m_dist3 = b["hand"]["mass"] + b["cup"]["mass"] + ball
    L1, L2, L3 = arm.upper, arm.fore, arm.hand
    t1 = g * (b["upper_arm"]["mass"] * b["upper_arm"]["com"][0] + m_dist2 * L1)
    t2 = g * (b["forearm"]["mass"] * b["forearm"]["com"][0] + m_dist3 * L2)
    t3 = g * (b["hand"]["mass"] * b["hand"]["com"][0] + b["cup"]["mass"] * (L3 + b["cup"]["com"][0]) + ball * L3)
    got = arm.motor_gravity_torque(np.zeros(4), ball)
    assert np.allclose(got[1:], [t1, t2, t3], rtol=1e-6), (got, [t1, t2, t3])
    assert got[1] < 0.7 * arm.gravity_torque(np.zeros(4), ball)[1]      # the coupling unloads the shoulder motor
    # against MuJoCo: motor-side inertia diag(C^-T M C^-1) and gravity C^-T qfrc_bias
    m = mujoco.MjModel.from_xml_path(str(d / "arm.xml"))
    data = mujoco.MjData(m)
    Ci = np.linalg.inv(C)
    rng = np.random.default_rng(5)
    for _ in range(25):
        q = rng.uniform(arm.limits[:, 0], arm.limits[:, 1])
        data.qpos[:4] = q
        data.qvel[:] = 0
        mujoco.mj_forward(m, data)
        M = np.zeros((4, 4))
        for i in range(4):
            e, res = np.zeros(m.nv), np.zeros(m.nv)
            e[i] = 1
            mujoco.mj_mulM(m, data, res, e)
            M[:, i] = res[:4]
        M -= np.diag(m.dof_armature[:4])
        assert np.allclose(arm.pitch_mass_matrix(q, 0.0), M[1:, 1:], rtol=1e-4, atol=1e-7)
        assert np.allclose(arm.motor_load_inertia(q, 0.0), np.diag(Ci.T @ M @ Ci), rtol=1e-4, atol=1e-7)
        assert np.allclose(arm.motor_gravity_torque(q, 0.0), np.abs(Ci.T @ data.qfrc_bias[:4]), rtol=1e-4, atol=1e-6)


def test_belt_arm_homing(built_project):
    d = built_project.variant_dir("v1")
    items = {r["item"]: r for r in _csv(d / "bom.csv")}
    assert int(items["KW12-3 micro switch (homing)"]["qty"]) == 2
    assert int(items["A3144 hall sensor (homing)"]["qty"]) >= 2
    assert int(items["Neodymium disc magnet 5x2 mm"]["qty"]) >= 2
    mp = json.loads((d / "mass_props.json").read_text())
    assert [h["joint"] for h in mp["homing"]] == ["base", "shoulder", "elbow", "wrist"]
    assert {"home_tab_shoulder", "home_tab_wrist", "hall_post_base"} <= {p.stem for p in (d / "stl").glob("*.stl")}
    assert "Homing" in (d / "summary.md").read_text()


# ---------------------------------------------------------------- v2: sprung cup slide (compliance: spring)
SLIDE_PARTS = {"slide_rod_l", "slide_rod_r", "slide_bearing_l", "slide_bearing_r", "slide_spring_l", "slide_spring_r",
               "slide_collar_l", "slide_collar_r", "slide_oring_l", "slide_oring_r", "slide_bumper", "grub_slide_l",
               "grub_slide_r", "slide_brake_felt_l", "slide_brake_felt_r", "brake_screw_l", "brake_screw_r"}


@pytest.fixture(scope="module")
def built_v2(built_project):
    code, _, res = mechy("cad", "build", "v2", "--project", str(built_project.root))
    assert code == 0 and res["ok"], res
    assert res["stats"]["warnings"] == [], res["stats"]["warnings"]
    return built_project


def test_v2_slide_parts_and_sizing(built_v2):
    from mechy.cad.belt_arm import SPRINGS, build_design
    arm = load_arm(built_v2, "v2")
    assert arm.compliance == "spring" and arm.hand > load_arm(built_v2, "v1").hand
    D = build_design(arm)
    names = {p.name: p for p in D.parts}
    assert SLIDE_PARTS <= set(names), SLIDE_PARTS - set(names)
    moving = {"slide_bearing_l", "slide_bearing_r", "slide_brake_felt_l", "slide_brake_felt_r", "brake_screw_l",
              "brake_screw_r", "cup_shell"}
    assert all(names[n].body == "cup" for n in moving)                                    # these slide
    assert all(names[n].body == "hand" for n in SLIDE_PARTS - moving)                     # these don't
    assert "screw_cup_l" not in names                                                     # cup no longer bolted
    # lugs: the cup shell is wider (across y) than the cup itself, and the rods clear the shell
    sl = D.info["slide"]
    bb = names["cup_shell"].shape.bounding_box()
    assert bb.max.Y - bb.min.Y > D.info["cup_outer_d_mm"] + 10
    rod = names["slide_rod_l"].shape.bounding_box()
    assert rod.min.Y - D.info["cup_outer_d_mm"] / 2 >= 0.5
    # spring sizing (closed form): catalogue rate x (free - min working) = catalogue load at min, the pair
    # gives the sim stiffness, full travel stays above the minimum working length, preload > 0
    sp = sl["spring"]
    for s in SPRINGS:
        assert abs(s["rate_n_per_mm"] * (s["free_mm"] - s["min_work_mm"]) - s["load_at_min_n"]) / s["load_at_min_n"] < 0.06
    assert abs(sl["k_hw_n_per_m"] - arm.spring_k) < 1e-6
    assert sl["rest_length_mm"] - sl["travel_m"] * 1000 >= sp["min_work_mm"]
    assert sl["rest_length_mm"] <= sp["free_mm"] and sl["preload_m"] > 0
    assert abs(sl["travel_m"] - arm.spring_travel) < 1e-9
    assert abs(sl["max_force_n"] - 2 * sp["rate_n_per_mm"] * (sp["free_mm"] - sl["rest_length_mm"] + sl["travel_m"] * 1000)) < 0.01
    # the cup bottom reaches the bumper exactly at full travel; the plate stays clear of the wrist hub
    bump = names["slide_bumper"].shape.bounding_box()
    assert abs((bb.min.X - sl["travel_m"] * 1000) - bump.max.X) < 0.05
    d = built_v2.variant_dir("v2")
    stls = {p.stem for p in (d / "stl").glob("*.stl")}
    assert {"cup_shell", "hand_fork"} <= stls
    rows = {r["part"]: r for r in _csv(d / "print_list.csv")}
    assert "lugs" in rows["cup_shell"]["orientation"] and float(rows["hand_fork"]["est_grams"]) > 0


def test_v2_bom_has_slide_hardware(built_v2):
    rows = _csv(built_v2.variant_dir("v2") / "bom.csv")
    items = {r["item"]: r for r in rows}
    spring = next(r for r in rows if r["item"].startswith("Compression spring"))
    assert "RS PRO 821-352" in spring["item"] and int(spring["qty"]) >= 2 and "0.11 N/mm" in spring["spec"]
    assert "rs-online.com" in spring["source"]
    assert int(items["LM4UU linear ball bearing"]["qty"]) == 2
    rods = [r for r in rows if r["item"].startswith("Steel rod 4 mm")]
    assert len(rods) == 1 and int(rods[0]["qty"]) == 2 and int(rods[0]["item"].split()[-2]) <= 100
    assert int(items["Shaft collar 4 mm"]["qty"]) == 2
    assert int(items["Rubber bumper foot 12.7 x 3.5 mm"]["qty"]) >= 1
    assert int(items["M3x6 set screw"]["qty"]) == 4                 # 2 rod clamps + 2 brake screws
    assert "friction brake" in items["Wool felt sheet 3 mm"]["spec"]
    v1 = {r["item"] for r in _csv(built_v2.variant_dir("v1") / "bom.csv")}
    assert not any(i.startswith(("Compression spring", "LM4UU", "Steel rod 4 mm")) for i in v1)


def test_v2_glb_cup_slide_node(built_v2):
    """GLB: cup parts hang under a `cup_slide` node (child of hand, at the cup centre) that a viewer can
    translate along the hand axis; cup_center stays on the hand at fk(q)."""
    from mechy.cad.glb import node_world, read_glb
    g = read_glb(built_v2.variant_dir("v2") / "arm.glb")
    names = [n.get("name") for n in g["nodes"]]
    parent = {c: i for i, n in enumerate(g["nodes"]) for c in n.get("children", [])}
    k = names.index("cup_slide")
    assert names[parent[k]] == "hand" and names[parent[names.index("cup_center")]] == "hand"
    ex = g["nodes"][k]["extras"]
    assert ex["type"] == "prismatic" and ex["axis"] == [1.0, 0.0, 0.0] and np.allclose(ex["range_m"], [-0.045, 0])
    for part in ("cup_shell", "cup_liner", "slide_bearing_l"):
        assert names[parent[names.index(part)]] == "cup_slide", part
    for part in ("slide_rod_l", "slide_spring_r", "slide_bumper", "hand_fork"):
        assert names[parent[names.index(part)]] == "hand", part
    arm = load_arm(built_v2, "v2")
    ca = arm.core_arm()
    rng = np.random.default_rng(7)
    for q in [np.zeros(4)] + [rng.uniform(arm.limits[:, 0], arm.limits[:, 1]) for _ in range(5)]:
        p, pitch = ca.fk(q)
        assert np.allclose(node_world(g, "cup_slide", q)[:3, 3], p, atol=1e-6)
        assert np.allclose(node_world(g, "cup_center", q)[:3, 3], p, atol=1e-6)
        # pushed back by s along the hand axis (toward the wrist)
        hand_dir = (np.asarray(p) - arm.points(q)[3]) / arm.hand
        pb = node_world(g, "cup_slide", q, slide_m=-0.045)[:3, 3]
        assert np.allclose(pb, np.asarray(p) - 0.045 * hand_dir, atol=1e-6)


def test_v2_mjcf_slide_matches_cad(built_v2):
    d = built_v2.variant_dir("v2")
    mp = json.loads((d / "mass_props.json").read_text())
    m = mujoco.MjModel.from_xml_path(str(d / "arm.xml"))
    j = m.joint("cup_slide")
    assert j.type[0] == mujoco.mjtJoint.mjJNT_SLIDE
    assert abs(m.jnt_stiffness[j.id] - mp["slide"]["k_hw_n_per_m"]) < 1e-6
    assert np.allclose(m.jnt_range[j.id], mp["slide"]["range_m"])
    assert abs(m.qpos_spring[m.jnt_qposadr[j.id]] - mp["slide"]["preload_m"]) < 1e-9
    arm = load_arm(built_v2, "v2")
    assert abs(m.dof_frictionloss[m.jnt_dofadr[j.id]] - arm.params["catcher"]["spring_friction_n"]) < 1e-9
    assert abs(m.body_mass[m.body("cup").id] - mp["bodies"]["cup"]["mass"]) < 1e-5
    assert mp["bodies"]["hand"]["mass"] > json.loads((built_v2.variant_dir("v1") / "mass_props.json").read_text())[
        "bodies"]["hand"]["mass"]
    # the spring holds the cup on its front stop: at rest, preload x k pushes it to q = 0
    data = mujoco.MjData(m)
    mujoco.mj_forward(m, data)
    adr = m.jnt_qposadr[j.id]
    data.qpos[adr] = -0.02
    mujoco.mj_forward(m, data)
    f = data.qfrc_passive[m.jnt_dofadr[j.id]]
    assert abs(f - m.jnt_stiffness[j.id] * (mp["slide"]["preload_m"] + 0.02)) < 1e-6
    # masses: ArmModel's gravity torque still matches MuJoCo with the slide body
    rng = np.random.default_rng(11)
    for _ in range(10):
        q = rng.uniform(arm.limits[:, 0], arm.limits[:, 1])
        data.qpos[:] = 0
        data.qpos[:4] = q
        data.qvel[:] = 0
        mujoco.mj_forward(m, data)
        assert np.allclose(arm.gravity_torque(q, ball_mass=0.0)[1:], np.abs(data.qfrc_bias[1:4]), rtol=1e-4, atol=1e-6)


def test_spring_slide_needs_hand_length():
    params = yaml.safe_load(open(__import__("mechy").__path__[0] + "/examples/tennis_catcher/design/v2/params.yaml"))
    from mechy.cad.belt_arm import build_design
    params["links"]["hand_m"] = 0.08
    D = build_design(ArmModel(params))
    assert any("hand_m" in w for w in D.warnings), D.warnings
    params["links"]["hand_m"] = 0.125
    params["catcher"]["spring_travel_m"] = 0.06            # more than the stock spring allows
    D = build_design(ArmModel(params))
    assert any("allows at most" in w for w in D.warnings) and D.info["slide"]["travel_m"] < 0.047
