# Mechanics of Materials and Materials Selection — Agent Reference

Purpose: the strength-of-materials and materials-selection knowledge a design agent needs to size a link,
shaft, bracket, pin, column or printed part, pick a material, and pick a safety factor. Formulas are
in SI. Numbers marked *typical* are handbook/datasheet values for screening; marked *estimate* are
rules of thumb or values with wide scatter. Always re-check a final design against the actual supplier
datasheet for the exact grade/temper/print settings.

Unit convention used throughout (consistent set, no conversion needed):
**N, mm, MPa (= N/mm²), N·mm**. E in MPa (200 GPa = 200 000 MPa). Density in kg/m³ unless noted.
Mixing m and mm is the #1 arithmetic error; stay in N–mm–MPa.

---

## 0. Quick decision checklist (read first)

1. **What fails first?** For most small mechanisms (robot arms, gantries, printed brackets) the governing
   criterion is **stiffness (deflection)**, not strength. Check deflection first, then stress.
2. Identify load type: static / cyclic (fatigue) / long-duration (creep) / impact. Rotating shafts and
   reciprocating arms are *always* fatigue problems.
3. Compute nominal stress (axial, bending, torsion, shear), multiply by stress concentration Kt (or
   Kf for fatigue) at features: holes, shoulders, keyways, grooves, sharp internal corners.
4. Combine stresses with **von Mises** (ductile) or **max normal stress / Mohr-Coulomb** (brittle,
   printed parts across layers, cast iron, CF composites).
5. Check: yield (static), Goodman (fatigue), buckling (slender compression members, thin walls),
   contact (balls, rollers, pins on soft material), creep (polymers under sustained load),
   thermal mismatch (mixed-material assemblies, polymers).
6. Apply safety factor appropriate to uncertainty (Section 17). Printed polymer parts need more.
7. Iterate geometry before material: depth of a beam enters cubed in stiffness.

Common agent mistakes:
- Using UTS instead of yield for ductile metal parts that must not permanently deform.
- Using the short-term modulus of a polymer for a part under constant load (use creep modulus).
- Treating FDM parts as isotropic: Z (layer) direction is often 30–70 % of XY strength *estimate*.
- Forgetting that aluminium has no true endurance limit.
- Treating a hole/shoulder as harmless (Kt 2–3 is normal).
- Euler buckling on a short stocky column (gives unconservative results; use Johnson).
- Using diameter where the formula wants radius (and vice versa) in J, I, Z.

---

## 1. Stress, strain, Hooke's law

| Quantity | Formula | Notes |
|---|---|---|
| Normal stress | σ = F / A | MPa; tension +, compression − |
| Shear stress (average) | τ = V / A | direct shear on pins, bolts, keys |
| Normal strain | ε = ΔL / L₀ | dimensionless; 0.001 = 0.1 % = 1000 µε |
| Shear strain | γ (radians) | |
| Hooke (uniaxial) | σ = E ε | valid below proportional limit |
| Hooke (shear) | τ = G γ | |
| Isotropic relation | G = E / (2(1+ν)) | steel: E 200 GPa, ν 0.29 → G ≈ 78 GPa |
| Bulk modulus | K = E / (3(1−2ν)) | |
| Axial elongation | δ = F L / (A E) | |
| Axial stiffness | k = A E / L | N/mm |
| 3D Hooke | εx = [σx − ν(σy+σz)]/E + αΔT | |

Poisson's ratio ν (typical): steels 0.27–0.30; aluminium 0.33; titanium 0.34; brass 0.34; POM 0.35;
nylon 0.39; PLA/ABS/PETG ~0.35–0.40; rubber ~0.49 (near incompressible).

Stress–strain landmarks (ductile metal): proportional limit → yield (Sy, usually 0.2 % offset)
→ ultimate (Sut) → fracture. Elongation at break: ductile > 5 %, brittle < 5 % (rule of thumb used by
Shigley-style texts). Cast iron, PLA, many CF composites and FDM parts in Z behave brittle.

True vs engineering stress: only matters past yield; ignore for design.

---

## 2. Axial loading

- σ = F/A, δ = FL/(AE). Series bars: δ_total = Σ FᵢLᵢ/(AᵢEᵢ). Parallel members share load by stiffness.
- Statically indeterminate (two materials in parallel, e.g. steel bolt clamping aluminium):
  compatibility δ₁ = δ₂ → load share ∝ AE.
- Bolt/rod in tension: use **tensile stress area** At, not shank area (M3: 5.03 mm², M4: 8.78, M5: 14.2,
  M6: 20.1, M8: 36.6, M10: 58.0 mm² — ISO 898-1 *typical*).
- Bearing stress (pin in hole): σ_b = F / (d · t). Critical for thin sheet and printed lugs.
- Lug/clevis failure modes: tension across net section, shear-out (tear-out) behind the hole,
  bearing, pin shear (single or double shear: A = πd²/4 per shear plane).

---

## 3. Bending

Flexure formula (pure bending, linear elastic, plane sections):

    σ = M · y / I        σ_max = M · c / I = M / Z        Z = I / c

- M: bending moment (N·mm); y: distance from neutral axis (mm); c: distance to extreme fibre;
  I: second moment of area about neutral axis (mm⁴); Z: elastic section modulus (mm³).
- Neutral axis passes through the centroid (homogeneous section).
- Curvature: 1/ρ = M/(EI). **EI = flexural rigidity** — the stiffness design variable.
- Plastic section modulus Zp: moment at full plastification M_p = Sy·Zp. Shape factor Zp/Z:
  rectangle 1.5, solid circle 1.70, I-beam ~1.12–1.15. Only use plastic capacity if permanent set is
  acceptable (not for mechanisms).
- Unsymmetric sections (angles, Z-sections): bend about principal axes or you get twisting/lateral
  deflection. Avoid for precision links.
- Open thin-walled sections (C, angle) loaded off the shear centre also twist — load through the shear
  centre or use closed sections.

Geometric insight (critical for agents):
- Rectangle b×h: I = bh³/12. **Doubling depth h → 8× stiffness, 4× strength.** Doubling width → 2×.
- Moving material away from the neutral axis (tubes, I-sections, ribs) is the cheapest stiffness.
- Hollow tube with D_i = 0.8 D_o keeps ~59 % of the solid's I with only 36 % of the mass.

---

## 4. Torsion

Circular shafts (solid or tube):

    τ = T · r / J          τ_max = T · c / J = 16 T / (π d³)   (solid)
    θ = T · L / (G · J)    (radians)        torsional stiffness k_t = G J / L  (N·mm/rad)

- J: polar second moment (mm⁴). For circles J = 2I.
- Power–torque: T [N·m] = P [W] / ω [rad/s] = 9549 · P[kW] / n[rpm].
- Tube: τ_max = 16 T D / (π (D⁴ − d⁴)).

Thin-walled closed sections (Bredt–Batho):

    τ = T / (2 A_m t)          θ = T L / (G J_eff),   J_eff = 4 A_m² / ∮(ds/t)

A_m = area enclosed by wall mid-line. For a thin round tube J ≈ 2π r_m³ t.

Rectangular solid sections, b ≥ c (long side b, short side c) — classic Saint-Venant coefficients
(Timoshenko; reproduced in most texts):

    τ_max = T / (α b c²)        θ = T L / (β b c³ G)

| b/c | 1.0 | 1.5 | 2.0 | 3.0 | 4.0 | 6.0 | 10 | ∞ |
|---|---|---|---|---|---|---|---|---|
| α | 0.208 | 0.231 | 0.246 | 0.267 | 0.282 | 0.299 | 0.312 | 0.333 |
| β | 0.141 | 0.196 | 0.229 | 0.263 | 0.281 | 0.299 | 0.312 | 0.333 |

Key insight: **open sections are terrible in torsion.** A slit tube is ~(3 r²/t²) times less stiff in
torsion than the closed tube. Close sections (boxes, tubes) for arm links that see twist.

Non-circular shafts with keyways: use Kts (Section 8).

---

## 5. Transverse shear in beams

    τ = V Q / (I b)

V: shear force; Q: first moment of area beyond the cut about neutral axis; b: width at the cut.
Maximum transverse shear (at neutral axis):

| Section | τ_max |
|---|---|
| Rectangle | 1.5 V / A |
| Solid circle | 4 V / (3A) |
| Thin-walled round tube | 2 V / A |
| I-beam / box | ≈ V / A_web (web carries nearly all shear) |

- Transverse shear is negligible vs bending for slender beams (L/h > ~10). It matters for short,
  deep beams, pins, and in sandwich/printed parts with weak interlayer shear.
- Shear deflection adds to bending deflection for short beams (L/h < ~5) — Timoshenko beam.
- Direct shear of pins/bolts: τ = F / (n · πd²/4), n = number of shear planes.

---

## 6. Section properties (common shapes)

I about centroidal axis bending as shown (h is the dimension in the bending plane). Z = I/c.
J listed is the torsion constant (exact for circles, approximate for others).

