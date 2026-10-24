# Design for Manufacturing (DFM): FDM 3D printing in depth, plus other processes

Reference for Mechy agents (concept, cad, docs) before choosing a process or drawing a part.
FDM (fused deposition modelling, also called FFF) gets the most depth because most Mechy parts are
printed on desktop printers. Other processes are summarised so agents can pick the right one and
avoid features a shop will reject.

Number labels used in this file:
- **[DS]** manufacturer datasheet or service-bureau design guide (cited)
- **[LIT]** published test or paper (cited)
- **[RoT]** widely repeated rule of thumb, cross-checked in 2+ sources
- **[EST]** estimate or engineering judgement, not verified for your printer. Test before relying on it.

Units: mm, N, MPa, °C unless stated. 1 MPa = 1 N/mm².

---

## 0. The 20 rules to remember (summary)

1. **Orient for the load, not for looks.** Layers are the weak plane. Put tensile/bending stress
   along the layers (XY), never across them (Z). Assume Z strength = 50% of XY unless tested. [RoT/LIT]
2. **Walls beat infill.** 3–4 perimeters (1.2–1.8 mm at 0.4 mm nozzle) plus 20–40% infill for general
   parts; 5–6 perimeters around bolt holes and load paths. [RoT]
3. **Holes print small, pins print big.** Vertical holes come out 0.1–0.3 mm undersize. Model holes
   +0.2 mm for a slip fit, or undersize them and drill/ream when the size matters. [RoT/DS]
4. **Horizontal holes need a teardrop or flat top** (45° roof), or they sag. [RoT]
5. **Clearances (diametral, FDM, 0.4 nozzle):** press 0 to −0.1 (test), snug 0.1, slide 0.2–0.3,
   free rotate 0.4–0.5, print-in-place gaps 0.3–0.5 mm per side. [RoT/EST]
6. **Always print a fit-test coupon** for bearing pockets, press-fits and inserts: 5 holes in 0.1 mm
   steps around nominal. Costs 10 minutes; saves a reprint of a 6-hour part.
7. **Overhang ≤ 45° from vertical, bridges ≤ 10–20 mm** unsupported. [RoT/DS]
8. **Use metal for threads.** Heat-set brass inserts (M3 hole ≈ 4.0–4.2 mm) or captive hex nuts.
   Never rely on threads printed or tapped in plastic for repeated assembly. [DS]
9. **Use metal for shafts and bearings.** Printed parts locate bearings; steel shafts carry them.
10. **PLA creeps and softens at ~55–60 °C.** A car interior, a motor mount next to a hot stepper (motors
    run 60–80 °C case), or a sustained clamp load all rule out PLA. Use PETG, ASA, or PA-CF. [DS]
11. **Carbon-fibre fill raises stiffness, lowers layer adhesion.** CF parts are stiff in XY, weak in Z. [DS]
12. **Chamfer the bottom edge 0.4–0.6 mm** to hide elephant's foot; it also helps mating parts seat.
13. **Minimum wall 0.8 mm (2 lines); structural walls ≥ 1.6 mm.** [RoT/DS]
14. **Warping scales with part length and material shrinkage.** ABS/ASA/nylon need an enclosure,
    brim, rounded corners. Keep long flat parts in PLA/PETG where possible.
15. **Split big or awkward parts** into printable pieces joined with screws, dowels, or dovetails, so
    each piece prints in its strongest orientation without supports.
16. **Use standard purchased parts** (bearings, shafts, GT2 pulleys, extrusions, fasteners) where
    precision matters. Print what is cheap to iterate.
17. **Pick a process by quantity:** 1–20 FDM; 10–500 SLS/MJF or CNC; 100–2000 urethane casting or
    aluminium-tool moulding; >1000–5000 injection moulding. [EST, see §15]
18. **CNC: internal corners always have a radius** (≥ 1/3 of pocket depth); pockets ≤ 4× tool
    diameter deep. [DS]
19. **Sheet metal: inside bend radius ≥ thickness; holes ≥ 2.5t + R from a bend.** [DS/RoT]
20. **Injection moulding: uniform walls 1–3.5 mm, draft ≥ 1°, ribs ≤ 60% of wall.** [DS]

---

## 1. FDM fundamentals: how a printed part carries load

### 1.1 Anatomy of a printed part

| Element | What it is | Typical setting (0.4 mm nozzle) | Effect on strength |
|---|---|---|---|
| Perimeters (walls, shells) | Outline loops of each layer | 2 (cosmetic) to 4–6 (structural); line width ~0.45 mm | Dominant for bending, torsion, and bolt bearing |
| Top / bottom layers | Solid skins | 4–6 layers (~0.8–1.2 mm at 0.2 mm layers) | Bending stiffness of plates; surface sealing |
| Infill | Internal lattice | 15–40%; gyroid, cubic, or grid | Supports skins, resists crushing; weak per gram |
| Layer height | Z step | 0.2 mm standard; 0.1–0.3 range | Thinner layers: finer detail, slightly better Z bond, longer print |
| Line width | Extrusion width | 100–120% of nozzle (0.42–0.48 mm) | Wider lines bond better, slightly stronger |

**Why walls beat infill.** Bending and torsion stress peaks at the outer surface (σ = M·c/I). Material
there does the most work. Infill sits near the neutral axis and carries little. Community tests (CNC
Kitchen tensile/bending series; Raspberry Pi HackSpace "Experiments with strong 3D prints") found extra
perimeters raised failure load more per gram than extra infill. In the HackSpace test, two extra
perimeters added about the same strength as roughly 10% more infill, using much less filament. [LIT/community,
cross-checked in 2 sources; exact numbers vary by setup]

**Rules:**
- General functional part: 3–4 walls, 5 top/bottom layers, 20–30% gyroid or cubic. [RoT]
- High-load part (arm link, motor bracket, gear hub): 5–6 walls, 40–60% infill, or make the cross
  section thin enough that it is solid perimeters (e.g. a 4 mm wall at 0.45 mm lines ≈ 9 perimeters). [EST]
- 100% infill is rarely the best use of plastic; a thicker section with more walls usually wins. [RoT]
- Around bolt holes, add local perimeters (slicer "modifier mesh" or make the boss wall ≥ 2–3 mm). [EST]
- Infill patterns: gyroid is near-isotropic and good for general use; grid/rectilinear is weak at
  crossings; honeycomb is slow; lightning is cosmetic-only (supports top skin, no strength). [RoT]

### 1.2 Anisotropy (the most important FDM fact)

A printed part is a laminate. Strength along a filament line ≈ bulk polymer. Strength across layers
depends on how well hot plastic welded to the cooler layer below.

| Direction | What fails | Typical strength vs XY | Source |
|---|---|---|---|
| XY, load along lines | Filament itself | 100% (reference) | — |
| XY, load across lines in one layer | Bead-to-bead bond | 80–95% | [EST] |
| Z (across layers) | Layer weld | PLA ~80%, ABS ~70%, PETG ~45% in one study; often 40–80% generally | [LIT] CSU Sacramento thesis (X build stronger than Z by 25% PLA, 42% ABS, 128% PETG) |
| Z, CF-filled | Layer weld, fibres do not cross layers | PLA-CF Z ≈ 15 MPa vs ~40 MPa for plain PLA (same vendor) | [DS] Polymaker PolyLite PLA-CF and PLA TDS |

Design value: **assume σ_Z = 0.5 × σ_XY** unless a datasheet gives a Z number. Halve allowable snap-fit
strain for Z-oriented beams (Fictiv). [RoT]

