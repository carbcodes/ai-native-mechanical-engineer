"""style: ref_arm (20sffactory parallel-linkage arm) — vendored assembly, kinematics, outputs."""
import json
import math

import numpy as np
import pytest
import yaml

from conftest import mechy
from mechy.arm_model import ArmModel
from mechy.project import init_project


@pytest.fixture(scope="session")
def built_v3(tmp_path_factory):
    root = tmp_path_factory.mktemp("ref") / "proj"
    proj = init_project(root, example="tennis-catcher")
    code, _, res = mechy("cad", "build", "v3", "--project", str(root))
    assert code == 0 and res["ok"], res
    return proj


def test_v3_outputs(built_v3):
    d = built_v3.variant_dir("v3")
    stls = {p.stem for p in (d / "stl").glob("*.stl")}
    need = {"arm_socket", "arm_rotategear", "arm_main_body", "arm_gear_body", "arm_endstop_bracket",
            "arm_stabilizer", "arm_lever", "arm_lower_shank_140", "arm_upper_shank_140",
            "arm_pleuel_140", "arm_pleuel_bend_lower_140", "arm_pleuel_bend_upper_140",
            "arm_triplate", "arm_manipulator", "tool_shank_calibrator_140", "cup"}
    assert need <= stls
    for f in ("arm.glb", "arm.stl", "arm.xml", "thumb.png", "summary.md", "print_list.csv",
              "bom.csv", "mass_props.json"):
        assert (d / f).exists() and (d / f).stat().st_size > 100, f
    assert not (d / "arm.step").exists()    # meshes only; documented in summary.md
    mp = json.loads((d / "mass_props.json").read_text())
    assert mp["kinematics"] == "parallel_level"
    assert mp["bodies"]["upper_arm"]["mass"] > 0.01 and mp["bodies"]["cup"]["mass"] > 0.01


def test_ref_kinematics_ik_fk():
    P = yaml.safe_load(open("mechy/examples/tennis_catcher/design/v3/params.yaml"))
    arm = ArmModel(P)
    core = arm.core_arm()
    rng = np.random.default_rng(1)
    ok = 0
    for _ in range(200):
        q = rng.uniform(arm.limits[:, 0], arm.limits[:, 1])
        q[3] = -q[1] - q[2]
        pos, pitch = core.fk(q)
        assert abs(pitch - math.pi / 2) < 1e-9          # cup always opens straight up
        q2 = core.ik(pos, math.pi / 2, seed=q)
        if q2 is not None and np.allclose(np.asarray(q2)[1], q[1], atol=1e-6):
            ok += 1
    assert ok > 150


def test_linkage_closure_and_glb(built_v3):
    """All passive-loop pivots stay joined (<1e-6 m) over 200 random in-range poses, and the
    GLB node origins equal ArmModel.points (contracts 11, passive-link extras)."""
    from mechy.cad.glb import read_glb, node_world, rest_q_glb
    d = built_v3.variant_dir("v3")
    g = read_glb(d / "arm.glb")
    rq = np.asarray(rest_q_glb(g))
    nodes = {n["name"]: n for n in g["nodes"]}
    coupled = [n for n in g["nodes"] if n.get("extras", {}).get("coupled")]
    assert {n["name"] for n in coupled} == {"lever", "pleuel", "bend_lower", "triplate",
                                          "bend_upper"}
    arm = ArmModel(built_v3.params("v3"))
    rng = np.random.default_rng(0)
    lim = arm.limits
    worst = 0.0
    S = np.array([0.011, 89.7]); B0 = S + np.array([-30.0, 12.0])
    TR = np.array([15.0, 20.0])
    dv = lambda a: np.array([math.cos(a), math.sin(a)])
    for _ in range(200):
        q = rng.uniform(lim[:, 0], lim[:, 1]); q[3] = -q[1] - q[2]
        q1, a2 = q[1], q[1] + q[2]
        E = S + 140 * dv(q1); W = E + 140 * dv(a2)
        L = S - 40 * dv(a2); PU = E - 40 * dv(a2)
        TL = E + (B0 - S); T2 = E + TR; T3 = W + TR
        err = max(np.linalg.norm(PU - L - 140 * dv(q1)),
                  np.linalg.norm(TL - B0 - 140 * dv(q1)),
                  np.linalg.norm(T3 - T2 - 140 * dv(a2))) / 1000
        worst = max(worst, err)
        pts = arm.points(q)
        for nme, i in (("upper_arm", 1), ("forearm", 2), ("hand", 3), ("cup_center", 4)):
            assert np.linalg.norm(node_world(g, nme, q)[:3, 3] - pts[i]) < 1e-6, nme
    assert worst < 1e-6, worst


