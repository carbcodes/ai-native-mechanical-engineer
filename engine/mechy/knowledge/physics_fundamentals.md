# Physics fundamentals for mechanism design

Reference for Mechy agents (planner, concept, cad, sim, controls). Read before sizing any joint,
motor, gripper, catcher or structure. Everything here is SI unless stated. Numbers are labelled:

- **[std]**: textbook result, closed form, exact by definition (unit conversions, formulas).
- **[typ]**: typical value from a cited reference; real parts vary, check the datasheet.
- **[est]**: estimate / rule of thumb; use for first sizing only, verify before committing.

Section map:

1. Units and dimensional analysis
2. Statics (FBDs, equilibrium, moments, friction, wedges, screws, capstan, grip)
3. Kinematics (linear, rotational, projectiles, catching and throwing)
4. Dynamics (Newton, inertia tables, parallel axis, reflected inertia, energy, power, momentum, impact)
5. Vibration (natural frequency, damping, resonance, avoidance)
6. Fluids (pressure, drag, buoyancy, pneumatics, vacuum)
7. Heat transfer (conduction, convection, motor and electronics heating)
8. Order-of-magnitude sanity numbers
9. Common physics mistakes in mechanism design
10. Worked mini-examples
11. Canonical references
12. Gaps / not verified

---

## 1. Units and dimensional analysis

### 1.1 Working rules

1. **Compute in base SI internally**: m, kg, s, N, N·m, rad, rad/s, W, Pa, K. Convert at the
   input boundary (datasheet values) and the output boundary (user-facing text) only.
2. **Carry units on every variable name** in code: `torque_Nm`, `len_mm`, `J_kgm2`, `omega_rads`.
   A variable with no unit suffix is a bug waiting to happen.
3. **Dimension-check every new formula** before trusting it. Write both sides in base units
   (M, L, T). If they do not match, the formula is wrong; no exceptions.
4. **Angles are radians in every physics formula** (ω = θ/t, v = ωr, arc = rθ, E = ½Jω²).
   Degrees only in UI and CAD input.
5. **Sanity-check magnitude** after every calculation against Section 8. A NEMA 17 arm that
   "needs" 40 N·m or "can lift" 50 kg is a unit error, not a discovery.

### 1.2 Conversion table [std]

| Quantity | From | To SI | Factor |
|---|---|---|---|
| Length | inch | m | × 0.0254 (exact) |
| Length | mm | m | × 1e-3 |
| Mass | lb (lbm) | kg | × 0.45359 |
| Mass | g | kg | × 1e-3 |
| Force | lbf | N | × 4.4482 |
| Force | kgf ("kg" on scales/specs) | N | × 9.80665 |
| Force | gf | N | × 0.0098 |
| Torque | kgf·cm (hobby servo spec) | N·m | × 0.0981 |
| Torque | oz·in (stepper spec, US) | N·m | × 0.007062 |
| Torque | lbf·in | N·m | × 0.11298 |
| Torque | lbf·ft | N·m | × 1.3558 |
| Torque | N·cm | N·m | × 0.01 |
| Mass inertia | g·cm² (motor rotor spec) | kg·m² | × 1e-7 |
| Mass inertia | kg·cm² | kg·m² | × 1e-4 |
| Mass inertia | kg·mm² (CAD default) | kg·m² | × 1e-6 |
| Mass inertia | oz·in² | kg·m² | × 1.829e-5 |
| Mass inertia | lb·in² | kg·m² | × 2.926e-4 |
| Angular speed | rpm | rad/s | × 2π/60 = 0.10472 |
| Angular speed | rev/s | rad/s | × 2π |
| Angle | deg | rad | × π/180 = 0.017453 |
| Pressure | bar | Pa | × 1e5 |
| Pressure | psi | Pa | × 6894.76 |
| Pressure | MPa | N/mm² | 1 : 1 (handy for stress) |
| Pressure | atm | Pa | × 101 325 |
| Power | hp (mech) | W | × 745.7 |
| Energy | Wh | J | × 3600 |
| Density | g/cm³ | kg/m³ | × 1000 |
| Stiffness | N/mm | N/m | × 1000 |
| Temperature diff | °C difference | K difference | 1 : 1 |
| Frequency | Hz | rad/s | × 2π |

### 1.3 Unit traps that recur

| Trap | What goes wrong | Fix |
|---|---|---|
| "kg" torque on hobby servos (e.g. "20 kg servo") | Means 20 kgf·cm = 1.96 N·m, not 20 N·m or 20 kg·m | Multiply kgf·cm by 0.0981 |
| Mass vs weight | Using m (kg) where m·g (N) belongs; off by ~10× | Force = m·g; write the g explicitly |
| Mass moment of inertia vs area moment of inertia | Both called "moment of inertia". Mass J is kg·m² (dynamics); area I is m⁴ (beam bending) | Name them `J_kgm2` and `I_m4` |
| CAD inertia in kg·mm² or g·mm² | 1e6 or 1e9 error in acceleration torque | Check the units field of the CAD mass-properties report |
| rpm into P = Tω | Power off by 9.55× | Convert to rad/s first |
| Degrees into sin/cos/ω | Wrong numbers that look plausible | Radians internally |
| Hz vs rad/s | Natural frequency off by 2π (6.28×) | ω_n = √(k/m) is rad/s; f_n = ω_n/2π is Hz |
| mm in E·I/L³ | E in GPa, I in mm⁴, L in mm gives N/mm if done consistently, garbage if mixed | Stay in N, mm, MPa together, or in N, m, Pa together, never mixed |
| Gear ratio direction | "3:1" sometimes means output/input speed, sometimes reverse | Define N = ω_motor/ω_load (>1 means reduction) and state it |
| Stepper "holding torque" | Torque at zero speed, rated current, both phases energised. Usable torque at speed is often 30–60% of it [est] | Use the pull-out torque curve at the actual speed and supply voltage |
| Peak vs RMS current | Driver current settings are often RMS; datasheet current may be per-phase peak or RMS | Check which; RMS = peak/√2 for sine microstepping |
| Belt "pitch" vs pulley "diameter" | Effective radius is the pitch radius, r = z·p/(2π), not the OD | GT2 20T: r = 20·2/(2π) = 6.37 mm |
| Lead vs pitch on screws | Lead = travel per rev = pitch × number of starts. T8 "8 mm lead" is 4-start 2 mm pitch | Use lead in T = F·l/(2πη) |
| Percent vs fraction efficiency | η = 90 used as 90 instead of 0.9 | Store as fraction |
| g = 9.81 vs g = 10 | 2% error; fine for sizing, not for verification tables | Use 9.81 in code |

### 1.4 Dimensional analysis in practice

- Base dimensions: mass M, length L, time T, temperature Θ, current I.
- Force N = M·L·T⁻², energy J = M·L²·T⁻², power W = M·L²·T⁻³, torque N·m = M·L²·T⁻² (same
  dimensions as energy, but a different quantity; never add torque to energy).
- Pressure Pa = M·L⁻¹·T⁻², stiffness N/m = M·T⁻², rotational stiffness N·m/rad = M·L²·T⁻².
- Use it to **derive scaling**: a geometrically scaled arm (all lengths × s, same material) has mass ×s³,
  inertia ×s⁵, gravity torque ×s⁴, bending stress from self-weight ×s. Doubling arm size needs
  ~16× the holding torque. This is why small arms feel easy and large ones do not.
- Buckingham π: if an answer depends on n variables with k base dimensions, it depends on n−k
  dimensionless groups (e.g. Reynolds number Re = ρvL/μ for drag).

---

## 2. Statics

### 2.1 Free-body diagram procedure (do this every time)

1. **Isolate** one body (a link, a carriage, the whole arm). Draw only that body.
2. **Replace every contact** with the force(s)/moment(s) it can carry:

| Support/contact | Unknowns it introduces (2D) |
|---|---|
| Smooth surface / roller | 1 force normal to the surface |
| Rough surface | normal N + friction F (F ≤ μs·N if not sliding) |
| Pin / revolute joint (bearing) | 2 forces (Fx, Fy), no moment |
| Fixed / clamped / bolted rigid joint | 2 forces + 1 moment |
| Cable / belt span | 1 tension along the cable, pulling only (T ≥ 0) |
| Two-force member (pinned at both ends, no load between) | 1 force along the line joining the pins |
| Driven joint (motor holding) | pin reactions + 1 motor torque |
| Spring | F = k·x along the spring axis |

