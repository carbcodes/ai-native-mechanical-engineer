"""Animatable arm.glb (contracts section 11), written directly (no OCC glTF writer).

Scene graph (glTF is y-up, so a root node `arm` turns the arm's z-up base frame into y-up):

    arm (rotation -90 deg about x)
      base
        turntable          origin on the yaw axis, rotates about +z by q0
          upper_arm        origin on the shoulder axis, rotates about -y by q1
            forearm        origin on the elbow axis, -y by q2
              hand         origin on the wrist axis, -y by q3 (cup parts included)
                cup_center (empty: the catch point, = mechy_core fk position)
                cup_slide  (sprung cup only: origin at the cup centre at rest; the cup parts are
                            its children; translate along its local +x axis by s in range_m)

Every part is its own mesh node, a child of the body it moves with, with its vertices already
in that body's frame (metres), so a viewer animates the arm by setting only the five body
nodes' rotations. Body translations never change. The file's rest rotations are the arm's
ready pose (so a static viewer shows the same pose as thumb.png); `scene.extras` carries the
joint axes and the rest pose so a viewer can reset to q = 0.
"""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import numpy as np

BODY_CHAIN = ("base", "turntable", "upper_arm", "forearm", "hand")
JOINT_AXES = {"turntable": (0.0, 0.0, 1.0), "upper_arm": (0.0, -1.0, 0.0), "forearm": (0.0, -1.0, 0.0),
              "hand": (0.0, -1.0, 0.0)}
JOINT_OF = {"turntable": 0, "upper_arm": 1, "forearm": 2, "hand": 3}
BODY_ALIAS = {"cup": "hand"}          # CAD bodies that move with a contract node
Z_UP_TO_Y_UP = (-math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5))   # quaternion x, y, z, w


def quat_axis_angle(axis, angle: float) -> list[float]:
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    s = math.sin(angle / 2)
    return [float(a[0] * s), float(a[1] * s), float(a[2] * s), float(math.cos(angle / 2))]


def quat_matrix(qx, qy, qz, qw) -> np.ndarray:
    return np.array([
        [1 - 2 * (qy * qy + qz * qz), 2 * (qx * qy - qz * qw), 2 * (qx * qz + qy * qw)],
        [2 * (qx * qy + qz * qw), 1 - 2 * (qx * qx + qz * qz), 2 * (qy * qz - qx * qw)],
        [2 * (qx * qz - qy * qw), 2 * (qy * qz + qx * qw), 1 - 2 * (qx * qx + qy * qy)]])


def body_offsets(origins_m: dict) -> dict:
    """Each chain body's translation relative to its parent (m)."""
    out, prev = {}, np.zeros(3)
    for b in BODY_CHAIN:
        o = np.asarray(origins_m.get(b, prev), float)
        out[b] = o - prev
        prev = o
    return out


def body_transforms(q, origins_m: dict, slide_m: float = 0.0) -> dict:
    """World (z-up base frame) 4x4 transform of each chain body at joint angles q (plus `cup_slide`,
    displaced by slide_m along the hand axis, when origins_m has a cup)."""
    off = body_offsets(origins_m)
    T = np.eye(4)
    out = {}
    for b in BODY_CHAIN:
        L = np.eye(4)
        L[:3, 3] = off[b]
        if b in JOINT_OF:
            L[:3, :3] = quat_matrix(*quat_axis_angle(JOINT_AXES[b], float(q[JOINT_OF[b]])))
        T = T @ L
        out[b] = T.copy()
    if origins_m.get("cup") is not None:
        L = np.eye(4)
        L[:3, 3] = np.asarray(origins_m["cup"], float) - np.asarray(origins_m["hand"], float) + [slide_m, 0, 0]
        out["cup_slide"] = out["hand"] @ L
    return out


def vertex_normals(v: np.ndarray, t: np.ndarray) -> np.ndarray:
    n = np.zeros_like(v)
    fn = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    for k in range(3):
        np.add.at(n, t[:, k], fn)
    ln = np.linalg.norm(n, axis=1, keepdims=True)
    n = np.where(ln > 1e-20, n / np.maximum(ln, 1e-20), np.array([0.0, 0.0, 1.0]))
    return n


