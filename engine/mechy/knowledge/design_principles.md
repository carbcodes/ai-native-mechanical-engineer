# Principles of Good Mechanical Design: what to account for

Reference for Mechy agents (planner, research, concept, cad, sim, controls, docs). Read before designing.
Scope: the design process, constraint and stiffness, precision principles, DFM/DFA, serviceability,
failure modes, FMEA, safety factors, tolerances, cable routing, ergonomics, aesthetics, cost,
sustainability, machine and robot safety. Ends with a design-review checklist, beginner mistakes,
canonical references, and gaps.

Number labels used below:
- **[typ]** typical value seen across sources; fine for a first pass.
- **[est]** engineering estimate / rule of thumb; verify for anything critical.
- **[std]** taken from (or widely reproduced from) a standard; check the current edition before relying on it.
- Sources in brackets refer to "Canonical references" at the end.

---

## 0. The ten rules that matter most (TL;DR)

1. **Write requirements with numbers first.** "Light, strong, fast" is not a spec. "Payload 0.5 kg at 400 mm reach, repeatability ±0.5 mm, 90°/s joint speed, BOM < 300 USD" is.
2. **Design for stiffness, then check strength.** In mechanisms, deflection and resonance usually fail you before stress does.
3. **Constrain exactly.** Each part should have exactly the degrees of freedom it needs, held by exactly as many constraints. Overconstraint causes binding, preload you didn't design, and wear.
4. **Make the load path short, direct and visible.** Trace the force from the payload to the ground through every part and joint. Every joint in that path is a spring and a failure point.
5. **Keep the measuring/working point on the axis of the guide (Abbe).** Offset × angle error = position error.
6. **Mass off the moving links.** Motors at the base; drive distal joints by belt/linkage. Inertia scales with mass × distance².
7. **Fewer parts, self-locating, one-way-only assembly.** Every part you remove can't fail, can't be mis-assembled, and doesn't need to be bought.
8. **Design for the failure modes you can name:** fatigue, wear, loosening, creep, corrosion, overheating. Plastic parts creep; bolts in plastic loosen; aluminium against steel in salty air corrodes.
9. **Prototype the riskiest thing first,** cheaply, then measure. Verify every analysis against a closed-form or published result.
10. **Safety by design first, guards second, warnings last** (ISO 12100 order). No pinch point should accept a finger unless it can't hurt one.

---

## 1. The design process

### 1.1 Stages (and what each must produce)

| Stage | Output | Typical time share [est] | Failure if skipped |
|---|---|---|---|
| 1. Problem definition | Need statement, users, use cases, environment, constraints | 5–10% | Solving the wrong problem |
| 2. Requirements / spec | Numbered table: metric, target, threshold, how verified | 5–10% | No way to judge concepts; endless scope creep |
| 3. Research / benchmark | 3–5 existing solutions with numbers; open-source bases | 10% | Re-inventing worse versions of known designs |
| 4. Concept generation | 3+ distinct concepts (conventional first) | 10% | Anchoring on first idea |
| 5. Concept selection | Pugh then weighted matrix; recorded rationale | 5% | Arguing by taste |
| 6. Embodiment / layout | Architecture, load paths, part split, interfaces, error/torque/mass budgets | 20% | Late integration surprises |
| 7. Detail design | Part geometry, tolerances, materials, fasteners, BOM | 25% | — |
| 8. Prototype & test | Measured performance vs spec | 15%+ | Unknown real behaviour |
| 9. Iterate / release | Rev-controlled files, assembly instructions, test record | — | Unrepeatable build |

Rule of thumb: roughly 70–80% of lifecycle cost is committed by decisions made in concept and embodiment, while
only a small fraction is spent there [typ; widely cited in DFMA literature, e.g. Boothroyd et al.; exact figure varies].
"Rule of tens" [est]: a fix costs ~10x more at each later stage (concept → detail → prototype → production → field).

### 1.2 Requirements and specifications (with numbers)

A good requirement is **specific, measurable, verifiable, solution-neutral**.

Spec table template (use this in every design note):

| ID | Requirement | Metric | Target | Threshold (min acceptable) | Verification | Priority |
|---|---|---|---|---|---|---|
| R1 | Carry payload | mass at tool flange, full reach | 0.5 kg | 0.3 kg | Hang mass, hold 60 s, no stall | Must |
| R2 | Reach | radius from base axis to flange | 400 mm | 350 mm | CAD + tape measure | Must |
| R3 | Repeatability | ISO 9283-style, 30 cycles, 1 pose | ±0.5 mm | ±1 mm | Dial indicator | Must |
| R4 | Speed | joint 1 max | 90 °/s | 45 °/s | Encoder log | Should |
| R5 | Cost | BOM excluding tools | 250 USD | 350 USD | bom.csv sum | Must |
| R6 | Noise | 1 m, A-weighted | 50 dBA | 60 dBA | Phone SPL meter | Could |

Checklist of requirement categories (most designs forget 3 or more):
- Function: motion ranges, loads, speeds, accelerations, accuracy, repeatability, resolution, duty cycle.
- Life: hours, cycles, shelf life. Convert to cycles for fatigue (e.g. 8 h/day × 250 d × 5 y × 1 cycle/10 s ≈ 3.6 M cycles).
- Environment: temperature range, humidity, dust, sunlight/UV, vibration, shock/drop, chemicals, outdoors.
- Interfaces: mounting, power (V, A), signals, mechanical connectors, tool flange standard (e.g. ISO 9409-1).
- Size and mass envelope.
- Safety: hazards, who is exposed, applicable standards.
- Manufacturing: process, printer build volume, available tools, quantity.
- Maintenance: what wears, interval, who services, which tools.
- Cost: unit BOM, tooling, labour/assembly time.
- Aesthetics/ergonomics: how users hold, see, hear, and operate it.
- Regulatory: CE/UKCA (EU Machinery Regulation 2023/1230 applies from Jan 2027), UL, RoHS, FCC for electronics.

Tips:
- Separate **targets** (what you hope) from **thresholds** (what you accept). Concepts are judged against thresholds.
- Every number gets a source: user, benchmark, calculation, or estimate.
- Write the **verification method** now. If you can't say how you'd test it, it's not a requirement yet.
- Use **QFD/House of Quality** only if there are many customer wants to map; for small projects a ranked list suffices.

### 1.3 Concept generation

Methods:
- **Functional decomposition:** break the overall function (e.g. "position tool in 3D") into sub-functions (support, actuate joint, transmit torque, sense position, route power). Generate options per sub-function.
- **Morphological chart:** rows = sub-functions, columns = options; pick one per row to form a concept. Ensure combinations are compatible.

  | Sub-function | Option A | Option B | Option C |
  |---|---|---|---|
  | Actuate J2 | Stepper + GT2 belt reduction | Stepper + planetary | Servo + cycloidal |
  | Transmit to J3 | Belt through J2 axis | Parallel linkage | Motor on link |
  | Sense home | Microswitch | Hall + magnet | Optical slot |
  | Structure | Printed shells | 2020 extrusion + printed nodes | Al tube + printed joints |

- **Benchmarking / prior art:** search open-source designs, patents (Google Patents), commercial products. Start from what works (Mechy standard 1).
- **Brainstorm rules:** quantity first, defer judgment, include one deliberately "wild" concept to expose assumptions.
- **TRIZ** contradictions (e.g. "stronger but lighter" → use segmentation, composite, shape change) are useful prompts, not a method to follow mechanically.

Always include the **conventional baseline** as concept 1 (Mechy standard 2).

### 1.4 Concept selection: Pugh matrix, then weighted decision matrix

**Pugh (datum) method** – fast, relative, good for screening many concepts:
1. Choose a datum (usually the conventional design).
2. For each criterion, score each concept vs datum: `+` better, `S` same, `−` worse.
3. Sum +/−. Don't just pick the winner: combine strengths of top concepts and rerun. Drop clear losers.

| Criterion | Datum: serial arm, belts | B: SCARA | C: delta |
|---|---|---|---|
| Reach/workspace volume | S | − | − |
| Stiffness at tool | S | + | + |
| Part count | S | + | − |
| Speed | S | + | + |
| Ease of printing | S | S | − |
| Sum + / − | 0/0 | 3/1 | 2/3 |

**Weighted decision matrix** – for the final 2–4 concepts:
- Weights sum to 1 (or 100). Derive from requirement priorities; set **before** scoring to avoid bias.
- Score 1–5 (or 1–10) against defined anchors (e.g. "5 = repeatability ≤ 0.2 mm, 1 = > 2 mm").
- Total = Σ weight × score. Then **sensitivity check**: vary top weights ±30%; if the winner changes, the decision is weak – say so.
- Any concept failing a **threshold** (Must) is eliminated regardless of score.

Mini-example:

| Criterion | Weight | A score | A wtd | B score | B wtd |
|---|---|---|---|---|---|
| Payload margin | 0.30 | 4 | 1.20 | 3 | 0.90 |
| Repeatability | 0.25 | 3 | 0.75 | 4 | 1.00 |
| Cost | 0.20 | 4 | 0.80 | 3 | 0.60 |
| Buildability | 0.15 | 5 | 0.75 | 3 | 0.45 |
| Looks | 0.10 | 3 | 0.30 | 4 | 0.40 |
| **Total** | 1.00 | | **3.80** | | **3.35** |

Other tools: AHP (pairwise weights) if stakeholders disagree on weights; Kepner-Tregoe "musts vs wants" is the same idea as thresholds vs weighted targets.

### 1.5 Embodiment: budgets you should always make

- **Torque budget** per joint: τ_required = (m_link·g·r_cg + m_payload·g·r_payload) + J·α + friction; compare to motor torque × ratio × efficiency × derating (Mechy standard: ≥ 50% margin, i.e. required ≤ available/1.5).
- **Mass budget**: every moving part; track mass and CG per link.
- **Error budget**: list every error source at the tool point (backlash, belt stretch, link deflection, encoder resolution, thermal growth, assembly tolerance). Combine systematic errors by adding, random ones by RSS: `e_total ≈ Σ|e_sys| + sqrt(Σ e_rand²)` [Slocum].
- **Stiffness budget**: springs in series, `1/k_total = Σ 1/k_i`; the softest element dominates (often a belt, a printed joint, or a bolted plastic interface).
- **Power/thermal budget**: motor and driver dissipation, enclosure temperature rise.
- **Cost budget**: per subsystem, so overspend is visible early.

### 1.6 Prototyping strategy

