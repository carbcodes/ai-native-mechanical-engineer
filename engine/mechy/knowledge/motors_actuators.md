# Motors, actuators and drive sizing

Reference for Mechy agents (concept, cad, sim, controls). Read it before choosing a motor, gear
ratio, driver or supply for any joint or axis. SI units throughout. Every number is labelled:
**[DS]** datasheet/manufacturer, **[typ]** typical value across several sources, **[est]** estimate
or rule of thumb, **[calc]** computed here. Sources are cited inline by short tag, full list at end.

---

## 0. The 12 rules a senior engineer would tell you first

1. **Size on torque at speed, not holding torque.** A stepper's holding torque is a zero-speed number.
   At your operating speed you may have 30-70% of it. Always read the pull-out curve for *your*
   supply voltage and driver.
2. **Load torque = gravity + inertia x acceleration + friction.** Worst case: gravity is at its
   maximum (link horizontal) while you are accelerating. Check that case.
3. **Apply a 50% safety margin** on required torque (Mechy standard: available >= 1.5 x required).
   For open-loop steppers it is non-negotiable: a stepper that runs out of torque loses position silently.
4. **Gear ratio trades speed for torque, and divides reflected inertia by N².** Pick N so that the
   motor runs in the flat (torque-rich) part of its curve and the inertia ratio is sensible.
5. **Inertia ratio J_load/N² : J_rotor <= 10:1** is the normal target for steppers and servos
   (Parker, Sanyo Denki). Above ~10 expect ringing and tuning problems; above ~30 with a stepper,
   expect missed steps unless the system is very stiff and well damped. [est]
6. **Supply voltage sets top speed; current sets torque.** Steppers need high voltage relative to
   their rated voltage (24-48 V for NEMA 17/23) to keep torque at speed.
7. **Most transmissions are not self-locking.** Belts, planetaries and spur gears back-drive. If
   power is lost, a gravity-loaded arm falls. Plan a brake, counterbalance, worm/lead screw, or
   accept it explicitly.
8. **Thermal limit is RMS torque, not peak.** Peak torque is limited by saturation/driver current;
   continuous torque by heat. Compute RMS over the duty cycle.
9. **Hobby servo "stall torque" is not usable torque.** Plan on <= 30-50% of the label for
   continuous holding, and less for a cheap analog servo. [est]
10. **Put motors at the base.** Mass on a distal link costs torque at every joint behind it
    (gravity x lever arm) and adds inertia ∝ r². (Mechy standards rule 3.)
11. **Drivers are rated by board, not chip.** A TMC2209 chip says 2 A RMS; a stick module without
    airflow reliably gives ~1.2-1.5 A RMS. A4988 modules ~1 A without a heatsink.
12. **Verify against a closed-form result** before trusting a sim or spreadsheet. The worked example in
    section 10 includes a verification table pattern to copy.

---

## 1. Quick selection table: which actuator family?

| Need | First choice | Why | Avoid |
|---|---|---|---|
| Hobby/3D-printed arm joint, position control, low cost | NEMA 17/23 stepper + belt/planetary reduction + TMC driver | Cheap, simple, holds position with no encoder (open loop) | Direct-drive stepper on a heavy joint |
| Must never lose position silently | Closed-loop stepper or BLDC/servo with encoder | Detects/corrects missed steps | Plain open-loop stepper without homing |
| Smooth, fast, back-drivable, force control (legs, haptics, cobot) | BLDC + FOC (ODrive, moteus, SimpleFOC) + low ratio (QDD, 6-10:1) | High torque bandwidth, transparency | High-ratio worm/harmonic if back-drivability matters |
| Small robot, many joints, minimal wiring | Smart serial servo (Dynamixel, Feetech STS) | Integrated gearbox, encoder, driver, daisy chain | MG996R-class PWM servos for anything precise |
| Toy/quick prototype, light load, 180° travel | PWM hobby servo (SG90, MG996R) | Trivial to drive | Precision, continuous load, feedback needs |
| Continuous rotation, constant speed, cheap | Brushed DC gearmotor (N20, 37 mm, 25GA) | Cheap, easy speed control with H-bridge | Precise positioning without encoder |
| Short-stroke push/pull, on/off | Solenoid | Fast, cheap, simple | Proportional or long-stroke motion |
| Linear push with moderate force, slow | Lead-screw linear actuator (Actuonix L16, 12 V "linear actuator") | Self-locking, integrated | High speed, high duty cycle |
| Fast linear on/off, high force, factory air available | Pneumatic cylinder | Very high force/weight, cheap cylinders | Mid-stroke positioning, no air supply |
| Gravity-loaded joint that must hold with power off | Worm gear, lead screw, or motor with brake | Self-locking | Belts/planetary without brake |

---

## 2. Stepper motors

### 2.1 How they work (enough to reason with)
- Hybrid stepper: permanent-magnet rotor with 50 teeth -> **200 full steps/rev (1.8°)** is the common
  standard; 0.9° (400 steps) motors exist with finer resolution but lower top speed. [typ]
- Two phases (bipolar, 4 wires). Torque ∝ phase current until magnetic saturation.
- Torque vs rotor angle error is roughly sinusoidal: maximum restoring torque occurs at **1 full step
  (1.8°) of lag**. If the load needs more than the peak, the rotor slips to the next stable point
  -> missed steps in multiples of 4 full steps (one electrical cycle). [typ, Zaber/Iowa tutorial]
- Open-loop: the controller assumes the rotor followed the command. Nothing detects slip.

### 2.2 Frame sizes (NEMA ICS 16 face size)

NEMA number = face size in tenths of an inch. Values below are *typical* for common models; check the
exact part's datasheet (torque varies 2-3x with stack length).

| Frame | Face | Typical body lengths | Holding torque range | Typical rated current | Rotor inertia | Mass | Mounting |
|---|---|---|---|---|---|---|---|
| NEMA 8 | 20 mm | 28-38 mm | 0.02-0.04 N·m | 0.6 A | ~2-4 g·cm² | 60 g | M2, 16 mm BC |
| NEMA 11 | 28 mm | 32-51 mm | 0.06-0.12 N·m | 0.67-1 A | ~9-18 g·cm² | 110-200 g | M2.5, 23 mm square |
| NEMA 14 | 35 mm | 20-52 mm | 0.08-0.4 N·m (common ~0.18) | 0.4-1.5 A | ~14-25 g·cm² | 150-250 g | M3, 26 mm square |
| NEMA 17 | 42.3 mm | 20-60 mm | 0.15-0.65 N·m (common 0.40-0.45) | 1-2.5 A (common 1.5-2 A) | 35-110 g·cm² (common ~54) | 150-500 g (common 280 g) | M3, 31 mm square, 22 mm pilot, 5 mm shaft |
| NEMA 23 | 57 mm | 41-112 mm | 0.4-3 N·m (common 1.26-1.9) | 2-4.2 A | 120-800 g·cm² (common ~300) | 0.45-1.4 kg | M5 / Ø5.1 holes, 47.14 mm square, 38.1 mm pilot, 6.35 or 8 mm shaft |
| NEMA 34 | 86 mm | 65-150 mm | 3-12 N·m | 4-6 A | 1000-4000 g·cm² | 1.7-5 kg | Ø5.5 holes, 69.6 mm square, 73 mm pilot, 14 mm shaft |

Sources: [Pimoroni NEMA table], [HANPOSE 17HS catalog], [StepperOnline listings]; ranges [typ].

**Reference motors** (cross-checked across multiple listings; minor spread between vendors):

| Part | Holding | Current | R/phase | L/phase | Rotor J | Notes |
|---|---|---|---|---|---|---|
| 17HS4401 (NEMA 17, 40 mm) | 0.40 N·m | 1.7 A | 1.5 Ω | 2.8 mH | 54 g·cm² = 5.4e-6 kg·m² | The default 3D printer motor [DS HANPOSE; some listings 43 N·cm] |
| 17HS19-2004S1 (NEMA 17, 48 mm) | 0.59 N·m | 2.0 A | 1.4 Ω | 3.0 mH | 82 g·cm² | [typ, StepperOnline-class] |
| NEMA 14 35 mm (Pimoroni) | 0.18 N·m | 1.0 A | 2.7 Ω | 4.0 mH | 14 g·cm² | Wide spread between models (0.08-0.25 N·m) |
| 23HS22-2804S (NEMA 23, 56 mm) | 1.26 N·m | 2.8 A | 0.9 Ω | 2.5 mH | 300 g·cm² = 3.0e-5 kg·m² | [DS-class listing, Pimoroni table] |

