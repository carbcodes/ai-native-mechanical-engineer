# Mechy engineering data

Machine-readable lookup data for Mechy's agents, built 2026-10-23 (see `_BRIEF.md`). Every row carries
`source_url` and `value_type` (datasheet | standard | handbook_typical | estimate). Treat `estimate`
and recalled values as unverified until checked against the current datasheet. Each folder has its own
README (columns, sources, licences, gaps) and a `check.py`; run `python3 -I check.py` inside it.

| Folder | What | Size |
|---|---|---|
| [materials/](materials/) | 348 materials, 70 3D-printing/AM materials (XY vs Z), galvanic series, 57 friction pairs, 28 bushing PV limits | 7 files |
| [standard_parts/](standard_parts/) | Bearings, rails, bushings, ISO fasteners, threads, torques, belts/pulleys, screws, extrusions, keys, rings, ISO 286 fits. Regenerate with `build.py` | 31 files, 1178 rows |
| [actuators_electronics/](actuators_electronics/) | Steppers (+ modelled torque-speed), BLDC, QDD actuators, servos, gearmotors, drivers, MCUs, sensors, power, wire ampacity, connectors | 20 files, 599 rows |
| [physics_tables/](physics_tables/) | CODATA constants, unit conversions, atmosphere/air/water, drag, restitution, ball properties, safety distances, tolerances, efficiencies; formula JSONs + `formulas.py` | 17 CSV + 4 JSON |
| [reference_designs/](reference_designs/) | 43 open-source arms, grippers, legged robots, actuators and motion systems, with licences read from LICENSE files; small BOM/URDF/MJCF files in `raw/` | 43 designs |

Licence warnings from reference_designs: AR4 (no licence, trademark), Arctos (CAD is paid), Faze4
(CERN-OHL-S, not MIT), Yale OpenHand and MPCNC (non-commercial), several printed gearboxes (no licence:
reference only).
