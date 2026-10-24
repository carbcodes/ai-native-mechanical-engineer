# References and sources: master bibliography and resource map

Purpose: tell every Mechy agent (planner, research, concept, cad, sim, controls, docs) **where to
look** for a fact, a proven design, a part, or a standard, and **how much to trust it**. Other
knowledge files hold the numbers; this file holds the map.

Conventions used below:

- **Cost**: `FREE` (legally free online), `FREE*` (free with registration / free tier / free
  preprint), `PAID` (book or standard you must buy; often in university libraries).
- **Roles**: `PLN` planner, `RES` research, `CON` concept, `CAD` cad, `SIM` sim, `CTL` controls,
  `DOC` docs.
- **Trust tier** (see section 1): T1 standard/datasheet, T2 textbook/handbook, T3 course notes /
  app note / peer-reviewed paper, T4 respected community reference, T5 forum/blog/video.
- URLs were checked for existence in Oct 2026 where marked (v); unmarked URLs are from memory of
  long-stable domains and should be treated as "probably right" (see Gaps).

Mechy context that shapes this list: CAD is **build123d** (OpenCascade), sim is **MuJoCo**
(MJCF export), the default design is a **3D-printed belt-driven arm** (NEMA 17 steppers, GT2
belts, 608/51105 bearings). Sources were picked to serve that stack first.

---

## 0. Quick lookup: "I need X, go to Y"

| Need | First stop (free) | Authoritative (often paid) | Role |
|---|---|---|---|
| Proven open-source arm to adapt | PAROL6, AR4, Thor, SO-101, Moveo repos (sec. 6) | n/a | RES, CON |
| Bearing size, load rating C/C0, life | SKF online catalogue + bearing calculator | ISO 281, ISO 76 | CAD, RES |
| GT2/GT3 belt tension, width, tooth-in-mesh | Gates PowerGrip GT design manual | ISO 13050 | CAD, CTL |
| Stepper torque/speed curve | Vendor datasheet (LDO, StepperOnline, Oriental) | n/a | CTL, SIM |
| Stepper driver behaviour (microstep, stall) | ADI/Trinamic TMC2209/TMC5160 datasheets + app notes | n/a | CTL |
| Motor sizing method (inertia ratio, RMS torque) | Oriental Motor technical reference; maxon formulae handbook | n/a | CTL, SIM |
| Beam deflection / plate / stress formula | Engineering Toolbox, eFunda, Roymech | Roark's | CAD, SIM |
| Shaft, key, fastener, spring sizing | Shigley (library), Roymech, Bolt Science, NASA RP-1228 | Shigley, Machinery's Handbook | CAD |
| Material properties of metals | MatWeb, MakeItFrom, MMPDS (paid)/MIL-HDBK-5J (free legacy) | ASM Handbooks | CAD, SIM |
| Material properties of print filaments | Manufacturer TDS (Prusament, Polymaker, Bambu), CNC Kitchen tests | ASTM D638 data | CAD, SIM |
| Fits and tolerances | ISO 286 summaries (Engineering Toolbox, Misumi tech data) | ISO 286, ISO 2768, ASME Y14.5 | CAD, DOC |
| Kinematics / IK / Jacobians | Lynch & Park Modern Robotics (free) | Craig, Siciliano | CON, SIM, CTL |
| Rigid-body dynamics, sim modelling | MuJoCo docs, Featherstone, Drake/Pinocchio docs | Featherstone book | SIM |
| Controller design (PID, loop shaping) | Åström & Murray FBS (free), Brian Douglas videos | Ogata, Franklin-Powell | CTL |
| Precision / kinematic coupling / stiffness budget | Slocum FUNdaMENTALS (free), Hale thesis (free) | Slocum Precision Machine Design | CON, CAD |
| Mechanism ideas | 507 Mechanical Movements (public domain), KMODDL (free) | Sclater sourcebook | CON |
| DfM for print/CNC/sheet | Protolabs, Xometry, Hubs knowledge base, Prusa KB | ISO/ASTM 52910 | CAD |
| Robot safety / performance terms | ISO OBP preview pages, robot vendor manuals | ISO 10218, ISO/TS 15066, ISO 9283 | PLN, DOC |
| CAD of purchased parts | McMaster, Misumi, TraceParts, cq_warehouse/bd_warehouse | n/a | CAD |
| Ready robot models for sim | MuJoCo Menagerie, robot_descriptions.py | n/a | SIM |
| Writing clear build docs | Prusa assembly manuals, Voron manuals (as style exemplars) | ASME Y14.100, ISO 128 | DOC |

---

## 1. How to use sources (rules for agents)

### 1.1 Trust tiers

| Tier | Examples | Use for | Caveat |
|---|---|---|---|
| T1 | ISO/ASME/DIN standard, manufacturer datasheet for the exact part number | Final numbers in bom.csv, ratings, tolerances | Datasheets are optimistic (rated at 25 C, ideal mounting). Derate. |
| T2 | Shigley, Roark's, Machinery's Handbook, Craig, Ogata | Methods, formulas, design factors | Edition matters; equation numbers change between editions. |
| T3 | MIT OCW notes, vendor app notes (Gates, Trinamic, SKF), peer-reviewed papers | Methods with worked examples; modern practice | App notes sell product; cross-check against T2. |
| T4 | Engineering Toolbox, eFunda, Roymech, Prusa KB, Klipper docs, CNC Kitchen | Quick values, sanity checks | Usually uncited; confirm design-driving numbers with T1/T2. |
| T5 | Hackaday posts, Reddit, YouTube, forums | Real-world failure modes, "what broke" | Anecdotal; never the sole source for a number. |

Rules:

1. A number that **drives a decision** (motor choice, safety factor, belt width, bearing size)
   needs two independent sources, at least one T1/T2. Write both in the note.
2. A number from T4/T5 only is labelled `estimate (T4: engineeringtoolbox.com)`.
3. Prefer the **datasheet for the exact part** over a generic table (a "NEMA 17" ranges from
   about 0.2 to 0.65 N·m holding torque depending on stack length; typical, from vendor
   catalogues such as StepperOnline/LDO).
4. Record edition/year for books and revision/date for standards and datasheets.
5. Do not paste copyrighted tables (Machinery's Handbook, Shigley, Roark's). Summarise the method
   and cite "Shigley 11th ed., ch. 11" instead. Datasheets and public-domain (US government) data
   may be tabulated with citation.

### 1.2 Licence hygiene for open hardware (RES, CAD, DOC)

| Licence | Can Mechy adapt and ship? | Obligation |
|---|---|---|
| CC BY 4.0 | Yes | Credit author, link licence, note changes |
| CC BY-SA 4.0 | Yes | Credit + derivative must stay BY-SA |
| CC BY-NC(-SA) | Personal/non-commercial only | Flag to user before any commercial use |
| CERN-OHL-S / -W / -P | Yes | S: share-alike on hardware; W: weak; P: permissive |
| GPLv3 (often used for firmware + CAD) | Yes | Source of derivative must be available |
| MIT / Apache-2.0 / BSD | Yes | Keep notice |
| "All rights reserved" / no licence file | **No** (look only) | Treat as reference, re-model from scratch |

Common mistake: assuming GitHub = open licence. A repo without a LICENSE file is all rights
reserved. Another: the README badge and LICENSE file disagree (seen on PAROL6 mirrors: MIT badge
vs GPLv3 text, per Oct 2026 search). Always read the LICENSE file itself.

### 1.3 Citation format in Mechy notes

```
[src] Gates, "PowerGrip GT4 Belt Drives Design Manual", rev. <date>, p. <n>  (T3, FREE)
[src] Budynas & Nisbett, Shigley's Mechanical Engineering Design, 11th ed., §11-9 (T2, PAID)
[src] SKF 6202-2RSH product page, C = 8.06 kN, accessed 2026-10-23 (T1, FREE)
```

---

## 2. Canonical textbooks and handbooks by discipline

Format per entry: **Title** (author, publisher, edition) | Cost | URL | Good for | Roles.
URLs point to the publisher or the author's free copy; buy/borrow details change.

### 2.1 General machine design and machine elements

| Book | Cost | URL | Good for | Roles |
|---|---|---|---|---|
| **Machinery's Handbook** (Oberg et al., Industrial Press, 32nd ed. 2024 approx.) | PAID | https://www.industrialpress.com | The shop bible: threads, fits, gears, springs, keys, material data, machining. Look up values; not a design-method book. | CAD, RES |
| **Shigley's Mechanical Engineering Design** (Budynas & Nisbett, McGraw-Hill, 11th ed.) | PAID | https://www.mheducation.com | Fatigue (Goodman/Marin), shafts, bolted joints (joint stiffness, preload), bearings, gears, springs. The default method reference. | CAD, SIM, RES |
| **Machine Design: An Integrated Approach** (Robert L. Norton, Pearson, 6th ed.) | PAID | https://www.pearson.com | Same scope as Shigley with clearer worked examples; good on failure theories and case studies. | CAD |
| **Design of Machinery** (Robert L. Norton, McGraw-Hill, 6th ed.) | PAID | https://www.mheducation.com | Linkage synthesis, cams, gear trains, kinematic/dynamic analysis of mechanisms. Concept-stage mechanism choice. | CON, SIM |
| **Fundamentals of Machine Component Design** (Juvinall & Marshek, Wiley) | PAID | https://www.wiley.com | Alternative to Shigley; strong on "force flow" thinking and load paths. | CAD, CON |
| **Theory of Machines and Mechanisms** (Uicker, Pennock, Shigley, Oxford/Cambridge) | PAID | publisher site | Kinematics of linkages, Grashof, instant centers. | CON |
| **Roymech** (UK machine-design reference site) | FREE | https://roymech.org | Shafts, keys, fits, belts, bearings, bolts summarised with formulas. T4. | CAD |
| **Mechanisms and Mechanical Devices Sourcebook** (Sclater, McGraw-Hill) | PAID | https://www.mheducation.com | Catalogue of mechanisms with sketches; idea generation. | CON |
| **507 Mechanical Movements** (Henry T. Brown, 1868, public domain) | FREE | http://507movements.com | Classic mechanism catalogue, animated online. | CON |
| **KMODDL** (Cornell Kinematic Models for Design Digital Library, Reuleaux collection) | FREE | https://kmoddl.library.cornell.edu | Historic mechanism models, video, Reuleaux text. | CON |