def tessellate_local(shape, origin_mm, tol_mm: float = 0.3, angular: float = 0.25):
    """Vertices (m, relative to origin_mm) and triangles of a build123d shape placed at q = 0."""
    verts, tris = shape.tessellate(tol_mm, angular)
    if not tris:
        return None
    v = (np.array([[x.X, x.Y, x.Z] for x in verts]) - np.asarray(origin_mm, float)) / 1000.0
    return v, np.asarray(tris, np.int64)


def write_glb(path: Path, parts: list[dict], origins_m: dict, rest_q, meta: dict | None = None,
              slide: dict | None = None, tree: list[dict] | None = None) -> dict:
    """parts: [{name, body, v (K,3) m in the body frame, t (M,3), rgba}]. Returns a small summary.
    slide: {axis, range_m, ...} adds the `cup_slide` node (child of hand, at the cup centre) for parts
    whose body is "cup_slide".
    tree: optional custom node list for the parallel-linkage arm (ref_arm):
        [{name, parent, translation (m, parent frame), rotation (quat rest), extras}] — extras may
        carry {"joint": <0..3>, "axis": [...]} for the driven joints or
        {"coupled": [[joint_index, coeff], ...], "rest": <node rest angle>} for passive links:
        the node's local angle about `axis` is rest + sum(coeff * (q[j] - rest_q[j]))."""
    if tree is not None:
        return _write_glb_tree(path, parts, tree, rest_q, meta or {})
    off = body_offsets(origins_m)
    rest_q = np.asarray(rest_q, float)
    nodes: list[dict] = [{"name": "arm", "rotation": list(Z_UP_TO_Y_UP), "children": []}]
    idx = {}
    parent = 0
    for b in BODY_CHAIN:
        n = {"name": b, "children": []}
        if np.any(np.abs(off[b]) > 0):
            n["translation"] = [float(x) for x in off[b]]
        if b in JOINT_OF:
            n["rotation"] = quat_axis_angle(JOINT_AXES[b], float(rest_q[JOINT_OF[b]]))
            n["extras"] = {"joint": ["base", "shoulder", "elbow", "wrist"][JOINT_OF[b]],
                           "axis": list(JOINT_AXES[b])}
        nodes.append(n)
        idx[b] = len(nodes) - 1
        nodes[parent]["children"].append(idx[b])
        parent = idx[b]
    cup_c = origins_m.get("cup")
    if cup_c is not None:
        nodes.append({"name": "cup_center", "translation": [float(x) for x in np.asarray(cup_c) - np.asarray(
            origins_m["hand"])]})
        nodes[idx["hand"]]["children"].append(len(nodes) - 1)
    if slide is not None and cup_c is not None:
        nodes.append({"name": "cup_slide", "translation": [float(x) for x in np.asarray(cup_c) - np.asarray(
            origins_m["hand"])], "children": [],
            "extras": {"joint": "cup_slide", "type": "prismatic", "axis": list(slide.get("axis", [1.0, 0, 0])),
                       "range_m": list(slide["range_m"]), "rest_m": 0.0,
                       "note": "translation = rest translation + s * axis (hand frame); s < 0 pushes the cup "
                               "toward the wrist"}})
        idx["cup_slide"] = len(nodes) - 1
        nodes[idx["hand"]]["children"].append(idx["cup_slide"])

    bin_chunks: list[bytes] = []
    buffer_views, accessors, meshes, materials = [], [], [], []
    mat_idx: dict[tuple, int] = {}
    offset = 0

    def add_view(data: bytes, target: int) -> int:
        nonlocal offset
        pad = (-len(data)) % 4
        bin_chunks.append(data + b"\0" * pad)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target})
        offset += len(data) + pad
        return len(buffer_views) - 1

    tri_total = 0
    for p in parts:
        body = BODY_ALIAS.get(p["body"], p["body"])
        v = np.asarray(p["v"], np.float32)
        t = np.asarray(p["t"], np.uint32)
        nrm = vertex_normals(v.astype(float), t.astype(np.int64)).astype(np.float32)
        rgba = tuple(round(float(c), 4) for c in (list(p["rgba"]) + [1.0])[:4])
        if rgba not in mat_idx:
            materials.append({"name": "mat_%02x%02x%02x" % tuple(int(c * 255) for c in rgba[:3]),
                              "pbrMetallicRoughness": {"baseColorFactor": list(rgba), "metallicFactor": 0.0,
                                                       "roughnessFactor": 0.6}})
            mat_idx[rgba] = len(materials) - 1
        bv_p = add_view(v.tobytes(), 34962)
        bv_n = add_view(nrm.tobytes(), 34962)
        bv_i = add_view(t.reshape(-1).tobytes(), 34963)
        accessors += [
            {"bufferView": bv_p, "componentType": 5126, "count": len(v), "type": "VEC3",
             "min": [float(x) for x in v.min(0)], "max": [float(x) for x in v.max(0)]},
            {"bufferView": bv_n, "componentType": 5126, "count": len(v), "type": "VEC3"},
            {"bufferView": bv_i, "componentType": 5125, "count": int(t.size), "type": "SCALAR"}]
        a0 = len(accessors) - 3
        meshes.append({"name": p["name"], "primitives": [{"attributes": {"POSITION": a0, "NORMAL": a0 + 1},
                                                           "indices": a0 + 2, "material": mat_idx[rgba]}]})
        nodes.append({"name": p["name"], "mesh": len(meshes) - 1})
        nodes[idx[body]]["children"].append(len(nodes) - 1)
        tri_total += len(t)
    for n in nodes:
        if not n.get("children"):
            n.pop("children", None)
    blob = b"".join(bin_chunks)
    gltf = {
        "asset": {"version": "2.0", "generator": "mechy cad build (animatable, contracts section 11)"},
        "scene": 0,
        "scenes": [{"name": "arm", "nodes": [0], "extras": {
            "units": "m", "frame": "arm base, z up (root node turns it y-up)",
            "joint_axes": {k: list(v) for k, v in JOINT_AXES.items()},
            "joint_names": ["base", "shoulder", "elbow", "wrist"],
            "rest_q_rad": [round(float(x), 6) for x in rest_q], **(meta or {})}}],
        "nodes": nodes, "meshes": meshes, "materials": materials, "accessors": accessors,
        "bufferViews": buffer_views, "buffers": [{"byteLength": len(blob)}],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<I4s", len(js), b"JSON"))
        f.write(js)
        f.write(struct.pack("<I4s", len(blob), b"BIN\0"))
        f.write(blob)
    return {"nodes": len(nodes), "meshes": len(meshes), "triangles": tri_total, "bytes": total}


def _write_glb_tree(path: Path, parts: list[dict], tree: list[dict], rest_q, meta: dict) -> dict:
    """Custom node tree (ref_arm): main joints + passive linkage nodes with extras.coupled."""
    rest_q = np.asarray(rest_q, float)
    nodes: list[dict] = [{"name": "arm", "rotation": list(Z_UP_TO_Y_UP), "children": []}]
    idx = {"arm": 0}
    for spec in tree:
        n = {"name": spec["name"], "children": []}
        if spec.get("translation") is not None and np.any(np.abs(spec["translation"]) > 0):
            n["translation"] = [float(x) for x in spec["translation"]]
        if spec.get("rotation") is not None:
            n["rotation"] = [float(x) for x in spec["rotation"]]
        if spec.get("extras"):
            n["extras"] = spec["extras"]
        idx[spec["name"]] = len(nodes)
        nodes.append(n)
    for spec in tree:
        nodes[idx[spec.get("parent") or "arm"]]["children"].append(idx[spec["name"]])
    bin_chunks: list[bytes] = []
    buffer_views, accessors, meshes, materials = [], [], [], []
    mat_idx: dict[tuple, int] = {}
    offset = 0

    def add_view(data: bytes, target: int) -> int:
        nonlocal offset
        pad = (-len(data)) % 4
        bin_chunks.append(data + b"\0" * pad)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target})
        offset += len(data) + pad
        return len(buffer_views) - 1

    tri_total = 0
    for p in parts:
        node = p["node"]
        v = np.asarray(p["v"], np.float32)
        t = np.asarray(p["t"], np.uint32)
        nrm = vertex_normals(v.astype(float), t.astype(np.int64)).astype(np.float32)
        rgba = tuple(round(float(c), 4) for c in (list(p["rgba"]) + [1.0])[:4])
        if rgba not in mat_idx:
            materials.append({"name": "mat_%02x%02x%02x" % tuple(int(c * 255) for c in rgba[:3]),
                              "pbrMetallicRoughness": {"baseColorFactor": list(rgba), "metallicFactor": 0.0,
                                                       "roughnessFactor": 0.6}})
            mat_idx[rgba] = len(materials) - 1
        bv_p = add_view(v.tobytes(), 34962)
        bv_n = add_view(nrm.tobytes(), 34962)
        bv_i = add_view(t.reshape(-1).tobytes(), 34963)
        accessors += [
            {"bufferView": bv_p, "componentType": 5126, "count": len(v), "type": "VEC3",
             "min": [float(x) for x in v.min(0)], "max": [float(x) for x in v.max(0)]},
            {"bufferView": bv_n, "componentType": 5126, "count": len(v), "type": "VEC3"},
            {"bufferView": bv_i, "componentType": 5125, "count": int(t.size), "type": "SCALAR"}]
        a0 = len(accessors) - 3
        meshes.append({"name": p["name"], "primitives": [{"attributes": {"POSITION": a0, "NORMAL": a0 + 1},
                                                           "indices": a0 + 2, "material": mat_idx[rgba]}]})
        nodes.append({"name": p["name"], "mesh": len(meshes) - 1})
        nodes[idx[node]]["children"].append(len(nodes) - 1)
        tri_total += len(t)
    for n in nodes:
        if not n.get("children"):
            n.pop("children", None)
    blob = b"".join(bin_chunks)
    gltf = {
        "asset": {"version": "2.0", "generator": "mechy cad build (animatable, contracts section 11)"},
        "scene": 0,
        "scenes": [{"name": "arm", "nodes": [0], "extras": {
            "units": "m", "frame": "arm base, z up (root node turns it y-up)",
            "joint_names": ["base", "shoulder", "elbow", "wrist"],
            "rest_q_rad": [round(float(x), 6) for x in rest_q], **meta}}],
        "nodes": nodes, "meshes": meshes, "materials": materials, "accessors": accessors,
        "bufferViews": buffer_views, "buffers": [{"byteLength": len(blob)}],
    }
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((-len(js)) % 4)
    total = 12 + 8 + len(js) + 8 + len(blob)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<I4s", len(js), b"JSON"))
        f.write(js)
        f.write(struct.pack("<I4s", len(blob), b"BIN\0"))
        f.write(blob)
    return {"nodes": len(nodes), "meshes": len(meshes), "triangles": tri_total, "bytes": total}


