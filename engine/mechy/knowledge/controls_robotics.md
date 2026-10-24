# Controls and Robotics: reference for Mechy agents

Audience: the controls, sim, cad and concept agents designing small robot arms and mechanisms
(3D-printed, belt/gear reduced, stepper or BLDC driven, hobby-to-prosumer budget).
Read the TL;DR first. Every number is labelled **typical** (common practice, several sources agree),
**estimate** (engineering judgement or one source) or **exact** (follows from math). Sources are in brackets
and listed in full under "Canonical references".

---

## 0. TL;DR: the 25 rules that matter most

1. **Close the fastest loop on the hardware closest to the motor.** Current loop on the driver, velocity loop
   next, position loop outermost. Each outer loop's bandwidth should be about **5–10x lower** than the loop
   inside it (typical) [Åström & Murray; ODrive forum].
2. **Sample at 10–20x the closed-loop bandwidth you want** (typical; 5x is the bare minimum, 40x is comfortable)
   [Franklin, Powell & Workman].
3. **Latency eats phase margin.** A pure delay τ costs `360·f·τ` degrees at frequency f. 10 ms of delay at a
   10 Hz crossover costs 36° (exact).
4. **Target phase margin 45–60° and gain margin ≥ 6 dB** (typical) [Åström & Murray; Ogata].
5. **Feedforward does most of the work, feedback cleans up.** Velocity, acceleration, friction and gravity
   feedforward routinely cut tracking error by 5–10x versus PID alone (estimate).
6. **Always add anti-windup** whenever the actuator can saturate (it always can).
7. **Never differentiate a raw encoder signal without filtering.** Use a first-order filter with N ≈ 5–20,
   and put the derivative on the measurement, not the error.
8. **Steppers are open-loop position devices.** Size them at ≤ 50% of the pull-out torque at the working speed
   (typical rule of thumb) or they skip steps silently.
9. **Reflected inertia scales with 1/N².** Keep the load-to-motor inertia ratio ≤ 10:1 for easy tuning
   (typical for servos; ≤ 5:1 for high performance) [Kollmorgen, Yaskawa app notes].
10. **Gravity compensation is the single largest win for an arm.** Model `g(q)` and feed it forward.
11. **Design the kinematics so analytic IK exists:** 6-DOF arms should have a spherical wrist (last three
    axes intersecting), 3–5-DOF arms should have parallel shoulder/elbow axes.
12. **Stay away from singularities** by design: keep the useful workspace out of full stretch, out of the
    region where the wrist centre is on the base axis, and avoid θ5 ≈ 0.
13. **Plan with jerk limits** (S-curve or minimum-jerk) on belt-driven or flexible arms. Trapezoidal
    profiles excite resonances.
14. **Home every incremental axis with two passes**: fast seek, back off, slow seek. Or use absolute encoders.
15. **The firmware loop must run at a fixed rate driven by a hardware timer**, not `delay()` or the OS scheduler.
16. **Never block inside an ISR.** No printf, no malloc, no I²C transactions with timeouts.
17. **Watchdog + safe state.** If the loop misses N deadlines or comms are lost for > 100 ms (estimate),
    disable torque or hold, depending on which state is safe for the axis.
18. **Simulate with realistic inertias and joint damping.** A URDF with default inertia tensors lies.
19. **Validate the sim timestep:** contact-rich sims need ≤ 1–2 ms (typical MuJoCo/PyBullet practice).
20. **For catching, the latency budget is the design.** Measure end-to-end (photon to motor) latency with an
    LED and a high-speed camera; don't add up datasheet numbers and trust them.
21. **Timestamp every sensor sample at capture**, not at processing.
22. **Fit a parabola (or a Kalman filter with gravity)** to ≥ 5–10 observations before committing to an
    intercept, then keep re-planning as new frames arrive.
23. **Stereo depth error grows with Z²**: δZ ≈ Z²·δd/(f·B). Baseline is your friend.
24. **Torque, not position, decides whether an arm can catch.** Check peak acceleration at the end effector
    versus motor torque after reflected inertia.
25. **Put limits in three places:** planner (soft), firmware (hard), mechanical (end stops / slip clutch).

---

## 1. Feedback basics

### 1.1 Vocabulary
| Term | Meaning |
|---|---|
| Plant G(s) | The thing being controlled (motor + drive + load) |
| Controller C(s) | Your algorithm |
| Reference r | Desired value (setpoint) |
| Error e = r − y | What feedback reacts to |
| Open-loop L(s) = C·G | Used to judge stability margins |
| Closed-loop T = L/(1+L) | What the user sees |
| Sensitivity S = 1/(1+L) | How much disturbance survives; want small at low frequency |
| Bandwidth f_bw | Frequency where closed-loop response drops 3 dB; "how fast" the loop is |
| Crossover f_c | Frequency where \|L\| = 1; close to the bandwidth for well-damped loops |

### 1.2 Time-domain rules of thumb (second-order approximation)
- Rise time (10–90%): `t_r ≈ 0.35 / f_bw` (typical, first-order approx) [Ogata].
- Settling time (2%): `t_s ≈ 4 / (ζ·ω_n)` (exact for 2nd order).
- Overshoot: `OS = exp(−πζ/√(1−ζ²))`. ζ = 0.7 → 4.6%, ζ = 0.5 → 16%, ζ = 1 → 0% (exact).
- Phase margin to damping, rough: `ζ ≈ PM / 100` for PM < 70° (typical) [Ogata].

### 1.3 Why feedback, and when it isn't enough
- Feedback rejects disturbances and model error **only below the bandwidth**. Above it, disturbances
  pass straight through (and sensor noise is amplified near crossover).
- Feedback cannot fix: a structural resonance below crossover, backlash larger than the accuracy target,
  a sensor on the wrong side of a compliant belt (non-collocated), or a saturated actuator.
- **Collocated vs non-collocated:** encoder on the motor shaft (collocated) is easy to stabilise; encoder
  on the joint after a belt (non-collocated) gives true joint position but puts the belt resonance inside
  the loop. Common solution: dual-loop: velocity loop on motor encoder, position correction from joint
  encoder at low bandwidth (typical industrial practice).

### 1.4 Typical plants
| Plant | Model | Notes |
|---|---|---|
| DC/BLDC motor, current to velocity | `ω/i = K_t / (J s + b)` | Integrator-like above b/J |
| Motor, voltage to current | `i/V = 1 / (L s + R)` | Electrical time constant L/R ~0.1–2 ms (typical small BLDC) |
| Position from velocity | `1/s` | Pure integrator |
| Heater/thermal | FOPDT `K e^{−θs}/(τs+1)` | Delay dominates tuning |
| Belt-driven load | Two-mass with spring k_belt | Resonance `f = (1/2π)√(k(1/J1+1/J2))` |

---

## 2. PID control

### 2.1 Forms
- **Parallel (independent):** `u = Kp·e + Ki·∫e dt + Kd·de/dt`
- **Standard (ISA):** `u = Kp·(e + (1/Ti)∫e dt + Td·de/dt)` → `Ki = Kp/Ti`, `Kd = Kp·Td`.
- Know which form a library/firmware uses before copying gains. Klipper's heater PID, ODrive and ROS
  `control_toolbox` use different forms and units.

### 2.2 What each term does
| Term | Fixes | Costs |
|---|---|---|
| P | Speeds response | Steady-state error remains with constant disturbance (e.g. gravity); too high → oscillation |
| I | Removes steady-state error | Adds phase lag (−90° at low f), overshoot, windup |
| D | Adds damping (phase lead) | Amplifies noise; useless without filtering |

For a motor position loop where the plant already has an integrator (velocity→position), a PD (or P on a
velocity loop) gives zero steady-state error to step commands, but **not** against a constant load like gravity,
which is why I or gravity feedforward is needed.

### 2.3 Discrete implementation (recommended pattern)
```c
// Runs at fixed Ts from a timer ISR. Derivative on measurement, filtered, clamped anti-windup.
float pid_step(PID *p, float r, float y, float ff) {
    float e = r - y;
    // filtered derivative of measurement (first-order, time constant Tf = Td/N)
    float alpha = p->Tf / (p->Tf + p->Ts);
    p->d = alpha * p->d - (1 - alpha) * p->Kd * (y - p->y_prev) / p->Ts;
    p->y_prev = y;
    float u_unsat = p->Kp * e + p->i + p->d + ff;
    float u = clamp(u_unsat, p->u_min, p->u_max);
    // back-calculation anti-windup (Kt ~ 1/Tt)
    p->i += p->Ki * p->Ts * e + p->Kt * p->Ts * (u - u_unsat);
    return u;
}
```
- Use `Ts` measured from the timer, not assumed, if any jitter is possible.
- Bumpless transfer: when switching from manual/open-loop to PID, initialise `i = u_current − Kp·e − ff`.