3. **Add body loads**: weight m·g at the centre of mass, inertial loads (−m·a, −J·α) if using
   d'Alembert for dynamics.
4. **Choose axes and a moment point.** Take moments about a point where the most unknowns act
   (often a pin) to eliminate them.
5. **Count**: 2D gives 3 equations per body (ΣFx, ΣFy, ΣM); 3D gives 6. More unknowns than
   equations means statically indeterminate (needs stiffness); fewer means a mechanism (it moves).
6. **Solve, then check signs**: a negative cable tension means the cable goes slack; a negative
   normal force means the contact lifts off; both change the model.

### 2.2 Equilibrium and moments [std]

- ΣF = 0 and ΣM_P = 0 about any point P.
- Moment of a force: M = r × F; magnitude M = F·d where d is the perpendicular distance from the
  point to the line of action (moment arm). Only the perpendicular component counts.
- A couple (two equal, opposite, offset forces) produces pure moment F·d, the same about any point.
- Moving a force to another point: add a couple equal to the moment it had about the new point.
- **Gravity torque on an arm joint**: τ = g · Σ mᵢ · xᵢ where xᵢ is the *horizontal* distance from
  the joint axis to each mass's centre of mass. Worst case is usually arm fully horizontal and
  extended. Include motors, belts, pulleys, bearings, fasteners and the payload, not only links.

### 2.3 Tipping and base stability

- A free-standing machine does not tip while the combined centre of mass (including the dynamic
  effect of acceleration) stays inside the support polygon.
- Tipping check about an edge: restoring moment = m_base·g·d_base must exceed
  overturning moment = Σ(payload and arm weights × their horizontal reach beyond the edge) +
  reaction moment from arm acceleration (= J_arm·α about the base axis, plus m·a·h of moving masses).
- Rule of thumb [est]: desktop arms need base mass ≥ 1–2× (arm + payload) mass, or clamping,
  or screws into the table. Fast throwing/catching motions demand clamping.

### 2.4 Friction

**Coulomb model** [std]: static friction F ≤ μs·N (it is whatever is needed, up to the limit);
kinetic friction F = μk·N, opposing relative sliding velocity. Independent of contact area and
(roughly) of speed. Friction angle φ = atan(μ); a block on a slope slips when slope angle > φ.

Real behaviour: μs > μk usually, causing **stick-slip** (jerky motion at low speed) when the
drive is compliant. Lubrication, PTFE, or rolling elements reduce it.

**Coefficient table** [typ]. Sources: Engineering Toolbox friction table (metals, rubber, wood,
glass, PTFE, nylon, leather); plastics values marked [est] are widely quoted ranges from
polymer supplier guides and depend heavily on load, speed, finish and humidity.

| Pair | μs (static) | μk (kinetic) | Note |
|---|---|---|---|
| Steel on steel, clean dry | 0.5–0.8 | ~0.42 | Engineering Toolbox |
| Steel on steel, oiled/greased | ~0.15 | ~0.08 | Engineering Toolbox |
| Aluminium on mild steel, dry | ~0.61 | ~0.47 | Engineering Toolbox; aluminium galls |
| Brass on steel, dry | ~0.51 | ~0.44 | Engineering Toolbox |
| Cast iron on cast iron, dry | ~1.1 | ~0.15 | Engineering Toolbox |
| Glass on glass | 0.9–1.0 | ~0.4 | Engineering Toolbox |
| PTFE on steel | 0.05–0.2 | 0.04–0.1 [est] | Lowest dry friction; creeps under load |
| Nylon on steel, dry | ~0.4 | 0.3–0.4 [est] | Absorbs water, dimensions change |
| Acetal (POM, Delrin) on steel | 0.2–0.35 [est] | 0.15–0.3 [est] | Good printed-free bushing material |
| PLA on PLA / PETG on PLA (printed) | 0.3–0.5 [est] | 0.25–0.4 [est] | Not verified; layer texture matters |
| Rubber on dry concrete | 0.6–0.85 | 0.5–0.8 [est] | Engineering Toolbox |
| Rubber / TPU / silicone pad on most dry solids | 0.5–1.0 [est] | — | Use for gripper pads; measure on the real object |
| Wood on wood, dry | 0.25–0.5 | ~0.2 [est] | Engineering Toolbox |
| Leather on cast iron | ~0.6 | ~0.56 | Engineering Toolbox |
| GT2 belt on aluminium pulley flank (for capstan calc) | 0.25–0.4 [est] | — | Teeth carry load; friction matters only for smooth idlers |

**Rolling element bearings** behave as an *equivalent* μ referred to the bore: friction torque
M ≈ 0.5·μ·P·d, with P = bearing load (N), d = bore diameter (m). SKF catalogue constants [typ]:
deep groove ball ~0.0015, angular contact ~0.0020, self-aligning ball ~0.0010, cylindrical roller
~0.0011, tapered roller ~0.0018, thrust ball ~0.0015, needle ~0.0025. Seals (2RS) add a fixed
drag that often dominates at light loads; shielded (ZZ) adds much less. Example: 608-2RS (d = 8 mm)
at 50 N: rolling part 0.5·0.0015·50·0.008 = 0.3 mN·m; seal drag is typically larger (~1–5 mN·m [est]).
Either way, bearing friction is negligible next to gravity torque in a desktop arm; plain printed
bushings are not (μ ~0.3 means 100× more torque).

**Rolling resistance** (wheels): F = Crr·N. Crr [typ, Engineering Toolbox ranges]: steel wheel on
steel rail 0.001–0.002; hard plastic wheel on smooth floor ~0.005–0.02 [est]; rubber tyre on
concrete ~0.01–0.02; soft polyurethane caster on carpet 0.05+ [est].

### 2.5 Wedges, inclines and self-locking

- Block on incline angle θ pushed up the slope by force P parallel to it:
  P = m·g·(sin θ + μ cos θ). Down the slope: P = m·g·(μ cos θ − sin θ) (negative means it slides).
- **Wedge self-locking** [std]: a wedge with included angle α stays put after the drive force is
  removed if each sliding face's angle satisfies α_face < φ = atan(μ). Two sliding faces: total
  included angle < 2φ (approximate, symmetric wedge). With μ = 0.3, φ ≈ 16.7°.
- Taper fits (Morse taper ~1.5° half-angle) are self-locking for this reason; steep tapers (7:24,
  ~8.3° half-angle) are deliberately not.
- Wedge mechanical advantage ≈ 1/(tan α + μ terms): small angles give huge force but most input
  work becomes friction heat. Efficiency of a self-locking wedge or screw is always < 50%.

### 2.6 Screws (lead screws, power screws) [std]

- Driving torque to push axial force F with lead l: T = F·l / (2π·η).
- Efficiency of a square-ish thread with lead angle λ (tan λ = l/(π·d_m)) and thread friction μ:
  η = tan λ / tan(λ + φ), φ = atan μ (ignores the thread flank angle; ACME adds a cos-term).
- **Back-drive** (load turns the screw) happens only if λ > φ. Trapezoidal screws with small lead
  are self-locking; ball screws (η ≈ 0.9 [typ, ball screw vendors]) always back-drive and need a
  brake on vertical axes.
- Typical efficiencies [est]: trapezoidal steel/bronze or steel/POM nut 0.2–0.5 depending on lead;
  T8 lead 8 mm 4-start with brass nut ~0.5–0.6; T8 lead 2 mm ~0.3; ball screw 0.85–0.95.
- Example: 50 N load, T8×8 lead, η = 0.5: T = 50·0.008/(2π·0.5) = 0.127 N·m. Fine for NEMA 17.

### 2.7 Belt / rope friction (capstan equation) [std]

T_tight / T_slack = e^(μ·θ), θ = wrap angle in radians. With μ = 0.3 and 180° wrap: ratio 2.57;
with 360°: 6.6. Used for flat/round belts, rope winches, tendon-driven joints over smooth pins,
and to estimate how much a smooth idler resists a slipping belt. Toothed GT2 belts transmit by
teeth, not friction; the useful rule there is teeth-in-mesh ≥ 6 for rated load [typ, Gates GT2
design manual].