### 2.2 Stress, deflection, structures

| Book | Cost | URL | Good for | Roles |
|---|---|---|---|---|
| **Roark's Formulas for Stress and Strain** (Young, Budynas, Sadegh, McGraw-Hill, 9th ed. 2020) | PAID | https://www.mheducation.com | Closed-form cases for beams, plates, shells, contact (Hertz), torsion of odd sections. The verification source for FEA/sim checks (standards rule 5). | SIM, CAD |
| **Mechanics of Materials** (Hibbeler, Pearson) | PAID | https://www.pearson.com | Undergrad stress/strain, torsion, bending, buckling. Clear examples. | CAD, SIM |
| **Mechanics of Materials** (Gere & Goodno, Cengage) | PAID | publisher site | Alternative to Hibbeler. | CAD |
| **Structures: Or Why Things Don't Fall Down** (J.E. Gordon, Da Capo) | PAID | n/a | Intuition for load paths, stiffness vs strength. Good for concept reasoning. | CON |
| **Building Better Products with Finite Element Analysis** (Adams & Askenazi, OnWord) | PAID | n/a | Practical FEA pitfalls: boundary conditions, singularities, mesh convergence. | SIM |
| **NASA Fastener Design Manual, RP-1228** (Barrett, 1990) | FREE | https://ntrs.nasa.gov (search "RP-1228") | Bolt preload, torque-tension, thread strength, locking methods. US gov, public domain. | CAD |
| **NASA-STD-5001** (structural design and test factors of safety) | FREE | https://standards.nasa.gov | Defensible factor-of-safety tables (aerospace, conservative). | CAD, PLN |
| **MIL-HDBK-5J** (legacy metallic materials handbook, superseded by MMPDS) | FREE (legacy) | https://quicksearch.dla.mil or archive mirrors | Design allowables for aluminium/steel; MMPDS (paid, Battelle) is current. | CAD, SIM |

### 2.3 Materials

| Book / resource | Cost | URL | Good for | Roles |
|---|---|---|---|---|
| **Materials Selection in Mechanical Design** (Michael F. Ashby, Butterworth-Heinemann, 5th ed.) | PAID | https://www.elsevier.com | Material indices (E/ρ, σ^(2/3)/ρ...), Ashby charts. Picking material for a link or bracket. | CON, CAD |
| **Ansys Granta EduPack** (ex-CES EduPack) | PAID (edu licences) | https://www.ansys.com/products/materials/granta-edupack | Interactive Ashby charts, property database. | CON |
| **Materials: Engineering, Science, Processing and Design** (Ashby, Shercliff, Cebon) | PAID | Elsevier | Gentler companion to Ashby. | CON |
| **MatWeb** | FREE* | https://www.matweb.com | Searchable datasheets (metals, plastics). T4: values are vendor-supplied, check grade/temper. | CAD, SIM |
| **MakeItFrom** | FREE | https://www.makeitfrom.com | Normalised property ranges, easy comparisons. | CAD, CON |
| **ASM Handbooks** (ASM International) | PAID | https://www.asminternational.org | Authoritative metallurgy, heat treat, failure analysis. | RES |

### 2.4 Precision engineering and exact constraint

| Book / resource | Cost | URL | Good for | Roles |
|---|---|---|---|---|
| **Precision Machine Design** (Alexander Slocum, Prentice Hall 1992; SME reprint) | PAID | SME / used | Error budgets, Abbe error, kinematic couplings, bearings, structures, actuators. The bible for stiffness/accuracy thinking. | CON, CAD |
| **FUNdaMENTALS of Design** (Slocum, MIT, 2007-2008) | FREE (v) | https://pergatory.mit.edu/resources/FUNdaMENTALS.html ; also https://meddevdesign.mit.edu/fundamentals-of-design | Free chapters + spreadsheets: Saint-Venant, Abbe, exact constraint, bearings, structures, power transmission, design process. Best free design-thinking text. | CON, CAD, PLN |
| **Principles and Techniques for Designing Precision Machines** (Layton Hale, PhD thesis MIT/LLNL 1999) | FREE | https://www.osti.gov (search "Hale precision machines") | Error budgeting, kinematic design, flexures; very practical. | CON, CAD |
| **Exact Constraint: Machine Design Using Kinematic Principles** (Douglass Blanding, ASME Press) | PAID | https://www.asme.org | Constraint counting, avoiding over-constraint (why two linear rails bind). | CON, CAD |
| **Foundations of Ultraprecision Mechanism Design** (Smith & Chetwynd, CRC) | PAID | CRC Press | Flexures, kinematic mounts, elastic design. | CON |
| **Compliant Mechanisms** (Larry Howell, Wiley) + BYU CMR site | PAID / FREE site | https://www.compliantmechanisms.byu.edu | Flexure/compliant mechanism design, printable flexures. | CON, CAD |

### 2.5 Robotics (kinematics, dynamics, planning)

| Book | Cost | URL | Good for | Roles |
|---|---|---|---|---|
| **Modern Robotics: Mechanics, Planning, and Control** (Lynch & Park, Cambridge UP 2017) | FREE preprint (v) | https://hades.mech.northwestern.edu/index.php/Modern_Robotics | Screw theory, PoE forward kinematics, Jacobians, singularities, dynamics, trajectory generation; free Python/MATLAB code library and video lectures. Default robotics reference for Mechy. | CON, SIM, CTL |
| **Introduction to Robotics: Mechanics and Control** (John J. Craig, Pearson, 4th ed. 2017) | PAID | https://www.pearson.com | Classic DH convention (modified DH), IK closed form, Newton-Euler dynamics. Many arm projects (e.g. AR4 modified-DH spreadsheets) follow Craig's convention. | SIM, CTL |
| **Robot Modeling and Control** (Spong, Hutchinson, Vidyasagar, Wiley, 2nd ed.) | PAID | https://www.wiley.com | Standard DH, dynamics, independent-joint control, actuator/transmission modelling. | CTL, SIM |
| **Robotics: Modelling, Planning and Control** (Siciliano, Sciavicco, Villani, Oriolo, Springer) | PAID | https://link.springer.com | Rigorous; trajectory planning, force control. | CTL |
| **Springer Handbook of Robotics** (Siciliano & Khatib, eds., 2nd ed. 2016) | PAID | https://link.springer.com | Survey chapters on every subfield, incl. robot hands, actuators, design. | RES |
| **A Mathematical Introduction to Robotic Manipulation** (Murray, Li, Sastry, CRC 1994) | FREE (author PDF) | https://www.cds.caltech.edu/~murray/mlswiki | Screw theory, grasping math. | SIM, CTL |
| **Robotics, Vision and Control** (Peter Corke, Springer, 3rd ed., Python edition) | PAID (book), FREE (toolbox) | https://petercorke.com ; https://github.com/petercorke/robotics-toolbox-python | Runnable examples; Robotics Toolbox for Python for quick FK/IK checks. | SIM, CTL |
| **Rigid Body Dynamics Algorithms** (Roy Featherstone, Springer 2008) | PAID | https://link.springer.com | Spatial vector algebra, RNEA/ABA/CRBA: what MuJoCo/Pinocchio compute. | SIM |
| **Planning Algorithms** (Steven LaValle, Cambridge UP 2006) | FREE | http://lavalle.pl/planning | Motion planning (RRT, PRM), configuration space. | SIM, CTL |
| **Underactuated Robotics** and **Robotic Manipulation** (Russ Tedrake, MIT course notes) | FREE | https://underactuated.mit.edu ; https://manipulation.mit.edu | Modern control/trajectory optimisation, manipulation pipeline, with Drake notebooks. | CTL, SIM |
| **Probabilistic Robotics** (Thrun, Burgard, Fox, MIT Press) | PAID | https://mitpress.mit.edu | State estimation, Kalman/particle filters (vision-based catching, sensing). | CTL |

### 2.6 Dynamics, vibration, statics