### 2.4 Tuning methods: decision table
| Situation | Method | Notes |
|---|---|---|
| Motor velocity/position loop, model known (J, Kt) | **Pole placement / loop shaping** | Pick crossover, compute gains (§2.5) |
| Unknown plant, you can make it oscillate safely | **Ziegler–Nichols ultimate gain** or **relay autotune** | Gives aggressive gains; detune |
| Process with delay (thermal) | **Lambda / IMC / SIMC** from step test | Robust, conservative |
| Hobbyist on a bench | **Manual procedure** (§2.4.3) | Works for 90% of small arms |
| Driver has autotune (ODrive, ClearPath, Klipper PID_CALIBRATE) | Use it, then verify margins | |

#### 2.4.1 Ziegler–Nichols (closed-loop) and gentler variants
Raise Kp with I and D off until sustained oscillation: ultimate gain `Ku`, period `Tu`.
| Rule | Kp | Ti | Td |
|---|---|---|---|
| ZN classic PID | 0.6 Ku | Tu/2 | Tu/8 |
| ZN PI | 0.45 Ku | Tu/1.2 | – |
| Tyreus–Luyben PI (less overshoot) | Ku/3.2 | 2.2 Tu | – |
| "No overshoot" PID | 0.2 Ku | Tu/2 | Tu/3 |
(typical published rules) [Åström & Hägglund; Wikipedia Ziegler–Nichols summary]. ZN gives roughly
25% overshoot / quarter-amplitude decay; it is a starting point, not an answer.

#### 2.4.2 Relay autotune (Åström–Hägglund)
Replace the controller with a relay of amplitude d; the loop oscillates at amplitude a and period Tu.
`Ku ≈ 4d / (π·a)` (describing-function approximation). Then apply a table above. Safer than gain
ramping because amplitude is bounded. Used by Klipper `PID_CALIBRATE` for heaters (typical).

#### 2.4.3 Manual tuning procedure (position/velocity of a joint)
1. Disable I and D. Set feedforward to zero. Limit current to a safe value.
2. Raise Kp until the step response just starts to ring, then halve it.
3. Add D (or raise the velocity-loop gain in a cascade) until ringing is damped; stop when audible noise
   or current jitter appears; back off 30%.
4. Add I slowly until steady-state error disappears within the required time; stop before overshoot grows.
5. Add feedforward (§2.7) and re-check. You can often lower Kp/Ki afterwards.
6. Verify at worst-case inertia (arm extended, full payload) and best case (folded, no payload).
7. Check margins (§4) with a frequency sweep if available.

#### 2.4.4 Lambda/IMC for FOPDT plants
Step-test → gain K, time constant τ, delay θ. Choose closed-loop time constant λ (≥ θ for robustness; λ = τ for
"same speed as open loop"). PI: `Kp = τ / (K·(λ + θ))`, `Ti = τ` (typical IMC/SIMC; Skogestad's SIMC uses
`Ti = min(τ, 4(λ+θ))`) [Skogestad 2003].

### 2.5 Loop-shaping a motor loop from physics (worked mini-example)
Velocity loop on a BLDC: plant `ω/i = Kt/(J s)` (friction ignored).
PI controller `Kp_v (1 + 1/(Ti s))`. Crossover where `Kp_v·Kt/(J·ω_c) = 1` → **`Kp_v = J·ω_c / Kt`**.
Place the PI zero a factor ~4–5 below crossover: `Ti ≈ 4/ω_c` (typical).

Example: J_total (reflected) = 2e-5 kg·m², Kt = 0.05 N·m/A, desired velocity bandwidth 50 Hz →
ω_c = 314 rad/s → Kp_v = 2e-5·314/0.05 = 0.126 A/(rad/s), Ti ≈ 12.7 ms.
Position loop (P only) at 1/5 of that: ω_pos = 63 rad/s → `Kp_p = ω_pos` = 63 (rad/s)/rad.

### 2.6 Anti-windup
Windup: actuator saturates, integrator keeps integrating, huge overshoot when saturation ends.
| Method | How | Use when |
|---|---|---|
| Clamping / conditional integration | Stop integrating when output saturated *and* error sign would push further into saturation | Simplest; good default for MCUs |
| Back-calculation | Feed `(u_sat − u_unsat)` back into the integrator with gain `1/Tt`; `Tt ≈ √(Ti·Td)` or `Tt ≈ Ti` for PI (typical) [Åström & Hägglund] | Smooth, standard in industry |
| Integrator limit | Clamp `i` to ±limit | Crude backstop; combine with one above |
| Reset on large error | Zero `i` when \|e\| exceeds a threshold or during moves | Hobby trick; use only for point-to-point moves |
Also: freeze the integrator while a fault, E-stop or homing is active.

### 2.7 Derivative filtering and setpoint weighting
- Implement D as `Kd·s / (1 + s·Td/N)`; **N = 5–20** typical (N = 10 is a fine default) [Åström & Hägglund].
- **Derivative on measurement** (−dy/dt) avoids the "derivative kick" on setpoint steps.
- **Setpoint weighting:** `P-term = Kp(b·r − y)`, b = 0.5–1: lowers overshoot to steps without changing
  disturbance rejection.
- Velocity from an encoder: use a tracking observer/PLL (ODrive style) or the `M/T` method rather than
  plain differencing. A 4096-count encoder at 1 kHz has a velocity quantum of 2π/4096·1000 ≈ 1.5 rad/s (exact),
  which is huge at low speed.

### 2.8 Feedforward
Total command: `u = u_ff + u_fb`.
| Term | Formula | Typical for |
|---|---|---|
| Velocity FF | `K_v · v_ref` (≈ back-EMF/viscous) | Voltage-mode drives |
| Acceleration FF | `J_eff · a_ref / K_t` (current) | Current-mode drives, the big one for fast moves |
| Static friction (Coulomb) | `K_s · sign(v_ref)` | Gearboxes, belts with preload |
| Gravity | `g(q)/K_t` (§8) | Any non-horizontal joint |
| Full inverse dynamics (computed torque) | `M(q)·a_ref + C·v_ref + g(q)` | Multi-DOF fast arms |
Rule: tune feedforward first with feedback gains low; if tracking error is proportional to acceleration,
your J estimate is off; if it is proportional to velocity, viscous term is off; if it flips sign at reversal,
Coulomb friction is off.

### 2.9 Cascaded loops (servo drive structure)
```
pos_ref ─► [P(+FF)] ─► vel_ref ─► [PI] ─► i_ref ─► [PI current, FOC] ─► PWM ─► motor
              ▲               ▲                ▲
           pos enc        vel est           phase currents
```
| Loop | Update rate (typical) | Achievable bandwidth (typical) | Who runs it |
|---|---|---|---|
| Current (torque) | 8–40 kHz (PWM synchronous) | 0.5–3 kHz | Drive (ODrive, VESC, moteus, TMC) |
| Velocity | 1–10 kHz | 20–300 Hz | Drive |
| Position | 1–10 kHz on drive; 100 Hz–1 kHz if on host | 5–50 Hz | Drive or MCU |
| Trajectory / setpoint stream | 100 Hz–1 kHz | – | Host / planner |
[ODrive forum: all loops at 8 kHz on ODrive 3.x, practical vel/pos ~50 Hz; moteus docs (estimate)]

Tuning order: **inside out**. Tune current first (usually done for you via R and L), then velocity, then position.
Stepper drivers (TMC2209/5160) replace the current loop with chopper control; you only own position
(open-loop) unless you add an encoder (closed-loop stepper: MKS Servo42, BTT S42C, etc.).

---

## 3. Control loop rates

### 3.1 Rule
`f_sample ≥ 10–20 × f_bw` (typical). Below ~5x, the zero-order hold delay (≈ Ts/2) plus compute delay
(≈ Ts) eats > 50° of phase at crossover (estimate from §4.3 formula).

### 3.2 Typical rates by function
| Function | Rate | Notes |
|---|---|---|
| FOC current loop | 10–40 kHz | Synchronous with PWM centre |
| Stepper step generation | up to 100s of kHz step rate | Hardware timers; see §11 |
| Joint servo (vel/pos) | 1–10 kHz | |
| Robot arm joint-space control on PC (ros2_control) | 100 Hz–1 kHz | 1 kHz needs PREEMPT_RT |
| Impedance/force control | ≥ 1 kHz | Stiff contact needs fast loops; 500 Hz minimum (estimate) |
| IMU fusion (complementary/EKF) | 100 Hz–1 kHz | |
| Vision tracking | 30–240 Hz | Camera-limited |
| Path planning / IK on host | 10–100 Hz replan, interpolated to servo rate | |
| Thermal (hotend) | 1–10 Hz | |

### 3.3 Jitter
Jitter of more than ~1–5% of Ts degrades derivative and velocity estimates (estimate). Drive the loop from
a hardware timer interrupt; do comms in lower-priority tasks; measure jitter by toggling a GPIO and scoping it.

---

## 4. Stability margins in plain terms

### 4.1 What they mean
- **Gain margin (GM):** how much you could multiply the loop gain before it oscillates. GM = 6 dB means
  "the gain can double before instability". Payload changes inertia, which changes gain, so GM is your
  inertia-variation budget.