### 2.8 Gripping by friction

Two-finger parallel grip holding mass m, with vertical acceleration a, friction μ, safety factor SF:

F_grip_per_finger ≥ SF · m · (g + a) / (2·μ)

- SF = 2 is a common minimum for light parts; 3–4 if the object swings or is accelerated
  sideways [est].
- Example: 100 g object, a = 10 m/s², μ = 0.5 (TPU pad), SF = 2: F ≥ 2·0.1·19.81/(1.0) = 4 N per
  finger. With hard PLA fingers (μ ≈ 0.3) it rises to 6.6 N. Pads are cheap force.
- Form closure (object caged by geometry) beats force closure (friction) whenever possible.

---

## 3. Kinematics

### 3.1 Linear, constant acceleration [std]

| Formula | Use |
|---|---|
| v = v₀ + a·t | speed after time |
| x = x₀ + v₀·t + ½·a·t² | position after time |
| v² = v₀² + 2·a·Δx | speed from distance (no time) |
| x = ½(v₀ + v)·t | distance from average speed |

### 3.2 Rotational analogues [std]

θ ↔ x, ω ↔ v, α ↔ a: ω = ω₀ + α·t, θ = ω₀·t + ½·α·t², ω² = ω₀² + 2α·Δθ.
Point at radius r: tangential v = ω·r, tangential a_t = α·r, centripetal a_c = ω²·r = v²/r
(always toward the centre, even at constant speed).

### 3.3 Motion profiles

- **Trapezoidal** (accelerate, cruise, decelerate). For a move of distance D with max speed v_max
  and accel a: if D < v_max²/a (no cruise reached), it becomes triangular with peak speed √(a·D)
  and time 2√(D/a). Otherwise t = D/v_max + v_max/a.
- **S-curve** (jerk-limited) softens acceleration steps, reducing excited vibration; costs ~10–30%
  more move time [est].
- **Rule**: torque sizing uses peak acceleration; heating uses RMS torque over the duty cycle.
- Stepper reality: max step rate is limited by the driver and firmware; e.g. 1.8° motor at 1/16
  microstepping needs 3200 steps per rev, so 10 rev/s = 32 kHz step rate.

### 3.4 Projectile motion (no drag) [std]

Launch speed v₀ at angle θ above horizontal, g = 9.81 m/s²:

| Quantity | Formula |
|---|---|
| Horizontal position | x = v₀·cos θ · t |
| Vertical position | y = v₀·sin θ · t − ½·g·t² |
| Time to apex | t_apex = v₀·sin θ / g |
| Max height | h = v₀²·sin²θ / (2g) |
| Range on level ground | R = v₀²·sin(2θ) / g (max at 45°) |
| Time of flight (level) | T = 2·v₀·sin θ / g |
| Free fall time from height h | t = √(2h/g) |
| Free fall impact speed | v = √(2gh) |

Handy numbers [std]: 0.1 m drop → 0.14 s, 1.4 m/s. 0.5 m → 0.32 s, 3.1 m/s. 1 m → 0.45 s, 4.4 m/s.
2 m → 0.64 s, 6.3 m/s.

### 3.5 When drag matters for projectiles

Compare drag to weight: F_d/F_g = ρ·C_d·A·v² / (2·m·g). Terminal speed v_t = √(2mg / (ρ·C_d·A)).
If the flight speed is well under ~0.3·v_t, ignore drag (error < ~10%) [est].

| Object | m | d | v_t (computed, C_d as noted) | Verdict |
|---|---|---|---|---|
| Tennis ball | 57 g | 67 mm | ~22 m/s (C_d ≈ 0.55) | Drag ~20% of weight at 10 m/s; matters for long throws |
| Ping-pong ball | 2.7 g | 40 mm | ~8.6 m/s (C_d ≈ 0.47) | Drag dominates; no-drag ballistics badly wrong |
| Steel ball 20 mm | 33 g | 20 mm | ~85 m/s [computed] | Ignore drag at desktop scale |
| Foam ball 70 mm, 10 g | 10 g | 70 mm | ~8 m/s [computed] | Drag dominates |

(Computed with ρ_air = 1.2 kg/m³; spin adds Magnus lift and can curve light balls substantially.)

### 3.6 Catching: kinematics budget

For a catcher (arm or cup moving to intercept a falling/thrown object):

1. **Sensing latency** t_s: camera frame period (30 fps = 33 ms; 60 fps = 17 ms; 120 fps = 8 ms) +
   exposure + processing. Typically 50–100 ms end to end for webcam + Python [est].
2. **Prediction**: fit a parabola (or drag model) to ≥ 3 observations; more frames = better fit
   but less time left.
3. **Move time** t_m: catcher must reach the intercept point before the object. Available time
   = flight time − t_s − t_m − margin.
4. **Position error** at catch: σ_pos ≈ v_object × timing error. At 4 m/s, 10 ms timing error = 40 mm.
   Size the catching cup/net accordingly (cup radius ≥ 2–3 σ_pos [est]).
5. **Catcher acceleration**: to move distance D in time t from rest (triangular profile) needs
   a = 4D/t². Example: 200 mm in 150 ms → a = 4·0.2/0.0225 = 35.6 m/s² (3.6 g). That is aggressive
   for a belt-driven printed arm. Shorten D (wider cup, better prediction) before raising a.
6. **Soft catch**: match catcher velocity to object velocity at contact (moving with the object)
   to reduce impact force and bounce. See 4.7.

### 3.7 Throwing: release kinematics

- Release speed of a point at radius r on a link rotating at ω: v = ω·r (tangential), direction
  perpendicular to the link at release.
- **Release timing error** δt changes release angle by ω·δt. At ω = 20 rad/s, 5 ms error = 0.1 rad
  = 5.7° of direction change. Use a release mechanism with repeatable timing, or a longer arm
  with lower ω for the same v.
- Energy delivered to the projectile: ½·m·v². Arm must also accelerate its own inertia; often the
  arm's KE ≫ the ball's, so the motor is sized by the arm.
- Range from release height h₀: solve y(t) = −h₀ with drag-free equations, or simulate with drag.

---

## 4. Dynamics

### 4.1 Newton's laws in usable form [std]

- Linear: ΣF = m·a (vectors). Rotation about a fixed axis or the CoM: ΣM = J·α.
- d'Alembert: treat −m·a and −J·α as extra loads and solve as statics. Convenient for FBDs.
- For a link rotating about a fixed pivot O: ΣM_O = J_O·α, where J_O is inertia about O (parallel
  axis). Do not mix inertia about the CoM with moments about the pivot.
- Multi-link arms: joint torques couple (moving the elbow pushes on the shoulder). For sizing use
  worst-case static + each joint's own acceleration with all distal links rigid; for control and
  simulation use a proper rigid-body dynamics solver (MuJoCo, PyBullet, Pinocchio).

### 4.2 Mass moments of inertia, common shapes [std]

m = mass (kg), dimensions in m, J in kg·m². Axis described in the "about" column.

| Shape | About | J |
|---|---|---|
| Point mass at radius r | the axis | m·r² |
| Thin ring / thin-walled tube radius r | central axis | m·r² |
| Solid cylinder / disc radius r | central (long) axis | ½·m·r² |
| Thick tube, radii r_i, r_o | central axis | ½·m·(r_i² + r_o²) |
| Solid cylinder radius r, length L | diameter through centre (transverse) | (1/12)·m·(3r² + L²) |
| Thin rod length L | perpendicular, through centre | (1/12)·m·L² |
| Thin rod length L | perpendicular, through one end | (1/3)·m·L² |
| Rectangular plate a × b | perpendicular to plate, through centre | (1/12)·m·(a² + b²) |
| Rectangular plate a × b | in-plane axis through centre, parallel to b | (1/12)·m·a² |
| Solid box a × b × c | through centre, parallel to c | (1/12)·m·(a² + b²) |
| Solid sphere radius r | diameter | (2/5)·m·r² |
| Thin spherical shell radius r | diameter | (2/3)·m·r² |
| Solid cone radius r | central axis | (3/10)·m·r² |

Radius of gyration k: J = m·k². Useful for comparing shapes (a ring puts all mass at k = r; a
disc has k = 0.707 r).