- **Prototype the riskiest assumption first** ("most critical module" approach used in MIT 2.007/2.75 teaching): e.g. "can a printed belt reducer hold 2 N·m without skipping?"
- Types: *looks-like* (form, ergonomics, aesthetics), *works-like* (function, ugly is fine), *test rigs* (one variable at a time), *alpha/beta* (integrated).
- Cheapest medium that answers the question: cardboard/foam for size and reach; FDM for fit; quick sim for loads; real parts for friction and backlash.
- **Plan the measurement before you build.** What value, with what instrument, what pass/fail.
- Change one thing between iterations when diagnosing; change many when exploring.
- Keep a log: rev, date, change, result, photo.

---

## 2. Exact constraint and kinematic design

### 2.1 Degrees of freedom and constraint counting

A rigid body in space has **6 DOF** (3 translation, 3 rotation). A design should impose exactly `6 − (desired DOF)` independent constraints.

- **Exact constraint (kinematic) design:** each constraint is a point contact (or idealised line of force) acting along a unique, non-redundant direction. Result: position is determined uniquely, no internal fighting, assembly doesn't need precise parts.
- **Overconstraint:** more constraints than needed in some direction. Requires precise manufacture or compliance; otherwise causes binding, stress, wear, and unpredictable position. Examples: two parallel linear rails bolted rigidly to a non-flat base; a shaft in three rigid bearings; four legs on an uneven floor (table rocks).
- **Underconstraint:** missing constraint → unwanted motion/rattle.

**Grübler–Kutzbach mobility** (for mechanisms):
- Spatial: `M = 6(n − 1 − j) + Σ f_i`
- Planar: `M = 3(n − 1 − j) + Σ f_i`
  - n = number of links including ground, j = number of joints, f_i = DOF of joint i.
- Caveat: the formula misses special geometries (parallel links, redundant constraints). If M from the formula is ≤ 0 but the mechanism moves, it's overconstrained and relies on geometry (e.g. a parallelogram linkage: formula gives 0 when the 4-bar is modelled spatially with revolute joints – real parts need tolerances or compliance).

**Constraint rules of thumb** [Blanding, Hale]:
- Constraint lines that intersect at a point, or are parallel, allow rotation about that point/line.
- Two parallel constraints in a plane ≡ one constraint + one rotation constraint.
- Don't place constraints so that they are nearly parallel/coincident; small misalignment → huge forces (poor "stability").
- Apply nesting force (preload) so that the body stays against its constraints: the resultant must pass inside the "triangle" of support.

### 2.2 Kinematic couplings (repeatable mounts)

Purpose: detachable interface that relocates repeatably without precise parts.

| Type | Contacts | Repeatability [typ] | Stiffness | Use when |
|---|---|---|---|---|
| Three balls in three V-grooves (Maxwell) | 6 point contacts | sub-µm (machined, hardened) [Slocum review]; ~tens of µm with printed grooves + steel dowels [est] | low–moderate (Hertz contacts) | Tool changers, sensor mounts, fixtures, removable end-effectors |
| Ball–cone, ball–V, ball–flat (Kelvin) | 3+2+1 contacts | sub-µm (machined) | lower | Thermal growth must be accommodated about a fixed point |
| Quasi-kinematic (ball/rounded pin in cone groove) | line contacts | 1–5 µm [typ] | higher | Need more stiffness and load capacity |
| Pin + slot + plane ("3-2-1", dowel pins) | — | ~3–5 µm practical for machined 3-2-1 fixtures [Slocum review] | high | General location of machined parts |
| Elastic averaging (many compliant contacts) | many | improves with N (~1/√N) [est] | high | Lego-like features, Hirth couplings, curvic couplings |

Design rules for 3-groove couplings [Slocum, "Design of three-groove kinematic couplings", 1992]:
- Grooves at roughly 120°, groove axes pointing toward the coupling centroid. The angle bisectors of the triangle formed by contact force lines should intersect, giving stability; good layouts have the coupling triangle roughly equilateral.
- The preload (gravity, magnet, spring or bolt) should pass through the centroid of the triangle.
- Hertz contact stress limits load; use hardened balls (bearing balls) and hard groove surfaces (steel dowel pins pressed into a printed body make cheap, good grooves).
- The instant centre / thermal centre is at the centroid; uniform thermal expansion leaves it in place.
- Clean, lubricated (or not) consistently; friction degrades repeatability – a light tap or vibration helps seating.

### 2.3 Bearing arrangements (the most common real-world overconstraint)

- Shaft on two radial bearings: **one locating (fixed axially both ways), one non-locating (floating axially)**. Otherwise thermal growth or tolerance preloads the bearings axially.
- Alternative: two angular-contact or tapered bearings, **face-to-face (X)** or **back-to-back (O)** with controlled preload. Back-to-back (O) gives higher moment stiffness (wider effective spread); face-to-face tolerates misalignment better [SKF].
- Two parallel linear rails: fix one rail (reference), let the other rail's carriages float or align the second rail to the first with a straight-edge/dial indicator. Or use one rail + an outrigger roller on a flat (a kinematic pair).
- Leadscrew + linear guide: the nut must float radially (oldham coupling or flexure nut mount), otherwise screw wobble fights the guide.
- Motor + shaft + bearings: a rigid coupling between a motor shaft (with its own bearings) and a separately supported shaft is overconstrained; use a flexible coupling or let the motor be the support.

### 2.4 Flexures (compliant mechanisms)

- Frictionless, backlash-free, repeatable; limited range. Great for printed parts if stresses stay low.
- Motion range limited by `σ_max ≈ E·t / (2R)` for bending to radius R (thickness t) → keep t small.
- Fatigue governs: for PLA/PETG keep peak strain well below ~1–2% for many cycles [est]; prefer PP, nylon, TPU, or spring steel for live hinges/high cycle.
- Parallelogram (four-blade) flexure: straight-line motion with small parasitic error ≈ δ²/(2L) (δ = deflection, L = blade length) [Smith/Hale].

---

## 3. Stiffness-first design and load paths

### 3.1 Why stiffness first

- Position error under load = F/k. A 5 N load on a 0.05 N/µm (50 kN/m) tool point gives 100 µm.
- Natural frequency `f_n = (1/2π)·sqrt(k/m)` (Hz; k in N/m, m in kg). Low f_n limits control bandwidth, settling time and acceleration. Rule of thumb [est]: keep the first structural mode ≥ 3–5x the position-loop bandwidth, and well above step/belt excitation frequencies.
- Strength rarely governs in a stiffness-driven design: if deflection is acceptable, stress is usually low. Still check stress, buckling, and joints.

### 3.2 Beam and shaft formulas (SI)

| Case | Deflection / rotation | Variables |
|---|---|---|
| Cantilever, tip load | δ = F·L³ / (3·E·I) | F [N], L [m], E [Pa], I [m⁴] |
| Cantilever, uniform load w | δ = w·L⁴ / (8·E·I) | w [N/m] |
| Simply supported, centre load | δ = F·L³ / (48·E·I) | |
| Fixed–fixed, centre load | δ = F·L³ / (192·E·I) | 4x stiffer than simply supported |
| Shaft torsion | θ = T·L / (G·J) | T [N·m], G [Pa], J [m⁴] |
| Axial bar | δ = F·L / (E·A) | A [m²] |

Section properties:
- Rectangle b × h (bending about the axis parallel to b): `I = b·h³/12` → doubling height = 8x stiffer.
- Solid round diameter D: `I = π·D⁴/64`, `J = π·D⁴/32`.
- Tube: `I = π(D⁴ − d⁴)/64`. A tube with same mass as a rod but 2x diameter is ~3–4x stiffer in bending [computed].
- **Closed vs open sections in torsion:** for a thin-walled tube of mean radius R and wall t, J_closed ≈ 2πR³t while a slit (open) tube has J_open ≈ (2πR·t³)/3, so the ratio is ≈ 3(R/t)² [Roark; computed]. With R/t = 10 the slit tube is ~300x less stiff in torsion. Never leave a long slot along a torsion member.

Key insight: **length cubed.** Halving a cantilever length = 8x stiffer. Shorten overhangs before adding material.

### 3.3 Specific stiffness (E/ρ) and material choice

| Material | E [GPa] | ρ [kg/m³] | E/ρ [MJ/kg] | Notes |
|---|---|---|---|---|
| Steel | 200–210 | 7850 | ~26 | Cheap, stiff, heavy |
| Aluminium 6061/6082 | 69 | 2700 | ~26 | Same specific stiffness as steel; 3x lighter per volume → bigger sections |
| Titanium Ti-6Al-4V | 114 | 4430 | ~26 | Expensive |
| CFRP tube (unidirectional-ish) | 70–150 | 1550–1600 | 45–95 | Great for arm links; joints are the hard part |
| Glass-filled nylon (printed) | 4–8 | 1200–1350 | ~3–6 | [est; datasheet dependent] |
| PLA (FDM, along layers) | 2.5–3.5 | 1240 | ~2–3 | Weaker/softer across layers |
| PETG (FDM) | 1.8–2.1 | 1270 | ~1.5 | |
| ABS/ASA (FDM) | 1.8–2.4 | 1050 | ~2 | |

Values [typ] from MatWeb/manufacturer datasheets; FDM values vary ±30% with settings.
Consequence: you can't beat geometry with material in metals (E/ρ ≈ constant); make sections deep and hollow. For printed parts, a 2020 aluminium extrusion or a CFRP/Al tube inside the link often gives 10–30x the stiffness of an all-printed link of the same size [est].

### 3.4 Load paths

- Draw the **force flow**: from the payload, through each part, joint, fastener and bearing, to ground. Mark each element as tension, compression, bending, torsion or shear.
- **Preferred hierarchy:** tension/compression (axial) >> torsion of closed section >> bending. Triangulate frames (trusses) to turn bending into axial loads.
- **Short and direct:** the stiffness of a load path is roughly the series sum; every extra part and joint adds compliance.
- **Avoid sudden changes in section** along the load path (stress concentration + compliance); use fillets, gussets.
- **Joints are the weak/soft spot:** bolted joints have contact compliance; a bolted plastic joint can be the softest element in the whole arm. Spread clamping load with washers/plates, use multiple fasteners spaced apart to resist moments.
- **Bearings in the load path:** moment loads on single bearings cause tilt; use bearing pairs spaced ≥ 1–2x shaft diameter apart, or crossed-roller / 4-point-contact bearings for moment loads [typ; bearing catalogue guidance].
- **Structural loop** [Slocum]: the closed path from tool to workpiece through the machine frame. Make it short, stiff, thermally symmetric, and with as few joints as possible.

### 3.5 Saint-Venant's principle

Statement (practical): the effect of how a load is applied (point vs distributed, bolt vs clamp) dies out at a distance of roughly **one to two characteristic widths** of the loaded region/section [typ; Timoshenko & Goodier]. Far from the load only the resultant force and moment matter.

