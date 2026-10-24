# physics_tables

Physics and engineering lookup data for Mechy agents. SI units are in column names. Every CSV row has `source_url` and a `value_type` (datasheet | standard | handbook_typical | estimate).

- Validate: `python3 -I check.py` runs 422 checks (schema, unit sanity, cross-checks and formula unit tests) and prints PASS or FAIL.
- Regenerate the computed tables: `python3 -I generate.py`.
- Use the formulas: `import formulas as F` (stdlib only), then call `F.evaluate(file, id, **vars)`, `F.convert(v, "kgf*cm", "N*m")`, `F.kt_stepped_shaft(D, d, r, "bending")`, `F.isa(h)`, `F.terminal_velocity(m, d, Cd)` or `F.interp_table(...)`.

## CSV files

| file | rows | contents / key columns | source | licence |
|---|---|---|---|---|
| physical_constants.csv | 20 | CODATA 2022 values parsed from `raw/nist_codata_allascii.txt`: id, value_SI, unit, exact, rel_uncertainty | NIST CODATA | US Gov public domain |
| unit_conversions.csv | 75 | from_unit -> SI to_unit, factor, offset (affine temperatures), exact, trap_note. Includes the hobby units that are easy to misread: kgf·cm, gf·cm, oz·in (ozf·in), g·cm², kg·mm², oz·in·s², kgf/cm², mAh, s/60° servo speed (an inverse unit) | NIST SP 811 App. B, BIPM SI Brochure | public |
| standard_atmosphere.csv | 42 | ISA from 0 to 32 km: T, p, rho, speed of sound, mu, nu | Computed from the US Std Atm 1976 / ISO 2533 equations, with Sutherland viscosity | public |
| air_properties_vs_T.csv | 25 | Dry air at 1 atm from -40 to 200 °C: rho, mu, nu, k, cp, Pr, speed of sound | Ideal gas + Sutherland (mu, k) + polynomial cp fit; agrees with Incropera tables to about 1-2 % | computed |
| water_properties_vs_T.csv | 11 | Liquid water from 0 to 100 °C: rho, mu, nu, k, cp, Pr, surface tension, vapour pressure | IAPWS-based handbook values (NIST WebBook) | summarised typical values |
| drag_coefficients.csv | 24 | Shape, orientation, reference area, Cd min/typ/max, Re range | NASA Glenn, Wikipedia (Hoerner-based) | summarised |
| restitution_coefficients.csv | 20 | Ball/surface COR min/typ/max and test basis. Sports values come from the governing-body drop-test rebound specs, using COR = sqrt(h_rebound/h_drop) | ITTF, ITF, MLB, USGA, FIBA, WSF, ASTM | summarised |
| ball_properties.csv | 16 | Ping-pong, tennis, baseball, golf, softball, juggling (beanbag, stage, silicone), squash, lacrosse, cricket, volleyball, soccer, basketball, shuttlecock and foam balls: mass and diameter min/nominal/max, Cd, COR, terminal velocity (computed with air at 20 °C) | Governing-body rules; juggling balls are estimates | summarised |
| efficiencies.csv | 34 | Gears, worm, planetary, harmonic, cycloidal, belts, chain, screws, rails, bearings (with SKF friction coefficients), motors, servos, cylinders | KHK, SKF, Gates, THK, igus, maxon, Pololu | summarised |
| surface_roughness_by_process.csv | 35 | Ra in µm (min/typ/max) for casting, forming, cutting, machining, abrasive, molding and AM processes | Classic process-roughness chart (ASME B46.1 appendix style), Protolabs, Hubs | summarised |
| tolerance_by_process.csv | 24 | Typical and best ± tolerance in mm, IT grade range, what the tolerance scales with | Protolabs, Xometry/Hubs, Formlabs, SendCutSend | summarised |
| iso2768_general_tolerances.csv | 30 | ISO 2768-1 linear general tolerances for classes f/m/c/v | ISO 2768 (via Wikipedia summary) | factual values |
| heat_transfer_coefficients.csv | 11 | h in W/m²K for free and forced convection, boiling, condensation, linearised radiation, enclosures and heatsinks | Incropera Table 1.1 (via Wikipedia) | summarised |
| pinch_point_gaps_iso13854.csv | 8 | Minimum gaps that avoid crushing, by body part (finger 25 mm ... body 500 mm) | ISO 13854 | factual values |
| safety_distances.csv | 32 | ISO 13857 Table 4 reach-through-opening distances (slot/square/round), upward reach heights, ISO 13855 approach speeds | ISO 13857, ISO 13855 | factual values |
| human_forces.csv | 20 | ISO/TS 15066 cobot quasi-static force limits by body region, MIL-STD-1472 button and toggle forces, grip and pinch strength norms | ISO/TS 15066, MIL-STD-1472, Mathiowetz 1985 | factual values |
| human_anthropometry.csv | 10 | Approximate 5th/50th/95th percentile hand, finger and reach dimensions (adult, combined sexes) | Estimates consistent with ANSUR-type data | estimate |