### 4.3 Parallel axis and composite bodies [std]

- **Parallel axis**: J_O = J_cm + m·d², d = distance between the CoM axis and the parallel axis O.
  Only valid between parallel axes and only from the CoM axis (never chain two non-CoM axes
  without going through the CoM).
- **Composite**: sum each part's J about the common axis (each with its own parallel-axis term).
  Subtract holes as negative masses.
- **Takeaway**: mass far from the joint dominates through d². A 0.3 kg motor at 0.25 m from the
  shoulder adds 0.3·0.0625 = 0.019 kg·m², about 40× a 50 mm disc of the same mass on the axis.
  This is why the standards say keep motors at the base.
- Get real numbers from CAD mass properties (with correct density: PLA ~1.24 g/cm³, PETG ~1.27,
  ABS ~1.04, aluminium 2.70, steel 7.85 [typ, supplier datasheets]; printed parts at 20–40% infill
  weigh roughly 40–70% of solid [est], depending on walls).

### 4.4 Reflected inertia through transmissions [std]

Define reduction ratio N = ω_motor / ω_load (> 1 for reduction).

| Transmission | Load inertia seen at motor |
|---|---|
| Gearbox / belt reduction N | J_load / N² (+ gear/pulley inertias on each shaft, reflected by their own ratio²) |
| Belt or rack moving linear mass m, pulley/pinion pitch radius r (direct) | m·r² |
| Lead screw lead l (m/rev) moving mass m | m·(l / 2π)² |
| Belt reduction N then pulley radius r | m·r² / N² |

Torque relations: T_motor = T_load / (N·η) when driving; speed ω_motor = N·ω_load.

**Total motor torque** for acceleration α_load:
T_motor = (J_motor + J_pulley_motor + J_load_total/N²)·(N·α_load) + T_gravity_and_friction/(N·η).

**Inertia ratio** (load reflected : rotor):
- Servo guidance [typ, motioncontroltips / Design World / vendor sizing guides]: keep ≤ 10:1 for
  general use; ≤ 5:1 for high-dynamic, high-precision; much higher works with stiff couplings and
  high-resolution feedback.
- Steppers [est]: open-loop steppers tolerate higher ratios at low speed, but large ratios worsen
  resonance and missed steps under fast acceleration; aim ≤ 10–30:1 and test. This is a rule of
  thumb, not verified against a vendor spec.
- **Optimal ratio for minimum move time** (inertia-dominated, no gravity): N_opt = √(J_load / J_motor).
  At N_opt the reflected load equals the rotor inertia. Above N_opt the motor spends its torque
  spinning itself; below it, it lacks leverage.

Typical rotor inertias [typ, vendor datasheets e.g. 17HS series]: NEMA 17 (40 mm long) ~50–70 g·cm²
= 5–7e-6 kg·m²; NEMA 23 (56 mm) ~300–500 g·cm²; NEMA 14 ~10–20 g·cm².

### 4.5 Work, energy, power [std]

| Quantity | Formula | Notes |
|---|---|---|
| Work, linear | W = F·d·cos θ | J |
| Work, rotational | W = T·Δθ | Δθ in rad |
| Kinetic energy | ½·m·v² + ½·J·ω² | translate + rotate |
| Potential (gravity) | m·g·Δh | |
| Spring energy | ½·k·x² (linear), ½·k_θ·θ² (torsion) | |
| Power, linear | P = F·v | W |
| Power, rotational | P = T·ω | ω in rad/s |
| Electrical in | P = V·I | |
| Efficiency chain | η_total = Π ηᵢ | |

Typical efficiencies [est, vendor app notes]: spur gear mesh 0.95–0.98 per stage; planetary stage
0.90–0.97; worm 0.4–0.9 (low-ratio higher; self-locking worms < 0.5); GT2 timing belt 0.95–0.98;
ball screw 0.9; trapezoidal screw 0.2–0.6; stepper motor electrical→mechanical 0.3–0.6 at typical
operating points (much worse at standstill, where it is 0 and all input is heat); small BLDC 0.7–0.9.

Energy checks catch errors: if a throw needs ½mv² = 2 J delivered in 0.1 s, the motor needs > 20 W
average mechanical power on top of moving the arm. A NEMA 17 delivers roughly 5–20 W mechanical
[est], so this is a real constraint.

### 4.6 Momentum and impulse [std]

- Linear momentum p = m·v; impulse J = ∫F dt = Δp. Average force F_avg = Δp / Δt.
- Angular momentum L = J·ω; angular impulse ∫T dt = ΔL.
- Conservation: in a collision with no external impulse, total momentum is conserved; energy is
  not (unless perfectly elastic).

### 4.7 Impact and coefficient of restitution

- Coefficient of restitution e = (relative separation speed) / (relative approach speed).
  e = 1 perfectly elastic, e = 0 perfectly plastic (they stick).
  Typical [est]: tennis ball on hard floor ~0.73–0.76 (ITF test spec drop 254 cm → rebound
  135–147 cm [typ, ITF rules]); golf ball ~0.8; steel on steel 0.6–0.9; ping-pong ~0.9; PLA on PLA
  ~0.5–0.7 (not verified); foam or bean bag ~0.1–0.3.
- Energy absorbed in a 1D collision of m₁, m₂: ΔE = ½·μ_r·(1 − e²)·v_rel², with reduced mass
  μ_r = m₁m₂/(m₁+m₂).
- **Impact force estimate from stopping distance** (energy method): F_avg = ½·m·v² / s, where s is
  the distance over which the object is decelerated (padding compression + catcher give).
  Peak force for a linear spring stop is 2× F_avg.
- **From stopping time**: F_avg = m·v / Δt.
- Example (catcher design): 57 g tennis ball at 5 m/s. KE = 0.71 J. Stopped in 5 mm (rigid cup):
  F_avg = 142 N. Stopped in 50 mm (foam/net/compliant mount): 14 N. Ten times softer catch means
  ten times less load on joints and bearings, and less bounce-out. Compliance is the cheapest
  fix for impact loads.
- To prevent bounce-out: lower e (foam, fabric, bean-bag lining), deeper cup, and move the cup
  with the ball at contact (reduces v_rel).
- A falling object of mass m dropped on a stationary spring (no damping) gives peak force
  F = m·g·(1 + √(1 + 2h/δ_st)), δ_st = m·g/k. Even h = 0 (sudden release) gives 2× static load.

---

## 5. Vibration

### 5.1 Single degree of freedom [std]

- Mass-spring: ω_n = √(k/m) rad/s, f_n = ω_n/(2π) Hz.
- Torsional: ω_n = √(k_θ/J).
- From static deflection under own weight: f_n = (1/2π)·√(g/δ_st) ≈ 15.8/√(δ_st in mm) Hz.
  1 mm sag → ~16 Hz; 0.1 mm → ~50 Hz; 10 mm → ~5 Hz. Quick and surprisingly good.
- Damped natural frequency ω_d = ω_n·√(1 − ζ²); damping ratio ζ = c / (2√(k·m)).
- Effect of a payload: f_n ∝ 1/√m. Doubling end mass lowers f_n by 29%.

### 5.2 Stiffness of common elements [std]

| Element | Stiffness |
|---|---|
| Cantilever beam, tip load | k = 3EI/L³ |
| Simply supported beam, centre load | k = 48EI/L³ |
| Fixed-fixed beam, centre load | k = 192EI/L³ |
| Axial bar | k = EA/L |
| Torsion of solid round shaft | k_θ = G·J_p/L, J_p = π d⁴/32 |
| Springs in series | 1/k = Σ 1/kᵢ (softest dominates) |
| Springs in parallel | k = Σ kᵢ |
| Timing belt span (tension member) | k ≈ E_belt·A/L_span; vendor gives "specific stiffness" c_sp = EA in N per unit strain |
| Through a reduction N (spring on load side) | seen at motor: k_θ / N² |

Area moments: solid rectangle b × h (bending about the axis parallel to b) I = b·h³/12;
solid round I = π d⁴/64; tube I = π(d_o⁴ − d_i⁴)/64. Depth h enters cubed: orient ribs and
links so their tall dimension is along the bending load.