| Shape | Area A | I | Z (elastic) | J (torsion) |
|---|---|---|---|---|
| Solid rectangle b × h | bh | bh³/12 | bh²/6 | βbc³ (table §4) |
| Solid square a | a² | a⁴/12 | a³/6 | 0.141 a⁴ |
| Solid circle d | πd²/4 | πd⁴/64 | πd³/32 | πd⁴/32 |
| Round tube D, d | π(D²−d²)/4 | π(D⁴−d⁴)/64 | π(D⁴−d⁴)/(32D) | π(D⁴−d⁴)/32 |
| Thin round tube r_m, t | 2πr_m t | π r_m³ t | π r_m² t | 2π r_m³ t |
| Rect. tube B×H outer, b×h inner | BH − bh | (BH³ − bh³)/12 | (BH³ − bh³)/(6H) | ≈ 2t(B−t)²(H−t)²/(B+H−2t) for uniform wall t |
| Symmetric I-beam (flange b, t_f; web t_w; overall h) | 2bt_f + (h−2t_f)t_w | [bh³ − (b−t_w)(h−2t_f)³]/12 | 2I/h | ≈ (2bt_f³ + (h−t_f) t_w³)/3 |
| Triangle (base b, height h), about centroid | bh/2 | bh³/36 | to apex: bh²/24 | — |
| Thin strip (open) b × t, b ≫ t | bt | — | — | bt³/3 |

Parallel axis theorem: I_x' = I_c + A d² (build composite sections, ribs, flanges).
Radius of gyration: r = √(I/A) — needed for buckling. Solid circle r = d/4; rectangle r = h/√12;
thin tube r ≈ r_m/√2.

Worked mini-example (section): 20×20×2 mm square aluminium tube:
I = (20⁴ − 16⁴)/12 = (160 000 − 65 536)/12 = **7 872 mm⁴**; Z = 7 872/10 = 787 mm³.
A solid 20×20 bar has I = 13 333 mm⁴ — the tube keeps 59 % of the stiffness at 36 % of the mass.

---

## 7. Beam deflection cases (standard results)

E in MPa, I in mm⁴, L in mm, P in N, w in N/mm, M₀ in N·mm → δ in mm, θ in rad.
These are standard closed-form results found in every strength-of-materials text and in free sources
such as MIT OCW 2.001 and engineering reference sites.

| # | Support & load | Max deflection δ_max | Location | Max slope θ | Max moment M_max |
|---|---|---|---|---|---|
| 1 | Cantilever, end point load P | PL³/(3EI) | free end | PL²/(2EI) | PL at wall |
| 2 | Cantilever, UDL w | wL⁴/(8EI) | free end | wL³/(6EI) | wL²/2 at wall |
| 3 | Cantilever, end moment M₀ | M₀L²/(2EI) | free end | M₀L/(EI) | M₀ (uniform) |
| 4 | Cantilever, point load P at a from wall | Pa²(3L−a)/(6EI) | free end | Pa²/(2EI) | Pa |
| 5 | Simply supported, central P | PL³/(48EI) | midspan | PL²/(16EI) at ends | PL/4 |
| 6 | Simply supported, UDL w | 5wL⁴/(384EI) | midspan | wL³/(24EI) at ends | wL²/8 |
| 7 | Simply supported, P at a, b (a > b) | Pb(L²−b²)^{3/2}/(9√3 L EI) | x = √((L²−b²)/3) from far support | — | Pab/L |
| 8 | Simply supported, end moment M₀ | M₀L²/(9√3 EI) | x = L/√3 from loaded end | M₀L/(3EI) | M₀ |
| 9 | Fixed–fixed, central P | PL³/(192EI) | midspan | 0 | PL/8 (ends & centre) |
| 10 | Fixed–fixed, UDL w | wL⁴/(384EI) | midspan | 0 | wL²/12 at ends |
| 11 | Propped cantilever (fixed–pinned), UDL | wL⁴/(185EI) | x ≈ 0.42L from pin | — | wL²/8 at fixed end |
| 12 | Propped cantilever, central P | PL³/(48√5 EI) ≈ PL³/(107EI) | x ≈ 0.447L from pin | — | 3PL/16 at fixed end |

Stiffness of a cantilever tip: k = 3EI/L³. Superposition applies for linear elastic small deflections:
add cases. Self-weight of a horizontal arm = UDL with w = ρ g A (careful: ρ in kg/mm³ → use
ρ[kg/m³]·9.81e−9 N/mm³ × A[mm²] = N/mm).

Rules of thumb (estimates, common machine-design practice):
- Deflection L/360 is a building-floor criterion; machines need tighter: general machine frames
  L/1000–L/5000; precision positioning tighter still (budget the error in µm at the tool point).
- Cantilever angular deflection at the end amplifies to position error at a distance: error = θ × arm.
- Fixing both ends (case 9 vs 5) gives 4× stiffness; this is why bearings at both ends of a shaft matter.
- Deflection ∝ L³ (point load) or L⁴ (UDL): halving span → 8–16× stiffer.

Worked mini-example: 300 mm cantilever, 20×20×2 6061 tube (I = 7 872 mm⁴, E = 69 000 MPa), 10 N tip load.
δ = 10·300³/(3·69 000·7 872) = 2.7×10⁸/1.63×10⁹ = **0.166 mm**.
σ = M/Z = (10·300)/787 = **3.8 MPa** — strength is irrelevant; stiffness governs (typical for arms).

---

## 8. Stress concentrations

Peak stress at a geometric discontinuity: σ_max = Kt · σ_nom (σ_nom on the net section, as defined by
the chart you use — always check which area the chart uses).

Typical Kt (estimates from Peterson-style charts, widely reproduced; use for screening):

| Feature | Kt typical |
|---|---|
| Small circular hole in wide plate, tension | 3.0 (exact for infinite plate) |
| Same, plate width ≈ 3× hole diameter (net section) | ~2.3 |
| Elliptical hole, semi-axis a ⊥ to load, b ∥ | 1 + 2a/b (crack-like when b→0) |
| Shaft shoulder, D/d = 1.5, r/d = 0.02 (sharp) bending | ~2.5–2.7 |
| Shaft shoulder, D/d = 1.5, r/d = 0.05 bending | ~2.0 |
| Shaft shoulder, D/d = 1.5, r/d = 0.1 bending | ~1.6–1.7 |
| Same, torsion (Kts) at r/d = 0.02 / 0.1 | ~1.8–2.0 / ~1.3 |
| End-milled (profile) keyway, bending / torsion | ~2.0–2.2 / ~2.8–3.0 (sharp corner) |
| Sled-runner keyway, bending | ~1.6–1.7 |
| Retaining-ring groove (sharp bottom) | ~3–5 |
| Transverse hole in shaft (d/D ~0.1), bending | ~2.2–2.5 |
| Thread root (rolled / cut), fatigue Kf | ~2.2–3.0 / ~2.8–3.8 (Shigley-style fatigue factors) |
| Sharp internal corner in printed/moulded part | 3+ (effectively unbounded as r→0) |

Fatigue notch factor: **Kf = 1 + q(Kt − 1)**, notch sensitivity 0 ≤ q ≤ 1. Hard steels and small radii
q→0.8–1.0; soft metals, tiny radii q lower; aluminium q lower than steel at the same radius. Use q = 1
(Kf = Kt) when unsure — conservative. Neuber/Peterson give q = 1/(1 + √a/√r) with a material constant.

Rules:
- Static loading, ductile metal: local yielding redistributes; Kt usually ignored for static strength
  (but not for brittle materials, printed parts, or fatigue).
- Fatigue: always apply Kf to the alternating (and with Goodman, mean) stress.
- Brittle materials (cast iron is the exception — internal flaws dominate), polymers and FDM parts:
  apply Kt even for static load.
- Design fixes: increase fillet radius (r/d ≥ 0.1 is a good target), relief grooves, undercut
  shoulders, move holes to low-stress regions (near neutral axis), add bosses around holes,
  minimum internal fillet ≈ 0.5–1× wall thickness in plastics.
- Interacting concentrations multiply in the worst case (hole at a fillet).

---

## 9. Combined stress, Mohr's circle, principal stresses

Plane stress (σx, σy, τxy):

    σ₁,₂ = (σx + σy)/2 ± √[ ((σx − σy)/2)² + τxy² ]
    τ_max(in-plane) = √[ ((σx − σy)/2)² + τxy² ]
    tan 2θp = 2τxy / (σx − σy)       (principal planes; max-shear planes at ±45°)

Absolute max shear in 3D: τ_abs = (σ_max − σ_min)/2 including σ₃ = 0 for plane stress — if σ₁ and σ₂
have the same sign, τ_abs = σ₁/2, larger than the in-plane value. Common mistake.

Mohr's circle construction (plane stress):
1. Plot points X(σx, τxy) and Y(σy, −τxy) (pick one sign convention and keep it).
2. Centre C = ((σx+σy)/2, 0); radius R = √[((σx−σy)/2)² + τxy²].
3. σ₁ = C + R, σ₂ = C − R; τ_max = R.
4. Rotating the element by θ rotates the diameter by 2θ on the circle in the same sense.

