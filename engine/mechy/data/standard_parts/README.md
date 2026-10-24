# standard_parts: off-the-shelf mechanical part tables

Lookup data for Mechy agents. Every CSV has a header row, SI units in column names (mm, kN, N, kg, MPa, rpm, N·m),
one row per item, and `source_url` and `value_type` columns (`datasheet | standard | handbook_typical | estimate`).
`value_type` records the weakest value in the row. For example, a row with standard dimensions and an estimated rating is `estimate`.

- `build.py` regenerates every file (stdlib only): `python3 -I build.py`. Edit the tables there, not the CSVs.
- `check.py` validates every file and prints PASS/FAIL: `python3 -I check.py`.

## Files

| File | Rows | Contents / key columns |
|---|---|---|
| bearings_deep_groove.csv | 91 | 6xx, 60xx, 62xx, 68xx, 69xx, miniature 68x/69x/MRxx (ZZ widths), flanged F6xx/F68x/F69x/MF. designation, series, d/D/B_mm, C_kN, C0_kN, reference/limiting_speed_rpm, mass_kg, flange_D_mm, flange_width_mm |
| bearings_thrust.csv | 11 | 51100 to 51110: d, D, H, C, C0, limiting speed, mass |
| bearings_angular_contact.csv | 15 | 7200 to 7208 BE (40°) and 3200 to 3205 double row: contact angle, C, C0, speed, mass |
| bearings_needle.csv | 18 | INA HK drawn cup (Fw, D, B) and NA49xx with inner ring |
| linear_bearings_LMUU.csv | 16 | LM3UU to LM60UU: d, D, L, retaining ring groove B/W/D1, C_N, C0_N, mass, fits |
| linear_rails.csv | 14 | HIWIN MGN7 to MGN15 C/H and HGH15 to HGH45 CA: rail W/H, assembly H, block W/L, hole pitch, bolt, C, C0, block mass, rail kg/m |
| bushings_plain_materials.csv | 6 | iglidur G/J/W300/X, sintered bronze, DU: p max, v max, PV, temperature, friction, fits |
| bushings_plain_sizes.csv | 18 | igus GSM sleeve / GFM flange sizes 3 to 30 mm with available lengths |
| threads_iso_metric.csv | 46 | M1 to M48 coarse and common fine pitches: d2, D1 (nut minor), d3 (bolt minor), stress area As, tap drill. Diameters computed from ISO 68-1/724 formulas |
| fastener_property_classes.csv | 12 | ISO 898-1 classes 4.6 to 12.9 and ISO 3506 A2-70/A4-80: Rm, Rp0.2/ReL, proof stress |
| fasteners_iso4762_shcs.csv | 14 | M1.6 to M24 SHCS: dk, k, key s, t, b, counterbore, ISO 273 clearance close/normal/loose, tap drill, As, proof load for 8.8/10.9/12.9 (As × Sp), common lengths |
| fasteners_iso7380_button.csv | 8 | M3 to M16 button head: dk, k, key |
| fasteners_iso10642_countersunk.csv | 9 | M3 to M20 flat head: theoretical/actual dk, k, key, 90° countersink dia |
| fasteners_hex_nuts.csv | 13 | M2 to M24: s, e, heights for ISO 4032, nyloc ISO 7040, thin ISO 4035 |
| fasteners_washers.csv | 20 | ISO 7089 normal and ISO 7093 large: d1, d2, h |
| fasteners_heat_set_inserts.csv | 8 | M2 to M8 brass FDM inserts: length, OD, hole dia, min wall |
| fastener_tightening_torque.csv | 168 | M1.6 to M24 × {8.8, 10.9, 12.9, A2-70} × μ {0.10, 0.12, 0.14}: preload kN, torque N·m |
| timing_belt_profiles.csv | 7 | GT2, GT3, HTD3M, HTD5M, MXL, XL, T5: pitch, tooth height, thickness, PLD, widths, min pulley teeth, working tension per mm width, mass |
| timing_belt_closed_loops.csv | 149 | Common closed-loop pitch lengths and tooth counts for GT2, GT3, HTD3M, HTD5M |
| timing_pulleys.csv | 96 | Pitch dia = z·p/π, OD = PD − 2·PLD, for common tooth counts |
| extrusions_aluminium.csv | 6 | 2020/2040 V-slot and T-slot, 3030, 4040: area, mass/m, Ixx, Iyy, Wxx, Wyy, E, yield |
| iso286_fits.json | 290 limit entries | IT5 to IT11; holes H6 to H11; shafts f6 f7 g5 g6 h5 to h11 js5 to js7 k5 k6 m5 m6 n5 n6 p6 s6 s7 for 0 to 120 mm (10 ranges, split at 65/80/100 for s). Each entry is [upper, lower] in µm. Also includes common fit descriptions |
| shafts_linear_precision.csv | 16 | Hardened linear shafts 3 to 50 mm: mass/m, g6 and h6 limits from ISO 286 |
| keys_din6885.csv | 16 | Parallel keys by shaft range 6 to 130 mm: b×h, t1, t2, length range |
| retaining_rings_din471_472.csv | 51 | External rings 3 to 50 mm and internal rings 8 to 62 mm: ring thickness s, groove dia d2, groove width m |
| dowel_pins.csv | 12 | ISO 8734 hardened m6 dowels 1.5 to 20 mm: m6 limits, length range, double-shear estimate |
| spring_wire_materials.csv | 7 | Shigley A/m constants (Sut = A/d^m), E, G, max temperature |
| springs_compression_typical.csv | 12 | Computed music-wire compression springs: rate, max working load, free and solid length |
| couplings.csv | 14 | Lovejoy L035 to L100 jaw couplings, plus hobby helical, jaw, Oldham, rigid and bellows couplings: OD, length, bores, torque, misalignment |
| lead_screws_trapezoidal.csv | 10 | Tr8 (ISO and hobby T8 lead 2/4/8), Tr10 to Tr24: d2, d3, lead angle, efficiency and torque/N at μ 0.1 and 0.2, self-locking, mass/m |
| ball_screws_SFU.csv | 5 | SFU1204, 1605, 1610, 2005, 2505: ball dia, root dia, Ca, C0a, nut/flange dims, mass/m |

