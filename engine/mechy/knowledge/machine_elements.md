# Machine elements: practical reference for Mechy agents

Scope: the parts a small mechanism (3D-printed robot arm, gantry, gripper, turntable) is built from:
bearings, bushings, shafts, gears, belts, screws, fasteners, springs, couplings, linear guides,
brakes and clutches, capstan drives and linkages. The level is Shigley, Norton or Juvinall, cut down
to the rules, formulas and numbers you act on.

How to read the numbers: every value carries a tag.
- **[DS]** comes from a manufacturer datasheet or catalogue (named).
- **[STD]** comes from a standard (ISO or DIN).
- **[TXT]** is a textbook principle or first-pass value (Shigley, Norton, Slocum), summarised.
- **[CALC]** was computed here from a formula shown in this file.
- **[EST]** is an estimate or rule of thumb. Check it before it drives a decision.

Before you use a catalogue number in a design, check it against the datasheet of the part you will
actually buy. Ratings differ by about 5 to 20% between brands (for example, a 608 is rated 3.3 kN by
Timken and 3.45 kN by SKF).

---

## 0. Quick decision tables

### 0.1 Which rotary support?
| Situation | Use | Why |
|---|---|---|
| Rotating shaft, radial load, small mechanism | Deep-groove ball bearing (608, 625, 6800 series) | Cheap, sealed, takes some axial load, very common |
| Joint must resist a tipping moment (arm shoulder, turntable) | Two bearings spaced well apart, or an angular-contact pair (back-to-back), or a crossed-roller or slewing bearing | One bearing gives almost no moment stiffness |
| Large hollow joint, cables through the centre | Thin-section (6800/6900 series, Kaydon-type) or a "lazy susan" slewing ring | Big bore, small cross-section |
| Pure axial load (turntable resting on a base, screw thrust) | Thrust ball bearing (51100 series, F8-16M) plus radial bearings for location | A thrust bearing has no radial capacity |
| Slow oscillation, dirty conditions, low cost, low precision | Plain bushing (sintered bronze, igus polymer, PTFE-lined) | No balls to brinell; tolerates shock |
| Very compact radial support on a hardened shaft | Drawn-cup needle bearing (HK0810 and similar) | Needs a shaft of about HRC 58 or a separate inner ring |
| Zero backlash with high moment stiffness in one part | Crossed-roller bearing | Expensive, but it carries radial, axial and moment loads |

### 0.2 Which transmission?
| Need | First choice | Ratio per stage | Backlash (typical) | Efficiency (typical) | Backdrives? |
|---|---|---|---|---|---|
| Move the motor off the moving link to the base | GT2 or HTD timing belt | 1:1 to 1:5 (more if the pulleys are big) | Low (tooth clearance plus stretch) | 95–98% [EST] | Yes |
| High ratio, compact, printable | Planetary gearbox | 3–10 | 0.5–2° when printed; 3–15 arcmin precision | 90–97% | Yes |
| High ratio, shock-tolerant, low backlash | Cycloidal drive | 10–100 | below 1–10 arcmin | 75–90% [EST] | Partly |
| Very high ratio, almost no backlash, thin | Strain wave (harmonic) | 30–160 | below 1 arcmin (but it is torsionally compliant) | 60–80% | Weakly |
| Right angle, self-locking, high ratio | Worm gear | 5–100 | Medium | 30–90% (lower at high ratio) | Often not (not guaranteed) |
| Zero backlash, smooth, transparent (for force control) | Capstan cable drive | 5–20 | ≈0 | ≈95%+ [EST] | Yes, very easily |
| Rotary to linear, cheap, should hold position | Trapezoidal lead screw | – | 0.05–0.3 mm unless the nut is preloaded | 25–70% | Depends on the lead (§6) |
| Rotary to linear, precise, efficient | Ball screw | – | 0–0.02 mm | ≈90% | Always, so a vertical axis needs a brake |
| Rotary to linear, long travel, fast | Belt with a carriage | – | Low | High | Yes |

### 0.3 Which linear guide?
| Need | Use |
|---|---|
| Cheap, printers, low moment loads | Ground rod plus LM8UU/LM10UU/LM12UU, or igus polymer bushings |
| Stiff, compact, moment-capable | Profile rail (MGN9/MGN12/MGN15, HIWIN-type) |
| Long travel on aluminium extrusion | V-slot wheels on 2020/2040 |
| Very dirty, low precision | Polymer plain slides (igus drylin) |

---

## 1. Rolling bearings

### 1.1 Types and what each one does
- **Deep-groove ball bearing (DGBB, 6xxx series):** carries radial load plus moderate axial load in both
  directions. It is the default choice. "ZZ" or "2Z" means metal shields (low friction, poor sealing).
  "2RS" or "2RS1" means rubber contact seals (better sealing, a little more drag). [DS SKF]
- **Angular-contact ball bearing (7xxx series):** carries a large axial load in one direction. It is
  used in pairs:
  - Back-to-back (DB, "O" arrangement): the load lines spread out, giving high moment stiffness. Best
    for robot joints and spindles.
  - Face-to-face (DF, "X" arrangement): tolerates misalignment and has low moment stiffness.
  - Tandem (DT): both carry axial load in the same direction.
- **Four-point contact:** one bearing carries axial load both ways plus some moment load. Common in
  slewing rings.
- **Crossed-roller:** rollers sit at alternating 90° angles. One bearing carries radial, axial and
  moment loads with high stiffness. It is the standard output bearing in harmonic and cycloidal
  robot joints. [DS THK RB/RU series]
- **Thrust ball bearing (511xx single direction):** axial only. It must be centred by something else,
  and it skids at high speed with low axial load.
- **Tapered roller:** carries heavy combined radial and axial load. Used in pairs and needs set-up
  preload. More than small mechanisms need.
- **Needle (drawn cup HK, or caged):** very thin radial section. The raceway is the shaft, which must be
  hardened (about HRC 58 or more) and ground. [DS INA/Schaeffler]
- **Thin-section (6700/6800/6900 series, Kaydon Reali-Slim):** big bore with a small cross-section.
  Good for hollow joints.
- **Flanged (F-prefix, e.g. F608ZZ, F624ZZ):** the flange takes axial location, so you can drop the
  bearing into a plain printed hole with no shoulder and no circlip. Used for idlers.

### 1.2 Common sizes (d × D × B mm, approximate dynamic C and static C0)
Ratings are approximate catalogue values. Brands differ, so check the part you actually buy.

| Bearing | d×D×B (mm) | C (kN) | C0 (kN) | Source / status |
|---|---|---|---|---|
| 623 | 3×10×4 | ≈0.5 | ≈0.2 | [EST] typical catalogue values |
| 624 / F624 | 4×13×5 | ≈1.0–1.3 | ≈0.35–0.5 | [EST] |
| 625 | 5×16×5 | 1.14 | 0.38 | [DS SKF 625-2Z, via distributors] |
| 626 | 6×19×6 | ≈2.3–2.6 | ≈0.9–1.0 | [EST] |
| **608** | 8×22×7 | 3.3–3.45 | 1.37–1.4 | [DS SKF 608-2RSH 3.45/1.37; Timken 608-2RS 3.3/1.4] |
| 6000 | 10×26×8 | ≈4.6–4.75 | ≈2.0 | [EST] from SKF tables |
| 6001 | 12×28×8 | ≈5.1–5.4 | ≈2.4 | [EST] |
| 6200 | 10×30×9 | ≈5.1–5.4 | ≈2.4 | [EST] |
| 6800 (61800) | 10×19×5 | ≈1.4–1.7 | ≈0.6–0.8 | [EST] not verified |
| 6805 (61805) | 25×37×7 | 4.36 | 2.6 | [DS distributor listing 61805-2RS] |
| 6806 (61806) | 30×42×7 | ≈4.5 | ≈3 | [EST] |
| 6808 (61808) | 40×52×7 | ≈5 | ≈3.5–4 | [EST] |
| 6810 (61810) | 50×65×7 | ≈6–6.5 | ≈5–6 | [EST] |
| 51100 thrust | 10×24×9 | ≈10 | ≈14 | [EST] |
| 51105 thrust | 25×42×11 | ≈18–20 | ≈30–40 | [EST] not verified |
| F8-16M thrust | 8×16×5 | small (≈1–2) | – | [EST] |
| LM8UU (linear) | 8×15×24 | 0.26 | 0.40 | [DS Adafruit/Samick-type listings] |
| LM10UU (linear) | 10×19×29 | ≈0.37 | ≈0.55 | [EST] |
| LM12UU (linear) | 12×21×30 | ≈0.51 | ≈0.78 | [EST] |
| HK0810 needle | 8×12×10 | ≈2.5–3 | ≈2.5–3 | [EST] needs a hardened shaft |