Typical combined cases:
- **Shaft with bending + torsion** (most common): σ = 32M/(πd³), τ = 16T/(πd³) at the surface.
  Principal: σ₁,₂ = σ/2 ± √((σ/2)² + τ²).
- **Bending + axial**: σ = F/A ± M c/I (add on one face, subtract on other).
- **Eccentric axial load**: M = F·e; check for tension on the far side.
- **Thin-walled pressure vessel**: hoop σ_h = p r / t, axial σ_a = p r /(2t) (cylinder); sphere p r/(2t).
- **Bolt in tension + torsion during tightening**: von Mises with τ from thread torque.

Worked mini-example: 10 mm steel shaft, M = 5 000 N·mm, T = 3 000 N·mm.
σ = 32·5 000/(π·1 000) = 50.9 MPa; τ = 16·3 000/(π·1 000) = 15.3 MPa.
σ₁ = 25.5 + √(25.5² + 15.3²) = 25.5 + 29.7 = 55.2 MPa; σ₂ = −4.2 MPa; τ_max = 29.7 MPa.
von Mises σ' = √(σ² + 3τ²) = √(2 591 + 702) = 57.4 MPa.

---

## 10. Failure theories: von Mises vs Tresca (and brittle criteria)

| Theory | Equivalent stress / criterion | Use when |
|---|---|---|
| **von Mises (distortion energy)** | σ' = √[σ₁² − σ₁σ₂ + σ₂²] (plane) = √[σx² − σxσy + σy² + 3τxy²]; fail when σ' ≥ Sy | Default for ductile metals; matches test data best |
| 3D von Mises | σ' = √{½[(σ₁−σ₂)² + (σ₂−σ₃)² + (σ₃−σ₁)²]} | FEA output "von Mises" |
| **Tresca (max shear)** | σ₁ − σ₃ ≥ Sy (with σ₃ the min incl. 0) | Conservative ductile check (≤ 15 % more conservative than VM) |
| Max normal stress (Rankine) | σ₁ ≥ Sut or σ₃ ≤ −Suc | Brittle, Sut ≈ Suc (rare) |
| Coulomb–Mohr (brittle) | σ₁/Sut − σ₃/Suc ≥ 1/n | Brittle with Suc > Sut (cast iron, PLA-like, FDM in Z) |
| Modified Mohr | similar, less conservative in 4th quadrant | Brittle, Shigley preference |

Special forms for bending σ + torsion τ (shaft):
- von Mises: σ' = √(σ² + 3τ²)
- Tresca: σ_eq = √(σ² + 4τ²)

Shear yield: **Ssy = 0.577 Sy (von Mises)**, 0.5 Sy (Tresca). Use 0.577 Sy for pins and keys in shear
(typical practice; some codes use 0.5 Sy for conservatism, and 0.6 Sy is common in bolt standards).

Ductile vs brittle selection: elongation at break > ~5 % → ductile theories; < 5 % → brittle theories.
FDM printed parts: treat as brittle across layers; quasi-ductile along filament (PETG, nylon) at best.

Safety factor with von Mises: n = Sy / σ'.

---

## 11. Buckling (columns, struts, linear actuators, leadscrews)

### 11.1 Euler (long, elastic)

    P_cr = π² E I / (K L)²        σ_cr = π² E / (K L / r)²

| End condition | K (theoretical) | K (recommended design, AISC-style) |
|---|---|---|
| Pinned–pinned | 1.0 | 1.0 |
| Fixed–fixed | 0.5 | 0.65 |
| Fixed–pinned | 0.7 | 0.80 |
| Fixed–free (flagpole) | 2.0 | 2.1 |
| Fixed–guided (rotation fixed, translation free) | 1.0 | 1.2 |

"Fixed" is rarely truly fixed in a mechanism — use the design K (or pinned–pinned) unless the end is
genuinely rigid. Buckling occurs about the axis with the **smallest I** (smallest r).

### 11.2 Johnson parabola (intermediate, inelastic)

    σ_cr = Sy − (Sy / (2π))² · (K L / r)² / E        P_cr = A σ_cr

Transition slenderness (Euler σ_cr = Sy/2, where the two curves are tangent):

    (K L / r)_t = √(2 π² E / Sy)

| Material | E (MPa) | Sy (MPa) | (KL/r)_t |
|---|---|---|---|
| Mild steel | 200 000 | 250 | ~126 |
| 1018 CD | 205 000 | 370 | ~105 |
| 6061-T6 | 69 000 | 276 | ~70 |
| 7075-T6 | 72 000 | 503 | ~53 |
| POM | 3 000 | 65 | ~30 |

Use Euler if KL/r > (KL/r)_t, Johnson if below. Very short (KL/r < ~10–20): simple compression yield.
Note: some sources use the transition where Euler stress = Sy (√(π²E/Sy)); the tangent-point version
above is the Shigley/Johnson convention.

### 11.3 Other buckling to remember
- Eccentric loading: secant formula; initial crookedness and eccentricity reduce real capacity —
  real columns fail at 50–80 % of Euler near the transition (*estimate*).
- Leadscrews/ballscrews: check compressive buckling with mount type (fixed–fixed vs fixed–free) and
  critical speed (whip); vendors (THK, Hiwin) publish charts.
- Thin walls: local buckling of tube walls, flange crippling, shear buckling of webs. Thin-walled tube
  under axial compression: classical σ_cr = 0.605 E t / R, but real shells reach only 20–50 % of that
  due to imperfections (NASA SP-8007 knock-down factors). Keep D/t < ~50 for robust tubes (*estimate*).
- Lateral-torsional buckling of deep narrow beams (tall thin ribs, I-beams without lateral support).
- Plate buckling under compression: σ_cr = k π² E /(12(1−ν²)) (t/b)², k ≈ 4 for simply supported edges.

Worked mini-example: 8 mm steel rod, 500 mm long, pinned–pinned.
I = π·8⁴/64 = 201 mm⁴; r = d/4 = 2 mm; KL/r = 250 > 105 → Euler.
P_cr = π²·200 000·201/500² = **1 590 N**. With n = 3 → allowable ~530 N.

---

## 12. Fatigue

### 12.1 Basics
- Parts fail at cyclic stresses well below yield. Cracks start at surface features, scratches,
  inclusions, stress concentrations, fretting zones, layer lines in prints.
- Regimes: low-cycle (< ~10³), high-cycle (10³–10⁶/10⁷), infinite life (steel beyond ~10⁶–10⁷).
- Stress definitions: σ_m = (σ_max + σ_min)/2, σ_a = (σ_max − σ_min)/2, R = σ_min/σ_max.
  Fully reversed (rotating bending): R = −1, σ_m = 0. Repeated (0 → max): R = 0, σ_a = σ_m.

### 12.2 Endurance limit estimates (rotating-beam specimen, Se')

| Material | Se' estimate | Note |
|---|---|---|
| Steel, Sut ≤ 1 400 MPa | 0.5 Sut | Shigley/Mischke; scatter ±~20 % |
| Steel, Sut > 1 400 MPa | ~700 MPa | |
| Cast iron | ~0.4 Sut | |
| Aluminium alloys | **no endurance limit** — use fatigue strength at 5×10⁸ cycles ≈ 0.3–0.4 Sut, max ~130–160 MPa | |
| Titanium alloys | ~0.5–0.6 Sut (has a knee) | |
| Copper alloys (brass) | ~0.3–0.4 Sut at 10⁸, no true limit | |
| POM (acetal) | ~20–35 MPa at 10⁶–10⁷ (*estimate*, frequency/temperature dependent) | among the best unfilled plastics for fatigue |
| Nylon (cond.) | ~15–25 MPa at 10⁷ (*estimate*) | |
| FDM PLA/PETG/ABS | ~20–40 % of printed UTS at 10⁶ (*estimate*, very print-dependent) | layer lines are notches |

### 12.3 Marin factors (Shigley convention)

    Se = ka · kb · kc · kd · ke · kf · Se'

**ka — surface factor:** ka = a · Sut^b (Sut in MPa)

| Finish | a (MPa) | b |
|---|---|---|
| Ground | 1.58 | −0.085 |
| Machined or cold-drawn | 4.51 | −0.265 |
| Hot-rolled | 57.7 | −0.718 |
| As-forged | 272 | −0.995 |

(Cap ka at 1.0.) Example: machined, Sut = 600 → ka ≈ 0.83.

**kb — size factor (rotating bending / torsion, round):**
- 2.79 ≤ d ≤ 51 mm: kb = 1.24 d^−0.107
- 51 < d ≤ 254 mm: kb = 1.51 d^−0.157
- Axial loading: kb = 1. Non-rotating or non-round: use equivalent diameter d_e (rectangle in
  non-rotating bending: d_e = 0.808 √(hb)).