| Book | Cost | URL | Good for | Roles |
|---|---|---|---|---|
| **Engineering Mechanics: Statics / Dynamics** (Hibbeler, Pearson) | PAID | https://www.pearson.com | Free-body diagrams, rigid-body dynamics, work-energy. | SIM, CAD |
| **Engineering Mechanics: Statics / Dynamics** (Meriam, Kraige, Bolton, Wiley) | PAID | https://www.wiley.com | Same scope, harder problems; good for gravity-torque and projectile checks. | SIM |
| **Engineering Vibration** (Inman, Pearson) or **Mechanical Vibrations** (S.S. Rao, Pearson) | PAID | publisher sites | Natural frequency, damping, resonance of belt/arm systems. | SIM, CTL |
| **MIT 2.003SC Engineering Dynamics** (OCW) | FREE | see sec. 3 | Free full course with problem sets. | SIM |

### 2.7 Control

| Book | Cost | URL | Good for | Roles |
|---|---|---|---|---|
| **Feedback Systems: An Introduction for Scientists and Engineers** (Åström & Murray, Princeton UP, 2nd ed. 2021) | FREE online (v, home moved to fbsbook.org) | https://fbsbook.org | Modern intro to feedback, PID, loop shaping, robustness; free PDF plus Python examples (python-control). Default control reference. | CTL |
| **Modern Control Engineering** (Katsuhiko Ogata, Pearson, 5th ed.) | PAID | https://www.pearson.com | Classical control, root locus, Bode, state space; many solved problems. | CTL |
| **Feedback Control of Dynamic Systems** (Franklin, Powell, Emami-Naeini, Pearson, 8th ed.) | PAID | https://www.pearson.com | Widely used alternative; good on digital control and design examples. | CTL |
| **Advanced PID Control** / **PID Controllers** (Åström & Hägglund, ISA) | PAID | https://www.isa.org | Anti-windup, set-point weighting, tuning rules. | CTL |
| **Digital Control of Dynamic Systems** (Franklin, Powell, Workman) | PAID | n/a | Sample-rate selection, discretisation (step-rate / loop-rate questions). | CTL |
| **Data-Driven Science and Engineering** (Brunton & Kutz, Cambridge UP, 2nd ed.) | FREE PDF (author site) | https://databookuw.com | System identification, SVD, Kalman, modern control from data. | CTL, SIM |
| **python-control** library docs | FREE | https://python-control.readthedocs.io | Implementing FBS examples, Bode/step responses in Python. | CTL |

### 2.8 Electronics, motors, mechatronics

| Book | Cost | URL | Good for | Roles |
|---|---|---|---|---|
| **The Art of Electronics** (Horowitz & Hill, Cambridge UP, 3rd ed. 2015) + **x-Chapters** (2020) | PAID | https://artofelectronics.net | Power supplies, MOSFET drivers, grounding, noise, sensors. The practitioner's electronics book. | CTL |
| **Practical Electronics for Inventors** (Scherz & Monk, McGraw-Hill) | PAID | publisher | Gentler; motors, sensors, microcontroller interfacing. | CTL |
| **Electric Motors and Drives** (Austin Hughes & Bill Drury, Newnes, 5th ed.) | PAID | https://www.elsevier.com | Intuitive treatment of DC, stepper, brushless, inverter drives. | CTL |
| **Introduction to Mechatronics and Measurement Systems** (Alciatore, McGraw-Hill) | PAID | publisher; book site has free resources | Sensors, encoders, motor drivers, microcontroller-mechanism integration. | CTL |
| **Handbook of Modern Sensors** (Jacob Fraden, Springer) | PAID | https://link.springer.com | Picking encoders, Hall sensors, limit switches, IMUs. | CTL |
| **TI Analog Engineer's Pocket Reference** | FREE | https://www.ti.com (search title) | Op-amp, ADC, PCB trace, unit conversion cheat sheet. | CTL |
| **All About Circuits** textbook | FREE | https://www.allaboutcircuits.com/textbook | Free basic electronics textbook. | CTL |
| **maxon "Key information on maxon DC motor and encoder" / formulae handbook** | FREE | https://www.maxongroup.com | Motor constants (kt, kn, R), thermal limits, operating range diagram. | CTL, SIM |

### 2.9 Design process, DfM/DfA, product development

| Book | Cost | URL | Good for | Roles |
|---|---|---|---|---|
| **The Mechanical Design Process** (David G. Ullman, 6th ed.) | PAID | https://www.mheducation.com (later editions possibly self-published; unsure) | Requirements → specs → concepts → embodiment; QFD, decision matrices. Mechy planner's process model. | PLN, CON |
| **Engineering Design: A Systematic Approach** (Pahl, Beitz, Feldhusen, Grote, Springer, 3rd ed. 2007) | PAID | https://link.springer.com | Function structures, morphological charts, embodiment rules ("clarity, simplicity, safety"). | PLN, CON |
| **Product Design and Development** (Ulrich & Eppinger, McGraw-Hill, 7th ed.) | PAID | https://www.mheducation.com | Concept selection (Pugh), architecture, prototyping strategy. | PLN, CON |
| **Product Design for Manufacture and Assembly** (Boothroyd, Dewhurst, Knight, CRC) | PAID | CRC Press | Part-count reduction, assembly time estimation. | CAD, CON |
| **Additive Manufacturing Technologies** (Gibson, Rosen, Stucker, Khorasani, Springer, 3rd ed.) | PAID | https://link.springer.com | AM processes, DfAM principles. | CAD |
| **The 3D Printing Handbook** (Redwood, Schöffer, Garret, 3D Hubs) | PAID | n/a | Process-specific design rules (wall thickness, holes, overhangs). Hubs knowledge base has free versions of much of this. | CAD |
| **Manufacturing Engineering and Technology** (Kalpakjian & Schmid, Pearson) | PAID | publisher | Processes beyond printing (machining, sheet metal, moulding). | CAD, RES |
| **Mechanical Tolerance Stackup and Analysis** (Bryan Fischer, CRC) | PAID | CRC Press | Worst-case vs RSS stacks, GD&T in stacks. | CAD |

### 2.10 Power transmission (gears, belts, screws, bearings)

| Book / resource | Cost | URL | Good for | Roles |
|---|---|---|---|---|
| **KHK Gear Technical Reference** | FREE | https://khkgears.net/new/gear_knowledge/ | Involute geometry, module, backlash, strength; free, clear. | CAD |
| **SDP/SI "Elements of Metric Gear Technology" and belt/pulley technical section** | FREE | https://www.sdp-si.com (technical resources) | Gear and timing-belt geometry, centre distance formulas. | CAD |
| **Dudley's Handbook of Practical Gear Design and Manufacture** (Radzevich, CRC) | PAID | CRC Press | Gear rating, failure modes. | CAD |
| **Rolling Bearing Analysis** (Harris & Kotzalas, CRC) | PAID | CRC Press | Deep bearing theory; rarely needed beyond SKF catalogue. | RES |
| **Gates belt design manuals** (PowerGrip GT, Poly Chain) | FREE | https://www.gates.com (catalogs/manuals) | See sec. 7. | CAD, CTL |
| **Harmonic Drive / cycloidal engineering data** | FREE | https://www.harmonicdrive.net | Strain-wave gear stiffness, ratings; reference for higher-end joints. | CON |

---

## 3. Free courses

| Course | Cost | URL | Good for | Roles |
|---|---|---|---|---|
| **MIT 2.007 Design and Manufacturing I** (Slocum et al., Spring 2009) | FREE (CC BY-NC-SA) | https://ocw.mit.edu/courses/2-007-design-and-manufacturing-i-spring-2009/ | Robot-competition design: power transmission, bearings, structures, FUNdaMENTALS-based lectures, spreadsheets. Closest course to Mechy's job. | CON, CAD, PLN |
| **MIT 2.72 Elements of Mechanical Design** (Culpepper, Spring 2009) | FREE (v) | https://ocw.mit.edu/courses/2-72-elements-of-mechanical-design-spring-2009/ | Machine elements with stiffness/error modelling; students build a desktop lathe. Uses Shigley + Norton. | CAD, CON |
| **MIT 2.003SC Engineering Dynamics** (Fall 2011) | FREE | https://ocw.mit.edu/courses/2-003sc-engineering-dynamics-fall-2011/ | Lagrange, rigid-body dynamics, vibration; video lectures + solutions. | SIM |
| **MIT 2.004 Dynamics and Control II** | FREE | https://ocw.mit.edu (search 2.004) | Motor modelling, transfer functions, lab-based control. | CTL |
| **MIT 2.14 Analysis and Design of Feedback Control Systems** | FREE | https://ocw.mit.edu (search 2.14) | Loop shaping, compensator design. | CTL |
| **MIT 2.12 Introduction to Robotics** (Fall 2005) | FREE | https://ocw.mit.edu (search 2.12) | Manipulator kinematics, actuators, control. | CTL, SIM |
| **MIT 2.75 Precision Machine Design** (Slocum) | FREE | https://ocw.mit.edu (search 2.75) ; https://stuff.mit.edu/afs/athena/course/2/2.75/ | Precision design projects, error budgets. | CON, CAD |
| **MIT 2.008 Design and Manufacturing II** | FREE | https://ocw.mit.edu (search 2.008) | Process physics, injection moulding, machining, DfM. | CAD |
| **MIT 6.4210 Robotic Manipulation** / **6.8210 Underactuated Robotics** (Tedrake) | FREE | https://manipulation.mit.edu ; https://underactuated.mit.edu | Notes + Drake notebooks + lecture videos. | CTL, SIM |
| **Stanford CS223A Introduction to Robotics** (Oussama Khatib) | FREE (videos) | https://see.stanford.edu (SEE) ; YouTube | Kinematics, Jacobians, dynamics, operational-space control. | SIM, CTL |
| **Modern Robotics specialization** (Northwestern, Lynch) on Coursera | FREE to audit* | https://www.coursera.org/specializations/modernrobotics | 6 courses following the free book, capstone on mobile manipulation. Certificate paid. | CON, SIM, CTL |
| **QUT Robot Academy** (Peter Corke) | FREE | https://robotacademy.net.au | Short video lessons on kinematics, vision, control. | SIM, CTL |
| **Steve Brunton Control Bootcamp** (YouTube, UW) | FREE | https://www.youtube.com/@Eigensteve | Intuitive state-space control, LQR, Kalman. | CTL |
| **MATLAB Tech Talks (Brian Douglas)** | FREE | https://www.mathworks.com/videos/series.html (Control Systems, PID, State Space) | The clearest short explanations of PID, loop shaping, Kalman filters. | CTL |
| **Kevin Lynch Modern Robotics videos** | FREE | linked from the Modern Robotics wiki | Chapter-by-chapter lectures. | SIM |
| **Cambridge "Design and Manufacture" library** | FREE | https://www-mdp.eng.cam.ac.uk/web/library/design.html | Index of design resources incl. Slocum chapters (with permission). | CON |
| **edX / MITx 2.01x Elements of Structures** | FREE to audit* | https://www.edx.org | Beam bending, torsion, structural basics. | CAD, SIM |