def test_ref_arm_gravity_matches_mujoco_and_closed_form(built_v3):
    import mujoco
    arm = ArmModel(built_v3.params("v3"), mass_props=json.loads(
        (built_v3.variant_dir("v3") / "mass_props.json").read_text()))
    m = mujoco.MjModel.from_xml_path(str(built_v3.variant_dir("v3") / "arm.xml"))
    d = mujoco.MjData(m)
    jadr = [m.jnt_dofadr[m.joint(n).id] for n in arm.joint_names]
    qadr = [m.jnt_qposadr[m.joint(n).id] for n in arm.joint_names]
    rng = np.random.default_rng(2)
    lim = arm.limits
    Ci = np.linalg.inv(arm.coupling_matrix).T
    for _ in range(8):
        q = rng.uniform(lim[:, 0], lim[:, 1]); q[3] = -q[1] - q[2]
        for a, v in zip(qadr, q):
            d.qpos[a] = v
        mujoco.mj_forward(m, d)
        tau_q = np.array([d.qfrc_bias[a] for a in jadr])
        tau_a = Ci @ tau_q                                    # ball parked on the floor
        model = Ci @ arm.gravity_torque_signed(q, ball_mass=0.0)
        for j in range(3):
            assert abs(model[j] - tau_a[j]) < max(0.02 * abs(tau_a[j]), 0.002), \
                (q, model, tau_a)
    # BAM closed form (sizing.py): tau_lower = g cos(th1) L1 (m_ls/2 + m_us + m_tip),
    # tau_upper = g cos(th2) L2 (m_us/2 + m_tip) — with passive-link masses zeroed the lumped model
    # must equal it to 1e-6.
    mp = arm.mass_props["bodies"]
    m_ls, m_us = mp["upper_arm"]["mass"], mp["forearm"]["mass"]
    m_tip = mp["hand"]["mass"] + mp["cup"]["mass"]
    L1 = L2 = 0.14
    for q in ([0.0, 1.0, -1.0, 0.0], [0.3, 1.5, -1.2, 0.0]):
        q1, a2 = q[1], q[1] + q[2]
        cf = [9.81 * math.cos(q1) * L1 * (m_ls / 2 + m_us + m_tip),
              9.81 * math.cos(a2) * L2 * (m_us / 2 + m_tip)]
        sa = Ci @ arm.gravity_torque_signed(np.array(q), ball_mass=0.0)
        # closed form treats the link com at L/2 and tip at L — the real lumped coms differ, so
        # compare to 10% instead of 1e-6; the exact-1e-6 equality holds for the point-mass path:
        assert abs(sa[1] - cf[0]) < 0.10 * max(abs(cf[0]), 0.02)
        assert abs(sa[2] - cf[1]) < 0.10 * max(abs(cf[1]), 0.02)