The 6800 series is the "thin" family: the same bore as 6000 with a much smaller outside diameter, and
less than half the load rating. For robot arm joints, the 6805 to 6810 sizes give big hollow bores for
cables.

### 1.3 Load ratings and L10 life (ISO 281)
- **C (basic dynamic load rating):** the load at which 90% of bearings survive 10⁶ revolutions.
  [STD ISO 281]
- **C0 (basic static load rating):** the load that causes permanent raceway deformation of about
  0.0001 × the rolling element diameter. [STD ISO 76]
- **Basic life:**
  `L10 = (C / P)^p` in millions of revolutions, where p = 3 for ball bearings and p = 10/3 for roller
  bearings.
- **In hours:** `L10h = 10^6 / (60 n) × (C / P)^p`, with n in rpm.
- **Equivalent dynamic load for a DGBB:** `P = X·Fr + Y·Fa`.
  - If Fa/Fr ≤ e, then P = Fr.
  - Otherwise, take X = 0.56 and Y ≈ 1.0–2.3. Y and e depend on f0·Fa/C0, so look them up in the
    catalogue. [DS SKF]
- **Equivalent static load:** `P0 = 0.6·Fr + 0.5·Fa`, and never less than Fr. [DS SKF, DGBB]
- **Static safety factor:** `s0 = C0 / P0`.
  - s0 ≥ 1 for smooth, quiet operation.
  - s0 ≥ 1.5–2 for shock loads or high-precision running.
  - s0 ≥ 2–3 for slow oscillating joints that take impacts. [DS SKF; EST for the robot case]
- **Reliability factor a1 (multiplies L10):**

  | Reliability | a1 |
  |---|---|
  | 90% | 1 |
  | 95% | 0.64 |
  | 99% | about 0.25 |

  [STD ISO 281]
- **Oscillating joints:** an equivalent revolution is about 2 × swing angle / 360° for each
  back-and-forth cycle. [EST]
- **Very small oscillations (under a few degrees) cause false brinelling and fretting.** Use grease
  plus preload, or a bushing.

**The rule for slow robot arms:** at 10–60 rpm, fatigue life is almost never what limits you.
1. Static capacity (s0) sets the size.
2. Moment stiffness sets the size.
3. Mounting in plastic sets the size.
4. Seal drag can set it too: a 2RS 608 has about 1–3 N·mm of seal friction torque. [EST]

**Worked example [CALC].**
1. A 608 with C = 3.3 kN, C0 = 1.37 kN carries Fr = 200 N at 30 rpm.
2. L10 = (3300/200)³ = 4,492 × 10⁶ rev.
3. L10h = 4.49e9 / (60 × 30) ≈ 2.5 million hours.
4. s0 = 1370/200 = 6.9.
5. Result: fine. The real question is whether the plastic housing creeps under 200 N.

### 1.4 Moment loads: never ask one bearing to resist a moment
Two bearings spaced s apart turn a moment M into a radial couple, `F = M / s`, on each bearing.

Example [CALC]: an arm puts 5 N·m on the shoulder.
- Bearings 20 mm apart: 250 N each.
- Bearings 60 mm apart: 83 N each.

Rule: make the spacing at least 1 to 2 shaft diameters, and as large as the package allows. [EST]

A single DGBB has internal clearance (C0 or CN class, roughly 5–20 µm radial on small sizes), so on
its own it tilts by about 0.1–0.5°. [EST]

### 1.5 Mounting arrangements
**Fixed-floating (the default for a shaft on two bearings).**
1. One bearing is "locating". It is clamped axially on both rings (shoulder plus circlip or nut) and
   takes all the axial load in both directions.
2. The other bearing is "non-locating". One of its rings, usually the outer ring in the housing, can
   slide axially, so thermal growth and printing tolerances do not load the bearings against each
   other. [DS SKF]

**Cross-located (two-bearing "fixed-fixed" in opposition).**
- Each bearing takes axial load in one direction.
- This works for short shafts with little thermal change. In printed assemblies it is common, but it
  needs a shim or spring so you do not overload both bearings.

**Preloaded pairs.**
- Back-to-back angular contact, or two DGBBs pushed apart by a wave washer.

**Fits** (ring that rotates relative to the load direction gets interference). [DS SKF; TXT Shigley]
- Rotating shaft with a fixed load direction: inner ring interference (shaft k5/j6), outer ring
  location fit (housing H7).
- The load rotates with the housing, for example an arm link that pivots on a fixed pin: the
  outer ring needs the tight fit.
- A ring that is loose against a load rotating relative to it "creeps", and that wears the seat.

**Printed housings [EST, from practice].**
- Printed bores come out undersize. Design the 608 bore at 22.0–22.15 mm and print a test coupon
  for each printer and material.
- Relying on press fit alone in PLA or PETG is risky because the plastic creeps and relaxes. Add a
  shoulder plus a printed or metal retaining cap held with screws.
- Clamp the inner ring axially with shaft shoulders, spacers (a printed tube, or better an aluminium
  tube), and a nut or e-clip.
- Leave 0.2–0.5 mm of axial room at the floating bearing.

### 1.6 Preload
- **Why preload:** it removes internal clearance, raises stiffness, and cuts noise and ball skidding.
- **DGBB spring preload (SKF guideline):** `F = k·d`, with F in N, d = bore in mm, and k = 5–10.
  Example: a 608 needs about 40–80 N axial. [DS SKF]
  - Apply it with a wave spring or Belleville washer on the outer ring of the floating bearing.
- **Angular contact pairs:** buy them as matched pairs with preload classes (light, medium, heavy). Or
  set the preload with a precision spacer or by grinding the spacer.
- **Linear guides:** preload classes are Z0 (light clearance), ZA (light preload, about 0.02 C) and ZB
  (medium preload, about 0.05–0.07 C). [DS HIWIN]
- **Too much preload** costs friction torque and life, and heats the bearing. In printed parts, the
  plastic relaxes and you lose the preload, so springs are more robust than rigid stack-ups.

### 1.7 Bearing mistakes to avoid
- Using a thrust bearing as the only support of a turntable. It needs radial location as well.
- Pressing a bearing in by pushing through the balls (pushing the outer ring onto a shaft). That
  brinells the races. Press only on the ring that is being fitted.
- Using an M8 threaded rod as an 8 mm bearing shaft. The thread crests make a poor fit and the shaft
  wobbles. Use a ground 8 mm rod or a shoulder bolt.
- Using a needle bearing on a soft shaft.
- Cantilevering a load far from a single bearing.
- Forgetting that ZZ shields let dust in.

---

## 2. Plain bushings
- **Design check:** p = F / (d·L) in MPa (projected area), v = surface speed in m/s. Keep p, v and
  p·v under the material's limits.

  | Material | Max p (MPa) | Max v (m/s) | PV (MPa·m/s) | Notes |
  |---|---|---|---|---|
  | Oil-impregnated sintered bronze (Oilite) | ≈14 static, lower when moving | ≈6 | ≈1.75 | [EST, common catalogue values]. Avoid very slow oscillation, where no oil film forms. |
  | PTFE-lined steel-backed (DU-type) | ≈50+ static | ≈2 | ≈1–3.6 (short duty) | [EST from GGB-type catalogues]. Dry running. |
  | igus iglidur (G, J etc.) | ≈35–80 depending on grade | ≈0.5–1.5 rotating | grade-specific | [DS igus]. Use the igus online life calculator. |
  | POM / nylon (machined) | ≈5–10 | ≈0.5–1 | ≈0.1–0.2 | [EST] |
  | Printed PLA/PETG/nylon | ≈2–5 | ≈0.2 | ≈0.05–0.1 | [EST]. It heats, then fails. Fine for slow pivots. |

- **Proportions:** length L = 0.5–1.5 d for rotary bushings. [EST]
- **Running clearance:** about 0.1–0.2% of d for metal bushings. [EST] Printed holes need about
  0.2–0.4 mm diametral clearance on a steel pin, set by tuning. [EST]