- **Phase margin (PM):** how much extra delay/lag you can tolerate at crossover before it oscillates.
  Low PM = ringing, high overshoot.
- **Delay margin:** `τ_max = PM[rad] / ω_c`. Example: PM = 45° = 0.785 rad, f_c = 20 Hz →
  τ_max = 0.785/(2π·20) = 6.2 ms (exact).

### 4.2 Targets (typical) [Åström & Murray; Ogata]
| Margin | Minimum | Good |
|---|---|---|
| Phase margin | 30° | 45–60° |
| Gain margin | 6 dB (2x) | 10–12 dB |
| Peak sensitivity Ms | < 2.0 | 1.3–1.6 |
Ms = max \|1/(1+L)\| is one number that captures both: Ms ≤ 2 guarantees GM ≥ 6 dB and PM ≥ 29° (exact).

### 4.3 Phase lost to delay and sampling
- Pure delay: `φ = −360°·f·τ` (exact).
- Sampling + ZOH ≈ delay of `Ts/2`; computation ≈ up to `Ts` more. Total ≈ `1.5·Ts` (typical worst case).
- Example: 1 kHz loop, 50 Hz crossover: 1.5 ms → 27° lost. At 200 Hz loop rate: 7.5 ms → 135°: unstable.
- First-order filters add lag too: a filter at f_f costs `atan(f_c/f_f)` at crossover. Keep filters
  ≥ 5–10x above crossover (typical).

### 4.4 Measuring margins on hardware
1. Inject a sine (or chirp) disturbance at the controller output; log u and y.
2. Compute L(jω) from the ratio of FFTs (or use a swept-sine at discrete frequencies).
3. Read crossover, PM and GM from the Bode plot.
Simpler proxy: step response overshoot ≤ 10–15% and ≤ 2 visible oscillations ≈ PM ≥ 45° (estimate).

---

## 5. State estimation basics

### 5.1 Picking an estimator
| Need | Use |
|---|---|
| Tilt from gyro + accelerometer | Complementary filter (or Mahony/Madgwick for 3D) |
| Velocity from encoder | PLL / tracking observer, or α-β filter |
| Position+velocity of a moving target from noisy camera | Linear Kalman filter (constant-velocity or constant-acceleration/ballistic model) |
| Nonlinear model (e.g. drag, camera projection) | EKF or UKF |
| Multi-modal, non-Gaussian | Particle filter (rarely needed for arms) |

### 5.2 Complementary filter
`θ_k = α·(θ_{k−1} + ω_gyro·dt) + (1−α)·θ_accel`
- Crossover time constant `τ = α·dt/(1−α)`. α = 0.98 at dt = 10 ms → τ ≈ 0.49 s (exact).
- Gyro trusted for fast changes (< τ), accelerometer for slow (> τ). Accelerometer tilt is wrong during
  acceleration; increase τ for dynamic platforms.
- Mahony/Madgwick extend the idea to quaternions with a gyro-bias integrator.

### 5.3 Kalman filter (linear), the minimum you need
Model: `x_k = F x_{k−1} + B u + w`, `z_k = H x_k + v`, with `w ~ N(0,Q)`, `v ~ N(0,R)`.
```
Predict:  x = F x + B u;          P = F P Fᵀ + Q
Update:   y = z − H x;            S = H P Hᵀ + R
          K = P Hᵀ S⁻¹;           x = x + K y;      P = (I − K H) P
```
Constant-velocity 1D model, state [p, v]: `F = [[1, dt],[0, 1]]`, `H = [1, 0]`.
Process noise for white-noise acceleration with spectral density q (m²/s³):
`Q = q·[[dt³/3, dt²/2],[dt²/2, dt]]` (exact) [Bar-Shalom].
Ballistic model: state [p, v] per axis, `B u` term adds gravity: `p += v dt + ½ g dt²`, `v += g dt`.

Tuning:
- R from data: variance of the measurement while target is still (e.g. stereo point noise, typically mm-level
  at 1 m for a good rig: estimate).
- Q: start small (trust model); raise until the filter keeps up with real manoeuvres. Too small Q → lag;
  too big Q → noisy.
- Check **innovation** y: should be zero-mean and its variance ≈ S. Use `yᵀS⁻¹y` > chi-square threshold
  (e.g. 9.2 for 2 DOF at 99%) to reject outliers (gating).
- Handle variable dt and out-of-order frames by predicting to the measurement timestamp.

### 5.4 α-β filter (cheap Kalman steady-state)
`p̂ = p_pred + α·r`, `v̂ = v_pred + (β/dt)·r`, r = residual. α ≈ 0.5–0.9, β ≈ α²/(2−α) (Benedict–Bordner
relation, typical). Great on MCUs for encoder velocity.

---

## 6. Robot kinematics

### 6.1 Conventions
- **Joint space** q (angles/displacements) vs **task space** x (position + orientation of tool, "pose").
- **DOF needed:** 3 for position only, 5 for position + pointing direction (axisymmetric tool),
  6 for full pose, 7 for redundancy (null-space for obstacle/singularity avoidance).
- Represent orientation with rotation matrices or unit quaternions inside code; Euler angles only at the UI.

### 6.2 Denavit–Hartenberg parameters
Four parameters per link describe the transform from frame i−1 to frame i.
**Standard (distal) DH**: `T_i = Rot_z(θ_i) · Trans_z(d_i) · Trans_x(a_i) · Rot_x(α_i)`
| Param | Meaning |
|---|---|
| θ_i | Rotation about z_{i−1} (joint variable for revolute) |
| d_i | Offset along z_{i−1} (joint variable for prismatic) |
| a_i | Link length along x_i (common normal) |
| α_i | Twist about x_i between z_{i−1} and z_i |
**Modified (proximal, Craig) DH**: `Rot_x(α_{i−1}) · Trans_x(a_{i−1}) · Rot_z(θ_i) · Trans_z(d_i)`.
Always state which convention you use; mixing them is the #1 DH bug.

Procedure:
1. Put z_i along joint axis i+1 (standard).
2. x_i along the common normal from z_{i−1} to z_i; if axes intersect, x_i ⊥ both; if parallel, choose
   one that zeros d.
3. Read off θ, d, a, α. Add fixed joint-offset to θ so that "zero" matches your mechanical home.

Alternative: **Product of Exponentials (PoE)** with screw axes [Lynch & Park]. No frame-placement rules;
easier to derive from CAD (just axis direction + a point on axis). Recommended for generated code.
URDF uses neither: it gives each joint an arbitrary origin xyz/rpy and an axis, which is easy to get from CAD.

Example: generic 6R arm with spherical wrist (standard DH, illustrative values, mm):
| i | θ | d | a | α |
|---|---|---|---|---|
| 1 | θ1 | d1 = 150 | 0 | +90° |
| 2 | θ2 | 0 | a2 = 250 | 0 |
| 3 | θ3 | 0 | 0 | +90° |
| 4 | θ4 | d4 = 220 | 0 | −90° |
| 5 | θ5 | 0 | 0 | +90° |
| 6 | θ6 | d6 = 60 | 0 | 0 |

### 6.3 Forward kinematics
`T_0n = T_1 · T_2 · … · T_n` (4×4 homogeneous). Always unique and cheap. Check with three tests:
1. All joints zero → tool at the expected CAD position.
2. Rotate each joint +90° alone → tool moves in the expected direction (sign check).
3. Compare to the sim (URDF/MJCF) at random poses; error should be < 1e-9 m.

### 6.4 Inverse kinematics
| Method | Pros | Cons | Use when |
|---|---|---|---|
| Analytical (closed form) | Fast (µs), all solutions, deterministic | Needs special geometry | 3–6 DOF arms designed for it: the default |
| IKFast (OpenRAVE) generated | Analytical, automatic | Toolchain hassle | 6-DOF arms w/o hand derivation |
| Numerical: Jacobian pseudo-inverse / DLS | Any geometry | Local minima, one solution, needs a seed | Redundant arms, odd geometries |
| Optimisation (TRAC-IK, KDL LMA, pink, ikpy) | Constraints, joint limits | Slower, ms | MoveIt, planning |

#### 6.4.1 2-link planar (the building block)
Links L1, L2, target (x, y):
```
c2 = (x² + y² − L1² − L2²) / (2 L1 L2)         # if |c2| > 1: unreachable
θ2 = ± acos(c2)                                  # + = elbow down, − = elbow up (convention dependent)
θ1 = atan2(y, x) − atan2(L2 sin θ2, L1 + L2 cos θ2)
```
(exact). Use `atan2`, never `atan`. Clamp c2 to [−1, 1] after a tolerance check to avoid NaN at full stretch.

#### 6.4.2 3-DOF "anthropomorphic" (base yaw + shoulder + elbow) for position
1. `θ1 = atan2(y, x)` (second solution: θ1 + π with "reaching backwards").
2. `r = √(x² + y²) − a1` (horizontal reach minus any shoulder offset), `s = z − d1`.
3. Solve the 2-link planar problem in (r, s) for θ2, θ3.
Up to 4 solutions (shoulder left/right × elbow up/down). Pick by joint limits then nearest to current q.