Young's modulus E [typ, supplier datasheets]: steel 200 GPa; aluminium 69 GPa; brass ~100 GPa;
carbon-fibre tube 70–150 GPa (layup dependent); PLA ~3.5 GPa bulk, printed 2–3.5 GPa [est];
PETG ~2.0 GPa; ABS ~2.2 GPa; nylon 1.5–2.8 GPa (wet lower); TPU 0.01–0.1 GPa.

The first bending mode of a uniform cantilever (no tip mass): ω₁ = 1.875²·√(EI/(ρA·L⁴)).
For a cantilever with a tip mass M much heavier than the beam: ω ≈ √(3EI/(L³·(M + 0.24·m_beam))).

### 5.3 Damping, typical values [est]

| System | ζ (damping ratio) |
|---|---|
| Welded steel frame | 0.01–0.02 |
| Bolted metal structure | 0.02–0.05 |
| Aluminium extrusion frame with brackets | 0.02–0.05 |
| 3D-printed PLA/PETG links | 0.02–0.06 (not verified) |
| Belt-driven axis | 0.03–0.1 |
| Rubber mounts / elastomer isolators | 0.05–0.2 |
| Active control (servo velocity loop) | whatever you tune; 0.5–0.7 typical target |

Most mechanical structures are lightly damped (ζ < 0.05), so resonance amplification Q ≈ 1/(2ζ)
is 10–50×. Do not rely on damping to save a resonant design.

### 5.4 Forced response and resonance [std]

Frequency ratio r = f_excitation / f_n.

- Amplitude magnification (force-excited): 1 / √((1 − r²)² + (2ζr)²). Peaks at r ≈ 1 with
  value ≈ 1/(2ζ).
- Transmissibility to the base: isolation (output < input) only for r > √2 ≈ 1.41. Between 0 and
  √2 a soft mount *amplifies*.
- Response at r ≪ 1 is quasi-static (stiffness-controlled); at r ≫ 1 it is mass-controlled
  (falls off as 1/r²).

### 5.5 Sources of excitation in desktop mechanisms

| Source | Frequency |
|---|---|
| Stepper full-step rate | f = steps/s; e.g. 1.8° motor at 2 rev/s full-step = 400 Hz |
| Stepper low-speed resonance | typically ~1–3 rev/s for unloaded NEMA 17 (rotor natural freq ~100–300 Hz) [est] |
| Stepper mid-band instability | several rev/s; driver/voltage dependent [est] |
| Belt tooth meshing | teeth/s = pulley rpm/60 × teeth |
| Move start/stop (acceleration step) | broadband; excites lowest structural mode |
| Rotating imbalance | 1× shaft speed |
| Fans | blade-pass = rpm/60 × blades |
| Mains hum | 50/60 Hz and 100/120 Hz |

Stepper rotor natural frequency estimate [est]: k_θ ≈ T_hold · N_r (N_r = 50 rotor teeth for 1.8°),
ω₀ = √(k_θ / (J_rotor + J_load_reflected)). NEMA 17 with 0.4 N·m hold, J = 5.4e-6 kg·m²:
k_θ ≈ 20 N·m/rad, f₀ ≈ 306 Hz unloaded, falling as load inertia rises. Microstepping and
modern drivers (e.g. TMC StealthChop/SpreadCycle) reduce but do not remove this.

### 5.6 Avoiding resonance: decision rules

1. **Separation**: keep f_n of each structural mode ≥ 2–3× the highest significant excitation,
   or ≤ 1/√2 of it (isolation) [est, common practice].
2. **Control bandwidth**: keep the lowest structural mode ≥ 3–5× the position/velocity loop
   bandwidth [est]; otherwise the controller excites the structure and you see chatter.
3. **Stiffen before damping**: raise k (deeper sections, triangulation, shorter spans, higher belt
   tension, larger pulleys for belts) or reduce moving mass. f_n ∝ √(k/m).
4. **Belt axes**: belt spans are often the softest spring. Shorter spans, wider belts (GT2 9 mm vs
   6 mm ≈ 1.5× stiffness), and steel-cord belts help.
5. **Shape the input**: S-curves, input shaping (ZV/ZVD shapers, as in Klipper "input shaper"),
   or avoiding dwelling at resonant speeds.
6. **Add damping when separation fails**: elastomer pads, constrained-layer damping, viscous
   couplings, or active damping in the controller.
7. **Measure**: tap test with a phone accelerometer or microphone, or the Klipper ADXL345 workflow,
   gives f_n within minutes. A measured f_n beats a calculated one.

### 5.7 Rotating shafts

Critical speed of a shaft ≈ its first bending natural frequency. For desktop shafts (8 mm, < 300 mm
span, < 3000 rpm) it is rarely limiting; long lead screws are the exception: a 8 mm screw 500 mm
long with one end free can whip at a few hundred rpm [est]. Support both ends.

---

## 6. Fluids

### 6.1 Pressure [std]

- p = F/A. Gauge pressure is relative to atmosphere; absolute = gauge + ~101 kPa.
- Hydrostatic: p = ρ·g·h. Water: ~9.8 kPa per metre depth (~0.1 bar/m).
- Pascal: pressure in a confined fluid acts equally everywhere; force multiplies with area ratio.
- Air: ρ ≈ 1.2 kg/m³ at 20 °C sea level; dynamic viscosity μ ≈ 1.8e-5 Pa·s.
  Water: ρ ≈ 1000 kg/m³, μ ≈ 1.0e-3 Pa·s. [typ, Engineering Toolbox]

### 6.2 Drag [std + typ]

- F_d = ½·ρ·v²·C_d·A, A = frontal (projected) area.
- Reynolds number Re = ρ·v·L/μ. For air at 1 m/s and L = 0.05 m, Re ≈ 3300.
- C_d values (bluff bodies, 1e4 < Re < 2e5 unless noted):

| Shape | C_d (based on frontal area) | Source |
|---|---|---|
| Flat plate normal to flow | 1.28 | NASA Glenn Beginner's Guide |
| Smooth sphere | ~0.47 (subcritical); drops to ~0.1–0.2 above Re ≈ 3e5 (drag crisis) | NASA Glenn; Re-dependent |
| Cube, face-on | ~0.95–1.07 | Volupe (from White, Fluid Mechanics) |
| Long cylinder, cross flow | ~1.0–1.2 | [typ, textbook] |
| Short cylinder, side-on (L/D ~ 1) | ~0.8 | [typ] |
| Streamlined body | 0.04–0.1 | NASA Glenn |
| Tennis ball (fuzz) | ~0.5–0.6 | [est, sports-ball literature] |
| Human / open hand | ~1.0–1.3 | [est] |

- At low Re (< 1, e.g. dust), Stokes drag F = 3π·μ·d·v (linear in speed). Irrelevant to most
  mechanisms; relevant to tiny particles and sensors.
- Arm drag check: a 50 mm wide link moving at 2 m/s sees ½·1.2·4·1.2·(0.05·0.3) ≈ 0.04 N. Ignore
  air drag on desktop arms; do not ignore it on fans, propellers, ping-pong balls, paper, foam.

### 6.3 Buoyancy [std]

F_b = ρ_fluid·g·V_displaced. In air it is ~1.2 g of "lift" per litre; negligible except for
balloons. In water, an object floats if its mean density < 1000 kg/m³. Printed parts with low infill
float and trap air; seal or fill them if submerged.

### 6.4 Pneumatics basics

- Cylinder extend force: F = p·A_bore; retract: F = p·(A_bore − A_rod). Real output ~80–90% after
  seal friction [est]; size with 50–70% of theoretical at the minimum supply pressure for dynamic
  moves [est, common sizing practice in SMC/Festo guides].
- Example: 20 mm bore at 6 bar gauge: A = π·0.01² = 3.14e-4 m²; F = 6e5·3.14e-4 = 188 N theoretical.
- Shop air is commonly 6–7 bar (600–700 kPa) gauge [typ]; small hobby compressors 2–8 bar.
- **Air is compressible**: pneumatics are great for bang-bang (end-to-end) moves, grippers, and
  soft compliant force; poor at mid-stroke positioning without servo valves. The trapped air acts
  as a spring: k ≈ γ·p_abs·A² / V (γ ≈ 1.4 adiabatic, 1.0 isothermal).