## JSON formula files

Each file has `formulas[]` with `id`, `name`, `variables{unit, desc}` and `outputs{name: {expr, unit}}`. The `expr` values are Python-syntax strings. `formulas.py` evaluates them through an AST whitelist: arithmetic plus math names only.

| file | entries | contents |
|---|---|---|
| moment_of_inertia_formulas.json | 24 | Point mass, rings, disks, cylinders, tubes, spheres and shells, rods, cuboid, plate about an edge, cones, torus, parallel axis, inertia reflected through a gearbox, leadscrew or pulley, inertia ratio, torque = J·alpha |
| section_properties.json | 9 | Rectangle, rectangular tube, circle, tube, thin tube, triangle, I-beam (A, I, J, c, S, r_gyr), Roark rectangle torsion constant, parallel axis |
| beam_deflection_cases.json | 15 | Cantilever (end load, load at a, UDL, end moment), simply supported (centre, at a, UDL), fixed-fixed, propped, bending stress, axial bar, round-shaft torsion, Euler buckling |
| stress_concentration.json | 5 formulas + 2 tables | Inglis elliptical hole, notch estimate, Howland finite-width plate with a hole, Neuber notch sensitivity for steel, Kf. Also a stepped-shaft power fit `Kt = A·(r/d)^b` for bending (11 D/d rows), axial (10 rows) and torsion (4 rows), and Shigley Table 7-1 first-pass Kt values |

## Raw

`raw/nist_codata_allascii.txt` is NIST's complete CODATA 2022 listing. It is a US Government work in the public domain. It is only parsed, never executed.

## Gaps / not verified

- **Values only partly cross-checked:** apart from the NIST constants, most values were compiled from memory of the cited public sources. Pages were not fetched one by one during this build, and many `source_url`s point to the organisation's top-level rules or catalogue page rather than the exact table.
- **Cross-checks that were done:** the constants were checked against each other (R = N_A·k_B, F = N_A·e, Stefan-Boltzmann from h, c and k). ISA at 11 km and air at 20 °C match the published tables. The stepped-shaft fits were spot-checked against Shigley chart readings (about 1.75 for bending and 1.50 for torsion at D/d = 2, r/d = 0.1).
- **ISO standards are paywalled.** The ISO 13854, 13857 and 13855 and ISO/TS 15066 numbers come from widely republished summaries. Check them against the purchased standard before any safety claim. The tables leave out ISO 13857 reaching over structures (Table 2), the child-specific tables and the ISO/TS 15066 pressure limits.
- **Stepped-shaft Kt fits** are third-party curve fits of Peterson's charts. They are only valid for roughly 0.01 <= r/d <= 0.3. Interpolating between D/d rows is an approximation.
- **Neuber q fit** uses imperial units (inches, kpsi). The `notch_sensitivity_steel` helper wraps it in SI units. It covers steel in bending/axial only; torsion would need its own constants, which are not included.
- **Rough estimates:** the efficiency, roughness and tolerance tables give typical ranges. Hobby and 3D-printing rows are rough estimates; use real supplier datasheets when you can.
- **Drag and COR** depend strongly on speed, spin, temperature and surface. The COR values are near the rules' test speeds, and squash balls in particular change a lot with temperature.
- **Anthropometry** values are approximate estimates, not ANSUR II percentiles. Use ISO 13854/13857 for any guarding decision.
- **Juggling balls** have no standard, so their mass, diameter and Cd are estimates.
- **Water** is liquid only, 0-100 °C at 1 atm. **Air** is dry; humidity is ignored.