---

## 4. Free online references

| Site | Cost | URL | Good for | Caveats | Roles |
|---|---|---|---|---|---|
| **The Engineering ToolBox** | FREE | https://www.engineeringtoolbox.com | Fast lookups: friction coefficients, densities, Young's modulus, beam formulas, unit conversions. | T4, rarely cited; check design-driving values. | All |
| **eFunda** | FREE* | https://www.efunda.com | Formula calculators (beams, plates, springs), material and unit data. | Some content behind membership; dated UI. | CAD, SIM |
| **Roymech** | FREE | https://roymech.org | UK-style machine design summaries. | T4. | CAD |
| **Bolt Science** | FREE | https://www.boltscience.com | Preload, self-loosening (Junker), thread stripping; explained plainly. | Sells software; content is solid. | CAD |
| **NASA Technical Reports Server (NTRS)** | FREE | https://ntrs.nasa.gov | Public-domain reports: fasteners, bearings, gears (NASA did lots of gear/bearing research), tribology, mechanisms (Aerospace Mechanisms Symposium proceedings: failure lessons). | Search well; dated but rigorous. | RES, CAD |
| **NASA Technical Standards** | FREE | https://standards.nasa.gov | NASA-STD-5001 (FoS), NASA-STD-5020 (threaded fasteners), NASA-STD-5017 (mechanisms). | Aerospace conservative. | PLN, CAD |
| **DLA ASSIST QuickSearch** (MIL-STD/MIL-HDBK) | FREE | https://quicksearch.dla.mil | Military standards and handbooks (many free). | Some require registration. | RES |
| **NIST/SEMATECH e-Handbook of Statistical Methods** | FREE | https://www.itl.nist.gov/div898/handbook/ | Design of experiments, measurement uncertainty, test result statistics. | n/a | SIM, DOC |
| **Hackaday / Hackaday.io** | FREE | https://hackaday.com ; https://hackaday.io | Build logs of DIY arms, actuators, cycloidal drives; real failure stories. | T5. | RES, CON |
| **Hackster.io** | FREE | https://www.hackster.io | Project write-ups (AR4, PAROL6 coverage). | T5. | RES |
| **Slocum FUNdaMENTALS** | FREE | see sec. 2.4 | Design principles + spreadsheets. | 2008 page, some links may rot. | CON, CAD |
| **Prusa Knowledge Base** | FREE | https://help.prusa3d.com | Material guide (PLA/PETG/ASA/PC/PA properties and print temps), DfAM tips, troubleshooting. | Vendor-specific but well-maintained. | CAD |
| **CNC Kitchen** (Stefan Hermann) | FREE | https://www.cnckitchen.com ; YouTube | Measured tests: infill vs strength, layer orientation, heat-set inserts, annealing, screw pull-out in prints. Best real data on FDM part strength. | T5 but systematic, measured. | CAD, SIM |
| **Ellis' Print Tuning Guide** | FREE | https://ellis3dp.com/Print-Tuning-Guide/ | Calibrating dimensional accuracy (hole compensation, flow, pressure advance). | Voron/Klipper focus. | CAD |
| **Klipper documentation** | FREE | https://www.klipper3d.org | Stepper kinematics, input shaping (resonance compensation), TMC driver tuning, rotation distance for belts. Excellent for stepper+belt motion control. | n/a | CTL, SIM |
| **Hubs (ex 3D Hubs) knowledge base** | FREE | https://www.hubs.com/knowledge-base/ | DfM guides for FDM, SLS, CNC, sheet metal, injection moulding. | Now part of Protolabs. | CAD |
| **Protolabs design guidelines / design tips** | FREE | https://www.protolabs.com/resources/ | DfM rules for CNC, moulding, sheet metal, AM. | Vendor. | CAD |
| **Xometry resources** | FREE | https://www.xometry.com/resources/ | DfM, material and process guides. | Vendor. | CAD |
| **Fastenal engineering & design support** | FREE | https://www.fastenal.com (Engineering → technical reference) | Fastener grades, torque, thread data. | US-centric. | CAD |
| **MuJoCo documentation** | FREE | https://mujoco.readthedocs.io | MJCF modelling, actuators, contacts, solver params. Required reading for SIM. | n/a | SIM |
| **build123d documentation** | FREE | https://build123d.readthedocs.io | Mechy's CAD API: builders, algebra mode, joints, export. | n/a | CAD |
| **CadQuery docs** | FREE | https://cadquery.readthedocs.io | Sibling OCC library; many examples port to build123d. | n/a | CAD |
| **ROS 2 / MoveIt 2 / ros2_control docs** | FREE | https://docs.ros.org ; https://moveit.picknik.ai ; https://control.ros.org | URDF conventions, controller architecture, motion planning. | n/a | SIM, CTL |
| **Drake** | FREE | https://drake.mit.edu | Multibody dynamics, trajectory optimisation, Python. Cross-check MuJoCo results. | n/a | SIM |
| **Pinocchio** | FREE | https://github.com/stack-of-tasks/pinocchio | Fast FK/Jacobian/RNEA for verification of sim and torque budgets. | n/a | SIM, CTL |
| **Engineering Stack Exchange / Robotics SE / Electronics SE** | FREE | https://engineering.stackexchange.com ; https://robotics.stackexchange.com ; https://electronics.stackexchange.com | Specific Q&A; good answers often cite sources. | T5. | RES |
| **Eng-Tips forums** | FREE | https://www.eng-tips.com | Practising engineers; bolted joints, fatigue, GD&T debates. | T5. | RES |
| **arXiv cs.RO / Google Scholar** | FREE | https://arxiv.org/list/cs.RO/recent ; https://scholar.google.com | Recent robot-design papers (low-cost arms, QDD actuators). | Preprints not peer-reviewed. | RES |
| **IEEE Xplore** | PAID (often via library) | https://ieeexplore.ieee.org | ICRA/IROS/T-RO papers. | Paywalled. | RES |

---

## 5. Key papers and theses worth knowing (free)

| Work | Cost | Where | Why it matters to Mechy | Roles |
|---|---|---|---|---|
| Gealy et al., "Quasi-Direct Drive for Low-Cost Compliant Robotic Manipulation" (Berkeley Blue, ICRA 2019) | FREE (arXiv) | https://arxiv.org (search title) | Low-cost arm with belt/timing reductions and BLDC; cost vs performance reasoning for belt arms. | CON, CTL |
| Benjamin Katz, "A Low Cost Modular Actuator for Dynamic Robots" (MIT MS thesis 2018, Mini Cheetah actuator) | FREE | https://dspace.mit.edu | QDD actuator design, FOC, torque density; source of many open actuators. | CON, CTL |
| Wensing et al., "Proprioceptive Actuator Design in the MIT Cheetah" (IEEE T-RO 2017) | PAID / preprint | IEEE / author pages | Gear ratio vs impact mitigation, transparency. | CON |
| Grimminger et al., "An Open Torque-Controlled Modular Robot Architecture for Legged Locomotion Research" (ODRI Solo, RA-L 2020) | FREE (arXiv) | https://arxiv.org ; https://open-dynamic-robot-initiative.github.io | Open BLDC actuator with **two-stage 9:1 timing-belt reduction** and printed parts; directly relevant belt-drive precedent. | CON, CAD, CTL |
| Slocum, "Kinematic couplings: A review of design principles and applications" (Int. J. Machine Tools & Manufacture 2010) | PAID / author copy | pergatory.mit.edu publications | Repeatable mounting (end-effectors, tool changers). | CON, CAD |
| Hale thesis (see 2.4) | FREE | OSTI | Error budgets, exact constraint. | CON |
| LeRobot docs and SO-100/101 tutorials (Hugging Face, 2024-2025) | FREE | https://huggingface.co/docs/lerobot | Low-cost servo arms for learning; data collection format. | RES, CTL |