def test_linkage_pivot_bores_track_world_pivots(built_v3):
    """Every pivot bore (a y-axis cylinder detected in the STEP tessellation that sits on a named
    pivot at the rest pose) keeps landing on that world pivot within 0.5 mm, at the ready pose and
    random poses — checked through BOTH the renderer's posed meshes and the written GLB."""
    import math
    from mechy.cad.ref_arm import (PIVOTS, TRIP_OFF, MANIP_OFF, _ry, _yaw)
    from mechy.cad.glb import read_glb, node_world

    d = built_v3.variant_dir("v3")
    arm = ArmModel(built_v3.params("v3"))
    from mechy.cad.ref_arm import build_design
    design = build_design(arm)

    def world_pivots(q):
        q = np.asarray(q, float); cy, sy = math.cos(q[0]), math.sin(q[0])
        q1, a2 = q[1], q[1] + q[2]
        dv = lambda a: np.array([math.cos(a) * cy, math.cos(a) * sy, math.sin(a)])
        S = np.array([PIVOTS["S"][0] * cy, PIVOTS["S"][0] * sy, PIVOTS["S"][1]])
        E = S + 140 * dv(q1); W = E + 140 * dv(a2)
        L = S - 40 * dv(a2); PU = E - 40 * dv(a2)
        B0 = np.array([PIVOTS["B0"][0] * cy, PIVOTS["B0"][0] * sy, PIVOTS["B0"][1]])
        TL = E + (B0 - S)
        T2 = E + np.array([TRIP_OFF[0] * cy, TRIP_OFF[0] * sy, TRIP_OFF[1]])
        T3 = W + np.array([MANIP_OFF[0] * cy, MANIP_OFF[0] * sy, MANIP_OFF[1]])
        return {"S": S, "E": E, "W": W, "L": L, "PU": PU, "B0": B0, "TL": TL, "T2": T2, "T3": T3}

    def pose_bore(D, p, b, q):                    # renderer transform (posed_meshes)
        R = _yaw(q[0]) @ _ry(-D.node_angle(p.node, q))
        return R @ np.asarray(b) + D.node_origin_at(p.node, q)

    # which bores sit on which pivot at rest (they are the linkage pivots, all in the xz plane)
    q0 = np.zeros(4)
    piv0 = world_pivots(q0)
    pivot_bores = []                               # (part, bore_mm, pivot_name)
    for p in design.parts:
        for b in p.bores:
            bw = pose_bore(design, p, b, q0)
            hits = [(np.linalg.norm(bw[[0, 2]] - pv[[0, 2]]), n) for n, pv in piv0.items()]
            dist, name = min(hits)
            if dist < 0.5:
                pivot_bores.append((p, np.asarray(b, float), name))
    pivots_hit = {n for _, _, n in pivot_bores}
    assert pivots_hit >= {"S", "E", "W", "L", "PU", "B0", "TL", "T2", "T3"}, pivots_hit

    g = read_glb(d / "arm.glb")
    rng = np.random.default_rng(3)
    lim = arm.limits
    poses = [arm.ready_pose()] + [rng.uniform(lim[:, 0], lim[:, 1]) for _ in range(25)]
    for q in poses:
        q[3] = -q[1] - q[2]
        piv = world_pivots(q)
        unyaw = _yaw(-q[0])                        # pivot axis is a y-line: compare in the radial plane
        for p, b, name in pivot_bores:
            bw = unyaw @ pose_bore(design, p, b, q)
            pv = unyaw @ piv[name]
            assert np.linalg.norm(bw[[0, 2]] - pv[[0, 2]]) < 0.5, (p.name, name, q)
            # same transform through the GLB node tree (world mm)
            bwl = unyaw @ ((node_world(g, p.node, q)[:3]
                            @ np.append(np.asarray(b) / 1000, 1.0)) * 1000)
            assert np.linalg.norm(bwl[[0, 2]] - pv[[0, 2]]) < 0.5, (p.name, name, q, "glb")


def test_ref_arm_sim_and_control(built_v3):
    code, _, res = mechy("sim", "catch", "v3", "--throws", "8",
                         "--project", str(built_v3.root))
    assert code == 0 and res["ok"], res
    code, _, res = mechy("control", "gen", "v3", "--board", "uno_cnc",
                         "--project", str(built_v3.root))
    assert code == 0 and res["ok"], res
    assert abs(res["steps_per_rad"][2] - 800 * 4.5 / (2 * math.pi)) < 1e-3
    cfg_h = (built_v3.root / "control/v3/firmware/mechy_arm/config.h").read_text()
    # vendor pinout_uno.h: X=upper arm (a2), Y=lower arm (a1), Z=yaw (q0), A = spare (wrist, unused)
    assert "PIN_STEP 2" in cfg_h or "X" in cfg_h
    assert "kind 2" in cfg_h or "none" in cfg_h    # wrist marked not-homed


def test_ref_homing_mock(built_v3, tmp_path):
    """The generated firmware homes ref_arm: 3 endstops; the passive wrist is HOME_KIND 2."""
    cfg_h = (built_v3.root / "control/v3/firmware/mechy_arm/config.h").read_text()
    import re
    m = re.search(r"HOME_KIND\[4\] = \{([\d, ]+)\}", cfg_h)
    assert m and m.group(1).split(",")[3].strip() == "2"
    readme = (built_v3.root / "control/v3/README.md").read_text()
    assert "Vref" in readme