**kc — load factor:** bending 1.0; axial 0.85; torsion 0.59 (when using Se directly for shear; if
combining via von Mises, use kc = 1 and fold torsion into σ').

**kd — temperature:** ~1.0 up to ~250 °C for steel; drops above. Polymers: much stronger temperature
sensitivity — derate significantly above ~40 °C (*estimate*).

**ke — reliability:**

| Reliability | 50 % | 90 % | 95 % | 99 % | 99.9 % | 99.99 % |
|---|---|---|---|---|---|---|
| ke | 1.000 | 0.897 | 0.868 | 0.814 | 0.753 | 0.702 |

**kf — miscellaneous:** corrosion, plating (chrome/nickel plating can cut Se substantially), fretting,
residual stress (shot peening / rolling *increase* Se), etc. Shigley puts Kf here in some editions;
in this file apply Kf to stress, not strength — don't double count.

### 12.4 S-N curve (steel, high-cycle, Basquin form)

    Sf = a · N^b,   a = (f Sut)² / Se,   b = −(1/3) log₁₀(f Sut / Se)     for 10³ ≤ N ≤ 10⁶

f ≈ 0.9 for Sut < ~500 MPa, falling to ~0.8 at ~1 400 MPa (*estimate*, Shigley Fig. 6-18).
Life at a given stress: N = (σ_a / a)^(1/b).
Variable amplitude: Miner's rule Σ nᵢ/Nᵢ = 1 at failure (in practice failures occur at 0.7–2.2; use
≤ 0.5–0.7 for safety-critical — *estimate*).

### 12.5 Mean stress: Goodman and friends

With σa and σm already multiplied by Kf (or von Mises equivalents σa', σm' of Kf/Kfs-amplified
components):

| Criterion | Equation (factor of safety n) | Character |
|---|---|---|
| **Modified Goodman** | σa/Se + σm/Sut = 1/n | Default design choice; slightly conservative, linear |
| Soderberg | σa/Se + σm/Sy = 1/n | Very conservative |
| Gerber | n σa/Se + (n σm/Sut)² = 1 | Fits ductile data well (analysis, not conservative design) |
| ASME-elliptic | (n σa/Se)² + (n σm/Sy)² = 1 | Used in shaft design standards |
| **Langer (first-cycle yield)** | σa + σm = Sy/n | Always check alongside Goodman |

Shaft design shortcut (DE-Goodman, Shigley):

    1/n = (16/(π d³)) { (1/Se) √[4(Kf Ma)² + 3(Kfs Ta)²] + (1/Sut) √[4(Kf Mm)² + 3(Kfs Tm)²] }

Typical rotating shaft: Ma = bending moment (rotation makes it fully reversed), Mm = 0, Ta = 0,
Tm = steady torque.

Worked mini-example (fatigue): steel shaft Sut = 600 MPa, Sy = 500 MPa, machined, d = 10 mm,
99 % reliability, rotating bending σa,nom = 50 MPa, steady torsion τm,nom = 30 MPa, Kf = 1.8, Kfs = 1.5.
1. Se' = 0.5·600 = 300 MPa.
2. ka = 4.51·600^−0.265 = 0.83; kb = 1.24·10^−0.107 = 0.97; ke = 0.814 → Se = 300·0.83·0.97·0.814 ≈ **196 MPa**.
3. σa' = 1.8·50 = 90 MPa; σm' = √3·1.5·30 = 78 MPa.
4. Goodman: 1/n = 90/196 + 78/600 = 0.459 + 0.130 = 0.589 → **n ≈ 1.7**.
5. Langer: n_y = 500/(90 + 78) ≈ 3.0. Fatigue governs.

Fatigue design tips: polish/grind highly stressed surfaces, generous fillets, avoid fretting (clamped
joints on rotating shafts), keep printed parts at low stress amplitude, orient FDM layers so cyclic
bending stresses run along filaments, never put cyclic tension across layer lines.

---

## 13. Creep and stress relaxation (especially polymers)

- **Creep:** strain grows over time at constant stress. **Relaxation:** stress decays at constant
  strain (press-fits, snap-fits, clamped plastic, bolted plastic flanges lose preload).
- Metals: creep matters above ~0.3–0.4 T_melt (K) — irrelevant for steel/aluminium in room-temperature
  mechanisms; relevant for aluminium above ~150 °C (*estimate*), lead, solder.
- **Polymers creep at room temperature.** Behaviour depends strongly on temperature relative to the
  glass transition Tg (amorphous) and on crystallinity.

| Polymer | Tg (°C) typical | HDT @0.45 MPa (°C) typical | Creep behaviour |
|---|---|---|---|
| PLA | 55–65 | ~55 | Good at 20 °C, collapses near 50–60 °C (car interior, sunlight, motor housings) |
| PETG | ~80 | ~70 | Moderate |
| ABS / ASA | ~100–105 | ~95 | Moderate; better hot than PLA |
| PC | ~145–150 | ~135 | Good, but notch-sensitive |
| POM (acetal) | −60 (semi-crystalline, Tm ~165–175) | ~160 (homopolymer) | Good among unfilled thermoplastics (~5× PP per Interplas) |
| PA6 / PA66 / PA12 | ~50 / ~60 / ~40 (Tm 220/260/178) | 150–200 (dry, depends) | Moderate; worse when wet |
| CF/GF-filled nylon | — | higher | Much better creep; fibre fraction governs |

Design approach:
1. Use the **creep (apparent) modulus** E_c(t, σ, T) from supplier isochronous curves (CAMPUS database,
   Celanese/DuPont/BASF design guides) instead of the short-term E. Typical *estimate*: at room
   temperature and moderate stress, E_c after 1 000 h ≈ 40–70 % of short-term E for POM/nylon;
   lower for amorphous polymers near Tg.
2. Limit sustained stress: rule of thumb (*estimate*) continuous load ≤ 20–30 % of short-term yield for
   POM/nylon at 23 °C; ≤ 15–25 % for FDM PLA/PETG/ABS; lower at elevated temperature.
3. Avoid polymer under bolted clamping load without metal compression limiters (brass/steel inserts,
   sleeves) — preload relaxes.
4. Creep rupture: polymers can crack after years at stress below short-term strength (Madison Group
   POM fastener case: failure after 4–5 years).
5. Moisture: nylons absorb water (PA6 up to ~2.5–3 % at 50 % RH equilibrium, ~9 % saturated —
   *typical datasheet*) → modulus may drop to roughly 1/2–1/3 of dry value and dimensions grow
   (~0.2–0.3 % per 1 % moisture — *estimate*). Design PA with *conditioned* properties.
6. Temperature: properties drop sharply approaching Tg/HDT. Motor housings and stepper mounts reach
   50–80 °C — **do not use PLA to mount steppers** (common failure).

Simple creep model (power law) for estimates: ε(t) = ε₀ + A σⁿ tᵐ, m ≈ 0.1–0.3 for many polymers
(*estimate*) — so creep strain at 10 years ≈ several times the 1 h value.

---

## 14. Fracture and toughness basics

- Linear elastic fracture mechanics (LEFM): a crack of length a under stress σ has stress intensity

      K_I = Y σ √(π a)        failure when K_I ≥ K_IC

  Y ≈ 1.0 centre crack in wide plate (a = half-length), ≈ 1.12 edge crack (a = depth).
- Critical crack size: a_c = (1/π) (K_IC / (Y σ))².
- Plane-strain validity (ASTM E399): thickness B ≥ 2.5 (K_IC/Sy)². Thin sections are tougher in practice.
- Toughness vs strength trade-off: high-strength tempers (7075-T6, high-hardness steel) are less
  tough than softer ones.
- Charpy impact energy: useful qualitative ranking, not a design value. Watch ductile-to-brittle
  transition in ferritic steels at low temperature; austenitic stainless, aluminium, titanium don't have
  a sharp transition.

Typical K_IC (MPa·√m, *typical/screening*, Wikipedia + course tables; varies with temper/orientation):

| Material | K_IC |
|---|---|
| Mild/structural steel | 50–150+ (often too ductile for valid K_IC) |
| 4340 steel (high strength) | ~50–60 |
| Maraging steel | ~100–175 |
| Austenitic stainless 304/316 | > 100 (very tough) |
| Al 6061-T6 | ~29 |
| Al 7075-T6 | ~20–35 (≈27) |
| Al 2024-T3 | ~35–45 |
| Ti-6Al-4V | ~45–100 (processing dependent) |
| Grey cast iron | ~6–20 |
| PMMA (acrylic) | ~0.7–1.6 |
| Polystyrene | ~0.7–1.1 |
| PC | ~2–3.5 |
| POM / nylon | ~3–5 (*estimate*) |
| CFRP (laminate, in-plane) | ~20–50 (*estimate*, layup dependent) |
| Glass / ceramics | 0.7–5 |