- Speed is set by flow (valve Cv / orifice, tube bore, cylinder volume), not pressure. Add flow
  controls (meter-out preferred) and end-of-stroke cushions; uncushioned cylinders slam.
- Air consumption per stroke ≈ (bore area × stroke) × (p_abs/p_atm) for each direction.
- Stored energy: compressed air in a volume is hazardous (≈ p·V scale); burst tests use
  water (incompressible) not air. Never pressurise 3D-printed vessels with air without
  testing; FDM layers leak and can fail abruptly.

### 6.5 Vacuum suction

- Holding force (theoretical) F = Δp·A. Maximum Δp is atmospheric (~101 kPa); practical vacuum
  generators reach 60–90 kPa below atmosphere [typ, Schmalz/SMC literature].
- Example: 30 mm cup at 60 kPa: F = 6e4·π·0.015² = 42 N theoretical.
- Safety factor common in vendor guides [typ]: ≥ 2 for horizontal pick (load pulling normal to cup),
  ≥ 4 for vertical cup face (load in shear, friction-limited), plus acceleration loads.
- Porous or rough surfaces (cardboard, fabric, printed parts) leak; test or use foam-lipped cups.

---

## 7. Heat transfer basics

### 7.1 Modes [std]

| Mode | Formula | Variables |
|---|---|---|
| Conduction (slab) | Q = k·A·ΔT / L | k thermal conductivity W/(m·K), A area, L thickness |
| Convection | Q = h·A·(T_s − T_∞) | h convection coefficient W/(m²·K) |
| Radiation | Q = ε·σ·A·(T_s⁴ − T_∞⁴) | σ = 5.67e-8 W/(m²·K⁴), ε emissivity, T in kelvin |
| Thermal resistance | R = ΔT / Q (K/W); series add, parallel add reciprocally | conduction L/(kA), convection 1/(hA) |
| Transient (lumped) | T(t) = T_∞ + (T₀ − T_∞)·e^(−t/τ), τ = m·c / (h·A) | valid if Biot number hL/k < 0.1 |

Linearised radiation: h_rad ≈ 4·ε·σ·T_mean³ ≈ 6 W/(m²·K) at ~320 K and ε ≈ 1 [computed]; for
anodised/black or painted surfaces (ε ~0.8–0.95) this is comparable to natural convection. Bare
polished aluminium (ε ~0.05) radiates almost nothing.

### 7.2 Typical values

Thermal conductivity k [typ, Engineering Toolbox / supplier data]:

| Material | k, W/(m·K) |
|---|---|
| Copper | ~390–400 |
| Aluminium (pure / 6061) | ~237 / ~167 |
| Steel (carbon) | ~45–55 |
| Stainless steel | ~15–16 |
| Thermal paste | 1–8 |
| Thermal pad (silicone) | 1–6 |
| Glass | ~1 |
| Nylon | ~0.25 |
| ABS | ~0.17 |
| PLA / PETG | ~0.13–0.2 |
| Still air | ~0.026 |

3D-printed plastics are thermal insulators: a PLA motor mount traps motor heat in the motor
and the motor heats the PLA.

Convection coefficient h [typ, SolidWorks help / Engineering Toolbox; very geometry dependent]:

| Condition | h, W/(m²·K) |
|---|---|
| Natural convection, air | 5–25 (use ~5–10 for small enclosed parts) |
| Forced air, small fan | 20–100 |
| Forced air, strong flow | 100–300 |
| Natural convection, water | 50–1000 |
| Forced water | 500–10 000 |

### 7.3 Motor heating

- **Copper loss** dominates at low speed: P_cu = Σ I²·R per winding. A two-phase stepper at
  standstill with both phases at rated current dissipates ≈ 2·I²·R (full-step), or similar average
  with sine microstepping (I_rms per phase).
- Copper resistance rises ~0.39%/K [std]; a winding 80 K above ambient has ~31% more resistance.
- Core (iron) losses rise with speed; at high step rates they can dominate.
- Example [computed, check against your datasheet]: NEMA 17, 1.7 A/phase, 1.5 Ω/phase:
  P = 2·1.7²·1.5 = 8.7 W at standstill. Outer area ~0.010 m² (42×42×40 mm). With h = 10 W/(m²·K)
  convection only: ΔT ≈ 8.7/(10·0.010) ≈ 85 K. Real motors bolted to metal run cooler (conduction
  to the frame). In free air on a PLA mount, expect 60–90 °C case at full current [est].
- Thermal time constant of a NEMA 17 [est]: ~0.3 kg × ~500 J/(kg·K) / ~0.1 W/K ≈ 25 min. Short tests
  do not reveal steady-state temperature; run ≥ 1 hour or extrapolate the exponential.
- **Limits** [typ]: NEMA 17 datasheets commonly state max case 80 °C (e.g. Lin Engineering 417
  series). Class B insulation is rated 130 °C winding; Oriental Motor says case runs ~30 K below
  winding and recommends case ≤ 80 °C (≤ 75 °C for UL/CSA use). Winding life roughly halves per
  ~10 K above rating [typ, Arrhenius rule of thumb].
- **Mitigations**: driver standstill current reduction (TMC "IHOLD" e.g. 50%, cuts standstill heat
  to ~25%); run current only as high as the torque budget needs; aluminium motor plates; fans;
  avoid PLA in contact with motors.

### 7.4 Plastics near heat [typ, supplier datasheets; values vary by grade]

| Material | Glass transition / softening (approx.) | Practical continuous limit [est] |
|---|---|---|
| PLA | Tg ~55–65 °C | < 50 °C under load; creeps near motors and in hot cars |
| PETG | Tg ~75–85 °C | < 65 °C |
| ABS / ASA | Tg ~100–105 °C | < 85 °C |
| PC | Tg ~145 °C | < 115 °C |
| Nylon (PA6/PA12) | Tg low but semicrystalline; HDT ~60–180 °C by grade | grade dependent |

Rule: any printed part touching a motor, driver heatsink, or hot end uses PETG/ABS/ASA or better,
or is separated by a metal plate or air gap.

### 7.5 Electronics heating

- Driver/MOSFET loss: P ≈ I²·R_ds(on) (conduction) + switching losses. TMC2209 R_ds(on) ~0.2 Ω per
  switch [typ, Trinamic datasheet; check yours]; at 1.5 A rms it runs hot without a heatsink.
- Junction temperature: T_j = T_ambient + P·(R_θjc + R_θcs + R_θsa). Keep T_j ≤ ~100–125 °C
  for margin (silicon is typically rated 150 °C max) [typ].
- Linear regulators dissipate (V_in − V_out)·I: 24 V → 5 V at 0.5 A is 9.5 W, far too much for a
  small LDO; use a buck converter.
- Enclosures trap heat. A sealed box with 10 W inside, 0.1 m² surface, h = 5 W/(m²·K): ΔT ≈ 20 K
  above room [computed]. Add vents (bottom in, top out) or a fan.
- Wire current: 24 AWG (0.2 mm²) is fine for ~1–2 A in free air for short runs; 18 AWG for ~5–7 A
  [est, varies by insulation and bundling; check chassis-wiring tables].

---

## 8. Order-of-magnitude sanity numbers

Use these to catch errors. Labelled [est] unless stated.

### 8.1 Masses and densities

| Thing | Typical |
|---|---|
| NEMA 17 stepper (40 mm body) | 0.28–0.35 kg [typ datasheets] |
| NEMA 23 stepper (56 mm) | 0.6–0.7 kg |
| SG90 micro servo | 9 g |
| MG996R servo | 55 g |
| 608 bearing | 12 g |
| M3×10 screw | ~0.7 g |
| GT2 6 mm belt | ~4–5 g/m [est] |
| 2020 aluminium extrusion | ~0.5 kg/m [typ vendor] |
| 8 mm steel rod | ~0.39 kg/m [computed, 7850 kg/m³] |
| Typical printed link (desktop arm) | 20–150 g |
| Tennis ball / ping-pong / golf | 57 g / 2.7 g / 46 g [typ, sports rules] |
| Water bottle 0.5 L full | ~0.52 kg |
| Smartphone | 0.15–0.25 kg |

### 8.2 Forces and torques