#### 6.4.3 4-DOF and 5-DOF desktop arms
- 4-DOF (yaw, shoulder, elbow, wrist pitch) with tool pitch φ specified: subtract the wrist link:
  `r_w = r − L3 cos φ`, `s_w = s − L3 sin φ`, solve 2-link for (r_w, s_w), then `θ4 = φ − θ2 − θ3`.
- 5-DOF adds wrist roll θ5 = desired tool roll − (θ1 contribution); full 6-DOF pose is generally not
  reachable, so the planner must only request 5-DOF-feasible poses.

#### 6.4.4 6-DOF with spherical wrist (Pieper decoupling)
If the last three axes intersect at one point (the wrist centre), position and orientation decouple:
1. Wrist centre `p_w = p_tool − d6 · R_tool · ẑ`.
2. Solve θ1..θ3 so the wrist centre reaches p_w (as §6.4.2, with offsets).
3. `R_36 = R_03(θ1..θ3)ᵀ · R_tool`.
4. Extract θ4, θ5, θ6 as ZYZ (or the wrist's) Euler angles from R_36; two wrist solutions (flip).
Up to 8 solutions in total (typical for PUMA-like arms) [Craig; Siciliano].
Design implication: **put the wrist axes through a common point** or analytic IK is lost.

#### 6.4.5 Numerical IK (damped least squares)
`Δq = Jᵀ (J Jᵀ + λ² I)⁻¹ · e` with e the 6D pose error (position + axis-angle orientation error).
- λ ≈ 0.01–0.1 (in units matching e; typical) [Buss 2004]. Bigger λ = stable near singularities, slower.
- Iterate until \|e\| < 1e-4 m / 1e-3 rad or 100 iterations; clamp step size; respect joint limits by
  clamping or by adding them to the optimisation.
- Seed with current q for continuity; use multiple random seeds to find other branches.

### 6.5 Jacobian
`ẋ = J(q) q̇` with J 6×n (rows: v_x, v_y, v_z, ω_x, ω_y, ω_z).
For revolute joint i with axis z_{i−1} through point o_{i−1}, end-effector at o_n:
`J_v,i = z_{i−1} × (o_n − o_{i−1})`, `J_ω,i = z_{i−1}` (exact, geometric Jacobian).
Prismatic: `J_v,i = z_{i−1}`, `J_ω,i = 0`.

Two uses an agent must remember:
- **Velocity:** joint speeds needed for a tool speed: `q̇ = J⁻¹ ẋ` (or pseudo-inverse).
- **Statics:** joint torques needed to push with wrench F at the tool: **`τ = Jᵀ F`** (exact). Use it to
  size motors for payload and push forces at every pose, not just at full stretch.

Manipulability (Yoshikawa): `w = √det(J Jᵀ)`; w → 0 at singularities. Condition number κ(J) = σ_max/σ_min;
keep κ < ~10–100 in the working region (estimate).

### 6.6 Singularities
At a singularity J loses rank: some tool directions become impossible and joint speeds for nearby motions
blow up (`q̇ ~ ẋ/σ_min`).
| Type (6R spherical wrist arm) | Condition | Symptom | Avoidance |
|---|---|---|---|
| Wrist | θ5 = 0 (axes 4 and 6 aligned) | θ4 and θ6 spin wildly | Keep \|θ5\| > 10–15° (estimate), tilt tool mount |
| Elbow | Arm fully stretched or folded (θ3 at 0 or π in 2-link terms) | Can't move radially | Limit reach to ~90–95% of max (estimate) |
| Shoulder | Wrist centre on the base (J1) axis | θ1 undefined | Keep work area off the base axis |
| Workspace boundary | Edge of reach | Same as elbow | Size links so targets sit mid-workspace |
For planar 2-link arms: `det J = L1 L2 sin θ2` → singular at θ2 = 0, π (exact).

### 6.7 Workspace
- **Reachable:** points the tool can reach in some orientation. **Dexterous:** points reachable in all
  orientations (much smaller).
- 2-link planar annulus: inner radius `|L1 − L2|`, outer `L1 + L2` (exact). Equal links give a solid disc;
  equal links are a good default.
- Joint limits, cable routing and self-collision shrink this; compute by sampling q on a grid and plotting FK.
- Size links so the main task volume sits at 40–80% of maximum reach (estimate): good manipulability, lower
  gravity torques, away from both elbow singularities.

---

## 7. Trajectory generation

### 7.1 Choosing a profile
| Profile | Continuity | Use when |
|---|---|---|
| Step / linear interpolation | position only | Never for real hardware except tiny moves |
| Trapezoidal velocity | C1 (vel), accel jumps | Rigid, direct-drive, steppers at low speed, simple firmware |
| S-curve (7-segment, jerk-limited) | C2 (accel continuous) | Belts, long arms, anything that rings; industrial default |
| Minimum-jerk quintic | C2, smooth by construction | Point-to-point with fixed duration, human-like, catching |
| Cubic polynomial | C1 | Via-points with velocity matching |
| Cubic / quintic splines, B-splines | C2 / C4 | Smooth multi-waypoint paths |
| Time-optimal (TOPP-RA, Ruckig) | respects v/a/j limits | Fast path following, online replanning |

Multi-axis rule: plan the **slowest** axis's profile and scale all others to finish at the same time
(synchronised), so the path is a straight line in joint space. For straight lines in Cartesian space,
interpolate in task space and run IK at each step (check speed limits along the way; they can be exceeded
near singularities).

### 7.2 Trapezoidal profile (exact formulas)
Distance D, limits v_max, a_max:
- Accel time `t_a = v_max/a_max`, accel distance `d_a = v_max²/(2 a_max)`.
- If `D ≥ 2 d_a`: total `T = D/v_max + v_max/a_max`.
- Else triangular: `v_peak = √(D·a_max)`, `T = 2√(D/a_max)`.
Example: joint move D = 1.5 rad, v_max = 3 rad/s, a_max = 10 rad/s² → t_a = 0.3 s,
d_a = 0.45 rad, 2d_a = 0.9 < 1.5 → T = 0.5 + 0.3 = 0.8 s.

### 7.3 S-curve (jerk-limited, 7 segments)
Phases: +jerk, const accel, −jerk, cruise, −jerk, const decel, +jerk. Time to reach a_max: `t_j = a_max/j_max`.
For a rest-to-rest move reaching v_max with a_max reached: `T = D/v_max + v_max/a_max + a_max/j_max` (exact
when all segments exist). Shorter moves drop the cruise and/or const-accel segments: let a library handle
the case analysis (**Ruckig** is the open-source reference, supports online, multi-DOF, time-synchronised).
Typical j_max: 5–20x a_max per second for small arms (estimate).

### 7.4 Minimum-jerk (Flash & Hogan 1985)
Rest-to-rest over duration T, normalised time τ = t/T:
`x(t) = x0 + (xf − x0)·(10τ³ − 15τ⁴ + 6τ⁵)` (exact).
- Peak velocity `1.875·D/T` at τ = 0.5. Peak acceleration `≈ 5.77·D/T²` at τ ≈ 0.21 (exact).
- Compare cubic rest-to-rest `3τ² − 2τ³`: peak velocity `1.5·D/T`, peak accel `6·D/T²`, but jerk is
  discontinuous (infinite at ends).
- General quintic (non-zero boundary v, a): solve the 6×6 linear system for coefficients from
  (x, v, a) at t=0 and t=T. Use this to **re-plan intercepts on the fly** from the current state.
Pick T from limits: `T ≥ max(1.875 D / v_max, √(5.77 D / a_max))`.

### 7.5 Splines through waypoints
- Cubic spline: C2, solve tridiagonal system; "natural" ends (zero accel) or clamped ends (given velocity).
- Avoid high-order single polynomials through many points (Runge oscillation).
- Catmull-Rom: passes through points, only C1, easy.
- B-splines: don't pass through control points but are local and smooth; good for optimisers.
- After building a geometric path, **time-parameterise** it against velocity/acceleration limits (TOPP-RA,
  MoveIt's time-optimal trajectory generation, Ruckig for segments).

### 7.6 Vibration suppression
- **Input shaping**: convolve the command with impulses timed to cancel a known resonance. ZV shaper delays
  by half the damped period; ZVD/EI are more robust to frequency error at the cost of more delay (typical)
  [Singer & Seering 1990]. Klipper ships MZV, EI, 2HUMP_EI, etc., and measures resonance with an
  accelerometer (ADXL345) [Klipper docs].
- Notch filter in the velocity loop at the structural resonance (servo drives).
- Rule: if your arm rings at f_r, keep the S-curve jerk phase ≥ 1/f_r long, or shape for f_r.

---

## 8. Dynamics and gravity compensation

### 8.1 Equation of motion
`τ = M(q)·q̈ + C(q, q̇)·q̇ + g(q) + τ_friction + Jᵀ F_ext`
- M: inertia matrix (configuration dependent: an extended arm has more inertia at the shoulder).
- C: Coriolis/centrifugal; small at hobby speeds, matters for fast catching moves.
- g: gravity torques; dominates for slow, heavy arms.
- Friction: Coulomb `F_c·sign(q̇)` + viscous `b·q̇` (+ Stribeck at low speed).
Compute with RNEA (recursive Newton–Euler) using Pinocchio, KDL, RBDL, MuJoCo `mj_inverse` or Drake.

### 8.2 Gravity torque, by hand
Joint j torque = sum over every link/payload k outboard of joint j of `m_k · g · (horizontal lever arm of COM_k from axis j)`.
Worked example (estimate, horizontal arm, worst case):
- Upper arm 0.30 m, mass 0.50 kg at 0.15 m; forearm+wrist 0.25 m, 0.35 kg COM at 0.42 m from shoulder;
  payload 0.20 kg at 0.55 m.
- Shoulder: 9.81·(0.50·0.15 + 0.35·0.42 + 0.20·0.55) = 9.81·(0.075 + 0.147 + 0.110) = **3.26 N·m**.
- Elbow: 9.81·(0.35·0.12 + 0.20·0.25) = 9.81·0.092 = **0.90 N·m**.
- Add dynamic torque `J·α` and a safety factor 1.5–2 (typical) → motor torque at joint, then divide by
  reduction ratio and efficiency (belts ~0.95–0.98, spur gears ~0.95/stage, cycloidal ~0.8–0.9,
  worm 0.4–0.9: typical) to get motor torque.
Note: NEMA17 holding torque is typically 0.4–0.6 N·m; usable torque at speed is much lower, so a 3.3 N·m
shoulder needs ≥ ~10:1 reduction with margin (estimate).

### 8.3 Reflected inertia and inertia ratio
Through reduction N (motor turns per joint turn): `J_reflected = J_load / N²`, `τ_motor = τ_load / (N·η)`.
- Inertia ratio `J_reflected / J_motor`: ≤ 10:1 easy, ≤ 3–5:1 for high bandwidth, 1:1 is "matched"
  (typical servo vendor guidance). Higher ratios need stiffer couplings and lower gains.
- Optimal ratio for max acceleration of a pure-inertia load: `N_opt = √(J_load / J_motor)` (exact).
- Belt compliance + high inertia ratio = low resonance inside the loop; that is the usual reason a
  3D-printed belt arm can't be tuned stiff.

### 8.4 Gravity compensation methods
| Method | How | Notes |
|---|---|---|
| Model-based feedforward | `τ_ff = g(q)` from URDF masses/COMs | Best; masses from CAD × ~1.1 for screws/wires (estimate) |
| Identified | Hold arm at many poses, record steady-state current, fit `τ = Y(q)·θ` | Linear in inertial parameters; very accurate |
| Lookup table | Current vs angle per joint | Only valid if other joints fixed |
| Integral term | Let I absorb it | Slow, overshoot on reversal: avoid as primary |
| Mechanical: springs/counterweights | Gas spring, extension spring + cam, parallelogram counterweight | Cuts motor size; zero-length spring gives exact balance for one link |
| Non-backdrivable reduction (worm, high-ratio) | Holds itself | Kills compliance, safety and efficiency |
Brakes: if a joint falls when power is removed, decide whether that's acceptable; add a brake or
self-locking stage for heavy shoulders.

### 8.5 Payload and motor sizing check (per joint)
1. Worst static torque from §8.2 at max reach.
2. Peak dynamic torque `M(q)·q̈_max` (take the extended pose).
3. RMS torque over a duty cycle for thermal (`τ_rms ≤ τ_continuous`).
4. Speed: `ω_motor = N·ω_joint` must sit inside the motor torque-speed curve at the needed torque.
5. Static force at the tool: `τ = Jᵀ F` over the workspace.

---

## 9. Compliance and impedance control

### 9.1 Concepts
- **Stiffness control:** behave like a spring `F = K Δx`.
- **Impedance control** (Hogan 1985): make the robot behave like mass–spring–damper:
  `F = K(x_d − x) + D(ẋ_d − ẋ) [+ M(ẍ_d − ẍ)]`. Input: motion, output: force. Needs a torque-controllable,
  backdrivable actuator.
- **Admittance control:** measure force, output motion `M ẍ + D ẋ + K x = F_ext`. Works on stiff,
  position-controlled robots with a force/torque sensor; can go unstable against stiff environments.
- **Hybrid force/position:** force control on some axes (pushing down), position on others (sliding).

| Hardware | Use |
|---|---|
| Quasi-direct-drive BLDC (≤ 10:1 gearing, current-mode drive) | Impedance control via motor current ≈ torque |
| High-ratio gearbox / stepper | Admittance with F/T sensor, or just limit current |
| Series elastic actuator (spring + encoder) | Accurate force from spring deflection, safe |

### 9.2 Joint-space impedance with gravity comp (common implementation)
`τ = K_p (q_d − q) + K_d (q̇_d − q̇) + g(q) [+ M q̈_d + C q̇]`
- Pick stiffness from desired tool stiffness via `K_joint ≈ Jᵀ K_cart J`.
- Damping ratio ~0.7–1: `D = 2ζ√(K·M_eff)` (typical).
- Stability against stiff environments needs a high loop rate (≥ 1 kHz, typical) and low delay; the
  maximum stable virtual stiffness scales roughly with `b / T` (passivity limits; Colgate & Brown) (estimate).

### 9.3 Cheap compliance for hobby arms
- Current/torque limits on each joint (TMC run current, ODrive current_lim).
- Following-error detection: if \|q_ref − q\| > threshold for > t, stop (collision detection).
- Slip clutch or magnetic coupling on the joint output.
- Stepper stall detection (TMC StallGuard) is unreliable at low speed and needs per-machine tuning (typical).
- For catching, passive compliance (foam, net, spring-loaded cup) is far easier than active impedance.

---

## 10. Homing strategies

### 10.1 Options
| Method | Repeatability (typical) | Cost | Notes |
|---|---|---|---|
| Mechanical microswitch | ±0.01–0.05 mm on linear axes (estimate); worse on joints via lever | Very low | Debounce, NC wiring for fail-safe |
| Optical slot / hall sensor | ±0.01–0.1° (estimate) | Low | Hall: sensitive to magnet distance/temp |
| Hall + encoder index pulse | Encoder-count level | Medium | Coarse switch picks the right index |
| Sensorless (StallGuard, hard stop + current) | ±0.1–1 mm (estimate) | Zero | Needs a solid hard stop; tune per axis |
| Absolute magnetic encoder on joint (AS5600 12-bit, AS5047/AS5048 14-bit, MT6701) | 0.1–0.5° absolute accuracy after calibration (estimate) | Low | No homing move; watch magnet alignment, multi-turn ambiguity behind reduction |
| Absolute multi-turn or joint-side encoder | Best | Higher | Industrial default |

AS5600: 12-bit (4096 counts/rev); AS5047P: 14-bit (16384) [ams datasheets]. Resolution ≠ accuracy; mounting
eccentricity gives errors ~0.5–1° unless calibrated (estimate).

### 10.2 Two-pass homing procedure (incremental axes)
1. Move toward the switch at fast speed (e.g. 10–20% of v_max) with **reduced current/torque**.
2. On trigger: stop, back off a fixed distance (e.g. 2–5 mm or 3–5°).
3. Approach again at slow speed (≈ 1/10 of fast).
4. Latch position at trigger (in ISR or hardware capture), set offset so home = configured value.
5. Move to a safe ready pose.
Timeout each phase; if the switch is already pressed at start, back off first.

### 10.3 Arm-specific homing rules
- **Order matters:** home the joint that can cause collisions first (often the wrist folds away), and home
  the shoulder with gravity helping, not fighting (estimate, depends on layout).
- Gravity-loaded joints may drop when motors are enabled: enable with hold torque, then move.
- For joints behind a reduction with an absolute encoder on the *motor*, there is an N-fold ambiguity: put
  the absolute encoder on the joint output, or add a coarse switch.
- Store a homing offset per joint in config; never hardcode in firmware.
- After homing, verify with a known reachable pose (e.g. touch-off) during commissioning.
- Wire switches normally-closed so a broken wire reads "triggered" (fail-safe).

---

## 11. Real-time firmware patterns

### 11.1 Stepper basics an agent must compute
- Steps per rev = `200 (1.8° motor) × microsteps`. 16 µsteps → 3200 steps/rev.
- GT2 belt, 20T pulley = 40 mm/rev → 80 steps/mm at 16 µsteps (exact).
- Step rate = `rpm/60 × steps/rev`. 600 rpm at 16 µsteps = 32 kHz (exact).
- Microstepping improves smoothness, **not** accuracy: real position error per microstep is load dependent
  (incremental torque per microstep falls as `sin(90°/µsteps)`) (typical) [Micromo/Faulhaber, TI app notes].
- Torque drops with speed because winding inductance limits current rise; higher supply voltage (24–48 V)
  helps (typical).
- Resonance band for steppers around 1–3 rev/s (estimate); microstepping and drivers like TMC
  StealthChop/SpreadCycle reduce it.

### 11.2 Firmware choices
| Stack | What it is | Strengths | Limits | Use for |
|---|---|---|---|---|
| **Klipper** | Host (Python, on Pi) plans + MCU executes timed step queues | Very high step rates, input shaping, pressure advance, multi-MCU, config not code | Built around Cartesian/delta/CoreXY kinematics; arm kinematics need custom module; no torque loops | Belt gantries, simple arms with custom kinematics |
| **grblHAL** | G-code interpreter on MCU (STM32, Teensy 4.x, ESP32, RP2040…) | Up to 6+ axes, plugins, HAL for many boards | Cartesian G-code; no arm IK built-in | CNC-like axes, arm with IK done on host and streamed |
| **Marlin** | 3D-printer firmware | Huge community, SCARA support | Monolithic, lower step rates on 8-bit | Printers, SCARA |
| **ROS 2 + ros2_control + MoveIt 2** | Linux middleware, controllers, planning | IK, collision-aware planning, sim integration | Not real-time by default; latency ~ms; complexity | Planning layer above MCU firmware |
| **micro-ROS** | ROS 2 client on MCU over XRCE-DDS via an agent | MCU appears as ROS 2 node; FreeRTOS/Zephyr/NuttX/ESP-IDF | Agent on host required; not a hard-RT link | Sensor/joint nodes talking to ROS 2 |
| **Smart servo drives** (ODrive, moteus, VESC, Dynamixel) | Drive runs current/vel/pos loops | High bandwidth, torque control | Cost, per-drive config | BLDC/QDD arms, impedance control |

Klipper step-rate benchmarks (max, 3 steppers active, from Klipper Features page, measured in benchmark
conditions, not real-print rates): STM32F103 ~818k steps/s, STM32F407 ~2.46M, RP2040 ~2.57M; 16 MHz AVR
~99k (benchmark figures) [Klipper Features]. grblHAL on Teensy 4.1 is commonly reported at ~160 kHz per axis
(community claim, unverified) vs ~30 kHz for classic Grbl on an Arduino Uno [Hackaday/OpenBuilds].

ROS 2 notes:
- ros2_control controller_manager typically runs 100 Hz–1 kHz; 1 kHz reliably needs a PREEMPT_RT kernel,
  CPU isolation and memory locking (typical) [ROS 2 real-time docs].
- Default DDS over Wi-Fi adds variable latency (tens of ms possible: estimate); keep the inner loops on
  the MCU and stream setpoints or trajectories with timestamps.
- MoveIt 2: KDL (numerical) IK by default; swap to IKFast/TRAC-IK/pick_ik for speed or robustness.

micro-ROS notes: default middleware is eProsima Micro XRCE-DDS; the MCU runs the client, a micro-ROS agent
on the host bridges to DDS; supported RTOSes include FreeRTOS, Zephyr, NuttX; ESP32 via ESP-IDF component
[micro.ros.org].

### 11.3 Architecture pattern for an arm controller
```
Host (PC/Pi): UI → task planner → IK + trajectory (Ruckig/MoveIt) → timestamped setpoints @100–500 Hz
   │ USB-CDC / CAN-FD / Ethernet (avoid Wi-Fi in the loop)
MCU: comms task → setpoint ring buffer → interpolator @1–10 kHz (timer ISR)
     → per-joint controller (pos/vel + gravity FF) → drivers (step/dir, SPI, CAN)
     → safety supervisor (limits, following error, watchdog, E-stop input)
```
Patterns:
1. **Fixed-rate timer ISR** for control; comms and logging at lower priority.
2. **Lock-free ring buffer** (single producer/single consumer) between comms and control.
3. **Look-ahead buffer:** keep ≥ 50–200 ms of setpoints buffered so comms jitter doesn't starve the
   interpolator (estimate); on underrun, decelerate to stop, don't jump.
4. **Timestamps:** synchronise host and MCU clocks (Klipper does this; or PTP/simple ping-pong offset
   estimation) so setpoints carry execution times.
5. **State machine:** DISABLED → HOMING → IDLE → RUNNING → FAULT; transitions only via explicit events.
6. **Hard limits in firmware** (joint position, velocity, current), independent of host.
7. **Watchdogs:** hardware watchdog for MCU lockup; comms watchdog (e.g. no setpoint for 100–250 ms →
   controlled stop: estimate).
8. **E-stop** cuts motor power in hardware (relay/driver enable), not only in software.
9. **Floats** are fine on Cortex-M4F/M7 (single-precision FPU); avoid double on M4. Use fixed-point on
   M0/AVR.
10. **No dynamic allocation, no printf, no blocking I/O in the control path.** Log to a buffer, flush in
    the background.
11. **Measure** loop time and jitter (GPIO toggle + logic analyser) and report max, not mean.
12. **CAN/CAN-FD** is the robust choice for multi-joint buses (differential, arbitration, error handling);
    RS-485 for Dynamixel-style servos; SPI for on-board drivers.

---

## 12. Simulation tools

### 12.1 Choosing a simulator
| Tool | Strengths | Weak spots | Use for |
|---|---|---|---|
| **MuJoCo** (Apache-2.0) | Fast, accurate contacts, stable, great for control/RL, analytic derivatives, Python bindings, MJX (JAX)/MJWarp (GPU) | MJCF-first (URDF import is limited) | Arm dynamics, controller testing, catching sims: **default for Mechy** |
| **PyBullet** | Easy Python, URDF native, IK helpers | Maintenance mode, contact quality lower | Quick prototypes, legacy code |
| **Gazebo (Harmonic+, "new Gazebo")** | ROS 2 integration, sensors (cameras, lidar), plugins | Slower, heavier setup | Full-system ROS 2 sims with sensors |
| **Isaac Sim / Isaac Lab** | Photoreal, GPU parallel RL | NVIDIA GPU required, heavy | Vision + RL at scale |
| **Drake** | Rigorous dynamics, optimisation, planning | Learning curve | Trajectory optimisation, verification |
| **Pinocchio** (not a simulator) | Fast kinematics/dynamics library | No contacts | IK, RNEA, gravity comp code |

### 12.2 Timesteps and integrators (typical defaults)
- MuJoCo: default `timestep` 0.002 s (2 ms); `implicitfast` integrator recommended for new models since
  v2.3.3 for stability with damping (MuJoCo changelog) [MuJoCo docs].
- PyBullet: default 1/240 s (typical, per PyBullet quickstart).
- Gazebo: default physics step 1 ms (typical).
- Rule: timestep ≤ 1/10 of the fastest mode you care about (joint servo, contact); controller rate in sim
  should equal hardware rate (decimate physics steps).

### 12.3 URDF vs MJCF
| Aspect | URDF | MJCF |
|---|---|---|
| Format | XML, links + joints tree | XML, nested bodies, actuators, sensors, contacts |
| Closed loops (parallelograms, 4-bars) | Not supported (tree only) | Supported via equality constraints |
| Actuators / transmissions | Minimal (`transmission` tags for ros2_control) | First-class (motor, position, velocity, gear, tendons) |
| Used by | ROS, MoveIt, PyBullet, Gazebo (via SDF) | MuJoCo |
| Convert | `mujoco` can compile URDF (add `<mujoco>` tag); tools: urdf2mjcf | |

### 12.4 Model-building checklist (common mistakes)
1. **Inertias**: export mass, COM and full inertia tensor from CAD per link (with correct material density;
   3D-printed PLA ~1.24 g/cm³ solid, but infill ~20–40% means effective density far lower: compute from the
   slicer's mass estimate) (typical). Never leave `ixx=1`.
2. Inertia tensor must be physically valid (positive definite, triangle inequality on principal moments).
3. Frame conventions: URDF joint origin is in the parent link frame; mesh origins often don't match link frames.
4. Units: URDF/MJCF use metres, kg, radians. CAD STLs are often in mm: scale 0.001.
5. Use simple collision geometry (capsules/boxes/convex hulls), detailed meshes only for visuals.
6. Add joint damping, armature (reflected rotor inertia `J_rotor·N²`; MuJoCo `armature`) and friction loss;
   otherwise the sim is far more agile than the hardware.
7. Actuator limits: torque (`forcerange`/`ctrlrange`), velocity, and gear ratio matching the real drive.
8. Model the control loop rate and sensor latency (delay buffer) when testing catching/fast control.
9. Compare sim and hardware on a simple step test (sys-ID) before trusting the sim for tuning.

### 12.5 Replay and validation
Log hardware q, q̇, τ, timestamps; replay commands in sim; compare tracking error. Discrepancy > 2x points to
wrong inertia, friction or missing compliance (estimate).

---

## 13. Interception and catching

### 13.1 Problem decomposition
```
Camera(s) → detection (2D) → triangulation (3D) → filter/predict (ballistic KF)
         → intercept point + time selection → IK feasibility → trajectory (quintic, re-planned) → arm
```
Everything is in a race against flight time. A tossed ball (≈ 3 m, ~0.8–1 s flight) gives a few hundred ms
for perception, decision and motion combined.

### 13.2 Ballistic prediction
No drag (good for dense balls, short flights): `p(t) = p0 + v0·t + ½·g·t²`, g = (0, 0, −9.81) m/s².
- Fit with linear least squares on the last N observations (x, y linear in t; z quadratic with known g, or
  fit g too as a sanity check: fitted g far from 9.81 means calibration/timestamp error).
- Or a Kalman filter with the ballistic model (§5.3) for continuous updates and uncertainty.

With quadratic drag: `m·dv/dt = m·g − ½·ρ·C_d·A·|v|·v`, ρ ≈ 1.2 kg/m³, C_d ≈ 0.47 for a sphere (subcritical Re,
typical) [NASA Glenn drag notes]. Integrate numerically (RK4, 1 ms). Drag matters when `½ρC_dA v²` is a
noticeable fraction of mg: e.g. a ping-pong ball (2.7 g, 40 mm) at 5 m/s has drag ≈ 0.5·1.2·0.47·1.26e-3·25 ≈
8.9 mN vs weight 26 mN: **33%, must model** (exact from values). A tennis ball (58 g, 67 mm) at 5 m/s:
≈ 25 mN vs 0.57 N: 4%, often ignorable for short throws. Spin (Magnus effect) adds error for light balls.

Prediction error growth: with velocity error δv and prediction horizon t_h, position error ≈ `δv·t_h`.
Velocity error from N position samples spaced Δt with noise σ: roughly `σ_v ≈ σ·√12 / (Δt·N^{1.5})` for a
linear fit (exact for LS slope with uniform spacing, approximate). More frames over a longer window beat a
faster camera with few frames.

### 13.3 Choosing the intercept point
1. Sample the predicted trajectory p(t) for t in [now + t_min, t_land].
2. Keep points inside the arm's reachable workspace (and away from singularities, §6.6).
3. For each candidate, compute required motion time T_move (from current q, with v/a/j limits) and require
   `T_move + t_latency + margin ≤ t_arrival − now`.
4. Choose the earliest feasible or the one with the largest time margin / lowest predicted uncertainty
   (prefer the plane where the trajectory is closest to the arm's sweet spot).
5. Re-plan every frame with a quintic from the current (q, q̇, q̈) to the updated intercept; smooth the
   target (hysteresis) to avoid chattering.
6. Align the catcher's opening with the incoming velocity vector (cup/net normal ∥ −v) at arrival.
7. Optionally match velocity briefly ("soft catch") to reduce bounce out.

### 13.4 Latency budget (worked example, estimate)
| Stage | Typical | Notes |
|---|---|---|
| Exposure (mid-exposure timestamp) | 1–4 ms | Short exposure to avoid motion blur; needs light |
| Sensor readout (rolling shutter) | 5–15 ms | Global shutter preferred for fast objects |
| USB/MIPI transfer + driver buffering | 5–30 ms | Webcams often buffer frames: set buffer size 1 |
| Detection + triangulation | 2–10 ms | HSV threshold/blob on ROI at 640×480 is ~1–3 ms on a modern CPU |
| Filtering + intercept planning | 1–5 ms | |
| Host → MCU comms | 1–5 ms (USB/CAN) | Wi-Fi: 5–50 ms with jitter |
| Controller + drive response | 10–50 ms | Set by servo bandwidth: ~1/(2π f_bw)·3 to settle |
| **Total photon-to-motion** | **~40–120 ms** | Measure it |
DLR's ball-catching system reported total perception-to-action latency on the order of tens of ms with a
fast arm (estimate; see Bäuml et al. 2010 in references). Measure your own: blink an LED in view and log
when the system detects it vs the LED trigger time; for motion, film motor and LED with a 240 fps phone.

Compensation: predict the target forward by the measured latency; command the arm with timestamps; account
for the servo's following lag with velocity feedforward.

### 13.5 Arm requirements for catching (rule-of-thumb sizing)
- Tool must cover a lateral error ε (prediction + calibration) within the remaining time t_r. With a
  minimum-jerk move: `a_peak ≈ 5.77·ε / t_r²`. Example: ε = 0.15 m, t_r = 0.3 s → a_peak ≈ 9.6 m/s²
  (~1 g) and v_peak = 1.875·0.15/0.3 ≈ 0.94 m/s (exact from formulas).
- Convert to joint torques via `M(q)` at the catch pose plus gravity; check motor torque at the needed speed.
- A larger catcher (net/cup diameter) trades directly against arm speed: every cm of opening radius is a cm
  of allowed error.
- Belt arms: account for wind-up/ringing; plan with jerk limits and give the catch a settled window.

### 13.6 Vision pipeline (practical defaults)
1. **Camera:** global shutter, 90–240 fps, fixed exposure/gain/white balance (disable auto), hardware trigger
   for stereo sync. Typical choices: OV9281 (global shutter, mono), Intel RealSense D4xx (stereo depth, ~90
   fps max at reduced resolution), OAK-D (on-board inference). (typical)
2. **Calibration:** intrinsics (checkerboard/ChArUco, OpenCV, reprojection error < 0.3–0.5 px typical);
   stereo extrinsics; **hand–eye/camera-to-robot** calibration (`cv::calibrateHandEye` or touch the tool to
   markers); verify by commanding the arm to a point the camera sees.
3. **Detection:** coloured ball + HSV threshold + morphology + contour/blob centroid inside a region of
   interest that follows the predicted position (fast, robust); background subtraction for unknown colours;
   a small CNN (YOLO-nano class) only if lighting/background is uncontrolled.
4. **3D:** stereo triangulation (`cv::triangulatePoints`) or depth camera lookup at centroid; or monocular
   with known ball diameter: `Z ≈ f·D_ball / d_pixels`.
5. **Depth error:** `δZ ≈ Z²·δd / (f·B)`. Example: f = 600 px, B = 0.1 m, Z = 2 m, δd = 0.25 px →
   δZ ≈ 4·0.25/60 ≈ 17 mm (exact from values). Doubling baseline halves the error.
6. **Timestamp** each frame at exposure; use the camera's hardware timestamp if available.
7. **Gating/outliers:** Mahalanobis gate in the KF; reject detections outside the predicted region.
8. **Initiation:** start a track after M of N detections (e.g. 3 of 4) consistent with a ballistic model.

### 13.7 Common catching mistakes
- Using processing-time timestamps (adds variable bias directly to velocity estimates).
- Auto-exposure on (blur + variable latency).
- Trusting the first 2–3 frames for intercept: commit only when predicted-landing covariance is small, but
  start moving early toward the coarse estimate.
- Ignoring drag for light balls.
- Planning a single trajectory and not re-planning.
- Arm too slow for the required acceleration (check §13.5 before building).

---

## 14. Robot-arm design checklist (controls view)

### 14.1 Requirements
- [ ] Payload mass and COM offset, reach, DOF (3/4/5/6), repeatability and accuracy targets.
- [ ] Max tool speed and acceleration; cycle time or catch-time requirement.
- [ ] Workspace volume and required orientations (dexterous vs reachable).
- [ ] Contact with people/environment? (→ compliance, current limits, low inertia).

### 14.2 Kinematics
- [ ] Geometry allows analytic IK (spherical wrist for 6-DOF, parallel shoulder/elbow axes).
- [ ] Link lengths put the task volume at ~40–80% reach, away from singularities.
- [ ] Joint ranges cover the task with margin; cables can handle the full range (no continuous rotation
      without slip ring).
- [ ] DH or PoE table written, convention stated, zero pose matches mechanical home.
- [ ] FK verified against CAD/sim at ≥ 3 poses.
- [ ] Workspace plot generated from FK sampling incl. joint limits and self-collision.

### 14.3 Actuation and dynamics
- [ ] Static gravity torque per joint at worst pose, + dynamic torque, × safety factor 1.5–2.
- [ ] Motor torque-speed curve checked at required joint speed × reduction.
- [ ] Reflected inertia ratio ≤ 10:1 (≤ 5:1 for high-performance loops).
- [ ] Reduction efficiency and backdrivability chosen deliberately (QDD for compliance, high-ratio for holding).
- [ ] Belt/drive stiffness gives first resonance well above the target position bandwidth (≥ 3–5x, estimate).
- [ ] Gravity compensation plan (model FF and/or springs/counterweight); behaviour on power loss decided
      (brake / self-locking / safe fall).
- [ ] Thermal: RMS torque ≤ continuous rating for the duty cycle.

### 14.4 Sensing
- [ ] Encoder type/location per joint (motor vs joint side) and resolution vs accuracy target
      (joint resolution ≥ 4–10x finer than required accuracy, estimate).
- [ ] Homing method per joint, order, and fail-safe wiring.
- [ ] Current sensing (if torque control), IMU/F-T if needed, camera spec if vision.

### 14.5 Control
- [ ] Loop architecture (current/velocity/position) and where each runs.
- [ ] Loop rates ≥ 10–20x bandwidths; jitter measured.
- [ ] Feedforward terms: gravity, acceleration, friction.
- [ ] Anti-windup, derivative filtering, output limits implemented.
- [ ] Margins: PM ≥ 45°, GM ≥ 6 dB at worst-case inertia; latency included.
- [ ] Trajectory generator respects v/a/j limits per joint; synchronised multi-axis moves.
- [ ] Input shaping or notch if belts ring.

### 14.6 Firmware and safety
- [ ] Fixed-rate timer ISR; no blocking in control path.
- [ ] State machine with FAULT state; E-stop cuts power in hardware.
- [ ] Soft limits (planner) + hard limits (firmware) + mechanical stops.
- [ ] Following-error and over-current detection → controlled stop.
- [ ] Comms watchdog and setpoint buffer underrun behaviour.
- [ ] Config (offsets, gains, limits) in a file, not hardcoded; versioned.

### 14.7 Simulation and validation
- [ ] URDF/MJCF with CAD-derived masses/inertias, armature, damping, friction, actuator limits.
- [ ] Sim runs the same controller code/rate with modelled latency.
- [ ] Step/sweep tests on hardware; sim-to-real comparison logged.
- [ ] Repeatability test (e.g. return to a point 30x, measure with dial indicator or camera).
- [ ] For catching: measured end-to-end latency, prediction error vs time-to-arrival plot, success rate over
      ≥ 50 throws.

---

## 15. Common mistakes (quick list)
1. Copying PID gains between different PID forms/units.
2. Tuning at one pose/payload only; arm goes unstable when extended.
3. Integral term used as gravity compensation.
4. Derivative on noisy encoder differencing; motor screams.
5. Position loop on a host over USB/Wi-Fi at 50–100 Hz, with no velocity loop on the drive.
6. Steppers sized by holding torque instead of torque at speed; silent missed steps.
7. DH convention mix-up (standard vs modified); joint zero offsets forgotten.
8. Using `atan` instead of `atan2`; not clamping acos argument.
9. Planning straight Cartesian lines through singularities.
10. Trapezoidal profiles on belt arms; ringing blamed on tuning.
11. URDF with placeholder inertias; sim says it works.
12. Wi-Fi in a real-time loop.
13. No watchdog; arm keeps moving when the host crashes.
14. Timestamps taken after image processing.
15. No mechanical overtravel protection.

---

## Canonical references

Free (online):
- K. Lynch & F. Park, *Modern Robotics: Mechanics, Planning, and Control* (2017), free PDF + Coursera course +
  videos: https://hades.mech.northwestern.edu/index.php/Modern_Robotics (free) — PoE kinematics, Jacobians,
  dynamics, trajectory generation.
- K. J. Åström & R. M. Murray, *Feedback Systems* (2nd ed.), free PDF:
  https://fbswiki.org/ (free) — feedback, margins, PID, sensitivity.
- MIT OCW 6.302 Feedback Systems; 2.14 Analysis and Design of Feedback Control Systems; 2.12 Introduction to
  Robotics: https://ocw.mit.edu (free).
- Brian Douglas, Control Systems Lectures and MATLAB Tech Talks (PID, Kalman filter):
  https://www.youtube.com/@BrianBDouglas (free).
- S. R. Buss, "Introduction to Inverse Kinematics with Jacobian Transpose, Pseudoinverse and Damped Least
  Squares methods" (2004): https://www.math.ucsd.edu/~sbuss/ResearchWeb/ikmethods/iksurvey.pdf (free).
- R. Labbe, *Kalman and Bayesian Filters in Python* (Jupyter book):
  https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python (free).
- Klipper docs (kinematics, input shaping, benchmarks, Features step-rate table):
  https://www.klipper3d.org/ (free).
- grblHAL: https://github.com/grblHAL (free).
- ROS 2 docs (ros2_control, real-time): https://docs.ros.org/ ; https://control.ros.org/ ;
  MoveIt 2: https://moveit.picknik.ai/ (free).
- micro-ROS: https://micro.ros.org/docs/overview/features/ (free).
- MuJoCo docs and changelog: https://mujoco.readthedocs.io/ (free). PyBullet quickstart guide:
  https://pybullet.org (free). Gazebo: https://gazebosim.org/docs (free).
- Ruckig (jerk-limited online trajectories): https://github.com/pantor/ruckig (free; paper Berscheid &
  Kröger, RSS 2021).
- TOPP-RA: https://github.com/hungpham2511/toppra (free).
- Pinocchio: https://github.com/stack-of-tasks/pinocchio (free).
- ODrive docs (control structure, tuning): https://docs.odriverobotics.com/ ; ODrive forum discussions of
  loop rates: https://discourse.odriverobotics.com/t/current-control-bandwidth/3360 (free).
- moteus docs (QDD control): https://github.com/mjbots/moteus (free).
- OpenCV calibration and hand-eye tutorials: https://docs.opencv.org/ (free).
- NASA Glenn, "Drag of a Sphere": https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/drag-of-a-sphere/ (free).
- ams OSRAM AS5600 / AS5047P datasheets: https://ams-osram.com (free).
- Trinamic (ADI) TMC2209/TMC5160 datasheets, StallGuard app notes: https://www.analog.com (free).

Books (paid):
- J. J. Craig, *Introduction to Robotics: Mechanics and Control* (4th ed.) — modified DH, analytic IK.
- B. Siciliano, L. Sciavicco, L. Villani, G. Oriolo, *Robotics: Modelling, Planning and Control* — DH,
  dynamics, impedance/force control.
- M. Spong, S. Hutchinson, M. Vidyasagar, *Robot Modeling and Control* — standard DH, Jacobians.
- K. J. Åström & T. Hägglund, *Advanced PID Control* (ISA, 2006) — anti-windup, derivative filtering, tuning.
- G. Franklin, J. D. Powell, M. Workman, *Digital Control of Dynamic Systems* — sample-rate rules.
- K. Ogata, *Modern Control Engineering* — time-domain specs, margins.
- Y. Bar-Shalom, X. R. Li, T. Kirubarajan, *Estimation with Applications to Tracking and Navigation* —
  Kalman tracking models.
- G. Ellis, *Control System Design Guide* — practical servo tuning, feedforward, resonance.

Papers:
- T. Flash & N. Hogan, "The coordination of arm movements" (J. Neuroscience, 1985) — minimum jerk.
- N. Hogan, "Impedance Control: An Approach to Manipulation" (ASME JDSMC, 1985).
- N. Singer & W. Seering, "Preshaping command inputs to reduce system vibration" (1990) — input shaping.
- S. Skogestad, "Simple analytic rules for model reduction and PID controller tuning" (J. Process Control, 2003).
- B. Bäuml, T. Wimböck, G. Hirzinger, "Kinematically optimal catching a flying ball with a hand-arm-system"
  (IROS 2010) — DLR catching, latency and planning.
- J. E. Colgate & J. M. Brown, "Factors affecting the Z-width of a haptic display" (ICRA 1994) — stiffness vs
  sample rate and damping.
- D. L. Pieper (1968) — closed-form IK for arms with three intersecting axes.

---

## Gaps / not verified
- **Loop bandwidth numbers** for drives (current 0.5–3 kHz, velocity 20–300 Hz, position 5–50 Hz) are typical
  ranges from vendor forums and practice, not a single datasheet; ODrive figures come from forum posts
  (8 kHz loop rate on 3.x; a 24 kHz update for ODrive Micro was mentioned but not confirmed shipped).
- **grblHAL step rates** (~160 kHz on Teensy 4.1) are community claims; check the specific driver's docs.
  Klipper figures are benchmark maxima, not real-world rates.
- **MuJoCo default timestep 0.002 s**: from memory of the MJCF reference; the search did not confirm it
  directly. Whether `implicitfast` has become the default integrator in the current version is not verified.
- **PyBullet 1/240 s and Gazebo 1 ms defaults**: from memory/common usage, not re-checked this session.
- **Catching latency numbers** (§13.4) are engineering estimates; the DLR paper's exact latency figures were
  not re-read. Measure on the actual system.
- **Singularity avoidance thresholds** (\|θ5\| > 10–15°, 90–95% reach) and condition-number limits are
  judgement calls, not standards.
- **Encoder accuracy after mounting** (~0.5–1° uncalibrated for on-axis magnetic encoders) is an estimate;
  datasheets quote INL under ideal alignment.
- **Stepper resonance band, microstep accuracy** statements are qualitative; driver-specific.
- Inertia-ratio guidance (≤ 10:1) is vendor rule-of-thumb (Kollmorgen/Yaskawa style) and varies with
  coupling stiffness; not checked against a specific current app note this session.
- Not covered in depth: model predictive control, adaptive/learning control, visual servoing (IBVS/PBVS),
  parallel/delta robot kinematics, collision-checking algorithms, functional-safety standards
  (ISO 10218, ISO/TS 15066, IEC 61508) beyond the basic safety patterns above.