- **Linear plain bushings and the "2:1 binding rule":** keep the moment arm of the driving force from
  the bushing axis below about 2 × the bushing length. Otherwise friction locks the slide. Two
  bushings spaced apart count as one long bushing. [DS igus/Thomson application notes, EST]
- **Use a bushing when:** motion is slow or oscillating, loads are shock-type, the joint is dirty,
  cost matters, or the space is tight.
- **Use a ball bearing when:** you need low friction or precision, speed is continuous, or the joint
  must be backdriveable.

---

## 3. Shafts

### 3.1 Stress, by hand
| Quantity | Formula |
|---|---|
| Torsion | `τ = 16 T / (π d³)` |
| Bending | `σ = 32 M / (π d³)` |
| Combined, static, von Mises (solid round) | `σ' = (32 / (π d³)) · √(M² + 0.75 T²)` |
| Static sizing | `d = [ (32 n / (π Sy)) · √(M² + 0.75 T²) ]^(1/3)` |

All in N·mm, mm and MPa.
- **Fatigue (rotating shaft, fully reversed bending):** use DE-Goodman with the endurance limit
  Se ≈ 0.5 Sut (steel, Sut < 1400 MPa), corrected by Marin factors (surface, size, reliability), so
  typically 0.25–0.4 Sut in practice. Apply stress concentration Kf at shoulders, keyseats and grooves.
  [TXT Shigley ch. 6–7]
- **First-pass Kt values** (sharp shoulders are the usual crack origin): [TXT Shigley Table 7-1,
  approximate]

  | Feature | Kt bending | Kt torsion |
  |---|---|---|
  | Sharp shoulder fillet (r/d ≈ 0.02) | ≈2.7 | ≈2.2 |
  | Well-rounded shoulder (r/d ≈ 0.1) | ≈1.7 | ≈1.5 |
  | End-milled keyseat | ≈2.1 | ≈3.0 |
  | Sled-runner keyseat | ≈1.7 | – |
  | Retaining-ring groove | ≈5 | ≈3 |

### 3.2 Stiffness usually governs in mechanisms
- **Twist:** `θ = T·L / (G·J)` with `J = π d⁴ / 32`. G is 79–80 GPa for steel and about 26 GPa for
  aluminium. [TXT]
- **Worked example [CALC]:** an 8 mm steel shaft carrying T = 2 N·m over L = 100 mm.
  1. Stress: τ = 16·2000/(π·512) = 19.9 MPa (trivial).
  2. Twist: J = 402 mm⁴, so θ = 2000·100/(79,300·402) = 0.0063 rad = 0.36°.
  3. With a 300 mm arm on the end, that is 1.9 mm at the tip.
  4. Stiffness, not strength, sizes this shaft.
- **Bending deflection:**
  - Simply supported, centre load: `δ = F L³ / (48 E I)`.
  - Cantilever: `δ = F L³ / (3 E I)`.
  - `I = π d⁴ / 64`. E is about 200 GPa for steel and 69 GPa for aluminium.
- **Typical slope limits at bearings:** [TXT Shigley Table 7-2, approximate]

  | Location | Max slope (rad) |
  |---|---|
  | Deep-groove ball bearing | 0.001–0.003 |
  | Cylindrical roller | 0.0008–0.0012 |
  | Tapered roller | about 0.0005–0.0012 |
  | Uncrowned spur gear mesh | below 0.0005 |

  Gear mesh deflection: keep it below about 0.01 × module-equivalent, roughly 0.03–0.13 mm for
  module 1–5. [EST]

### 3.3 Getting torque from shaft to hub
| Method | Torque capacity | Notes |
|---|---|---|
| D-flat plus set screw | Low to medium | NEMA 17 motor shafts are 5 mm with a 0.5 mm flat (4.5 mm across the flat). Put the set screw on the flat. |
| Set screw on a round shaft | Low; slips and marks the shaft | Use only for light loads |
| Parallel key (ISO/DIN 6885) | High | Needs machined keyways |
| Clamp hub (split hub with a screw) | Medium to high, no backlash, no shaft damage | Preferred in printed and aluminium hubs |
| Keyless bushing / taper lock | High | Bigger shafts |
| Pin (spring or dowel) through hub and shaft | Medium | Weakens the shaft (Kt about 2–3) |
| Hex or square shaft | High, printable | Common in FRC/VEX; good for printed hubs |
| Spline | High | Gearbox shafts |

**Parallel key sizes (DIN 6885 / ISO 773, width × height, mm)** [STD summary, cross-checked with common
vendor tables]

| Shaft diameter (mm) | Key (w × h) |
|---|---|
| 6–8 | 2×2 |
| 8–10 | 3×3 |
| 10–12 | 4×4 |
| 12–17 | 5×5 |
| 17–22 | 6×6 |
| 22–30 | 8×7 |
| 30–38 | 10×8 |

**Key checks:**
- Shear: `τ = 2T / (d·w·L)`.
- Bearing (crushing) on the half-height in the hub: `σ = 4T / (d·h·L)`.
- Key length is about 1–1.5 d; very long keys do not share load evenly. Key steel is softer than the
  shaft on purpose, so the key fails first. [TXT Shigley]

**Set screw axial holding force (cup point, properly torqued on a steel shaft).** [EST, from published
Unbrako-type tables in imperial sizes, converted to the nearest metric size]

| Screw | Holding force |
|---|---|
| M3 | ≈0.5–0.7 kN |
| M4 | ≈1.2–1.7 kN |
| M5 | ≈2–2.4 kN |
| M6 | ≈3.5–4.4 kN |

- Torque capacity ≈ F × d_shaft / 2. For example, M3 on a 5 mm shaft gives about 1.5 N·m, at best.
- Two screws at 90° hold more than one, but not twice as much.
- In printed hubs the plastic (or heat-set insert) limits seating torque, so expect only 20–40% of
  these values. [EST]
- Use a metal nut trap and a drop of threadlocker, and always put the screw on a flat.

### 3.4 Critical speed (whirl)
- **Simply supported uniform shaft:** `ω1 = (π/L)² · √(E I / (ρ A))` rad/s.
- **General end conditions:** `ω1 = (λ/L)² √(EI/ρA)`, with λ given below. [TXT; EngineersEdge]

  | Ends | λ |
  |---|---|
  | Fixed–free | 1.875 |
  | Pinned–pinned | π |
  | Fixed–pinned | 3.927 |
  | Fixed–fixed | 4.730 |

- **Shaft with lumped masses (Rayleigh):** `ω ≈ √( g Σ mᵢ yᵢ / Σ mᵢ yᵢ² )`. Dunkerley gives a lower
  bound. [TXT Shigley §7-6]
- **Rule:** run below about 0.7–0.8 of the first critical speed. [EST; THK applies 0.8]
- Robot joints are far below whirl speeds. Long lead screws and ball screws are where whirl matters
  (§6).

---

## 4. Gears

### 4.1 Geometry (metric, standard 20° full-depth involute)
| Quantity | Formula |
|---|---|
| Module | `m = d / z` (mm per tooth) |
| Circular pitch | `p = π m` |
| Addendum / dedendum | `ha = m`, `hf = 1.25 m` |
| Outside diameter | `da = m(z + 2)` |
| Centre distance | `a = m(z1 + z2) / 2` |
| Ratio | `i = z2 / z1` |

[STD ISO 53 / KHK reference]

- **Pressure angle:** 20° is standard. 14.5° is legacy. 25° gives stronger teeth and more bearing load.
- **Minimum teeth without undercut (20°, rack-cut):** 17 in theory; 14 in practice with slight
  undercut. Use profile shift (x > 0) for fewer teeth. [TXT; KHK]
- **Contact ratio:** at least 1.2 at minimum, typically 1.4–1.8. Low tooth counts reduce it. [TXT]
- **Printable modules [EST]:**
  - m ≥ 1 on an FDM printer with a 0.4 mm nozzle.
  - m 1.5–2 for load-bearing gears.
  - m 0.5–0.8 only on resin (SLA) printers or for molded or machined gears.

### 4.2 Gear types: when to use each one
- **Spur:** simple, cheap, no thrust. Noisy at speed. Easy to print.
- **Helical:** helix angle β 15–30°. Smoother and stronger, but makes axial thrust `Fa = Ft·tan β`.
  Normal module mn and transverse module `mt = mn / cos β`. Use herringbone (double helical) to cancel
  thrust; it is very printable.