| Thing | Typical |
|---|---|
| Weight of 100 g | ~1 N |
| Finger pinch (adult) | 50–100 N |
| Comfortable hand push | 20–50 N |
| NEMA 17 holding torque | 0.2–0.65 N·m [typ datasheets] |
| NEMA 17 usable torque at 300–600 rpm, 24 V | ~0.1–0.35 N·m |
| NEMA 23 holding torque | 0.5–3 N·m |
| SG90 servo stall | ~0.18 N·m (1.8 kgf·cm) [typ] |
| MG996R stall | ~0.9–1.1 N·m [typ] |
| Desktop arm shoulder gravity torque (0.5 m reach, 200 g payload) | 1–3 N·m |
| GT2 6 mm belt working tension | up to ~20–40 N continuous for long life [est]; breaks at hundreds of N |
| M3 screw into printed plastic, pull-out | ~200–600 N with heat-set insert; less self-tapped [est] |
| M3 steel screw (8.8) proof load | ~2.9 kN [typ, ISO 898-1 stress area 5.03 mm² × 580 MPa] |

### 8.3 Speeds and accelerations

| Thing | Typical |
|---|---|
| Hobby arm joint speed | 30–180 °/s (0.5–3 rad/s) |
| Industrial cobot tool speed | ~1 m/s (collaborative limits often lower) |
| FDM printer head acceleration | 1–10 m/s² (Klipper tuned 3–20) |
| Free fall | 9.81 m/s² |
| Human throw (casual) | 10–20 m/s |
| Human reaction time | 150–250 ms |
| Webcam frame time | 33 ms (30 fps) |
| Stepper max useful speed, NEMA 17 at 24 V | ~600–1500 rpm before torque collapses |

### 8.4 Stiffness, frequency, power, heat

| Thing | Typical |
|---|---|
| Printed arm first mode (desktop) | 5–30 Hz |
| Aluminium extrusion frame mode | 20–100 Hz |
| Stepper mechanical output | 5–20 W |
| Small USB fan airflow | moves enough air for h ≈ 20–50 W/(m²·K) nearby |
| PC-style 5 V 2 A supply | 10 W |
| 24 V 5 A supply | 120 W (enough for 3–4 NEMA 17 + electronics) |

---

## 9. Common physics mistakes in mechanism design

Grouped by symptom. Each is a check the agents should run.

### 9.1 Torque and sizing

1. **Static torque only.** Forgetting J·α acceleration torque. For fast moves it can exceed gravity
   torque. Size with gravity + acceleration + friction, then apply the safety factor.
2. **Using holding torque as running torque.** Steppers lose torque with speed; use the pull-out
   curve at the real voltage.
3. **Ignoring distal motor mass.** A motor on the elbow adds weight × reach to the shoulder torque
   and inertia × reach². Put motors at the base (standards rule 3).
4. **Measuring payload reach from the wrong place.** Gravity torque uses horizontal distance from
   the joint axis to each CoM, not link length to the joint.
5. **Forgetting the arm's own mass.** Often 2–5× the payload in printed arms.
6. **Reflected inertia applied linearly.** Divide by N², not N. Friction and gravity torques divide
   by N (and η); inertia by N².
7. **Ignoring efficiency direction.** Driving: T_motor = T_load/(N·η). Back-driving: T_motor =
   T_load·η_back/N. Worms and fine lead screws do not back-drive at all.

### 9.2 Structure and stiffness

8. **Treating printed parts as rigid.** PLA's E is ~1/60 of aluminium. Deflection at a 0.4 m tip
   can be millimetres. Compute tip deflection δ = F·L³/(3EI) for every cantilevered link.
9. **Optimising strength, ignoring stiffness.** For positioning mechanisms, stiffness and natural
   frequency usually bind long before stress.
10. **Wrong section orientation.** Bending stiffness scales with depth³; turn the tall side
    along the load.
11. **Series compliance**: the softest element (belt span, printed clamp, set-screw coupling,
    bearing play) dominates; stiffening the others does nothing.
12. **Cantilevered shafts and pulleys.** Overhung loads on motor shafts and bearings; support
    the far end or keep the overhang short. Motor shaft radial load limits are often ~20–30 N
    for NEMA 17 [est; check the datasheet].

### 9.3 Friction and contact

13. **Assuming μ from a table is exact.** Table values vary ±50%. Design so the mechanism works for
    the whole plausible range (e.g. grip with the low end, drive force with the high end).
14. **Forgetting stick-slip.** Plastic-on-plastic sliders and compliant drives give jerky motion.
    Use bearings, PTFE, or stiffer drives.
15. **Friction depending on preload you did not control.** Belt tension, bearing preload and screw
    clamp all change friction; specify them.
16. **Unintended self-locking (or not).** Steep wedges, cams and screws that should back-drive
    lock up; ones that should hold slip. Check lead/wedge angle against atan(μ).

### 9.4 Dynamics and impact

17. **Rigid catches.** Stopping a falling object in millimetres gives forces of 100+ N. Add
    compliance; compute F = ½mv²/s.
18. **Assuming energy is conserved in collisions.** Use the coefficient of restitution.
19. **Ignoring reaction forces on the base.** Fast arm moves push back on the base; unclamped
    bases walk or tip.
20. **Centripetal loads forgotten.** At ω = 10 rad/s, a payload at 0.4 m sees 40 m/s² (4 g) radially;
    grippers must hold it.
21. **Linearising big angles.** sin θ ≈ θ only below ~15° (error ~1%). Pendulum and arm dynamics at
    large swings are nonlinear.

### 9.5 Vibration and control

22. **Low first mode near the motion bandwidth.** Ringing after every move. Check f_n ≥ 3–5× control
    bandwidth.
23. **"Soft mounts isolate."** Only above √2 × f_n; below that they amplify.
24. **Running steppers at resonant speeds.** Audible buzz, lost steps around 1–3 rev/s. Use
    microstepping, damping, or avoid the band.
25. **Neglecting backlash.** Gear and belt backlash makes position error at reversal and limit
    cycles in closed loops. Preload, anti-backlash nuts, or tensioned belts.

### 9.6 Thermal and electrical

26. **Steady-state temperature judged from a 5-minute test.** τ ≈ 20–30 min for NEMA 17.
27. **PLA next to motors, drivers or sunlight.** Creep and droop at 50–60 °C.
28. **Full current at standstill forever.** Use driver current reduction.
29. **Forgetting supply sizing.** Sum peak currents; steppers draw less from the supply than
    phase current (chopper drivers), but servos stall-draw several amps each.

### 9.7 Units and modelling

30. Any unit trap from 1.3 (kgf·cm, g·cm², rpm, degrees, Hz vs rad/s).
31. **Averages hiding peaks.** RMS torque for heat, peak torque for sizing; both needed.
32. **One pose checked.** Torque and deflection vary with configuration; check the worst pose and
    many random poses (standards rule 5).
33. **Sim parameters not physical.** Simulators accept impossible inertia tensors (violating the
    triangle inequality J_xx + J_yy ≥ J_zz). Validate tensors and use CAD-derived mass properties.

---

## 10. Worked mini-examples

### 10.1 Shoulder torque budget for a 2-link belt-driven arm

Setup (horizontal, worst case): upper link 0.25 m, 0.15 kg (CoM at 0.125 m); forearm 0.25 m, 0.10 kg
(CoM at 0.375 m from shoulder); payload 0.20 kg at 0.50 m. Elbow motor at the base (belt drive).

1. Gravity: τ_g = 9.81·(0.15·0.125 + 0.10·0.375 + 0.20·0.50) = 9.81·0.15625 = **1.53 N·m**.
2. Inertia about shoulder (rods, payload as point mass):
   - Upper: (1/3)·0.15·0.25² = 0.00313 kg·m²
   - Forearm: (1/12)·0.10·0.25² + 0.10·0.375² = 0.00052 + 0.01406 = 0.01458 kg·m²
   - Payload: 0.20·0.50² = 0.0500 kg·m²
   - Total J = **0.0677 kg·m²**
3. Acceleration α = 10 rad/s²: τ_a = 0.677 N·m.
4. Required joint torque = (1.53 + 0.68)·1.5 (50% safety factor) = **3.3 N·m**.
5. NEMA 17 delivering ~0.3 N·m at operating speed [est], belt η = 0.95:
   N ≥ 3.3/(0.3·0.95) ≈ 11.6 → use a two-stage GT2 belt reduction ≈ 12:1 (e.g. 20T→60T then 20T→80T = 12:1).
