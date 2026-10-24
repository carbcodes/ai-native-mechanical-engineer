"""MuJoCo MJCF generated from the same params as the CAD model.

Frames follow contracts 7.1: at q = 0 every link points along +X (horizontal), pitch
joints use axis (0, -1, 0) so positive = up and MuJoCo qpos equals mechy_core's q exactly,
base yaw is about +Z. The cup's centre (hand tip) sits at the `cup` body origin; the cup
body's local +Z (its opening) points along the hand. A `ball` free body is included (parked on the floor)
so the same file can be used for catching sims.
"""

from __future__ import annotations

import functools
import math
import numpy as np

from ..arm_model import NEMA17_MASS_KG, NEMA17_SIDE_M, PULLEY_MASS_KG, ArmModel

CUP_WALL_SEGMENTS = 16
CUP_WALL_T = 0.004
STEPPER_TEETH = 50          # 1.8 deg hybrid stepper: 50 rotor teeth


def _f(*v) -> str:
    return " ".join(f"{float(x):.6g}" for x in v)


def stepper_kp(arm: ArmModel, i: int) -> float:
    """Small-angle joint-side stiffness of a stepper holding position (N m/rad)."""
    hold = float(arm.motor_specs[i]["torque_curve"][0][1])
    return hold * STEPPER_TEETH * arm.gear[i] ** 2


def cad_inertial(b: dict, R=None) -> str:
    """<inertial> from CAD mass properties (com from the body origin, inertia about the com).
    R: columns = this body's MJCF axes in the CAD body axes (for rotated bodies such as the cup)."""
    com = np.asarray(b["com"], float)
    I = np.asarray(b["inertia"], float)
    if R is not None:
        com, I = R.T @ com, R.T @ I @ R
    I = (I + I.T) / 2
    w = np.linalg.eigvalsh(I)
    if w.min() <= 1e-10:                      # keep MuJoCo happy for near-degenerate parts
        I = I + np.eye(3) * (1e-9 - min(w.min(), 0))
    full = _f(I[0, 0], I[1, 1], I[2, 2], I[0, 1], I[0, 2], I[1, 2])
    return f'<inertial pos="{_f(*com)}" mass="{float(b["mass"]):.6g}" fullinertia="{full}"/>'


CUP_R = np.array([[0.0, 0, 1], [0, 1, 0], [-1, 0, 0]])   # MJCF zaxis="1 0 0" = rotation of +90 deg about y


BALL_SOLREF = (0.01, 0.35)
CONTACT_SOLIMP = "0.9 0.95 0.001"


def drop_restitution(cup_dampratio: float, v: float = 4.0, timeconst: float = 0.01) -> float:
    """Measured (MuJoCo) restitution of the ball dropped on a cup-class surface at v m/s."""
    import mujoco
    xml = f"""<mujoco><option timestep="0.0005" gravity="0 0 0" integrator="implicitfast"/>
    <worldbody><geom type="box" size="0.1 0.1 0.002" solref="{timeconst} {cup_dampratio}" solimp="{CONTACT_SOLIMP}"/>
    <body pos="0 0 0.04"><freejoint/><geom type="sphere" size="0.0335" mass="0.057" solref="{_f(*BALL_SOLREF)}"
    solimp="{CONTACT_SOLIMP}" condim="4" conaffinity="3"/></body></worldbody></mujoco>"""
    m = mujoco.MjModel.from_xml_string(xml)
    d = mujoco.MjData(m)
    d.qvel[2] = -v
    for _ in range(1200):
        mujoco.mj_step(m, d)
    return float(d.qvel[2] / v)


@functools.lru_cache(maxsize=32)
def cup_dampratio(restitution: float) -> float:
    """Cup contact damping ratio that gives `restitution` in a MuJoCo drop test (bisection).
    The ball's own solref is mixed in by MuJoCo, so the mapping is calibrated, not analytic."""
    lo, hi = 0.0, 6.0
    if restitution >= drop_restitution(lo):
        return lo
    if restitution <= drop_restitution(hi):
        return hi
    for _ in range(24):
        mid = (lo + hi) / 2
        if drop_restitution(mid) > restitution:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 4)