- **Bevel:** right-angle drive. Needs accurate mounting distances.
- **Worm and wheel:** high ratio, right angle, low efficiency.
  - Ratio = wheel teeth / worm starts.
  - Efficiency: `η = (cos φn − f·tan λ) / (cos φn + f·cot λ)`, with λ = lead angle, φn = normal pressure
    angle and f = friction coefficient (about 0.03–0.1 for steel on bronze when running). [TXT
    Shigley §13]
  - Worked example [CALC]: single start with λ = 4°, f = 0.08, φn = 20° gives
    η = (0.940 − 0.006)/(0.940 + 1.144) = 45%.
  - **Self-locking** happens roughly when tan λ < f, meaning a lead angle under about 3–5°. Vibration
    can still creep it, so never rely on it as a safety brake. [TXT; EST]
- **Planetary:** high torque density, coaxial, shares the load across planets.
  - With the ring fixed, sun as input and carrier as output: `i = 1 + Zr / Zs`.
  - Mesh geometry: `Zr = Zs + 2 Zp`.
  - Equal-spacing assembly condition: `(Zs + Zr) / N_planets` must be an integer.
  - Example [CALC]: Zs = 12, Zp = 24, Zr = 60 gives i = 6, and (12 + 60)/3 = 24, so 3 planets fit.
  - Typical 3–10 per stage. Compound or "Wolfrom" printed gearboxes reach 50–200:1 in one housing.
- **Cycloidal:**
  - A lobed disc (Z_lobes) rolls inside a ring of pins (Z_pins = Z_lobes + 1), driven by an eccentric.
  - `i = Z_lobes / (Z_pins − Z_lobes)`, which is Z_lobes:1. The output turns in the reverse direction.
  - Example: 11 lobes with 12 pins gives 11:1.
  - Many teeth in contact, so it handles shock well and has low backlash. The eccentric bearing is
    heavily loaded. Use two discs 180° apart for balance. [DS Nabtesco RV; TXT]
- **Strain wave (harmonic):**
  - Elliptical wave generator, flexspline (Zf), circular spline (Zc = Zf + 2).
  - With the circular spline fixed: `i = Zf / (Zc − Zf)`, and the output turns in reverse.
  - Example: Zf = 100, Zc = 102 gives 50:1.
  - Near-zero backlash, but torsional compliance ("wind-up") and hysteresis. It "ratchets" (teeth jump)
    if overloaded. Limited torque at the small sizes. [DS Harmonic Drive LLC]
  - Printed versions work for light loads; the flexspline fatigues.

### 4.3 Backlash
- **Typical backlash:** [EST, vendor ranges]

  | Gearing | Backlash |
  |---|---|
  | Hobby or cheap spur gearmotors | 1–3° |
  | Printed planetary | 0.5–2° |
  | Precision planetary | 3–15 arcmin |
  | Cycloidal / harmonic | below 1 arcmin |

- **Design allowance:** circumferential backlash of about 0.03–0.1·m for metal gears. [EST, from
  KHK/AGMA ranges]
- **Printed gears:** open the centre distance by about 0.1–0.2 mm, or thin the teeth, so they do not
  bind from print error and swelling. [EST]
- **Backlash cures:**
  - Spring-loaded split gear (anti-backlash).
  - Adjustable centre distance.
  - Preloaded dual drive.
  - Belt or capstan instead of gears.
  - Joint-side encoder (this hides the backlash, but does not remove it).

### 4.4 Tooth strength: Lewis equation (first pass)
- **Bending stress at the root:**
  `σ = Kv · Ft / (b · m · Y)` (SI form), where:
  - Ft = tangential force = 2T/d (N)
  - b = face width (mm)
  - m = module (mm)
  - Y = Lewis form factor
  - Kv = velocity factor [TXT Shigley §14-1]
- **Y (20° full depth), selected values:** [TXT; originally Lewis, 1892]

  | Teeth | Y |
  |---|---|
  | 12 | ≈0.245 |
  | 15 | ≈0.29 |
  | 17 | ≈0.30 |
  | 20 | ≈0.32 |
  | 25 | ≈0.34 |
  | 30 | ≈0.36 |
  | 50 | ≈0.41 |
  | 100 | ≈0.45 |
  | Rack | ≈0.485 |

- **Kv (Barth), V = pitch-line speed in m/s:**
  - Cast or printed profile: `Kv = (3.05 + V)/3.05`.
  - Cut or milled profile: `Kv = (6.1 + V)/6.1`.
  - At robot speeds, Kv is about 1.
- **Face width:** b is typically 8–16 m, and about 10 m is common.
- **Allowable bending stress for plastics [EST, not verified, depends strongly on print settings and
  temperature]:**

  | Material | Allowable (MPa) |
  |---|---|
  | Printed PLA/PETG | ≈10–20 |
  | Printed nylon / PA-CF | ≈20–35 |
  | Molded POM | ≈30–40 |
  | Steel | 200+ (use AGMA in that case) |

- **Worked example [CALC]:** printed m = 1, z = 20 pinion, b = 10 mm, allowable 15 MPa, Y = 0.32.
  1. Ft = 15·10·1·0.32 = 48 N.
  2. Pinion pitch radius is 10 mm, so T = 0.48 N·m.
  3. With a safety factor of 2, that is about 0.24 N·m.
  4. Lesson: printed m1 gears are weak. Go to m1.5–2 with wider faces, or use metal, or use belts.
- **What Lewis does not cover:** contact (pitting) stress, which is covered by Hertz/AGMA. Lewis is
  enough for low-cycle printed mechanisms. For steel at speed, use AGMA 2001 or ISO 6336.

---

## 5. Timing belts

### 5.1 Profiles
| Profile | Pitch | Typical widths | Notes |
|---|---|---|---|
| **GT2 (2MGT, PowerGrip GT2/GT3)** | 2 mm | 6, 9, 10 mm (3D-printer standard 6 mm) | Curved tooth for low backlash. Fibreglass cord; steel-core and Kevlar versions exist. Gates calls the current generation GT3, which is compatible. |
| GT2 3 mm / 5 mm (3MGT / 5MGT) | 3 / 5 mm | 6–25 mm | For higher torque |
| **HTD 3M / 5M / 8M** | 3 / 5 / 8 mm | 9–30 mm+ | Round tooth for high torque, but more backlash than GT2 |
| T2.5 / T5 (trapezoidal) | 2.5 / 5 mm | – | Legacy; more backlash. Do not mix with GT2. |
| MXL / XL (imperial trapezoidal) | 2.032 / 5.08 mm | – | Legacy |

Never mix GT2 belts with HTD or T pulleys. They look similar but the tooth forms differ.

### 5.2 Geometry
- **Pitch diameter:** `PD = p·z / π`.
  - GT2 16T: 10.19 mm. 20T: 12.73 mm. 36T: 22.92 mm. 60T: 38.20 mm. [CALC]
- **Belt length, open drive:**
  `L ≈ 2C + π(D + d)/2 + (D − d)²/(4C)`, with C = centre distance and D, d = pitch diameters. [TXT]
- **Centre distance from a chosen belt length:**
  `C = [b + √(b² − 8(D − d)²)] / 8`, where `b = 2L − π(D + d)`.
- **Closed belts come in whole tooth counts:** `N_belt = L / p`. Pick a stock length, recompute C, and
  give the design a tensioner or slotted mount with about ±2–3 mm of travel.
- **Wrap angle on the small pulley:** `θ = 180° − 2·asin((D − d)/(2C))`.
- **Teeth in mesh (TIM):** `TIM = z_small · θ / 360`. Keep TIM ≥ 6. Below that, the belt's torque
  rating drops and teeth can jump. [DS Gates design manual guidance; EST]
- **Worked example [CALC]:** GT2 20T to 60T (a 3:1 ratio), target C = 100 mm.
  1. L = 200 + π·50.93/2 + 25.47²/400 = 281.6 mm, which is 140.8 teeth.
  2. Choose a 280 mm (140T) closed belt.
  3. b = 560 − 160.0 = 400.0, so C = (400 + √(160000 − 5188))/8 = 99.18 mm.
  4. θ = 165.3°, so TIM = 9.2. OK.

### 5.3 Pulley size
- **Minimum GT2 2 mm pulley:** catalogues start at 12T. Use 16T at least for load, and 20T is the
  common default. [DS McMaster/Gates offerings; EST]
- Small pulleys bend the cords hard, which shortens belt life, cuts TIM and raises "polygon" ripple.
  This matters most with fibreglass cords, which crack when bent sharply.