Unit conversions: 1 N·m = 100 N·cm = 10.2 kgf·cm = 141.6 oz·in. 1 g·cm² = 1e-7 kg·m².

### 2.3 Holding, detent, pull-in and pull-out torque
- **Holding torque**: max static torque with rated current in both phases (full-step position). Zero speed.
- **Detent torque**: torque with motor unpowered (magnet cogging), typically ~2-5% of holding. [est]
  Too small to hold a gravity load.
- **Pull-out torque curve**: max torque the motor can deliver *while running* at a given speed without
  losing sync. **This is the sizing curve.** It depends on driver, supply voltage, current, microstep
  mode and coupling/load inertia; vendor curves are measured at a stated voltage - re-read them for yours.
- **Pull-in torque**: max torque to start/stop instantly from rest without ramping. Lower than pull-out;
  only relevant if you do not ramp. Always ramp (trapezoid or S-curve).

**Shape of the pull-out curve** (constant-current chopper driver):
1. Low-speed region: torque ≈ 70-90% of holding (microstepping and real-world losses). [est]
2. A **corner speed** where the winding inductance stops the current reaching its set value within a step.
3. Above the corner: torque falls roughly ∝ 1/speed (constant power region), then drops off a cliff.

**Corner speed rule of thumb** (current must reverse from -I to +I each full step):

```
f_corner [full steps/s] ≈ V_supply / (2 · L · I)
ω_corner [rev/s]        ≈ f_corner / 200       (1.8° motor)
```
V in volts, L phase inductance in henries, I phase current in amps. [est; crude, ignores back-EMF]

Examples [calc]: 17HS4401 (2.8 mH, 1.7 A): 24 V -> ~2520 steps/s ≈ 12.6 rev/s; 12 V -> ~6.3 rev/s.
23HS22-2804S (2.5 mH, 2.8 A): 24 V -> ~8.6 rev/s; 36 V -> ~12.9 rev/s; 48 V -> ~17 rev/s.

**Crude available-torque model for early sizing** (replace with the real curve before committing):

```
T_avail(ω) ≈ 0.7 · T_hold                     for ω ≤ ω_corner
T_avail(ω) ≈ 0.7 · T_hold · ω_corner / ω      for ω > ω_corner   (valid up to ~2-3x ω_corner)
```
[est; conservative-ish for TMC/SpreadCycle drivers at rated current; StealthChop at high speed is worse]

**Maximum useful supply voltage** (Geckodrive rule): `V_max ≈ 32 · sqrt(L_mH)` volts.
17HS4401: 32·√2.8 ≈ 54 V. 23HS22: ≈ 51 V. Going above this mostly adds heat (iron losses). [est, Geckodrive]
Practical: NEMA 17 at 24 V is the 3D printer norm; 36-48 V buys speed if the driver supports it
(TMC2209 max 29 V does **not**; TMC5160/TMC2160 does).

### 2.4 Microstepping: what it really buys you
- Driver sets phase currents to sin/cos of the target angle, so the rotor can sit between full steps.
- **Benefits**: smoother motion, less noise, less low-speed resonance, finer *commanded* resolution.
- **Reality**: microsteps are not accurate positions under load. Incremental torque for moving one
  microstep is:

```
T_inc = T_hold · sin(90° / μ)        μ = microsteps per full step
```

