# Mechy engineering knowledge base

Reference files for Mechy's agents to read before designing. Each file ends with
"Canonical references" and "Gaps / not verified"; treat every number as cited, typical or an
estimate exactly as it is labelled there. Written 2026-10-23 by research agents (see `_BRIEF.md`).

| File | Covers | Main roles |
|---|---|---|
| [design_principles.md](design_principles.md) | Design process, exact constraint, stiffness, DFM/DFA, failure modes, FMEA, safety standards, design-review checklist | planner, concept, docs |
| [physics_fundamentals.md](physics_fundamentals.md) | Unit traps, statics, friction, inertia, dynamics, vibration, fluids, heat, sanity checks | all |
| [materials_strength.md](materials_strength.md) | Stress, beams, buckling, fatigue, creep, safety factors, ~47-material property tables, Ashby indices | concept, cad, sim |
| [machine_elements.md](machine_elements.md) | Bearings, shafts, gears, belts, screws, fasteners, springs, couplings, linear guides, linkages | concept, cad |
| [motors_actuators.md](motors_actuators.md) | Steppers, drivers, BLDC/FOC, servos, gearmotors, pneumatics, 9-step sizing workflow | concept, controls |
| [electronics.md](electronics.md) | Power, batteries, wiring, protection, MOSFETs, MCUs, buses, sensors, EMI, cable routing, safety | controls |
| [controls_robotics.md](controls_robotics.md) | PID and cascaded loops, estimation, kinematics/IK, trajectories, firmware, simulation, catching | controls, sim |
| [machining_tolerances_fits.md](machining_tolerances_fits.md) | ISO 286 fits, bearing seats, threads, hole sizes, finish, GD&T, tolerance stacks | cad, docs |
| [manufacturing_dfm_3dprinting.md](manufacturing_dfm_3dprinting.md) | FDM strength and fits, filaments, inserts, other processes, process selection | cad |
| [cad_sim_verification.md](cad_sim_verification.md) | Code-CAD, file formats, mesh quality, FEA, MuJoCo, tolerance analysis, verification tables | cad, sim |
| [references_and_sources.md](references_and_sources.md) | Books, free courses, open hardware, supplier catalogues, standards, per-role reading lists | research |

## Weakest areas (check before relying on them)

- ISO 286 fit tables: mostly from memory, only checked at Ø8 and Ø20 (machining_tolerances_fits.md).
- Safety-standard numbers (ISO/TS 15066 forces, ISO 13854/13857 distances) from secondary sources (design_principles.md).
- controls_robotics.md had the least web cross-checking of any file.
- Most URLs in references_and_sources.md were written from memory (link check below).

## Link check (2026-10-23)

381 unique URLs: 300 returned 200. 57 returned 403, which is usually a site blocking automated requests
rather than a dead page. Eight big vendor sites timed out. These returned 404 and need replacing:

- MIT OCW 2.008 course page, micro.ros.org features page, AS5048 datasheet mirror (mlab.cz),
  CCI clearance/tolerance wiki page, AGMA ABMA 7 errata PDF, firgelliauto ISO 286 calculator, campusplastics.com.