Worked mini-example: 7075-T6 plate, σ = 300 MPa, edge crack, K_IC = 27:
a_c = (1/π)(27/(1.12·300))² = **2.1 mm**. A 2 mm scratch/corrosion pit can be critical at high stress
— reason to avoid running 7075 near yield with notches, and to prefer 6061/2024 for damage tolerance.

Practical rules:
- Acrylic, PS, PLA: low toughness — avoid sharp notches, press-fits, threads cut into them, impact loads.
- Brittle failure is sudden; ductile failure gives warning. Prefer ductile materials for safety-critical
  load paths, or raise safety factor.
- Environment: stress-corrosion cracking (7075-T6 in short-transverse direction; use T73/T7351 for
  SCC resistance), solvent stress cracking of PC/ABS (thread-lockers, cleaners!), hydrogen
  embrittlement of high-strength plated steel fasteners.

---

## 15. Thermal expansion and thermal stress

    δ = α L ΔT                   (free expansion)
    σ = −E α ΔT                  (fully constrained bar; compressive on heating)
    Mismatch between two materials: Δδ = (α₁ − α₂) L ΔT

Bi-material constraint (e.g. bolted aluminium plate to steel frame) builds shear in fasteners or
bending (bimetal strip curvature). Allow slotted holes or a floating mount at one end.

Typical CTE (µm/m·K = 10⁻⁶/K, *typical*): steel 11–13; stainless 304 ~17; 17-4PH ~11; aluminium
~23; brass ~20; titanium ~8.6–9; Invar ~1.2; POM ~100–120; PA ~80–100; PLA ~68–75; PETG ~60–70;
ABS ~80–95; PC ~65–70; CFRP UD fibre direction ~0 (−0.5 to +1); CFRP quasi-iso ~2–4;
GFRP/FR4 in-plane ~14–17; wood along grain ~3–5, across grain 30–60.

Worked mini-examples:
- 300 mm aluminium plate on steel frame, ΔT = 30 K: Δδ = (23.6 − 12)·10⁻⁶·300·30 = **0.10 mm** —
  enough to bind a precision linear guide.
- 200 mm PLA part, ΔT = 40 K: δ = 68·10⁻⁶·200·40 = **0.54 mm**.
- Constrained steel bar, ΔT = 50 K: σ = 200 000·12·10⁻⁶·50 = **120 MPa** — thermal stress is not small.

Other thermal points:
- Bearing fits: aluminium housings expand away from steel bearings when hot → outer race creep;
  use steel sleeves or tighter fits. Shafts in plastic bores loosen/tighten with temperature.
- Polymers' CTE is 5–10× metals: avoid long plastic–metal bonded joints; leave clearance.
- Thermal conductivity matters for stepper mounts (aluminium spreads heat, PLA softens).

---

## 16. Contact stress (Hertz) basics

Assumptions: elastic, frictionless, smooth, contact small vs radii.

Effective modulus and radius:

    1/E* = (1 − ν₁²)/E₁ + (1 − ν₂²)/E₂
    1/R  = 1/R₁ + 1/R₂        (flat: R = ∞; concave surface: negative radius)

**Sphere on sphere/flat (point contact), load F:**

    a  = (3 F R / (4 E*))^(1/3)          contact radius
    p₀ = 3 F / (2 π a²)                  max pressure (= 1.5 × mean)
    δ  = a² / R                          approach
    τ_max ≈ 0.31 p₀ at depth ≈ 0.48 a    (subsurface — origin of spalling)

**Cylinder on cylinder/flat (line contact), load F over length L:**

    b  = √(4 F R / (π L E*))             half-width
    p₀ = 2 F / (π b L)
    τ_max ≈ 0.30 p₀ at depth ≈ 0.78 b

Allowable contact pressure (*estimates / typical*):
- Through-hardened bearing steel (52100, ~60 HRC): ISO 76 static limit for ball bearings ≈ 4 200 MPa;
  for rolling life design typically p₀ ≤ ~1 500–2 500 MPa.
- Unhardened steel or any ductile metal: subsurface yield begins at p₀ ≈ 1.6 Sy (point contact) and
  p₀ ≈ 1.67 Sy (line contact), von Mises, ν ≈ 0.3. Shakedown allows somewhat more under repeated rolling.
- Aluminium 6061-T6: yield onset p₀ ≈ 1.6·276 ≈ 440 MPa — brinelled easily by steel balls/rollers.
- POM/nylon rollers: limited by creep/heat; keep mean pressures in tens of MPa.

Worked mini-examples:
1. 6 mm steel ball on steel flat, F = 50 N: E* = 115 GPa, R = 3 mm →
   a = (3·50·3/(4·115 000))^(1/3) = 0.099 mm; p₀ = 150/(2π·0.0098) ≈ **2 400 MPa**.
   Fine for hardened bearing races; would dent 6061 (yield onset ~440 MPa) and mild steel.
2. Same ball on POM flat (E = 3 000, ν = 0.35): E* ≈ 3 400 MPa → a ≈ 0.32 mm, p₀ ≈ **230 MPa** >>
   POM yield → indents/creeps. Use larger radii, line contact, or metal inserts.

Design rules:
- Hertz stress ∝ F^(1/3) for point contact — doubling load raises p₀ only 26 %, but life of rolling
  elements ∝ load^−3 (balls), ^−10/3 (rollers).
- Bigger radii and conforming contact (ball in groove) cut stress dramatically.
- Steel V-wheels on aluminium extrusion, cam followers on aluminium cams: check p₀ vs 1.6 Sy.
- Belt/pulley and gear teeth contact: see gear/belt knowledge files (AGMA contact stress).

---

## 17. Safety factor selection guidance

Definition: n = strength / stress (or load capacity / applied load). Use the *design factor* chosen
up front; compute the *realised* factor after rounding sizes.

Guidance (synthesised from Juvinall & Marshek's / Vidosic-style tables and common machine-design
practice — *estimates*; codes override when applicable):

| Situation | n (on yield, static) |
|---|---|
| Well-known material (certified), loads well defined, analysis validated, controlled environment | 1.25–1.5 |
| Typical machine part, average material data, loads determined with some confidence | 1.5–2.0 |
| Average materials, loads/environment moderately uncertain (default for Mechy metal parts) | 2.0–2.5 |
| Less-tried materials, brittle materials, uncertain loads | 2.5–3.0 |
| Untried materials, unknown loads/environment, or failure would injure people | 3.0–4.0+ |
| **FDM / 3D-printed polymer parts** (vs datasheet XY strength; anisotropy, porosity, process scatter) | **3–4** (on Z-direction strength if load crosses layers) |
| Polymer parts under sustained load | apply n on creep-rupture strength or limit strain; n ≥ 2 on long-term value |
| Fatigue (on Goodman, with Marin factors applied) | 1.5–2.0 (more if load spectrum is guessed) |
| Buckling | 2.5–3.5 (sensitive to imperfections and end fixity); thin shells higher |
| Lifting / overhead loads | follow standards (e.g. ASME B30, EN 13155; often 4–5 on ultimate for rigging) |
| Pressure vessels | follow ASME BPVC (≈3.5 on UTS for Div. 1) |

Multiplicative (Pugsley-style) thinking: n = n_material × n_load × n_analysis × n_consequence.
Examples: material data ±10 % → 1.1; loads ±30 % → 1.3; simplified hand analysis → 1.2; serious
consequence → 1.3 ⇒ n ≈ 2.2.

Rules:
- Apply n to loads that are *uncertain*; don't stack n on top of an already conservative load case
  (e.g. stall torque of a motor is already a ceiling — n = 1.5 may be enough on stall).
- For mechanisms driven by motors, the worst static load is often **motor stall torque × gear ratio**,
  or a crash/collision into an end stop — design the drivetrain to survive that or include a slip
  clutch/current limit.
- Impact: dynamic load factor for suddenly applied load = 2× static; for drop from height h:
  F ≈ W(1 + √(1 + 2h/δ_st)).
- Stiffness-driven parts naturally have high strength factors (often n > 10) — that's fine.
- Report the governing failure mode and its realised factor.

---

## 18. Material property table (common engineering materials)

Room-temperature *typical* values for screening. ρ kg/m³; E GPa; Sy (0.2 % yield) MPa; Sut MPa;
CTE 10⁻⁶/K; cost tier: $ cheap commodity → $$$$$ expensive (raw stock per kg + machining difficulty,
*estimate*). Sources: ASM/MatWeb-derived datasheets (6061/7075 cross-checked against Quickparts/ASM
sheet, MakeItFrom, PMC), Prusament TDS (PLA/PETG), DuPont/Celanese-sourced Delrin TDS (Trident,
HPC Europe), Shigley appendix-style typical values. Ranges reflect grade/temper/process variation.

### 18.1 Metals