- **HTD 5M:** about 14T minimum at light load, and more is better. [EST, not verified]
- **Idlers:** a smooth idler on the back of the belt should be at least as big as the minimum pulley,
  and preferably bigger (GT2: at least an 18 mm OD smooth idler). [EST]

### 5.4 Tension, stiffness, load
- **Static (install) tension for 6 mm GT2 in printers:** about 10–40 N. Vendor guidance varies, and
  there is no Gates-published figure in hand. [EST]
- **Measuring tension:** pluck the span and measure its frequency, then
  `T = 4·μ·L²·f²`, with μ = mass per length (kg/m, about 0.008 kg/m for 6 mm GT2 [EST]), L = free span
  (m) and f = frequency (Hz). Phone apps work for this.
- **Tension rule:** pretension must exceed the peak working tension difference, so the slack side
  never goes slack. A typical choice is pretension ≥ 0.5–1 × effective pull (Te = T/r). [TXT belt
  theory; EST]
- **Stiffness:** a belt span acts like a spring, `k = EA / L_span`.
  - For 6 mm fibreglass GT2, EA ≈ 10–25 kN. [EST, not verified; measure it or ask the vendor]
  - Steel-core belts are stiffer.
  - Long spans are soft. This compliance often sets the robot arm's end-effector stiffness and
    resonance, so check it.
- **Working load [EST]:**
  - 6 mm GT2 fibreglass breaks at roughly 0.6–1 kN.
  - Design working pull is about 50–100 N with 9+ teeth in mesh.
  - Use 9–10 mm width or 3M/5M profiles for more.
  - Tooth shear (jumping) usually fails before the cords break.
- **Torque on a joint:** `T_joint = F_eff · r_big`. A 2-stage belt reduction (for example 20→60 then
  20→60, giving 9:1) is the classic way to put a NEMA 17 at the base and drive a joint with enough
  torque.

### 5.5 Belt mistakes
- Twisting the belt, or running it with misaligned pulleys. Use flanged pulleys or flanged idlers, and
  keep alignment within about 0.5°.
- Putting the tensioner on the tight side.
- Clamping an open belt with a small screw bite. Use tooth-matched clamps.
- Forgetting that the belt length must be a whole number of teeth.
- Using 16T pulleys plus a long span plus fibreglass where stiffness matters.

---

## 6. Rotary-to-linear: lead screws and ball screws

### 6.1 Torque and efficiency
| Quantity | Formula |
|---|---|
| Lead | `l = starts × pitch` (Tr8×8 means 8 mm lead, 2 mm pitch, 4 starts) |
| Lead angle | `λ = atan( l / (π d_m) )`, d_m = mean diameter |
| Effective friction angle (trapezoidal, 30° thread) | `φ' = atan( μ / cos 15° )` |
| Driving efficiency | `η = tan λ / tan(λ + φ')` |
| Backdriving efficiency | `η_b = tan(λ − φ') / tan λ` (zero or negative means self-locking) |
| Drive torque | `T = F·l / (2π η)` |
| Torque produced when backdriven | `T = F·l·η_b / (2π)` |

[TXT Shigley §8-2]

**Friction coefficient μ:** [EST]
- Steel on bronze, lubricated: 0.08–0.15.
- Steel on POM or polymer nut: 0.1–0.2.
- Steel on printed nut: 0.2–0.3.

**Worked examples [CALC], μ = 0.15, d_m ≈ 7 mm:**
| Screw | Lead angle λ | Efficiency η | Self-locking? |
|---|---|---|---|
| Tr8×2 (1 start) | 5.2° | 36% | Yes (λ < φ' = 8.8°) |
| Tr8×8 (4 start) | 20° | 66% | No. It backdrives: η_b = tan 11.2°/tan 20° = 54% |

- Lifting 50 N with Tr8×8 needs T = 50·0.008/(2π·0.66) = 0.097 N·m.
- **Ball screws:** η ≈ 90%+ in both directions, so they always backdrive. A vertical axis needs a
  brake, a counterbalance, or a powered hold. [DS THK/HIWIN]
- **Rule of thumb:** driving efficiency below about 50% roughly means self-locking. Vibration can still
  make it creep. [TXT]

### 6.2 Selection
| | Trapezoidal lead screw | Ball screw |
|---|---|---|
| Efficiency | 25–70% | 85–95% |
| Backlash | 0.05–0.3 mm; anti-backlash nuts available | 0–0.02 mm when preloaded |
| Holds position unpowered | Yes, if the lead is small | No |
| Cost / size | Low / compact | Higher / bigger nut |
| Duty | Intermittent; heat and wear limit it (PV) | Continuous; L10 life rated |
| Use for | Z axes of printers, light lifts, hand adjusters | CNC, fast precise linear axes |

### 6.3 Critical speed and buckling
- **Whirl:** `n_c = f · d_r / L² × 10⁷` rpm, with d_r = root diameter (mm) and L = unsupported length
  (mm). The f values below include THK's 0.8 safety factor. [DS THK selection guide, cross-checked by
  [CALC] from beam theory: plain steel gives 12.1 for pinned-pinned, and 0.8 × 12.1 = 9.7]

  | Support | f |
  |---|---|
  | Fixed–fixed | 21.9 |
  | Fixed–supported | 15.1 |
  | Supported–supported | 9.7 |
  | Fixed–free | 3.4 |

- **Example [CALC]:** Tr8, d_r ≈ 6 mm, L = 400 mm.
  - Fixed–supported: 15.1·6/160000·1e7 ≈ 5,700 rpm.
  - Fixed–free (motor coupling only): about 1,300 rpm.
- **DN limit for ball screws:** d (mm) × n (rpm) ≤ about 50,000–70,000 for rolled screws and about
  100,000+ for precision ground screws. Use the lower of the DN limit and n_c. [DS THK; EST]
- **Buckling under compression:** `P_cr = c·π²EI/L²`, with c = 0.25 (fixed–free), 1 (pinned–pinned),
  2 (fixed–pinned) or 4 (fixed–fixed). Use I from the root diameter, and apply a safety factor of
  about 0.5. [TXT; DS THK]
- **Mounting:**
  - The fixed end has an angular-contact pair or a "BK" support block.
  - The supported end has a single DGBB ("BF" block) that floats.
  - Couple the screw to the motor with a flexible coupling, and do not also constrain it with a second
    rigid nut (over-constraint causes "Z wobble"). [DS HIWIN/THK]

---

## 7. Fasteners

### 7.1 Strength classes (ISO 898-1 steel; ISO 3506 stainless) [STD summary; values approximate]
| Class | Rm, tensile (MPa) | Rp0.2, yield (MPa) | Sp, proof (MPa) | Notes |
|---|---|---|---|---|
| 4.6 | 400 | 240 | 225 | Mild steel |
| 8.8 | 800 | 640 | 580 (≤ M16) | General machine bolts |
| 10.9 | 1040 | 940 | 830 | |
| 12.9 | 1220 | 1100 | 970 | Black socket head cap screws are commonly 12.9 |
| A2-70 / A4-70 stainless | 700 | 450 | – | Galls; use anti-seize |

How to read the class name: "8.8" means Rm = 8 × 100 MPa, and yield = 0.8 × Rm.

**Tensile stress areas At (coarse thread, mm²):** [STD ISO 898-1]
| Size | At |
|---|---|
| M2 | 2.07 |
| M2.5 | 3.39 |
| M3 | 5.03 |
| M4 | 8.78 |
| M5 | 14.2 |
| M6 | 20.1 |
| M8 | 36.6 |
| M10 | 58.0 |

### 7.2 Preload and torque
- **Target preload:** `Fi = 0.75 · At · Sp` for reusable joints, and 0.9 for permanent ones. [TXT
  Shigley §8-8; Fastenal tech note]
- **Torque:** `T = K · Fi · d`, with d = nominal diameter in metres. [TXT; Fastenal]

  | Thread condition | Nut factor K |
  |---|---|
  | Dry steel, as received | ≈0.2 |
  | Lubricated | ≈0.15 |
  | Anti-seize | ≈0.1–0.12 |
  | Zinc, dry | ≈0.2–0.3 |