def build_mjcf(arm: ArmModel, ball_diameter: float = 0.067, ball_mass: float = 0.057,
               timestep: float = 0.0005) -> str:
    L1, L2, L3 = arm.upper, arm.fore, arm.hand
    h = arm.base_height
    m1, m2, m3 = arm.link_masses()
    lim = arm.limits
    rotor = [float(m["rotor_inertia_kgm2"]) for m in arm.motor_specs]
    armature = [rotor[i] * arm.gear[i] ** 2 for i in range(4)]
    J = arm.load_inertia(None, ball_mass)
    r_cup = arm.cup_d / 2
    depth = arm.cup_depth
    hand_len = max(L3 - depth / 2, 0.005)

    def rod_inertial(m, L, extra_pos=0.0):
        ixx = m * L * L / 12 + 1e-6
        return (f'<inertial pos="{L / 2 + extra_pos:.6g} 0 0" mass="{max(m, 1e-4):.6g}" '
                f'diaginertia="{min(max(m * 5e-5, 1e-8), ixx):.6g} {ixx:.6g} {ixx:.6g}"/>')

    def joint(i, axis):
        nm = arm.joint_names[i]
        return (f'<joint name="{nm}" type="hinge" axis="{axis}" range="{_f(*lim[i])}" '
                f'limited="true" armature="{armature[i]:.6g}" damping="0.002"/>')

    parallel = arm.kinematics == "parallel_level"
    # actuator gains: stiffness of the stepper, damping ratio ~0.7 for the stretched-arm inertia
    act = []
    for i, nm in enumerate(arm.joint_names):
        if parallel and i == 3:
            continue                                    # passive wrist: no actuator (Dobot linkage)
        kp = stepper_kp(arm, i)
        kv = 2 * 0.7 * math.sqrt(kp * (J[i] + armature[i]))
        tmax = float(arm.motor_specs[i]["torque_curve"][0][1]) * arm.gear[i]
        act.append(f'    <position name="act_{nm}" joint="{nm}" kp="{kp:.6g}" kv="{kv:.6g}" '
                   f'ctrlrange="{_f(*lim[i])}" ctrllimited="true" forcerange="{_f(-tmax, tmax)}" '
                   f'forcelimited="true"/>')

    # cup: bottom disc + ring of boxes, opening along +Z, centre at origin
    cup_geoms = [f'<geom name="cup_bottom" type="cylinder" size="{r_cup + CUP_WALL_T:.6g} {CUP_WALL_T / 2:.6g}" '
                 f'pos="0 0 {-depth / 2 - CUP_WALL_T / 2:.6g}" class="cup"/>']
    n = CUP_WALL_SEGMENTS
    seg_w = 2 * (r_cup + CUP_WALL_T) * math.tan(math.pi / n) * 1.05
    for k in range(n):
        a = 2 * math.pi * k / n
        rr = r_cup + CUP_WALL_T / 2
        cup_geoms.append(
            f'<geom name="cup_wall{k}" type="box" size="{CUP_WALL_T / 2:.6g} {seg_w / 2:.6g} {depth / 2:.6g}" '
            f'pos="{rr * math.cos(a):.6g} {rr * math.sin(a):.6g} 0" euler="0 0 {a:.6g}" class="cup"/>')
    cup_xml = "\n            ".join(cup_geoms)

    s = NEMA17_SIDE_M
    motors_xml = ""
    turntable_mass = 0.15
    if arm.motors_at_base:
        mot = []
        for k, nm in enumerate(("shoulder", "elbow", "wrist")):
            mot.append(f'<geom name="motor_{nm}" type="box" size="{s / 2:.4g} {0.02:.4g} {s / 2:.4g}" '
                       f'pos="-0.05 {(k - 1) * 0.045:.4g} {0.077:.4g}" mass="{NEMA17_MASS_KG}" class="visual" rgba="0.15 0.15 0.17 1"/>')
        motors_xml = "\n        ".join(mot)

    pulley_m = PULLEY_MASS_KG
    # catcher.compliance: spring = the cup rides on a slide along its axis, sprung toward the opening
    travel = arm.spring_travel if arm.compliance == "spring" else 0.0
    slide = ""
    if arm.compliance == "spring":
        m_cup = arm.cup_mass
        c_spring = 2 * arm.spring_zeta * math.sqrt(arm.spring_k * max(m_cup, 1e-3))
        # preload: the drawn spring pair is compressed by preload_m at rest (mass_props.json -> slide), so
        # the spring's zero-force position sits preload_m in front of the front stop (q = 0)
        preload = float(((arm.mass_props or {}).get("slide") or {}).get("preload_m", 0.0))
        # catcher.spring_friction_n: Coulomb drag of the slide's friction brake (felt pads on the rods)
        fric = float((arm.params.get("catcher") or {}).get("spring_friction_n", 0.0) or 0.0)
        slide = (f'<joint name="cup_slide" type="slide" axis="0 0 1" range="{-travel:.6g} 0" limited="true" '
                 f'stiffness="{arm.spring_k:.6g}" springref="{preload:.6g}" damping="{c_spring:.6g}"'
                 f'{f" frictionloss={chr(34)}{fric:.6g}{chr(34)}" if fric > 0 else ""}/>')
    # liner restitution 0.40 reproduces the original constant (0.35) exactly
    cup_dr = 0.35 if abs(arm.cup_restitution - 0.40) < 1e-9 else cup_dampratio(round(arm.cup_restitution, 3))
    mp = (arm.mass_props or {}).get("bodies") if arm.mass_props else None
    if mp:
        # belt_arm: inertials from the solids; collision boxes sized like the printed links
        info = arm.mass_props.get("geom", {})
        ua_w = info.get("upper_arm_half_width_m", 0.032)
        tt_in = cad_inertial(mp["turntable"])
        base_in = cad_inertial(mp["base"])
        up_in, fo_in, ha_in = (cad_inertial(mp[n]) for n in ("upper_arm", "forearm", "hand"))
        cup_in = cad_inertial(mp["cup"], None if parallel else CUP_R)
        up_geom = (f'<geom name="upper_arm" type="box" size="{L1 / 2:.6g} {ua_w:.4g} 0.026" pos="{L1 / 2:.6g} 0 0" '
                   f'mass="0"/>')
        fo_geom = f'<geom name="forearm" type="box" size="{L2 / 2:.6g} 0.010 0.015" pos="{L2 / 2:.6g} 0 0" mass="0"/>'
        hb = max(hand_len - CUP_WALL_T - 0.012 - travel, 0.004)   # well behind the soft cup floor (and its travel)
        ha_geom = (f'<geom name="hand" type="box" size="{hb / 2:.6g} 0.025 0.015" pos="{hb / 2:.6g} 0 0" '
                   f'mass="0"/>')
        tt_geoms = (f'<geom name="turntable" type="cylinder" size="0.085 0.003" pos="0 0 0.075" class="visual" '
                    f'rgba="0.8 0.81 0.83 1" mass="0"/>')
        mz = arm.mass_props.get("motor_xz_m", {})
        mots = []
        for nm, y in (("shoulder", -0.072), ("elbow", -0.026), ("wrist", 0.026)):
            if nm in mz:
                mots.append(f'<geom name="motor_{nm}" type="box" size="{s / 2:.4g} 0.02 {s / 2:.4g}" '
                            f'pos="{mz[nm][0]:.4g} {y} {mz[nm][1]:.4g}" class="visual" rgba="0.09 0.09 0.1 1" mass="0"/>')
        motors_xml = "\n        ".join(mots)
        base_geoms = (f'<geom name="base_housing" type="cylinder" size="0.09 0.026" pos="0 0 0.026" class="visual" '
                      f'rgba="0.8 0.81 0.83 1" mass="0"/>')
        tower = ""
    else:
        tt_in = f'<inertial pos="0 0 0.05" mass="{turntable_mass}" diaginertia="0.0004 0.0004 0.0004"/>'
        base_in = ""
        up_in, fo_in, ha_in = rod_inertial(m1, L1), rod_inertial(m2 + pulley_m, L2), rod_inertial(m3 + pulley_m, hand_len)
        cup_in = ""
        up_geom = f'<geom name="upper_arm" type="capsule" fromto="0 0 0 {L1:.6g} 0 0" size="0.014" mass="0"/>'
        fo_geom = f'<geom name="forearm" type="capsule" fromto="0 0 0 {L2:.6g} 0 0" size="0.012" mass="0"/>'
        # the capsule's rounded tip must stay behind the cup floor (it used to poke 10 mm into the cup)
        hb = max(hand_len - CUP_WALL_T - 0.012 - travel, 0.002)
        ha_geom = f'<geom name="hand" type="capsule" fromto="0 0 0 {hb:.6g} 0 0" size="0.01" mass="0"/>'
        tt_geoms = (f'<geom name="turntable" type="cylinder" size="0.072 0.004" pos="0 0 0.051" class="visual" '
                    f'rgba="0.85 0.86 0.88 1" mass="{turntable_mass}"/>')
        base_geoms = (f'<geom name="base_housing" type="cylinder" size="0.08 0.0225" pos="0 0 0.0225" class="visual" '
                      f'rgba="0.85 0.86 0.88 1" mass="0.4"/>\n      <geom name="motor_base" type="box" '
                      f'size="{s / 2:.4g} {s / 2:.4g} 0.02" pos="0.048 0 0.034" class="visual" '
                      f'rgba="0.15 0.15 0.17 1" mass="{NEMA17_MASS_KG}"/>')
        tower = (f'<geom name="tower_l" type="box" size="0.02 0.003 {(h - 0.055) / 2 + 0.01:.4g}" '
                 f'pos="0 0.026 {(h + 0.055) / 2 + 0.01:.4g}" class="visual" rgba="0.85 0.86 0.88 1" mass="0.03"/>\n'
                 f'        <geom name="tower_r" type="box" size="0.02 0.003 {(h - 0.055) / 2 + 0.01:.4g}" '
                 f'pos="0 -0.026 {(h + 0.055) / 2 + 0.01:.4g}" class="visual" rgba="0.85 0.86 0.88 1" mass="0.03"/>')
    xml = f"""<mujoco model="mechy-{arm.name}">
  <!-- Generated by `mechy cad build {arm.name}` from params.yaml. Do not edit by hand. -->
  <compiler angle="radian" autolimits="true"/>
  <option timestep="{timestep}" gravity="0 0 -9.81" integrator="implicitfast"/>
  <size memory="4M"/>
  <visual><global offwidth="1280" offheight="960"/></visual>
  <default>
    <geom contype="2" conaffinity="0" rgba="0.95 0.55 0.15 1" friction="0.8 0.01 0.001"/>
    <default class="visual"><geom contype="0" conaffinity="0" group="1"/></default>
    <default class="cup"><geom rgba="0.2 0.55 0.85 1" solref="0.01 {cup_dr:.4g}" solimp="0.9 0.95 0.001" friction="1.0 0.02 0.002" mass="{arm.cup_mass / (CUP_WALL_SEGMENTS + 1):.6g}"/></default>
  </default>
  <asset>
    <texture name="grid" type="2d" builtin="checker" width="256" height="256" rgb1=".85 .87 .9" rgb2=".75 .78 .82"/>
    <material name="grid" texture="grid" texrepeat="8 8"/>
  </asset>
  <worldbody>
    <light pos="0.5 -1 2" dir="-0.3 0.5 -1" directional="true"/>
    <geom name="floor" type="plane" size="3 3 0.05" material="grid" contype="1" conaffinity="1"/>
    <body name="base_housing" pos="0 0 0">
      {base_in}
      {base_geoms}
      <body name="turntable" pos="0 0 0">
        {joint(0, "0 0 1")}
        {tt_in}
        {tt_geoms}
        {tower}
        {motors_xml}
        <body name="upper_arm" pos="{arm.shoulder_x:.6g} 0 {h:.6g}">
          {joint(1, "0 -1 0")}
          {up_in}
          {up_geom}
          <body name="forearm" pos="{L1:.6g} 0 0">
            {joint(2, "0 -1 0")}
            {fo_in}
            {fo_geom}
            <body name="hand" pos="{L2:.6g} 0 0">
              {joint(3, "0 -1 0")}
              {ha_in}
              {ha_geom}
              <body name="cup" pos="{L3:.6g} 0 {arm.tool_z if parallel else 0:.6g}"
                    {'zaxis="1 0 0"' if not parallel else ""}>
                {slide}
                {cup_in}
                <site name="cup_center" pos="0 0 0" size="0.005"/>
                {cup_xml}
              </body>
            </body>
          </body>
        </body>
      </body>
    </body>
    <body name="ball" pos="0.6 0.6 {ball_diameter / 2:.6g}">
      <freejoint name="ball"/>
      <geom name="ball" type="sphere" size="{ball_diameter / 2:.6g}" mass="{ball_mass:.6g}" rgba="0.8 0.95 0.2 1" contype="1" conaffinity="3" solref="0.01 0.35" solimp="0.9 0.95 0.001" condim="4" friction="1.0 0.02 0.002"/>
    </body>
  </worldbody>
  <actuator>
{chr(10).join(act)}
  </actuator>
  {f'''<tendon>
    <fixed name="level"><joint joint="shoulder" coef="1"/><joint joint="elbow" coef="1"/>
    <joint joint="wrist" coef="1"/></fixed>
  </tendon>
  <equality>
    <!-- parallel linkage: the wrist is passive and q1+q2+q3 = level_pitch keeps the cup level -->
    <tendon tendon1="level" polycoef="{arm.level_pitch:.6g} 0 0 0 0"/>
  </equality>''' if parallel else ""}
</mujoco>
"""
    return xml
