import json
import mujoco
import numpy as np

from mechy.arm_model import load_arm


def test_cad_outputs(built_project):
    d = built_project.variant_dir("v1")
    for f in ("arm.step", "arm.stl", "arm.glb", "arm.xml", "thumb.png", "summary.md"):
        assert (d / f).stat().st_size > 500, f
    assert (d / "arm.glb").read_bytes()[:4] == b"glTF"
    assert (d / "arm.step").read_text(errors="ignore").startswith("ISO-10303-21")
    assert (d / "thumb.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_mjcf_matches_kinematics(built_project):
    m = mujoco.MjModel.from_xml_path(str(built_project.variant_dir("v1") / "arm.xml"))
    d = mujoco.MjData(m)
    arm = load_arm(built_project, "v1")
    ca = arm.core_arm()
    assert m.nu == 4 and [m.joint(i).name for i in range(4)] == ["base", "shoulder", "elbow", "wrist"]
    assert np.allclose(m.jnt_range[:4], arm.limits)
    rng = np.random.default_rng(0)
    for _ in range(20):
        q = rng.uniform(arm.limits[:, 0], arm.limits[:, 1])
        d.qpos[:4] = q
        mujoco.mj_forward(m, d)
        p, pitch = ca.fk(q)
        assert np.allclose(d.site("cup_center").xpos, p, atol=1e-9)
        axis = d.xmat[m.body("cup").id].reshape(3, 3)[:, 2]          # cup opening
        r = np.array([np.cos(q[0]), np.sin(q[0]), 0])
        assert np.allclose(axis, np.cos(pitch) * r + [0, 0, np.sin(pitch)], atol=1e-9)
    # a ball dropped into an upright cup stays there
    d = mujoco.MjData(m)
    target, _ = ca.fk(np.radians([0, 75, -70, 85]))     # a pose with the cup opening straight up
    q = ca.ik(target, np.pi / 2)
    assert q is not None
    d.qpos[:4] = q
    mujoco.mj_forward(m, d)
    adr = m.joint("ball").qposadr[0]
    d.qpos[adr:adr + 3] = d.site("cup_center").xpos + [0, 0, 0.05]
    m.opt.gravity[:] = [0, 0, -9.81]
    m.dof_frictionloss[:4] = 100  # hold the arm still without actuators
    for _ in range(2000):
        d.ctrl[:] = q
        mujoco.mj_step(m, d)
    assert np.linalg.norm(d.xpos[m.body("ball").id] - d.site("cup_center").xpos) < 0.05


def _glb_json(path):
    """GLB JSON via pygltflib when installed (independent parser), else mechy's reader."""
    try:
        import pygltflib
        g = pygltflib.GLTF2().load(str(path))
        return json.loads(g.to_json())
    except ImportError:
        from mechy.cad.glb import read_glb
        return read_glb(path)


def test_glb_animatable_nodes(built_project):
    """contracts 11: nodes base > turntable > upper_arm > forearm > hand, origins on the joint axes;
    with the joint rotations set to q the hand node sits on the wrist axis and cup_center on fk(q)."""
    from mechy.cad.glb import node_world
    g = _glb_json(built_project.variant_dir("v1") / "arm.glb")
    names = [n.get("name") for n in g["nodes"]]
    chain = ["arm", "base", "turntable", "upper_arm", "forearm", "hand", "cup_center"]
    for a, b in zip(chain, chain[1:]):
        assert names.index(b) in g["nodes"][names.index(a)]["children"], (a, b)
    assert g["scenes"][g.get("scene", 0)]["nodes"] == [names.index("arm")]
    arm = load_arm(built_project, "v1")
    ca = arm.core_arm()
    rng = np.random.default_rng(3)
    for q in [np.zeros(4)] + [rng.uniform(arm.limits[:, 0], arm.limits[:, 1]) for _ in range(10)]:
        P = arm.points(q)
        assert np.allclose(node_world(g, "hand", q)[:3, 3], P[3], atol=1e-6)
        assert np.allclose(node_world(g, "forearm", q)[:3, 3], P[2], atol=1e-6)
        assert np.allclose(node_world(g, "upper_arm", q)[:3, 3], P[1], atol=1e-6)
        p, _ = ca.fk(q)
        assert np.allclose(node_world(g, "cup_center", q)[:3, 3], p, atol=1e-6)
    # every part is a mesh node under one of the five bodies; cup parts move with the hand
    parent = {c: i for i, n in enumerate(g["nodes"]) for c in n.get("children", [])}
    bodies = {"base", "turntable", "upper_arm", "forearm", "hand"}
    meshes = [i for i, n in enumerate(g["nodes"]) if "mesh" in n]
    assert len(meshes) > 100
    assert all(names[parent[i]] in bodies for i in meshes)
    assert names[parent[names.index("cup_shell")]] == "hand"
    assert len({tuple(m["pbrMetallicRoughness"]["baseColorFactor"]) for m in g["materials"]}) >= 6
    # the static file shows the ready pose; the root turns z-up into glTF's y-up
    rest = node_world(g, "cup_center")[:3, 3]
    assert np.allclose(rest, ca.fk(arm.ready_pose())[0], atol=1e-6)
    world = node_world(g, "cup_center", below_root=False)[:3, 3]
    assert np.allclose(world, [rest[0], rest[2], -rest[1]], atol=1e-6)


def test_glb_meshes_match_cad_pose(built_project):
    """A part's mesh, moved by the GLB body transform at q, lands where the CAD posed solid is."""
    from mechy.cad.belt_arm import build_design
    from mechy.cad.glb import BODY_ALIAS, read_glb
    import struct
    path = built_project.variant_dir("v1") / "arm.glb"
    g = read_glb(path)
    raw = path.read_bytes()
    jlen = struct.unpack_from("<I", raw, 12)[0]
    blob = raw[20 + jlen + 8:]
    arm = load_arm(built_project, "v1")
    D = build_design(arm)
    from mechy.cad.glb import node_world
    q = np.radians([25, 40, -60, 30])
    locs = D.body_locations(q)
    by_name = {n["name"]: n for n in g["nodes"]}
    for part in ("cup_shell", "forearm", "upper_arm_plate_l", "turntable", "hand_fork"):
        p = next(x for x in D.parts if x.name == part)
        node = by_name[part]
        acc = g["accessors"][g["meshes"][node["mesh"]]["primitives"][0]["attributes"]["POSITION"]]
        bv = g["bufferViews"][acc["bufferView"]]
        v = np.frombuffer(blob, np.float32, acc["count"] * 3, bv["byteOffset"]).reshape(-1, 3).astype(float)
        T = node_world(g, part, q)
        vw = v @ T[:3, :3].T + T[:3, 3]
        bb = p.shape.moved(locs[p.body]).bounding_box()
        lo, hi = np.array([bb.min.X, bb.min.Y, bb.min.Z]) / 1000, np.array([bb.max.X, bb.max.Y, bb.max.Z]) / 1000
        assert np.allclose(vw.min(0), lo, atol=2e-3) and np.allclose(vw.max(0), hi, atol=2e-3), part