- Torque control is only accurate to about ±25–30% in preload. [TXT]
- **Computed torques, class 8.8, K = 0.2, 75% of proof load [CALC]:**

  | Size | Preload Fi | Torque |
  |---|---|---|
  | M3 | 2.19 kN | 1.3 N·m |
  | M4 | 3.82 kN | 3.1 N·m |
  | M5 | 6.18 kN | 6.2 N·m |
  | M6 | 8.74 kN | 10.5 N·m |
  | M8 | 15.9 kN | 25.5 N·m |

  - For 12.9, multiply by about 1.67. For example, M3 12.9 is about 3.7 kN at 2.2 N·m.
  - These agree with published charts within a few percent (AIMS lists M4 at 3.2 N·m and M5 at
    6.4 N·m for 8.8, dry).
- **Into plastic or heat-set inserts, these torques strip the threads.** [EST, depends on insert and
  print]

  | Fastener | Torque limit |
  |---|---|
  | M3 heat-set insert in PLA/PETG | ≈0.5–1 N·m (pull-out roughly 0.3–0.8 kN) |
  | M3 self-tapping into plastic | ≈0.3–0.6 N·m |
  | M3 through-bolt with a nut and washers on printed parts | limited by plastic crushing and creep, not by the bolt |

### 7.3 Joint behaviour
- **Joint stiffness constant:** `C = kb / (kb + km)`, with kb = bolt stiffness and km = clamped member
  stiffness.
  - The bolt sees an extra `C·P` of an external tensile load P. The members lose `(1 − C)·P` of their
    clamp force.
  - The joint separates when `P > Fi / (1 − C)`.
  - For steel joints, C ≈ 0.2–0.3, so the bolt sees little of the external load and fatigue is low.
    [TXT Shigley §8-7]
- **Plastic clamped parts have a small km,** so C rises, preload is lost to creep, and joints loosen
  over weeks. Fixes:
  - Put metal sleeves or spacers through the plastic so the bolt clamps metal to metal.
  - Use wide washers.
  - Use Belleville or wave washers to hold preload through creep.
  - Use a longer grip length.
- **Shear joints:** in friction-grip design, slip resistance ≈ μ·Fi per interface (μ about 0.1–0.2
  for steel on steel, lower on printed surfaces). For precision location, do not rely on bolts in
  clearance holes. Use dowel pins (one round, one diamond, or a slot) to locate, and bolts to clamp.
  [TXT Slocum]
- **Thread engagement:** steel nut or steel tapped hole ≥ 1 d; aluminium ≥ 1.5–2 d; plastic: use
  inserts. [EST, common practice]

### 7.4 Loosening and locking
- Transverse slip under vibration is the main cause of self-loosening. This was shown by the Junker
  vibration test (DIN 65151).
- **The best cure is enough preload** plus a long, elastic bolt.
- **Locking options** [TXT; vendor Junker data]:

  | Option | Effectiveness |
  |---|---|
  | Anaerobic threadlocker: Loctite 222 (low, purple, small screws), 243 (medium, blue, oil-tolerant), 263/271 (high, red, needs heat to remove) | Effective |
  | Wedge-lock washers (Nord-Lock) | Effective |
  | Prevailing-torque nylon insert nuts (DIN 985) | Medium; limited reuse; about 120 °C max |
  | All-metal prevailing-torque nuts | Medium |
  | Split (helical) lock washers | Largely ineffective in Junker tests; do not specify them |

- Most threadlockers attack some plastics (stress-cracking PC and ABS). Use a plastic-safe type
  (for example Loctite 425 or a nylon patch) or avoid threadlocker on printed parts. [DS Henkel; EST]

### 7.5 Holes [STD ISO 273 clearance (fine / medium); common tap drills]
| Size | Clearance hole fine / medium | Tap drill | Heat-set insert hole (typical) |
|---|---|---|---|
| M2 | 2.2 / 2.4 | 1.6 | ≈3.2 |
| M2.5 | 2.7 / 2.9 | 2.05 | ≈3.6 |
| M3 | 3.2 / 3.4 | 2.5 | ≈4.0–4.2 |
| M4 | 4.3 / 4.5 | 3.3 | ≈5.6 |
| M5 | 5.3 / 5.5 | 4.2 | ≈6.4 |
| M6 | 6.4 / 6.6 | 5.0 | ≈8 |
| M8 | 8.4 / 9.0 | 6.8 | – |

- Insert holes vary by brand. Use the datasheet of the insert you will buy. [EST]
- Printed holes come out undersize. Add +0.2–0.3 mm, or drill or ream them after printing.

---

## 8. Springs

### 8.1 Helical compression and extension
| Quantity | Formula |
|---|---|
| Rate | `k = G d⁴ / (8 D³ Na)` |
| Shear stress | `τ = K_W · 8 F D / (π d³)` |
| Spring index | `C = D/d` (keep it 4–12) |
| Wahl factor | `K_W = (4C − 1)/(4C − 4) + 0.615/C` |

d = wire diameter, D = mean coil diameter, Na = active coils. [TXT Shigley ch. 10]

- **Music wire:** G ≈ 79–82 GPa. Tensile strength `Sut ≈ A / d^m`, with A ≈ 2211 MPa·mm^m and
  m ≈ 0.145. [TXT Shigley Table 10-4]
- **Static allowable shear:** about 45% of Sut for music wire without set removal. [TXT]
- **Worked example [CALC]:** music wire, d = 1 mm, D = 8 mm, Na = 10.
  1. k = 79,300/(8·512·10) = 1.94 N/mm.
  2. C = 8, so K_W = 1.18.
  3. At F = 20 N: τ = 482 MPa.
  4. Allowable is 0.45 × 2211 = 995 MPa. OK.
- **Solid length:** about (Nt)·d. Keep working deflection at 75–85% of the deflection to solid or less.
  [EST]
- **Buckling:** a spring with both ends on parallel flat plates is roughly stable if L0 < 5.26 D (the
  limit for steel). For long springs, guide them on a rod or in a bore. [TXT Shigley]
- **Extension springs** have initial tension, and the hooks fail first because stress is high at the
  bends.
- **Ends:** squared and ground ends give square seating. Total coils = active coils + 2.

### 8.2 Other spring types
- **Torsion springs:** the rate in N·mm per radian is about `E d⁴ / (64 D Na)`. Load them in the
  direction that winds the coil tighter. [TXT]
- **Belleville (disc) springs:** high force in a short height, and a nonlinear curve. Use them for bolt
  preload retention and bearing preload. [DS DIN EN 16983]
- **Wave springs:** about half the height of a coil spring for the same force. Use them for bearing
  preload. [DS Smalley]
- **Constant-force springs (flat coiled strip):** nearly constant force over long travel. Use them for
  counterbalancing a Z axis or for cable retraction.
- **Gas springs:** used for gravity compensation of big arms.
- **Gravity compensation:** a "zero-free-length" spring between a point on the link and a point above
  the pivot gives exact static balance at all angles. Approximate it with a spring plus a cable over a
  pulley. [TXT: Herder; robotics literature]
- **Printed flexures:** PETG and nylon creep less than PLA. Keep strain below about 2–3% for fatigue,
  and expect creep under constant load. [EST]

---

## 9. Couplings
| Type | Backlash | Torsional stiffness | Misalignment it tolerates (typical [EST]) | Use |
|---|---|---|---|---|
| Rigid (sleeve or clamp) | 0 | Highest | ≈0; it forces the shafts into line | Only if the shafts are already co-axial by design |
| Beam / helical (one-piece aluminium) | 0 | Low to medium | Parallel 0.1–0.25 mm, angular 3–5° | Encoders, light steppers |
| Bellows | 0 | High | Parallel 0.1–0.3 mm, angular 1–2° | Servo axes, ball screws |
| Jaw / spider (Lovejoy) | ≈0 when preloaded; the spider is compliant | Medium | Parallel 0.1–0.2 mm, angular ≈1° | General; damps shock |
| Oldham | Small | Medium | Parallel up to ≈1–2 mm (scales with size) | Printer Z lead screws; parallel offset |
| Disc pack | 0 | High | Angular ≈1°/disc, small axial | Industrial servo |
| Universal joint | Small | High | Large angle (≈20–30°) | Big angles; the speed fluctuates unless two are used in phase |

- A single flexible coupling cannot take parallel offset well. Parallel offset needs two flex planes
  (double beam, or Oldham).
- Do not double-constrain a lead screw (rigid coupling plus a fixed nut plus a fixed far bearing).
  [TXT Slocum]

---

## 10. Linear guides

