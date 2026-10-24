"""Joint angles <-> motor angles.

`theta = M @ q`, where q are the joint angles of contracts 7.1 (q1 shoulder elevation,
q2/q3 relative to the previous link) and theta[m] is the joint-side angle that motor m drives
(motor shaft angle = theta[m] * gear_ratio[m]).

In the `belt_arm` design the elbow and wrist are belt pass-through drives with 1:1 belts
along the links and all motors on the turntable, so the elbow motor sets the forearm's
absolute pitch (q1+q2) and the wrist motor the hand's absolute pitch (q1+q2+q3):

    M = [[1,0,0,0],
         [0,1,0,0],
         [0,1,1,0],
         [0,1,1,1]]

`simple` style joints are driven directly (M = I); params `drive.coupling` (passthrough |
independent) overrides the style default. A `motor_mapping` (or `motor_map`, as the CAD build
writes it) entry in design/<v>/mass_props.json overrides both (see `parse_mapping`).
"""

from __future__ import annotations

import numpy as np

JOINTS = ("base", "shoulder", "elbow", "wrist")

PASS_THROUGH = np.array([[1, 0, 0, 0],
                         [0, 1, 0, 0],
                         [0, 1, 1, 0],
                         [0, 1, 1, 1]], float)


def coupling(params: dict) -> str:
    """params `drive.coupling` (passthrough | independent); default passthrough for belt_arm."""
    style = str(params.get("style", "simple"))
    c = str((params.get("drive") or {}).get(
        "coupling", "passthrough" if style in ("belt_arm", "ref_arm") else "independent"))
    if c not in ("passthrough", "independent"):
        raise ValueError(f"unknown drive.coupling {c!r} (passthrough | independent)")
    return c


def default_mapping(params: dict) -> np.ndarray:
    """Pure function of params.yaml: pass-through for belt_arm (or drive.coupling: passthrough),
    identity otherwise."""
    return PASS_THROUGH.copy() if coupling(params) == "passthrough" else np.eye(4)


def parse_mapping(spec, joint_names=JOINTS) -> np.ndarray:
    """Accepts:
    * a 4x4 list (rows = motors, columns = joints), or {"matrix": 4x4};
    * {motor_name: [joint names summed]}, e.g. {"elbow": ["shoulder", "elbow"]};
    * {motor_name: {joint_name: coefficient}};
    * a dict with "motors" holding either of the two dict forms above.
    Motors not named keep their identity row."""
    names = list(joint_names)
    if isinstance(spec, str):
        if spec not in ("passthrough", "independent"):
            raise ValueError(f"motor_mapping {spec!r}: expected passthrough or independent")
        return PASS_THROUGH.copy() if spec == "passthrough" else np.eye(4)
    if isinstance(spec, dict) and "coupling_matrix" in spec:      # ArmModel.motor_map() form
        spec = spec["coupling_matrix"]
    elif isinstance(spec, dict) and "matrix" in spec:
        spec = spec["matrix"]
    elif isinstance(spec, dict) and set(spec) <= {"coupling", "note"} and "coupling" in spec:
        return parse_mapping(spec["coupling"], names)
    elif isinstance(spec, dict) and isinstance(spec.get("motors"), dict):
        spec = spec["motors"]
    if isinstance(spec, (list, tuple)):
        M = np.asarray(spec, float)
        if M.shape != (4, 4):
            raise ValueError(f"motor_mapping matrix must be 4x4, got {M.shape}")
    elif isinstance(spec, dict):
        M = np.eye(4)
        for motor, row in spec.items():
            if motor not in names:
                raise ValueError(f"motor_mapping: unknown motor {motor!r}")
            r = np.zeros(4)
            if isinstance(row, (list, tuple)):
                for j in row:
                    r[names.index(j)] = 1.0
            elif isinstance(row, dict):
                for j, c in row.items():
                    r[names.index(j)] = float(c)
            else:
                raise ValueError(f"motor_mapping[{motor!r}] must be a list of joints or a dict")
            M[names.index(motor)] = r
    else:
        raise ValueError("motor_mapping must be a 4x4 list or a dict")
    if abs(np.linalg.det(M)) < 1e-9:
        raise ValueError("motor_mapping is singular (motors cannot reach every joint pose)")
    return M


def motor_mapping(params: dict, mass_props: dict | None = None) -> tuple[np.ndarray, str]:
    """(M, source) where source says where M came from. mass_props.json `motor_mapping` (or the
    CAD build's `motor_map` block) wins over the params default."""
    for key in ("motor_mapping", "motor_map"):
        if mass_props and mass_props.get(key) is not None:
            return parse_mapping(mass_props[key], [j["name"] for j in params["joints"]]), f"mass_props.json {key}"
    c = coupling(params)
    style = str(params.get("style", "simple"))
    return default_mapping(params), (f"{style} style, {c}: belt pass-through (elbow motor = q1+q2, wrist = q1+q2+q3)"
                                     if c == "passthrough" else f"{style} style, {c}: direct drive")


def joints_to_motors(M: np.ndarray, q) -> np.ndarray:
    return np.asarray(M, float) @ np.asarray(q, float)


def motors_to_joints(M: np.ndarray, theta) -> np.ndarray:
    return np.linalg.solve(np.asarray(M, float), np.asarray(theta, float))
