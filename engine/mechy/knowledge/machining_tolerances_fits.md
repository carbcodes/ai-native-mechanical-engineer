# Machining, Tolerances and Fits: practical shop knowledge

Reference for Mechy agents (cad, concept, docs, sim). Read it before you size a hole, a shaft
seat, a bearing pocket, a fastener or a tolerance note. Units are SI (mm, µm, N, m/min) unless a
section is explicitly about inch hardware.

**How the numbers are labelled**
- **[std]**: comes from a standard (ISO 286, ISO 273, ISO 2768, ISO 4762, DIN 974) via a public
  summary. Cross-checked against at least two sources unless marked otherwise.
- **[typ]**: typical shop practice, quoted from handbooks, catalogues or vendor guides. It is a
  starting value, not a guarantee.
- **[est]**: an engineering estimate or rule of thumb. Verify it before it drives a decision.
- **[derived]**: computed in this file from the standard values. The method is shown.

---

## 0. TL;DR: the 25 things to remember

1. **Default general tolerance for machined parts is ISO 2768-mK.** That means ±0.1 to ±0.3 mm
   on most small dimensions. Only tighten the features that mate. [std]
2. **Hole-basis system.** Make the hole H (lower deviation 0) and change the shaft letter to get
   the fit. Reamers and pin gauges come in H7. [std]
3. **The fit ladder** (loose to tight): H11/c11, H9/d9, H8/f7, H7/g6, H7/h6, H7/k6, H7/n6,
   H7/p6, H7/s6, H7/u6. [std]
4. **At 8 mm**, H7 is +0/+15 µm and g6 is −5/−14 µm, which gives 5 to 29 µm of clearance. At
   20 mm, H7/g6 gives 7 to 41 µm of clearance. [derived, std]
5. **Bearings: the ring that rotates relative to the load gets the interference fit.** The
   other ring gets a clearance or transition fit. [typ, SKF/ABMA]
6. **Small ball bearing with a rotating shaft and normal load:** shaft j5/k5 (≤18 mm), housing
   H7. For axial float, use housing G7/H7. [typ, SKF]
7. **Metric coarse tap drill ≈ D − P.** M2 1.6, M2.5 2.05, M3 2.5, M4 3.3, M5 4.2, M6 5.0,
   M8 6.8, M10 8.5, M12 10.2 mm. [std, 3 sources agree]
8. **Form (roll) tap drill ≈ D − 0.5·P.** M3 2.8, M4 3.7, M5 4.6, M6 5.5 mm. [typ]
9. **Normal clearance holes (ISO 273 medium):** M2 2.4, M2.5 2.9, M3 3.4, M4 4.5, M5 5.5,
   M6 6.6, M8 9, M10 11, M12 13.5 mm. [std]
10. **Thread engagement:** about 1×D in steel, 1.5×D in cast iron, brass or aluminium, 2×D in
    soft aluminium or for repeated assembly, and 2–2.5×D in plastic. Beyond about 1.5×D in
    steel you gain almost nothing. [typ]
11. **Counterbores for ISO 4762 socket head cap screws (DIN 974):** M3 ⌀6.5×3.3, M4 ⌀8×4.4,
    M5 ⌀10×5.4, M6 ⌀11×6.4, M8 ⌀15×8.6 mm. [std/typ]
12. **Typical Ra:** turned or milled 1.6–3.2 µm, ground 0.2–0.8 µm, reamed 0.8–1.6 µm, FDM
    side walls 6–25 µm. [typ]
13. **Achievable IT grades:** grinding IT5–6, reaming IT7, fine turning IT6–7, milling
    IT8–9, drilling IT10–11. FDM is roughly IT12–14. [typ]
14. **GD&T: datums first (3-2-1), then position for holes** (cylindrical zone ⌀). Under MMC
    you get bonus tolerance as the hole grows. [std ASME Y14.5 / ISO 1101]
15. **Floating fastener:** position tolerance T = H − F on each part. **Fixed fastener**
    (tapped part): T_total = H − F, split between the two parts. [std]
16. **Converting ±x/±y to diametral position:** ⌀ = 2·√(x² + y²). A square ±0.1 zone becomes
    roughly ⌀0.28. [std]
17. **Stack-up:** worst case = Σ tᵢ. RSS = √(Σ tᵢ²). Use worst case for fewer than about 4
    parts or safety-critical stacks, and RSS for 5+ independent, centred processes. [typ]
18. **Projection:** ISO first-angle (Europe/Asia) vs third-angle (US). Always show the symbol.
    [std]
19. **Speeds:** n [rpm] = 1000·Vc / (π·D). Feed vf [mm/min] = fz · z · n. [std formula]
20. **Break all sharp edges 0.2–0.5 mm** unless specified otherwise. Add a 15–30° lead-in
    chamfer on press-fit shafts and pins. [typ]
21. **Internal pocket corners always have a radius** of at least the cutter radius; use ×1.1–1.3
    for a clean finish. [typ]
22. **FDM holes come out 0.1–0.3 mm undersize.** Sliding fit needs about 0.2–0.3 mm diametral
    clearance in PLA/PETG; snug fit 0.1–0.15 mm. Print a test coupon. [typ, vendor guides]
23. **Printed bearing seats:** design near nominal OD (608 → ⌀22.0–22.15 mm) and tune with a
    test ladder. Plastic creeps, so retain bearings mechanically and don't rely on interference
    alone. [typ/est]
24. **Heat-set inserts:** use the hole size on the insert's datasheet, not the screw size. A
    standard M3 insert is about ⌀4.0 mm (3.9–4.2 mm), ≥1 mm deeper than the insert, with ≥1.6 mm
    of wall. [typ, CNC Kitchen/DigiKey]
25. **Never put a tolerance tighter than the process can hold** without naming the process
    (ream, grind) on the drawing. Every tight tolerance costs money. [typ]

---

## 1. ISO 286 limits and fits

### 1.1 Vocabulary

| Term | Meaning |
|---|---|
| Nominal (basic) size | The design size, e.g. ⌀8 |
| Deviation | Actual or limit size minus nominal. ES/EI apply to holes (upper/lower), es/ei to shafts |
| Fundamental deviation | The deviation nearest to zero. The **letter** sets where the band sits |
| IT grade (tolerance grade) | The **width** of the band. The **number**: IT01 … IT18 |
| Tolerance class | Letter + number, e.g. H7 (hole) or g6 (shaft). Capitals are holes, lower case shafts |
| Clearance fit | Hole is always larger than the shaft (min clearance ≥ 0) |
| Transition fit | Either clearance or interference is possible, depending on the actual parts |
| Interference fit | Shaft is always larger than the hole (needs a press or thermal fit) |
| Hole-basis system | All holes are H (EI = 0) and the shaft letter varies. **Default; use this.** |
| Shaft-basis system | All shafts are h (es = 0) and the hole letter varies. Used with ground bar or linear rods bought in h6/h7, and with bearing outer rings |

**Letter position.**
- Shafts: a–g sit below zero (clearance), h is at zero, js is symmetric, and k–zc sit above
  zero (transition, then interference).
- Holes are the mirror image: A–G are above zero (oversize), H is at zero, and K–ZC are below
  zero.
- Bearing rings behave like "h" parts. The bore and the OD both have a negative-only tolerance.
- [std; Roymech, cadforum.cz summaries of ISO 286]

**IT grade formula (for sizes ≤ 500 mm).**
- Standard tolerance unit: i [µm] = 0.45·∛D + 0.001·D, where D is the geometric mean of the size
  band in mm.