---

## 6. Open-hardware projects to learn from

Rule (from _standards.md #1): start from the closest proven design. This table says what each is
good to borrow and its known weak points. Licences change; read LICENSE before reuse.

### 6.1 Robot arms

| Project | Key facts (typical, from project docs / press) | Borrow | Watch out | Cost | URL | Roles |
|---|---|---|---|---|---|---|
| **BCN3D Moveo** (2016) | 5-DOF, printed, NEMA 17/23 steppers with belts and printed pulleys, Arduino Mega + RAMPS. | Simple belt-and-printed-pulley joints; good starter reference for a cheap belt arm. | Low stiffness, noticeable backlash/sag, dated firmware; community considers it a learning toy. | FREE (CC BY-SA, check) | https://github.com/BCN3D/BCN3D-Moveo | CON, CAD |
| **Annin Robotics AR4** (Mark 5 "final" hardware, 2025) | 6-DOF, CNC aluminium + printed parts, steppers with integrated encoders, Teensy 4.1; about 1-1.9 kg payload, 600-630 mm reach (sources disagree); ~USD 2k build (estimate, Hackster). Published modified-DH parameters. ROS 2 driver + URDF exist. | Industrial-style joint layout, encoder closed-loop steppers, homing (Hall on J1-J3), DH tables, MoveIt integration. | Mostly aluminium (not fully printable); planetary-geared steppers add backlash; licence is not a standard open-hardware licence (check site terms). | FREE plans / kits PAID | https://www.anninrobotics.com ; ROS 2 driver: https://github.com/ycheng517/ar4_ros_driver (believed; verify) | CON, CAD, CTL, SIM |
| **Thor** (Ángel L.M.) | 6-DOF fully 3D-printed, steppers, belt + printed gear reductions, GRBL-based control board. | Fully printable design with belt reductions and hollow joints for cable routing. | Modest payload/precision; large print volume. | FREE (CC BY-SA, check) | https://github.com/AngelLM/Thor | CON, CAD |
| **PAROL6** (Petar Crnjak / Source Robotics) | 6-DOF desktop, printed + stock parts, steppers with belts/planetaries; claims 1 kg payload, 400 mm reach, 0.08 mm repeatability (creator claims via Hackster). Commander GUI, Python API, simulator, BOM + build docs. | **Closest match to Mechy's default** (printed, belts, steppers, documented BOM and assembly). Software stack and BOM structure are good templates. | Licence mismatch seen across mirrors (MIT badge vs GPLv3); README says still in development; repeatability claim unverified. | FREE (files) / kits PAID | https://github.com/PCrnjak/PAROL6-Desktop-robot-arm (v) ; https://source-robotics.com | CON, CAD, CTL, DOC |
| **Faze4** (Petar Crnjak, earlier) | 6-DOF printed, belts + cycloidal/planetary. | Earlier PAROL lineage; cycloidal reducer reference. | Older, less maintained. | FREE | https://github.com/PCrnjak/Faze4-Robotic-arm | CON |
| **Arctos** | 6-DOF printed, steppers, belt and cycloidal reductions, open STEP/STL. | Belt-driven printed arm with public CAD. | Licence terms (some parts NC). | FREE / kits PAID | https://arctosrobotics.com | CON, CAD |
| **SO-100 / SO-101** (TheRobotStudio + Hugging Face) | 5-DOF + gripper, printed, Feetech STS3215 serial bus servos; leader/follower pair for teleop + imitation learning via LeRobot. SO-101 supersedes SO-100 (easier assembly). | Cheapest well-documented arm; servo-in-joint layout; LeRobot data pipeline; calibration procedure. | Motors on links (violates "mass off distal links" rule, accepted at small scale); hobby-servo backlash and low torque (~1-3 N·m class, estimate). | FREE (Apache-2.0, check) | https://github.com/TheRobotStudio/SO-ARM100 ; https://github.com/huggingface/lerobot | CON, CTL, SIM |
| **Koch v1.1** (LeRobot ecosystem) | Low-cost Dynamixel-based leader/follower. | Same use as SO-101 with Dynamixel servos. | Dynamixel cost. | FREE | linked from LeRobot docs (verify repo) | RES |
| **Dummy Robot** (Peng Zhihui) | Small 6-DOF arm with harmonic/strain-wave reducers and custom closed-loop stepper drivers. | Compact joint integration, closed-loop stepper boards. | Docs mostly Chinese; precision parts. | FREE | https://github.com/peng-zhihui/Dummy-Robot | CON |
| **OpenArm** (Enactic, 2025) | Open 7-DOF humanoid-scale arm with QDD BLDC actuators. | Modern open BLDC arm reference. | Newer project, not verified here. | FREE (check) | https://openarm.dev (believed; verify) | RES |
| **ODRI Solo / Open Dynamic Robot Initiative** | Open BLDC actuator module, 9:1 two-stage belt reduction, printed housing. | **Belt-reduction actuator design** with published CAD + test data. | Legged focus; needs custom electronics. | FREE (BSD-3, check) | https://open-dynamic-robot-initiative.github.io | CON, CAD, CTL |
| **Stanford Pupper / Doggo** | Low-cost quadrupeds. | Linkage and belt-drive legs, cheap BLDC/servo control. | Not an arm. | FREE | https://github.com/stanfordroboticsclub | RES |

### 6.2 3D printers (as motion-system references)

| Project | Borrow | Cost | URL | Roles |
|---|---|---|---|---|
| **Voron Design** (2.4, Trident, 0.2) | Belt tensioning, GT2 belt path design, idlers with F695/625 bearings, printed part standards (ABS/ASA, 40% infill, 4 perimeters), excellent assembly manuals and BOM sourcing guides. | FREE (GPLv3) | https://vorondesign.com ; https://docs.vorondesign.com ; https://github.com/VoronDesign | CAD, DOC, CTL |
| **Prusa Research** (Original Prusa MK4/Core One, open source) | Reliable printed-part design, frame stiffness, Prusa assembly manuals (gold standard for build docs with photos and step lists). | FREE (GPLv3) | https://github.com/prusa3d ; https://help.prusa3d.com | DOC, CAD |
| **Rat Rig V-Core** | Extrusion frame + belt CoreXY reference with good docs. | FREE plans / kits PAID | https://ratrig.com | CAD |
| **Klipper** firmware | Kinematics, input shaping, TMC tuning; reference implementation for stepper motion. | FREE (GPLv3) | https://www.klipper3d.org | CTL |
| **OpenBuilds** (V-slot systems) | Extrusion-based linear motion, parts library. | FREE | https://openbuilds.com | CAD |

### 6.3 Actuators, drivers, motion firmware

| Project | What it is | Borrow | Cost | URL | Roles |
|---|---|---|---|---|---|
| **ODrive** | BLDC FOC controller. v3.6 hardware was open; newer S1/Pro are closed hardware with open docs. | Cascaded position/velocity/current loop structure, tuning guide, anticogging, encoder notes. | Board PAID; docs FREE | https://odriverobotics.com ; https://docs.odriverobotics.com | CTL |
| **mjbots moteus** | Compact BLDC FOC controller (open firmware/hardware) + qdd100 actuator. | Torque control, CAN-FD, practical tuning docs; QDD actuator reference. | Board PAID; source FREE | https://mjbots.com ; https://github.com/mjbots/moteus | CTL, CON |
| **SimpleFOC** | Arduino FOC library + open driver boards. | Cheapest route to BLDC position control; very readable docs on FOC theory. | FREE (MIT) | https://simplefoc.com ; https://docs.simplefoc.com ; https://github.com/simplefoc | CTL |
| **MIT Mini Cheetah actuator** (Katz) | QDD 6:1 planetary BLDC actuator. | Design rationale for low-ratio, backdrivable joints. | FREE (thesis) | https://dspace.mit.edu | CON, CTL |
| **VESC** | Open BLDC controller (e-skate origin). | Robust high-current FOC, motor detection. | FREE (GPL) | https://vesc-project.com | CTL |
| **grblHAL / FluidNC** | Stepper motion firmware. | Step generation, homing, G-code-driven arm control (Thor uses GRBL lineage). | FREE | https://github.com/grblHAL ; https://github.com/bdring/FluidNC | CTL |
| **MKS SERVO42 / closed-loop stepper boards** | Encoder-on-stepper closed-loop drivers. | Skipped-step protection on belt arms. | PAID boards | vendor sites | CTL |

---

## 7. Supplier catalogues with engineering data

Use these as T1 for the exact part, and as cheap T3 tutorials. Buy-link stability varies; cite
part number + access date.

| Supplier | What engineering data | Cost | URL | Roles |
|---|---|---|---|---|
| **McMaster-Carr** | Huge catalogue with clean specs, free STEP/CAD for nearly every part, short "About" technical notes per category (fastener grades, bearing types, belt profiles). Best place to find a real part number fast. | FREE (US shipping) | https://www.mcmaster.com | CAD, RES |
| **Misumi** | Configurable parts (shafts, pulleys, extrusions) with CAD; extensive **technical data pages** (fits/tolerances, belt calcs, linear guide life, material properties). | FREE | https://us.misumi-ec.com (tech data under "Technical Information") | CAD |
| **SKF** | Product pages with C, C0, limiting speed, dimensions; online **SKF Bearing Select** life calculator (ISO 281 modified life); Rolling Bearings catalogue PDF. | FREE* | https://www.skf.com | CAD, SIM |
| **NSK / NTN / Timken / Schaeffler (FAG/INA)** | Alternative bearing catalogues with technical sections (preload, lubrication, fits). Schaeffler "medias" tool. | FREE | https://www.nsk.com ; https://www.ntnglobal.com ; https://www.timken.com ; https://medias.schaeffler.com | CAD |
| **igus** | iglidur plastic plain bearings with **online service-life calculators**, drylin linear guides, chainflex cables, energy chains, robolink/ReBeL low-cost robot joints. Real test-lab wear data. | FREE | https://www.igus.com | CAD, CON |
| **Gates** | PowerGrip GT2/GT3/HTD design manuals: belt width selection, tension (span-deflection method), minimum pulley teeth, teeth-in-mesh correction. Gates Design Flex Pro / Design IQ online tools. | FREE* | https://www.gates.com | CAD, CTL |
| **Optibelt / Megadyne / Continental (Synchroflex)** | Timing-belt manuals with tension and stiffness data; useful for belt stiffness (compliance) in sim. | FREE | https://www.optibelt.com ; https://www.megadyne.com ; https://www.continental-industry.com | SIM, CAD |
| **SDP/SI (Stock Drive Products)** | Timing belts, pulleys, gears with technical handbook sections (centre distance, belt length). | FREE | https://www.sdp-si.com | CAD |
| **Oriental Motor** | **Motor sizing calculations** (load inertia, acceleration torque, safety margin), stepper vs servo guides, technical reference, online sizing tool. | FREE | https://www.orientalmotor.com (Technical Support → Technical Reference / Motor Sizing) | CTL, SIM |
| **Trinamic (now Analog Devices)** | TMC2209/TMC2226/TMC5160 datasheets; app notes on StealthChop vs SpreadCycle, StallGuard sensorless homing, CoolStep, microstep resolution, motor parameter calculations. | FREE | https://www.analog.com (search "TMC2209", "Trinamic application notes") | CTL |
| **maxon** | Motor data sheets with full constants, selection program, "maxon formulae handbook", gearhead/encoder data. | FREE | https://www.maxongroup.com | CTL, SIM |
| **Faulhaber** | Technical library: motor constants, thermal behaviour, tutorials. | FREE | https://www.faulhaber.com | CTL |
| **LDO Motors / StepperOnline** | Cheap NEMA steppers with real torque-speed curves (LDO in particular); the parts hobby arms actually use. | FREE datasheets | https://www.ldomotors.com ; https://www.omc-stepperonline.com | CTL, CAD |
| **Robotis (Dynamixel) e-Manual** | Servo specs, control tables, torque curves. | FREE | https://emanual.robotis.com | CTL |
| **Feetech** | STS3215 serial bus servo (SO-101). | FREE datasheet | https://www.feetechrc.com | CTL |
| **Harmonic Drive LLC** | Strain-wave gear engineering data (stiffness curves, ratings). | FREE | https://www.harmonicdrive.net | CON |
| **THK / HIWIN / Bosch Rexroth** | Linear guide and ball screw catalogues with life and rigidity calculations. | FREE | https://www.thk.com ; https://www.hiwin.com ; https://www.boschrexroth.com | CAD |
| **Lee Spring** | Spring catalogue + calculators. | FREE | https://www.leespring.com | CAD |
| **Ruland** | Shaft couplings, collars; technical articles on misalignment. | FREE | https://www.ruland.com | CAD |
| **Bossard / Würth** | Fastener technical handbooks (preload, friction, thread engagement). | FREE | https://www.bossard.com ; https://www.wurth.com | CAD |
| **Pololu / Adafruit / SparkFun** | Motor drivers, encoders, tutorials with tested data. | FREE | https://www.pololu.com ; https://learn.adafruit.com ; https://learn.sparkfun.com | CTL |
| **Digi-Key / Mouser / Octopart / LCSC** | Datasheets for every electronic part; parametric search. | FREE | https://www.digikey.com ; https://www.mouser.com ; https://octopart.com ; https://www.lcsc.com | CTL |
| **Filament makers: Prusament, Polymaker, Bambu Lab, eSun** | Technical data sheets (tensile, HDT, Tg) and sometimes layer-direction data. | FREE | https://prusament.com ; https://polymaker.com ; https://bambulab.com ; https://www.esun3d.com | CAD, SIM |
| **JLCPCB / JLC3DP / PCBWay** | PCB and print/CNC services with DfM rules. | FREE | https://jlcpcb.com ; https://www.pcbway.com | CAD, CTL |

---

## 8. Standards bodies and the standards Mechy actually touches

Standards are mostly PAID. Free paths: ISO OBP (preview of scope, terms, often first pages),
public summaries by vendors (Misumi, Engineering Toolbox), US government standards (NASA, MIL),
national libraries, and university library access.

### 8.1 Bodies

| Body | URL | Notes |
|---|---|---|
| **ISO** | https://www.iso.org ; preview: https://www.iso.org/obp | International; most mechanical standards. |
| **IEC** | https://www.iec.ch | Electrical, motors, machine electrical safety. |
| **ASME** | https://www.asme.org/codes-standards | US: GD&T (Y14.5), drawings, fasteners (B18), keys, chains. |
| **DIN / DIN Media** (ex Beuth) | https://www.din.de ; https://www.dinmedia.de | German; many fastener/part standards (DIN 912, 933, 625) still in common use in hobby BOMs, mostly replaced by ISO equivalents. |
| **ANSI webstore** | https://webstore.ansi.org | Buy ISO/ASME/IEC in one place. |
| **ASTM International** | https://www.astm.org | Material tests (D638 plastics tensile, E8 metals). |
| **AGMA** | https://www.agma.org | US gear rating standards. |
| **SAE** | https://www.sae.org | Automotive; fasteners (J429), materials. |
| **BSI / JIS** | https://www.bsigroup.com ; https://www.jisc.go.jp | British / Japanese national standards. |
| **NEMA** | https://www.nema.org | Motor frame conventions (NEMA 17 = 1.7 in face, about 42.3 mm). |
| **Khronos (glTF)** | https://www.khronos.org/gltf | GLB/glTF format spec (Mechy viewer). FREE. |

### 8.2 Standards map (what, why, roles)

| Standard | Topic | Why Mechy cares | Roles |
|---|---|---|---|
| ISO 286-1/-2 | Limits and fits (H7/g6 etc.) | Bearing seats, shaft fits; printed parts need compensation beyond this. | CAD |
| ISO 2768-1/-2 | General tolerances | Default tolerance note on drawings. | CAD, DOC |
| ISO 1101 / ASME Y14.5-2018 | GD&T | Specifying flatness/position for machined parts. | CAD, DOC |
| ISO 128 / ASME Y14.100 | Technical drawing practice | Docs role drawing conventions. | DOC |
| ISO 898-1 | Steel bolt property classes (8.8, 10.9, 12.9) | Bolt strength in bom.csv. | CAD |
| ISO 4762 (was DIN 912), ISO 4017, ISO 7380, ISO 10642 | Socket head, hex, button, countersunk screws | Correct screw names and dimensions. | CAD |
| ISO 15 / ISO 281 / ISO 76 | Bearing dimensions, dynamic life (L10), static rating | Bearing selection (608, 6000-series, 51105 thrust). | CAD, SIM |
| ISO 5296 / ISO 13050 | Synchronous belts (trapezoidal / curvilinear incl. GT-like profiles) | Belt profile references. GT2 itself is a Gates proprietary profile. | CAD |
| ISO 6336 / AGMA 2001 | Gear load capacity | If spur/planetary gears are used. | CAD |
| ISO 9409-1 | Robot mechanical interface (tool flange) | End-effector mounting pattern. | CAD, CON |
| ISO 9283 | Robot performance criteria (repeatability, accuracy) | Defining and testing repeatability correctly. | PLN, SIM, DOC |
| ISO 10218-1/-2 (2025 revision) | Industrial robot safety | Safety requirements framing; hobby arms not certified. | PLN, DOC |
| ISO/TS 15066 (being folded into ISO 10218) | Collaborative robot force/pressure limits | Human contact limits if the arm is near people. | PLN, CTL |
| ISO 12100 | Machinery risk assessment | Risk-assessment structure for docs. | PLN, DOC |
| ISO 13849-1 | Safety-related control systems (PL a-e) | E-stop and interlock design. | CTL |
| IEC 60204-1 | Electrical equipment of machines | Wiring, E-stop category, PE. | CTL, DOC |
| IEC 60034 | Rotating electrical machines | Motor ratings, duty cycles. | CTL |
| ISO/ASTM 52900, 52910 | AM terminology; DfAM guidelines | Vocabulary and design rules for printed parts. | CAD |
| ASTM D638 / ISO 527 | Plastic tensile tests | Understanding filament datasheet numbers. | CAD, SIM |
| ISO 10303-242 (STEP AP242) | CAD exchange | STEP export from build123d. | CAD |
| URDF / SDF / MJCF specs | Robot description formats | Sim and ROS interop. FREE (wiki.ros.org/urdf, sdformat.org, mujoco docs). | SIM |

Free legal sources for some standards: https://law.resource.org (US incorporated-by-reference
codes), https://standards.nasa.gov, https://quicksearch.dla.mil. Do not use pirated PDFs.