Design uses:
- Keep critical precision features (bearing seats, reference faces) **≥ 1–2 section widths away** from bolts, clamps and press fits, so local distortion doesn't reach them.
- Conversely, you can rely on simple beam theory only once you're a few widths from load points and supports; near them, use FEA or generous margins.
- Bolt pattern: clamp pressure under a bolt spreads in a cone of roughly 30–45° half-angle [typ; VDI 2230 uses ~30° for the pressure cone]; bolts spaced more than ~3–5 bolt diameters apart leave unclamped gaps (leaks, fretting) between them [est].
- Flexure and gauge locations: put strain gauges/sensors where the stress field is uniform.

### 3.6 Bolted joints (essentials)

- A joint stays tight because of **preload**. Target preload ≈ 70–75% of proof load for reusable steel joints [typ; Shigley, Bickford]. Torque T ≈ K·F·d with nut factor K ≈ 0.2 dry steel, ≈ 0.15–0.18 lubricated [typ].
- Example (estimate): M3 class 8.8 steel, stress area 5.03 mm², proof ≈ 600 MPa → proof load ≈ 3.0 kN; 75% ≈ 2.3 kN; T ≈ 0.2 × 2300 × 0.003 ≈ 1.4 N·m. **Into plastic or heat-set inserts use far less** – typically 0.3–0.8 N·m for M3 inserts depending on insert size and material [est; insert vendor data varies].
- Long grip length (bolt stretch) improves resistance to loosening and fatigue: aim for grip ≥ 3–5 d where practical [est; Bickford].
- Plastic in the clamp stack **creeps**, so preload decays. Use metal spacers/sleeves through printed parts so the bolt clamps metal-to-metal, or use spring washers (disc/Belleville) to maintain load.
- Threads in printed plastic: OK for low-cycle assembly; use heat-set inserts or captive nuts for anything reassembled more than a few times.

---

## 4. Precision engineering principles (Slocum and others)

Accuracy vs repeatability vs resolution:
- **Accuracy:** closeness to true value (mean error).
- **Repeatability:** spread when returning to the same command (precision). Calibrate away systematic errors only if repeatability is good.
- **Resolution:** smallest step commanded or measured.
- Rule: design for repeatability, calibrate for accuracy. A cheap machine with good repeatability can be mapped and corrected in software.

Principles summarised (paraphrased from Slocum, *Precision Machine Design*, and MIT 2.75 notes):

| Principle | What it says | Design action |
|---|---|---|
| Occam's razor | Simplest design that meets spec wins | Fewer parts, fewer joints |
| Saint-Venant | Local load effects fade within ~1–2 widths | Keep precision features away from clamps/bolts |
| Abbe | Offset between measurement axis and motion axis amplifies angular error | Align sensor/tool with guide axis |
| Maxwell / exact constraint | Constrain each DOF once | Kinematic mounts, floating bearings |
| Stiffness | Errors = loads/stiffness | Short loops, closed sections |
| Symmetry | Symmetric structures deflect and grow thermally symmetrically | Centre drives on guides, symmetric heat sources |
| Structural loop | Path between tool and work determines error | Minimise length and joints |
| Self-principles | Use the load to help (self-reinforcing, self-aligning, self-locating) | Preload into constraints; gravity seats parts |
| Thermal | Thermal errors often dominate at µm level | Low CTE, symmetric heat paths, thermal centre |
| Reciprocity / reversal | Measure, flip, measure again to separate part error from instrument error | Calibration procedures |
| Elastic averaging | Many compliant contacts average errors | Hirth couplings, ribbed press fits |
| Sensitive direction | Only errors in certain directions matter | Spend tolerance budget only where sensitive |
| Superposition / error budget | Combine all error sources at the tool point | Error budget table |
| Isolation | Isolate from vibration and heat sources | Mounts, separate motor heat from structure |

### 4.1 Abbe error

`ε_Abbe = h · tan(θ) ≈ h · θ` (θ in radians)
- h = Abbe offset: perpendicular distance between the line of measurement (scale/encoder axis) and the line of the functional point (tool/probe).
- θ = angular error (pitch/yaw) of the carriage.

Worked examples [computed]:
- Precision stage: h = 100 mm, θ = 10 arcsec (48.5 µrad) → ε ≈ 4.9 µm.
- Hobby printer/arm linear axis: h = 50 mm, θ = 0.1° (1.75 mrad) → ε ≈ 87 µm.
- Robot arm joint: tool 400 mm from J1, joint angle error 0.1° → 0.70 mm at the tool. **For rotary joints the "Abbe offset" is the reach itself**; joint angular accuracy and backlash dominate tool error.

Bryan principle (extension): the displacement sensor should lie on the effective line of the functional point, in all directions; if it can't, measure the angle and correct.

### 4.2 Thermal design

Free expansion: `ΔL = α · L · ΔT`
- α [1/K], L [m], ΔT [K].

| Material | α [µm/(m·K)] [typ] |
|---|---|
| Invar 36 | ~1.2 |
| Granite | ~6–8 |
| Steel (carbon) | ~11–12 |
| Stainless 304 | ~17 |
| Aluminium 6061 | ~23 |
| Brass | ~19 |
| CFRP (quasi-isotropic) | ~0–5 (direction dependent) |
| PLA | ~60–80 [est; datasheets vary] |
| PETG | ~60–70 [est] |
| ABS / ASA | ~80–100 [est] |
| Nylon (PA12/PA6) | ~80–120 [est] |
| PC | ~65–70 |

Worked example [computed]: 300 mm aluminium link, 10 K warm-up → ΔL = 23e-6 × 0.3 × 10 = 69 µm.
Steel shaft in an aluminium housing over 40 K: the bore grows ~(23−12)e-6 × 22 mm × 40 ≈ 10 µm more than the shaft → a light press fit can loosen.

Plastic-specific thermal limits (glass transition / heat deflection, [typ, datasheets]):
- PLA: Tg ~55–60 °C → printed PLA parts deform in hot cars, near motors (steppers often run 50–80 °C case), or in sun.
- PETG: Tg ~75–80 °C. ABS/ASA: ~100–105 °C. PC: ~140–150 °C. PA (nylon): Tg low but HDT 80–180 °C depending on grade/fill.
- **Rule [est]:** keep continuous service temperature ≥ 20 K below Tg/HDT under load; don't bolt a stepper directly to PLA without a metal or air gap if the motor runs hot.