### 10.1 Round rod plus linear ball bushings (LMxUU)
- **Cheap, but the shaft deflection is usually the weak point.**
- **Worked example [CALC]:** an 8 mm rod, 400 mm span, simply supported, 20 N at the centre.
  - I = 201 mm⁴, so δ = 20·400³/(48·200,000·201) = 0.66 mm.
  - With a 12 mm rod: I = 1018 mm⁴, so δ = 0.13 mm.
  - Stiffness scales as d⁴, so going up one rod size helps a lot.
- **LM8UU ratings:** C ≈ 260 N, C0 ≈ 400 N per bearing [DS]. Life (ball type):
  `L = (fH·fT·fC·C / (fW·P))³ × 50 km`, with hardness, temperature, contact and load factors. Many
  vendors use 50 km as the reference distance.
- **Rods should be hardened and ground** (about HRC 60, h6/g6). Soft rods get grooved by the balls.
- **Use two bushings per rod, spaced apart, and two rods,** or the carriage tilts. LMxLUU is the long
  (double-length) version.
- Printed or press-fit housings for LMxUU: clamp them, do not squeeze them, because a distorted
  housing binds the balls.

### 10.2 Profile rails (miniature MGN, HIWIN-type)
- **Approximate HIWIN MGN12 ratings:** [DS HIWIN catalogue values as commonly quoted; check the
  current catalogue]

  | Block | C | C0 |
  |---|---|---|
  | MGN12C | ≈2.8–2.9 kN | ≈3.9–4.0 kN |
  | MGN12H | ≈3.7 kN | ≈5.9 kN |

  Moment ratings are on the order of 10–30 N·m.
- **Life:** `L = (C/P)³ × 50 km` for ball type. [DS HIWIN]
- **Mounting:** the rail needs a straight, flat reference edge or datum and screws at the full pitch
  (MGN12: M3 at 25 mm).
  - Rails bolted to printed parts lose most of their precision. Bolt them to aluminium.
  - Two parallel rails must be parallel within tens of µm, or one rail floats (vendors give allowable
    parallelism by preload class).
- **Cheap clone rails:** often need cleaning and greasing, and they vary in preload. Inspect them
  before use.

### 10.3 V-wheels on extrusion
- Easy and cheap, with adjustable preload through an eccentric spacer.
- Lower stiffness. The wheels flat-spot if left preloaded under load for long periods. [EST]

---

## 11. Brakes and clutches

### 11.1 Torque formulas (disc type, N friction surfaces, axial clamp F) [TXT Shigley ch. 16]
| Assumption | Formula |
|---|---|
| Uniform wear (worn-in, conservative) | `T = N · μ · F · (ro + ri)/2` |
| Uniform pressure (new) | `T = N · μ · F · (2/3)(ro³ − ri³)/(ro² − ri²)` |
| Band or capstan brake | `T_tight / T_slack = e^(μθ)` |

**Friction coefficients μ:** [EST]
- Dry steel on steel: about 0.15–0.3.
- Organic lining on steel: about 0.3–0.4.
- PU or rubber on printed plastic: about 0.4–0.8, but this varies a lot.

### 11.2 Practical types
- **Spring-applied, power-off electromagnetic brake:**
  - The spring clamps the brake when power is removed, and a coil releases it.
  - Mandatory for vertical axes and gravity-loaded arm joints on ball screws, belts or backdriveable
    gearboxes, if the payload must not fall when power is lost.
  - Small units for NEMA 17/23 motors are about 0.3–2 N·m. [DS vendor ranges; EST]
- **Put the brake on the motor (high-speed) side,** so the required brake torque is divided by the
  ratio. The transmission must then hold the full joint torque.
- **Worked example [CALC]:** 1 kg at 0.3 m gives 2.94 N·m at the shoulder. With a 10:1 belt, the brake
  must hold 0.29 N·m, or about 0.6 N·m with a safety factor of 2.
- **Stepper detent torque is not a brake.** It is only about 1–5% of holding torque, and an unpowered
  stepper backdrives.
- **Slip clutch / torque limiter** (friction disc and spring, or ball detent): protects printed gears
  and lets the user push the arm by hand. Set it to about 1.2–1.5 × the maximum working torque and
  below the gear's failure torque. [EST]
- **One-way (sprag or roller) clutches:** HF0612 and similar drawn-cup types need a hardened shaft.
  Use them for ratchets and anti-backdrive.
- **Wrap-spring clutches and brakes:** self-energising, which gives high torque in a small size.

---

## 12. Capstan (cable) drives
- **How it works:**
  1. A cable (steel wire rope or Dyneema/UHMWPE) wraps several turns around a small motor-side drum,
     with its ends anchored to a large output drum or sector.
  2. Friction transmits torque, so there are no teeth and no backlash. The drive is highly
     backdriveable, which is good for haptics and force control.
- **Ratio:** `i = D_big / D_small`, using diameters to the cable centre. Typical 5–20:1 per stage.
- **Capstan equation:** `T_load / T_hold = e^(μθ)`.
  - Worked example [CALC]: μ = 0.15 and 3 wraps (θ = 6π) give e^2.83 ≈ 17. The anchor side needs only
    1/17 of the load tension, so 3–5 wraps on the small drum is typical. [TXT; EST for μ]
- **Drum to cable diameter:** steel wire rope needs drum/cable diameter of at least about 20–40 to keep
  bending fatigue acceptable. 7×19 rope is more flexible than 1×19. Dyneema tolerates smaller drums
  but creeps under tension, so retension it. [EST; wire-rope vendor guidance]
- **Groove the small drum helically** with a pitch of about the cable diameter plus 10%, so wraps do not
  ride over each other.
- **Pretension the cable** above the peak working tension with a screw tensioner at one anchor.
- **Limits:**
  - Output travel is limited to less than 360° (the cable unwraps), unless you use continuous loops.
  - Cable stretch sets stiffness: `k = E A / L`.
  - The cable walks along the small drum, so allow axial length for the wraps.
- References: the MIT/Stanford haptics literature, and Aaed Musa's open-source capstan drives. [EST;
  see §References]

---

## 13. Linkages

### 13.1 Mobility (Gruebler / Kutzbach, planar)
- `M = 3(n − 1) − 2 j1 − j2`, where n = number of links including ground, j1 = full joints (pin or
  slider), and j2 = half joints (cam or rolling-with-slip).
- A four-bar has n = 4 and j1 = 4, so M = 1. [TXT Norton ch. 2]

### 13.2 Grashof condition (four-bar)
- Let s = shortest link, l = longest, and p, q the other two.
- **Grashof (at least one link rotates fully):** `s + l ≤ p + q`.
  - Shortest link adjacent to ground: crank-rocker.
  - Shortest link is the ground: double-crank (drag link).
  - Shortest link is the coupler: double-rocker.
  - `s + l = p + q`: change-point mechanism. It can flip branches, so avoid it unless you guide it.
- **Non-Grashof (s + l > p + q):** every motion is a triple-rocker, and no link fully rotates. [TXT
  Norton]
- **Example [CALC]:** ground 100, crank 40, coupler 120, rocker 90.
  - s + l = 160 ≤ p + q = 190, so it is Grashof.
  - The shortest link is next to ground, so it is a crank-rocker.

### 13.3 Transmission angle and dead points
- **Transmission angle μ:** the angle between the coupler and the output rocker. Keep it between 40°
  and 140° over the whole motion; near 90° is ideal. Below about 30°, force transmission collapses and
  the linkage binds. [TXT Norton]
- **Toggle (dead) points:** the input and coupler are collinear. Here mechanical advantage tends to
  infinity at the output. That is useful for clamps and grippers. It also makes the mechanism
  uncontrollable if the dead point is approached as an input-side singularity.

### 13.4 Linkages in arms
- **Parallelogram (pantograph-type) linkage:**
  - Keeps the end link at a fixed orientation and lets the forearm motor sit at the base.
  - Used in palletizing robots, uArm and the Dobot-style desktop arms.
  - Trades a smaller workspace for less distal mass. This follows the Mechy standard of keeping mass
    off distal links.
- **Slider-crank:**
  - Stroke = 2 × crank radius.
  - Common in grippers driven by a lead screw or linear actuator.
- **Analyse linkages numerically:** solve loop closure (vector loop) at many input angles, then check
  Grashof, transmission angle range, link interference, and the torque profile. Verify against the
  closed-form four-bar position solution (Freudenstein equation) at a few poses.

---