## Sources and licences

- **ISO/DIN standards** (ISO 15, 286, 273, 898-1, 3506, 4032, 4762, 7089, 7093, 7380, 10642, 8734; DIN 471, 472, 6885). Dimensions are reproduced as factual engineering values. Formulas (thread geometry, As, pulley PD, IT tolerances) are applied directly. The standards themselves are copyrighted and were not copied wholesale.
- **Manufacturer catalogues**, summarised (factual specs). Sources are SKF bearings, HIWIN MGN 2023 catalogue and HG series, THK/Misumi LM bushings, INA/Schaeffler needles, igus iglidur, GGB DU, Lovejoy/Timken L-type, TBI SFU, Gates PowerGrip, OpenBuilds/Misumi extrusions, and Ruthex/CNC Kitchen inserts.
- **Shigley's Mechanical Engineering Design**: spring-wire constants only (typical values, cited).
- **Tightening torques** are computed with the VDI 2230 simplified formula: 90 % yield utilisation, head bearing dia = (dk + clearance)/2.
- Nothing was bulk-scraped and no raw files were downloaded (there is no `raw/` folder).

Cross-checks done this session:
- **SKF 6204:** C 13.5 kN and C0 6.55 kN, open limiting speed 20000 rpm (several distributor listings).
- **HIWIN MGN12H:** 3.72/5.88 kN, 0.050 kg (HIWIN catalogue).
- **HGH15/20/25CA:** C, C0, block mass and rail mass, via a distributor copy of the HIWIN table.
- **TBI 16×5:** 1380/3052 kgf. This was confirmed for the SFI series, and SFU uses the same values.
- **Lovejoy L050 and L035:** OD and max bore for L050; spider rated 3.5 in-lb for L035.
- **Computed values:** M8 8.8 at μ 0.12 comes out at 25.3 N·m (VDI table about 24.6 N·m). ISO 286 spot values for g6, p6, k6, f7 and s6 at 18 to 30 mm match the printed tables; check.py asserts these.

## Gaps / not verified

- **Bearing ratings and masses:** Most are recalled catalogue values (`handbook_typical`) and were not re-checked against a live datasheet, because SKF pages are JS-rendered and did not fetch.
- **Bearing limiting speeds:** 68/69xx, thrust, angular contact and miniature speeds are estimated as constant/dm.
- **Miniature, flanged, needle and 3200-series data:** C/C0 values are **estimates**. Miniature masses are estimated from the envelope (fill factor 0.66). Open 68x widths differ from the ZZ widths listed.
- **Extrusions:** Section properties are typical and vendor-dependent (±15 %). Use the vendor sheet for structural margins.
- **Timing belts:** Working tension and belt mass are rough **estimates**. Gates does not publish them in an accessible form, so size drives with the Gates design manual. The closed-loop lengths are common catalogue lengths, not a complete list.
- **Ball screws:** SFU ratings other than 1605 are estimates. Chinese clones are often derated, and the root diameter is approximated as d − ball.
- **Couplings:** Hobby coupling torques are rough estimates. Lovejoy torques other than L050 were not re-verified.
- **Dowel pins:** The double-shear value uses 2·A·900 MPa. This matches ISO 8734 orders of magnitude but is not the tabulated value.
- **Heat-set inserts:** Hole sizes vary by vendor (±0.2 mm).
- **Retaining rings:** Ring load capacities (groove and ring thrust) are not included.
- **ISO 286:** js is ±IT/2 with no rounding to even. Only H holes are included (no G7/F8, etc.). The k ei values apply to grades 4 to 7 only.
- **Not covered:** inch/UNC fasteners, 63xx bearings, bearing housings (KFL/UCP), BK/BF screw supports, extension and torsion springs, belt stiffness.