| Material | ρ | E | G | Sy | Sut | Elong % | CTE | Cost | Notes |
|---|---|---|---|---|---|---|---|---|---|
| Structural steel S235 / A36 | 7 850 | 200 | 79 | 235–250 | 360–550 | 20–25 | 12 | $ | Plate, weldable, frames |
| 1018 cold-drawn | 7 870 | 205 | 80 | ~370 | ~440 | 15 | 11.7–12 | $ | Shafts, pins (low duty) |
| 1045 cold-drawn | 7 850 | 205 | 80 | ~530 | ~625 | 12 | 11–12 | $ | Shafts; induction hardenable |
| 4140 pre-hard (Q&T ~28–32 HRC) | 7 850 | 205 | 80 | 650–900 | 950–1 100 | 15–17 | 12.2 | $$ | High-strength shafts, gears |
| Linear shaft (CF53/Cf53, induction hardened ~60 HRC case) | 7 850 | 210 | 81 | core ~400–550 | ~650–800 | — | 11–12 | $$ | Rods for linear bearings |
| 52100 bearing steel (hardened) | 7 810 | 210 | 80 | ~1 600–2 000 | ~2 000–2 200 | <2 | 12 | $$ | Balls/races, brittle |
| Stainless 304 annealed | 8 000 | 193 | 77 | ~215 | ~505 | 40+ | 17.3 | $$ | Corrosion; work-hardens; galls |
| Stainless 316 annealed | 8 000 | 193 | 77 | ~205–290 | ~515–580 | 40+ | 16 | $$ | Marine/chemical |
| Stainless 303 | 8 000 | 193 | 77 | ~240 | ~620 | 40+ | 17.3 | $$ | Free-machining 304 variant |
| 17-4PH H900 / H1150 | 7 780 | 197 | 77 | ~1 170 / ~725 | ~1 310 / ~930 | 10 / 16 | 10.8 | $$$ | High strength stainless |
| 440C hardened | 7 650 | 200 | 78 | ~1 900 | ~1 970 | 2 | 10.2 | $$$ | Stainless bearings/blades |
| Grey cast iron (class 30) | 7 200 | 90–115 | ~40 | — (brittle) | ~210 (Suc ~750) | <1 | 10.5 | $ | Damping, machine bases |
| Al 6061-T6 | 2 700 | 68.9 | 26 | 276 (min ~240) | 310 | 12 | 23.6 | $ | Default machined/extruded Al |
| Al 6063-T5/T6 (extrusion profiles) | 2 700 | 68.9 | 26 | 145–215 | 185–240 | 8–12 | 23.4 | $ | V-slot/T-slot extrusions |
| Al 7075-T6 | 2 810 | 71.7 | 27 | ~480–503 | ~570 | 11 | 23.4 | $$ | High strength; poor weldability, SCC |
| Al 2024-T3 | 2 780 | 73.1 | 28 | ~345 | ~483 | 18 | 23.2 | $$ | Fatigue-tolerant aerospace sheet |
| Al 5052-H32 | 2 680 | 70.3 | 26 | ~193 | ~228 | 12 | 23.8 | $ | Sheet metal (bends well) |
| Brass C360 (free-cutting, half hard) | 8 500 | 97 | 37 | 124–310 | 340–470 | 15–50 | 20.5 | $$ | Inserts, fittings, bushings |
| Bearing bronze C932 (SAE 660) | 8 930 | 100 | 37 | ~125 | ~240 | 20 | 18 | $$ | Plain bushings |
| Ti CP Grade 2 | 4 510 | 105 | 45 | 275–345 | 345–450 | 20 | 8.6 | $$$$ | Corrosion |
| Ti-6Al-4V Grade 5 (annealed) | 4 430 | 114 | 44 | ~880 | ~950 | 10–14 | 8.6–9.2 | $$$$$ | Highest strength-to-weight metal; hard to machine |
| Spring steel (music wire ASTM A228) | 7 850 | 200 | 79–81 | wire-size dependent (~0.6–0.8 Sut) | 1 600–2 800 | — | 12 | $ | Springs |

### 18.2 Polymers (injection-moulded / stock unless noted)

| Material | ρ | E | Sy (or σ_t) | Elong % | CTE | Max cont. temp (°C, est.) | Cost | Notes |
|---|---|---|---|---|---|---|---|---|
| POM homopolymer (Delrin 150) | 1 420 | 2.9–3.1 | ~70–76 (yield) | 25–40 | 100–120 | ~90 | $$ | Low friction, gears, bushings, good fatigue, stiff for a plastic |
| POM copolymer (Hostaform/Celcon) | 1 410 | 2.6–2.9 | ~60–65 | 30–60 | 110 | ~100 | $$ | Better chemical/hot water resistance, slightly weaker |
| PA6 dry / conditioned | 1 130 | ~3.0 / ~1.0–1.5 | ~80 / ~40–50 | 30 / 150+ | 80–100 | ~80–100 | $$ | Tough, wear resistant, absorbs water |
| PA66 dry / conditioned | 1 140 | ~3.0 / ~1.5–2.0 | ~85 / ~55 | 25 / 100+ | 80 | ~100 | $$ | |
| PA12 (SLS/MJF printed) | 1 010 | 1.7–1.8 | ~48 (UTS) | 10–20 | ~100 | ~80 | $$$ | Near-isotropic print; good snap-fits |
| UHMW-PE | 940 | 0.7–0.9 | ~20 | 300+ | 150–200 | ~80 | $$ | Wear strips, very low friction, high creep |
| PTFE | 2 150 | 0.4–0.6 | ~10–15 | 300 | 100–150 | ~260 | $$$ | Lowest friction, cold flows badly |
| PC (polycarbonate) | 1 200 | 2.3–2.4 | ~60–65 | 100 | 65–70 | ~115 | $$ | Tough, clear; notch & solvent sensitive |
| PMMA (acrylic) | 1 190 | 3.0–3.3 | ~70 (UTS, brittle) | 3–5 | 70–75 | ~80 | $ | Brittle, laser-cuttable |
| PEEK | 1 300 | 3.6–4.0 | ~95–100 | 30 | 45–50 | ~250 | $$$$$ | High temp/chemical |

### 18.3 FDM/FFF printed polymers (as-printed, 100 % infill, XY = along filament)

Printed values are **lower and more variable** than resin datasheet values. Z (interlayer) strength
typically 30–70 % of XY (*estimate*, highly dependent on nozzle temperature, layer height, cooling,
moisture). Partial infill: strength roughly scales with load-bearing area; walls/perimeters carry most
bending load — use ≥ 4 perimeters for structural parts.

| Material | ρ | E (GPa) XY | σ_t XY (MPa) | Z strength (est.) | Elong % | CTE | Tg/HDT (°C) | Cost | Notes |
|---|---|---|---|---|---|---|---|---|---|
| PLA | 1 240 | 2.3–3.5 (Prusament TDS 2.3–2.4) | 50–60 (Prusament yield 51–59) | 20–40 | 2–6 | 68–75 | Tg ~60 | $ | Stiff, brittle, creeps when warm. Prototypes, jigs, indoor cold parts |
| PETG | 1 270 | 1.5–2.1 (Prusament 1.5–1.6) | 45–50 (Prusament 47–50) | 25–40 | 5–20 | 60–70 | Tg ~80 | $ | Tougher than PLA, good layer adhesion, slightly flexible |
| ABS / ASA | 1 040 / 1 070 | 1.8–2.3 | 35–45 | 15–30 | 3–10 | 80–95 | Tg ~100 | $ | Heat tolerant, warps; ASA UV stable |
| PC (printed) | 1 200 | 2.0–2.4 | 55–65 | 25–45 | 5–10 | 65–70 | Tg ~145 | $$ | Strong, hot, hard to print |
| Nylon (PA6/PA12 FDM) | 1 010–1 140 | 0.8–2.0 (wet-dependent) | 40–60 | 25–45 | 20–200 | 80–110 | ~50 / higher HDT | $$ | Tough, wear; must dry filament |
| CF-filled PETG/PA (chopped) | 1 200–1 300 | 4–8 (XY) | 50–100 (XY) | often ≤ unfilled Z | 2–5 | 20–50 (XY) | as matrix | $$$ | Stiffer & more dimensionally stable; lower toughness; abrasive |
| TPU 95A | 1 210 | ~0.03 | ~30–50 (at break) | — | 400–600 | ~150 | — | $$ | Flexible: dampers, grips, belts tensioners |

### 18.4 Composites and wood