6. Reflected inertia: 0.0677/144 = 4.7e-4 kg·m² vs rotor ~5.4e-6 → ratio ≈ 87:1. High. N_opt =
   √(0.0677/5.4e-6) ≈ 112, so the ratio is near-optimal for speed, but the large inertia ratio means
   accelerate gently and watch for resonance/missed steps; closed-loop steppers help.
7. Output speed: 600 rpm motor / 12 = 50 rpm = 5.2 rad/s at the shoulder; payload tip speed 2.6 m/s.

Verification check: gravity torque with all mass lumped at the payload point should be an upper
bound: 9.81·0.45·0.5 = 2.2 N·m ≥ 1.53. PASS.

### 10.2 Tip deflection of a printed link

PLA link 0.25 m, rectangular 20 mm wide × 10 mm deep, load 2 N at the tip, E = 3 GPa.
I = 0.02·0.01³/12 = 1.67e-9 m⁴. δ = 2·0.25³/(3·3e9·1.67e-9) = 0.03125/15.0 = **2.1 mm**. Too floppy.
Rotate to 10 wide × 20 deep: I = 6.67e-9, δ = 0.52 mm (4× better, same material). Make it a 30×30
square tube, 2.5 mm walls: I = (0.03⁴ − 0.025⁴)/12 = (8.1e-7 − 3.9e-7)/12 = 3.5e-8 m⁴,
δ = 0.03125/314 = **0.10 mm**. Shape beats material.
Natural frequency with 0.2 kg tip mass on the tube version (beam mass neglected): k = F/δ =
2/1.0e-4 = 2.0e4 N/m; f_n = (1/2π)·√(2.0e4/0.2) ≈ **50 Hz**.

### 10.3 Catching a dropped ball

Tennis ball dropped from 1.0 m above the cup. Impact speed √(2·9.81·1.0) = 4.43 m/s, flight 0.45 s.
Vision latency 80 ms + prediction from 3 frames at 60 fps (50 ms) leaves ~320 ms to move; minus
margin 50 ms → 270 ms. To move 150 mm: a = 4·0.15/0.27² = 8.2 m/s². Feasible for a belt-driven
gantry. Catch force with 30 mm foam give: ½·0.057·4.43²/0.03 = 18.6 N avg, ~37 N peak. Bounce-out
risk: e ≈ 0.75 on hard cup → line it with foam or fabric (e < 0.3).

### 10.4 Lead-screw Z axis holding a 1 kg carriage

T8×2 (2 mm lead), η ≈ 0.3: lifting torque = 9.81·0.002/(2π·0.3) = 0.010 N·m. Lead angle with
d_m ≈ 7 mm: tan λ = 0.002/(π·0.007) = 0.091 → λ = 5.2°; φ = atan(0.15) = 8.5° (brass on steel,
lightly lubricated, est). λ < φ → self-locking; no brake needed. With T8×8 (λ ≈ 20°) it back-drives
when power is cut; add a brake, counterweight, or keep the motor energised.

### 10.5 Pneumatic gripper sanity check

16 mm bore cylinder at 4 bar gauge drives two fingers via a 1:1 linkage. F = 4e5·π·0.008² = 80 N
theoretical, ~64 N after 80% efficiency, 32 N per finger. Holding a 0.5 kg part, μ = 0.4,
a = 5 m/s², SF 2: needed 2·0.5·14.8/(2·0.4) = 18.5 N per finger. PASS with margin.

---

## 11. Canonical references

Free:

- MIT OCW 8.01 Classical Mechanics (Walter Lewin / Physics I): https://ocw.mit.edu/courses/8-01sc-classical-mechanics-fall-2016/ (free)
- MIT OCW 2.003SC Engineering Dynamics (inertia, vibration): https://ocw.mit.edu/courses/2-003sc-engineering-dynamics-fall-2011/ (free)
- MIT OCW 2.001 Mechanics and Materials I (statics, beams): https://ocw.mit.edu/courses/2-001-mechanics-materials-i-fall-2006/ (free)
- MIT OCW 2.72 Elements of Mechanical Design: https://ocw.mit.edu/courses/2-72-elements-of-mechanical-design-spring-2009/ (free)
- NASA Glenn Beginner's Guide to Aeronautics (drag, shape effects): https://www1.grc.nasa.gov/beginners-guide-to-aeronautics/shape-effects-on-drag/ (free)
- Engineering Toolbox (friction, conductivity, convection, unit tables): https://www.engineeringtoolbox.com/friction-coefficients-d_778.html and https://www.engineeringtoolbox.com/convective-heat-transfer-d_430.html (free, cross-check values)
- SolidWorks Simulation help, convection coefficient ranges: https://help.solidworks.com/2017/English/SolidWorks/cworks/c_Convection.htm (free)
- Motion Control Tips, inertia ratio and gear ratio sizing: https://www.motioncontroltips.com/how-do-i-determine-what-gear-ratio-i-need-for-servo-system/ (free)
- Oriental Motor technical FAQ on stepper surface temperature and insulation class: https://www.orientalmotor.eu/eu/support/faq/0191 and https://www.orientalmotor.eu/es/tech/glossary/sa26 (free)
- Lin Engineering 417 series NEMA 17 datasheet (max case temp): https://www.linengineering.com/products/stepper-motors/hybrid-stepper-motors/417-series/417-11-03 (free)
- RepRap wiki, NEMA motors: https://www.reprap.org/wiki/NEMA_Motor (free)
- SKF bearing friction estimation (constant μ method): https://www.skf.com (search "estimating the frictional moment") (free)
- Klipper documentation, resonance compensation / input shaping: https://www.klipper3d.org/Resonance_Compensation.html (free)
- Gates GT2 / PowerGrip design manuals (belt stiffness, teeth in mesh): https://www.gates.com (free PDFs)
- ITF Rules of Tennis, ball specification (rebound test): https://www.itftennis.com (free)
- Volupe drag coefficient summary (from White): https://volupe.com/support/c_d-and-c_l-calculation/ (free)

Books (not free):

- Hibbeler, *Engineering Mechanics: Statics* and *Dynamics* (FBDs, friction, wedges, screws).
- Meriam and Kraige, *Engineering Mechanics* (alternative to Hibbeler).
- Budynas and Nisbett, *Shigley's Mechanical Engineering Design* (screws, bearings, shafts).
- Rao, *Mechanical Vibrations*; Den Hartog, *Mechanical Vibrations* (Dover reprint, inexpensive).
- Incropera et al., *Fundamentals of Heat and Mass Transfer*.
- White, *Fluid Mechanics*.
- Slocum, *Precision Machine Design* (stiffness, error budgets).
- Oberg et al., *Machinery's Handbook* (tables; summarise, do not copy).

---

## 12. Gaps / not verified

- Plastics friction coefficients (PLA, PETG, acetal, TPU on various surfaces) are [est] from widely
  quoted ranges; not cross-checked against two primary sources this session. Measure on the real
  parts (incline test: tan of slip angle = μs).
- SKF bearing μ constants are from memory of the SKF catalogue; the SKF web page could not be read
  during research. Seal drag values for 608-2RS are estimates.
- Damping ratios for 3D-printed structures and belt axes are estimates; no published dataset found.
- Stepper inertia-ratio guidance is extrapolated from servo practice; no vendor stepper-specific
  limit was verified.
- Stepper resonance band (1–3 rev/s) and rotor natural frequency formula k_θ ≈ T_hold·N_r are
  approximations; real values depend on driver, current and microstepping.
- Motor heating example uses a convection-only model; real case temperature depends strongly on
  conduction into the mount. Not measured.
- Plastic Tg/HDT and practical limits vary by brand and grade; check the filament datasheet.
- Coefficient of restitution values other than the ITF tennis-ball spec are estimates.
- Tennis ball C_d, foam ball terminal speed and drag ratios are computed from assumed C_d values.
- Belt working tension, motor shaft radial load limits, screw pull-out into plastic, and wire ampacity
  are rough estimates; use vendor data for final design.
- Pneumatic and vacuum safety factors are paraphrased from general vendor practice (SMC, Festo,
  Schmalz) without a specific document fetched.