---

## 9. CAD libraries, model repositories, datasets

| Resource | What | Cost | URL | Good for | Roles |
|---|---|---|---|---|---|
| **GrabCAD Community Library** | Millions of user CAD models (STEP, native). | FREE* | https://grabcad.com/library | Reference geometry of arms, motors, grippers. Quality varies; licences unclear (default GrabCAD terms limit commercial use). | RES, CAD |
| **Printables** (Prusa) | Printable models with licences shown per model; good engineering-oriented community. | FREE* | https://www.printables.com | Printable arm parts, cycloidal drives, belt tensioners. | RES, CAD |
| **Thingiverse** | Oldest printable model site. | FREE* | https://www.thingiverse.com | Huge archive (Moveo, early arms). Many STL-only, unmaintained. | RES |
| **MakerWorld** (Bambu Lab) | Printables-like site; PAROL6 posted there. | FREE* | https://makerworld.com | Same. | RES |
| **Thangs** | Model search engine across sites. | FREE* | https://thangs.com | Geometric search for similar parts. | RES |
| **TraceParts** | Manufacturer-certified CAD for industrial parts (bearings, motors, linear guides). | FREE* | https://www.traceparts.com | Exact purchased-part geometry. | CAD |
| **PARTcommunity (CADENAS)** | Same as TraceParts, different vendor set. | FREE* | https://www.partcommunity.com | Exact purchased-part geometry. | CAD |
| **3D ContentCentral** (Dassault) | Supplier and user models. | FREE* | https://www.3dcontentcentral.com | Purchased parts. | CAD |
| **McMaster / Misumi CAD downloads** | STEP per part number. | FREE | see sec. 7 | Most reliable dimensions for hardware. | CAD |
| **bd_warehouse** (build123d) / **cq_warehouse** (CadQuery) | Parametric fasteners (ISO screws, nuts, washers), bearings, threads, chains, sprockets as code. | FREE (Apache-2.0) | https://github.com/gumyr/bd_warehouse ; https://github.com/gumyr/cq_warehouse | **Direct use in Mechy CAD** to model real screws/bearings at true size. | CAD |
| **FreeCAD Fasteners workbench / BOLTS** | Parametric standard parts. | FREE | https://github.com/shaise/FreeCAD_FastenersWB | Cross-check dimensions. | CAD |
| **Onshape public documents** | Public parametric models searchable in Onshape. | FREE* | https://www.onshape.com | Inspect parametric arm designs. | RES |
| **MuJoCo Menagerie** (Google DeepMind) | Curated, tuned MJCF models of real robots (arms, hands, quadrupeds), incl. low-cost arms. | FREE (per-model licences) | https://github.com/google-deepmind/mujoco_menagerie | Reference MJCF practice: actuator gains, armature, damping, contact settings. | SIM |
| **robot_descriptions.py** | One-line loader for 100+ URDF/MJCF robot descriptions. | FREE | https://github.com/robot-descriptions/robot_descriptions.py | Quick comparisons of link masses/inertias of real arms. | SIM, RES |
| **ABC Dataset** | 1M CAD models (NYU). | FREE | https://deep-geometry.github.io/abc-dataset/ | ML on CAD; not needed for design. | RES |
| **Fusion 360 Gallery Dataset** (Autodesk) | Sketch/extrude sequences and assemblies with joints. | FREE (research licence) | https://github.com/AutodeskAILab/Fusion360GalleryDataset | Examples of design-sequence data; joint/assembly datasets. | RES |
| **DeepCAD / Text2CAD datasets** | CAD command sequences, text-to-CAD pairs. | FREE (research) | GitHub (search titles) | Benchmarks for LLM-driven CAD. | RES |
| **Open X-Embodiment / LeRobot datasets** | Robot manipulation trajectories. | FREE | https://huggingface.co/lerobot ; https://robotics-transformer-x.github.io | Realistic motion profiles for SO-101-class arms. | CTL, SIM |
| **KiCad libraries** | Electronic symbols/footprints/3D models. | FREE | https://www.kicad.org/libraries/ | Electronics enclosure geometry. | CTL, CAD |