Thermal design rules:
1. Identify heat sources (motors, drivers, PSUs, friction, sunlight, people) and sinks.
2. **Thermal symmetry:** symmetric structures bend less (they grow, but don't curl).
3. **Thermal centre:** place the datum (fixed point) where the precise feature is, so growth happens away from it.
4. **Match CTE** across bonded or tightly fitted joints, or allow sliding (slots, flexures).
5. Bimetal bending: two bonded materials of different α curl; avoid clamping long aluminium to long steel rigidly.
6. Warm-up time: let machines reach equilibrium before precise work; time constant scales with mass/(h·A).
7. Electronics derating: semiconductor and capacitor life halves roughly every 10 K rise (Arrhenius rule of thumb for electrolytic caps) [typ].
8. Motor winding temperature limits (class B 130 °C, class F 155 °C insulation) [std; IEC 60034-1]; stepper case may be 80 °C+ at full current.

---

## 5. DFM and DFA (Boothroyd–Dewhurst)

### 5.1 Part count reduction – the three questions

For each part, ask (Boothroyd–Dewhurst minimum part criteria):
1. Does the part **move relative to** all other parts already assembled (during normal operation)? Small motions that a flexure could provide don't count.
2. Must the part be of a **different material** (or isolated) from the others for a fundamental reason (electrical insulation, wear, thermal)?
3. Must the part be **separate** from all others to allow assembly or disassembly (service) of other parts?

If all three answers are "no", the part is a candidate for elimination or combination. Fasteners almost always fail this test – they're "non-theoretical" parts.

**DFA index** (manual assembly efficiency): `E_ma = (N_min × t_ideal) / T_actual`, with t_ideal ≈ 3 s per part (some sources cite 2.93 s) [Boothroyd–Dewhurst; DFMA literature]. Typical products score 5–20%; good designs 25%+ [typ, est]. Reported part-count reductions from DFA studies are commonly 20–60% [DFMA case studies; varies by source].

### 5.2 DFA guidelines (manual assembly)

Handling:
- Parts symmetric about their insertion axis (alpha symmetry) and about the perpendicular axis (beta symmetry) – or **obviously** asymmetric. Avoid nearly-symmetric parts.
- Avoid parts that tangle, nest, stick, are slippery, flexible, very small (< ~2 mm) or very large.
- Standardise fasteners: one or two sizes (e.g. all M3 + M5), one drive type, one hex key.

Insertion:
- **Self-locating** features: chamfers, lead-ins, tapers, pilots, bosses, dowels, snap fits. A part should locate itself before it's fastened.
- **Top-down, single-direction assembly (z-axis)**; avoid flipping the assembly.
- Provide **access** for tools and fingers (hex key swing ~60°; wrench clearance).
- Hold-free: the part should stay in place until fastened (no "third hand" needed).
- Avoid simultaneous alignment of multiple features (e.g. a bearing, a shaft and a pulley all at once).
- Fastening cost order (cheapest first) [typ]: snap fit < press fit < heat-staked/insert < screw < screw+nut+washer < adhesive with cure time.
- Base part: large, stable, with features that receive and locate the next parts.

### 5.3 Poka-yoke (mistake proofing)

- Make wrong assembly **physically impossible**: asymmetric pin patterns, keyed connectors, different screw sizes for parts that look alike, D-shaped shafts, offset dowels.
- Make wrong assembly **obvious**: colour coding, arrows, labels moulded/printed in, witness marks for timing (e.g. belt pulley alignment marks).
- Left/right handed parts: either make them identical (mirror-symmetric design) or make them impossible to swap.
- Connectors: unique connector type or keying per cable when several sit together; avoid identical 4-pin connectors for motor and sensor side by side.
- Software poka-yoke: homing checks, current-limit checks, end-stop sanity check at boot.

### 5.4 DFM by process (quick table)

| Process | Key rules [typ] |
|---|---|
| FDM 3D printing | Orient so layers aren't loaded in tension across them (Z strength ~50–70% of XY for PLA/PETG [est]); avoid overhangs > 45–50° without support; holes print ~0.1–0.3 mm undersize – ream/drill or compensate; min wall ≈ 2–3 perimeters (0.8–1.2 mm with 0.4 nozzle); add fillets at load-bearing corners; teardrop horizontal holes; first-layer "elephant foot" ~0.1–0.3 mm – chamfer bottom edges; design for heat-set inserts (pilot hole per vendor, typically ~0.1–0.2 mm under insert OD [est]) |
| SLS / MJF nylon | No supports; ~0.3 mm clearance between moving parts; escape holes for powder; min wall ~0.7–1 mm |
| CNC milling | Internal corner radii ≥ tool radius (use ≥ 1/3 cavity depth); avoid deep narrow pockets (depth ≤ 3–4x tool diameter); minimise setups; standard hole sizes and threads; don't tolerance what doesn't matter |
| CNC turning | Concentric features in one setup; undercuts for thread runout; standard chamfers |
| Sheet metal | Bend radius ≥ material thickness; holes ≥ 2–2.5 t from bend; flange length ≥ 4 t; relief cuts at bend intersections; uniform thickness |
| Injection moulding | Uniform walls (1.5–3 mm typical); draft 0.5–2°; ribs ~50–60% of wall thickness to avoid sink; bosses cored out; avoid undercuts or use side actions/snaps; gate and weld line locations matter |
| Laser cutting | Kerf ~0.1–0.3 mm; tab-and-slot for self-jigging; min feature ≈ material thickness |
| Extrusion (2020/2040) | Cut-to-length; use standard brackets/T-nuts; tap end holes (M5 for 2020) |

General DFM:
- Use **standard parts** (bearings, fasteners, extrusions, belts) before custom ones.
- Design to the process capability; don't specify tolerances the process can't hold.
- Minimise the number of distinct parts, materials, and processes.
- Prefer features that can be made in one setup/orientation.

---

## 6. Design for maintenance and serviceability

- **List what wears or needs adjustment** (belts, bearings, brushes, filters, batteries, cables in flex, lubricated screws) and design access for each.
- Wear parts should be the **cheap, standard, replaceable** parts – the belt, not the pulley; the bushing, not the housing.
- Access rule: servicing a wear item should not require removing an unrelated part (no "remove the arm to change the J1 belt").
- **Belt tension adjustable** in place (slotted motor mount, idler with screw adjustment), with a way to measure tension (frequency method, deflection gauge).
- Captive fasteners on service panels; fewer, larger fasteners; same tool for everything.
- Modular: replaceable subassemblies with connectors (not soldered wires) at the module boundary.
- Diagnostics: test points, LEDs, accessible connectors, homing/limit switch state visible.
- Lubrication points accessible; specify lubricant and interval.
- Label cables and connectors at both ends.
- Provide reference/datum features that let a technician realign after service (dowels, witness marks, alignment jigs).
- Spare parts: STL + BOM entries for every printed part; vendor part numbers for purchased parts.
- Mean time to repair target: e.g. "replace any belt in < 15 min with one hex key" is a good spec item.

---

## 7. Failure modes and how to design against them

### 7.1 Overview table

| Failure mode | Cause | Typical symptoms | Design countermeasures |
|---|---|---|---|
| Yield / fracture (static) | Stress > strength | Permanent bend, crack | Safety factor; fillet; correct layer orientation |
| Buckling | Slender member in compression | Sudden sideways collapse | Euler check; shorten, increase I |
| Fatigue | Cyclic stress, stress concentrations | Crack at notch/hole/thread/layer line, beach marks | Lower stress amplitude; fillets; avoid notches; surface finish; preload bolts |
| Wear | Sliding/rolling contact, abrasion | Backlash grows, debris, noise | Hard/soft pairing, lubrication, PV limits, replaceable wear parts |
| Fretting | Micro-slip in clamped joints | Rust-red/black powder at joints | Higher clamp load, avoid micro-motion |
| Self-loosening | Transverse slip under vibration | Fasteners back out | Preload, long grip, positive locking |
| Creep / stress relaxation | Sustained stress, esp. plastics or warm metals | Gradual sag, loss of preload/press fit | Low sustained stress, metal inserts, design for relaxation |
| Corrosion (uniform/pitting/crevice) | Moisture, salts, chemicals | Rust, pits | Material choice, coatings, drainage |
| Galvanic corrosion | Dissimilar metals + electrolyte | Corrosion of the anodic metal at contact | Anodic index limits, isolate, coat the cathode |
| Thermal damage | Heat above Tg/HDT, overheated motor | Warp, softening, insulation failure | Thermal design, derating, temperature sensing |
| Belt failure / skipping | Under-tension, overload, small pulleys | Lost steps, ratcheting, tooth shear | Proper tension, ≥ 6 teeth in mesh, min pulley size |
| Electrical / cable fatigue | Repeated bending/torsion | Intermittent faults | Bend radius, strain relief, flex-rated cable |
| UV / environmental degradation | Sunlight, ozone, hydrolysis | Brittleness, colour change | ASA/UV-stable materials, coatings |

### 7.2 Fatigue

- Most mechanical failures in service are fatigue (often cited ~50–90% [typ; ASM, Shigley commentary]).
- **Steel:** endurance limit S_e' ≈ 0.5 × S_ut for S_ut ≤ ~1400 MPa; capped ~700 MPa above that [Shigley]. Then derate with Marin factors (surface, size, load type, temperature, reliability) – real S_e often 0.25–0.4 S_ut [est].
- **Aluminium:** no true endurance limit; use fatigue strength at 5×10⁸ cycles ≈ 0.3–0.4 S_ut [typ].
- **FDM plastics:** fatigue strength at 10⁶ cycles often ~15–30% of UTS, worse across layers and at layer-line notches [est; limited literature, wide scatter].
- Mean stress: use Goodman (conservative) `σ_a/S_e + σ_m/S_ut = 1/n`.
- Stress concentration factor K_t: a sharp internal corner can have K_t ≥ 3; a fillet with r/d ≈ 0.1 gives ~1.5–2 [Peterson; typ]. In fatigue, fillets matter more than material upgrades.
- Bolts: threads have K_f ≈ 2.2–3.8 depending on grade/rolled vs cut [Shigley]; high preload protects bolts by reducing the alternating load they see.
- **Count cycles honestly**: a pick-and-place arm at 1 cycle/5 s, 8 h/day, 1 year ≈ 1.5 M cycles. Every joint and cable sees each.

### 7.3 Wear

- Archard: wear volume `V = K · F · s / H` (K dimensionless wear coefficient, F normal load [N], s sliding distance [m], H hardness [Pa]). Use to compare designs, not to predict life precisely.
- Plain bearings / bushings: check **PV** (pressure × velocity) against the material limit (e.g. PTFE-, nylon- or igus iglidur-type materials list PV limits in datasheets) [manufacturer data].
- Rolling bearings: L10 life `L10 = (C/P)^p × 10⁶ revs` with p = 3 (ball), 10/3 (roller); C = dynamic load rating, P = equivalent load [ISO 281]. Printed housings don't change L10 but misalignment and poor fits reduce real life.
- Pair a **hard** and a **soft** material, or a hard pair with lubricant. Avoid like-on-like metals (aluminium on aluminium galls; stainless on stainless galls).
- Belts and gears: wear increases backlash; design tensioners/adjusters.
- Keep dirt out: covers, seals, 2RS bearings in dusty settings.

### 7.4 Self-loosening of threaded fasteners

- Main mechanism: **transverse slip** under vibration/cyclic load lets the thread rotate loose (Junker test) [Junker 1969; Bickford]. Secondary: embedding and creep reducing preload.
- Countermeasures, roughly in order of effectiveness:
  1. Sufficient preload and stiff joint so it doesn't slip (friction > transverse load).
  2. Long grip / thin-shank bolts (more stretch → less preload loss from embedding).
  3. Adhesive thread locker (medium strength, removable – e.g. "blue" grade) for metal threads. Not on plastics (crazes PC/ABS).
  4. Wedge-locking washer pairs (Nord-Lock type), prevailing-torque (nylon-insert) nuts, safety wire, cotter pins.
  5. Positive mechanical locks: tab washers, castellated nuts.
- **Split (helical) lock washers provide little resistance to vibration loosening** – this is documented in NASA and Junker-style tests [NASA RP-1228 fastener design manual; Bickford]. Don't rely on them.
- Set screws on shafts loosen: use a flat on the shaft (D-shaft), cup-point set screw + thread locker, two set screws at 90°, or clamp collars/keyed hubs.
- Fasteners in printed plastic: preload relaxes via creep; use inserts, metal sleeves and Belleville washers; recheck after 24 h.

### 7.5 Creep and stress relaxation

- **Creep:** strain grows under constant stress. **Relaxation:** stress falls under constant strain (press fits, bolt preload, snap fits held deflected).
- Plastics creep at room temperature. PLA is especially poor near 40–50 °C; nylon is affected by moisture.
- Rules [est]: keep sustained stress in FDM PLA/PETG below ~10–20% of short-term UTS; don't hold snap fits deflected; avoid permanently loaded press fits in plastic for bearings that carry high loads (use a clamping cap instead or accept periodic re-tightening).
- Metals: creep matters above ~0.3–0.4 T_melt (K) [typ] – relevant for aluminium near ~150 °C+, solder, lead, zinc die cast.

### 7.6 Corrosion and galvanic corrosion

Galvanic corrosion needs three things: **two dissimilar metals, electrical contact, and an electrolyte** (moisture, salt). Remove any one and it stops.

Anodic index [V] (legacy MIL-STD-889-style table, reproduced by Engineers Edge; values [std/typ]):

| Metal / finish | Anodic index (V) |
|---|---|
| Gold | 0.00 |
| Silver | 0.15 |
| Nickel, titanium, Monel | 0.30 |
| Copper | 0.35 |
| Brass, bronze | 0.40 |
| 18% chromium (300-series-type) stainless | 0.50 |
| Chromium plate, tin plate, 12% Cr stainless | 0.60 |
| Lead | 0.70 |
| Aluminium 2000 series | 0.75 |
| Carbon / low-alloy steel, cast iron | 0.85 |
| Aluminium wrought (non-2000) e.g. 6061 | 0.90 |
| Cast aluminium (non-Si), cadmium plate | 0.95 |
| Galvanised (hot-dip zinc) steel | 1.20 |
| Zinc plate, zinc die cast | 1.25 |
| Magnesium | 1.75 |

Allowable difference [typ; Engineers Edge / Carr Lane, legacy guidance – current MIL-STD-889 revision uses galvanic current instead]:
- Harsh (outdoor, salt, high humidity): ≤ 0.15 V
- Normal indoor, not climate-controlled: ≤ 0.25 V
- Climate-controlled indoor: ≤ 0.50 V

Design rules:
- The **more anodic** (higher index) metal corrodes. **Area ratio matters:** small anode + large cathode = rapid attack (e.g. aluminium rivets in a stainless sheet – bad). Large anode + small cathode is tolerable (stainless screws in an aluminium plate indoors usually fine).
- Stainless fasteners in aluminium outdoors: isolate with nylon washers / sleeves, use anti-seize or zinc-chromate/duralac-type barrier, or anodise the aluminium.
- Coat the cathode (not just the anode) – a scratch in a coated anode concentrates attack.
- Avoid crevices and water traps; provide drainage holes; don't trap moisture under gaskets.
- Plastics don't galvanically corrode but carbon fibre is **cathodic** (noble, like graphite) – aluminium bonded/bolted to CFRP corrodes in wet conditions; isolate with glass-fibre layer or film.
- Indoor robot arms and printers: galvanic issues are minor; still avoid bare steel in humid rooms (use zinc-plated or stainless fasteners, black-oxide steel needs oil).

---

## 8. FMEA (Failure Mode and Effects Analysis)

Purpose: systematically ask "how can each function fail, what happens, why, and how will we prevent/detect it?" Do it at concept and again at detail design.

Steps:
1. Define scope and block diagram (functions, interfaces).
2. For each function/component: list **failure modes** (how it fails to perform).
3. **Effects** on the system/user → rate **Severity S** (1–10).
4. **Causes** → rate **Occurrence O** (1–10), considering current prevention controls.
5. **Current detection controls** (tests, sensors, inspection) → rate **Detection D** (1–10; 10 = can't detect).
6. Prioritise: classic **RPN = S × O × D** (1–1000), or the **AIAG-VDA (2019) Action Priority (AP)** lookup (High/Medium/Low) which weights Severity first, then Occurrence, then Detection. AP replaced RPN in automotive because equal RPNs can hide very different risks (S=10,O=2,D=5 and S=4,O=5,D=5 both = 100) [AIAG-VDA FMEA Handbook 2019].
7. Actions: change design to reduce S (best), then O, then improve D. Re-rate after actions.

Rules:
- Any **S ≥ 9** (safety/regulatory) needs action regardless of O and D.
- Don't write effects as "breaks" – say what the user experiences ("arm drops payload onto operator's hand").
- Include cables, connectors, firmware/limit logic, power loss, and assembly errors as failure sources.

Compact severity scale (simplified for small projects) [est, adapted]:

| S | Meaning |
|---|---|
| 10 | Injury without warning / safety function lost |
| 8–9 | Injury with warning; loss of primary function |
| 5–7 | Degraded performance, user notices, repair needed |
| 2–4 | Minor annoyance |
| 1 | No noticeable effect |

FMEA row example:

| Item / function | Failure mode | Effect | S | Cause | O | Prevention | Detection | D | Action |
|---|---|---|---|---|---|---|---|---|---|
| J2 belt: transmit torque | Skips teeth | Arm drops ~20 mm, loses position | 7 | Low tension, overload | 5 | Tensioner, ≥ 6 teeth in mesh | Encoder vs step count | 4 | Add belt tension spec + output encoder |
| J2 at power loss | Back-drives | Arm falls onto table/hand | 9 | Low gearing, no brake | 6 | — | — | 10 | Add brake or gravity counterbalance spring; reduce mass |

Related tools: **FTA** (fault tree, top-down from a hazard), **DFMEA vs PFMEA** (design vs process), **HAZOP** (process plants).

---

## 9. Safety factors by situation

Definition: `n = strength / applied stress` (or capacity / demand). Choose n from uncertainty in loads, material, analysis, and consequence of failure. A higher n doesn't fix the wrong failure mode.

Guide values (compiled from RoyMech, Engineering Toolbox, Juvinall/Ullman-style tables – sources broadly agree but band labels differ) [typ]:

| Situation | n (on yield or ultimate as noted) |
|---|---|
| Well-known materials, loads and conditions; tested; low consequence | 1.25–1.5 |
| Reliable materials, reasonably known loads, normal environment | 1.5–2 |
| Ordinary materials, average conditions, loads estimated | 2–2.5 |
| Less tried or brittle materials, average conditions | 2.5–3 |
| Untested materials or uncertain loads/environment; FDM printed structural parts | 3–4 |
| Impact/shock loads, or failure could injure people (non-code) | ≥ 4 or use dynamic analysis + code |
| Lifting equipment, cranes, rigging | Use the governing code (e.g. wire rope commonly 5:1, chain slings 4:1) [std; ASME B30, EN 13414 etc.] |
| Pressure vessels, buildings, aircraft | Use the code (ASME BPVC, Eurocodes, FAR) – don't pick your own |

Mechy-specific guidance [est]:
- **Torque budget:** required ≤ available / 1.5 (standard 4). For steppers, also derate pull-out torque with speed (torque falls steeply above a few hundred RPM) and voltage.
- **Printed structural parts:** n ≥ 3 on the across-layer strength for static loads; n ≥ 4 if dynamic or if layer adhesion is uncertain. Prefer redesign of print orientation over more n.
- **Belts:** stay within manufacturer's rated working tension (GT2 6 mm glass-fibre belts commonly rated in the tens of N working tension [manufacturer data varies; verify]). Under-tensioning causes skipping before breaking.
- **Fatigue:** n = 1.5–2 on the Goodman line after Marin factors [typ].
- **Buckling:** n ≥ 3 on Euler load (sensitive to imperfections) [typ].
- **Bearings:** static safety factor s0 = C0/P0 ≥ 1–2 for normal operation, higher for shock [SKF guidance].
- **Electrical:** wire ampacity derated for bundling and temperature; fuse below wire rating.

Don't stack safety factors blindly (load × 1.5 and strength ÷ 1.5 and n = 2 → effective 4.5). Say where margin is applied, once.

---

## 10. Tolerances, fits and adjustability

### 10.1 Tolerance rules

- Tolerance **only what matters functionally**; leave the rest at general tolerance (e.g. ISO 2768-m: about ±0.1 mm for 6–30 mm, ±0.2 mm for 30–120 mm [std, verify current edition]).
- Use datums that match how the part is located in assembly (GD&T idea: datum A = the face that sits on the mating part).
- Process capability [typ]: FDM ±0.1–0.3 mm (plus shrink for ABS/nylon ~0.5–1.5%); SLS ±0.2–0.3 mm or ±0.3%; CNC ±0.02–0.05 mm routine, ±0.01 achievable; laser-cut ±0.1 mm; sheet bend ±0.2–0.5 mm.

### 10.2 Tolerance stack-up

- **Worst case:** `T_total = Σ |T_i|` – guaranteed, conservative, expensive.
- **Statistical (RSS):** `T_total = sqrt(Σ T_i²)` – assumes independent, centred, normal distributions; reasonable for ≥ 4 contributors and large volumes. Some use a Bender inflation factor ~1.5 × RSS for safety [typ].
- Mini-example: 5 printed parts in a stack each ±0.2 mm → worst case ±1.0 mm; RSS ±0.45 mm. For a one-off print, use worst case or **design an adjustment**.

### 10.3 Common fits (ISO 286 hole-basis) [std, typ uses]

| Fit | Type | Use |
|---|---|---|
| H11/c11 | Loose running | Agricultural, loose pins |
| H9/d9 | Free running | Large-clearance rotating |
| H8/f7 | Close running | Shafts in bushings |
| H7/g6 | Sliding | Locating, sliding gears/pins |
| H7/h6 | Locational clearance | Snug, assemble by hand |
| H7/k6 | Transition | Accurate location, light press |
| H7/p6 | Locational interference | Press fit, bearing outer ring in a rotating-load housing (check bearing maker) |
| H7/s6 | Medium drive | Permanent press |

Bearing fits: follow manufacturer tables (SKF/NSK). Rule: the ring that rotates relative to the load gets the interference fit; the other ring gets a transition/clearance fit.

FDM rules of thumb [est; printer-dependent – always print a test coupon]:
- Clearance (sliding) fit: +0.2–0.4 mm on diameter.
- Bearing press fit (e.g. 608, 22 mm OD): print hole ~22.0–22.1 mm nominal after calibration; tune with a test ring. PLA relaxes over time – a cap/retainer is safer than relying on press.
- Heat-set inserts and dowel pins: follow vendor pilot dimensions; test on scrap.

### 10.4 Adjustability (design it in rather than tolerancing it out)

- Slots for one-time alignment (then lock with dowels if repeatability is needed).
- Eccentric bushings/cams for tensioning and removing backlash (common on V-wheel carriages).
- Shims and spacers for axial positioning.
- Jack screws / push-pull screws for tilt adjustment.
- Belt tensioners with a measurable setting.
- Software calibration: homing offsets, joint zero offsets, link-length calibration.
- Rule: every adjustment needs (1) a way to measure, (2) a way to lock, (3) a stated procedure. An adjustment you can't lock will drift.
- Prefer **one** adjustment per error, decoupled from others (adjusting X shouldn't change Y).

---

## 11. Cable routing and wire management

Rules [typ; igus, Lapp, robot integrator guidance]:
- **Bend radius:** continuous-flex cables in cable chains typically need ≥ 7.5–10x cable OD (some high-flex rated to ~5x); standard PVC cable flexed repeatedly needs ≥ 10–15x and still fails eventually [manufacturer data varies – check cable datasheet].
- **Use flex-rated (stranded, fine-wire, Class 6) cable** for anything that moves; solid-core never moves.
- **Route through or close to the joint axis** to minimise bending/stretch; for continuous rotation use a slip ring.
- **Torsion:** cables tolerate twist better than bending only when the twisted length is long – allow ≥ ~±180° over a length of several hundred mm for typical torsion-rated cables [est; check torsion rating e.g. ±180°/m].
- **Service loop** at each joint sized for full range of motion plus margin; check the extreme poses in CAD/sim.
- **Strain relief** at every connector and where cable leaves a moving link; clamp the jacket, not the conductors.
- **Separation:** keep motor power (PWM, steppers) away from or perpendicular to signal lines (encoders, limit switches, I²C/SPI). Use twisted pairs for each stepper coil, shielded cable for encoders, shield grounded at one end (driver side) typically.
- **Connectors:** locking, keyed, rated for current; avoid Dupont jumpers for anything that moves. JST-XH/PH for signals, XT30/XT60 or screw terminals for power [typ hobby practice].
- Avoid sharp edges (chamfer cable holes, grommets), pinch points between links, and contact with hot motors.
- Wire gauge from current and length (voltage drop ≤ 2–5% [typ]); fuse to protect the wire.
- Label both ends; document a wiring diagram.
- Leave space: cable cross-section at a joint pass-through should be ≤ ~60% of the hole area [est].
- Plan cables in CAD from the start – "we'll route cables later" is the commonest reason arms get rebuilt.

---

## 12. Ergonomics and human factors

Anthropometry: design for the **5th–95th percentile** range of users; use 5th percentile for reach, 95th for clearance [typ; ISO 7250, NASA-STD-3000 / Pheasant "Bodyspace"].

Rules of thumb [typ; verify against anthropometric tables for the target population]:
- Power-grip handle diameter: ~30–40 mm; precision grip: ~8–16 mm.
- Push buttons: ≥ ~10–15 mm for fingertip, ≥ 25 mm for palm/E-stop actuators; spacing ≥ ~12–25 mm.
- Emergency stop: red mushroom on yellow background, easy to reach, latching, manual reset [std; ISO 13850, IEC 60204-1].
- Working height for light work at standing: ~elbow height to 100–150 mm below elbow; for seated, keep frequent controls within ~400 mm forward reach.
- Manual lifting: NIOSH lifting equation load constant 23 kg under ideal conditions; reduced by distance, height, frequency, twisting [std; NIOSH 1991].
- Hand operating forces: keep frequently used controls under ~10–20 N; occasional up to ~50 N [est].
- Hot surfaces: touchable metal surfaces kept below ~48–51 °C for brief contact [est; ISO 13732-1 gives curves by material and time].
- Edges and corners: break all edges (≥ 0.5 mm chamfer/radius) on anything handled; no sharp sheet metal edges.
- Feedback: every user action gets visible/audible/tactile feedback within ~100 ms.
- Labels readable at use distance; controls map spatially to what they move (stimulus-response compatibility: "up moves up").
- Noise: keep near-user noise below ~70 dBA for comfort; 85 dBA is a typical occupational action level [std; EU 2003/10/EC, OSHA hearing conservation].
- Maintenance ergonomics: can a hand + hex key reach every screw?

---

## 13. Aesthetics and industrial design basics

Good-looking machines look **intentional**. Principles:
- **Form follows function, honestly expressed:** let the load path and motion be readable (people trust an arm that looks stiff where it needs to be).
- **Consistency:** a small set of fillet radii (e.g. 2, 5, 10 mm), one chamfer size, consistent wall/edge thickness, matching fastener heads.
- **Proportion and hierarchy:** primary masses (base, links) → secondary (motor housings) → tertiary details (screws, labels). Taper links toward the tip – it looks right and puts mass where torque is lowest.
- **Alignment:** axes, edges, and parting lines line up; avoid near-misses (2 mm offsets look like mistakes; make offsets clearly deliberate).
- **Surface continuity:** tangent (G1) at minimum; curvature-continuous (G2) on prominent surfaces avoids visible highlight breaks.
- **Hide or celebrate** fasteners and cables – choose deliberately. Counterbore screw heads; route cables internally or in neat carriers.
- **CMF (colour, material, finish):** 1–2 main colours + 1 accent (often for moving parts or safety/interaction points); match layer lines direction to the form; matte hides print artefacts.
- **Parting lines and split lines:** place on edges or in deliberate grooves (a small reveal/shadow gap hides misalignment).
- **Visual weight:** dark colours and large flat areas look heavier; put them low.
- **Affordance:** handles look graspable; buttons look pressable; things that shouldn't be touched look like it (guards, colour).
- **Reduce clutter:** fewer visible parts is better – this aligns with DFA.
- Show the user something early (render, GLB) and iterate on feedback (Mechy standard 10, 11).

---

## 14. Cost

Cost components: materials + purchased parts + process (machine time) + assembly labour + tooling (amortised) + overhead + quality/scrap + shipping + service/warranty.

Rules:
- Part count drives cost more than part complexity, especially assembly and logistics [DFMA].
- **Purchased standard parts are usually cheaper and better** than custom (bearings, belts, extrusions).
- Fasteners: often cost more to install than to buy; reduce count and variety.
- Tolerance cost rises steeply (roughly exponentially) as tolerance tightens [typ, many sources].
- For 3D-printed parts: cost ≈ filament mass × price (~20–30 USD/kg FDM PLA/PETG [typ 2024–26]) + machine time; print time is often the bottleneck. Track grams per part (print_list.csv).
- Quantity changes the right process: 1–50 → print/CNC; 100–10k → injection moulding/die cast/sheet; tooling amortises.
- Quote real prices with source and date in bom.csv; flag estimates.
- **Should-cost** check: material × 2–4 for simple CNC parts in low volume is a crude sanity bound [est].
- Cost of failure: weigh the price of a better part against field failure (shipping, time, reputation).

---

## 15. Sustainability

- **Durability and repairability** beat recyclability: a machine that lasts 10 years beats one recycled after 2.
- Use standard fasteners, accessible screws (no glue where avoidable) so it can be repaired and disassembled.
- Minimise material: optimise infill and wall count for printed parts; topology-optimise only where it matters.
- Mono-material or easily separable assemblies (no metal inserts moulded into plastic where avoidable; mark plastic types with ISO 11469 codes, e.g. >PLA<, >PETG<).
- PLA is bio-based but **not home-compostable**; it needs industrial composting conditions (~58 °C+) [typ]. Don't claim otherwise.
- Energy: right-size motors and drivers; use idle current reduction on steppers; counterbalance gravity loads (springs) so motors don't hold torque continuously.
- Avoid restricted substances (RoHS: lead, mercury, cadmium, hexavalent chromium, some brominated flame retardants, phthalates) [std; EU 2011/65/EU].
- Design for end of life: list materials in the BOM.
- Life-cycle thinking: for most powered machines, use-phase energy and lifespan matter more than the plastic in the frame [est; LCA studies vary].

---

## 16. Safety: standards and design rules

### 16.1 Standards map (machine and robot safety)

| Standard | Topic | Notes |
|---|---|---|
| ISO 12100:2010 | Risk assessment and risk reduction – general principles (type A) | Core method; everything else builds on it |
| ISO 13849-1 / -2 | Safety-related parts of control systems (Performance Level PL a–e) | Determines required reliability of safety functions (E-stop, interlocks) |
| IEC 62061 | Functional safety of machine control (SIL) | Alternative to 13849 for electrical/electronic |
| IEC 60204-1 | Electrical equipment of machines | Wiring colours, E-stop categories, PE |
| ISO 13850 | Emergency stop function design | E-stop is a complementary measure, not a substitute for guarding |
| ISO 13857:2019 | Safety distances to prevent reaching hazard zones | Opening size vs distance tables |
| ISO 13854:2017 | Minimum gaps to avoid crushing body parts | Gap table by body part |
| ISO 13855 | Positioning of protective devices for approach speed | Light curtain distance S = K·T + C |
| ISO 14118 | Prevention of unexpected start-up | Lockout, stored energy |
| ISO 14119 | Interlocking devices with guards | Defeat resistance |
| ISO 14120 | Guards – design and construction | Fixed vs movable guards |
| ISO 10218-1 / -2 (2011; revised editions published 2025) | Industrial robots: robot (part 1) and robot systems/integration (part 2) | 2025 revision folds in much of ISO/TS 15066 content [verify edition] |
| ISO/TS 15066:2016 | Collaborative robots: biomechanical limits for contact | Power and force limiting values |
| ISO 13482 | Personal care robots | Service robots near people |
| OSHA 29 CFR 1910.212 / 1910.147 (US) | General machine guarding / lockout-tagout | US legal requirements |
| EU Machinery Directive 2006/42/EC → Machinery Regulation (EU) 2023/1230 (applies from 20 Jan 2027) | Legal framework for CE marking | Harmonised standards give presumption of conformity |

### 16.2 ISO 12100 method

1. **Determine limits** of the machine: intended use, reasonably foreseeable misuse, users (trained/untrained, children?), lifecycle phases (transport, assembly, setup, operation, cleaning, maintenance, disposal), space and time limits.
2. **Identify hazards:** mechanical (crushing, shearing, cutting, entanglement, drawing-in, impact, stabbing, friction/abrasion, ejection of parts, stored energy/springs), electrical, thermal, noise, vibration, radiation, materials/substances, ergonomic, environment, combinations.
3. **Estimate risk:** risk = f(severity of harm, probability of occurrence of harm). Probability considers exposure frequency/duration, probability of the hazardous event, and possibility of avoiding/limiting harm.
4. **Evaluate risk:** is it adequately reduced?
5. **Reduce risk – the three-step method, in this order:**
   1. **Inherently safe design** (remove the hazard: lower forces, speeds, energies; eliminate pinch points; round edges; low voltage; stable design).
   2. **Safeguarding and complementary protective measures** (guards, interlocks, light curtains, two-hand controls, E-stop, enabling devices).
   3. **Information for use** (warnings, manuals, training, PPE instructions, signs).
6. Iterate until risk is acceptable; document.

### 16.3 Mechanical hazards and minimum gaps

**Crushing gaps – ISO 13854 minimum gaps** (widely reproduced values [std; verify against the 2017 edition]):

| Body part | Minimum gap |
|---|---|
| Body | 500 mm |
| Head | 300 mm |
| Leg | 180 mm |
| Foot | 120 mm |
| Arm | 120 mm |
| Hand, wrist, fist | 100 mm |
| Toes | 50 mm |
| Finger | 25 mm |

Use: two parts that close on each other must either never get closer than the gap for the body part that can enter, or the opening must be too small for that body part to enter in the first place (≤ ~4 mm practically excludes fingertips per ISO 13857 [std]), or the force must be low enough not to injure.

**Reach-through safety distance – ISO 13857** (selected fingertip/finger values reproduced in guard-maker brochures, [std; verify]): opening ≤ 4 mm → ≥ 2 mm distance; 6–8 mm slot → ≥ 20 mm; 8–10 mm → ≥ 80 mm. Larger openings admit hands/arms and need much greater distances (hundreds of mm). For hobby/consumer devices: keep openings to moving belts/pulleys/gears ≤ 4–6 mm or fully enclose them.

**Pinch points on robot arms and mechanisms:**
- Belt-on-pulley in-running nip: always cover (a nip draws fingers in).
- Gear meshes: always enclose.
- Link-to-link closing angles (elbow folding onto upper arm): either keep ≥ 25 mm (finger) / ≥ 100 mm (hand) gap at full fold, or limit joint range in hardware, or add soft covers and force limits.
- Linear axis ends: carriages closing on end blocks; add bumpers and end gaps.
- Shear points: a moving edge passing a fixed edge – guard or gap.
- Rotating shafts and set screws: entanglement of hair/clothing; cover or use flush fittings.
- Stored energy: springs (counterbalance), gravity (arm falls at power loss), capacitors.

**Guarding hierarchy:** fixed guard (tools required to remove) > interlocked movable guard > presence-sensing (light curtain, scanner, safety mat) > hold-to-run / enabling device > warnings.

### 16.4 Robots: ISO 10218 and ISO/TS 15066

Collaborative operation modes (ISO 10218 / TS 15066):
1. **Safety-rated monitored stop (SMS):** robot stops when a human enters the collaborative space.
2. **Hand guiding (HG):** operator moves the robot by hand via a guiding device with enabling switch.
3. **Speed and separation monitoring (SSM):** robot slows/stops based on measured human distance; minimum protective separation distance from robot speed, stopping time, human speed (1.6 m/s walking speed used in ISO 13855 / TS 15066 formula [std]).
4. **Power and force limiting (PFL):** contact may occur but forces/pressures stay below biomechanical limits.

**TS 15066 body model – maximum permissible quasi-static contact force** (Annex A, as reproduced in arXiv:2311.13814 Table 1 and other secondary sources) [std; verify]:

| Body region | Max force (N) | Effective spring const. (N/mm) | Effective mass (kg) |
|---|---|---|---|
| Skull and forehead | 130 | 150 | 4.4 |
| Face | 65 | 75 | 4.4 |
| Neck | 150 | 50 | 1.2 |
| Back and shoulders | 210 | 35 | 40 |
| Chest | 140 | 25 | 40 |
| Abdomen | 110 | 10 | 40 |
| Pelvis | 180 | 25 | 40 |
| Upper arms and elbows | 150 | 30 | 3 |
| Lower arms and wrists | 160 | 40 | 2 |
| Hands and fingers | 140 | 75 | 0.6 |
| Thighs and knees | 220 | 50 | 75 |
| Lower legs | 130 | 60 | 75 |

- Transient (impact, the body can recoil) contact limits are commonly **2x the quasi-static values** for most regions; **head/face/neck contact should be avoided entirely** in design [std, as commonly interpreted; verify in Annex A]. TS 15066 also lists pressure limits per body region (N/cm²), which often bind first for sharp or small contact areas – so round and pad contact surfaces.
- Permissible relative speed from energy transfer: `E = F² / (2k) = ½ μ v²` → `v_max = F / sqrt(μ·k)`, with reduced mass `μ = (1/m_H + 1/m_R)⁻¹` (m_H = body-region effective mass, m_R = robot effective moving mass) [TS 15066 Annex A].
  - Worked example [computed]: hand (F = 140 N, k = 75 000 N/m, m_H = 0.6 kg), robot effective mass m_R = 2 kg → μ = 0.46 kg → v_max ≈ 140 / sqrt(0.46 × 75 000) ≈ 0.75 m/s (quasi-static limit; transient 2x force would give ~1.5 m/s). Shows why **light distal links** matter for safety, not just performance.
- Design implications for hobby/desktop arms near people:
  - Low moving mass, low gear ratio / back-drivable or current-limited drives, compliant (padded, rounded) covers, no sharp tools near face height.
  - Collision detection via motor current/encoder following error; limit speed near humans.
  - Clamping (quasi-static) is worse than free impact: avoid configurations that trap a hand between the arm and a table or the arm's own links.
  - Industrial cobots claim PFL compliance only after application-level risk assessment; the robot alone isn't "safe", the application is.

### 16.5 Electrical and control safety basics (for mechanical designers)

- E-stop: stop category 0 (immediate power removal) or 1 (controlled stop then power removal) [std; IEC 60204-1]. Must be hard-wired or safety-rated, not just a software flag, for real machines.
- Power-loss behaviour: what does each axis do when power drops? Gravity-loaded axes need brakes, non-back-drivable drives, or counterbalance.
- Restart: no automatic restart after power returns or E-stop reset.
- Limit switches: use normally-closed wiring so a broken wire reads as "triggered" (fail-safe).
- Low voltage (≤ 24–48 V DC) for anything users touch; mains wiring enclosed, earthed, fused; use certified PSUs.
- Thermal: thermal fuses/cut-outs on heaters; motor driver over-temperature protection.

---

## 17. Comprehensive design-review checklist

Use at concept review (C), detail review (D) and pre-build review (B). Each item: Pass / Fail / N/A + note.

### 17.1 Requirements and process
- [ ] (C) Spec table exists with numbered requirements, targets, thresholds, verification methods.
- [ ] (C) Environment, life (cycles), duty cycle, and users defined.
- [ ] (C) Benchmark/open-source base identified and credited.
- [ ] (C) ≥ 2 concepts compared in a numbers-backed table; conventional option first.
- [ ] (C) Selection rationale and sensitivity of the decision recorded.
- [ ] (D) Each requirement traces to a design feature and a test.
- [ ] (B) Riskiest assumption has been prototyped or analysed and verified against closed-form.

### 17.2 Kinematics and constraint
- [ ] Each part's DOF counted; no unintended over- or under-constraint.
- [ ] Bearing arrangement: one locating, one floating (or properly preloaded pair).
- [ ] Parallel guides: one reference, the other aligned or floating.
- [ ] Couplings between separately supported shafts are flexible.
- [ ] Joint ranges checked for collisions at extremes; hard stops present and stronger than motors.
- [ ] Singularities and workspace verified (random-pose check, e.g. 500 poses).

### 17.3 Stiffness, strength and load path
- [ ] Load path traced from payload to ground; each element's load type identified.
- [ ] Deflection at tool point estimated (series stiffness) and within error budget.
- [ ] First natural frequency estimated; ≥ 3–5x control bandwidth [est].
- [ ] Closed sections for torsion; no long slots in torsion members.
- [ ] Overhangs minimised; bearing spans adequate for moment loads.
- [ ] Static stress with safety factor; buckling checked for slender compression members.
- [ ] Fatigue: cycles counted; stress concentrations filleted; Goodman check where cyclic.
- [ ] Printed parts oriented so critical loads are in-plane (not across layers).
- [ ] Bolted joints: preload method defined; metal-to-metal clamp where plastic would creep.

### 17.4 Actuation and transmission
- [ ] Torque budget per joint with ≥ 50% margin (incl. acceleration, friction, speed derating).
- [ ] Belt: tooth count in mesh ≥ 6, pulley ≥ manufacturer min, closed-loop length is a stock size, tension method defined.
- [ ] Backlash budget and its effect at the tool.
- [ ] Motor heat path doesn't soften printed parts.
- [ ] Power-loss/back-drive behaviour defined (brake, counterbalance, or acceptable).
- [ ] Homing sensor per axis; fail-safe wiring.

### 17.5 Precision and thermal
- [ ] Error budget at tool point (systematic summed, random RSS).
- [ ] Abbe offsets identified and minimised.
- [ ] Thermal sources identified; CTE mismatches checked on fits and long joints.
- [ ] Service temperature ≥ 20 K below Tg/HDT for loaded plastic parts [est].
- [ ] Adjustment provisions where tolerance stacks exceed requirement; adjustments lockable.

### 17.6 Manufacturing and assembly
- [ ] Every part checked against its process rules (overhangs, walls, radii, draft, bends).
- [ ] Tolerances only on functional features; stack-up done for critical chains.
- [ ] Part count reviewed with the three DFA questions; fasteners minimised and standardised.
- [ ] Self-locating features (chamfers, pilots, dowels); top-down assembly where possible.
- [ ] Poka-yoke: similar-looking parts can't be swapped or are clearly marked; connectors keyed.
- [ ] Tool access for every fastener; hex key swing room.
- [ ] Assembly order written and tested in CAD (exploded view).
- [ ] STL per printed part, print_list.csv (material, orientation, grams), bom.csv with sources.

### 17.7 Reliability, failure modes, maintenance
- [ ] DFMEA done for main functions; all S ≥ 9 items have actions.
- [ ] Loosening: positive locking or thread locker on vibration-exposed metal threads; no reliance on split washers; set screws on flats.
- [ ] Creep: no sustained high stress in plastics; press fits backed by retainers.
- [ ] Wear parts identified, cheap, replaceable, accessible.
- [ ] Galvanic pairs checked for the environment; isolation where needed.
- [ ] Cable flex life: flex-rated cable, bend radius ≥ datasheet, strain relief, service loops verified at extreme poses.
- [ ] Lubrication specified (or self-lubricating materials).
- [ ] Spare parts list and maintenance intervals documented.

### 17.8 Safety
- [ ] ISO 12100-style hazard list for all lifecycle phases, including foreseeable misuse.
- [ ] Inherently safe measures applied first (force, speed, energy, gaps).
- [ ] Pinch/crush gaps meet ISO 13854 values or openings ≤ ~4 mm, or force-limited.
- [ ] Belts, gears, and in-running nips enclosed.
- [ ] E-stop reachable, latching, hard-wired where required; no auto-restart.
- [ ] Stored energy (springs, gravity, capacitors) controlled.
- [ ] Collaborative robot: contact forces/speeds checked against TS 15066 values for exposed body regions; head-height contact designed out.
- [ ] Edges broken; hot surfaces guarded or labelled.
- [ ] Electrical: low voltage for touchable parts, fused, PE where mains, certified PSU.
- [ ] Warnings/labels and user instructions written.

### 17.9 Ergonomics, aesthetics, cost, sustainability
- [ ] Controls and handles sized for 5th–95th percentile users; feedback for each action.
- [ ] Consistent radii/chamfers/colours; cables managed; visible fasteners deliberate.
- [ ] Render/GLB shown to the user.
- [ ] BOM cost within threshold; prices sourced and dated; estimates labelled.
- [ ] Repairable with standard tools; materials listed for end of life.

### 17.10 Documentation and verification
- [ ] Verification table (Check | Expected | Got | PASS/FAIL) for every analysis that drove a decision.
- [ ] Every number labelled (measured / datasheet / computed / estimate).
- [ ] "Not verified" and "Open decisions" lists present.
- [ ] Rebuild command for each artifact.

---

## 18. Classic beginner mistakes

Design process
1. No numbers in the requirements ("strong enough", "fast").
2. Falling in love with the first concept; no comparison with the conventional solution.
3. Designing the whole thing in detail before testing the riskiest part.
4. Picking a motor from a hunch – no torque budget, forgetting acceleration torque and stepper torque drop with speed.
5. Treating CAD as reality: no tolerances, no clearance for print shrink or assembly.
6. Leaving cables, fasteners and assembly order "for later".
7. No error budget – then surprised by 3 mm of slop at the tool.

Mechanics
8. Designing for strength, ignoring stiffness → floppy arm that never breaks but never works.
9. Putting motors on distal links ("just add a bigger motor at the base") – cascading mass.
10. Long cantilevers and open sections in torsion; slots along tubes.
11. Overconstraining: two rigid parallel rails, shaft in three bearings, both bearings axially fixed.
12. Single bearing carrying a moment load (tilts, wears out fast).
13. Set screw on a round shaft (it slips; use a D-flat or clamp).
14. Belt with too few teeth in mesh, pulleys too small, no tensioner, or belt length that isn't a stock size.
15. Backlash ignored in gear/belt trains; drive placed off the axis of the guide (racking).
16. Hard stops weaker than the motor, or none at all.

Materials and printing
17. Loading printed parts across layer lines.
18. PLA next to a hot motor, in a car, or in the sun.
19. Expecting printed press fits and threads to hold preload long-term (creep).
20. Holes exactly nominal in CAD for a printed part (they print undersize).
21. Using "100% infill" as the fix for a bad geometry instead of more perimeters/better shape.

Fasteners and joints
22. Mixing many screw sizes and drive types.
23. Trusting split lock washers against vibration.
24. Over-torquing screws into plastic or heat-set inserts; using thread locker on plastic (crazing).
25. Screw heads with no tool access once assembled.

Failure and safety
26. Forgetting fatigue: counting load once instead of millions of cycles.
27. Dissimilar metals outdoors with no isolation (stainless screws in aluminium in salt air; aluminium on carbon fibre).
28. Exposed belt nips and gears; link pinch points sized just right to trap a finger.
29. Arm collapses when power is cut (gravity-loaded axis, no brake/counterbalance).
30. Software-only E-stop; limit switches wired normally-open (broken wire = no stop).
31. Thinking "it's small, so it's safe" – a 2 kg arm moving at 1 m/s can exceed TS 15066 hand limits.

Electrical and cables
32. Solid-core or non-flex cable through moving joints; no strain relief; Dupont jumpers in moving harnesses.
33. Stepper wiring bundled with encoder/limit switch lines with no twisting or shielding.
34. Undersized wires and no fuse.

Manufacturing and cost
35. Tight tolerances everywhere (cost explodes) or nowhere (nothing fits).
36. Custom-made parts where a standard bearing/extrusion/bracket exists.
37. No assembly instructions; parts that look alike but aren't interchangeable and aren't marked.
38. Unsourced BOM prices and placeholder numbers presented as facts.

---

## 19. Quick decision tables

**Structure choice for a desktop arm link** [est]:

| Need | Use |
|---|---|
| Fast iteration, low load (< 0.3 kg payload, < 300 mm reach) | All-printed link, ribbed/hollow closed section, PETG/PLA+ |
| Medium load or reach > 300 mm | Al or CFRP tube / 2020 extrusion core + printed joint nodes |
| High stiffness, precision | Machined aluminium or CFRP tube with bonded metal inserts |

**Joint location/retention method** [typ]:

| Need | Use |
|---|---|
| Repeatable removable mount | Kinematic coupling (3 balls / 3 grooves) |
| Permanent accurate location | Dowel pins (one round, one diamond/slot) + screws |
| Quick adjust then lock | Slots + clamp screws, then pin if needed |
| Torque transmission to shaft | Keyway, D-flat + clamp, spline, or clamp hub (not set screw alone) |

**Fastener locking** [typ]:

| Situation | Use |
|---|---|
| Metal threads, vibration, serviceable | Medium-strength thread locker or wedge-lock washers, good preload |
| Into plastic | Heat-set insert + modest torque; Belleville washer to keep load; no anaerobic thread locker |
| Must never come loose (safety) | Positive lock: castellated nut + cotter pin, safety wire, prevailing-torque nut |

**Safety measure choice** (ISO 12100 order):

| Hazard | First choice | Second | Last |
|---|---|---|---|
| Belt/gear nip | Enclose fully | Interlocked cover | Warning label |
| Link pinch point | Gap ≥ ISO 13854 or ≤ 4 mm opening | Joint range limits, soft covers, force limit | Warning |
| Gravity fall at power loss | Counterbalance / non-back-drivable drive | Brake | Instruction |
| Human contact with moving arm | Low mass, low speed, rounded padded covers | Collision detection, SSM | Training |

---

## Canonical references

Books (paid unless noted):
- Slocum, A. H., *Precision Machine Design*, Prentice Hall/SME, 1992. The precision-engineering bible. Slocum's MIT course material and the "FUNdaMENTALs of Design" topics are free (below).
- Blanding, D. L., *Exact Constraint: Machine Design Using Kinematic Principles*, ASME Press, 1999.
- Hale, L. C., *Principles and Techniques for Designing Precision Machines*, PhD thesis, MIT/LLNL, 1999 – **free** via OSTI: https://www.osti.gov/biblio/9745
- Smith, S. T., *Foundations of Ultraprecision Mechanism Design*, CRC, 1992; Smith, *Flexures*, CRC, 2000.
- Budynas & Nisbett, *Shigley's Mechanical Engineering Design* (fatigue, bolts, fits, safety factors).
- Juvinall & Marshek, *Fundamentals of Machine Component Design*.
- Ullman, D. G., *The Mechanical Design Process* (requirements, Pugh, decision matrices).
- Ulrich & Eppinger, *Product Design and Development* (specs, concept selection).
- Pahl & Beitz, *Engineering Design: A Systematic Approach*.
- Boothroyd, Dewhurst & Knight, *Product Design for Manufacture and Assembly*.
- Bickford, J. H., *An Introduction to the Design and Behavior of Bolted Joints*.
- Pilkey, *Peterson's Stress Concentration Factors*; Young & Budynas, *Roark's Formulas for Stress and Strain*.
- Pheasant & Haslegrave, *Bodyspace* (anthropometry/ergonomics).
- Norman, D., *The Design of Everyday Things* (affordances, feedback, mapping).
- Ashby, M., *Materials Selection in Mechanical Design* (E/ρ, material indices).

Free courses and notes:
- MIT OCW 2.007 Design and Manufacturing I – https://ocw.mit.edu/courses/2-007-design-and-manufacturing-i-spring-2009/ (free)
- MIT OCW 2.72 Elements of Mechanical Design – https://ocw.mit.edu/courses/2-72-elements-of-mechanical-design-spring-2009/ (free)
- MIT OCW 2.75 Precision Machine Design – https://ocw.mit.edu/courses/2-75-precision-machine-design-fall-2001/ (free)
- Slocum, "FUNdaMENTALs of Design" (MIT 2.007 reading) – https://meddevdesign.mit.edu/ and web.mit.edu/2.75/resources (free; URLs move – search "Slocum FUNdaMENTALs")
- Slocum, kinematic coupling review article – https://web.mit.edu/course/2/2.70/Reading%20Materials/Kinematic%20coupling%20review%20article.pdf (free)
- NASA RP-1228, *Fastener Design Manual* (Barrett, 1990) – https://ntrs.nasa.gov/citations/19900009424 (free, public domain)
- NIOSH Revised Lifting Equation – https://www.cdc.gov/niosh/docs/94-110/ (free)
- OSHA 3170, *Safeguarding Equipment and Protecting Employees from Amputations* – https://www.osha.gov/sites/default/files/publications/osha3170.pdf (free)
- OSHA machine guarding eTool – https://www.osha.gov/etools/machine-guarding (free)

Standards (paid unless noted):
- ISO 12100:2010; ISO 13849-1:2023; ISO 13850; ISO 13854:2017; ISO 13855; ISO 13857:2019; ISO 14118; ISO 14119; ISO 14120; IEC 60204-1; ISO 10218-1/-2 (2025 editions); ISO/TS 15066:2016; ISO 286-1/-2; ISO 2768-1; ISO 281; ISO 9283; ISO 7250; ISO 13732-1; ISO 11469.
- AIAG & VDA FMEA Handbook (2019).
- MIL-STD-889 (galvanic compatibility) – free from US DoD ASSIST: https://quicksearch.dla.mil/
- EU Machinery Regulation (EU) 2023/1230 – free on EUR-Lex: https://eur-lex.europa.eu/eli/reg/2023/1230/oj
- OSHA 29 CFR 1910.212, 1910.147 – free: https://www.ecfr.gov/

Web references used for cross-checking (free):
- Engineers Edge, galvanic compatibility/anodic index – https://www.engineersedge.com/galvanic_capatability.htm
- Carr Lane, anodic index guideline – https://www.carrlane.com/engineering-resources/technical-information/galvanic-corrosion/practical-guideline-for-the-anodic-index-of-materials-in-different-environments
- RoyMech safety factors – https://roymech.org/Useful_Tables/ARM/Safety_Factors.html
- Engineering Toolbox factors of safety – https://www.engineeringtoolbox.com/factors-safety-fos-d_1624.html
- Boothroyd Dewhurst DFA / part consolidation – https://www.dfma.com/resources/part-consolidation.asp
- Accendo Reliability, design for assembly – https://accendoreliability.com/design-for-assembly/
- arXiv 2311.13814 (reproduces ISO/TS 15066 body model table) – https://arxiv.org/abs/2311.13814
- A3 / automate.org, "ISO/TS 15066 Explained" – https://www.automate.org/tech-papers/iso-ts-15066-explained
- Troax safety guide (reproduces ISO 13857 tables) – https://www.troax.com/app/uploads/Brochure-Safety-Guide_EN.pdf
- igus chainflex cable bend-radius guidance – https://www.igus.com/ (product datasheets)
- SKF bearing arrangements and fits – https://www.skf.com/ (free online engineering data)
- MatWeb material property database – https://www.matweb.com/ (free tier)

---

## Gaps / not verified

- **ISO/TS 15066 values** were cross-checked against one secondary reproduction (arXiv:2311.13814) and match common citations; the "transient = 2x quasi-static" rule, the pressure limits (N/cm²), and the treatment of head/face contact were **not** checked against Annex A. The 2025 ISO 10218 revision may have changed values/structure – verify.
- **ISO 13854 gap table** values are from memory of widely reproduced figures; searches confirmed the standard's scope but not the table. Verify against ISO 13854:2017.
- **ISO 13857 opening/distance values** came from one guard maker's brochure; only small-opening fingertip values are quoted. Larger-opening values are not given here.
- **Galvanic anodic index** allowable differences: two secondary sources disagree slightly on environment mapping; current MIL-STD-889 uses galvanic current, not potential.
- **Safety-factor bands** vary between sources (RoyMech/Engineering Toolbox vs textbooks); the Juvinall table was not directly checked.
- **FDM property numbers** (E, CTE, Tg, fatigue %, layer strength %, fit clearances, insert torques) are estimates; they vary strongly with printer, material brand and settings. Print test coupons.
- **Boothroyd t_ideal = 3 s** (2.93 s in one source) and typical DFA index ranges were not confirmed from a primary Boothroyd Dewhurst document.
- **"70–80% of cost committed at design"** and the "rule of tens" are widely repeated industry heuristics, not rigorously sourced.
- Cable bend-radius and torsion numbers are generic; always use the specific cable's datasheet.
- ISO 2768-m tolerance values and ISO 286 fit uses are summarised from memory of common tables; check the standard or a fits calculator for exact limits.
- Ergonomic numbers (handle diameters, button sizes, forces, hot-surface temperatures) are general rules of thumb; check ISO 7250/ISO 13732-1 and population-specific data for products.
- EU Machinery Regulation 2023/1230 application date (20 Jan 2027) is from memory – verify on EUR-Lex.