def read_glb(path: Path) -> dict:
    """Parse a GLB's JSON chunk (enough for tests and tools; no mesh data)."""
    raw = Path(path).read_bytes()
    magic, _, _ = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF":
        raise ValueError("not a GLB")
    n, kind = struct.unpack_from("<I4s", raw, 12)
    return json.loads(raw[20:20 + n])


def rest_q_glb(gltf: dict) -> list:
    return list(gltf["scenes"][gltf.get("scene", 0)].get("extras", {}).get("rest_q_rad", [0, 0, 0, 0]))


def node_world(gltf: dict, name: str, q=None, below_root: bool = True, slide_m: float = 0.0) -> np.ndarray:
    """World 4x4 of a named node, with the joint nodes' rotations set to q (contract axes) when q
    is given and the cup_slide node displaced by slide_m along its axis. below_root=True returns it
    in the arm's z-up base frame (root node excluded)."""
    nodes = gltf["nodes"]
    parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}
    k = next(i for i, n in enumerate(nodes) if n.get("name") == name)
    chain = []
    while k is not None:
        chain.append(k)
        k = parent.get(k)
    T = np.eye(4)
    for i in reversed(chain):
        n = nodes[i]
        if below_root and n.get("name") == "arm" and i not in parent:
            continue
        L = np.eye(4)
        L[:3, 3] = n.get("translation", [0, 0, 0])
        if slide_m and n.get("name") == "cup_slide":
            L[:3, 3] = np.asarray(L[:3, 3]) + slide_m * np.asarray(n.get("extras", {}).get("axis", [1, 0, 0]))
        rot = n.get("rotation", [0, 0, 0, 1])
        ex = n.get("extras", {})
        if q is not None and n.get("name") in JOINT_OF:
            ax = ex.get("axis", JOINT_AXES[n["name"]])
            rot = quat_axis_angle(ax, float(q[JOINT_OF[n["name"]]]))
        elif q is not None and ex.get("coupled"):
            ax = ex.get("axis", [0, -1, 0])
            rq = ex.get("rest_q", None) or np.asarray(rest_q_glb(gltf), float)
            ang = float(ex.get("rest", 0.0)) + sum(float(c) * (float(q[j]) - float(rq[j]))
                                                   for j, c in ex["coupled"])
            rot = quat_axis_angle(ax, ang)
        L[:3, :3] = quat_matrix(*rot)
        T = T @ L
    return T
