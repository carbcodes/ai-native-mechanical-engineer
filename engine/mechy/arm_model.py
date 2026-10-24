"""Derived arm quantities from design/v<N>/params.yaml + hw/motors.yaml.

Shared by the CAD generator (MJCF masses), the planner (load inertias) and the sim.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

import numpy as np

from .core import get_core

NEMA17_SIDE_M = 0.0423
NEMA17_LEN_M = 0.040
NEMA17_MASS_KG = 0.28
PULLEY_MASS_KG = 0.02          # belt pulley + bearing at each belt-driven joint
DEFAULT_STEP_RATE_HZ = 4000.0   # per motor, Arduino Uno driving 4 A4988s (assumed)
JOINT_NAMES = ("base", "shoulder", "elbow", "wrist")
DEFAULT_GIVE_M = 0.0            # catcher.give_m: cup travel past the catch point (off: 0.06 m raised impact skips, see summary.md)
DEFAULT_GIVE_RUNUP_M = 0.03     # catcher.give_runup_m: run-up before it
STYLES = ("simple", "belt_arm", "ref_arm")
COUPLINGS = ("independent", "passthrough")
KINEMATICS = ("serial", "parallel_level")
# Ball-on-liner coefficient of restitution (estimates, not measured; verify with a drop test).
# eva_foam 0.40 is what the original sim contact (solref 0.01 0.35) produces; a tennis ball
# rebounds ~0.75 off hard ground (ITF drop test), thin EVA over a rigid shell keeps much of
# that. A slack net/fabric pocket inside the windowed shell is assumed to be much deader.
LINER_RESTITUTION = {"eva_foam": 0.40, "net_pocket": 0.15}
MOVING_BODIES = (("upper_arm", 1, 1), ("forearm", 2, 2), ("hand", 3, 3), ("cup", 3, 4))  # body, first joint, origin point
DEFAULT_MOTOR = {
    "id": "nema17", "holding_torque_nm": 0.45, "rotor_inertia_kgm2": 5.4e-6,
    "max_speed_rps": 10, "step_angle_deg": 1.8,
    "torque_curve": [[0, 0.45], [2, 0.40], [5, 0.28], [10, 0.12]],
}


@dataclass
class ArmModel:
    params: dict
    motors_hw: list = field(default_factory=list)
    drivers_hw: list = field(default_factory=list)
    microsteps_override: int | None = None
    mass_props: dict | None = None      # from the CAD solids (design/vN/mass_props.json), belt_arm style

    def __post_init__(self):
        p = self.params
        self.style = str(p.get("style", "simple"))
        if self.style not in STYLES:
            raise ValueError(f"unknown style {self.style!r}; known: {', '.join(STYLES)}")
        L = p["links"]
        self.name = p.get("name", "v?")
        # ref_arm.mount_mm: a riser (printed column / plywood box) under the socket raises the arm
        self.mount_mm = float((p.get("ref_arm") or {}).get("mount_mm", 0.0))
        self.base_height = float(L["base_height_m"]) + self.mount_mm / 1000.0
        self.upper = float(L["upper_arm_m"])
        self.fore = float(L["forearm_m"])
        self.hand = float(L["hand_m"])
        self.lin_mass = float(L.get("link_mass_kg_per_m", 0.35))
        self.motors_at_base = bool(L.get("motors_at_base", True))
        c = p.get("catcher", {})
        self.cup_d = float(c.get("diameter_m", 0.11))
        self.cup_depth = float(c.get("depth_m", 0.06))
        self._cup_mass = float(c.get("mass_kg", 0.04))
        self.catcher_type = c.get("type", "cup")
        self.liner = str(c.get("liner", "eva_foam"))
        if self.liner not in LINER_RESTITUTION and "restitution" not in c:
            raise ValueError(f"unknown catcher liner {self.liner!r}; known: {', '.join(LINER_RESTITUTION)} "
                             "(or give catcher.restitution)")
        self.cup_restitution = float(c.get("restitution", LINER_RESTITUTION.get(self.liner, 0.40)))
        # kinematics: "parallel_level" (ref_arm, Dobot-style parallel linkage): the wrist joint is
        # passive and the linkage enforces q1+q2+q3 = level const (the hand stays level, pitch 0);
        # the cup opens straight up (catch pitch = +90 deg). Motors drive a = (q0, q1, q1+q2).
        self.kinematics = str(p.get("kinematics") or ("parallel_level" if self.style == "ref_arm" else "serial"))
        if self.kinematics not in KINEMATICS:
            raise ValueError(f"unknown kinematics {self.kinematics!r}; known: {', '.join(KINEMATICS)}")
        self.level_pitch = float(p.get("level_pitch_rad", 0.0))       # q1+q2+q3 the linkage holds
        self.shoulder_x = float(L.get("shoulder_x_m", 0.0))           # shoulder axis fwd of the yaw axis
        self.tool_z = float(L.get("tool_z_m", 0.0))                   # cup centre above the wrist level
        # soft catch (sim + firmware): keep moving the cup along the ball's path through the catch
        # point, starting give_runup_m before it, and stop give_m past it
        self.give_m = float(c.get("give_m", DEFAULT_GIVE_M) or 0.0)
        self.give_runup_m = float(c.get("give_runup_m", DEFAULT_GIVE_RUNUP_M) or 0.0)
        self.compliance = str(c.get("compliance", "none") or "none")
        if self.compliance not in ("none", "spring"):
            raise ValueError(f"unknown catcher.compliance {self.compliance!r}; known: none, spring")
        self.spring_k = float(c.get("spring_k_n_per_m", 400.0))
        self.spring_travel = float(c.get("spring_travel_m", 0.025))
        self.spring_zeta = float(c.get("spring_damping_ratio", 0.4))
        js = p["joints"]
        if len(js) != 4:
            raise ValueError("params.yaml must list exactly 4 joints (base, shoulder, elbow, wrist)")
        self.joint_names = [j["name"] for j in js]
        self.limits = np.radians(np.array([j["limit_deg"] for j in js], float))
        self.gear = np.array([float(j.get("gear_ratio", 1.0)) for j in js])
        by_id = {m.get("id"): m for m in (self.motors_hw or [])}
        self.motor_specs = []
        for j in js:
            m = dict(DEFAULT_MOTOR)
            m.update(by_id.get(j.get("motor", "nema17"), {}))
            self.motor_specs.append(m)
        # elbow/wrist drive: "passthrough" = 1:1 belts along the links from pulleys turning on the
        # shoulder shaft, so the elbow motor sets the forearm's absolute pitch (q1+q2) and the wrist
        # motor the hand's (q1+q2+q3); "independent" = each motor drives its own joint angle.
        drive = p.get("drive") or {}
        self.coupling = str(drive.get("coupling",
                                     "passthrough" if self.style in ("belt_arm", "ref_arm") else "independent"))
        if self.coupling not in COUPLINGS:
            raise ValueError(f"unknown drive.coupling {self.coupling!r}; known: {', '.join(COUPLINGS)}")
        drv = (self.drivers_hw or [{}])[0]
        self.microsteps = int(self.microsteps_override or drv.get("microsteps", 16))
        rate = drv.get("max_step_rate_hz", DEFAULT_STEP_RATE_HZ)
        self.step_rate_hz = float(rate) if rate else None

    # ------------------------------------------------------------- masses
    @property
    def cup_mass(self) -> float:
        if self.mass_props:
            return float(self.mass_props["bodies"]["cup"]["mass"])
        return self._cup_mass

    def link_masses(self) -> np.ndarray:
        """Masses of upper arm, forearm, hand links (kg), excluding the cup."""
        if self.mass_props:
            b = self.mass_props["bodies"]
            return np.array([float(b[n]["mass"]) for n in ("upper_arm", "forearm", "hand")])
        return self.lin_mass * np.array([self.upper, self.fore, self.hand])

    def _parallel_lumped(self):
        """parallel_level lumped bodies: (name, kind) with kind in ("pitch1" (rotates about S by q1),
        "pitch2" (rotates about E by a2 = q1+q2), "level" (keeps orientation, origin tracks a link
        point), "yaw"). The CAD build lumps each passive link into the nearest contract body, so
        these bodies are what MJCF and this model share."""
        return (("upper_arm", "pitch1"), ("forearm", "pitch2"), ("hand", "level"), ("cup", "level"))

    def _parallel_points(self, q):
        """Link-frame pivots (x, z) in the radial plane for parallel_level: S, E, W, cup centre."""
        q1, a2 = float(q[1]), float(q[1]) + float(q[2])
        sx, h = self.shoulder_x, self.base_height
        E = (sx + self.upper * math.cos(q1), h + self.upper * math.sin(q1))
        W = (E[0] + self.fore * math.cos(a2), E[1] + self.fore * math.sin(a2))
        T = (W[0] + self.hand, W[1] + self.tool_z)
        return (sx, h), E, W, T

    def _parallel_body_coms(self, q, ball_mass: float = 0.0):
        """World (x, z, y) coms of the lumped moving bodies plus the ball, in the un-yawed plane."""
        q = np.asarray(q, float)
        S, E, W, T = self._parallel_points(q)
        a2 = float(q[1] + q[2])
        origins = {"upper_arm": (S, q[1]), "forearm": (E, a2), "hand": (W, self.level_pitch),
                   "cup": (T, self.level_pitch)}
        out = []
        for name, _ in self._parallel_lumped():
            b = self.mass_props["bodies"][name]
            (ox, oz), ang = origins[name]
            c = np.asarray(b["com"], float)
            ca, sa = math.cos(ang), math.sin(ang)
            out.append((name, float(b["mass"]),
                        np.array([ox + c[0] * ca - c[2] * sa, c[1], oz + c[0] * sa + c[2] * ca]),
                        np.asarray(b["inertia"], float)))
        out.append(("ball", float(ball_mass), np.array([T[0], 0.0, T[1]]), np.zeros((3, 3))))
        return out

    def _parallel_a_torque_inertia(self, q, ball_mass: float):
        """Motor-coordinate (a0=q0 yaw, a1=q1, a2=q1+q2, a3=q123 const) statics: gravity torque
        tau_a = -dU/da and load inertia J_a = sum m |d com/da|^2 + I_pitch (d pitch/da)^2.
        Coms are differentiated numerically in the (a1, a2) coordinates."""
        q = np.asarray(q, float)
        h = 1e-7

        def state(a1, a2):
            qq = np.array([q[0], a1, a2 - a1, self.level_pitch - a2])
            return self._parallel_body_coms(qq, ball_mass)

        coms0 = state(q[1], q[1] + q[2])
        U0 = 9.81 * sum(m * p[2] for _, m, p, _ in coms0)
        tau = np.zeros(4)
        J = np.zeros(4)
        for j, a_j, is_a1 in ((1, q[1], True), (2, q[1] + q[2], False)):
            def pos_at(d, a_j=a_j, is_a1=is_a1):
                # differentiate in motor coordinates: for a1 hold a2 fixed, for a2 hold a1 fixed
                return state(a_j + d, q[1] + q[2]) if is_a1 else state(q[1], a_j + d)
            dp = pos_at(h)
            dm = pos_at(-h)
            U_p = 9.81 * sum(m * p[2] for _, m, p, _ in dp)
            U_m = 9.81 * sum(m * p[2] for _, m, p, _ in dm)
            tau[j] = (U_p - U_m) / (2 * h)              # matches MuJoCo qfrc_bias sign convention
            for (_, m, p0, Ip), (_, _, pp, _), (_, _, pm, _) in zip(coms0, dp, dm):
                dpos = (pp - pm) / (2 * h)
                J[j] += m * float(dpos @ dpos)
            for (name, kind), (_, _, _, Ip) in zip(self._parallel_lumped(), coms0):
                rot = 1.0 if (kind == "pitch1" and is_a1) or (kind == "pitch2" and not is_a1) else 0.0
                J[j] += float(Ip[1, 1]) * rot
        # yaw inertia: every body orbits the z axis
        for name, m, p, Ip in coms0:
            J[0] += m * float(p[0] ** 2 + p[1] ** 2) + float(Ip[2, 2])
        tt = self.mass_props["bodies"].get("turntable")
        if tt:
            c = np.asarray(tt["com"], float)
            J[0] += float(tt["mass"]) * float(c[0] ** 2 + c[1] ** 2) + float(np.asarray(tt["inertia"])[2, 2])
        return tau, J

    def _cad_bodies(self, q, ball_mass: float):
        """Moving bodies from CAD mass properties at pose q: list of (com world (3,), mass,
        first joint, inertia about com in world axes (3,3)). The ball is a point at the cup centre."""
        q = np.asarray(q, float)
        P = self.points(q)
        cy, sy = math.cos(q[0]), math.sin(q[0])
        u, v, ez = np.array([cy, sy, 0.0]), np.array([-sy, cy, 0.0]), np.array([0.0, 0.0, 1.0])
        Rz = np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1.0]])
        angs = np.cumsum(q[1:4])
        out = []
        for name, first, k in MOVING_BODIES:
            b = self.mass_props["bodies"][name]
            a = float(angs[first - 1])
            ca, sa = math.cos(a), math.sin(a)
            cx, cyy, cz = b["com"]
            pos = P[k] + (cx * ca - cz * sa) * u + (cx * sa + cz * ca) * ez + cyy * v
            R = Rz @ np.array([[ca, 0, -sa], [0, 1, 0], [sa, 0, ca]])
            out.append((pos, float(b["mass"]), first, R @ np.asarray(b["inertia"], float) @ R.T))
        out.append((P[4], ball_mass, 3, np.zeros((3, 3))))
        return out

    def _cad_load_inertia(self, q, ball_mass: float) -> np.ndarray:
        q = np.asarray(q, float)
        P = self.points(q)
        v = np.array([-math.sin(q[0]), math.cos(q[0]), 0.0])     # pitch axes direction
        bodies = self._cad_bodies(q, ball_mass)
        J = np.zeros(4)
        for j in range(1, 4):
            for pos, m, first, I in bodies:
                if first < j:
                    continue
                d = pos - P[j]
                d -= (d @ v) * v
                J[j] += m * float(d @ d) + float(v @ I @ v)
        for pos, m, first, I in bodies:
            J[0] += m * float(pos[0] ** 2 + pos[1] ** 2) + float(I[2, 2])
        tt = self.mass_props["bodies"].get("turntable")
        if tt:
            cx, cyy, _ = tt["com"]
            J[0] += float(tt["mass"]) * (cx * cx + cyy * cyy) + float(np.asarray(tt["inertia"])[2, 2])
        return J

    def _cad_gravity_torque(self, q, ball_mass: float) -> np.ndarray:
        q = np.asarray(q, float)
        P = self.points(q)
        u = np.array([math.cos(q[0]), math.sin(q[0]), 0.0])
        out = np.zeros(4)
        bodies = self._cad_bodies(q, ball_mass)
        for j in range(1, 4):
            out[j] = abs(9.81 * sum(m * float((pos - P[j]) @ u) for pos, m, first, _ in bodies if first >= j))
        return out

    # ------------------------------------------------------- motor mapping
    @property
    def coupling_matrix(self) -> np.ndarray:
        """C with motor-side coordinate a = C @ q (each motor turns gear_ratio * a). Identity for
        independent joints; for belt pass-through a = (q0, q1, q1+q2, q1+q2+q3)."""
        if self.coupling == "passthrough":
            return np.array([[1.0, 0, 0, 0], [0, 1, 0, 0], [0, 1, 1, 0], [0, 1, 1, 1]])
        return np.eye(4)

    def to_motor(self, q) -> np.ndarray:
        """Joint angles (..., 4) -> motor-side coordinates a = C q (rad at the output pulley)."""
        return np.asarray(q, float) @ self.coupling_matrix.T

    def from_motor(self, a) -> np.ndarray:
        return np.asarray(a, float) @ np.linalg.inv(self.coupling_matrix).T

    def motor_angles(self, q) -> np.ndarray:
        """Motor shaft angles (rad) for joint angles q: gear_ratio * (C q)."""
        return self.gear * self.to_motor(q)

    def steps_per_rad(self) -> np.ndarray:
        """Driver (micro)steps per radian of the motor-side coordinate a."""
        spr = np.array([360.0 / float(m.get("step_angle_deg", 1.8)) * self.microsteps for m in self.motor_specs])
        return spr * self.gear / (2 * math.pi)

    def motor_steps(self, q) -> np.ndarray:
        """Step counts from the q = 0 home for joint angles q (what firmware commands)."""
        return np.rint(self.steps_per_rad() * self.to_motor(q)).astype(np.int64)

    def motor_map(self) -> dict:
        """The joint <-> motor mapping as data, for report meta / mass_props.json / firmware."""
        C = self.coupling_matrix
        spr = self.steps_per_rad()
        return {
            "coupling": self.coupling,
            "joint_names": list(self.joint_names),
            "coupling_matrix": C.tolist(),
            "gear_ratio": [float(g) for g in self.gear],
            "microsteps": self.microsteps,
            "steps_per_rad": [round(float(x), 4) for x in spr],
            "steps_per_deg": [round(float(x) * math.pi / 180, 5) for x in spr],
            "formula": ("motor_angle = gear_ratio * (C @ q); steps = round(steps_per_rad * (C @ q)); "
                        "q = C^-1 @ (motor_angle / gear_ratio); motor torque = (C^-T tau_joint) / gear_ratio"),
            "inverse": np.linalg.inv(C).round(12).tolist(),
            "note": ("belt pass-through: the elbow motor sets the forearm's absolute pitch q1+q2 and the wrist "
                     "motor the hand's q1+q2+q3; moving the shoulder alone keeps forearm and cup pitch fixed"
                     if self.coupling == "passthrough" else "each motor drives its own joint angle"),
        }

    # ------------------------------------------------- dynamics (pitch joints)
    def _pitch_bodies(self, q, ball_mass: float):
        """Moving bodies as (com (3,), mass, first joint, rotational inertia about the pitch axis)."""
        q = np.asarray(q, float)
        v = np.array([-math.sin(q[0]), math.cos(q[0]), 0.0])
        if self.mass_props:
            return [(pos, m, first, float(v @ I @ v)) for pos, m, first, I in self._cad_bodies(q, ball_mass)]
        pos, mass, first = self._point_masses(q, ball_mass)
        out = [(pos[k], float(mass[k]), int(first[k]), 0.0) for k in range(len(mass))]
        L = np.array([self.upper, self.fore, self.hand])
        m = self.link_masses()
        for k in range(3):                         # rod inertia of each link
            out.append((self.points(q)[k + 1], 0.0, k + 1, float(m[k] * L[k] ** 2 / 12)))
        out.append((self.points(q)[4], 0.0, 3, float(self.cup_mass * (self.cup_d / 2) ** 2 / 2)))
        return out

    def pitch_mass_matrix(self, q, ball_mass: float = 0.057) -> np.ndarray:
        """Joint-space inertia (3,3) of the shoulder, elbow, wrist joints at pose q (kg m^2),
        rotor inertia excluded. Its diagonal equals load_inertia(q)[1:]."""
        q = np.asarray(q, float)
        P = self.points(q)
        v = np.array([-math.sin(q[0]), math.cos(q[0]), 0.0])
        M = np.zeros((3, 3))
        for pos, m, first, Irot in self._pitch_bodies(q, ball_mass):
            for i in range(1, 4):
                if first < i:
                    continue
                di = pos - P[i]
                di = di - (di @ v) * v
                for j in range(1, 4):
                    if first < j:
                        continue
                    dj = pos - P[j]
                    dj = dj - (dj @ v) * v
                    M[i - 1, j - 1] += m * float(di @ dj) + Irot
        return M

    def motor_load_inertia(self, q=None, ball_mass: float = 0.057) -> np.ndarray:
        """Load inertia seen by each motor's output pulley (kg m^2 about the motor-side coordinate a),
        i.e. the diagonal of C^-T M C^-1. Equals load_inertia() for independent joints."""
        if q is None:
            q = np.zeros(4)
        if self.kinematics == "parallel_level" and self.mass_props:
            return self._parallel_a_torque_inertia(q, ball_mass)[1]
        J = self.load_inertia(q, ball_mass)
        if self.coupling == "independent":
            return J
        Ci = np.linalg.inv(self.coupling_matrix)[1:, 1:]
        Ma = Ci.T @ self.pitch_mass_matrix(q, ball_mass) @ Ci
        return np.concatenate([[J[0]], np.diag(Ma)])

    def gravity_torque_signed(self, q, ball_mass: float = 0.057) -> np.ndarray:
        """Joint-side gravity torque with sign (N m, positive = gravity pushes the joint toward +q)."""
        q = np.asarray(q, float)
        if self.kinematics == "parallel_level":
            q = q.copy()
            q[3] = self.level_pitch - q[1] - q[2]
            if self.mass_props:
                tau_a = self._parallel_a_torque_inertia(q, ball_mass)[0]
            else:
                tau_a = np.zeros(4)
                P = self.points(q)
                u = np.array([math.cos(q[0]), math.sin(q[0]), 0.0])
                pos, mass, first = self._point_masses(q, ball_mass)
                m3 = float(mass[first >= 2].sum())
                L1, L2 = self.upper, self.fore
                m_ls, m_us = float(mass[0]), float(mass[1])
                tau_a[1] = -9.81 * math.cos(q[1]) * L1 * (m_ls / 2 + m_us + m3)
                tau_a[2] = -9.81 * math.cos(q[1] + q[2]) * L2 * (m_us / 2 + m3)
                tau_a[0] = 0.0
            return self.coupling_matrix.T @ tau_a   # joint-side equivalent; C^-T gives tau_a back
        P = self.points(q)
        u = np.array([math.cos(q[0]), math.sin(q[0]), 0.0])
        out = np.zeros(4)
        for j in range(1, 4):
            out[j] = -9.81 * sum(m * float((pos - P[j]) @ u)
                                 for pos, m, first, _ in self._pitch_bodies(q, ball_mass) if first >= j and m > 0)
        return out

    def motor_gravity_torque(self, q=None, ball_mass: float = 0.057) -> np.ndarray:
        """Static gravity torque each motor's output pulley holds (N m, magnitude): |C^-T tau_q|."""
        if q is None:
            q = np.zeros(4)
        tau = self.gravity_torque_signed(q, ball_mass)
        return np.abs(np.linalg.inv(self.coupling_matrix).T @ tau)

    def motor_gravity_torque_max(self, ball_mass: float = 0.057) -> np.ndarray:
        return self.motor_gravity_torque(np.zeros(4), ball_mass)

    def moving_motor_mass(self) -> float:
        """Motors carried by the shoulder/elbow joints (0 when all motors sit at the base)."""
        return 0.0 if self.motors_at_base else NEMA17_MASS_KG

    def _point_masses(self, q, ball_mass: float):
        """Point masses (pos (K,3), mass (K,), first joint index they hang from) for pose q.
        Joint indices: 1 = moves with the upper arm, 2 = forearm, 3 = hand."""
        P = self.points(q)               # base, shoulder, elbow, wrist, tip
        m = self.link_masses()
        pos, mass, first = [], [], []
        for k in range(3):               # link midpoints
            pos.append((P[k + 1] + P[k + 2]) / 2)
            mass.append(m[k])
            first.append(k + 1)
        for k in (2, 3):                 # pulleys (and carried motors) at elbow and wrist
            pos.append(P[k])
            mass.append(PULLEY_MASS_KG + (self.moving_motor_mass() if k == 2 else 0.0))
            first.append(k)
        pos.append(P[4])
        mass.append(self.cup_mass + ball_mass)
        first.append(3)
        return np.array(pos), np.array(mass), np.array(first)

    def points(self, q) -> np.ndarray:
        """Base, shoulder, elbow, wrist, tool (cup centre) positions (5,3) at pose q
        (contracts 7.1 conventions)."""
        q = np.asarray(q, float)
        if self.kinematics == "parallel_level":
            q = q.copy()
            q[3] = self.level_pitch - q[1] - q[2]           # passive wrist keeps the hand level
            S, E, W, T = self._parallel_points(q)
            cy, sy = math.cos(q[0]), math.sin(q[0])
            pts = [np.zeros(3), np.array([S[0] * cy, S[0] * sy, S[1]]),
                   np.array([E[0] * cy, E[0] * sy, E[1]]), np.array([W[0] * cy, W[0] * sy, W[1]]),
                   np.array([T[0] * cy, T[0] * sy, T[1]])]
            return np.array(pts)
        pts = [np.zeros(3), np.array([0.0, 0.0, self.base_height])]
        r, z, ang = 0.0, self.base_height, 0.0
        for L, dq in zip((self.upper, self.fore, self.hand), q[1:]):
            ang += dq
            r += L * math.cos(ang)
            z += L * math.sin(ang)
            pts.append(np.array([r * math.cos(q[0]), r * math.sin(q[0]), z]))
        return np.array(pts)

    def load_inertia(self, q=None, ball_mass: float = 0.057) -> np.ndarray:
        """Joint-side load inertia (kg m^2) about each joint axis at pose q (default: arm
        stretched horizontally, the worst case). Point masses plus rod inertia of each link."""
        if q is None:
            q = np.zeros(4)
        q = np.asarray(q, float)
        if self.kinematics == "parallel_level" and self.mass_props:
            return self._parallel_a_torque_inertia(q, ball_mass)[1]
        if self.mass_props:
            return self._cad_load_inertia(q, ball_mass)
        P = self.points(q)
        pos, mass, first = self._point_masses(q, ball_mass)
        L = np.array([self.upper, self.fore, self.hand])
        m = self.link_masses()
        J = np.zeros(4)
        for j in range(1, 4):
            axis_pt = P[j]                       # pitch axis passes through this point (horizontal)
            sel = first >= j
            d = pos[sel] - axis_pt
            J[j] = float(np.sum(mass[sel] * np.sum(d ** 2, axis=1)))
            J[j] += float(sum(m[k] * L[k] ** 2 / 12 for k in range(j - 1, 3)))
            J[j] += self.cup_mass * (self.cup_d / 2) ** 2 / 2
        r2 = np.sum(pos[:, :2] ** 2, axis=1)
        turntable = 0.5 * 0.15 * 0.07 ** 2
        motors_on_turntable = 3 * NEMA17_MASS_KG * 0.05 ** 2 if self.motors_at_base else 0.0
        J[0] = float(np.sum(mass * r2)) + turntable + motors_on_turntable + self.cup_mass * (self.cup_d / 2) ** 2 / 2
        return J

    def gravity_torque(self, q=None, ball_mass: float = 0.057) -> np.ndarray:
        """Joint-side static gravity torque magnitude (N m) at pose q (default: stretched)."""
        if q is None:
            q = np.zeros(4)
        if self.mass_props:
            return self._cad_gravity_torque(q, ball_mass)
        P = self.points(q)
        pos, mass, first = self._point_masses(q, ball_mass)
        out = np.zeros(4)
        yaw = float(np.asarray(q)[0])
        u = np.array([math.cos(yaw), math.sin(yaw), 0.0])   # radial direction of the arm plane
        for j in range(1, 4):
            sel = first >= j
            lever = (pos[sel] - P[j]) @ u
            out[j] = abs(9.81 * float(np.sum(mass[sel] * lever)))
        return out

    def gravity_torque_max(self, ball_mass: float = 0.057) -> np.ndarray:
        return self.gravity_torque(np.zeros(4), ball_mass)

    # ------------------------------------------------------- core objects
    def core_arm(self):
        if self.kinematics == "parallel_level":
            return ParallelLevelArm(self)
        return get_core().Arm(self.base_height, self.upper, self.fore, self.hand, limits=self.limits)

    def max_speed_rps(self, i: int) -> float:
        """Usable motor speed: min of the motor's max_speed_rps and the driver step-rate cap."""
        m = self.motor_specs[i]
        cap = float(m.get("max_speed_rps") or m["torque_curve"][-1][0])
        if self.step_rate_hz:
            steps_rev = 360.0 / float(m.get("step_angle_deg", 1.8)) * self.microsteps
            cap = min(cap, self.step_rate_hz / steps_rev)
        return cap

    def core_motors(self):
        mc = get_core()
        return [mc.Stepper(np.asarray(m["torque_curve"], float), float(g), float(m["rotor_inertia_kgm2"]),
                           self.max_speed_rps(i))
                for i, (m, g) in enumerate(zip(self.motor_specs, self.gear))]

    @property
    def reach(self) -> float:
        return self.upper + self.fore + self.hand

    def ready_pose(self) -> np.ndarray:
        rp = self.params.get("ready_pose_deg")
        if rp:
            return np.radians(np.asarray(rp, float))
        q = np.radians([0.0, 70.0, -80.0, 40.0])   # contracts 7.1: elevation, relative, +up
        return np.clip(q, self.limits[:, 0], self.limits[:, 1])