| Material | ρ | E (GPa) | Strength (MPa) | CTE | Cost | Notes |
|---|---|---|---|---|---|---|
| CFRP unidirectional (T300/epoxy, 0°) | 1 550–1 600 | 130–140 (0°), ~9 (90°) | 1 500–2 000 (0° tension), ~1 200 comp., ~50 (90°) | ~0 (0°), ~30 (90°) | $$$$ | Extremely anisotropic |
| CFRP pultruded rod/tube (axial) | 1 500–1 600 | 100–135 | 1 000–2 000 tension | ~0–1 | $$$ | Cheap stiff arm links; brittle at clamps |
| CFRP roll-wrapped tube (0/±45) | 1 500–1 600 | 60–100 axial | 500–900 | 0–3 | $$$ | Better torsion than pultruded |
| CFRP quasi-isotropic plate | 1 550–1 600 | 45–55 | 500–700 | 2–4 | $$$$ | Waterjet/CNC plates |
| GFRP / FR4 (woven glass/epoxy) | 1 850 | 18–24 in-plane | ~300 tension | 14–17 in-plane | $$ | PCBs, insulating plates |
| Spruce/pine (along grain) | 400–550 | 9–12 | ~70–100 tension, ~35–45 compression | 3–5 | $ | Very anisotropic; across grain ~1/20 strength |
| Oak/beech hardwood (along grain) | 650–750 | 11–14 | ~90–120 tension, ~45–55 comp. | 3–5 | $ | Moisture swells across grain |
| Birch plywood (Baltic) | 650–700 | ~8–12 (face direction, layup-dependent) | ~40–60 bending | ~5–7 | $ | Laser cut frames |
| MDF | 700–800 | 2.5–4 | ~20–35 bending | ~10 | $ | Cheap, low strength, moisture sensitive |

CFRP notes: design for brittle behaviour (no yield; use n ≥ 2–3 on ultimate), avoid bearing loads
on thin laminates (use bonded/potted metal inserts), galvanic corrosion against aluminium (isolate
with glass ply or coating), crush under clamping (sleeves), and strength values above are coupon
values — real joints govern.

Wood notes: properties at ~12 % moisture; derate for long-term load (duration-of-load factor ~0.6 in
timber codes — *estimate*) and wet conditions.

---

## 19. Ashby-style materials selection

Method (Ashby, *Materials Selection in Mechanical Design*):
1. **Function** (tie, beam, shaft, column, panel, spring).
2. **Objective** (minimise mass, cost, deflection...).
3. **Constraints** (stiffness, strength, geometry fixed vs free).
4. **Free variable** (usually a section dimension).
5. Write objective, substitute constraint to eliminate the free variable → **material index M**;
   maximise M.

Derivation sketch (light stiff beam, square section side a free): stiffness S = C E I / L³,
I = a⁴/12 → a² = √(12 S L³/(C E)); mass m = ρ a² L ∝ ρ/E^(1/2) → maximise **E^(1/2)/ρ**.

### 19.1 Index table

| Component & mode | Constraint | Free variable | Maximise |
|---|---|---|---|
| Tie (tension rod) | stiffness | area | E/ρ |
| Tie | strength | area | σ_f/ρ |
| Beam in bending (shape fixed, scaled) | stiffness | section size | **E^(1/2)/ρ** |
| Beam in bending | strength | section size | σ_f^(2/3)/ρ |
| Panel/plate in bending (width fixed) | stiffness | thickness | **E^(1/3)/ρ** |
| Panel in bending | strength | thickness | σ_f^(1/2)/ρ |
| Column (buckling) | buckling load | section size | E^(1/2)/ρ |
| Shaft in torsion | stiffness | diameter | G^(1/2)/ρ |
| Spring, max stored energy per volume | no failure | — | σ_f²/E |
| Spring, per mass | — | — | σ_f²/(E ρ) |
| Flexure hinge (max elastic bend) | no failure | — | σ_f/E |
| Precision frame, min thermal distortion | heat flux | — | λ/α (conductivity / CTE) |
| Cheapest stiff beam | stiffness | section size | E^(1/2)/(C_m ρ) (C_m = cost/kg) |

Key insight: the larger the exponent penalty (beam, panel), the more **low-density** materials win.
For ties, steel ≈ aluminium ≈ titanium (all ~25 GPa per Mg/m³). For beams and panels, aluminium,
wood, and CFRP beat steel. For flexures/springs, polymers and titanium/spring steel shine.

### 19.2 Computed indices (from Section 18 typical values)

Units: E in GPa, ρ in Mg/m³ (= g/cm³), σ_y in MPa. Higher is better. Last column is yield strain
σ_y/E in % (flexure/snap-fit capacity). Computed here, values *estimate* (depend on chosen grade).

| Material | E/ρ (tie) | E^½/ρ (beam) | E^⅓/ρ (panel) | σ_y/ρ | σ_y^⅔/ρ | σ_y/E % |
|---|---|---|---|---|---|---|
| Steel 1018 | 26.0 | 1.82 | 0.75 | 47 | 6.5 | 0.18 |
| Stainless 304 | 24.1 | 1.74 | 0.72 | 27 | 4.5 | 0.11 |
| Al 6061-T6 | 25.6 | 3.08 | 1.52 | 102 | 15.7 | 0.40 |
| Al 7075-T6 | 25.6 | 3.02 | 1.48 | 179 | 22.5 | 0.70 |
| Brass C360 | 11.4 | 1.16 | 0.54 | 36 | 5.4 | 0.32 |
| Ti-6Al-4V | 25.7 | 2.41 | 1.09 | 199 | 20.7 | 0.77 |
| POM | 2.1 | 1.22 | 1.02 | 49 | 12.0 | 2.3 |
| PA6 (cond.) | 1.2 | 1.05 | 0.99 | 40 | 11.2 | 3.2 |
| PLA (FDM, XY) | 2.4 | 1.40 | 1.16 | 40 | 10.9 | 1.7 |
| PETG (FDM) | 1.4 | 1.06 | 0.96 | 37 | 10.3 | 2.6 |
| ABS (FDM) | 2.0 | 1.39 | 1.23 | 37 | 10.9 | 1.8 |
| CFRP quasi-iso | 31.6 | 4.48 | 2.33 | 348* | 42.5* | 1.1* |
| CFRP UD / pultruded tube (axial) | 77.4 | 7.07 | 3.18 | 774* | 72.9* | 1.0* |
| Spruce (along grain) | 22.2 | 7.03 | 4.79 | 133* | 34.1* | 0.6* |

*Composites and wood: strength = ultimate (no yield), along fibre/grain only.

Reading the table:
- Steel vs aluminium tie: equal. Steel vs aluminium beam of the same shape scaled for equal stiffness:
  aluminium is ~40 % lighter (3.08 vs 1.82). Panel: aluminium ~half the mass of steel.
- Printed plastics: for the same *mass*, a printed beam is ~half as stiff as aluminium; for the same
  *size*, it's ~25–35× less stiff (E ratio). Printed arms therefore need big, deep, hollow sections.
- CFRP tubes are the stiffness-per-mass champion for arm links (and wood is surprisingly close for
  beams, but anisotropic and moisture-sensitive).
- Flexures and snap-fits: polymers (2–3 % elastic strain) vastly outperform metals (0.1–0.8 %).

### 19.3 Decision table: "use X when..."

| Need | First choice | Alternatives / notes |
|---|---|---|
| Machined structural brackets, plates, arm links (general) | Al 6061-T6 | 7075-T6 if strength-limited; 5052 for bent sheet |
| Stiffest light arm link / boom | CFRP tube (pultruded or roll-wrapped) with bonded Al end fittings | Al tube; deep printed section if prototyping |
| Shafts (motor, pulley, joint) | 1045 / 4140 steel, or hardened linear rod | Stainless 303/416 for corrosion; aluminium shafts only if lightly loaded and keyless |
| Linear bearing rails/rods | Induction-hardened steel rod (≥ 58 HRC) | Hard-anodised Al only with polymer bearings |
| Bushings / plain bearings | Bronze (oil-impregnated sintered), POM, PTFE-lined (DU), iglidur-type polymers | Check PV limit (see bearings knowledge file) |
| Gears, low-load quiet | POM | PA66 (tougher, moisture); steel for high torque |
| Corrosive/wet environment | 316 stainless, POM, PP, HDPE, anodised 6061 | Avoid plain steel, 7075, CFRP–Al contact |
| Threaded inserts in plastic | Brass heat-set inserts | Never rely on self-tapped PLA threads for repeated assembly |
| Fast prototype structure, room temp, low load | PLA | Expect creep, brittleness; not near motors |
| Printed functional part, moderate temp/impact | PETG or ASA | PC or CF-nylon for higher stiffness/heat |
| Printed part near steppers/hotends/sun (>50 °C) | ASA, ABS, PC, CF-PA | Not PLA |
| Living hinge / snap fit | PP (moulded), PA, PETG (printed, along filament) | Not PLA |
| High strength-to-weight, cost no object | Ti-6Al-4V, 7075-T6, CFRP | |
| Vibration damping, heavy machine base | Cast iron, epoxy granite | |
| Electrical insulation + stiffness | FR4/G10 | |
| Low thermal expansion precision | Invar, CFRP, granite | Steel over aluminium for ambient-change stability |

---

## 20. Worked end-to-end mini-example (robot arm link)

Problem: horizontal arm link, 250 mm long, carries 0.5 kg payload + 0.2 kg wrist motor at the tip
(≈ 6.9 N), accelerations add 1.5× → design load 10.3 N. Target tip deflection ≤ 0.2 mm (link only).
Choose between FDM PETG and 6061 tube.