**Factors that improve layer adhesion** (each a few % to tens of %): [RoT/LIT]
- Hotter nozzle (top of the material's range), less part cooling fan (for PETG/ABS/ASA/PC).
- Wider lines and thinner layers relative to line width.
- Shorter layer time (small parts cool too fast between layers; print several at once).
- Enclosure for ABS/ASA/PC/nylon.
- Dry filament (wet PETG and nylon bond poorly and string).

### 1.3 Orientation decision procedure

1. Find the main load path and the main stress (tension, bending, torsion, bearing).
2. Orient so the stress acts along the layers. For a bending beam, lay the beam flat or on its edge,
   so the layers are parallel to the beam axis. **A cantilever arm printed standing up will snap at a
   layer line.**
3. Check: does the orientation need supports? If yes, can a split, a chamfer, or a 45° change remove
   them?
4. Check: which surfaces need accuracy? Holes are most accurate with their axis vertical (round in XY).
   Flat mating faces are best on the bed (bottom face) or as top skin.
5. Check: does the part fit the bed with a 5 mm margin, and is it under ~200 mm in the longest
   dimension for warp-prone materials? [EST]
6. If two needs conflict (e.g. a vertical boss and a horizontal beam), split the part.

**Orientation by part type** (typical Mechy parts):

| Part | Recommended orientation | Why |
|---|---|---|
| Arm link / beam | Flat on its widest face, long axis in XY | Bending along layers; bearing bores vertical and round |
| Motor mount plate (NEMA17) | Plate face down | Flat datum; screw holes vertical and round |
| L-bracket | On its side so the L shape is in the XY plane | The corner fillet is in-layer; printed upright, the corner peels apart |
| Bearing housing | Bore axis vertical | Round bore; seat face on bed |
| Spur gear | Face down (axis vertical) | Tooth roots in-layer; round profile |
| Pulley / idler | Axis vertical | Same |
| Shaft collar / clamp | Axis vertical; clamp screw horizontal with teardrop | Ring strength in-layer |
| Snap-fit hook | Beam in XY | Beam bends along layers |
| Long thin pin | Lying flat | A vertical pin < ~5 mm diameter is weak and wobbles while printing [DS-secondary] |
| Enclosure / box | Open side up | No supports; walls in-layer |

### 1.4 Sizing a printed part for strength (method)

Use ordinary beam formulas with **printed allowables**, not datasheet peaks.

Allowable stress (static, room temperature) [EST, conservative design practice]:
- σ_allow = σ_tensile(orientation) / SF, with SF = 3 for static known loads, 4–5 for shock, cyclic,
  or unknown loads; use the **Z value** if any stress crosses layers.
- For sustained loads in PLA (clamps, springs, preloaded joints) keep stress below ~20–25% of
  short-term strength because of creep. [EST]

Worked mini-example (cantilever arm link):
- PETG link, flat-printed, 20 mm wide (b) × 8 mm tall (h), length L = 150 mm, tip load F = 20 N.
- M = F·L = 20 × 150 = 3000 N·mm. Section modulus Z = b·h²/6 = 20 × 64 / 6 = 213 mm³.
- σ = M/Z = 14.1 MPa. PETG XY yield ~47 MPa [DS Prusament PETG TDS] → SF ≈ 3.3. OK for static.
- If the same link were printed standing up (layers across the span), use ~0.45 × 47 ≈ 21 MPa → SF
  1.5. **Not OK.** Re-orient.
- Deflection: δ = F·L³/(3·E·I). I = b·h³/12 = 853 mm⁴. E_PETG ~2000 MPa (estimate; printed parts with
  infill are 10–30% lower) → δ = 20 × 3.375e6 / (3 × 2000 × 853) = 13 mm. **Stiffness, not strength,
  usually limits printed arms.** Fix by making the section deeper (δ ∝ 1/h³), a tube/I-shape, or by
  using aluminium extrusion for long links.

Key insight: printed polymer E (~2–3.5 GPa) is ~25–35× lower than aluminium (69 GPa). Long printed
links sag and vibrate. For links > ~150 mm carrying a payload, consider a carbon tube or aluminium
extrusion with printed end fittings. [EST]

---

## 2. FDM materials

### 2.1 Comparison table

Values are typical ranges for printed test bars from reputable vendors. Brands vary by ±20%. Always cite
the specific filament's TDS when it drives a decision.

| Material | Tensile XY (MPa) | Tensile Z (MPa) | E (GPa) | Tg (°C) | HDT @0.45 MPa (°C) | Creep | Print difficulty | Use for |
|---|---|---|---|---|---|---|---|---|
| PLA | 45–60 | 30–40 [DS Polymaker PolyLite PLA Z 40.5; PolyMax PLA Z 32.4] | 2.5–3.5 | ~60 [DS Polymaker] | 55–60 [DS vendor, e.g. QIDI 57.6] | High (worst of common) | Easy | Prototypes, fixtures, indoor parts below ~45 °C, low sustained load |
| PETG | 40–50 [DS Prusament yield 47] | 20–35 (weak layer bond in some tests) [LIT] | 1.8–2.2 | ~80 | 68–72 [DS Prusament 68] | Moderate | Easy-medium (stringing) | Default functional material: brackets, housings, gears at light load |
| ABS | 35–45 | 25–35 | 1.8–2.3 | ~105 | 85–95 [EST] | Low-moderate | Hard (warp, fumes, enclosure) | Heat-tolerant parts, acetone smoothing |
| ASA | 35–45 | ~32 [DS Polymaker PolyLite ASA] | 1.8–2.2 | ~98 [DS Polymaker] | 90–95 [EST] | Low-moderate | Hard (warp, enclosure) | Outdoor/UV, near motors, heat |
| PC | 55–65 | 35–50 | 2.0–2.4 | ~145 | 110–135 [EST] | Low | Very hard (270 °C+, 100 °C+ bed) [DS Prusa] | Hot environments, tough parts |
| PA (nylon, unfilled) | 40–70 dry, 30–50 conditioned | 25–45 | 0.8–2.0 (drops a lot when wet) | 50–70 wet / higher dry | 80–110 [DS Polymaker PolyMide CoPA 111] | Moderate; wet nylon creeps more | Hard (dry 70–80 °C before print, warps) | Wear parts, living hinges, tough gears |
| PA-CF (PA6/PA12 + CF) | 70–100 [DS Bambu PAHT-CF 92 ± 7] | 30–50 [EST]; Z bending ~61 MPa PAHT-CF [DS] | 4–8 | — | 130–215 [DS Polymaker PA12-CF10 131, PA6-CF20 215; Bambu PAHT-CF 194] | Low | Medium-hard (hardened nozzle, dry) | Stiff, hot, structural parts: arm links, motor mounts |
| PETG-CF / PLA-CF | 40–60 | low (PLA-CF Z ~15 [DS Polymaker]) | 3–6 | as base | as base (PETG-CF up to ~96 for Prusament) [DS] | as base | Easy-medium (hardened nozzle) | Stiff, dimensionally stable, matte; not for Z loads |
| TPU 95A | 25–40 | 15–30 | 0.02–0.08 | <−20 | n/a | High (elastomer) | Medium (slow, direct drive) | Grippers, dampers, feet, belt tensioners, seals |

Sources: Polymaker TDS documents (wiki.polymaker.com), Prusament PETG TDS v1.1, Bambu Lab PAHT-CF
spec (via retailer reproductions), Prusa Filament Material Guide (print temperatures), CSU Sacramento
anisotropy thesis. Unfilled E values and ABS/ASA/PC HDT are [EST] from general vendor ranges.

Note: HDT at 0.45 MPa is a short-term softening point under light load. **Design max service
temperature ≈ HDT − 10–20 °C for loaded parts.** [EST]

### 2.2 Material selection decision table

| If the part... | Use | Avoid |
|---|---|---|
| Is a quick fit check / jig | PLA | — |
| Is a general mechanism part, indoors, below 50 °C | PETG | PLA if under sustained load |
| Touches or is near a stepper motor (case 60–80 °C) | ASA, PETG (marginal), PA-CF, PC | PLA |
| Sits in sun / outdoors | ASA | PLA, ABS (UV yellowing/embrittlement) |
| Must be stiff (long link, motor bracket) | PA-CF, PETG-CF, or thicker section | TPU, unfilled nylon |
| Sees wear / sliding / impact | Nylon (PA6, PA12) | PLA (brittle), CF grades on sliding faces (abrasive) |
| Needs to flex many times (living hinge, clip) | PP, nylon, PETG (some cycles) | PLA, CF-filled |
| Is a gripper pad, damper, foot, seal | TPU 85A–95A | — |
| Must hold a press-fit bearing long-term | PETG, ASA, PA-CF | PLA (creep relaxes the fit; may loosen over months) [EST] |
| Holds a constant clamping preload (screws in tension through plastic) | PA-CF, PC, PETG with metal washers/spacers | PLA |

### 2.3 Material handling notes

- **Moisture:** nylon, PA-CF, TPU, PETG, PC absorb water. Dry before printing (nylon/PA-CF ~70–80 °C,
  8–12 h; Bambu recommends 80 °C 8–12 h for PAHT-CF [DS]). Wet filament pops, strings, and loses Z
  strength. Store at < 20% RH. [DS]
- **Nylon mechanical properties drop when conditioned** (absorbs ambient moisture): PA-CF bending
  strength fell 12–18% (PAHT-CF) vs 40–45% (ordinary PA-CF) after water absorption [DS Bambu]. Design
  with "conditioned" values.
- **Abrasives:** CF/GF-filled filaments need hardened steel or ruby nozzles. Brass wears out in
  hundreds of grams. [RoT]
- **Fumes:** ABS/ASA (styrene), nylon, and PC need ventilation/enclosure filtering. [RoT]

---

## 3. FDM accuracy and tolerances

### 3.1 What a typical printer holds

| Printer class | Typical XY accuracy | Z accuracy | Source |
|---|---|---|---|
| Well-tuned desktop (Prusa MK4, Bambu X1/P1, Voron) | ±0.1–0.2 mm on features < 100 mm; ~±0.2–0.5% beyond | ±(layer height) | [EST/RoT] |
| Generic desktop (Hubs guidance) | ±0.5%, lower limit ±0.5 mm | — | [DS] Hubs FDM guide (as recalled; verify) |
| Industrial FDM (Stratasys) | ±0.15%, lower limit ±0.2 mm | — | [DS] Hubs FDM guide (as recalled; verify) |

Assembly clearance recommended by service guides: 0.2–0.4 mm. [DS secondary, Hubs/eduhk comparison]

### 3.2 Systematic errors and their fixes

| Error | Cause | Typical size | Design fix |
|---|---|---|---|
| Vertical holes undersize | Polygon facets in STL, plastic pulled inward on tight curves, over-extrusion | 0.1–0.3 mm on diameter; worse for small holes | Add +0.2–0.3 mm (CNC Kitchen tested M3 insert holes ~0.25 mm smaller than CAD) [DS]; use fine STL tessellation; or drill/ream |
| Outer dimensions oversize | Line width squish, over-extrusion | +0.05–0.2 mm | Calibrate flow; slicer XY compensation |
| Elephant's foot | First layer squished | 0.2–0.5 mm flare on bottom 0.2–0.6 mm | 0.4–0.6 mm × 45° chamfer on bottom edges; slicer elephant-foot compensation |
| Horizontal holes droop | Top of hole is a bridge/overhang | 0.2–0.5 mm sag at top | Teardrop (45° roof) or flat-top hole; drill out after |
| Shrinkage | Thermal contraction | PLA ~0.3%, PETG ~0.4%, ABS/ASA 0.5–0.8%, nylon 1–2% [EST] | Scale in slicer per material; anneal-shrink compensation |
| Warp / corner lift | Differential shrinkage | 0.1–2 mm on long parts | See §6 |
| Z-seam | Start/stop of each loop | Small bump 0.1–0.2 mm | Put seam at a non-mating edge ("rear" or "aligned" in a corner) |

### 3.3 Hole compensation

- **CAD tessellation:** export STL/3MF with chord tolerance ≤ 0.01 mm or angle ≤ 5°. A coarse polygon
  inscribed in a circle is undersize by r·(1 − cos(π/n)).
- **Polyholes (nophead/Hydraraptor method):** for small holes use a polygon with n = max(round(2·d), 3)
  sides, sized across the flats, plus a printer-specific "windage" (0.2–0.6 mm reported). [community,
  softsolder.com/hydraraptor; verify for your printer]
- **Practical defaults** for vertical holes (0.4 nozzle, PETG/PLA, calibrated) [EST]:

| Fit wanted | Model the hole at |
|---|---|
| Screw clearance (M3) | 3.4 mm (ISO medium is 3.4); M4 4.5; M5 5.5 |
| Slip fit on a shaft/dowel | d + 0.25 to 0.35 |
| Snug locating fit | d + 0.1 to 0.15 |
| Press fit on steel pin | d to d + 0.05 (or undersize 0.2 and ream to size) |
| Free-running clearance | d + 0.4 to 0.5 |

- **Precision method:** model the hole 0.2–0.5 mm undersize, then drill or ream with a real tool to
  final size. Hubs recommends drilling critical vertical holes. [DS] Reamer finish in PETG/ABS/PA is
  good; PLA can gum up (use a sharp tool at low speed).

### 3.4 Fit-test coupon (always do this)

Print a small plate (5–10 min) with the exact feature at nominal −0.2, −0.1, 0, +0.1, +0.2, +0.3 mm,
in the same material, orientation, and slicer profile as the real part. Label sizes with embossed
text. Pick the one that fits. Record the result in the project notes per printer/material.

---

## 4. Fits: press-fits, bearings, shafts, print-in-place

### 4.1 Clearance table (FDM, 0.4 nozzle, calibrated printer) [RoT/EST]

All diametral (total) unless noted.

| Joint | Clearance | Notes |
|---|---|---|
| Press fit, printed hole on steel part | 0 to −0.1 mm (test!) | Printed holes already shrink ~0.1–0.3; "nominal in CAD" is often already a press fit |
| Tight push fit | +0.1 mm | Assembles by hand, holds |
| Sliding fit (pin in hole, printed-to-metal) | +0.2–0.3 mm | |
| Printed-to-printed sliding (both FDM) | +0.3–0.4 mm | Two surfaces each have ±0.1 error |
| Free rotation | +0.4–0.5 mm | |
| Print-in-place hinge gap | 0.3–0.5 mm per side (radial), 0.3 mm layer gaps in Z | Fictiv: allow 0.1–0.3 mm for 3D printed snap gaps [DS] |
| Dovetail / tongue-groove | 0.15–0.2 mm per side | |

### 4.2 Press-fits into printed plastic

- Plastic relaxes (creeps) over time; a press fit loses grip, especially in PLA and when warm. Prefer
  a **press fit + positive retention** (shoulder, circlip, screw, glue, or a clamp slot). [RoT]
- Interference on diameter for printed hubs: 0.05–0.15 mm effective (after the hole's own shrinkage).
  More than ~0.2 mm risks splitting the boss along a layer line or seam. [EST]
- Boss wall around a press fit: ≥ 2.5–3 mm or ≥ 0.4 × bore diameter; put the Z-seam away from the
  thinnest wall. [EST]
- Use a 0.5 mm × 45° lead-in chamfer on the hole and the pin.
- **Crush ribs:** 3–6 small vertical ribs (0.3–0.5 mm tall) inside an oversize bore. The ribs deform and
  centre the part. Less sensitive to printer calibration than a plain bore. Good for bearings. [RoT]

### 4.3 Bearing pockets

Common bearings in Mechy designs:

| Bearing | ID × OD × W (mm) | Typical printed pocket (FDM, test it) |
|---|---|---|
| 608-2RS | 8 × 22 × 7 | 22.0–22.2 bore; community designs report 22.2–22.3 for press in PLA [community, MakerWorld]; a PETG study used 0.1–0.2 mm *undersize* housings for interference [LIT, scidar.kg.ac.rs, 6000-2RS] — printers differ, so test |
| 625ZZ | 5 × 16 × 5 | 16.0–16.2 |
| 623ZZ / F623ZZ | 3 × 10 × 4 | 10.0–10.2 |
| 6001 | 12 × 28 × 8 | 28.0–28.2 |
| 6800 / 61800 thin | 10 × 19 × 5 | 19.0–19.2 |
| 51105 thrust | 25 × 42 × 11 | 42.2–42.4 (loose; thrust bearings locate axially) |

Rules:
1. Bore axis vertical (round in XY). Seat face on the bed or on a flat top skin.
2. Provide a **shoulder** (step) for axial location: 1–1.5 mm wide, ideally contacting only the outer
   ring. Never let a printed face rub the inner ring or seal; add a 0.5 mm relief.
3. Through-bore behind the bearing so it can be pushed out (≥ ID + 4 mm hole). [EST]
4. Wall around the pocket ≥ 3 mm (608) and 4+ perimeters. [EST]
5. Use two bearings spaced ≥ 1–1.5 × shaft diameter apart (more is better, e.g. 2× for arms) to resist
   moment loads. Single bearings allow wobble. [RoT]
6. Shaft fit in bearing ID: use steel shafts (h6/g6 ground rod, or a bolt shank, not threads) —
   never a printed shaft for a real bearing. M8 bolt shank in 608: fine for low precision. [RoT]
7. Flanged bearings (F-series) drop into a counterbore and need no press fit; good for printed parts.

### 4.4 Shafts and pins in printed parts

- Printed pins < 5 mm diameter are weak and inaccurate; design a hole and insert a steel dowel or
  screw. [DS secondary]
- Torque transmission from a shaft to a printed hub: never rely on a round press fit. Use a D-flat with
  a grub screw on a captive nut or heat-set insert, a key, or a clamp hub (split hub + screw). For
  stepper 5 mm D-shafts use a metal pulley/coupler where torque > ~0.2 N·m. [EST]
- Hex shafts (e.g. 1/4" or 8 mm hex) in printed hex bores (+0.2 mm across flats) transmit torque well. [RoT]

---

## 5. Snap-fits and flexures

### 5.1 Cantilever snap-fit formulas

Source: Bayer/BASF snap-fit design manuals as summarised by Fictiv. [DS]

```
Root strain:        ε = 1.5 · t · Y / (L² · Q)          (Q ≈ 1 for a beam on a rigid wall)
Deflection limit:   Y_max = ε_allow · L² · Q / (1.5 · t)
Deflection force:   P = b · t² · E · ε / (6 · L)
Mating force:       W = P · (μ + tan α) / (1 − μ · tan α)

t = beam thickness at root (mm), L = beam length (mm), b = beam width (mm),
Y = hook depth / required tip deflection (mm), E = flexural modulus (MPa),
α = lead angle (insertion) or return angle (removal), μ = friction coefficient (~0.3–0.5 plastic on plastic [EST])
```

Allowable strain for printed parts [DS Fictiv]: ABS 7%, PLA 4–8%, Nylon 4–15%, SLA "ABS-like"
20–40%. **Halve these for beams loaded across layers.** For repeated use, design to ~50–60% of these
values. [EST]

My working defaults for FDM [EST]: PLA 2–3%, PETG 3–4%, ABS/ASA 3–5%, nylon 6–10% (one-time assembly);
half that for many cycles.

### 5.2 Worked example

PETG hook, beam in XY, L = 15 mm, t = 1.5 mm, b = 6 mm, hook depth Y = 1.0 mm, E ≈ 2000 MPa.
- ε = 1.5 × 1.5 × 1.0 / 225 = 0.010 = 1.0% → well under 3–4%. OK.
- P = 6 × 2.25 × 2000 × 0.01 / (6 × 15) = 3.0 N.
- Insertion with α = 30°, μ = 0.3: W = 3.0 × (0.3 + 0.577)/(1 − 0.173) = 3.2 N.
- If the same hook were printed with the beam vertical (Z), allowable halves to ~1.5–2%; 1.0% still
  passes but with a thin margin given layer-line notches. Prefer XY.

### 5.3 Snap-fit design rules

- Taper the beam (thickness at tip ≈ 0.5 × root) to spread strain; it nearly doubles allowable
  deflection for the same strain. [DS BASF/Bayer manuals]
- Root fillet ≥ 0.5 × t; never a sharp internal corner at the root. [DS Fictiv]
- Lead angle 25–35°. Return angle 90° = permanent (needs a release tool); 35–45° = removable. [DS Fictiv]
- Make L ≥ 5–10 × t for FDM cantilevers. Short stubby beams crack. [EST]
- Add 0.1–0.3 mm gap for printed snaps. [DS Fictiv]
- For anything opened often, use screws instead. Snap-fits in PLA fatigue quickly.

### 5.4 Living hinges and flexures

- FDM living hinges work in PP, nylon, TPU; PETG survives tens to hundreds of cycles; PLA fails. [RoT]
- Print the hinge with lines **along** the bend direction (lines cross the fold line), thickness
  0.3–0.6 mm (1–2 layers if horizontal; better: print on edge so it is 1–2 perimeters). [EST]
- Compliant flexure (e.g. for a gripper): stress σ = E · t / (2R) for a strip bent to radius R. Keep
  σ < 0.3 × yield for fatigue. [EST, standard beam theory]

---

## 6. Threads and fasteners in printed parts

### 6.1 Options ranked

| Method | Strength | Reusability | When |
|---|---|---|---|
| Heat-set brass insert | High (M3 ~1400 N pull-out in PLA, CNC Kitchen test) [DS] | Excellent | Default for anything assembled more than once |
| Captive hex nut (pocket or slot) | High (limited by plastic around nut) | Excellent | Cheapest; good where you can access the nut pocket |
| Through bolt + nut + washers | Highest | Excellent | Load-bearing joints (arm joints) |
| Self-tapping / thread-forming screw into a printed pilot | Medium | Poor (5–10 cycles) | Covers, low-load, non-serviced |
| Printed thread | Low | Poor | Only large threads (≥ M10, caps, jars) |
| Tapped hole in plastic | Low-medium | Poor | Avoid; acceptable in nylon/PC for low load |

### 6.2 Heat-set inserts

- Hole diameter: follow the insert maker. CNC Kitchen M3 standard insert: packaging says 4.0 mm (for
  drilled holes); for as-printed holes, 4.2 mm in CAD worked best; add 0.2–0.3 mm to datasheet value
  for printed holes. Pull-out fell sharply when the drilled hole exceeded ~4.1–4.2 mm. [DS CNC Kitchen
  "Are our heat-set insert datasheets wrong?"]
- Hole depth: insert length + ≥ 1 mm for displaced plastic. [DS secondary, DigiKey/FreeCAD tutorial]
- Wall around insert: ≥ 1.5–2 × insert OD total boss diameter, i.e. ≥ 1.5–2 mm wall; 3–4 perimeters. [EST]
- Install with a soldering iron fitted with an insert tip, set near the material's print temperature
  (much hotter melts a crater): PLA 200–220 °C, PETG 230–245 °C, ABS/ASA 240–260 °C. Push ~90% in with the iron,
  then flatten flush with a cold flat tool. [EST; CNC Kitchen technique]
- Insert axis vertical in print is best (round hole); horizontal inserts work with a teardrop or a
  slightly oversized hole.
- Typical CNC Kitchen-style sizes (verify with vendor) [DS, vendor sheets vary]:

| Thread | Insert OD (approx) | Length | Printed hole (CAD) |
|---|---|---|---|
| M2 | 3.6 | 3 | ~3.4 |
| M2.5 | 4.6 | 4 | ~4.0 |
| M3 short/standard | 4.6–5.0 | 3 / 5.7 | 4.0–4.2 |
| M4 | 6.3 | 8.1 | 5.6–5.8 |
| M5 | 7.1 | 9.5 | 6.4–6.6 |

(The OD/length column is [EST] from common vendor catalogs; always take the hole size from the
specific vendor's sheet.)

### 6.3 Captive nuts

ISO 4032 hex nuts (across flats s, thickness m):

| Nut | s (AF) | m | Printed hex pocket AF | Pocket depth |
|---|---|---|---|---|
| M3 | 5.5 | 2.4 | 5.7–5.8 | 2.6–3.0 |
| M4 | 7.0 | 3.2 | 7.2–7.3 | 3.4–3.8 |
| M5 | 8.0 | 4.7 | 8.2–8.3 | 4.9–5.2 |
| M6 | 10.0 | 5.2 | 10.2–10.3 | 5.4–5.8 |

Pocket clearances are [EST]. Options: a hex pocket from the face (nut pressed or pulled in by the
screw), or a side-entry slot (nut slides in from the side; good for mid-part locations). For a hex
pocket printed facing up, a "sacrificial layer" (one-layer bridge) over the hole lets the screw hole
start cleanly above the pocket; drill it out after.

### 6.4 Screws directly into plastic

- Pilot for thread-forming screws in FDM: ~0.8–0.85 × screw major diameter (M3 → 2.5 mm, M4 → 3.3 mm). [EST]
- Engagement ≥ 2 × d. Boss OD ≥ 2.5 × d. [RoT, from moulded-plastic boss rules]
- Do not over-torque: plastic strips easily; creep relaxes preload. Use washers under heads on plastic to
  spread bearing stress (bearing stress under an M3 head should stay < ~20 MPa in PETG). [EST]

### 6.5 Bolted joints through printed parts

- Preload in plastic relaxes. For joints that must stay tight (arm joints, motor mounts), use metal
  spacers/tubes through the plastic so the bolt clamps metal-to-metal, or use nyloc nuts and accept
  re-tightening. [RoT]
- Screw holes: model ISO 273 medium clearance (M3 3.4, M4 4.5, M5 5.5) plus 0–0.1 for printing.
- Counterbores for socket heads: M3 head 5.5 dia × 3 → counterbore 6.0–6.5 × 3.2; M4 7.0 → 7.5–8.0;
  M5 8.5 → 9.0–9.5. [EST]

---

## 7. Overhangs, bridges, supports, warping

### 7.1 Geometry limits (0.4 nozzle, 0.2 mm layers, good cooling) [RoT/DS]

| Feature | Limit | Source |
|---|---|---|
| Overhang angle (from vertical) without support | ≤ 45° (55–60° possible with good cooling, rough underside) | [DS] Hubs |
| Bridge length unsupported | 10–20 mm clean; 50+ mm possible with sag | [DS secondary] |
| Minimum wall (vertical) | 0.8 mm (2 lines); 1.2–1.6 mm for structural | [DS secondary] |
| Minimum feature/pin diameter | ~1–2 mm (weak); use metal below 5 mm for load | [DS secondary] |
| Minimum hole (vertical) | ~2 mm (drill smaller) | [EST] |
| Embossed/engraved text | ≥ 0.6 mm line width, ≥ 0.4–0.6 mm depth; ≥ 5 mm tall | [EST] |
| Minimum gap between parts printed together | 0.3–0.5 mm | [EST] |

### 7.2 Designing out supports

1. Replace horizontal overhangs with 45° chamfers (not fillets) on downward-facing edges.
2. Horizontal holes: teardrop (pointed top at 45°) or flat-top (bridge).
3. Counterbore on the underside: use a sacrificial bridge layer or "stepped bridging" (two
   perpendicular bridge layers making the hole square then round).
4. Split the part at the overhang and join with screws/dowels.
5. Rotate the part so the overhang becomes a vertical wall.
6. When supports are needed, put them on non-critical faces; supported faces are rough (~0.2–0.5 mm). Tree/
   organic supports remove more cleanly on curved parts.

### 7.3 Warping

Cause: each new layer shrinks as it cools, pulling up the edges of the layers below. Worse with high
shrink materials (ABS, ASA, nylon, PC), long parts, sharp corners, and large solid areas. [RoT]

Mitigation (design + process):
- Round outside corners (R ≥ 3–5 mm) on the footprint; sharp corners lift first.
- Avoid large solid bottom slabs; use ribs or lower infill.
- Brim 5–10 mm, or "mouse ears" (thin disks) at corners.
- Enclosure at 40–60 °C for ABS/ASA/nylon/PC; no drafts; reduce fan.
- Bed adhesion: textured PEI for PETG/ABS; glue stick for nylon; correct bed temperature.
- For ABS/ASA, keep parts under ~150–200 mm long without an actively heated chamber. [EST]
- Split long parts and join them.

---

## 8. Gears, pulleys and belts

### 8.1 Printed gears

- **Module:** ≥ 1.0 for light loads; 1.5–2.0 for robot joints in PETG/nylon. [community examples, no
  authoritative minimum found] Smaller modules print with rounded teeth and backlash.
- **Pressure angle:** 20° (standard; stronger root than 14.5°).
- **Backlash:** add 0.1–0.2 mm (centre distance + ~0.1 mm or tooth thinning). FDM perimeters expand in
  XY and zero-backlash CAD gears bind. [community]
- **Minimum teeth:** 17+ for 20° to avoid undercut (standard gear theory); 12–14 with profile shift.
- **Orientation:** face down (axis vertical). Herringbone or double helical gears are self-centering,
  quieter, and print without supports when the apex is mid-height.
- **Material:** nylon (best wear), PETG or POM (if available). PLA works for low duty but wears and
  softens. CF-nylon is stiff but abrasive on mating gears. [RoT]
- **Infill:** solid teeth (enough perimeters that the tooth is solid: e.g. 4+ walls for m1.5). [EST]
- **Hub:** metal hub or clamp; round-shaft press fit will slip.
- **Strength check (Lewis equation)** — standard gear theory:

```
σ_b = F_t / (b · m · Y)
F_t = 2·T / d,  d = m·z   (tangential force at pitch circle, N; T in N·mm)
b = face width (mm), m = module (mm), Y = Lewis form factor (≈0.29–0.32 for z = 17–20, ≈0.35 for z = 30, ≈0.42 for z = 60, 20° full depth)
```

Allowable bending stress for printed teeth [EST]: PLA/PETG ~8–15 MPa, nylon ~10–20 MPa, PA-CF ~20–30 MPa
for light cycles; much less for continuous running (heat build-up). Treat these as unverified.

Worked example: m = 1.5, z = 20 pinion (d = 30 mm), b = 10 mm, PETG, T = 1.0 N·m = 1000 N·mm.
F_t = 2 × 1000 / 30 = 66.7 N. Y ≈ 0.32. σ = 66.7 / (10 × 1.5 × 0.32) = 13.9 MPa. Marginal for PETG.
Increase face width to 15–20 mm, use m = 2, or use nylon.

**Mechy default:** for motor-to-joint reduction prefer GT2 belts (with metal pulleys) or a printed
cycloidal/planetary only after checking tooth stress. Belts tolerate printer inaccuracy better.

### 8.2 Belts and pulleys

- Buy GT2 aluminium pulleys for motor shafts (16T, 20T). Printed small pulleys (< 30 teeth) have poor
  tooth form. Large printed driven pulleys (60–120T) work fine in PETG/ASA if printed axis-vertical. [RoT]
- Printed idlers: use bearings (F623ZZ or 625ZZ) with printed flanges; smooth idlers on the belt back. [RoT]
- Belt clamp: tooth-shaped clamp pocket matching the GT2 profile (2 mm pitch) plus a screw; never
  rely on friction only. [RoT]
- Tensioner: slotted motor mount or an idler on a slot; give ≥ 5–10 mm adjustment. [EST]

---

## 9. Post-processing

| Process | What it does | Typical change | Notes |
|---|---|---|---|
| Drilling / reaming | True hole size | Hole to ±0.02–0.05 mm | Best for bearing seats, dowels. Model 0.2–0.5 undersize first |
| Heat-set inserts | Metal threads | — | §6.2 |
| Annealing (PLA, PETG, nylon) | Crystallises; raises heat resistance | PLA HDT can rise toward 80–100 °C; shrinks XY a few %, grows Z | Dimensional change is the problem; scale before printing or use annealing-specific PLA (e.g. HTPLA). [EST, vendor claims] |
| Vapour smoothing (ABS/ASA with acetone) | Glossy, seals layers | Loses ~0.05–0.1 mm on edges | Softens fine features; ventilate |
| Sanding / filler primer | Cosmetic | Removes 0.05–0.2 mm | Not for mating faces |
| Epoxy coating (XTC-3D etc.) | Smooth, seals | Adds 0.1–0.3 mm | Cosmetic, waterproofing |
| Bead blasting (SLS/MJF) | Removes powder, uniform finish | ~0.05 mm | Standard for powder parts |
| Dyeing (SLS/MJF nylon) | Colour | — | |
| Support removal | — | Leaves 0.2–0.5 mm scars | Plan supported faces as non-critical |
| Gluing | Join split parts | — | PLA: CA or epoxy; PETG: epoxy (poor CA bond); ABS/ASA: acetone/ABS slurry weld; nylon: hard to glue (mechanical joints) |

---

## 10. Other additive processes: SLA, SLS, MJF

### 10.1 Comparison

| Property | FDM (desktop) | SLA / MSLA (resin) | SLS (nylon powder) | MJF (HP, nylon powder) |
|---|---|---|---|---|
| Typical accuracy | ±0.1–0.5 mm | ±0.05–0.15 mm [EST] | ±0.3%, ±0.3 mm [EST] | ±0.2 mm up to 100 mm, ±0.2% beyond (after bead blast) [DS bureau citing HP] |
| Min wall | 0.8 mm | 0.2 mm (Form 3/4, supported or unsupported) [DS Formlabs]; older printers 0.4–0.6 | 0.7–1.0 mm | 0.5–1.0 mm (1.0 recommended; thicker for bigger parts) [DS bureaus] |
| Supports | Yes for > 45° | Yes (marks); max unsupported overhang ~5 mm [DS Formlabs] | None (powder supports) | None |
| Clearance, assembled/moving | 0.3–0.5 mm | 0.2–0.5 mm | 0.4–0.6 mm moving [DS bureau] | 0.6 mm moving; 0.7 mm for parts printed assembled [DS bureau/HP-titled guide] |
| Anisotropy | Strong (Z weak) | Low | Low (Z ~80–95%) [EST] | Low |
| Escape holes for hollow | n/a | ≥ 3–3.5 mm drain holes [EST, Formlabs advice] | ≥ 2.5–5 mm | ≥ 2.5 mm [DS bureaus] |
| Typical materials | PLA, PETG, ABS, PA-CF, TPU | Standard (brittle), Tough, Durable, High-temp, Flexible | PA12, PA11, TPU, GF-PA | PA12, PA11, PP, TPU |
| Strength (PA12) | — | Tough resins ~40–55 MPa | PA12 ~45–50 MPa, E ~1.7 GPa [EST] | PA12 ~48 MPa, E ~1.8 GPa [EST, HP spec as recalled] |
| Best for | Cheap iteration, big parts | Fine detail, smooth, small parts, moulds | Functional nylon parts, assemblies, small batch | Same as SLS; better consistency, grey/black |
| Cost driver | Print time, grams | Resin volume, height, post-cure | Bounding box / packing density, build height | Same as SLS |

### 10.2 SLA design rules

- Standard resins are brittle (elongation 5–10%) and creep and yellow under UV; use "Tough" or
  "Durable" resins for snap fits or impacts. [RoT]
- Hollow parts need drain holes or trapped resin cracks the part later.
- Avoid large flat cross-sections parallel to the build plate (suction/peel forces); tilt parts 15–45°. [RoT]
- Post-cure changes dimensions slightly; design fits after testing cured parts.

### 10.3 SLS/MJF design rules

- No supports: put complex internals, print-in-place hinges, chains freely (keep 0.6+ mm gaps).
- Avoid thick solid sections (> ~10–15 mm): heat accumulates, shrink sinks. Core out with 2–3 mm walls. [DS bureau]
- Bureau pricing is often by bounding box volume or packed volume; compact, nestable parts are cheaper.
- Threads: tap M4+ directly in PA12, or use heat-set inserts (work well in nylon).
- Excellent for Mechy small-batch (10–200) of final parts: isotropic, tough, no warping concerns.

---

## 11. Laser cutting

| Item | Typical value | Source |
|---|---|---|
| Kerf, CO2 laser (wood, acrylic, thin metal) | 0.25–0.5 mm (0.010–0.020") | [DS SendCutSend] |
| Kerf, fiber laser (metal) | 0.15–1.0 mm (0.006–0.040"), grows with thickness | [DS SendCutSend] |
| Tolerance (bureau) | ±0.13 mm (±0.005") on most materials | [DS SendCutSend] |
| Min hole / slot / bridge | ≥ 50% of material thickness; nothing below ~0.4 mm | [DS SendCutSend] |
| Min hole for CNC-routed sheet (wood, composites) | 3.2 mm (0.125") (tool size) | [DS SendCutSend] |
| Hole-to-edge distance | ≥ 1 × thickness (≥ 2× in brittle acrylic) | [EST] |

Rules:
1. Bureaus compensate kerf automatically on outlines; for **self-cut** parts (hobby CO2), offset
   outlines by kerf/2 or tab-slot joints will be loose.
2. Tab-and-slot joints for flat-pack frames: slot width = sheet thickness + 0.05–0.1 mm (measure the sheet;
   plywood varies ±0.3 mm). [EST]
3. Acrylic (PMMA) cracks from stress concentrations and solvent; use radii ≥ 1 mm on inside corners and
   avoid press fits. Cast acrylic cuts cleaner than extruded. [RoT]
4. Never laser-cut PVC or polycarbonate on a CO2 laser (chlorine gas; PC burns/yellows). [RoT]
5. Cut parts are 2D; add bends (sheet metal, §13), tapped holes, or countersinks as secondary ops.
6. Cost driver: cut length (perimeter) + pierces + material area. Fewer small holes = cheaper.
7. Common Mechy uses: aluminium 3–6 mm plates for motor mounts and base plates (stiffer and more accurate
   than printed), acrylic covers, plywood prototypes of frames.

---

## 12. CNC machining (milling and turning)

### 12.1 Milling rules [DS Hubs CNC guide, cross-checked with Yijin and Core77]

| Feature | Recommendation |
|---|---|
| Internal vertical corner radius | ≥ 1/3 of cavity depth; slightly larger than tool radius (+~1 mm) so the tool arcs, not stops; min R0.5 |
| Pocket depth | ≤ 4 × pocket width (or tool diameter); 3–4× is typical, up to ~6× at higher cost |
| Wall thickness | ≥ 0.8 mm metal (0.5 feasible), ≥ 1.5 mm plastic (1.0 feasible) |
| Hole diameter | Use standard drill sizes; depth ≤ 4× diameter typical, up to 10× possible |
| Thread length | 1.5–2× d useful engagement; > 3× d adds nothing; leave ~0.5× d unthreaded at a blind hole bottom |
| Smallest thread | M2–M3 common; M6 is easy |
| Standard tolerance | ±0.1–0.125 mm; tight ±0.025 mm costs more |
| Text | Engraved (not embossed), ≥ 20 pt sans-serif |
| Undercuts | Avoid, or use standard T-slot / dovetail cutter dimensions |
| Setups | Each additional fixture orientation adds cost; design so most features are reached from one or two sides |

Other rules:
- Sharp internal corners are impossible; if a square part must fit in a pocket, add "dog-bone" or
  "T-bone" corner reliefs. [RoT]
- Outside corners can be sharp; add a small chamfer (0.5 mm × 45°) to break edges anyway.
- Specify tight tolerances only on functional features (bearing bores, dowel holes); call out the rest
  at ISO 2768-m (general tolerance standard). [RoT]
- Bearing bores in aluminium: H7 housing for a light interference/transition fit with a standard
  bearing OD (e.g. 22 mm H7 = 22.000 to +0.021). [DS ISO 286 values]
- Materials: 6061-T6 aluminium is the default (cheap, machines well); 7075 for strength; 303/304
  stainless for corrosion; POM (Delrin) for low-friction plastic parts; brass for small precision parts.
- Cost drivers: machining time (material removal, small tools, deep pockets), setups, tolerances,
  material, finishing (anodise). Hard materials (stainless, titanium) cost 2–5× aluminium time. [EST]

### 12.2 Turning (lathe) rules [RoT/EST]

- All features coaxial; non-axial features (flats, cross holes) need milling (live tooling) — cost up.
- Length/diameter > ~4–8 needs tailstock or steady support; slender shafts deflect and chatter.
- Add a thread relief groove (undercut) at a shoulder so the thread runs out cleanly.
- Add chamfers to shaft ends and edges (0.5 × 45°) for assembly.
- Shoulder fillet radius ≤ the bearing's corner chamfer so the bearing seats flat.
- Standard bar stock sizes save cost (design ODs at stock size where the surface is not critical).
- For Mechy: ground shafts (h6, linear rod) are cheaper to buy than to turn; turn only shoulders,
  grooves for circlips (DIN 471), and D-flats.

---

## 13. Sheet metal

### 13.1 Key rules

| Feature | Rule | Source |
|---|---|---|
| Inside bend radius | ≥ 1 × t for steel/5052 aluminium; 6061-T6 needs ≥ 2–3 t or cracks (use 5052-H32 for bent parts) | [RoT] |
| Standard tooling radius (Protolabs) | 0.76 mm (0.030") for t ≤ 3.2 mm (1/8"); cheapest to keep | [DS Protolabs] |
| Minimum flange length | ≥ 4 × t (commonly; check bureau) | [RoT] |
| Hole to bend distance | ≥ 2.5 t + R (holes); slots ≥ 4 t + R | [RoT, cross-checked] |
| Hole to edge | ≥ 1/16" (1.6 mm) for t ≤ 0.036"; ≥ 1/8" (3.2 mm) otherwise | [DS Protolabs] |
| Minimum hole diameter | ≥ t (≥ 1.2 t for stainless) | [RoT] |
| Bend relief | Width ≥ t; depth ≥ R + t beyond bend line | [RoT; Protolabs adds reliefs ≤ R + t] |
| Bend angle tolerance | ±1° typical | [DS Protolabs] |
| Bends in a line | Keep bend lines on the same part parallel/aligned where possible; each new bend orientation adds handling | [RoT] |
| Hardware | PEM self-clinching nuts/studs/standoffs: follow PEM min sheet thickness and edge distance | [DS PEM catalogue] |

### 13.2 Flat pattern: bend allowance and K-factor

```
Bend allowance:  BA = θ · (R + K · t)              θ in radians, R = inside radius, t = thickness
Outside setback: OSSB = tan(θ/2) · (R + t)
Bend deduction:  BD = 2 · OSSB − BA
Flat length = sum of outside flange lengths − (number of bends × BD)
K = position of neutral axis as a fraction of t from the inside face (0 < K < 0.5 for air bending)
```

Typical K-factors (air bending): 0.33–0.50, average ~0.44; mild steel ~0.33–0.45, 6061 Al ~0.42,
copper ~0.45; lower for tight radii (R < t), toward 0.5 for large radii (R > 3t). Bottoming 0.5–0.67. [DS
multiple secondary sources disagree; use your bureau's value — they publish K or bend deduction tables]

Worked example: 90° L-bracket, 2 mm mild steel, R = 2 mm, K = 0.42, outer flanges 30 mm and 40 mm.
- θ = π/2 = 1.571. BA = 1.571 × (2 + 0.42 × 2) = 1.571 × 2.84 = 4.46 mm.
- OSSB = tan(45°) × (2 + 2) = 4.0 mm. BD = 8.0 − 4.46 = 3.54 mm.
- Flat length = 30 + 40 − 3.54 = 66.46 mm.

### 13.3 Sheet-metal decision notes

- Gauge choice for robot brackets: 1.5–3 mm aluminium 5052 or 1–2 mm steel. [EST]
- Bureaus (SendCutSend, Protolabs, Xometry) quote instantly; cheap from ~1 part. Often cheaper and much
  stiffer than a printed bracket above ~5 parts or for motor mounts. [EST]
- Add stiffening: flanges, beads, or hems rather than thicker sheet.

---

## 14. Injection moulding basics

### 14.1 Rules [DS Protolabs unless noted]

| Feature | Guideline |
|---|---|
| Wall thickness | Material dependent (Protolabs table): ABS 1.1–3.6 mm; nylon 0.8–2.9; PC 1.0–3.8; PP 0.9–3.8; acetal 0.8–3.0; PE 0.8–5.1 |
| Uniformity | Keep walls uniform; transitions gradual (3:1 taper), variation ≤ ~15–25% [RoT] |
| Draft | 0.5° minimum on vertical faces; 2° for most; 3° for shut-offs and light texture; 5°+ heavy texture |
| Ribs | Thickness ≤ 60% of nominal wall (prevents sink) [DS Protolabs]; height ≤ 3× wall; spacing ≥ 2× wall; 0.5–1° draft [RoT] |
| Bosses | OD ≈ 2–2.5× hole ID; wall ≤ 60% of nominal; connect to walls with ribs; core out [RoT] |
| Corners | Inside radius ≥ 0.5 t, outside = inside + t (keeps wall uniform) [RoT] |
| Undercuts | Avoid; or use side actions/lifters (cost) or bump-offs; design snap-fits with pass-through cores |
| Tolerance | Machining ±0.08 mm plus resin shrink tolerance ≥ ±0.002 mm/mm |
| Gate & parting line | Leave a flat area for the gate; expect a parting line witness and ejector-pin marks |
| Text | Raised text on part = engraved in mould (cheaper) |

### 14.2 Cost and tooling

- Tooling: aluminium prototype tools ~$1.5k–$10k (thousands to tens of thousands of shots); hardened
  steel production tools $10k–$100k+ (100k–1M+ shots). [EST, industry ranges]
- Part price: cents to a few dollars, driven by cycle time (thickest wall sets cooling time ∝ t²),
  material, cavities.
- Lead time: 2–6 weeks (rapid), 8–16 weeks (production steel). [EST]
- Design printed parts with moulding in mind if volume will grow: constant walls, draft, ribs instead of
  solid bulk — this also prints well on FDM.

---

## 15. Aluminium extrusion framing (2020, 2040, etc.)

### 15.1 Common profiles [EST from vendor datasheets; verify per supplier]

| Profile | Slot | T-nut / screw | End hole (tap) | Ix (cm⁴) | Mass (kg/m) |
|---|---|---|---|---|---|
| 2020 (B-type slot 6, Misumi HFS5, V-slot 2020) | 6 mm opening | M5 (M4/M3 possible) | 4.2 mm → tap M5 | ~0.70 (both axes) [DS generic 2020 datasheet 0.72; deflection guide 0.70] | ~0.45–0.55 |
| 2040 | 6 | M5 | 2× 4.2 → M5 | ~4.8 strong / ~1.2 weak [DS deflection guide; units/axes vary between sources] | ~0.8–0.9 |
| 3030 (slot 8) | 8 | M6 | 6.8 → M8 or 5.0 → M6 | ~2.5–3 | ~0.8–0.9 |
| 4040 (slot 8 or 10) | 8–10 | M8 | 6.8 → M8 | ~8–10 | ~1.4–1.6 |

Aluminium 6063-T5/T6, E ≈ 69 GPa.

### 15.2 Deflection check (worked)

Simply supported 2020, span L = 500 mm, centre load F = 100 N, I = 0.70 cm⁴ = 7000 mm⁴:
δ = F·L³ / (48·E·I) = 100 × 1.25e8 / (48 × 69 000 × 7000) = 0.54 mm.
Cantilever 300 mm, tip 20 N: δ = F·L³/(3EI) = 20 × 2.7e7 / (3 × 69 000 × 7000) = 0.37 mm.
Compare: the same 2020 profile vs a solid PETG 20×20 bar (E 2 GPa, I 13 333 mm⁴): the extrusion is
~18× stiffer.

### 15.3 Framing rules [RoT]

- Joints: corner brackets (cheap, adds clutter), blind joints (tap the end M5, drill a 5–7 mm access
  hole in the mating profile for a hex key; clean and very rigid), printed corner cubes (prototypes).
- T-nut types: drop-in (spring-loaded, insert after assembly), slide-in (must be loaded before closing the
  frame — **count them before assembly**), hammer-head/roll-in.
- Specify cut lengths with ±0.2–0.5 mm tolerance and square ends; bureaus (Misumi) cut to 0.5 mm and
  tap ends to order. [EST]
- Use V-slot profiles with POM wheels for simple linear motion; use MGN linear rails for precision.
- Printed parts that clamp onto extrusion: mate to the slot with a 0.2 mm clearance tongue (slot width
  6.2 mm → 6.0 mm tongue) to locate squarely. [EST]
- Screw lengths into T-nuts: plate thickness + 4–6 mm for M5 into slot 6 T-nuts (do not bottom out in the
  slot). [EST]

---

## 16. Choosing a process: quantity, cost drivers, decision table

### 16.1 Cost drivers per process

| Process | Fixed (setup/tooling) | Variable cost driven by | Sweet spot quantity [EST] |
|---|---|---|---|
| FDM (in-house) | ~0 | Print hours (~$0.3–1/h machine) + grams (~$20–40/kg) + failure rate | 1–50 |
| FDM (bureau) | Small | Volume, material, hours | 1–20 |
| SLA | ~0 | Resin volume, build height, post-processing labour | 1–100 (small parts) |
| SLS / MJF | ~0 | Bounding box / packed volume; part count per build | 10–1000 |
| Laser cutting | Small (file setup) | Cut length, pierces, material area | 1–10 000 |
| Sheet metal (cut + bend) | Small | Number of bends, setups, hardware insertion | 1–10 000 |
| CNC milling | Programming + fixtures ($50–300 per design) [EST] | Machine time, setups, tolerances, material | 1–1000 |
| CNC turning | Setup | Cycle time | 10–100 000 |
| Urethane (vacuum) casting | Silicone mould ($300–1500) [EST] | Labour per shot; mould life ~20–25 parts | 10–200 |
| Injection moulding | Tool $1.5k–100k+ | Cycle time, material | 1000+ (500+ with aluminium tooling) |
| Extrusion framing (buy) | ~0 | Length, cutting, tapping | Any |

### 16.2 Break-even formula

```
N* = (Tooling_B − Tooling_A) / (Unit_A − Unit_B)
```
Example [EST numbers]: FDM bracket $4/part, no tooling; injection moulded $0.40/part with a $6000
aluminium tool. N* = 6000 / (4 − 0.40) ≈ 1670 parts. Below ~1700, print (or MJF); above, mould.

### 16.3 Decision table: "use X when..."

| Situation | Use |
|---|---|
| First prototype, 1–5 parts, geometry still changing | FDM PLA/PETG |
| Functional robot part, low volume, needs heat/stiffness | FDM PA-CF or ASA |
| Fine detail, small, smooth (< 50 mm), low load | SLA (tough resin) |
| 10–500 durable nylon parts, complex shapes, assemblies | MJF / SLS PA12 |
| Flat plate needing stiffness/accuracy (motor plate, base) | Laser-cut aluminium (3–6 mm) |
| Bent bracket, enclosure, chassis, > 5 parts | Sheet metal |
| Precision bore, shaft, high-load joint, thermal path | CNC aluminium |
| Round parts (spacers, shafts with shoulders, pulleys) | CNC turning (or buy standard) |
| Structural frame, > 200 mm members | Aluminium extrusion (2020/2040) |
| 1000+ identical plastic parts | Injection moulding |
| Small batch with moulded look (cosmetic covers) | Urethane casting |

---

## 17. FDM part review checklist (run before exporting STLs)

Geometry
- [ ] Print orientation chosen and stated; main stresses lie in XY.
- [ ] No unsupported overhang > 45°; bridges ≤ 15 mm; or supports planned on non-critical faces.
- [ ] Horizontal holes are teardrops or flat-topped.
- [ ] Bottom edges chamfered 0.4–0.6 mm (elephant's foot).
- [ ] Walls ≥ 1.6 mm on load paths; ≥ 0.8 mm anywhere.
- [ ] Footprint corners rounded for warp-prone materials.
- [ ] Part fits the bed with margin; long parts split if > ~200 mm in ABS/ASA/nylon.

Fits and hardware
- [ ] Every hole has an intent (clearance / slip / press / insert) and a compensated CAD size.
- [ ] Bearing pockets: shoulder, push-out hole, ≥ 3 mm wall, fit coupon planned.
- [ ] Threads via heat-set inserts or captive nuts, with hole sizes from the vendor sheet.
- [ ] Torque into shafts via D-flat + set screw, clamp, key, or hex — not round press fit.
- [ ] Bolted joints that need preload have metal spacers or are accepted as "re-tighten".
- [ ] Screw lengths checked against insert depth / nut pocket / T-nut.

Material and loads
- [ ] Material chosen with temperature check: service temp ≤ HDT − 15 °C.
- [ ] Stress check with σ_allow = σ_orientation / SF (SF 3–5), Z value used if stress crosses layers.
- [ ] Deflection check (E_printed ~2–3.5 GPa; CF 4–8 GPa).
- [ ] Creep considered for sustained loads (PLA → no).

Documentation (Mechy standard)
- [ ] print_list.csv row: part, qty, material, orientation, est. grams, walls/infill.
- [ ] Fit coupon STL included where fits matter.

---

## 18. Common mistakes (and the fix)

| Mistake | Consequence | Fix |
|---|---|---|
| Arm link printed standing up | Snaps at layer line | Print flat; split if needed |
| Bearing bore modelled at exactly 22.000 without testing | Too tight or loose | Fit coupon; crush ribs |
| PLA motor mount | Sags / loosens as motor heats to 60–80 °C | ASA, PA-CF, or aluminium plate |
| Tapping M3 threads into PLA for a serviced cover | Strips after a few cycles | Heat-set insert |
| 100% infill for "strength" | Heavy, slow, warps, little gain | More perimeters, deeper section |
| Round shaft press-fit for torque | Slips under load | D-flat + set screw, clamp hub |
| Sharp internal corners on loaded printed parts | Crack initiation | Fillets R ≥ 1–2 mm (in-plane); 45° chamfers where overhang |
| Horizontal round hole | Sagging top, tight fit | Teardrop; drill |
| Snap-fit beam vertical | Breaks on first assembly | Beam in XY; halve strain |
| Long printed beams for a robot arm | Too flexible, vibrates | Deeper section, CF tube, 2020 extrusion |
| CNC part with sharp internal pocket corners | Rejected or costly EDM | Corner radius ≥ 1/3 depth; dog-bones |
| 6061-T6 sheet with tight bend | Cracks at bend | 5052-H32 or larger radius |
| Holes too close to bends | Holes distort into ovals | ≥ 2.5 t + R from bend |
| Moulded part with thick sections | Sink marks, voids, long cycle | Core out; ribs ≤ 60% wall |
| Slide-in T-nuts forgotten | Frame disassembly | Drop-in T-nuts or count before assembly |
| Wet nylon printed | Weak, stringy, bubbly | Dry 8–12 h at 70–80 °C |

---

## 19. Quick reference: numbers an agent will need most

| Quantity | Value | Label |
|---|---|---|
| Z/XY strength ratio (design) | 0.5 | [RoT] |
| Default walls / infill (functional) | 4 walls, 5 top/bottom, 25–40% gyroid | [RoT] |
| Vertical hole shrink | 0.1–0.3 mm | [DS/RoT] |
| Slip-fit clearance (printed hole, metal pin) | +0.25–0.35 mm | [EST] |
| Free-rotation clearance | +0.4–0.5 mm | [EST] |
| M3 heat-set insert printed hole | 4.0–4.2 mm, depth L + 1 mm | [DS] |
| M3 insert pull-out (PLA) | ~1400 N | [DS CNC Kitchen] |
| M3 nut pocket | 5.7–5.8 AF × 2.6–3.0 | [EST] |
| Max overhang / bridge | 45° / 10–20 mm | [DS/RoT] |
| PLA / PETG / ASA / PA-CF HDT (0.45 MPa) | ~57 / ~68–72 / ~95 / 130–215 °C | [DS] |
| Printed E (PLA / PETG / PA-CF) | ~3 / ~2 / 4–8 GPa | [EST] |
| Safety factor on printed parts | 3 static, 4–5 dynamic/unknown | [EST] |
| CNC internal corner radius | ≥ depth/3 | [DS Hubs] |
| CNC standard tolerance | ±0.1–0.125 mm | [DS Hubs] |
| Sheet bend radius | ≥ t (6061-T6: ≥ 2–3 t) | [RoT] |
| K-factor (air bend) | 0.33–0.5, ~0.42 typical | [DS secondary] |
| Hole-to-bend distance | ≥ 2.5 t + R | [RoT] |
| Injection draft / rib | ≥ 1–2° / ≤ 60% wall | [DS Protolabs] |
| 2020 extrusion Ix | ~0.70 cm⁴ | [DS generic] |
| Laser min hole | ≥ 0.5 t | [DS SendCutSend] |
| MJF moving-part clearance | 0.6 mm | [DS bureau] |

---

## Canonical references

Free (online):
- Hubs (Protolabs Network) knowledge base — FDM design guide: https://www.hubs.com/knowledge-base/how-design-parts-fdm-3d-printing/ ; CNC design guide: https://www.hubs.com/knowledge-base/how-design-parts-cnc-machining/ ; CNC cost tips: https://www.hubs.com/knowledge-base/reducing-cnc-machining-costs-13-design-tips/ (free)
- Protolabs injection moulding design guidelines: https://protolabs.com/services/injection-molding/plastic-injection-molding/design-guidelines (free); wall thickness tips: https://www.protolabs.com/resources/design-tips/solving-wall-thickness-issues-in-molded-parts/ ; sheet metal bend relief: https://www.protolabs.com/resources/blog/bend-relief/ ; sheet metal tolerances PDF: https://protolabs.com/media/roognect/sheet-metal-tolerances-one-pager-2.pdf (free)
- Fictiv, "How to design snap fit components": https://www.fictiv.com/articles/how-to-design-snap-fit-components (free)
- BASF / Bayer (Covestro) Snap-Fit Joints for Plastics design manuals (free PDFs from manufacturers; search "Bayer snap-fit joints for plastics design guide")
- CNC Kitchen (Stefan Hermann) blog and YouTube — heat-set inserts: https://cnckitchen.com/blog/are-our-heat-set-insert-datasheets-wrong ; many tests of walls/infill/orientation/annealing (free)
- Prusa Filament Material Guide: https://help.prusa3d.com/materials (free)
- Polymaker technical data sheets and wiki: https://wiki.polymaker.com (free; give Z-direction data)
- Formlabs SLA and Fuse SLS design guides: https://formlabs.com/white-papers/fuse-series-sls-design-guide/ (free with form)
- HP Multi Jet Fusion design guidelines (free PDF from HP; bureau summaries e.g. https://jlc3dp.com/help/article/3d-printing-design-guideline)
- SendCutSend guidelines (laser, bending, kerf): https://sendcutsend.com/faq/what-are-best-practices-for-minimum-geometry/ and https://sendcutsend.com/do-i-need-to-compensate-for-kerf-in-my-design/ (free)
- Ed Nisley's softsolder.com on hole calibration / polyholes; nophead's HydraRaptor blog (free)
- MIT OCW 2.008 Design and Manufacturing II (process physics, cost models): https://ocw.mit.edu/courses/2-008-design-and-manufacturing-ii-spring-2004/ (free)
- MIT OCW 2.007 Design and Manufacturing I (robot building, practical DFM) (free)
- The Fabricator (sheet metal articles): https://www.thefabricator.com (free)
- PEM self-clinching fastener catalogue (free PDF, PennEngineering)

Books / standards (paid):
- Boothroyd, Dewhurst & Knight, *Product Design for Manufacture and Assembly* (DFMA standard text).
- Kalpakjian & Schmid, *Manufacturing Engineering and Technology* (process fundamentals).
- Bralla, *Design for Manufacturability Handbook*.
- Malloy, *Plastic Part Design for Injection Molding*.
- Gibson, Rosen, Stucker, *Additive Manufacturing Technologies*.
- Shigley's *Mechanical Engineering Design* (beams, fasteners, gears — Lewis equation).
- Machinery's Handbook (threads, fits, sheet metal tables).
- ISO 286 (limits and fits), ISO 2768 (general tolerances), ISO 273 (clearance holes), ISO 4032 (hex nuts),
  ISO/ASTM 52910 (design for additive manufacturing guidelines), ISO 527 (tensile testing of plastics),
  ISO 75 (HDT).

Research cited:
- CSU Sacramento graduate thesis, mechanical and FEA comparison of FDM PLA/ABS/PETG orientation: https://scholars.csus.edu/esploro/outputs/graduate/Mechanical-and-FEA-comparison-of-FDM/99258311232901671
- Bembenek et al. 2022, PET-G and PLA FDM parameter effects: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9230522/
- Jovanović/Pešić et al., PET-G bearing housing interference fits (University of Kragujevac): https://scidar.kg.ac.rs/handle/123456789/22351
- Raspberry Pi HackSpace, "Experiments with strong 3D prints": https://hackspace.raspberrypi.com/articles/experiments-with-strong-3d-prints

---

## Gaps / not verified

- **Z/XY strength ratios** come from one thesis plus vendor Z data; real values depend heavily on printer,
  temperature, and cooling. The 0.5 design factor is a conservative rule, not a measured constant.
- **XY tensile values for PLA, ABS, ASA, PC, unfilled nylon** are general vendor ranges recalled rather
  than pulled from a single fetched TDS (several Polymaker TDS PDFs returned 404). Z values for PLA, ASA,
  PLA-CF and HDT values for PETG, PA-CF were seen in vendor data.
- **Bambu PAHT-CF numbers** were read from retailer reproductions of the Bambu spec sheet, not the
  official PDF; print axis for the 92 MPa tensile figure is not stated.
- **Creep:** no controlled room-temperature creep data for printed PLA vs PETG was found. The "keep PLA
  sustained stress < 20–25% of strength" rule is an estimate.
- **Clearance tables, nut pocket sizes, insert OD/length table, bearing pocket sizes, counterbore sizes**
  are engineering estimates and community practice. Every printer differs; always print a fit coupon.
- **Gear allowable stresses** for printed teeth are estimates; no authoritative source was found for
  minimum printable module or printed-tooth allowable stress.
- **Hubs FDM tolerance figures (±0.5%/±0.5 mm desktop, ±0.15%/±0.2 mm industrial)** are as recalled and
  were not re-read on the live page.
- **SLA accuracy, SLS figures, HP PA12 tensile/modulus** are typical values, not fetched from the HP
  datasheet.
- **K-factor** sources disagree (mild steel cited as 0.33 in one and 0.44–0.46 in another); use the
  bureau's own tables.
- **2020/2040 extrusion properties** vary by supplier (and sources disagree on axis labels for 2040);
  check the specific vendor (Misumi HFS5, OpenBuilds, 80/20) datasheet before final sizing.
- **Cost figures** (tooling, machine rates, crossover quantities) are rough industry estimates and vary
  widely by region and year.
- **Heat-set insert installation temperatures** are estimates; follow the insert vendor's guidance.