- IT5 ≈ 7i, IT6 = 10i, IT7 = 16i, IT8 = 25i, IT9 = 40i, IT10 = 64i, IT11 = 100i, IT12 = 160i.
- Each grade is about 1.6× the previous one (the R5 series).
- [std, ISO 286-1; formula also quoted by Firgelli's ISO 286 calculator page]

### 1.2 IT grade values (µm) [std, ISO 286-1; cross-checked with engineersedge and cadforum]

| Size band (mm) | IT5 | IT6 | IT7 | IT8 | IT9 | IT10 | IT11 | IT12 |
|---|---|---|---|---|---|---|---|---|
| >0–3 | 4 | 6 | 10 | 14 | 25 | 40 | 60 | 100 |
| >3–6 | 5 | 8 | 12 | 18 | 30 | 48 | 75 | 120 |
| >6–10 | 6 | 9 | 15 | 22 | 36 | 58 | 90 | 150 |
| >10–18 | 8 | 11 | 18 | 27 | 43 | 70 | 110 | 180 |
| >18–30 | 9 | 13 | 21 | 33 | 52 | 84 | 130 | 210 |
| >30–50 | 11 | 16 | 25 | 39 | 62 | 100 | 160 | 250 |
| >50–80 | 13 | 19 | 30 | 46 | 74 | 120 | 190 | 300 |
| >80–120 | 15 | 22 | 35 | 54 | 87 | 140 | 220 | 350 |

**What each grade is used for** [typ]:
- IT5–IT6: bearing seats, precision spindles.
- IT7: reamed holes and general precision fits. **This is the workhorse.**
- IT8–IT9: running fits, ordinary machining.
- IT11+: free fits, rough machining.
- IT12–IT14: punching, casting, moulding, FDM.

### 1.3 Shaft fundamental deviations (µm) for the common letters [std, ISO 286-2; verify against a table]

These are the deviations nearest to zero. For a–h, the value is es (upper deviation) and
ei = es − IT. For k–u, the value is ei (lower deviation) and es = ei + IT.

| Size (mm) | c (es) | d (es) | f (es) | g (es) | h | k (ei, IT4–7) | m (ei) | n (ei) | p (ei) | s (ei) | u (ei) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| >0–3 | −60 | −20 | −6 | −2 | 0 | 0 | +2 | +4 | +6 | +14 | +18 |
| >3–6 | −70 | −30 | −10 | −4 | 0 | +1 | +4 | +8 | +12 | +19 | +23 |
| >6–10 | −80 | −40 | −13 | −5 | 0 | +1 | +6 | +10 | +15 | +23 | +28 |
| >10–18 | −95 | −50 | −16 | −6 | 0 | +1 | +7 | +12 | +18 | +28 | +33 |
| >18–30 | −110 | −65 | −20 | −7 | 0 | +2 | +8 | +15 | +22 | +35 | +41 (>24) |
| >30–50 | −120 | −80 | −25 | −9 | 0 | +2 | +9 | +17 | +26 | +43 | +60 (>40) |

**Notes.**
- js is symmetric: ±IT/2.
- **j** is not symmetric. j5 and j6 values for common sizes:

  | Size (mm) | j5 | j6 |
  |---|---|---|
  | 6–10 | +4/−2 | +7/−2 |
  | 10–18 | +5/−3 | +8/−3 |
  | 18–30 | +5/−4 | +9/−4 |

- [std] The u deviation splits inside the 18–30 mm band (at 24 mm) and inside 30–50 mm (at
  40 mm). Look u up in a full table; it is not verified here.

**Hole deviations.**
- For the **H** hole, EI = 0 and ES = +IT.
- For K, M, N and P holes, the hole value is not a simple mirror of the shaft value (ISO adds a
  Δ correction for grades ≤ 8). Use these looked-up values for the 18–30 mm band, which is
  common for bearing ODs such as 608 = ⌀22 or 6001 = ⌀28:

| Hole class (18–30 mm) | Upper (µm) | Lower (µm) |
|---|---|---|
| G7 | +28 | +7 |
| H7 | +21 | 0 |
| H8 | +33 | 0 |
| J7 | +12 | −9 |
| K7 | +6 | −15 |
| M7 | 0 | −21 |
| N7 | −7 | −28 |
| P7 | −14 | −35 |

[std, ISO 286-2 values as published in SKF and Roymech tables; check them before you release a
drawing]

### 1.4 ISO preferred fits: what to use when [std ISO 286 / ANSI B4.2 preferred-fit list; selection guidance typ]

| Fit (hole basis) | Type | Character | Use it for | Assembly |
|---|---|---|---|---|
| H11/c11 | Clearance | Loose running | Agricultural or dirty pivots, cast parts, big thermal expansion | By hand, sloppy |
| H9/d9 | Clearance | Free running | Large temperature swings, high speed, plain bearings with heavy journal pressure, idler pins | By hand |
| H8/f7 | Clearance | Close running | Accurate running fits at moderate speed: plain bushings, gear-on-shaft that must rotate, sliding rods | By hand, no play felt |
| H7/g6 | Clearance | Sliding | Parts that must slide or turn accurately with almost no play: locating pins, spigots, pistons, sliding gears, linear guides in plain bushings | By hand, lubricated |
| H7/h6 | Clearance (zero min) | Locational clearance | Snug location of parts that are disassembled: spigot location, removable pulleys with keys, gear hubs with set screws | By hand or light tap |
| H7/k6 | Transition | Locational transition | Accurate location with slight interference possible: pulleys and gears with keys, couplings, bearing inner rings (normal load) | Rubber or plastic mallet |
| H7/n6 | Transition (mostly interference) | Locational transition, tight | More accurate location where larger interference is OK: bushes into housings, gear hubs that must not move | Light press |
| H7/p6 | Interference (light) | Locational interference | Rigid location without big stress; **standard press fit for steel bushings and dowels in steel or cast iron**. Not for torque transmission alone | Press |
| H7/s6 | Interference | Medium drive | Permanent press fits in steel, shrink fits in cast iron; transmits moderate torque by friction | Press or heat the hub |
| H7/u6 | Interference | Force fit | Heavily loaded permanent joints, shrink fits | Shrink (heat or cool) |

**Rules of thumb for picking a fit** [typ]:
- **Does it need to move?** Rotate → f7 or g6 on the shaft. Slide axially but no rotation
  play → g6 or h6. Located but removable → h6 or k6. Never moves → n6, p6 or s6.
- **Who carries the torque?** If a key, spline, pin or set screw carries torque, use a
  transition fit (k6). If friction alone carries torque, use s6 or u6, and check it with the
  press-fit formula (§1.7).
- **Is the hub soft?** Aluminium and plastic hubs need **less** interference than steel to
  avoid yield, but they also lose grip when hot. Aluminium expands about 2× as much as steel
  (23 vs 12 µm/m·K). A steel shaft in an aluminium bore loosens by about 0.011 µm per mm of
  diameter per K. [typ, CTE values]
- **Does it see thermal change?** Size the fit at the operating temperature. A 20 mm steel
  shaft in an aluminium hub that heats by 50 K: Δ ≈ 20 × (23 − 12)·10⁻⁶ × 50 ≈ 11 µm looser.
  That is enough to turn an H7/k6 into a clearance fit. [derived]

### 1.5 Worked fit numbers [derived from §1.2–1.3; spot-checked against ANSI B4.2 preferred-fit tables at 20 mm]

Signs: a positive value is clearance and a negative value is interference, in µm.

| Fit | ⌀8 hole | ⌀8 shaft | ⌀8 fit range | ⌀20 hole | ⌀20 shaft | ⌀20 fit range |
|---|---|---|---|---|---|---|
| H11/c11 | 0/+90 | −80/−170 | +80 … +260 | 0/+130 | −110/−240 | +110 … +370 |
| H9/d9 | 0/+36 | −40/−76 | +40 … +112 | 0/+52 | −65/−117 | +65 … +169 |
| H8/f7 | 0/+22 | −13/−28 | +13 … +50 | 0/+33 | −20/−41 | +20 … +74 |
| H7/g6 | 0/+15 | −5/−14 | +5 … +29 | 0/+21 | −7/−20 | +7 … +41 |
| H7/h6 | 0/+15 | 0/−9 | 0 … +24 | 0/+21 | 0/−13 | 0 … +34 |
| H7/k6 | 0/+15 | +1/+10 | +14 … −10 | 0/+21 | +2/+15 | +19 … −15 |
| H7/n6 | 0/+15 | +10/+19 | +5 … −19 | 0/+21 | +15/+28 | +6 … −28 |
| H7/p6 | 0/+15 | +15/+24 | 0 … −24 | 0/+21 | +22/+35 | −1 … −35 |
| H7/s6 | 0/+15 | +23/+32 | −8 … −32 | 0/+21 | +35/+48 | −14 … −48 |

Read it like this: "⌀20 H7/g6 has 7 µm minimum and 41 µm maximum clearance." The ANSI B4.2
preferred-fit table gives 0.041/0.007 for this fit, which matches.

**How to compute a fit (method).**
1. Max clearance = ES(hole) − ei(shaft).
2. Min clearance = EI(hole) − es(shaft). A negative result means interference.

**Drawing callout.**
- On a part: `⌀8 H7` (on the hole) or `⌀8 g6` (on the shaft).
- On an assembly: `⌀8 H7/g6`.
- Add the limits in brackets for the shop if you like: `⌀8 H7 (8.000/8.015)`.

### 1.6 When NOT to use ISO fits [typ]
- **3D-printed parts.** The process is IT12–IT14, and a µm-level class is meaningless. Use the
  printed-part clearances in §14.
- **Sheet metal and laser-cut holes.** These are ±0.1–0.2 mm. Write plain ± tolerances.
- **Purchased precision parts.** Bearings, dowel pins (m6), linear rods (h6/g6) and stepper
  shafts already have their own classes, so design the mating part around them.
  - NEMA17 shaft: ⌀5 mm, typically 0/−0.012 mm. [typ, datasheets vary]
  - Hardened linear rod: usually h6 or g6. [typ, Misumi/HIWIN]
  - ISO 8734 hardened dowel: m6. [std]

### 1.7 Interference (press) fit check: closed form [Shigley ch. 3/7 thick-wall cylinder; principle summarised]

**Contact pressure** for a solid shaft in a hub of outer diameter D_o:

p = δ / [ d·( (1/E_h)·((D_o² + d²)/(D_o² − d²) + ν_h) + (1/E_s)·(1 − ν_s) ) ]

where:
- δ = **diametral** interference [mm]
- d = nominal interface diameter [mm]
- E = Young's modulus [MPa]
- ν = Poisson's ratio
- subscript h = hub, s = shaft

**Hub stress and transmitted torque.**
- Hub hoop stress at the bore: σ_t = p·(D_o² + d²)/(D_o² − d²). Keep it below about 0.7×yield.
- Transmissible torque: T ≈ µ · p · π · d² · L / 2 [N·mm].
  - µ ≈ 0.1–0.15 for steel on steel, lubricated or press-assembled.
  - µ ≈ 0.15–0.25 for dry or shrink-fit joints.
  - L = engaged length.
- Press force: F ≈ µ · p · π · d · L.
- [typ µ values, Shigley / Roymech]

**Mini example.**
- Steel shaft and steel hub (E = 207 GPa, ν = 0.3), d = 20 mm, D_o = 40 mm, L = 20 mm.
- Mean H7/s6 interference ≈ 31 µm (0.031 mm).
- Steps:
  1. (D_o² + d²)/(D_o² − d²) = 2000/1200 = 1.667.
  2. Denominator = 20 × [(1.667 + 0.3) + (1 − 0.3)] / 207000 = 20 × 2.667 / 207000
     = 2.577·10⁻⁴ mm/MPa.
  3. p ≈ 0.031 / 2.577·10⁻⁴ ≈ 120 MPa.
  4. Hoop stress σ_t ≈ 200 MPa. That is fine for steel and would yield 6061-T6 (yield
     ≈ 275 MPa) with a thin wall.
  5. Torque T ≈ 0.12 × 120 × π × 400 × 20 / 2 ≈ 181 N·m.
- [derived; magnitude agrees with Shigley's worked examples. Estimate.]

---

## 2. Bearing seats: shaft and housing fits

### 2.1 The one rule
**The ring that rotates relative to the load direction must have an interference fit.** Under
"circumferential load" it will otherwise creep (fret) around its seat. The ring with a
stationary load can be a clearance or transition fit and may float axially.
[typ, SKF Rolling Bearings catalogue "Selecting fits"; ABMA 7]

| Situation | Inner ring | Outer ring | Example |
|---|---|---|---|
| Rotating shaft, fixed load direction (most robot joints, pulleys) | Interference (j5/k5/k6/m6) | Clearance or transition (H7, J7) | Motor shaft, belt idler on a rotating axle |
| Stationary shaft, rotating housing, load fixed relative to the shaft | Clearance (g6/h6) | Interference (N7/P7) | Wheel hub on a fixed axle, idler pulley with bearings in the pulley |
| Unbalanced or indeterminate load | Interference | Interference | Vibrating screens |
| Light-load precision miniature (608, 6xx in a printed arm) | Light transition (h5/j5; or h6 + retaining compound) | H7 or printed snug | Typical Mechy case |

### 2.2 Bearing ring tolerances (Normal class, P0 / ABEC-1) [std ISO 492; SKF table]

| Feature | 2.5–10 mm | >10–18 mm | >18–30 mm | >30–50 mm |
|---|---|---|---|---|
| Bore deviation Δdmp | 0 / −8 µm | 0 / −8 µm | 0 / −10 µm | 0 / −12 µm |
| OD deviation ΔDmp | 0 / −8 µm (6–18) | 0 / −8 µm | 0 / −9 µm | 0 / −11 µm |

**Consequence.** The bore sits **below** nominal. A k5 or k6 shaft therefore gives more
interference than the same shaft in an H7 hole would.

### 2.3 Typical recommended shaft classes, ball bearings, solid steel shaft [typ, SKF catalogue guidance; ABMA 7; cross-checked with NHBB fits page]

| Load (P = equivalent load, C = dynamic rating) | Shaft ⌀ ≤ 18 mm | 18–100 mm |
|---|---|---|
| Light (P ≤ 0.05 C) | js5 / h5 | j6 / k6 (ABMA: j6) |
| Normal (0.05 C < P ≤ 0.1 C) | j5 / js5 | k5 / k6 |
| Heavy (P > 0.1 C) | k5 | m5 / m6 |
| Stationary inner ring, must slide on shaft (floating or idler) | g6 / h6 | g6 / h6 |
| Higher running accuracy | Use grade 5 instead of grade 6 (k5 not k6) | |

**Notes.**
- Hollow shafts and non-ferrous shafts (aluminium) need **tighter** fits. So do inner rings
  that run warmer than the shaft. [typ, ABMA 7 note]
- A robot-arm joint bearing is almost always "light load" by this definition. A 608 has
  C ≈ 3.3 kN, so 0.05 C ≈ 165 N. [datasheet, SKF 608]

### 2.4 Typical housing classes [typ, SKF]

| Condition | Housing class |
|---|---|
| Rotating inner ring, stationary outer, normal load, split or one-piece housing | H7 (outer ring can float axially) |
| Same, but needs more accurate location | J7 / JS7 |
| Floating (non-locating) bearing, must slide axially for thermal growth | H7 or G7 |
| Rotating outer ring load, light | M7 |
| Rotating outer ring load, normal or heavy (wheel hub) | N7 / P7 |
| Thin-wall or light-alloy housing | One class tighter than for steel |

**Thrust bearings (e.g. 51105).**
- Shaft ring: j6.
- Housing ring: give radial clearance (H8 or more) so the thrust bearing carries only axial
  load, and support radial load with a separate radial bearing. [typ, SKF]

### 2.5 Worked bearing example: 608-2RS (8×22×7) [derived from §1.3 and §2.2]

**Shaft ⌀8 k5.**
- ei = +1 µm, IT5 = 6 µm, so the shaft is 8.001–8.007 mm.
- Bore is 7.992–8.000 mm.
- Fit: 1 to 15 µm interference. This is a light press; use a sleeve on the inner ring.

**Shaft ⌀8 h6.**
- Shaft is 7.991–8.000 mm.
- Fit: +8 µm clearance to 8 µm interference. A slip/transition fit. Add Loctite 641/603 if the
  inner ring must not creep.

**Housing ⌀22 H7.**
- Housing is 22.000–22.021 mm. OD is 21.991–22.000 mm.
- Fit: 0 to 30 µm clearance. The outer ring can be pushed in by hand.

**Housing ⌀22 K7.**
- Housing is 21.985–22.006 mm.
- Fit: 15 µm interference to 15 µm clearance. The ring is located, and you need a press.

### 2.6 Seat geometry checklist [typ, SKF/NSK catalogues]
- **Shaft seat Ra:** ≤ 0.8 µm for IT6 seats (d ≤ 80 mm). **Housing bore Ra:** ≤ 1.6 µm.
- **Form tolerance.** Seat roundness and cylindricity should be about IT3–IT4 for precision,
  or about IT5/2 for normal grade.
- **Shoulder runout.** About IT5 for a normal-grade seat.
- **Fillet radius** at the shoulder < the bearing's chamfer r_s,min (608: 0.3 mm), or the ring
  won't seat. You can also use a relief groove (undercut, DIN 509).
- **Shoulder height.** Big enough to contact the ring face, small enough not to touch the
  seal. Use the catalogue d_a/D_a values; for a 608, d_a,min ≈ 10 mm.
- **Lead-in chamfer** on the shaft (about 0.5 mm × 15–30°) for pressing.
- **Press only on the ring being fitted.** Pressing through the balls brinells the races.
- **Axial retention options:**
  - Shoulder plus circlip (DIN 471 for shafts, DIN 472 for bores).
  - Locknut (KM).
  - End cap.
  - In printed parts: a lip or clamp plate.
- **Pairs on one shaft.** Fix one bearing axially (locating) and let the other float, so the
  pair is not preloaded by thermal growth. The exception is angular-contact pairs that are
  meant to be preloaded.

### 2.7 Linear bearings and bushings [typ, Misumi/THK/igus]

| Part | Shaft | Housing |
|---|---|---|
| LMxUU (e.g. LM8UU, ⌀8×15×24) | h6 / g6 hardened rod | H7 (J7 to remove play) |
| Sintered bronze bushing (oil-impregnated) | f7 / g6 | Press into H7 (the bush closes up about 0.5–1 × interference, so the bore after pressing is roughly F7) |
| igus iglidur plain bearing | h9 recommended (iglidur wants clearance) | H7. The bushing ID is designed to reach E10-ish only after press-in |
| Dowel pin ISO 8734 (m6) | — | Press side: H7 (light press). Slip side: F7 / G7, or ream +0.01 mm |

---

## 3. Threads

### 3.1 ISO metric coarse (ISO 261/262), pitch and key data [std; cross-checked with TR Fastenings and Optimas]

| Size | Pitch P (mm) | Fine pitch(es) | Tap drill (cut), D−P | Tap drill (form/roll), ≈D−0.5P | Tensile stress area As (mm²) | Hex key (ISO 4762) | Wrench AF (ISO 4032 nut) |
|---|---|---|---|---|---|---|---|
| M2 | 0.40 | 0.25 | 1.60 | 1.80 | 2.07 | 1.5 | 4 |
| M2.5 | 0.45 | 0.35 | 2.05 (2.1) | 2.30 | 3.39 | 2 | 5 |
| M3 | 0.50 | 0.35 | 2.50 | 2.80 | 5.03 | 2.5 | 5.5 |
| M4 | 0.70 | 0.50 | 3.30 | 3.70 | 8.78 | 3 | 7 |
| M5 | 0.80 | 0.50 | 4.20 | 4.60 | 14.2 | 4 | 8 |
| M6 | 1.00 | 0.75 | 5.00 | 5.50 | 20.1 | 5 | 10 |
| M8 | 1.25 | 1.0 | 6.80 (fine: 7.0) | 7.40 | 36.6 | 6 | 13 |
| M10 | 1.50 | 1.25, 1.0 | 8.50 (fine 1.25: 8.8) | 9.30 | 58.0 | 8 | 16 (ISO; 17 DIN) |
| M12 | 1.75 | 1.5, 1.25 | 10.20 (fine 1.5: 10.5) | 11.20 | 84.3 | 10 | 18 (ISO; 19 DIN) |

**Formulas.**
- Tensile stress area: As = (π/4)·(d − 0.9382·P)² [mm²]. [std, ISO 898-1]
- Tap drill for cut taps (gives about 75–80 % thread): D − P.
- Form taps displace material and need a larger hole, about D − 0.5P. Check the tap maker's
  table because it depends on the material. [typ, OSG/Emuge guides]

**Thread tolerance classes.**
- Default is **6H** (nut or internal) / **6g** (bolt or external). This is "medium".
- 4H/5H/4h are fine. 7H/8g are coarse.
- Callout example: `M6x1-6H`. When the pitch is coarse you may simply write `M6`. [std ISO 965]

**Thread depth notes.**
- Internal thread minor diameter for 6H: M3 is about 2.46–2.60 mm, M6 about 4.92–5.15 mm. A
  2.5 mm or 5.0 mm drill sits inside that range. [std ISO 965 summary; est]
- **Blind holes.** Drill depth ≥ thread depth + about 3–5·P for a plug tap (the tap chamfer is
  about 3–5 threads), or + about 1.5–2·P for a bottoming tap.
- On drawings, give both depths: `M5 ↧10 / drill ⌀4.2 ↧13`. [typ]

### 3.2 Unified (UNC/UNF) common sizes [std ASME B1.1; tap drill values typ at about 75 % thread; cross-check with Fastenal/TR charts]

| Size | TPI UNC / UNF | Major ⌀ (in / mm) | Tap drill UNC (75 %) | Close clearance | Free clearance |
|---|---|---|---|---|---|
| #2 | 56 / 64 | 0.086 / 2.18 | #50 (1.78 mm) | #44 (2.18) | #41 (2.44) |
| #4 | 40 / 48 | 0.112 / 2.84 | #43 (2.26) | #32 (2.95) | #30 (3.26) |
| #6 | 32 / 40 | 0.138 / 3.51 | #36 (2.71) | #28 (3.57) | #25 (3.80) |
| #8 | 32 / 36 | 0.164 / 4.17 | #29 (3.45) | #19 (4.22) | #16 (4.50) |
| #10 | 24 / 32 | 0.190 / 4.83 | #25 (3.80); 10-32: #21 (4.04) | #11 (4.85) | #7 (5.11) |
| 1/4 | 20 / 28 | 0.250 / 6.35 | #7 (5.11); 1/4-28: #3 (5.41) | F (6.53) | H (6.76) |
| 5/16 | 18 / 24 | 0.3125 / 7.94 | F (6.53) | P (8.20) | Q (8.43) |
| 3/8 | 16 / 24 | 0.375 / 9.53 | 5/16" (7.94) | W (9.80) | X (10.08) |
| 1/2 | 13 / 20 | 0.500 / 12.7 | 27/64" (10.72) | 33/64" (13.1) | 17/32" (13.5) |

**Notes.**
- Classes are 2A/2B (default, comparable to 6g/6H) and 3A/3B (tighter).
- Unified tap drill (inch units): drill ≈ D − 0.01299 · %thread / n, where n = TPI.
  [std formula, Machinery's Handbook principle]
- **Never mix metric and unified on one product without a reason.** Mechy designs are metric,
  so use M-threads and stock M-hardware.

### 3.3 Percentage of thread [typ]
- 75 % thread already gives about 95 % or more of 100 % thread strength, with far less tap
  torque.
- In tough materials (stainless, titanium) or deep holes, 60–65 % is common.
- Bigger drill = longer tap life. Thin sheet may need 85 %.

### 3.4 Thread engagement length [typ; FED-STD-H28/2 method summarised; rules cross-checked across Machinery's Handbook principle, Fastenal and Bossard guidance]

**Goal:** the bolt shank should break before the internal threads strip. The internal threads
in a weaker material need more length.

| Internal thread material | Recommended engagement Le (min) |
|---|---|
| Steel nut, or steel ≥ bolt strength | 1.0 × D (a standard nut is about 0.8 D, and that is OK for matched grades) |
| Cast iron, brass, bronze | 1.5 × D |
| Aluminium alloy (6061-T6, 7075) | 1.5–2.0 × D |
| Soft aluminium, magnesium, zinc die-cast | 2.0–2.5 × D |
| Plastic (direct tapped or self-tapping) | 2.0–3.0 × D, or use inserts |
| FDM print, self-tapped | ≥ 2.5 × D, and prefer a heat-set insert |

**Useful facts.**
- The first engaged thread carries about 1/3 of the load, and the first 3 threads together
  carry about 3/4 of it. Going beyond about 1.5–2 D adds almost no strength. [typ]
- To check against strength, use the strength ratio. For a weak internal material:
  Le ≈ Le_steel × (Su_bolt / Su_internal) × ~0.5–0.6 correction. That is an estimate; for real
  numbers use the FED-STD-H28 formula
  Le = 2·As / [π·Kn,max·(0.5 + 0.57735·n·(Es,min − Kn,max))] (inch) together with the material
  ratio J = (As_ext·Su_ext)/(As_int·Su_int). [std, FED-STD-H28/2B]
- **Threaded inserts** (helicoil or Keensert) let a short engagement in aluminium carry the
  full bolt load. Helicoil lengths come in 1D, 1.5D, 2D and 2.5D. [typ]

### 3.5 Fastener mini-rules [typ]
- In aluminium and plastic, use socket head cap screws (ISO 4762) with a washer under the head.
- Use button heads (ISO 7380) where clearance is limited. Their hex key is one size smaller:
  M3 = 2 mm.
- Grade 8.8 (steel) is normal. 12.9 is for high-preload joints. A2/A4 stainless is weaker
  (about 70 class ≈ 8.8 yield ×0.75).
- For a screw into a printed part, set the max torque by stripping, not by the screw. M3 in a
  PLA boss is about 0.5–1 N·m. [est]

---

## 4. Clearance holes, counterbores and countersinks

### 4.1 Clearance holes (ISO 273: fine / medium / coarse) [std; cross-checked with TR Fastenings (medium column) and Optimas]

| Thread | Fine (close) | Medium (normal) | Coarse (free) |
|---|---|---|---|
| M2 | 2.2 | 2.4 | 2.6 |
| M2.5 | 2.7 | 2.9 | 3.1 |
| M3 | 3.2 | 3.4 | 3.6 |
| M4 | 4.3 | 4.5 | 4.8 |
| M5 | 5.3 | 5.5 | 5.8 |
| M6 | 6.4 | 6.6 | 7.0 |
| M8 | 8.4 | 9.0 | 10.0 |
| M10 | 10.5 | 11.0 | 12.0 |
| M12 | 13.0 | 13.5 | 14.5 |

**When to use each column** [typ]:
- **Fine:** precision location by screws. Avoid it, and use dowels for location instead.
- **Medium:** the default.
- **Coarse:** cast, laser-cut or 3D-printed parts, or any case where the position tolerance is
  loose.
- For FDM, start from **coarse + 0.1–0.2 mm**. For example, M3 → 3.4–3.6 mm as designed (it
  prints at about 3.2–3.4). [typ/est]

**The position link.**
- The medium column allows a floating-fastener position tolerance of T = H − F. For M5 that is
  5.5 − 5.0 = ⌀0.5 on each part.
- Fine M5 gives only ⌀0.3. See §8.5.

### 4.2 Counterbores for socket head cap screws (ISO 4762), DIN 974-1 series [std head data ISO 4762, from engineersedge and fasten.it; counterbore ⌀ from DIN 974 typ]

| Screw | Head ⌀ dk (max) | Head height k | Counterbore ⌀ | Counterbore depth (head flush) | Clearance (medium) |
|---|---|---|---|---|---|
| M2 | 3.8 | 2.0 | 4.4 | 2.2–2.4 | 2.4 |
| M2.5 | 4.5 | 2.5 | 5.5 | 2.7–2.9 | 2.9 |
| M3 | 5.5 | 3.0 | 6.5 | 3.3–3.5 | 3.4 |
| M4 | 7.0 | 4.0 | 8.0 | 4.4–4.6 | 4.5 |
| M5 | 8.5 | 5.0 | 10.0 | 5.4–5.6 | 5.5 |
| M6 | 10.0 | 6.0 | 11.0 | 6.4–6.6 | 6.6 |
| M8 | 13.0 | 8.0 | 15.0 | 8.6 | 9.0 |
| M10 | 16.0 | 10.0 | 18.0 | 10.6 | 11.0 |
| M12 | 18.0 | 12.0 | 20.0 | 12.6 | 13.5 |

**Notes.**
- Counterbore depth = k + about 0.2–0.6 mm so the head sits just below the surface. Add the
  washer thickness if you use one (ISO 7092 small washers fit inside these bores).
- Some charts quote slightly different diameters (M3 6.5, M4 8.0–8.25, M5 9.75–10). All of them
  are dk + about 1 mm, which is the governing rule. [typ]
- **Printed counterbores:** use dk + 0.6–1.0 mm (M3 → ⌀6.2–6.5).
- **Upside-down counterbores** (bore facing the build plate) need a sacrificial bridge layer or
  "keyhole" bridging: two stepped layers that turn the circle into a rectangle and then a
  square. [typ, Prusa/community practice]

### 4.3 Countersinks [std ISO 10642 / ISO 7046]
- Metric countersunk heads are **90°**. Unified flat heads are **82°**. Do not mix them up.
- Countersink ⌀ ≈ head ⌀ + 0.2–0.5 mm. ISO 10642 M3 head is about 6.7 mm, so countersink
  ⌀6.9–7.2. M4 is about 8.96 → ⌀9.4. M5 is about 11.2 → ⌀11.5. M6 is about 13.4 → ⌀13.7.
  [std head sizes; typ countersink]
- **Tapped holes:** add a 90° countersink to about the major diameter (M5 → ⌀5.5 × 90°). It
  protects the first thread and stops burrs. [typ]
- Thin sheet less than about 0.6× head height cannot take a countersink. Use a counterbore,
  a dimple or a pan head.

---

## 5. Surface finish

### 5.1 Parameters [std ISO 21920 (replaces ISO 4287/1302), ASME B46.1]
- **Ra:** arithmetic mean roughness in µm. This is the default parameter.
- **Rz:** mean peak-to-valley over 5 cuts. Rz ≈ 4–7 × Ra for machined surfaces. [typ]
- **N grades (old ISO 1302):** N5 = 0.4, N6 = 0.8, N7 = 1.6, N8 = 3.2, N9 = 6.3,
  N10 = 12.5 µm Ra. Each grade doubles.
- **US microinches:** 1 µm = 39.37 µin. So 32 µin ≈ 0.8 µm and 63 µin ≈ 1.6 µm.
- **Drawing symbol.** A check mark with Ra written on it. A bar on top means "material removal
  required". A circle means "no material removal".

### 5.2 Ra by process [typ; consensus of the classic ASME B46.1 / Machinery's Handbook process-range chart, Engineering Toolbox, and vendor guides. The bold value is the typical result]

| Process | Achievable Ra range (µm) | Typical (µm) |
|---|---|---|
| Sand casting | 6.3–25 | **12.5** |
| Investment casting | 1.6–3.2 | **3.2** |
| Die casting | 0.8–3.2 | **1.6** |
| Forging | 3.2–12.5 | 6.3 |
| Flame or plasma cut | 6.3–25 | 12.5 |
| Saw cut | 3.2–25 | 6.3 |
| Laser cut (thin sheet) | 0.8–6.3 | 3.2 |
| Waterjet | 1.6–6.3 | 3.2–6.3 |
| Wire EDM | 0.4–3.2 | 1.6 |
| Drilling | 1.6–6.3 | **3.2** |
| Milling (end or face) | 0.8–6.3 | **1.6–3.2** |
| Turning | 0.4–6.3 | **1.6** (finish) / 3.2 (general) |
| Boring | 0.4–6.3 | 1.6 |
| Reaming | 0.4–3.2 | **0.8–1.6** |
| Broaching | 0.4–3.2 | 1.6 |
| Grinding (cylindrical or surface) | 0.1–1.6 | **0.4–0.8** |
| Honing | 0.1–0.8 | 0.2–0.4 |
| Lapping or superfinishing | 0.025–0.4 | 0.1 |
| Polishing | 0.05–0.4 | 0.2 |
| Injection moulding | 0.05–3.2 | depends on mould finish (SPI A–D) |
| FDM print, side walls | 6–25 (layer lines; 0.2 mm layer ≈ 10–15) | 12 [est] |
| FDM print, top skin | 2–8 | 5 [est] |
| SLA / MSLA resin | 0.5–3 | 1.5 [est] |
| SLS / MJF nylon | 4–12 | 6–8 [est] |
| Metal LPBF (as-built) | 6–20 | 10 [est] |

### 5.3 Required Ra by function [typ, SKF / Parker O-ring handbook / general design guides]

| Function | Ra (µm) |
|---|---|
| Bearing shaft seat, IT6 (d ≤ 80 mm) | ≤ 0.8 (precision: 0.4) |
| Bearing housing bore | ≤ 1.6 |
| Plain bushing journal | 0.2–0.8 |
| Dynamic O-ring or lip-seal shaft | 0.1–0.4 (lip seals 0.2–0.8, plunge-ground, no lead) |
| Static O-ring groove | ≤ 1.6 (flanks 3.2) |
| Press-fit surfaces | 0.8–1.6 (rougher surfaces lose interference: about 0.5–1× Rz is flattened) |
| Sliding fit (g6) | 0.4–1.6 |
| General machined face | 3.2 (default if not specified) |
| Non-functional | 6.3–12.5 |
| Clearance holes | 6.3 (drilled is fine) |

**Cost.** Each halving of Ra below 1.6 µm roughly adds a process step: turn → fine turn →
grind → lap. Specify finish only where it matters. [typ]

---

## 6. Achievable tolerances by process

### 6.1 IT grade by process [typ; Engineering Toolbox "Machine processes tolerance grades" chart and process literature; cross-checked with a Springer machining chapter (rough turning IT12–14, fine turning IT6–7) and mfgrobots (turning IT7–8)]

| Process | IT grade range | Comment |
|---|---|---|
| Lapping, honing | IT4–IT5 | Gauge work |
| Cylindrical or surface grinding | IT5–IT7 | Bearing seats, hardened parts |
| Fine (diamond) turning or boring | IT5–IT7 | |
| Reaming | IT7–IT8 (IT6 with care) | Standard H7 holes |
| Broaching | IT7–IT8 | |
| Finish turning | IT7–IT8 | |
| Finish milling | IT8–IT9 | |
| Boring (general) | IT8–IT10 | |
| Rough turning | IT11–IT13 | |
| Rough milling | IT11–IT13 | |
| Drilling (twist drill) | IT10–IT12 | Drills cut about 0.02–0.1 mm oversize and wander |
| Punching or blanking | IT10–IT12 | |
| Die casting | IT11–IT14 | |
| Injection moulding | IT11–IT14 (often quoted IT13) | Depends on material shrink |
| SLA | IT11–IT13 [est] | |
| FDM | IT12–IT15 [est] | |
| Sand casting | IT14–IT16 | |
| Flame cutting | IT15–IT16 | |

### 6.2 Practical ± tolerances (what to expect from a job shop or online service) [typ; Protolabs, Xometry, Hubs design guides; values commonly quoted, check the vendor's current guide]

| Process | Standard (no extra cost) | Precision (extra cost) | Notes |
|---|---|---|---|
| CNC milling | ±0.1 mm (ISO 2768-m) to ±0.05 | ±0.01–0.025 | Holes for fits: ream |
| CNC turning | ±0.05 | ±0.01 | Diameters easier than lengths |
| Grinding | ±0.01 | ±0.002–0.005 | |
| Reamed hole | H7 | H6 | |
| Drilled hole | +0.1 / −0 (approximately) | | Positional ±0.1 without a spot drill |
| Laser cut sheet (≤ 6 mm) | ±0.1–0.2 | ±0.05 | Kerf about 0.1–0.3 mm; small holes ≥ material thickness |
| Waterjet | ±0.1–0.25 | | Taper on thick stock |
| Sheet metal bend | ±0.25–0.5 linear, ±1° angle | | Tolerances accumulate across bends |
| Wire EDM | ±0.005–0.01 | ±0.002 | |
| Injection moulding | ±0.1 (small parts) | ±0.05 | Plus about ±0.1 % of size |
| FDM | ±0.2–0.5 mm or ±0.5 % (larger) | ±0.1 (tuned printer) | Holes undersize, Z steps = layer height |
| SLA / MSLA | ±0.1–0.15 or ±0.2 % | ±0.05 | Post-cure shrink |
| SLS / MJF | ±0.3 mm or ±0.3 % (larger) | | Warp on large flats |
| Sand casting | ±1–2 mm | | Machine the functional faces |

### 6.3 ISO 2768 general tolerances (for any dimension without its own tolerance) [std ISO 2768-1; widely reproduced, e.g. on engineersedge]

Linear dimensions (± mm):

| Size band (mm) | f (fine) | m (medium) | c (coarse) | v (very coarse) |
|---|---|---|---|---|
| 0.5–3 | 0.05 | 0.1 | 0.2 | — |
| >3–6 | 0.05 | 0.1 | 0.3 | 0.5 |
| >6–30 | 0.1 | 0.2 | 0.5 | 1.0 |
| >30–120 | 0.15 | 0.3 | 0.8 | 1.5 |
| >120–400 | 0.2 | 0.5 | 1.2 | 2.5 |
| >400–1000 | 0.3 | 0.8 | 2.0 | 4.0 |

**Other rules from the standard.**
- **External radii and chamfers (m class):** 0.5–3 → ±0.2; >3–6 → ±0.5; >6 → ±1.
- **Angles (m class):** ≤10 mm → ±1°; 10–50 → ±30'; 50–120 → ±20'.
- **ISO 2768-2 (geometric) classes H, K, L.** These cover straightness, flatness,
  perpendicularity, symmetry and runout. Use **"ISO 2768-mK"** as the default title-block note
  for machined parts. For printed parts, write something like "General tol. ±0.3 mm unless
  stated".

---

## 7. Tolerance stack-up

### 7.1 Method
1. **Define the requirement.** Name the gap or the result, and its limits. Example: "the
   bearing must clear the housing lip: gap ≥ 0.1 mm".
2. **Draw the loop diagram.** Start at one side of the gap and walk part by part through the
   dimensions to the other side. Give each dimension a direction (+ or −).
3. **Nominal gap** = Σ (signed nominal dimensions).
4. **Choose the method** and compute the variation.
5. **Compare** the min and max against the requirement. If it fails, tighten the biggest
   contributor or change the design: add an adjustment or a datum, or shorten the loop.

### 7.2 Methods [typ; standard tolerance-analysis texts, e.g. Fischer "Mechanical Tolerance Stackups"; MIT 2.008 notes]

| Method | Formula (tᵢ = ± tolerance) | Assumption | Use when |
|---|---|---|---|
| Worst case (WC) | T = Σ tᵢ | Every part is at its limit at once | ≤ about 4 contributors, safety-critical, low volume (prototype, 3D print), or interchangeability is a must |
| RSS (statistical) | T = √(Σ tᵢ²) | Independent, normal, centred, tolerance = ±3σ (99.73 %) | ≥ about 5 contributors, high volume, processes are in control |
| Modified (Benderized) RSS | T = 1.5 × √(Σ tᵢ²) | Allows for drifting or non-centred processes | Middle ground and the common industrial default |
| Monte Carlo | Simulate the distributions | Non-normal, non-linear stacks | Complex geometry; Mechy can run this easily |

**Notes.**
- For non-linear stacks (angles, radii), use the sensitivities: T_wc = Σ |∂y/∂xᵢ|·tᵢ and
  T_rss = √Σ (∂y/∂xᵢ·tᵢ)².
- Under RSS, the biggest tolerance dominates, so tighten that one first.

### 7.3 Worked mini-example [derived]

Four stacked plates, each 5.00 ± 0.10 mm, sit inside a slot of 20.40 ± 0.05 mm. What is the
gap?

1. Nominal gap = 20.40 − 4 × 5.00 = 0.40 mm.
2. **Worst case:** T = 0.05 + 4 × 0.10 = 0.45, so the gap ranges from −0.05 to 0.85. **It can
   interfere.**
3. **RSS:** T = √(0.05² + 4 × 0.10²) = √(0.0025 + 0.04) = 0.206, so the gap is 0.19 to 0.61
   (99.7 % of assemblies).
4. **Modified RSS:** T = 0.31, so the gap is 0.09 to 0.71.
5. **Decision.** For a prototype or low volume, use worst case. Either widen the slot to
   20.50, or hold the plates to ±0.05: T_wc = 0.05 + 0.2 = 0.25, giving a gap of +0.15 to
   +0.65.

### 7.4 Stack-up tips [typ]
- **Shorten the loop.** Dimension functional features from one common datum. Chain
  dimensioning accumulates error; baseline dimensioning does not.
- **Add adjustment.** Slots, shims, set screws or belt tensioners remove the stack entirely.
  This is the normal answer in printed robots.
- **Include geometric terms:** position, perpendicularity, runout, bearing internal clearance
  and thermal growth.
- **Bearing stacks:** include the bearing width tolerance (608: 7 mm 0/−0.12) and the circlip
  groove tolerance. Then give the floating bearing axial room ≥ the stack plus thermal growth.
- **Printed parts:** use worst case with ±0.2–0.3 mm per printed dimension. Several printed
  parts in a loop easily add ±1 mm, so design compliance or adjustment into the stack.

---

## 8. GD&T basics

### 8.1 Why
± tolerances on X and Y create square zones, leave the measurement origin ambiguous, and cannot
control form or orientation. GD&T states **what** is controlled, **relative to what** (the
datums), and **how much**. [std ASME Y14.5-2018 / ISO 1101]

### 8.2 Datums
- **Datum features** are real surfaces, marked with a datum triangle and a letter (A, B, C).
  The datum is the theoretical plane or axis simulated from them.
- **3-2-1 rule.**
  - Primary A: the largest stable face, 3 contact points. It locks 3 DOF.
  - Secondary B: 2 points. It locks 2 DOF.
  - Tertiary C: 1 point. It locks the last DOF.
- **Pick datums the way the part is assembled and fixtured.** Use the mounting face as A and
  the locating bore or dowel as B or C. Holes used as datums give you an axis.
- **Basic dimensions** (boxed values) are exact and have no tolerance. The tolerance lives in
  the feature control frame.

### 8.3 Feature control frame
`| ⌖ | ⌀0.1 Ⓜ | A | B | C |` reads as: symbol | zone (⌀ for a cylindrical zone) + modifier |
primary | secondary | tertiary datum.

### 8.4 The 14 characteristics (the ones that matter for Mechy are in bold) [std]

| Category | Symbol | Datum needed? | Typical use |
|---|---|---|---|
| Form | **Flatness ⏥** | No | Mounting faces, sealing faces. Typical machined: 0.02–0.05 mm over 100 mm |
| Form | Straightness ⏤ | No | Shafts, rails |
| Form | Circularity ○ | No | Seats |
| Form | **Cylindricity ⌭** | No | Bearing seats (about IT5/2) |
| Orientation | **Perpendicularity ⊥** | Yes | Bore to face, shaft to flange |
| Orientation | **Parallelism ∥** | Yes | Rail mounting faces, opposite faces |
| Orientation | Angularity ∠ | Yes | |
| Location | **Position ⌖** | Yes (usually) | **Holes, pins, bores: the most used callout** |
| Location | Concentricity / Symmetry | Yes | Removed in ASME Y14.5-2018. Use position or runout |
| Runout | **Circular runout ↗** | Yes (axis) | Pulleys, shaft seats, shoulders |
| Runout | Total runout | Yes | Spindles |
| Profile | **Profile of a surface ⌓** | Optional | Complex surfaces; increasingly used for everything |
| Profile | Profile of a line ⌒ | Optional | |

### 8.5 Position, MMC and bonus tolerance [std; formulas standard in ASME Y14.5 and any GD&T primer]

- **MMC (Ⓜ)** is the condition with the most material: the smallest hole or the largest pin.
  **LMC (Ⓛ)** is the opposite. **RFS** (no modifier) is the default.
- **Bonus.** With Ⓜ on a hole, the allowed position zone grows by however much the actual hole
  departs from its MMC size. Example: ⌀5.5 +0.1/0 hole with ⌖ ⌀0.2 Ⓜ. If the hole is made at
  ⌀5.6, the allowed position becomes ⌀0.3. This matches how bolts actually fit, and it allows
  simple functional go-gauges. Use Ⓜ on clearance holes and pins. Use RFS on bearing bores and
  precision locating features.
- **Virtual condition** (hole) = MMC size − geometric tolerance at MMC. The mating pin must be
  ≤ this.
- **Floating fastener** (clearance holes in both parts, bolt and nut): T = H − F, the position
  tolerance allowed on **each** part. H is the hole MMC (minimum) diameter and F is the
  fastener max diameter. M5 in ⌀5.5 holes gives T = ⌀0.5 on each part.
- **Fixed fastener** (one part tapped or pressed): T₁ + T₂ = H − F. With an equal split,
  T = (H − F)/2. M5 into a tapped hole through a ⌀5.5 hole gives T = ⌀0.25 on each part.
  - Use a **projected tolerance zone Ⓟ** on the tapped hole (height = the mating part
    thickness). A tilted tapped hole uses up clearance above the surface.
- **Converting coordinate tolerances.** ±a in X and ±b in Y corresponds to a diametral zone of
  2·√(a² + b²). ±0.1/±0.1 gives ⌀0.283. Conversely, a ⌀0.28 position zone gives about 57 % more
  area than the ±0.1 square it circumscribes. [std]

### 8.6 ISO vs ASME default principle [std]
- **ASME Y14.5: Rule #1 (envelope principle).** The size tolerance also limits form. At MMC
  the feature must be perfect form. This is the default.
- **ISO 8015: independency principle.** Size and form are independent unless Ⓔ is added.
  Write `⌀8 h6 Ⓔ` on fits where the envelope matters (bearing seats, sliding fits).
- **State the standard in the title block:** "Tolerancing ISO 8015" or "ASME Y14.5-2018".

### 8.7 GD&T callouts Mechy should use (templates) [typ]

| Feature | Callout |
|---|---|
| Base mounting face | ⏥ 0.05, datum A |
| Bearing bore | `⌀22 H7 Ⓔ`, ⊥ 0.02 A, datum B |
| Bolt pattern (clearance) | `4× ⌀5.5 +0.1/0`, ⌖ ⌀0.2 Ⓜ A B |
| Tapped pattern | `4× M5-6H ↧10`, ⌖ ⌀0.2 Ⓟ 8 A B |
| Shaft seat | `⌀8 k5 Ⓔ`, ↗ 0.01 A-B (common axis of the two seats) |
| Pulley | ↗ 0.05 to the bore |
| Printed part (if used at all) | Profile ⌓ 0.4 A B C on all surfaces, plus explicit holes |

---

## 9. Drawing conventions

### 9.1 Must-haves on every drawing [std ISO 128, ISO 7200 title block, ISO 129 dimensioning; ASME Y14.5/Y14.100]
1. **Title block:**
   - Part name, part number, revision, material and condition (e.g. "6061-T6", "PETG").
   - Finish or treatment (anodise, black oxide), mass, scale, units ("mm").
   - Projection symbol, general tolerance note ("ISO 2768-mK"), tolerancing standard.
   - Drawn and approved by, and the date.
2. **Projection.**
   - **First angle (ISO, Europe):** the right-side view is drawn on the left.
   - **Third angle (US, ASME):** the right-side view is drawn on the right.
   - Always print the truncated-cone symbol. Misreading the projection is a classic scrap
     cause.
3. **Views:** front, top, side, plus sections and details as needed. Hidden lines only if they
   add clarity. Use an isometric for orientation.
4. **Dimension each feature once.** Do not over-dimension or close chains; leave one
   dimension of a chain undimensioned, or mark it as a reference "(…)".
5. **Dimension from datums** (baseline or ordinate), not chained, wherever function matters.
6. **Fits:** `⌀8 H7`, threads `M5-6H ↧10`, holes `4× ⌀5.5 THRU`, counterbore
   `⌴ ⌀10 ↧5.4`, countersink `⌵ ⌀11.5 × 90°`.
7. **Surface finish symbol:** a general one in the title block ("Ra 3.2 unless stated") plus
   specific symbols on functional surfaces.
8. **Edge notes:** "Break all sharp edges 0.2–0.5" and "Remove burrs". Use ISO 13715 for edge
   conditions.
9. **Notes in imperative form:** "HEAT TREAT TO 58–62 HRC", "ANODISE TYPE II BLACK".

### 9.2 Line types (ISO 128) [std]
- Continuous thick: visible edges.
- Continuous thin: dimension lines, hatching.
- Dashed: hidden edges.
- Chain thin: centre lines and axes.
- Chain thick: cutting planes at the ends.

### 9.3 Hole and thread notation cheat-sheet

| Callout | Meaning |
|---|---|
| `⌀6 H7 ↧12` | ⌀6 H7 hole, 12 deep (full diameter depth) |
| `M4-6H ↧8 / ⌀3.3 ↧11` | M4 thread 8 deep, tap drill ⌀3.3, 11 deep |
| `⌀4.5 THRU ⌴ ⌀8 ↧4.4` | M4 SHCS counterbored clearance hole |
| `0.5 × 45°` | Chamfer |
| `R0.5 MAX` | Internal radius allowed up to 0.5 |
| `2× ⌀3 m6 DOWEL PRESS` | Assembly note for dowels |
| `(12.5)` | Reference dimension, not inspected |
| `[25.000]` boxed | Basic dimension (GD&T) |

### 9.4 For Mechy outputs [typ]
- **For 3D printing, the STL/STEP is the drawing.** You still need a one-page "critical
  dimensions" sheet: bearing bores, shaft holes, insert holes and belt paths with their
  intended fit and test method.
- **For machined parts, send STEP + PDF drawing.** The STEP carries the geometry. The PDF
  carries tolerances, threads, finishes and notes. Online shops quote tight tolerances only
  when they are on the PDF.

---

## 10. Feeds and speeds principles

### 10.1 Formulas [std, Sandvik Coromant formula library]
- Spindle speed: **n = 1000 · Vc / (π · D)** [rpm], where Vc is cutting speed [m/min] and D is
  the tool (milling, drilling) or work (turning) diameter [mm].
- Milling feed: **vf = fz · z · n** [mm/min], where fz is chip load per tooth [mm] and z is the
  number of flutes.
- Turning feed: vf = fn · n, where fn is feed per rev [mm/rev].
- Metal removal rate: Q = ap · ae · vf / 1000 [cm³/min], where ap is axial depth and ae is
  radial width [mm].
- Power: Pc ≈ Q · kc / 60 000 [kW], where kc is specific cutting force [N/mm²].
  - kc ≈ 700–800 for aluminium, 1500–2000 for mild steel, 2000–2500 for stainless.
    [typ, Sandvik]
- **Chip thinning.** When ae < D/2 the actual chip is thinner than fz. Raise fz by
  D / (2·√(ae·(D − ae))) to keep the chip thickness. [std, Sandvik/Harvey]

### 10.2 Typical cutting speeds Vc (m/min) [typ; manufacturer ranges from Sandvik, Harvey Tool and Kennametal summaries. Always use the tool maker's own data]

| Material | HSS | Carbide (uncoated / coated) |
|---|---|---|
| Aluminium 6061 / 6082 | 60–120 | 200–600+ (limited by spindle rpm) |
| Brass, bronze | 45–90 | 150–300 |
| Mild steel (S235, 1018) | 25–35 | 120–250 |
| Alloy steel (4140, 42CrMo4), annealed | 15–25 | 100–180 |
| Stainless (304 / 316) | 10–18 | 60–150 |
| Cast iron | 15–30 | 80–150 |
| Titanium (Ti-6Al-4V) | 6–10 | 30–60 |
| Acetal (POM/Delrin) | 60–150 | 150–300 |
| Nylon, PEEK | 60–120 | 150–250 (sharp tools; heat is the enemy) |

### 10.3 Typical chip loads fz (mm/tooth), carbide end mill, full-slot to moderate engagement [typ, est]

| Tool ⌀ | Aluminium | Mild steel | Stainless | Plastics |
|---|---|---|---|---|
| 3 mm | 0.015–0.03 | 0.01–0.02 | 0.008–0.015 | 0.03–0.06 |
| 6 mm | 0.03–0.06 | 0.02–0.04 | 0.015–0.03 | 0.05–0.10 |
| 10 mm | 0.05–0.10 | 0.03–0.06 | 0.025–0.05 | 0.08–0.15 |
| 12 mm | 0.06–0.12 | 0.04–0.07 | 0.03–0.06 | 0.10–0.20 |

- **Drilling feed:** fn ≈ 0.01–0.02 × D mm/rev in steel, and up to about 0.03 × D in
  aluminium. Peck deeper than about 3×D. [typ]
- **Tapping:** feed = pitch per rev, exactly (rigid tapping). Use about 1/3–1/2 of the
  drilling Vc. [typ]
- **Reaming:** about 1/2–2/3 of the drilling Vc and 2–3× the drilling feed. Leave stock of
  0.1–0.2 mm on the diameter for ⌀3–10 and 0.2–0.3 mm for ⌀10–25. [typ]

### 10.4 Principles and failure modes [typ]
- **Too low a chip load causes rubbing.** You get work hardening (stainless), heat and dull
  tools. "Feed it like you mean it."
- **Too high a chip load** breaks the tool or chatters.
- **Built-up edge in aluminium:** use sharp, polished 2–3 flute tools, coolant or air blast,
  and higher speed.
- **Chatter:** reduce stick-out (keep it under about 3×D), reduce ae, change rpm by ±10–20 %,
  and use variable-pitch tools.
- **Pocket depth:** keep it ≤ about 3–4× the tool diameter for standard tools. Deep, narrow
  pockets are expensive.
- **Climb milling** is better on rigid CNC. **Conventional milling** is better on manual
  machines with backlash.
- **Hobby routers** (low rigidity) need a small ap, adaptive or trochoidal toolpaths, high rpm
  with chip loads near the low end of the table, and single-flute tools for aluminium and
  plastics.
- **Plastics melt.** Use sharp single- or "O"-flute tools with high feed and chip evacuation.
  Don't dwell.

---

## 11. Common stock sizes

Always design to stock and avoid machining off whole millimetres. [typ; Misumi, McMaster,
Metals4U and Online Metals catalogues; the availability of sizes varies by region]

### 11.1 Metric round bar (mm)
- **Common:** 3, 4, 5, 6, 8, 10, 12, 14, 15, 16, 18, 20, 22, 25, 30, 32, 35, 40, 45, 50, 60.
- **Hardened chromed linear shaft (h6 or g6):** 3, 4, 5, 6, 8, 10, 12, 13, 16, 20, 25, 30.
  Of these, **8 mm and 10 mm** are standard for small machines.
- **Silver steel / drill rod (h9-ish, ground):** 1–20 mm in 0.5 mm steps.
- **Dowel pins (ISO 8734, m6, hardened):** ⌀1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12. Lengths 4–60.

### 11.2 Plate and flat (mm)
- **Aluminium plate (6061/6082/5083/MIC-6 cast plate):** 1, 1.5, 2, 3, 4, 5, 6, 8, 10, 12, 15,
  20, 25, 30.
  - Cast tooling plate (MIC-6, 5083 cast) is flat to about 0.13 mm/300 mm and stress-free. Use
    it for bases. [typ, Alcoa MIC-6 datasheet]
- **Steel sheet:** 0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0, 4, 5, 6.
- **Stainless sheet:** 0.5–3.
- **Acrylic and polycarbonate sheet:** 2, 3, 4, 5, 6, 8, 10.
- **Inch plate:** 1/16, 1/8, 3/16, 1/4, 3/8, 1/2, 3/4, 1 in. In the US, inch stock is far
  easier to source, and metric-designed parts may be cut from a slightly thicker inch plate.

### 11.3 Tube and profile
- **Aluminium tube OD:** 6, 8, 10, 12, 16, 20, 25, 30, 40 with 1–2 mm walls.
- **Carbon-fibre tube:** 8, 10, 12, 16, 20, 25 OD.
- **Aluminium extrusion:** 2020 (6 mm slot, M5 T-nut), 2040, 3030 (8 mm slot, M6), 4040.
  Typical cut tolerance is ±0.2–0.5 mm unless "precision cut".

### 11.4 Hardware stock sizes
- **Screw lengths (ISO 4762):** 4, 5, 6, 8, 10, 12, 14, 16, 20, 25, 30, 35, 40, 45, 50… mm.
  **M3 ×6/8/10/12/16/20, M4 and M5 ×8–30** are the hobby staples.
- **Bearings (common in printed robotics):**
  - 608 (8×22×7)
  - 625 (5×16×5)
  - 623 (3×10×4)
  - 6000 (10×26×8)
  - 6001 (12×28×8)
  - 6800-series thin section (6800: 10×19×5; 6805: 25×37×7)
  - F-flanged variants (F623, F624, F625)
  - LM8UU (8×15×24)
  - Thrust: 51100 (10×24×9), 51105 (25×42×11)
- **GT2 belts:** 6 mm and 9 mm wide, pitch 2 mm. Closed loops in 2 mm length steps (e.g. 158,
  200, 280, 400 mm). Pulleys have 16, 20, 36, 60 teeth with 5 or 8 mm bores.

---

## 12. Deburring, chamfers, edges and corners

[typ; ISO 13715 edge notation; vendor DFM guides from Protolabs and Xometry]

| Situation | Rule |
|---|---|
| General external edges (machined) | Break 0.2–0.5 mm (or 0.5 × 45°). Write "Break sharp edges" as a general note |
| Edges handled by people | ≥ 0.5 mm chamfer or R0.5 |
| Press-fit shaft or pin | Lead-in chamfer 15–30° (included 30–60°), length about 0.5–1 mm |
| Holes receiving pins or bearings | 0.3–0.5 × 45° entry chamfer; for a bearing seat, smaller than the bearing chamfer gap |
| Bearing shoulder fillet | Radius < bearing r_s,min (608: < 0.3); otherwise use a DIN 509 undercut |
| Tapped hole | 90° countersink to the major ⌀ |
| Internal pocket corners | Radius ≥ cutter radius; use 1.1–1.3 × R. Deep pockets need a larger tool, so a larger radius. For square-corner mating parts, use dogbone or T-bone relief |
| Bottom of a blind milled pocket | Flat with a small corner radius (bull nose) is fine. Specifying a sharp corner forces EDM |
| Drilled blind hole bottom | 118° (or 135°) cone. Don't dimension a flat bottom unless you need one (and pay for it) |
| Sheet metal | Inside bend radius ≥ material thickness (steel); hole edge ≥ 2 × t from a bend; add bend relief |
| Thread ends on shafts | Chamfer to the minor diameter. Thread undercut for full thread to the shoulder (DIN 76) |
| Sealing O-ring grooves | Break edges 0.1–0.2 so the O-ring is not cut; lead-in 15–20° on the bore |
| 3D prints, bottom layer | 0.3–0.6 mm × 45° chamfer to hide elephant's foot |
| 3D prints, overhangs | Use 45° chamfers, not fillets, on downward-facing edges (fillets droop) |

**Deburring methods** [typ]:
- Hand deburr tool (swivel blade), countersink tool in a drill, or a file or Scotch-Brite pad.
- Tumbling or vibratory finishing for batches.
- Thermal or electrochemical deburring for internal cross-holes (industrial).
- Burrs on bearing seats and threads are the most common cause of "it doesn't fit". Always
  deburr before assembly and measure after.

---

## 13. Measuring and verifying (so tolerances mean something)

[typ; Mitutoyo application notes]
- **Rule of 10.** The measuring instrument should resolve about 1/10 of the tolerance.
  - Calipers (0.01 mm resolution, about ±0.02–0.03 accuracy) suit ±0.1 or wider.
  - Micrometers (±0.002 mm) suit IT7 shafts.
  - Pin gauges or bore gauges are needed for H7 holes.
- **H7 holes:** check them with a go/no-go plug gauge, or with a dowel or ground pin of known
  size.
- **Measure printed parts after they cool and condition.** Nylon absorbs moisture and grows
  about 0.5–2 %. [typ]
- **Temperature.** The reference temperature is 20 °C (ISO 1). A 100 mm aluminium part grows
  23 µm per 10 K.

---

## 14. Fits for 3D-printed parts vs machined parts

### 14.1 Why printed parts are different [typ; Prusa Knowledge Base, Sovol, UAL CCI fab-lab wiki, Zbotic guides, Xometry forum]
- **Process tolerance** is about ±0.1–0.3 mm on a tuned FDM printer, i.e. IT12–IT14, so ISO
  classes do not apply.
- **Holes print small.** STL faceting, extrusion squish and the inner-perimeter shrink pull
  the hole in by 0.1–0.3 mm on the diameter. Small holes suffer most.
- **Horizontal holes** (axis parallel to the bed) are oval and sag at the top. Use a
  **teardrop** or flat-top profile, or orient the part so critical bores are vertical.
- **Elephant's foot.** The first layers bulge 0.1–0.3 mm.
- **Z steps** are quantised to the layer height (0.1–0.3 mm).
- **Plastic creeps and relaxes.** PLA loses press-fit grip within weeks under load, especially
  when warm (PLA Tg ≈ 55–60 °C). PETG and ABS/ASA are better. PA-CF and PC are better still.
  [typ]
- **Shrinkage:** about 0.2–0.5 % for PLA/PETG, about 0.5–0.8 % for ABS/ASA, and more for
  nylon. Large parts need scale compensation. [typ]

### 14.2 Printed clearance starting values (FDM, 0.4 mm nozzle, tuned printer) [typ; values from the cited vendor guides vary. Always confirm with a test coupon]

All values are **total diametral clearance**: hole ⌀ − pin ⌀.

| Fit intent | PLA | PETG | ABS / ASA | Notes |
|---|---|---|---|---|
| Press (interference) for pins or bearings | −0.05 to +0.10 (yes, often ≥ 0 because holes print small) | 0 to +0.15 | +0.05 to +0.2 | Tune on a coupon. Bearing should go in with a vise or clamp, not a hammer |
| Snug / tight slip (located, hand assembly) | +0.10 to +0.20 | +0.15 to +0.25 | +0.20 to +0.30 | |
| Sliding / running (rotates freely) | +0.20 to +0.40 | +0.30 to +0.45 | +0.35 to +0.50 | |
| Loose (print-in-place hinges, gap between printed parts) | ≥ 0.4–0.6 gap per side for print-in-place | | | Print-in-place needs ≥ 0.3–0.5 mm air gap per side |

**Cross-check of sources.**
- Sovol quotes sliding fits of 0.15–0.25 (PLA), 0.2–0.3 (PETG) and 0.25–0.35 (ASA) mm.
- Zbotic suggests 0.1–0.2 mm of design interference for bearing presses.
- UAL's fab-lab wiki suggests about 0.2 mm as a safe press starting point on Ultimakers.
- The spread between sources is ±0.1 mm. That is exactly why a **test coupon is mandatory**:
  print a ladder of holes, e.g. ⌀21.90–22.30 in 0.05 steps for a 608.

### 14.3 Printed feature recipes [typ/est. Verify on the target printer]

| Feature | Starting design value |
|---|---|
| 608 bearing pocket (OD 22, vertical axis) | ⌀22.05–22.15, depth 7.0 plus a 0.4 mm lip or clamp ring. Test a ladder |
| 625 pocket (OD 16) | ⌀16.05–16.15 |
| ⌀8 steel shaft, sliding in a printed hole | ⌀8.3–8.4, or print ⌀7.8 and ream or drill to ⌀8.0–8.1 for accuracy |
| ⌀8 shaft, press into print | ⌀7.9–8.0 (test) |
| ⌀5 NEMA17 shaft into a printed hub | Don't. Use a metal GT2 pulley or coupler with a set screw on the shaft flat |
| M3 clearance | ⌀3.4–3.6 |
| M3 self-tap into plastic | ⌀2.5–2.8 (PLA 2.6, PETG 2.7), engagement ≥ 2.5 × D, boss wall ≥ 1.5–2 mm |
| M3 hex nut trap (nut is 5.5 AF, 2.4 thick) | 5.7–5.8 AF, 2.6–2.8 deep |
| M4 nut trap (7 AF) | 7.2–7.3 AF |
| M5 nut trap (8 AF) | 8.2–8.3 AF |
| M3 heat-set insert (standard, e.g. CNC Kitchen or ruthex M3×5.7, OD about 4.6 knurl) | ⌀4.0 (range 3.9–4.2), depth ≥ insert length + 1 mm, wall ≥ 1.6 mm. **Use the insert datasheet** |
| M4 insert (about 5.6 OD knurl) | about ⌀5.6–5.7 per datasheet [not verified] |
| Printed threads | Only ≥ M8, or use coarse custom threads with 0.2–0.4 mm clearance. Prefer inserts and nuts |
| Snap fits | Strain ≤ about 2–4 % (PLA brittle: ≤ 2 %; PETG/PA ≤ 4–6 %); print the cantilever in the XY plane |
| Dowel / alignment pins between printed parts | Steel dowel ⌀3 or ⌀4 press into a ⌀(D − 0.05 to D + 0.05) hole, slip side D + 0.2 |
| Belt clamp teeth (GT2) | Use the published profile models; tooth clearance about 0.1 mm |

### 14.4 Rules for printed mechanisms [typ]
1. **Critical bores vertical** (axis along Z) for roundness. Orient for strength in the load
   direction (layer adhesion is the weak axis, at about 50–80 % of in-plane strength).
2. **Retain bearings mechanically.** Use a lip, a screw-on clamp ring or a slight chamfer
   snap. Interference alone creeps.
3. **Steel against plastic only where it is lightly loaded.** For shafts in bearings, use a
   metal shaft in a metal bearing inner ring. The print only holds the outer ring.
4. **Post-process precision features.** Ream or drill holes, and press bearings with a
   clamp, not a hammer, aligned with a bolt and washers.
5. **Hole compensation.** Some slicers offer "XY hole compensation" (PrusaSlicer, Orca). If you
   use it, design at nominal and state that you did.
6. **Tolerances on drawings of printed parts:** state the intended fit and the test, e.g.
   "608 press, tuned by coupon C1". Don't write H7.

### 14.5 Machined vs printed: decision table [typ]

| Need | Machined | Printed |
|---|---|---|
| Bearing seat for precision (runout < 0.02) | Yes: H7/k5 + ground shaft | No. Use a metal insert or bearing housing pressed into the print |
| Light-duty joint (hobby arm) | Overkill | Yes, with tested pockets and a clamp ring |
| Torque-transmitting shaft–hub | Key, D-flat + set screw, or s6 press | Metal hub (pulley or coupler) with set screw, bolted to the print |
| Tapped threads | Tapped (≥ 1.5 D in aluminium) | Heat-set insert or captured nut |
| Alignment of two parts | Dowels H7/m6 + slip F7 | Printed pegs ±0.2, or steel dowels in tuned holes |
| Large flat datum | Milled, ⏥ 0.05 | Flat only to about 0.1–0.3 mm. Use an aluminium plate as the base |

---

## 15. Common mistakes (checklist for review agents)

1. **Fits written on non-mating features**, or H7 called out on a printed or laser-cut hole.
2. **Hole-basis fit with an off-the-shelf shaft class ignored.** E.g. designing for g6 when the
   purchased rod is h6.
3. **The bearing's own negative tolerances forgotten.** The stack becomes tighter than
   intended.
4. **Both bearings on a shaft fixed axially**, so thermal growth preloads them.
5. **Shoulder fillet larger than the bearing chamfer.** The bearing doesn't seat and is cocked.
6. **Tap drill confused with clearance hole**, or the tap drill depth not given for blind holes.
7. **Metric 90° vs inch 82° countersink** mismatch.
8. **Square internal corners** on milled pockets.
9. **Chain dimensioning** of hole patterns. Use a datum or GD&T position.
10. **Square ±x/±y zones** where the fit really allows a circular zone. You lose 57 % of the
    usable area.
11. **RSS on 2–3 part prototype stacks.** Use worst case.
12. **Thermal effects ignored** in aluminium hubs on steel shafts (or vice versa).
13. **Screw length not checked.** It bottoms out in a blind hole, or engages less than 1.5 D in
    aluminium.
14. **Ra tighter than function needs** (e.g. Ra 0.4 on a cover).
15. **Printed press fits relied on long-term** in PLA near motors (60 °C+).
16. **No test coupon** before printing a big part with bearing pockets.
17. **Nominal printed hole for a heat-set insert taken from the screw size** instead of the
    insert datasheet.

---

## 16. Quick decision tables for agents

### 16.1 "What fit do I write?"

| Part pair | Machined | Printed |
|---|---|---|
| 608 on ⌀8 rotating shaft (light load) | Shaft ⌀8 h5/j5 (+Loctite 641) or k5 | Steel shaft; bearing slip + retaining compound or shaft collar |
| 608 in housing, outer stationary | ⌀22 H7 (or J7 for less play) | ⌀22.05–22.15 tested + clamp ring |
| Idler: bearings in a pulley on a fixed bolt | Bolt/shaft g6/h6; pulley bore N7/M7 | Bolt through; pulley pocket tested press |
| Locating dowel | Press H7 + m6 dowel; slip F7/G7 | Steel dowel in tested hole |
| Gear or pulley on a keyed shaft | H7/k6 | Metal hub, bolted |
| Sliding rod in a plain bush | H8/f7 or H7/g6 | Bronze/igus bush pressed into the print |
| Lid spigot or pilot diameter | H7/h6 or H8/f7 | +0.2–0.3 mm clearance |
| Permanent hub on shaft by friction | H7/s6 (check p, σ, T §1.7) | Don't. Use a mechanical lock |

### 16.2 "Which hole size do I model?" (metric, M2–M12)

| Thread | Tap drill (cut) | Form tap | Clearance (normal) | Clearance (printed) | SHCS counterbore ⌀ × depth | Heat-set insert hole |
|---|---|---|---|---|---|---|
| M2 | 1.6 | 1.8 | 2.4 | 2.4–2.6 | 4.4 × 2.2 | about 3.2 (datasheet) |
| M2.5 | 2.05 | 2.3 | 2.9 | 2.9–3.1 | 5.5 × 2.7 | about 3.6–4.0 (datasheet) |
| M3 | 2.5 | 2.8 | 3.4 | 3.4–3.6 | 6.5 × 3.3 | 4.0 (3.9–4.2) |
| M4 | 3.3 | 3.7 | 4.5 | 4.5–4.8 | 8.0 × 4.4 | about 5.6 (datasheet) |
| M5 | 4.2 | 4.6 | 5.5 | 5.5–5.8 | 10 × 5.4 | about 6.4 (datasheet) |
| M6 | 5.0 | 5.5 | 6.6 | 6.6–7.0 | 11 × 6.4 | about 8.0 (datasheet) |
| M8 | 6.8 | 7.4 | 9.0 | 9.0–9.4 | 15 × 8.6 | about 9.6–10 (datasheet) |
| M10 | 8.5 | 9.3 | 11.0 | 11–11.5 | 18 × 10.6 | — |
| M12 | 10.2 | 11.2 | 13.5 | 13.5–14 | 20 × 12.6 | — |

The heat-set insert holes for M2 and for M4–M8 are estimates. Confirm them on the insert
vendor's datasheet.

### 16.3 Verification table template (per _standards.md §5)

| Check | Expected | Got | PASS/FAIL |
|---|---|---|---|
| ⌀20 H7/g6 clearance range (computed vs ANSI B4.2 table) | +7…+41 µm | (agent fills) | |
| M6 tap drill = D − P | 5.0 mm | | |
| Stack-up WC ≤ requirement | gap ≥ 0.1 | | |

---

## Canonical references

**Standards (paid unless noted; summaries freely available)**
- ISO 286-1:2010 / ISO 286-2:2010: Limits and fits. https://www.iso.org/standard/45975.html (paid)
- ANSI B4.2: Preferred metric limits and fits (paid). Its preferred-fit table is widely
  reproduced.
- ISO 2768-1/-2: General tolerances (paid). Summary at https://www.engineersedge.com (free)
- ISO 273: Clearance holes for bolts and screws (paid). DIN 974: Counterbores (paid).
- ISO 261/262/965: Metric threads (paid). ASME B1.1: Unified threads (paid).
- ISO 4762: Socket head cap screws. Free dimension summaries:
  https://engineersedge.com/iso_socket_head_screw.htm,
  https://fasten.it/norms/norm/din_en_iso_4762
- ASME Y14.5-2018: Dimensioning and tolerancing (paid). ISO 1101, ISO 8015, ISO 5459 (paid).
- ISO 21920 / ISO 1302: Surface texture indication (paid).
- ISO 13715: Edges of undefined shape (paid).
- FED-STD-H28/2B: Screw-thread standards for federal services, including the thread
  engagement formula. **Free** (US government), e.g. via http://everyspec.com
- ABMA 7: Shaft and housing fits for metric radial ball and roller bearings (paid). Errata page:
  https://www.agma.org/wp-content/uploads/2026/03/Errata-Page_ANSI-ABMA-7-Mar-2026.pdf (free)

**Manufacturer catalogues and app notes (free)**
- SKF Rolling Bearings catalogue, sections "Selecting fits" and "Tolerances":
  https://www.skf.com (free PDF)
- NHBB engineering reference, shaft and housing fits:
  https://www.nhbb.com/knowledge-center/engineering-reference/ball-roller-bearings/shaft-housing-fits
- Sandvik Coromant formulas and definitions:
  https://www.sandvik.coromant.com/en-us/knowledge/machining-formulas-definitions (free)
- Harvey Tool / Helical "In the Loupe" speeds and feeds articles: https://www.harveyperformance.com
  (free)
- Misumi technical data (fits, shafts, linear bushings): https://us.misumi-ec.com (free)
- igus iglidur design guide: https://www.igus.com (free)
- Mitutoyo measurement basics: https://www.mitutoyo.com (free)

**Free online references**
- Roymech ISO tolerances (how to use):
  https://www.roymech.co.uk/Useful_Tables/ISO_Tolerances/how-to-use-iso-tolerances/
- cadforum.cz ISO tolerance tables: https://www.cadforum.cz/en/tolerance.asp (the column
  layout can be offset, so read carefully)
- Machining Doctor fit calculator (H7/g6 etc.):
  https://www.machiningdoctor.com/calculators/tolerances/
- Firgelli ISO 286 shaft/hole fit calculator:
  https://www.firgelliauto.com/en-de/blogs/engineering-calculators/shaft-hole-fit-calculator-iso-286
- Engineering Toolbox, machine process tolerance grades:
  https://www.engineeringtoolbox.com/machine-processes-tolerance-grades-d_1367.html
- Engineers Edge IT grade table: https://www.engineersedge.com/international_tol.htm
- TR Fastenings tapping and clearance sizes:
  https://www.trfastenings.com/Knowledge-Base/Engineering-Data/tapping-sizes-and-clearance-holes
- Optimas tapping sizes: https://optimas.com/technical-resources/tapping-sizes/
- AMES metric counterbore chart:
  https://amesweb.info/Screws/Metric-Counterbore-Hole-Dimensions-Chart.aspx
- Protolabs and Xometry design guides (CNC, sheet metal, 3D printing): https://www.protolabs.com,
  https://www.xometry.com (free)

**3D-printing fit references (free)**
- Sovol FDM tolerances and clearances:
  https://www.sovol3d.com/blogs/news/fdm-3d-printing-tolerances-clearances-how-to-design-parts-that-fit
- Zbotic press fits, threads and snap fits:
  https://zbotic.in/3d-printing-tolerances-designing-gaps-for-press-fits-threads-and-snap-fits/
- UAL CCI fab-lab clearance guide:
  https://wiki.cci.arts.ac.uk/books/digital-fabrication-lab/page/design-the-clearance-and-tolerance
- DigiKey Maker.io heat-set inserts (CNC Kitchen sizing method):
  https://www.digikey.com/es/maker/tutorials/2025/intro-to-freecad-part-4-how-to-use-heat-set-inserts
- CNC Kitchen heat-set insert tips and CAD models: https://www.cnckitchen.com (free)
- Prusa Knowledge Base: https://help.prusa3d.com (free)
- Kragujevac study on PETG printed bearing seats: https://scidar.kg.ac.rs/handle/123456789/22640

**Books and courses**
- *Machinery's Handbook* (Oberg et al., Industrial Press). The shop bible; paid.
- *Shigley's Mechanical Engineering Design* (Budynas & Nisbett): fits, press fits, threads;
  paid.
- Bryan R. Fischer, *Mechanical Tolerance Stackups and Analysis* (CRC); paid.
- Alex Krulikowski, *Fundamentals of GD&T*; paid.
- MIT OCW 2.008 Design and Manufacturing II (process capability, tolerances), **free**:
  https://ocw.mit.edu/courses/2-008-design-and-manufacturing-ii-spring-2004/
- MIT OCW 2.007 / 2.72 Elements of Mechanical Design (precision, fits), **free**:
  https://ocw.mit.edu/courses/2-72-elements-of-mechanical-design-spring-2009/
- Alexander Slocum, *FUNdaMENTALS of Design* (MIT), **free** PDFs:
  https://meddevdesign.mit.edu/

---

## Gaps / not verified

- **ISO 286 deviation tables (§1.2–1.3)** were reproduced from engineering memory and
  cross-checked only at selected points (⌀8 and ⌀20 H7/g6, H7/p6, H7/s6 against ANSI B4.2
  preferred-fit values and search summaries). Values for the c, d and u letters and for the
  K, M, N and P holes should be confirmed against an ISO 286-2 table before a drawing release.
  The u deviation changes inside the 18–30 mm band (split at 24 mm).
- **SKF shaft and housing recommendations (§2.3–2.4)** are summarised from memory of the SKF
  catalogue and from ABMA 7 snippets. SKF's own table was not fetched in this session.
- **Bearing ring tolerances (§2.2)** for Normal class are standard values but were not
  re-fetched from ISO 492.
- **The ISO 273 fine and coarse columns** come from Optimas (M2–M3) plus memory. The medium
  column was confirmed against TR Fastenings. Several web charts list M12 coarse as 15 mm; the
  ISO 273 value is believed to be 14.5 mm.
- **Counterbore diameters:** DIN 974 values from memory. AMES quotes slightly different values
  (M4 8.25, M5 9.75); the difference is ±0.25 mm.
- **Unified clearance-drill letters and numbers** are typical chart values and were not
  cross-checked in this session.
- **Heat-set insert hole sizes:** only M3 has a source (3.9 mm from DigiKey/CNC Kitchen; 4.0 mm
  is common vendor guidance). The M2 and M4–M8 values are estimates.
- **Feeds and speeds (§10)** are generic ranges. Tool maker data always overrides them. They
  were not re-checked against a specific Sandvik or Harvey table.
- **Printed fit values (§14)** vary ±0.1 mm between printers, slicers and materials. The
  sources conflict (interference vs clearance for presses). A test coupon is required.
- **IT grades by process (§6.1)** are consensus ranges. The Engineering Toolbox chart could not
  be read as text.
- **Surface finish table (§5.2)** is a consensus of commonly published ranges. The FDM, SLA and
  SLS Ra values are estimates.
- **The press-fit worked example (§1.7)** uses an assumed µ. The real friction coefficient
  varies from 0.07 to 0.25.