| Microstep | Incremental torque / holding [calc] |
|---|---|
| 1 (full) | 100% |
| 2 | 70.7% |
| 4 | 38.3% |
| 8 | 19.5% |
| 16 | 9.8% |
| 32 | 4.9% |
| 256 | 0.6% |

  Meaning: with 1/16 microstepping, any load torque (or friction) above ~10% of holding stops the rotor
  from moving a single microstep - it only moves once the error accumulates. [Machine Design "Microstepping
  myths"; MPS app note "Why microstepping isn't as good as you think"]
- **Accuracy**: typical hybrid steppers are ±3-5% of a full step static angle error unloaded
  (±0.05-0.09° on a 1.8° motor) and microstep linearity error is often larger than one 1/16 step. [typ]
- Microstepping does **not** reduce available torque at the full-step level much (sin/cos keeps vector
  magnitude ≈ constant; peak per-phase current = rated, so torque ≈ 70-100% of full-step holding). [typ]
- **Rule**: use 1/16 (with TMC "interpolation to 1/256" for quietness) as the default. Do not count on
  resolution finer than ~1/4-1/8 step for positioning; if you need finer real resolution, add gear
  reduction or an encoder.
- Step-rate limit: microcontroller step generation. At 1/16 and 15 rev/s: 200·16·15 = 48 kHz pulse rate.
  Arduino-class AccelStepper tops out ~4-10 kHz; Klipper/grbl on 32-bit MCUs ~100+ kHz. [est]

### 2.5 Resonance
- Rotor + load is a mass-spring system (magnetic stiffness). Two problem zones [Geckodrive, Dover Motion]:
  1. **Low-speed resonance**: ~1-3 rev/s for unloaded NEMA 17 (natural frequency ~100-200 Hz full-step
     rate). Rough, noisy, can stall. **Cure: microstepping, add load inertia/damping, ramp through it.**
  2. **Mid-band instability**: typically **5-15 rev/s** (1200-3000 full steps/s). Oscillation builds over
     0.5-10 s and stalls the motor even with ample torque on paper. Caused by extra phase lag when the
     drive goes voltage-limited. **Cure: driver with mid-band damping (TMC SpreadCycle with good
     tuning, Gecko, closed-loop drivers), elastomer coupling, friction, or avoid dwelling there.**
- Symptoms: motor stalls at a specific constant speed but accelerates through it fine.
- Belts help (they add compliance and damping); rigid direct coupling to a low-friction load is worst.

### 2.6 Missed steps: causes and defences
Causes: insufficient torque at speed; acceleration too high (J·α); resonance; driver overheating
(thermal foldback, e.g. TMC "otpw" then shutdown); supply sag; step pulses too fast/jittery; mechanical
binding at one point of travel; inertia ratio too high; StealthChop at high speed/load.

Defences, cheapest first:
1. 50% torque margin on the *pull-out* curve, at the real supply voltage.
2. Conservative acceleration with S-curve or trapezoid ramp; tune max accel to ~50-70% of the value
   where steps are first lost in test. [est]
3. Home every power-up (limit switch or sensorless) and re-home periodically for long runs.
4. Use SpreadCycle (not StealthChop) for loaded/high-speed axes.
5. Closed loop (encoder on motor or joint) where losing position is unacceptable.

### 2.7 Current, voltage, heat
- Steppers are **current-driven**. Rated voltage on the label (e.g. 2.55 V = 1.5 Ω x 1.7 A) is irrelevant
  for chopper drivers; supply is typically 5-20x rated voltage.
- Set driver current to ≤ rated phase current. TMC drivers take **RMS** current; peak = RMS x √2.
  17HS4401 rated 1.7 A (peak, per datasheet convention, check) -> set ~1.2 A RMS in Klipper. Many printer
  NEMA 17 run at 0.8-1.2 A RMS. [typ]
- Copper loss at standstill ≈ 2 · I² · R (both phases). 17HS4401 at 1.7 A: 2·1.7²·1.5 ≈ 8.7 W [calc].
- Steppers are rated for a case temperature rise ~80 °C at rated current (class B insulation, 130 °C).
  A stepper at 60-80 °C case is normal; PLA mounts soften at ~55-60 °C -> use PETG/ABS/ASA/PC near motors
  or a metal mount/spacer. [typ]
- **Hold current reduction** (TMC IHOLD, e.g. 50-70% of run current) cuts idle heat by 50-75% but also
  cuts holding torque proportionally - check gravity joints.
- Supply current: a chopper is a buck converter, so supply current < phase current. Budget PSU watts =
  sum over axes of (mechanical power + copper loss), ~20-40 W per loaded NEMA 17, 40-80 W per NEMA 23. [est]

### 2.8 Closed-loop steppers
- Stepper + encoder (usually 14-bit magnetic, 16384 counts/rev, e.g. AS5047/MT6816) + driver that
  corrects position error or runs FOC on the stepper.
- Examples: MKS SERVO42C/42D/57D (NEMA 17/23, 12-24 V, ~3 A, step/dir, UART/RS485/CAN), BTT S42C,
  StepperOnline CL57T / "hybrid servo" kits, Leadshine HBS. [listing-level data; MKS manual not verified]
- What you gain: no silent missed steps (it alarms or recovers), current scales with load (cooler,
  quieter), can run nearer to the torque curve (smaller margin, ~20-30% instead of 50%).
- What you do not gain: more peak torque. Physics of the motor is unchanged.
- Note: encoder is on the motor shaft, so belt stretch/backlash after the motor is still unseen. For true
  joint position, put an encoder (AS5600/AS5048) on the joint output.

---

## 3. Stepper drivers

| Driver | Supply | Current (board, realistic) | Microsteps | Interface | Key features | Use when |
|---|---|---|---|---|---|---|
| A4988 (Allegro; Pololu carrier) | 8-35 V | ~1 A/phase no heatsink; 2 A with good cooling | 1-16 | Step/dir, pins | Cheap, noisy, ~1/16 max | Legacy only; replace with TMC2209 |
| DRV8825 (TI) | 8.2-45 V | ~1.5 A/phase no heatsink; 2.2 A with cooling | 1-32 | Step/dir, pins | Higher V; known low-current decay issues on some motors | Cheap 36 V NEMA 17 axis |
| TMC2208/2209 (Trinamic/ADI) | 4.75-29 V | Chip 2 A RMS (2.8 A peak); stick module ~1.2-1.5 A RMS realistic | to 1/256 (interpolated) | Step/dir + 1-wire UART | StealthChop2 (silent), SpreadCycle, StallGuard4 (2209), CoolStep | Default for NEMA 17 at 12-24 V |
| TMC2130/5160 | TMC5160: 8-60 V | External MOSFETs: board-dependent, typically 3-4.4 A RMS modules (chip up to ~20 A with right FETs) | to 1/256 | SPI (5160 also has motion controller) | StallGuard2, CoolStep, SpreadCycle tuning | NEMA 23, 36-48 V, high speed |
| TMC2160 | 8-60 V | as TMC5160 | to 1/256 | SPI + step/dir | 5160 without motion controller | Same as 5160 |
| External "DM542/DM556" | 20-50 V DC | 1-4.2 A peak | DIP | Opto step/dir | Robust, anti-resonance | NEMA 23/34 CNC |

Sources: [TMC2209 DS rev1.08], [Pololu A4988 #1183, DRV8825 #2133], [TMC5160 distributor listings, BTT wiki].

### 3.1 Trinamic modes (what to configure)
- **StealthChop2**: voltage-mode PWM, near-silent. Great for low speed/light load. Loses torque and can
  lose steps at high speed/high acceleration. 
- **SpreadCycle**: current-mode chopper, full dynamic torque. Use for loaded robot joints.
- **TPWMTHRS** / Klipper `stealthchop_threshold`: switch speed from StealthChop to SpreadCycle. Klipper docs
  recommend **not switching mid-motion** - pick one mode per axis. [Klipper TMC_Drivers.md]
- **CoolStep**: reduces current at light load using StallGuard measurement (saves heat).
- **IHOLD/IRUN/IHOLDDELAY**: standstill current reduction.

### 3.2 StallGuard sensorless homing
- Driver measures back-EMF-related load signal; when the motor stalls against a hard stop, DIAG pin fires.
- TMC2209 = StallGuard4 (works in **StealthChop**); TMC2130/5160 = StallGuard2 (works in **SpreadCycle**).
- Needs a **minimum speed** (back-EMF must be measurable) - homing speed of roughly 20-60 mm/s on a belt
  axis / ~1-3 rev/s at the motor is typical; too slow and it false-triggers or never triggers. [est, Klipper community]
- Tune threshold (SGTHRS on 2209: higher = more sensitive; SGT on 5160: lower = more sensitive) per axis,
  one axis at a time.
- **Limitations for robot arms**: unreliable through high reductions (load signal is diluted by N),
  under gravity load, or with soft/compliant hard stops. Stalling into a stop at speed also stresses
  printed parts. **For arm joints with N > ~5, prefer a physical switch or Hall/optical sensor**
  (e.g. A3144 Hall + magnet, TCST2103 optical interrupter, microswitch). [est]

### 3.3 Driver selection rules
1. Driver continuous RMS rating (board-level, with your cooling) ≥ 1.2 x set motor RMS current.
2. Driver max voltage ≥ 1.2 x supply (regen spikes during decel). TMC2209 at 24 V is fine; never 29 V.
3. Add bulk capacitance near the driver (≥100 µF low-ESR per driver, voltage rating ≥ 1.5 x supply). [typ]
4. Never connect/disconnect a motor while the driver is powered - it destroys drivers.

---

## 4. BLDC motors and FOC

### 4.1 Motor constants (memorise)
```
Kv [rpm/V]   : no-load speed per volt
Kt [N·m/A]   : torque per amp of phase current
Kt ≈ 60 / (2π · Kv) = 9.55 / Kv      (consistent SI definition)
Kt ≈ 8.27 / Kv                       (ODrive convention: Kv from line-to-line, current as phase amplitude)
Ke [V·s/rad] = Kt (in SI, same number)
Km [N·m/√W]  = Kt / sqrt(R)           motor constant: torque per sqrt(copper loss) - best figure of merit
T  = Kt · I
P_copper = 1.5 · I² · R_phase (or ≈ I² · R_line-line for FOC with I as peak phase current, convention-dependent)
```
[ODrive docs/forum; Bodine "motor constants"; check conventions on each datasheet - the 9.55 vs 8.27
factor is a √3/2 convention difference, so a measured Kt may sit anywhere between them]

Examples [calc]: 100 Kv -> Kt ≈ 0.083-0.096 N·m/A. 270 Kv -> ≈ 0.031-0.035 N·m/A.
So a 100 Kv motor needs ~30 A for 2.5 N·m.

- **Low Kv ≠ more torque per watt.** Kv mostly sets the voltage/current trade. Torque per watt (Km) comes
  from size: Km grows with copper/iron volume. For a given motor frame, rewinding to lower Kv just means
  more turns: higher Kt, higher R, same Km.
- **Torque scales with rotor diameter² x stack length** (air-gap shear stress x area x radius). Hence
  "pancake" motors (large diameter, short) for joints. [typ, Katz thesis]

### 4.2 Motor types
| Type | Kv | R/phase | Driving | Typical use |
|---|---|---|---|---|
| Drone/RC outrunner (2204-5010) | 300-2500 | 0.05-0.5 Ω | ESC (no position) or FOC current mode | Props, not joints, unless heavily geared |
| Gimbal motor (GM2804, GM4108H-120T, GM5208) | 20-100 | 5-15 Ω | **FOC voltage mode** fine (low current) | Smooth slow direct drive, camera gimbals, small low-torque joints |
| Robot-joint pancake BLDC (T-motor U8/ antigravity 8108, Eaglepower 90 Kv, MAD M6C12) | 50-150 | 0.05-0.2 Ω | FOC current mode, 24-48 V, 20-40 A | QDD actuators, legged robots |
| Integrated joint actuator (CubeMars AK series, MyActuator RMD-X, MIT-style) | - | - | CAN, built-in FOC + planetary | Drop-in QDD joints |

GM4108H-120T reference: R ≈ 11.1 Ω, rated 20 V, load torque ~0.12-0.18 N·m, 124 g. [DS iFlight listing; RPM figures
conflict between vendors]. Gimbal motors are *weak*: 0.1-0.3 N·m. Great for smoothness, not for lifting.

### 4.3 FOC controllers
| Controller | Bus V | Current | Encoder | Interface | Notes |
|---|---|---|---|---|---|
| ODrive S1 | 12-48 V (max rec. 50.5 V) | 40 A nominal / 80 A peak (peak derated with bus V; ~40 A at 48 V) | onboard magnetic + external | CAN, USB, UART, step/dir | Single axis, polished firmware [ODrive comparison table] |
| ODrive Pro | 12-56 V (max rec. 58 V) | 70 A nominal / 120 A peak (with heatsink + airflow) | external | CAN, etc. | High power |
| ODrive v3.6 (legacy, clones) | 24 or 56 V | ~40-60 A | external | USB/UART/CAN | Clones vary in quality |
| moteus r4/c1 (mjbots) | 10-44 V / 10-51 V | ~100 A peak (r4) | onboard | CAN-FD | Legged robots [not verified here] |
| SimpleFOC (library) + SimpleFOC Mini / Shield, B-G431B-ESC1 | 8-30 V typical | 1-5 A (mini) to ~20-40 A (B-G431) | AS5600/AS5047/MT6701 | Arduino/STM32 code | Cheap, educational; voltage mode for gimbals, current mode with sensing |
| VESC | 8-60+ V | 50+ A | Hall/encoder | UART/CAN | Vehicles; position control possible but less suited |

### 4.4 FOC essentials an agent must know
- Needs **rotor angle**: absolute magnetic encoder (AS5047P 14-bit, AS5600 12-bit I2C - slow, MT6701)
  or Hall sensors. Sensorless FOC does not work at zero speed - unusable for position-holding joints.
- Mount the diametric magnet on the motor shaft end, 0.5-2 mm gap, centred within ~0.25 mm. [typ, AMS DS]
- **Voltage mode** (no current sensing): set voltage, current ≈ (V - back-EMF)/R. OK only for high-R
  gimbal motors (>~5 Ω). **Current/torque mode** needs phase current sensing: required for low-R motors.
- Cascaded loops: current (~10-20 kHz) -> velocity (~1-8 kHz) -> position. Tune inner first.
- **Regen**: decelerating a BLDC pumps energy into the bus. With a battery that is fine; with a PSU
  you need a **brake resistor** (ODrive: required with PSU) or the bus overvoltage trips/kills the board.
- **Cogging**: can be compensated (ODrive anticogging calibration).
- Thermal: continuous torque limited by copper loss. Pancake BLDCs with no airflow: continuous current
  often ~1/3 of peak. [est]

### 4.5 Quasi-direct-drive (QDD) actuators
- **Definition**: high-torque-density BLDC + single low reduction (typically 6:1-10:1 planetary or belt).
- **Why**: back-drivable (low reflected inertia J·N², low friction), sense force through motor current
  (no torque sensor), high bandwidth, survives impacts. [Katz 2018 MIT thesis; Wensing et al. 2017 IEEE T-RO]
- Reference: MIT Mini Cheetah actuator - custom pancake BLDC, 6:1 planetary, ~17 N·m peak, ~0.5 kg. [Katz;
  peak figure from secondary source, primary not opened]
- Reflected motor inertia at the output = J_rotor·N². At 6:1 that is 36x; at 100:1 (harmonic) 10,000x -
  why high-ratio joints feel "stiff" and hit hard.
- Open-source references: OpenTorque actuator (cycloidal/planetary on 5010-8308 BLDC), Skyentific/Aaed
  Musa 3D-printed planetary QDD, Stanford Doggo (belt 3:1 on T-motor + ODrive), Berkeley Humanoid Lite.
- **QDD design rules** [est]:
  1. Ratio 6-10:1; beyond ~10:1 back-drivability drops fast.
  2. Motor 80-100 mm diameter for 10-25 N·m peak class.
  3. 24-48 V bus, 30-60 A peak.
  4. Output bearing must take the joint moment (crossed roller, or two angular-contact/deep groove widely spaced).

---

## 5. Brushed DC motors and gearmotors

```
T = Kt · I          ω = (V - I·R) / Ke          Kt = Ke (SI)
Stall torque T_s = Kt · V / R      No-load speed ω_0 ≈ V / Ke
Linear torque-speed line: T(ω) = T_s · (1 - ω/ω_0)
Max mechanical power at ω_0/2, T_s/2:  P_max = T_s · ω_0 / 4
Max efficiency at roughly 10-20% of stall torque. [typ, Maxon key info; Bodine]
```

- **Continuous rating ≈ the torque at max efficiency, typically ~10-25% of stall** [est]. Running near
  stall burns the motor in seconds-minutes.
- **Gearmotor ratings**: label "rated torque" is continuous; "stall torque" is short duration. Gearboxes
  often have a *gear strength* limit below motor stall x ratio - plastic/zinc spur gearboxes strip first.
- Common families: **N20** micro gearmotor (6-12 V, ~0.02-0.2 N·m rated by ratio), **25GA/JGA25-370**,
  **37 mm metal gearmotor** (Pololu 37D: 12 V, up to ~5 N·m stall at 100:1+), **Maxon/Faulhaber**
  (precision, real datasheets). Chinese listing torque values are frequently stall values or inflated. [est]
- Gearbox efficiency: spur ~0.9-0.95 per stage; planetary ~0.9-0.97 per stage; worm 0.3-0.7 (self-locking
  if efficiency < 0.5, roughly). [typ, KHK/maxon]
- Position control needs an encoder (quadrature Hall on motor shaft, e.g. 7-12 PPR x ratio) + PID + H-bridge
  (DRV8871 3.6 A, TB6612FNG 1.2 A/ch, BTS7960 ~40 A, L298N - obsolete, 2-4 V drop, avoid).
- Brushes wear (1000-3000 h typical for cheap motors) and make EMI: add 100 nF ceramic across terminals. [est]

---

## 6. Hobby and smart servos: real specs vs claims

### 6.1 Label torque is stall torque
"kg·cm" on a servo label = **stall torque** (max momentary, at stated voltage, motor drawing stall current).
ROBOTIS itself states stall torque differs from continuous output and real-world performance is closer
to the performance graph. Use:

```
Usable continuous torque ≈ 0.2-0.3 x stall   (cheap analog/digital PWM servos)   [est]
Usable continuous torque ≈ 0.3-0.5 x stall   (Dynamixel / quality smart servos, from N-T curves) [est]
Peak for short moves       ≤ 0.6-0.7 x stall                                       [est]
```

### 6.2 Reference servos

| Servo | Stall torque (label) | Voltage | Speed | Stall current | Feedback | Real-world notes |
|---|---|---|---|---|---|---|
| SG90 (micro, plastic) | 1.8 kg·cm (0.18 N·m) @4.8 V | 4.8-6 V | 0.1 s/60° | ~0.65 A | None (pot inside, not exposed) | Toy; clones far below spec; jittery |
| MG996R (metal gear) | 9.4 kg·cm @4.8 V, 11 kg·cm @6 V (0.92/1.08 N·m) | 4.8-7.2 V | 0.17 s/60° @4.8 V, 0.14 s/60° @6 V | 2.5 A @6 V | None | Large deadband (~5-10 µs ≈ 0.5-1°), clones common, overheats holding loads. Supply must deliver 2.5 A per servo [DS Tower Pro] |
| DS3218 (20 kg) | 19-21.5 kg·cm @5-6.8 V | 4.8-6.8 V | ~0.16 s/60° | ~2-3 A | None | Better than MG996R, same caveats [listing-level] |
| Feetech STS3215 (7.4 V class) | ~19.5 kg·cm @6 V peak (~1.9 N·m); rated ~6.5 kg·cm | 6-7.4 V | ~0.2 s/60° | ~2 A @6 V | 12-bit magnetic encoder (4096/rev), position/speed/load/temp | Used in LeRobot SO-100/SO-101 arms. Several gear ratios (1/345, 1/191, 1/147) with different torque: check SKU. 12 V variant ~30 kg·cm [listings conflict] |
| Dynamixel XL430-W250-T | 1.5 N·m @12 V (1.4 A); 1.4 N·m @11.1 V | 6.5-12 V | 61 rpm @12 V | 1.4 A | 4096/rev magnetic, 258.5:1 | 57.2 g. Mostly plastic gears. Good mid-range [DS ROBOTIS e-manual] |
| Dynamixel XM430-W350 | ~4.1 N·m @12 V | 10-14.8 V | ~46 rpm @12 V | ~2.3 A | 4096/rev, metal gears, current sensing | Quality reference servo [from memory, not re-verified] |
| Dynamixel XM540-W270 | ~10.6 N·m @12 V | 10-14.8 V | ~30 rpm | ~4.4 A | as above | Shoulder-class servo [from memory, not re-verified] |

### 6.3 PWM hobby servo facts
- Signal: 50 Hz (20 ms period), pulse 1.0-2.0 ms nominal (many go 0.5-2.5 ms for 180°). Digital servos
  accept up to ~330 Hz.
- Internal pot: limited resolution (~0.5-1° effective), no feedback to your controller.
- Powering: never from an Arduino 5 V pin. Use a 5-6 V BEC/regulator sized for **sum of stall currents**
  (or at least 50% of it with good bulk capacitance, 470-1000 µF).
- They draw current to hold any load against gravity - heat accumulates; they can burn out holding
  a heavy arm still.

### 6.4 Smart serial servos
- Half-duplex TTL (Dynamixel X, Feetech STS/SCS) or RS485 bus at 1 Mbps; daisy chain; each has an ID.
- Readback of position, speed, load (current proxy), voltage, temperature. Torque limits and
  compliance settings available.
- Good for small arms (< ~0.5 kg payload at ~0.3 m with STS3215/XL430 class at the wrist, larger servos at
  shoulder). Shoulder joints often need 2 servos ganged or a 2:1-3:1 external reduction.
- Downside: motor mass on distal links (every servo is at its joint) - violates "motors at base"
  unless the arm is small. Estimate the payload penalty explicitly.

---

## 7. Solenoids, linear actuators, pneumatics

### 7.1 Solenoids
- Force is **strongly stroke dependent**: roughly ∝ 1/gap² - maximum when closed, low at full stroke.
  Datasheet force-stroke curves are the only reliable data. [typ]
- **Duty cycle** rating (e.g. 100%, 50%, 25%, 10%) sets allowed power; a 25% rated solenoid can take
  ~4x the continuous power for short pulses. Max on-time also specified (e.g. 30-120 s). [typ, Ledex/Johnson Electric]
- Push vs pull types; return spring is usually yours to add. Typical small (12 V, 0.5-1 A) open-frame:
  2-10 N at 2-5 mm, a few tens of N when closed. [est]
- Use **hit-and-hold**: full voltage to pull in, then PWM ~30-50% to hold (cuts heat 4-10x).
- Always a **flyback diode** across the coil (1N4007, or diode + zener for faster release). Drive with a
  logic-level N-MOSFET (e.g. IRLZ44N, AO3400 for small).

### 7.2 Electric linear actuators
- DC motor + gearbox + lead screw (self-locking for most, ACME or ~1-2 mm lead) or ball screw (not self-locking).
- Example Actuonix L16 (micro, 50/100/140 mm stroke) [DS Actuonix L16]:

| Gear | Peak power point | Max speed (no load) |
|---|---|---|
| 35:1 | 50 N @ 16 mm/s | 32 mm/s |
| 63:1 | 75 N @ 10 mm/s | 20 mm/s |
| 150:1 | 175 N @ 4 mm/s | 8 mm/s |

  Duty cycle ~20%. Variants: -P (pot feedback), -R (RC servo input), -S (limit switches).
- Generic "12 V 1000-1500 N" actuators: ~5-15 mm/s, 10-25% duty cycle, built-in limit switches, ~2-5 A.
- Lead-screw linear force from motor torque:

```
F = 2π · η · T / p         p = lead [m/rev], η = screw efficiency
η: ACME/trapezoidal 0.2-0.5 (self-locking if η < ~0.5);  ball screw 0.85-0.95  [typ, THK/Misumi]
Example [calc]: NEMA 17 0.3 N·m usable on T8x8 (lead 8 mm, η≈0.6): F ≈ 2π·0.6·0.3/0.008 ≈ 141 N
                on T8x2 (lead 2 mm, η≈0.35):                       F ≈ 330 N
```

### 7.3 Pneumatics basics
```
F_extend  = P · A_bore = P · π·D²/4
F_retract = P · π·(D² - d_rod²)/4
P in Pa (gauge). 6 bar = 0.6 MPa.
Example [calc]: 20 mm bore at 6 bar: 0.6e6 · π·0.02²/4 ≈ 188 N theoretical.
```
- **Load factor** (load / theoretical force): choose bore so load factor ≈ **≤ 0.5 for dynamic motion,
  ≤ 0.7 for slow/static clamping** [est; SMC sizing method, exact table not re-verified - SMC hydraulic
  data gives 60-80% slow, 25-35% fast].
- Shop air: 6-7 bar (0.6-0.7 MPa). Valves: 5/2 for double acting, 3/2 for single acting; solenoid
  valves 12/24 V DC.
- Speed control with **meter-out** flow controls on both ports. Cushioning at ends for speed > ~0.3 m/s.
- Pneumatics are naturally **end-to-end** devices. Mid-stroke positioning needs proportional valves and is
  hard; air compressibility makes position control spongy.
- Soft pneumatic actuators (PneuNets, McKibben muscles) are 0.3-1.5 bar devices; separate topic.
- Air consumption per cycle (free air) ≈ V_swept · (P_gauge + 1 bar)/1 bar, both strokes.

---

## 8. Actuator sizing workflow (the procedure)

Do these steps in order for each joint/axis. Record every number with its label.

### Step 1: Define the motion profile
- Required travel θ (rad) or s (m), move time t_move, dwell, cycles/hour.
- **Trapezoidal profile, 1/3 accel - 1/3 cruise - 1/3 decel** (good default, minimises max power for a given time):

```
ω_max = 1.5 · θ / t_move          α = ω_max / t_a = 4.5 · θ / t_move²     (t_a = t_move/3)
Triangular (no cruise): ω_max = 2θ/t_move,  α = 4θ/t_move²
```
- S-curve (jerk-limited) reduces vibration; peak α is ~1.5-2x the trapezoid for the same t_move.

### Step 2: Load torque at the joint (output side)
```
T_load = T_gravity + T_inertia + T_friction + T_external
T_gravity = g · Σ (m_i · r_i · cos φ)        worst case cos φ = 1 (link horizontal)
T_inertia = J_load · α
T_friction: bearings + seals + belt; estimate 0.02-0.2 N·m for small printed joints [est], or μ·F·r_bearing
```
- **Inertia of common shapes about the joint axis** (parallel axis: J = J_cm + m·d²):

| Shape | J about own centre | About one end / offset |
|---|---|---|
| Point mass m at r | - | m·r² |
| Slender rod, length L | m·L²/12 | m·L²/3 (about end) |
| Solid cylinder about axis, radius R | m·R²/2 | |
| Thin ring | m·R² | |
| Rectangular block a x b (axis ⊥ face) | m·(a²+b²)/12 | |
| Solid sphere | 2/5 · m·R² | |

- For a multi-link arm, evaluate the shoulder with the arm **fully extended horizontally** (max gravity
  and max inertia) unless the workspace forbids it.

### Step 3: Reflect to the motor through the gear ratio N (N = ω_motor/ω_joint > 1 for reduction)
```
ω_m = N · ω_joint
T_m,required = T_load / (N · η)  +  (J_rotor + J_gear_input) · α · N
J_reflected  = J_load / N²
Inertia ratio  R_J = J_reflected / J_rotor
```
- η: GT2/HTD belt stage 0.95-0.98; 3D-printed planetary stage 0.80-0.90; metal planetary 0.90-0.97;
  printed cycloidal 0.70-0.85; harmonic drive 0.65-0.85; worm 0.3-0.7 [typ/est; printed values are estimates].
- Include pulley/gear inertia on the motor side (a 20T GT2 aluminium pulley ≈ 1.5-3 g·cm², often negligible
  vs a NEMA 17 rotor; a large steel gear on the motor shaft is not).

### Step 4: Choose N
Conditions to satisfy simultaneously:
1. **Torque**: T_avail(ω_m) ≥ 1.5 · T_m,required (Mechy 50% margin).
2. **Speed**: ω_m,max within the motor's useful range (stepper: ideally ≤ ~1-1.5 x corner speed;
   BLDC: ≤ ~80% of Kv·V_bus·modulation_depth).
3. **Inertia ratio**: R_J ≤ 10 preferred (≤ 5 for snappy stepper moves, up to ~30 acceptable for slow,
   stiff, well-damped belt systems [est]).
4. **Resolution**: joint resolution = 360° / (steps_per_rev · N). Use the *full step* or *1/4 step* number
   for honest accuracy.
5. **Back-drivability** if needed: low N (≤ 10), efficient transmission.

- **Optimal ratio for pure inertial load** (max acceleration): N_opt = sqrt(J_load / J_rotor). This is the
  "inertia matching" ratio (R_J = 1). Real designs land below it because of speed limits, and above it
  when gravity dominates. [typ, standard mechatronics result]
- Typical results for 3D-printed arms with NEMA 17: base yaw 10-20:1, shoulder 20-50:1, elbow 10-30:1,
  wrist 3-10:1. [typ from open-source arms: BCN3D Moveo, AR4 (uses 10:1-50:1 gearboxes on NEMA 17/23),
  Thor, PAROL6]

### Step 5: Torque-speed check across the move
- Plot required motor torque vs motor speed for the whole profile (accel phase at increasing speed,
  cruise, decel). Overlay T_avail(ω)/1.5. Every point must sit below the line.
- Conservative shortcut: check (peak torque, peak speed) together. If that passes, the curve passes.

### Step 6: RMS torque and thermal check (BLDC, DC, servo)
```
T_rms = sqrt( Σ (T_i² · t_i) / t_cycle )      include dwell (gravity holding torque during dwell!)
Require T_rms ≤ T_continuous (at your ambient, mounting, airflow)
Copper loss P = (T_rms/Kt)² · R_phase-equivalent
ΔT_winding ≈ P · R_th (R_th winding-to-ambient from datasheet, K/W)
```
- Steppers at constant current dissipate ≈ the same heat whether loaded or not: thermal check is just
  "rated current, sufficient cooling, mount material tolerates 60-80 °C".
- Servos/BLDC holding a gravity load continuously = 100% duty at the holding torque. This is the case that
  burns hobby servos. Counterbalance (springs, counterweight) to cut holding torque.
- Duty cycle for intermittent devices (solenoids, linear actuators): on_time / (on_time + off_time) over
  the rated period (often 2-10 min).

### Step 7: Electrical budget
- Driver current ≥ required phase current with margin; supply voltage gives required speed; PSU power ≥
  sum of axis powers (simultaneous moves) x 1.3. Add regen handling for BLDC (brake resistor).
- Wiring: 22 AWG OK to ~2-3 A for motor leads; 18 AWG for 5-10 A. [typ]

### Step 8: Failure modes and holding
- Power loss: does the joint fall? Back-drive torque at motor = T_gravity · η_back / N. Compare to detent
  (stepper ~2-5% holding) or no-power friction. If it falls: brake, counterbalance, self-locking stage,
  or a mechanical rest position.
- Collisions/stalls: torque limit (servo/BLDC current limit), slip clutch, or accept damage to printed parts.
- Endstop/homing method chosen and listed in BOM.

### Step 9: Record a verification table
```
| Check                         | Expected | Got | PASS/FAIL |
| T_avail/T_req at peak speed   | ≥ 1.5    |     |           |
| Inertia ratio                 | ≤ 10     |     |           |
| Motor speed vs corner         | ≤ 1.5x   |     |           |
| T_rms vs T_cont (servo/BLDC)  | ≤ 1.0    |     |           |
| Hand calc vs sim peak torque  | ±5%      |     |           |
```

---

## 9. Decision tables

### 9.1 Stepper vs BLDC/servo vs smart servo for a joint

| Criterion | Stepper (open loop) | Closed-loop stepper | BLDC + FOC | Smart servo |
|---|---|---|---|---|
| Cost per joint (motor+driver) | $15-40 | $40-80 | $80-300 | $15-50 (STS) / $50-300 (Dynamixel) |
| Position without encoder | Yes (until it slips) | Encoder built in | Needs encoder | Built in |
| Torque at low speed per $ | Excellent | Excellent | Good | Fair |
| High speed torque | Poor (falls with speed) | Poor | Excellent | Fixed by gearbox |
| Back-drivable / force control | No (with gearing) | Limited | Yes (low N) | Limited (high N) |
| Noise | Moderate (StealthChop quiet) | Quiet | Quiet | Gear whine |
| Heat at standstill | High (full current) | Lower | Load-proportional | Load-proportional |
| Complexity | Low | Low | High (tuning, regen) | Very low |
| Best for | Printed arms, gantries | Same, when missed steps are costly | Legged robots, cobots, haptics | Small arms, education |
[est; prices 2024-2026 hobby market, rough]

### 9.2 Reduction type for a printed arm joint (motor at base)

| Reduction | Typical N per stage | Backlash | Efficiency | Back-drivable | Notes |
|---|---|---|---|---|---|
| GT2 belt (6-9 mm) | 3-5 | Low (elastic) | 0.95-0.98 | Yes | Simple, quiet; limited by belt tension rating at high torque |
| HTD 5M / GT2 3M belt (15 mm+) | 3-5 | Low | 0.95-0.98 | Yes | For shoulder final stages |
| Printed planetary | 3-10 | 0.5-2° | 0.8-0.9 | Yes | Compact, coaxial |
| Printed cycloidal | 10-40 | Low (if well made) | 0.7-0.85 | Partly | High ratio in one stage; friction |
| Strain-wave (harmonic) | 30-160 | ~0 | 0.65-0.85 | Poorly | Expensive bought; printed versions experimental |
| Worm | 10-60 | Moderate | 0.3-0.7 | Usually no (self-lock) | Holds gravity loads with power off |
| Capstan (cable) | 5-15 | ~0 | 0.95+ | Yes | Smooth, backlash-free; needs careful tensioning |

---

## 10. Worked example: robot-arm shoulder joint

**Task (illustrative, numbers are estimates for a typical 3D-printed desktop arm):** 2-link arm, 0.45 m
reach, 0.5 kg payload. Motors at the base; elbow driven by belt from the base. Size the shoulder
(pitch) joint. Move: 90° in 1.0 s.

### 10.1 Mass properties [est]
| Item | Mass m (kg) | Distance from shoulder r (m) | Model |
|---|---|---|---|
| Upper arm link (L1 = 0.25 m) | 0.30 | 0.125 (COM) | slender rod |
| Elbow hardware (bearings, pulleys, idler) | 0.20 | 0.25 | point |
| Forearm link (L2 = 0.20 m) | 0.25 | 0.35 (COM) | slender rod |
| Wrist + gripper | 0.25 | 0.45 | point |
| Payload | 0.50 | 0.45 | point |

### 10.2 Gravity torque (arm horizontal) [calc]
```
Σ m·r = 0.30·0.125 + 0.20·0.25 + 0.25·0.35 + 0.25·0.45 + 0.50·0.45
      = 0.0375 + 0.050 + 0.0875 + 0.1125 + 0.225 = 0.5125 kg·m
T_g = 9.81 · 0.5125 = 5.03 N·m
```
Note: payload + wrist give 66% of it. Every 100 g at the wrist costs 0.44 N·m at the shoulder.

### 10.3 Inertia about the shoulder [calc]
```
Upper arm (rod about end):   0.30·0.25²/3                 = 0.00625
Elbow hw:                    0.20·0.25²                   = 0.01250
Forearm (rod, offset):       0.25·(0.20²/12 + 0.35²)      = 0.03146
Wrist+gripper:               0.25·0.45²                   = 0.05063
Payload:                     0.50·0.45²                   = 0.10125
J_load                                                    = 0.202 kg·m²
```

### 10.4 Motion profile [calc]
```
θ = π/2 = 1.571 rad, t_move = 1.0 s, trapezoid 1/3-1/3-1/3
ω_max = 1.5·1.571/1.0 = 2.356 rad/s (22.5 rpm at the joint)
α     = 4.5·1.571/1.0² = 7.07 rad/s²
```

### 10.5 Load torque [calc]
```
T_inertia = 0.202 · 7.07 = 1.43 N·m
T_friction = 0.10 N·m [est]
T_load,peak = 5.03 + 1.43 + 0.10 = 6.56 N·m   (gravity max while accelerating: conservative)
With 50% margin: T_design = 1.5 · 6.56 = 9.83 N·m at the joint
```

### 10.6 Try candidate motors and ratios [calc]
Assumptions: two belt stages, η = 0.90 total; crude T_avail model from §2.3 (0.7·T_hold flat to corner,
then ∝ 1/ω). Motor-side rotor acceleration term included (it is < 0.01 N·m here).

| Motor | N | T_m required (incl. 1.5x) | Motor speed | Inertia ratio | Corner @24 V / 36 V | T_avail @24 V / 36 V | Verdict |
|---|---|---|---|---|---|---|---|
| 17HS4401 (0.40 N·m) | 20 | 0.547 N·m | 7.5 rev/s | 94 | 12.6 / 18.9 rev/s | 0.28 / 0.28 | FAIL torque |
| 17HS4401 | 40 | 0.275 | 15.0 rev/s | 23 | 12.6 / 18.9 | 0.235 / 0.28 | FAIL @24 V; marginal @36 V (needs non-TMC2209 driver) |
| 17HS4401 | 60 | 0.184 | 22.5 rev/s | 10.4 | 12.6 / 18.9 | 0.16 / 0.235 | FAIL @24 V; PASS @36 V (1.28x) but 72 kHz step rate at 1/16 and not on TMC2209 |
| 23HS22-2804S (1.26 N·m) | 20 | 0.551 | 7.5 rev/s | 16.8 | 8.6 / 12.9 | 0.88 / 0.88 | PASS torque; inertia ratio high |
| **23HS22-2804S** | **30** | **0.371** | **11.25 rev/s** | **7.5** | 8.6 / 12.9 | 0.67 / 0.88 | **PASS (1.8x / 2.4x over requirement incl. margin)** |
| 23HS22-2804S | 40 | 0.282 | 15.0 rev/s | 4.2 | 8.6 / 12.9 | 0.50 / 0.76 | PASS but high step rate; slower top speed headroom |

**Selection**: NEMA 23 (23HS22-2804S class), N = 30, 36 V supply, TMC5160-class driver (TMC2209 max 29 V is
out) set to ~2.0 A RMS, SpreadCycle. At 24 V it still passes with 1.8x over the already-margined requirement.

### 10.7 Implement N = 30 with real parts [calc]
- Stage 1: GT2 20T (motor, 8 mm bore) -> 100T (Ø 63.7 mm pitch) = 5:1, 6 or 9 mm belt.
- Stage 2: GT2 16T -> 96T (Ø 61.1 mm pitch) = 6:1. Total 30:1.
- Stage 2 belt tension at peak: T_design / r = 9.83 / 0.0306 ≈ 320 N tight-side effective pull. That
  exceeds the comfortable working range of 6-9 mm GT2 (rough guide: low hundreds of N *breaking-adjacent*
  for 6 mm glass-fibre GT2; working tension far lower) [est - see belts knowledge file and Gates data].
  **Fix**: final stage HTD-5M 15 mm, or a larger output pulley (radius x2 halves force), or a printed
  planetary/cycloidal final stage. This is the kind of downstream check sizing must trigger.
- Joint resolution: 360°/(200·30) = 0.06° per full step; ~0.015° at 1/4 step. At r = 0.45 m: 0.47 mm per
  full step, 0.12 mm per quarter step. [calc]
- Step rate at 1/16: 200·16·11.25 = 36 kHz - needs a 32-bit MCU step generator (Klipper, grblHAL, FluidNC).

### 10.8 Static, holding and power-off checks [calc]
- Static gravity hold at the motor: 5.03/(30·0.9) = 0.19 N·m vs 1.26 N·m holding -> 6.7x. Hold current can
  be reduced to ~50% (still 3.3x). PASS.
- Power-off: back-driving torque at motor ≈ 5.03·0.95/30 ≈ 0.16 N·m vs detent ~0.03-0.06 N·m [est] -> **arm
  falls** when unpowered. Decision required: (a) gas spring / extension spring counterbalance (also cuts the
  gravity term ~70-90%), (b) NEMA 23 with 24 V brake, (c) worm final stage, (d) accept with a soft rest pose.
- Alternative design worth tabulating: **spring counterbalance cancelling 80% of T_g** -> T_load = 1.0 + 1.43 +
  0.1 = 2.53 N·m, T_design = 3.8 N·m. Then a 17HS4401 at N = 30 needs 0.14 N·m at 11.25 rev/s vs 0.28
  available at 24 V -> PASS, on a TMC2209. Inertia ratio 42 (high; accept only with stiff belts and slower
  acceleration, or raise N). A counterbalance often lets you drop a motor size.

### 10.9 Electrical [est]
- Mechanical peak at joint: 6.56 N·m · 2.356 rad/s ≈ 15.5 W. NEMA 23 copper loss at 2 A RMS: 2·(2.0)²·0.9 ≈ 7 W.
  Budget ~40-60 W per NEMA 23 axis including driver losses -> 36 V 10 A PSU for a 4-6 axis arm where not all
  axes peak together.

### 10.10 Verification table (example)
| Check | Expected | Got | PASS/FAIL |
|---|---|---|---|
| T_g by Σm·r vs CAD mass properties | within 5% | (run CAD) | - |
| J_load vs CAD inertia tensor about shoulder axis | within 10% | (run CAD) | - |
| Trapezoid: θ = ω_max·(t - t_a) | 1.571 rad | 2.356·0.667 = 1.571 | PASS |
| T_avail/T_m,req (NEMA 23, N=30, 24 V) | ≥ 1.0 (margin already in T_req) | 0.67/0.371 = 1.8 | PASS |
| Inertia ratio | ≤ 10 | 7.5 | PASS |
| Motor speed / corner speed (36 V) | ≤ 1.5 | 11.25/12.9 = 0.87 | PASS |
| Sim peak shoulder torque vs hand calc 6.56 N·m | within 5% | (run sim) | - |
| Pull-out curve from real datasheet at 36 V, 11.25 rev/s | ≥ 0.37 N·m | (read datasheet) | NOT VERIFIED |

---

## 11. Common mistakes (catch these in reviews)

1. Using holding torque at operating speed. Read pull-out at the actual voltage.
2. Forgetting the payload's lever arm effect on inner joints, or leaving wrist motors on the arm.
3. Using kg·cm as if it were N·m (factor 9.81/100). 1 kg·cm = 0.0981 N·m.
4. Gear ratio applied to inertia linearly instead of N².
5. Ignoring efficiency of printed gear stages (0.8 not 1.0).
6. Setting TMC current to the motor's peak rating as RMS (overdrives by 41%).
7. Running TMC2209 at > 28 V, or hot-plugging motors.
8. StealthChop on a heavily loaded axis -> missed steps at speed.
9. Expecting sensorless homing to work through 30:1 reductions under gravity.
10. Hobby servo powered from the MCU's 5 V rail; brown-outs reset the board.
11. BLDC on a bench PSU without a brake resistor -> overvoltage on decel.
12. Sizing to peak torque only and burning a servo/BLDC that holds gravity continuously (RMS check missing).
13. Assuming the arm holds itself when powered off.
14. Using microstep count as accuracy.
15. No margin for supply sag, temperature (winding resistance +40% at 100 °C reduces voltage headroom),
    and part-to-part variation.
16. PLA motor mounts next to 70 °C steppers creep and lose belt tension.
17. Belt/gear stage after the motor rated below the motor's peak x ratio: the transmission fails first.

---

## 12. Agent checklist (copy into notes)

- [ ] Motion profile defined (θ, t, profile shape, duty cycle).
- [ ] Worst-case pose chosen and justified.
- [ ] T_gravity, J_load, α, T_friction computed with units and labels.
- [ ] Gear ratio N chosen; inertia ratio, motor speed, joint resolution computed.
- [ ] T_avail at operating speed from the real pull-out curve (or crude model, labelled estimate).
- [ ] ≥ 1.5x margin on torque.
- [ ] RMS/thermal check (servo/BLDC/DC) or current + mount temperature check (stepper).
- [ ] Transmission strength (belt tension, gear tooth load) checked at peak output torque.
- [ ] Driver named, current and voltage within its board-level rating; supply V and W chosen.
- [ ] Power-off behaviour decided (brake/counterbalance/self-lock/accept).
- [ ] Homing method chosen (switch part number or sensorless with justification).
- [ ] Verification table filled; "Not verified" list includes any curve not read from a datasheet.

---

## 13. Useful formulas collection

```
Torque from force at radius:           T = F · r
Power:                                 P = T · ω         (W = N·m · rad/s)
rpm to rad/s:                          ω = rpm · 2π/60
Gear reduction N:                      T_out = T_in · N · η,  ω_out = ω_in / N
Reflected inertia:                     J_ref = J_load / N²
Belt/pulley pitch diameter (GT2):      D = teeth · 2 mm / π
Linear axis (belt) equivalent inertia: J_eq = m · r_pulley²
Lead screw equivalent inertia:         J_eq = m · (p / 2π)²
Lead screw force:                      F = 2π · η · T / p
Optimal (inertia-matched) ratio:       N_opt = sqrt(J_load / J_motor)
Stepper corner speed:                  f ≈ V / (2 L I) full steps/s
Stepper max useful voltage:            V ≈ 32 · sqrt(L_mH)
Microstep incremental torque:          T_inc = T_hold · sin(90°/μ)
BLDC Kt:                               Kt ≈ 8.27/Kv to 9.55/Kv  N·m/A
DC motor line:                         T(ω) = T_stall · (1 - ω/ω_0)
RMS torque:                            T_rms = sqrt(Σ T_i² t_i / t_cycle)
Pneumatic force:                       F = P · π D² / 4
Winding resistance vs temp (Cu):       R_T = R_20 · (1 + 0.00393 · (T - 20))
```

---

## Canonical references

Free unless noted.

**Courses and tutorials**
- MIT OCW 2.14 Analysis and Design of Feedback Control Systems; 2.12 Introduction to Robotics; 6.302 - motors,
  dynamics, control. https://ocw.mit.edu (free)
- Douglas W. Jones, "Control of Stepping Motors" tutorial, University of Iowa (classic, free).
  https://homepage.divms.uiowa.edu/~jones/step/
- Zaber, "Microstepping tutorial". https://www.zaber.com/articles/microstepping-tutorial (free)
- Geckodrive, "Step motor basics" guide (mid-band resonance, V = 32√L rule). https://www.geckodrive.com (free)
- Dover Motion, "Midrange resonance". https://dovermotion.com/midrange-resonance/ (free)
- Machine Design, "Microstepping myths". https://www.machinedesign.com/archive/microstepping-myths (free)
- Monolithic Power, "Why microstepping isn't as good as you think" (PDF app note). https://www.monolithicpower.com (free)
- Kollmorgen, "Motor inertia mismatch" white paper.
  https://www.kollmorgen.com/uploadedFiles/kollmorgencom/Service_and_Support/Knowledge_Center/White_Papers/KOL_MotorInertiaMismatch_Brief_08_12_10.pdf (free)
- Parker Motion KB, "Inertia ratio". https://parkermotion.atlassian.net/wiki/spaces/EIPKB1/pages/18841889/Inertia+Ratio (free)
- Sanyo Denki, allowable load inertia ratio. https://knowledge.sanyodenki.com/en/allowable-load-inertia-ratio-to-rotor-inertia (free)
- maxon "Key information on maxon DC motors / formulae" (in catalogue). https://www.maxongroup.com (free)
- Bodine Electric, "Introduction to motor constants" (PDF). https://bodine-electric.com (free)

**Datasheets and docs**
- Trinamic/ADI TMC2209 datasheet rev 1.08; TMC5160 and TMC2160A datasheets. https://www.analog.com (free)
- Pololu A4988 (#1183) and DRV8825 (#2133) carrier pages. https://www.pololu.com (free)
- Klipper TMC drivers documentation. https://www.klipper3d.org/TMC_Drivers.html (free)
- ODrive docs: comparison table, S1 datasheet, getting started (brake resistor). https://docs.odriverobotics.com (free)
- SimpleFOC docs and community. https://docs.simplefoc.com, https://community.simplefoc.com (free)
- ROBOTIS Dynamixel e-manual (XL430-W250, XM430, XM540). https://emanual.robotis.com (free)
- Feetech STS3215 datasheet (machine-translated PDF via Core Electronics). (free)
- Tower Pro MG996R datasheet (copies hosted by Cornell ECE). (free)
- Actuonix L16 datasheet. (free via RobotShop CDN)
- SMC pneumatic "Best Pneumatics" technical data / cylinder sizing. https://www.smcworld.com (free)
- HANPOSE 17HS series catalogue; Pimoroni NEMA comparison table (stepper reference values). (free)

**Papers and theses**
- B. Katz, "A Low Cost Modular Actuator for Dynamic Robots", MIT SM thesis, 2018. https://dspace.mit.edu/handle/1721.1/118671 (free)
- P. Wensing et al., "Proprioceptive Actuator Design in the MIT Cheetah", IEEE T-RO 2017 (paywalled; preprints exist).
- S. Seok et al., "Design principles for energy-efficient legged locomotion and implementation on the MIT Cheetah robot", IEEE/ASME T-Mech 2015 (paywalled).

**Books** (paid)
- Hughes & Drury, *Electric Motors and Drives*, 5th ed. (best plain-language motor book).
- Kenjo & Sugawara, *Stepping Motors and Their Microprocessor Controls*.
- Hanselman, *Brushless Permanent Magnet Motor Design*.
- Lynch & Park, *Modern Robotics* (free PDF from Northwestern: dynamics, actuation chapter). http://modernrobotics.org (free)
- Parker / Oriental Motor sizing handbooks (Oriental Motor "Motor sizing calculations" is free on their site).

**Open-source designs to anchor on**
- AR4 robot arm (Annin Robotics, NEMA 17/23 + gearboxes). BCN3D Moveo, Thor (Angel LM), PAROL6 (Source Robotics).
- LeRobot SO-100/SO-101 (Feetech STS3215). OpenTorque actuator, Stanford Doggo, Berkeley Humanoid Lite (QDD).

---

## Gaps / not verified

- **Pull-out curves**: the crude T_avail model in §2.3 is an estimate; no vendor pull-out curve for
  17HS4401 or 23HS22-2804S at 24/36 V was read. Worked-example verdicts depend on it - re-check against a
  real curve before committing.
- **Corner-speed formula** V/(2LI) ignores back-EMF and driver decay behaviour; it is an order-of-magnitude tool.
- **NEMA frame dimension columns** (bolt circles, pilot diameters, inertias for NEMA 8/11/34) are from memory
  and typical listings, not checked against NEMA ICS 16 directly.
- **Dynamixel XM430-W350 and XM540-W270** figures are from memory, not re-fetched. XL430-W250 was verified.
- **Feetech STS3215** torque/voltage pairings conflict across retailers (19.5 kg·cm quoted at both 6 V and
  7.4 V; multiple gear ratios). Verify per SKU.
- **MG996R** figures are datasheet-verified, but clones vary widely; real torque often lower.
- **Mini Cheetah 17 N·m peak** from a secondary source; Katz thesis PDF not opened.
- **MKS SERVO42D** specs from retailer listings (current and MCU conflict); manufacturer manual not read.
- **TMC5160 board-level current** depends on sense resistor and MOSFETs; 3-4.4 A RMS figure is for common
  stick modules (BTT), not the chip.
- **StallGuard minimum homing speed** values are community-derived estimates; TMC datasheet TCOOLTHRS/
  TPWMTHRS behaviour not reviewed in detail.
- **Pneumatic load-factor values** (0.5 dynamic / 0.7 static) are rules of thumb; SMC pneumatic table not
  directly verified (hydraulic table found instead).
- **Usable-vs-stall servo fractions** (0.2-0.5) are engineering estimates, not manufacturer data.
- **Printed gearbox efficiencies** (planetary 0.8-0.9, cycloidal 0.7-0.85) are estimates; measure on the build.
- **GT2 belt working tension** limits not quantified here; see belts/transmissions knowledge file and Gates data.
- **Kt convention** (8.27 vs 9.55 / Kv) depends on how each vendor defines Kv and current; measure Kt if
  torque accuracy matters.
- Prices in §9.1 are rough hobby-market estimates.