1. Required EI: δ = PL³/(3EI) → EI ≥ 10.3·250³/(3·0.2) = 2.68×10⁸ N·mm².
2. 6061 (E = 69 000): I ≥ 3 890 mm⁴ → 20×20×1.5 tube (I = (20⁴ − 17⁴)/12 = 6 373 mm⁴) OK
   (δ ≈ 0.12 mm). Stress: M = 2 575 N·mm, Z = 637 mm³ → σ = 4 MPa, n ≫ 10.
3. PETG (E ≈ 1 800, printed): I ≥ 149 000 mm⁴ → solid 40×40 square gives 213 000 mm⁴ — a big,
   heavy part; a 50×50 hollow section with 4 mm walls: I = (50⁴ − 42⁴)/12 = 261 500 mm⁴ OK.
   Stress ≈ 2 575/(10 460) ≈ 0.25 MPa — strength trivial, but check creep (the load is sustained):
   with E_c ≈ 0.5E after long hold, δ doubles → oversize by 2× or accept.
4. Conclusion: stiffness drives; aluminium (or CFRP) tube is far more compact. Printed link is viable
   only with large hollow section and acceptance of creep sag. Joint/bearing compliance is often larger
   than link compliance — check it too.

---

## 21. Formula cheat-sheet (copy-ready)

    Axial:    σ = F/A;  δ = FL/(AE);  k = AE/L
    Bending:  σ = Mc/I = M/Z;  1/ρ = M/(EI)
    Torsion:  τ = Tr/J;  θ = TL/(GJ);  τ_solid = 16T/(πd³);  T = P/ω
    Shear:    τ_avg = V/A;  τ_max,rect = 1.5V/A;  τ_max,circ = 4V/(3A)
    Rect:     I = bh³/12;  Z = bh²/6
    Circle:   I = πd⁴/64;  J = πd⁴/32;  Z = πd³/32;  r = d/4
    Cantilever tip P: δ = PL³/(3EI);  SS centre P: δ = PL³/(48EI);  SS UDL: δ = 5wL⁴/(384EI)
    Principal: σ₁,₂ = (σx+σy)/2 ± √(((σx−σy)/2)² + τ²)
    von Mises: σ' = √(σx² − σxσy + σy² + 3τ²);  shaft: √(σ² + 3τ²);  Ssy = 0.577 Sy
    Tresca shaft: √(σ² + 4τ²)
    Euler:    P_cr = π²EI/(KL)²;  Johnson: σ_cr = Sy − (Sy KL/(2π r))²/E;  (KL/r)_t = √(2π²E/Sy)
    Fatigue:  Se = ka kb kc kd ke Se';  Se' = 0.5 Sut (steel ≤ 1400);  Goodman σa/Se + σm/Sut = 1/n
    Kf = 1 + q(Kt − 1)
    Fracture: K = Yσ√(πa);  a_c = (1/π)(K_IC/(Yσ))²
    Thermal:  δ = αLΔT;  σ = EαΔT (constrained)
    Hertz sphere: a = (3FR/(4E*))^(1/3);  p₀ = 3F/(2πa²)
    Hertz cylinder: b = √(4FR/(πLE*));  p₀ = 2F/(πbL)
    1/E* = (1−ν₁²)/E₁ + (1−ν₂²)/E₂;  1/R = 1/R₁ + 1/R₂

---

## Canonical references

Free:
- MIT OpenCourseWare 2.001 Mechanics & Materials I / 3.032 Mechanical Behavior of Materials —
  https://ocw.mit.edu (free lecture notes, problem sets).
- Roylance, *Mechanics of Materials* (MIT) — free on LibreTexts:
  https://eng.libretexts.org/Bookshelves/Mechanical_Engineering/Mechanics_of_Materials_(Roylance)
  (includes material property appendix).
- DoITPoMS (Cambridge) teaching library — Ashby maps, fracture, creep:
  https://www.doitpoms.ac.uk/tlplib/optimisation-biomaterials/modulus_density.php
- NPTEL course on materials selection (IIT): https://archive.nptel.ac.in/content/storage2/courses/112104122/
- Iowa State ME 325 fatigue lecture notes (Marin factors summary):
  https://www.engineering.iastate.edu/~gkstarns/me325/fatigue_2.pdf
- MechaniCalc reference pages (buckling, beams, fatigue, stress concentration):
  https://mechanicalc.com/reference/column-buckling
- AmesWeb column buckling & K factors: https://amesweb.info/Beam/Column-Buckling-Formulas.aspx
- Wikipedia: Fracture toughness (property table), Johnson's parabolic formula:
  https://en.wikipedia.org/wiki/Fracture_toughness, https://en.wikipedia.org/wiki/Johnson%27s_parabolic_formula
- NASA SP-8007 Buckling of thin-walled circular cylinders (public domain): https://ntrs.nasa.gov
- MatWeb (free tier) material datasheets: https://www.matweb.com
- MakeItFrom material comparisons: https://www.makeitfrom.com/compare/6061-T6-Aluminum/7075-T6-Aluminum
- CAMPUS plastics database (free, supplier creep/isochronous data): https://www.campusplastics.com
- Prusament technical data sheets (PLA, PETG, ASA, PC Blend): https://www.prusa3d.com/ (TDS per material;
  PLA TDS mirror https://www.matterhackers.com/r/xFvGl8; PETG TDS mirror
  https://www.3dprintergear.com.au/assets/files/technical-data-sheet%20(1).pdf)
- Delrin 150 technical data sheet (Trident mirror): https://plastics.tridentplastics.com/Asset/TDS_Delrin150%20NC010.pdf;
  HPC Europe Delrin sheet: https://www.hpceurope.com/docFichesTechniques/DelrinPlastic.pdf
- Interplas Insights on polymer creep: https://interplasinsights.com/blogs/materials-blog/creepy-things-can-happen-with-long-term-loading-of-thermopla/
- Madison Group, POM creep-rupture case study (ANTEC 2021):
  https://madisongroup.com/wp-content/uploads/2023/01/Jansen_ANTEC_-2021_creep.pdf

Books (paid):
- Budynas & Nisbett, *Shigley's Mechanical Engineering Design* — fatigue/Marin/Goodman, shafts.
- Juvinall & Marshek, *Fundamentals of Machine Component Design* — safety factor guidance.
- Pilkey & Pilkey, *Peterson's Stress Concentration Factors* — Kt charts (authoritative).
- Young, Budynas & Sadegh, *Roark's Formulas for Stress and Strain* — beams, plates, shells, contact.
- Ashby, *Materials Selection in Mechanical Design* — indices, selection charts (Granta/Ansys EduPack).
- Gere & Goodno, *Mechanics of Materials*; Hibbeler, *Mechanics of Materials* — fundamentals.
- Johnson, *Contact Mechanics* — Hertz theory.
- Dowling, *Mechanical Behavior of Materials* — fatigue, fracture, creep.
- DuPont/Celanese/BASF/Covestro plastics design guides (free PDFs from suppliers) — creep, snap-fits.
- MMPDS (Metallic Materials Properties Development and Standardization) — design-allowable metals data.

Standards:
- ASTM E8 (tension testing metals), E399 (K_IC), E466 (fatigue), D638 / ISO 527 (plastics tension),
  D2990 (plastics creep).
- ISO 898-1 (fastener strength, stress areas), ISO 76 (bearing static load ratings),
  AISC 360 (column K factors), ASME BPVC VIII, ASME B30 (lifting).

---

## Gaps / not verified

- Polymer fatigue strengths (POM, nylon, FDM materials) are estimates from general experience/design
  guides; they vary strongly with frequency (self-heating), temperature, moisture and print settings.
  Not cross-checked against two primary sources.
- Creep fractions (E_c ≈ 40–70 % of E at 1 000 h; sustained-stress limits 15–30 % of yield) are rules of
  thumb, not verified against specific isochronous curves. Use CAMPUS or supplier data for real designs.
- FDM Z-direction strength ratio (30–70 %) is a broad estimate; published studies range widely.
- PA6 conditioned modulus/strength values are typical-datasheet ranges, not cross-checked in this
  research pass (searches did not return a primary dry-vs-conditioned table).
- Kt values are approximate readings of Peterson-type charts (from memory/secondary sources); use
  Peterson's or an FEA for final design of highly stressed fatigue features.
- 4140 pre-hard, linear-rod and 52100 properties are given as ranges; exact values depend on heat
  treatment and supplier.
- CFRP and wood properties are coupon-level typical values; joints and manufacturing defects usually
  govern real components.
- Yield-onset contact pressure p₀ ≈ 1.6 Sy (point contact) is the classical von Mises result for
  ν ≈ 0.3; allowable p₀ for rolling life is an estimate — use bearing/rail vendor ratings.
- Cost tiers are qualitative and market-dependent.
- Safety-factor table is synthesised guidance, not a code; regulated applications (lifting, pressure,
  medical, aerospace) must follow their governing standards.
- Some Marin coefficient sets differ slightly between Shigley editions (the values here match the 8th–10th
  edition SI table as reproduced in Iowa State course notes).