## 14. Worked design flow: one robot arm joint (belt-driven shoulder)
1. **Load:** payload plus links gives the gravity torque at the worst pose.
   Example: 0.5 kg at 0.35 m plus 0.4 kg of links at 0.18 m gives 1.72 + 0.71 = 2.43 N·m. Add
   acceleration torque (J·α), then apply a 1.5–2 × safety factor, giving about 4–5 N·m. [CALC]
2. **Motor:** a NEMA 17 at about 0.4 N·m holding gives about 0.2 N·m usable at speed (≈50% derate
   [EST]). The required ratio is 4.5/0.2 ≈ 22.
   - Two belt stages (20→60, then 20→60) give 9:1, which is not enough.
   - Use 16→60 then 20→72 (3.75 × 3.6 = 13.5:1), plus a planetary, or a bigger motor, or a cycloidal.
   - Iterate with the torque budget rule (Mechy standard 4).
3. **Belt check:**
   - Final-stage pull = T_joint / r_big. For example, 4.5 N·m on a 72T (r = 22.9 mm) is 196 N.
   - That is too high for 6 mm GT2, so use 9–10 mm GT2 or HTD 5M 15 mm. Check that TIM ≥ 6. [CALC; EST
     limits]
4. **Bearings:**
   - Joint moment from the arm is about 2.4 N·m. With two 6805 bearings 25 mm apart: 97 N each.
   - s0 = 2600/97 ≈ 27. OK. Hollow bore for cables.
   - Fixed-floating, with a wave spring for preload.
5. **Shaft or hub:** check twist and the hub key or clamp torque. Use a clamp hub or hex bore on the
   big pulley, not a set screw.
6. **Fasteners:** use metal-to-metal clamp paths and heat-set inserts within their torque limits.
7. **Brake:** will the arm fall when power is lost? For a belt plus planetary, yes, so it needs a motor
   brake or a gravity spring.
8. **Stiffness:** check the belt span spring rate, then the tip deflection from belt stretch
   (δ_tip = (F_belt/k_belt) · L_arm / r_pulley). Iterate.
9. **Verification table** (Mechy standard 5): hand-calculate every number above, then compare it with
   the sim or FEA.

---

## 15. Common mistakes checklist (review every design against this)
- [ ] Every rotating joint has two bearings spaced apart (or one moment bearing). None rely on a single
      DGBB to carry moment loads.
- [ ] A fixed-floating arrangement, or an explicit preload spring, is present. There is no
      over-constrained rigid stack-up in plastic.
- [ ] Bearing seats in printed parts have shoulders and retaining caps, not just a press fit.
- [ ] No threaded rod is used as a precision shaft. Needle bearings run only on hardened shafts.
- [ ] Hubs transmit torque by clamp, key, hex or D-flat with the set screw on the flat, and the
      capacity has been calculated.
- [ ] Gear module is printable (≥ 1 FDM; ≥ 1.5 if loaded), and Lewis stress has been checked with a
      plastic allowable value labelled as an estimate.
- [ ] Planetary tooth counts satisfy Zr = Zs + 2Zp and the equal-spacing assembly condition.
- [ ] Each belt is a stock whole-tooth length, has TIM ≥ 6, has a tensioner with travel, uses a
      small pulley of at least 16T (GT2), and its effective pull is within its width's rating.
- [ ] Every vertical or gravity-loaded axis that can backdrive (ball screw, belt, efficient gearing)
      has a brake, counterbalance or self-locking stage, and the power-loss case is stated.
- [ ] Lead and ball screws are checked against critical speed (THK f values) and buckling. The screw
      is not double-constrained.
- [ ] Fastener torque is matched to what it threads into (metal or insert). No split lock washers.
      Threadlocker is compatible with the plastics.
- [ ] Linkages are checked for Grashof type, transmission angle 40–140°, and branch or toggle issues
      over the full range.
- [ ] Stiffness (shaft twist, rod deflection, belt stretch) is computed and turned into tip
      deflection, not only strength.
- [ ] Every number is tagged: datasheet, calc, or estimate.

---

## Canonical references
**Free:**
- MIT OCW 2.007 Design and Manufacturing I, and 2.72 Elements of Mechanical Design (lecture notes,
  free): https://ocw.mit.edu/courses/2-007-design-and-manufacturing-i-spring-2009/ and
  https://ocw.mit.edu/courses/2-72-elements-of-mechanical-design-spring-2009/
- Alex Slocum, *FUNdaMENTALs of Design* (free PDF chapters, MIT; covers bearings, couplings, exact
  constraint and bolted joints): https://meddevdesign.mit.edu/ (also on MIT OCW 2.007 resources)
- SKF bearing catalogue and online Bearing Select tool, covering L10, fits, preload and arrangements
  (free): https://www.skf.com/group/products/rolling-bearings
- Schaeffler/INA technical pocket guide (free PDF): https://www.schaeffler.com/
- THK ball screw selection guide, covering permissible rotational speed, buckling and mounting
  (free): https://www.thk.com/eu/en/products/ball_screw/selection/0007/
- HIWIN linear guideway and ball screw technical catalogues (free PDFs): https://www.hiwin.com/
- KHK Gear Technical Reference, covering geometry, profile shift, backlash and strength (free):
  https://khkgears.net/new/gear_knowledge/
- Gates PowerGrip / GT belt design manuals and the Design Flex Pro online tool (free with
  registration): https://www.gates.com/
- igus iglidur and drylin expert systems, life calculators for polymer bushings and slides (free):
  https://www.igus.com/
- Fastenal technical reference, "Torque-Tension Relationship for Metric Fasteners" (free PDF):
  https://crafter.fastenal.com/static-assets/pdfs/technical-resources/Torque-Tension-Relationship-for-Metric-Fasteners-Property-Class-4.6-8.8-10.9-12.9.pdf
- Harmonic Drive LLC engineering data (free): https://www.harmonicdrive.net/
- Nabtesco RV (cycloidal) reducer technical data (free): https://www.nabtescomotioncontrol.com/
- EngineersEdge, for shaft critical speed and assorted formulas (free, but verify):
  https://www.engineersedge.com/
- Aaed Musa's open-source capstan drive and cycloidal projects, for practical printed
  implementations (free, GitHub/YouTube).

**Paid books and standards:**
- Budynas and Nisbett, *Shigley's Mechanical Engineering Design* (paid). Covers shafts, bearings,
  gears (Lewis/AGMA), springs, bolted joints, clutches and brakes.
- Norton, *Machine Design* and *Design of Machinery* (paid). Covers linkages, Grashof and
  transmission angle.
- Juvinall and Marshek, *Fundamentals of Machine Component Design* (paid).
- *Machinery's Handbook* (paid). Covers threads, keys, fits and springs.
- ISO 281 (bearing dynamic life), ISO 76 (static rating), ISO 898-1 (bolt property classes), ISO 273
  (clearance holes), DIN 6885 (keys), ISO 6336 / AGMA 2001 (gear rating). All paid standards.

## Gaps / not verified
- Ratings for the 6800-series, 6000/6200, 623/624/626, the 51100/51105 thrust bearings, and the
  LM10UU/LM12UU are approximate catalogue-range estimates. Only the 608 (two sources, SKF and Timken),
  625 (SKF), 61805 and LM8UU (several distributor listings) were cross-checked. Use the exact datasheet
  of the bought part.
- MGN12 C and C0 values are as commonly quoted from HIWIN. They were not re-read from the current
  catalogue in this session.
- GT2 belt numbers are not from a Gates-published table:
  - minimum pulley 12T (only catalogue availability was confirmed)
  - working pull of about 50–100 N for 6 mm
  - install tension of 10–40 N
  - EA of 10–25 kN
  - mass of about 8 g/m

  Measure these, or get the Gates GT2 design manual.
- HTD 5M minimum pulley size was not verified.
- The THK critical speed f values were reconstructed from memory and cross-checked by beam-theory
  calculation (they agree to within 1–2%). THK's equation image was not read directly.
- Allowable stress for printed gears (PLA/PETG/nylon) varies strongly with print settings, and the
  values given are rough estimates. Test-print and load-test before relying on them.
- Set screw holding forces were converted from imperial-size tables to metric. The printed-hub
  derating is an estimate.
- Heat-set insert torque and pull-out values vary by insert brand and plastic. They are estimates.
- Coupling misalignment tolerances are generic. Each vendor's datasheet governs.
- Plain-bushing PV limits are typical catalogue values. igus grades differ widely, so use the igus
  calculator.