def torque_curve_at(spec: dict, omega_motor: float) -> float:
    tc = np.asarray(spec["torque_curve"], float)
    rps = abs(omega_motor) / (2 * math.pi)
    if rps > tc[-1, 0]:
        return 0.0
    return float(np.interp(rps, tc[:, 0], tc[:, 1]))


def load_mass_props(project, variant: str, params: dict) -> dict | None:
    """CAD mass properties for a belt_arm/ref_arm variant: design/vN/mass_props.json when it matches
    the current params, else computed from the solids (slower)."""
    style = params.get("style", "simple")
    if style not in ("belt_arm", "ref_arm"):
        return None
    from .cad.belt_arm import params_hash
    f = project.variant_dir(variant) / "mass_props.json"
    if f.exists():
        try:
            mp = json.loads(f.read_text())
            if mp.get("params_hash") == params_hash(params):
                return mp
        except (ValueError, OSError):
            pass
    if style == "ref_arm":
        from .cad.ref_arm import build_design
    else:
        from .cad.belt_arm import build_design
    return build_design(ArmModel(params)).mass_props()


class ParallelLevelArm:
    """Core-Arm-compatible kinematics for `kinematics: parallel_level` (ref_arm style).

    The parallel linkage holds q1+q2+q3 = level_pitch (the manipulator stays level and the cup
    opens straight up), so the hand pitch is fixed: fk always reports cup-axis pitch pi/2 and ik
    solves the two-shank planar problem for the wrist point behind the tool offset."""

    def __init__(self, model: "ArmModel"):
        self.model = model
        self._lim = model.limits.copy()

    @property
    def limits(self) -> np.ndarray:
        return self._lim.copy()

    def within_limits(self, q, tol: float = 1e-9) -> bool:
        q = np.asarray(q, float)
        return bool(np.all(q >= self._lim[:, 0] - tol) and np.all(q <= self._lim[:, 1] + tol))

    def fk(self, q):
        P = self.model.points(q)
        return P[4].copy(), self.model.level_pitch + math.pi / 2  # cup opens up: axis elevation +90 deg

    def ik(self, target_xyz, hand_pitch: float = math.pi / 2, seed=None):
        m = self.model
        x, y, z = (float(v) for v in target_xyz)
        if not all(math.isfinite(v) for v in (x, y, z)):
            return None
        r = math.hypot(x, y)
        yaw = (float(seed[0]) if seed is not None else 0.0) if r < 1e-9 else math.atan2(y, x)
        # wrist pivot = cup centre minus the level tool offset (hand_m radial, tool_z vertical)
        cy, sy = math.cos(yaw), math.sin(yaw)
        rw = x * cy + y * sy - m.shoulder_x - m.hand
        zw = z - m.base_height - m.tool_z
        a, b = m.upper, m.fore
        c2 = (rw * rw + zw * zw - a * a - b * b) / (2 * a * b)
        if c2 > 1 + 1e-9 or c2 < -1 - 1e-9:
            return None
        q2abs = math.acos(min(1.0, max(-1.0, c2)))
        ref = np.asarray(seed, float) if seed is not None else np.array([yaw, 0, 0, 0.0])
        best, out = math.inf, None
        for sgn in (1.0, -1.0):
            q2 = sgn * q2abs
            q1 = math.atan2(zw, rw) - math.atan2(b * math.sin(q2), a + b * math.cos(q2))
            q = np.array([yaw, q1, q2, m.level_pitch - q1 - q2])
            q[3] = (q[3] + math.pi) % (2 * math.pi) - math.pi
            if self.within_limits(q):
                cost = float(np.sum((q - ref) ** 2))
                if cost < best:
                    best, out = cost, q
            if q2abs == 0.0:
                break
        if out is not None:
            out = np.clip(out, self._lim[:, 0], self._lim[:, 1])
            out[3] = m.level_pitch - out[1] - out[2]
        return out

    def reachable(self, target_xyz, hand_pitch: float = math.pi / 2) -> bool:
        return self.ik(target_xyz, hand_pitch) is not None

    def __reduce__(self):
        return (_parallel_level_arm_from_params, (self.model.params,))


def _parallel_level_arm_from_params(params):
    return ParallelLevelArm(ArmModel(params))


def load_arm(project, variant: str, microsteps: int | None = None) -> ArmModel:
    hw = project.hardware()
    params = project.params(variant)
    return ArmModel(params, hw["motors"], hw["drivers"], microsteps, load_mass_props(project, variant, params))