---

## 10. Role-by-role reading lists

Short lists so each agent knows its top sources. "Must" = consult before acting on that topic.

### Planner (PLN)
1. Must: Ullman (process, requirement → spec), Pahl & Beitz (function structure), Ulrich & Eppinger (concept selection).
2. Must for scope/safety framing: ISO 12100 (risk assessment), ISO 10218 / ISO/TS 15066 (if humans nearby), ISO 9283 (how to specify repeatability).
3. Slocum FUNdaMENTALS chapter 1-2 (design process, "FRDPARRC" tables).
4. Open-hardware arms (sec. 6.1) to set realistic targets (payload, reach, cost).

### Research (RES)
1. Must: sec. 6 projects (read LICENSE, BOM, issues tab for failure modes).
2. Printables/GrabCAD/Thingiverse/MakerWorld search; Hackaday.io build logs.
3. arXiv/Google Scholar for low-cost arm and QDD papers (sec. 5).
4. NTRS for public-domain mechanism data; Aerospace Mechanisms Symposium for failure lessons.
5. Supplier catalogues (sec. 7) to confirm parts exist and are buyable.

### Concept (CON)
1. Must: Slocum FUNdaMENTALS / Precision Machine Design (Abbe, Saint-Venant, exact constraint, stiffness).
2. Lynch & Park (workspace, singularities, DOF choice).
3. Norton Design of Machinery, Sclater, 507 Movements, KMODDL (mechanism options).
4. Ashby (material indices for links).
5. ODRI/Berkeley Blue/Katz (belt and QDD actuator architectures).

### CAD (CAD)
1. Must: build123d docs, bd_warehouse; McMaster/Misumi/TraceParts CAD for purchased parts.
2. Must: SKF (bearings), Gates (belts), datasheets of the exact motor.
3. Shigley / Norton / Roymech / Bolt Science (shafts, bolts, keys).
4. Prusa KB, CNC Kitchen, Hubs/Protolabs DfAM, Ellis guide (printability, hole compensation, inserts).
5. ISO 286/2768/4762 summaries (fits, tolerances, screw dims).
6. Voron docs (belt paths, tensioners, printed part standards).

### Simulation (SIM)
1. Must: MuJoCo docs, MuJoCo Menagerie (modelling practice).
2. Must for verification: Roark's, Hibbeler/Meriam (closed-form checks), Lynch & Park (FK/Jacobian checks), Featherstone (dynamics).
3. Drake / Pinocchio / Robotics Toolbox as independent cross-checks.
4. Belt stiffness from Gates/Optibelt/Megadyne manuals; motor curves from LDO/Oriental/maxon.
5. NIST e-Handbook (statistics of Monte Carlo / random-pose results).

### Controls (CTL)
1. Must: Åström & Murray FBS (free), python-control.
2. Must: Trinamic/ADI TMC app notes, Klipper docs (stepper + belt practice), Oriental Motor sizing.
3. Ogata / Franklin-Powell (classical design), Åström & Hägglund (PID details).
4. Spong (independent-joint control with transmissions), Lynch & Park ch. 11 (robot control).
5. ODrive, moteus, SimpleFOC docs (if moving to BLDC).
6. Horowitz & Hill (power, grounding, noise); IEC 60204-1 / ISO 13849 (E-stop).

### Docs (DOC)
1. Must: Prusa and Voron assembly manuals as style exemplars (one action per step, photo/render per step, part callouts, torque values).
2. ISO 128 / ASME Y14.100 / ISO 2768 (drawing notes).
3. Licence obligations (sec. 1.2): credit every adapted design.
4. ISO 12100 for a safety section; ISO 9283 vocabulary when quoting repeatability.

---

## 11. Common mistakes when using sources

1. **Quoting a generic "NEMA 17 torque"**: holding torque varies about 3x across stack lengths,
   and usable torque at speed is much lower than holding torque. Use the pull-out curve of the
   exact motor at the supply voltage and driver current (Oriental Motor / LDO curves).
2. **Using filament datasheet strength as part strength**: datasheets are often injection-moulded
   or XY-printed specimens; Z-direction (layer adhesion) strength can be well under half
   (typical, CNC Kitchen tests and vendor TDS that report both). Always state print orientation.
3. **Treating GT2 as an ISO standard profile**: it is Gates' proprietary profile; clone belts vary
   (glass vs steel cord, tooth fit). Use Gates data as upper-bound reference and derate clones.
4. **Mixing DH conventions**: Craig uses modified DH, Spong uses standard DH, Lynch & Park use PoE.
   Say which one in every kinematics note; AR4 publishes modified DH.
5. **Old edition equation numbers**: cite section titles, not only equation numbers.
6. **Copying an open design without its licence**: see 1.2. NC licences block commercial use.
7. **Trusting a single creator claim** (e.g. 0.08 mm repeatability on PAROL6): mark as "creator
   claim, unverified" unless measured per ISO 9283.
8. **Assuming free = pirated**: Modern Robotics, FBS, Planning Algorithms, Tedrake notes, Slocum
   FUNdaMENTALS, Brunton & Kutz, NASA/MIL docs are legally free from the authors/government.
   Never link pirate mirrors.
9. **Ignoring the issues tab**: for open hardware, GitHub issues/forums list the real failure
   modes (belt slip, cracked printed pulleys, backlash) faster than the README.
10. **Engineering Toolbox as final authority**: fine for sanity checks, not for a safety factor.

---

## 12. Worked mini-examples of source use

### 12.1 Choosing a bearing for a base yaw joint
1. Concept from Slocum FUNdaMENTALS (bearing chapter): separate axial load (thrust bearing) from
   moment/radial (radial pair spaced apart).
2. Candidate 51105 thrust + 608-2RS (Mechy default). Get C and C0 from SKF product pages (T1).
3. Life method: ISO 281 basic L10 = (C/P)^p × 10^6 rev with p = 3 for ball bearings (Shigley ch.
   11 and SKF catalogue agree; T1+T2, two sources).
4. Note: `[src] SKF 51105 page, C0 = <value>, accessed <date>`; label loads as computed.

### 12.2 Sizing a GT2 belt stage
1. Gates PowerGrip GT design manual (T3): minimum pulley teeth, belt width vs torque table,
   teeth-in-mesh factor (needs at least ~6 teeth in mesh, typical per Gates; verify in manual).
2. Cross-check centre distance / belt length with SDP/SI or Misumi formula (two sources).
3. Belt stiffness for sim from Gates/Megadyne specific stiffness data, or estimate and label.
4. Klipper docs: rotation_distance = pulley teeth × pitch for linear; for rotary joints use the
   pulley ratio.

### 12.3 Verifying a sim gravity-torque result (standards rule 5)
1. Closed form: τ = Σ m_i g r_i (horizontal arm), from Hibbeler/Meriam statics (T2).
2. Independent tool: Pinocchio RNEA with zero velocity/acceleration, or Robotics Toolbox
   `rne`. Compare to MuJoCo `qfrc_bias`.
3. Verification table: | Check | Expected | Got | PASS/FAIL |.

### 12.4 Picking a control approach for stepper joints
1. Read TMC2209 datasheet + Trinamic app notes: StealthChop (quiet, lower torque at speed) vs
   SpreadCycle (better at speed/load). Typical guidance: SpreadCycle for loaded robot joints.
   (T1/T3; verify the current app note wording.)
2. Oriental Motor sizing: acceleration torque = (J_load/ratio² + J_rotor) × α, plus load torque,
   with a safety factor (Mechy uses 50%).
3. FBS ch. on PID only if closing a loop on encoders (AR4-style closed loop).

---

## Canonical references

Compact list; full annotations above. FREE = legally free online.

**Books (paid unless noted)**
- Oberg et al., *Machinery's Handbook* — https://www.industrialpress.com
- Budynas & Nisbett, *Shigley's Mechanical Engineering Design* — https://www.mheducation.com
- Norton, *Machine Design* (Pearson); *Design of Machinery* (McGraw-Hill)
- Young, Budynas, Sadegh, *Roark's Formulas for Stress and Strain*, 9th ed.
- Ashby, *Materials Selection in Mechanical Design* — https://www.elsevier.com
- Slocum, *Precision Machine Design* (SME); *FUNdaMENTALS of Design* — FREE https://pergatory.mit.edu/resources/FUNdaMENTALS.html
- Hale, *Principles and Techniques for Designing Precision Machines* — FREE https://www.osti.gov
- Blanding, *Exact Constraint* (ASME Press)
- Craig, *Introduction to Robotics*, 4th ed. (Pearson)
- Lynch & Park, *Modern Robotics* — FREE preprint https://hades.mech.northwestern.edu/index.php/Modern_Robotics
- Spong, Hutchinson, Vidyasagar, *Robot Modeling and Control* (Wiley)
- Murray, Li, Sastry, *A Mathematical Introduction to Robotic Manipulation* — FREE https://www.cds.caltech.edu/~murray/mlswiki
- Featherstone, *Rigid Body Dynamics Algorithms* (Springer)
- LaValle, *Planning Algorithms* — FREE http://lavalle.pl/planning
- Tedrake, *Underactuated Robotics* / *Robotic Manipulation* — FREE https://underactuated.mit.edu , https://manipulation.mit.edu
- Horowitz & Hill, *The Art of Electronics*, 3rd ed. — https://artofelectronics.net
- Hughes & Drury, *Electric Motors and Drives* (Newnes)
- Ogata, *Modern Control Engineering* (Pearson)
- Åström & Murray, *Feedback Systems*, 2nd ed. — FREE https://fbsbook.org
- Franklin, Powell, Emami-Naeini, *Feedback Control of Dynamic Systems* (Pearson)
- Brunton & Kutz, *Data-Driven Science and Engineering* — FREE https://databookuw.com
- Hibbeler, *Statics*, *Dynamics*, *Mechanics of Materials* (Pearson)
- Meriam, Kraige, Bolton, *Engineering Mechanics* (Wiley)
- Ullman, *The Mechanical Design Process*
- Pahl, Beitz et al., *Engineering Design: A Systematic Approach* (Springer)
- Ulrich & Eppinger, *Product Design and Development*
- Boothroyd, Dewhurst, Knight, *Product Design for Manufacture and Assembly*
- Brown, *507 Mechanical Movements* — FREE http://507movements.com

**Free courses**
- MIT OCW 2.007 — https://ocw.mit.edu/courses/2-007-design-and-manufacturing-i-spring-2009/
- MIT OCW 2.72 — https://ocw.mit.edu/courses/2-72-elements-of-mechanical-design-spring-2009/
- MIT OCW 2.003SC — https://ocw.mit.edu/courses/2-003sc-engineering-dynamics-fall-2011/
- MIT OCW 2.004, 2.12, 2.14, 2.75, 2.008 — https://ocw.mit.edu
- Stanford CS223A (Khatib) — https://see.stanford.edu
- Coursera Modern Robotics (Northwestern) — https://www.coursera.org/specializations/modernrobotics
- QUT Robot Academy — https://robotacademy.net.au

**Free sites**
- https://www.engineeringtoolbox.com , https://www.efunda.com , https://roymech.org , https://www.boltscience.com
- https://ntrs.nasa.gov , https://standards.nasa.gov , https://quicksearch.dla.mil , https://www.itl.nist.gov/div898/handbook/
- https://hackaday.io , https://help.prusa3d.com , https://www.cnckitchen.com , https://www.klipper3d.org
- https://mujoco.readthedocs.io , https://build123d.readthedocs.io , https://github.com/google-deepmind/mujoco_menagerie

**Standards (paid; preview at ISO OBP)**
- ISO 286, 2768, 1101, 898-1, 4762, 281, 76, 13050, 9409-1, 9283, 10218, TS 15066, 12100, 13849, ISO/ASTM 52910; IEC 60204-1; ASME Y14.5-2018, Y14.100
- Bodies: https://www.iso.org , https://www.iec.ch , https://www.asme.org , https://www.dinmedia.de , https://www.astm.org , https://www.agma.org

**Open hardware**
- PAROL6 https://github.com/PCrnjak/PAROL6-Desktop-robot-arm ; AR4 https://www.anninrobotics.com ; Thor https://github.com/AngelLM/Thor ; Moveo https://github.com/BCN3D/BCN3D-Moveo ; SO-ARM100/101 https://github.com/TheRobotStudio/SO-ARM100 ; LeRobot https://github.com/huggingface/lerobot
- Voron https://vorondesign.com ; Prusa https://github.com/prusa3d
- ODrive https://odriverobotics.com ; moteus https://github.com/mjbots/moteus ; SimpleFOC https://simplefoc.com ; ODRI https://open-dynamic-robot-initiative.github.io

**Suppliers**
- https://www.mcmaster.com , https://us.misumi-ec.com , https://www.skf.com , https://www.igus.com , https://www.gates.com , https://www.orientalmotor.com , https://www.analog.com (Trinamic) , https://www.maxongroup.com

## Gaps / not verified

1. Only these URLs were confirmed live by web search on 2026-10-23: Slocum FUNdaMENTALS pages
   (pergatory + meddevdesign), PAROL6 GitHub, Modern Robotics wiki, MIT OCW 2.72, FBS move to
   fbsbook.org, AR4 coverage. All other URLs are from long-stable domains but were not fetched.
2. SO-ARM100 canonical repo (TheRobotStudio) did not appear in search results (only forks); URL
   is from memory. Licence (Apache-2.0) not verified.
3. AR4 ROS 2 driver repo URL, OpenArm URL, Koch v1.1 repo, and Faze4 repo URL are from memory.
4. Book edition numbers (Machinery's Handbook 32nd, Norton 6th, Ullman 6th and its current
   publisher) are approximate; check before citing.
5. Licences for Moveo, Thor, Arctos, ODRI listed as "check": not read from LICENSE files.
6. AR4 payload/reach figures conflict between sources (1 kg / 600 mm vs 1.9 kg / 630 mm).
7. PAROL6 repeatability (0.08 mm) and payload (1 kg) are creator claims, not independently tested.
8. Typical values in sec. 11-12 (NEMA 17 torque range, Z-strength fraction, teeth-in-mesh count)
   are estimates for orientation only; the dedicated knowledge files should carry sourced numbers.
9. Coursera "free to audit" status changes over time; not verified for 2026.
10. Exact location of Gates design manuals and Trinamic app notes on vendor sites (pages move
    after acquisitions, e.g. Trinamic → Analog Devices) not verified.
