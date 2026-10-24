# CAD, simulation and engineering verification: practice reference

For Mechy agents (cad, sim, controls, docs, research). Read this before you write a generator, export a file,
run FEA or a MuJoCo sim, or write a verification table. Mechy's stack is **build123d** (OCCT B-rep CAD) ->
STEP / STL / GLB / MJCF, then **MuJoCo** (`implicitfast`, 0.5 ms step in `cad/mjcf.py`) for dynamics.
Numbers are labelled *typical*, *estimate* or *default (docs)*, with the source. SI units unless stated; CAD
geometry is in mm by convention.

Contents
1. The verification mindset (read this first)
2. Parametric CAD best practice: design intent, references, assemblies, mates
3. Code-CAD: build123d, CadQuery, OpenSCAD idioms and pitfalls
4. File formats and when to use each
5. Mesh quality for 3D printing and for simulation
6. FEA fundamentals
7. Open FEA tools
8. Multibody / physics simulation (MuJoCo, PyBullet, Drake)
9. Tolerance analysis
10. Closed-form results library for verification
11. Writing verification tables
12. Sanity checks for simulation output
13. BOM and print-list conventions
14. Checklists
15. Canonical references
16. Gaps / not verified

---

## 1. The verification mindset

Three different questions, never confuse them:

| Term | Question | Example |
|---|---|---|
| Code verification | Does the solver solve the equations correctly? | MuJoCo free-fall matches `z = z0 - g t^2/2` |
| Solution verification | Is my discretisation fine enough? | Mesh convergence study, timestep halving |
| Validation | Do the equations describe reality? | Measured arm deflection vs FEA |

(Terminology from ASME V&V 10 / Roache; see refs.) Mechy can usually do the first two in software;
validation needs a physical test and must be listed under "Not verified" until one exists.

Rules of thumb:
- **Every new analysis gets a trivially simple twin with a known answer** (a cantilever, a pendulum, a
  dropped ball) run through the *same* pipeline, same units, same export path. If the twin fails, nothing
  downstream counts.
- **Garbage in is the usual failure**, not the solver: wrong units (mm vs m is a 1000x or 10^9x error in
  inertia), wrong material, wrong boundary condition, wrong sign of gravity, wrong joint axis.
- **Check order of magnitude before precision.** Estimate the answer by hand to +/-50% before you run
  anything. If the tool disagrees by >2x, the tool setup is wrong until proven otherwise.
- **Random/sweep checks beat one point** (Mechy standard 5: e.g. 500 random poses).
- **Change one thing at a time** and keep the old result to compare against.

---

## 2. Parametric CAD best practice

### 2.1 Design intent
Design intent = which dimensions are the *inputs* and how the rest should react when they change.
- Drive geometry from a small set of named parameters (link length, bearing OD, belt pitch, wall,
  clearance). Derive everything else (`boss_od = bearing_od + 2*wall`). Mechy: params live in
  `params.yaml`; generators must not contain magic numbers that duplicate a parameter.
- Dimension to **functional** features: bearing bore centre-to-centre, not edge-to-edge. Belt centre
  distance is a function of belt length and pulley teeth, not a free number.
- Put purchased-part dimensions in one table (bearing OD/ID/width, screw clearance, nut flats) and look
  them up. Never retype `22` for a 608 OD in three places.
- Test intent by **flexing**: change each key parameter +/-20% and rebuild. If it fails or produces
  nonsense, the model has hidden dependencies. Do this in CI for generators (cheap, catches most bugs).

### 2.2 Robust references (the "topological naming problem")
- Reference **datum planes, axes, origin and sketches**, not faces/edges created by earlier features.
  Generated face IDs change when upstream topology changes (FreeCAD calls this the topological naming
  problem; mitigated but not eliminated in FreeCAD 1.0).
- In code-CAD, never select by index (`faces()[3]`). Select by geometry: direction (`>Z`), position
  (`sort_by(Axis.Z)[-1]`), type (`filter_by(GeomType.CIRCLE)`), or by tags/labels you set yourself.
- Build features from sketches on known planes, then fillet/chamfer **last** (they add faces and are the
  most fragile operation; build123d docs, "Tips").
- Prefer 2D operations (sketch + extrude/revolve) over 3D boolean chains; they are faster and fail less.

### 2.3 Feature order (typical)
1. Skeleton: datum planes, joint axes, key points (layout sketch).
2. Primary solids from sketches.
3. Holes and pockets for purchased parts (bearing seats, screw holes, nut traps).
4. Ribs, cosmetic cuts.
5. Fillets / chamfers.
6. Print-specific tweaks (teardrop holes, elephant-foot chamfer, sacrificial bridges).

### 2.4 Assemblies and mates
- **Ground one part** (base). Everything else is located relative to it.
- **Skeleton / top-down layout** for mechanisms: one layout defines joint axes and link frames; parts are
  built in their own local frame and placed at that frame. This makes the CAD frame = the joint frame =
  the MJCF body frame, which removes a whole class of sim bugs.
- Mates (SolidWorks/Onshape/FreeCAD Assembly) remove DOF. A mechanism assembly should end with exactly
  the mechanism DOF remaining. Count with Grübler-Kutzbach:
  - Spatial: `M = 6(n - 1) - sum(6 - f_i)`; planar: `M = 3(n - 1) - 2 j1 - j2`
  - `n` = links including ground, `f_i` = DOF of joint i, `j1` = 1-DOF joints, `j2` = 2-DOF joints.
  - Worked: 4-bar linkage: n = 4, j1 = 4 -> M = 3*3 - 8 = 1. A 3-DOF serial arm: n = 4, three revolutes
    -> M = 6*3 - 3*5 = 3.
  - Formula ignores special geometry (parallel axes can create redundant constraints; Mechy's belt
    parallelograms are over-constrained in 3D and need clearance or a compliant joint).
- Avoid redundant mates (two concentric mates on one shaft). They solve in CAD but hide over-constraint
  that becomes binding in the real print. Use one concentric + one coincident per revolute.
- Run **interference detection** in the home pose and across the range of motion (sweep each joint).
- Keep purchased parts as separate bodies (or simplified envelopes) so BOM and collision use them.

### 2.5 Mass properties from CAD
- CAD mass = volume x density. For FDM parts use an *effective* density: `rho_eff ~= rho_material *
  (shell_fraction + (1 - shell_fraction) * infill)`. Estimate shell fraction from perimeters and part
  size; a simpler rule: thin parts (<6 mm) ~ solid, chunky parts ~ 40-60% of solid at 20% infill
  (estimate, verify by weighing a print). PLA ~1.24 g/cm^3, PETG ~1.27, ABS ~1.04, PA12/nylon ~1.01-1.14
  (typical datasheet values, cross-check with your filament's sheet).
- Inertia tensor must be about the **CoM**, in a stated frame, in kg m^2 for sims. Validity check:
  principal moments positive and satisfying the triangle inequality `I1 + I2 >= I3` (MuJoCo rejects
  violators unless `balanceinertia` is set).
- Add purchased parts' masses (steppers are often the heaviest items: NEMA17 ~0.28-0.40 kg; 608 bearing
  ~12 g; typical datasheet values).

---

## 3. Code-CAD

### 3.1 Shared idioms (OCCT-based: build123d and CadQuery)
- Units are unitless floats; **convention is mm**. Convert to metres exactly once, at the MJCF/GLB
  boundary (Mechy: `arm.glb` and `arm.xml` in m, STEP/STL in mm).
- Check validity after booleans: `shape.is_valid()` (build123d) / `.val().isValid()` (CadQuery). Valid does
  not guarantee printable (build123d docs warn self-touching shapes may pass).
- Coplanar / co-tangent booleans fail or produce slivers. **Overlap cutters by 0.01-0.1 mm** past the face
  they cut, and overlap fused bodies by the same.
- Booleans between many small features are slow; build one cutter compound and subtract once.
- Fillet radius must be < adjacent face size and < wall thickness; fillet failures usually mean the radius
  consumes a neighbouring edge. Fillet in 2D where possible.
- Threads: model as plain holes for printing (use heat-set inserts or tap); real helical threads are slow
  and fragile in OCCT.
- Exchange between libraries via the wrapped OCP shape (`shape.wrapped`).

### 3.2 build123d (Mechy's CAD kernel)
- Two styles: **builder mode** (`with BuildPart() as p: ...`, implicit context) and **algebra mode**
  (`part = Box(10,10,5) - Cylinder(2, 5)`). Algebra mode is easier for generators and functions that
  return shapes; builder mode is easier for interactive, sketch-heavy parts. Do not mix inside one function.
- Placement: `Pos(x, y, z) * Rot(0, 0, 45) * shape` or `Location(...)`. `Locations`, `GridLocations`,
  `PolarLocations` in builder mode place multiple features (hole patterns).
- Selectors: `part.faces().sort_by(Axis.Z)[-1]` (top face), `.edges().filter_by(Axis.Z)` (vertical edges),
  `.group_by(Axis.Z)[-1]` (everything at max Z), `.filter_by(GeomType.CIRCLE)`.
- **Pitfall: sketch selectors use global coordinates** while the sketch is built on local `Plane.XY`;
  sorting inside `BuildSketch(Plane.XZ)` can surprise you (build123d docs, "Tips").
- **Pitfall: nested builders do not inherit the parent's placement.**
- `Joint`s (`RigidJoint`, `RevoluteJoint`, `LinearJoint`) can connect parts by named frames; useful to keep
  CAD frames equal to sim frames.
- Export: `export_step(shape, path)`, `export_stl(shape, path, tolerance=, angular_tolerance=)`,
  `export_gltf(shape, path, binary=True, linear_deflection=, angular_deflection=)`. `tolerance` is linear
  chord deviation in model units (mm), angular in radians. Mechy uses 0.05 mm / 0.2 rad for per-part STLs
  and 0.2-0.3 for preview assemblies (coarse is fine for viewing, not for printing).
- `pack()` lays parts out for a print plate; `align_z` puts them on Z = 0.
- Shallow copies of repeated parts (fasteners) are fast but share geometry.

### 3.3 CadQuery
- Fluent chain on a `Workplane`: `cq.Workplane("XY").box(20,20,5).faces(">Z").workplane().hole(3)`.
- String selectors: `">Z"` (max Z), `"<X"`, `"|Z"` (parallel to Z), `"#Z"` (perpendicular), `"%CIRCLE"`,
  combinable (`">Z and %PLANE"`). Use `.tag("name")` and `.workplaneFromTagged("name")` to return to a
  known reference instead of chaining off selected faces.
- Pitfall: `.workplane()` on a selected face uses that face's centre/normal; `centerOption` matters
  (`"CenterOfBoundBox"` vs `"ProjectedOrigin"`). Use `ProjectedOrigin` for parametric stability.
- Pitfall: the chain's "stack" changes after each call; long chains become hard to debug. Break into
  named intermediate variables.
- `cq.Assembly` with constraints (`Plane`, `Axis`, `Point`) solves positions; export to STEP keeps colours
  and names.

### 3.4 OpenSCAD
- CSG on meshes (CGAL; the Manifold backend in recent dev snapshots is much faster). **Output is mesh only**
  (STL, 3MF, OFF): no STEP, no exact B-rep, so no clean FEA or CAD hand-off.
- `$fn` controls facet count; set it per object (`$fn=64` for bearing seats) or globally via `$fa`/`$fs`.
  A circle at `$fn=n` is a polygon **inscribed** in the true circle, so holes print small. Compensate:
  `r_poly = r / cos(180/n)`.
- Coplanar differences produce zero-thickness skins: extend cutters (`translate([0,0,-0.01]) ... h+0.02`).
- `minkowski()` is very slow; `hull()` is fast. `offset()` in 2D is the cheap way to round.
- Variables are immutable (assigned at compile time); last assignment wins in scope, which surprises
  programmers. Use functions and modules, pass parameters explicitly.
- Good for: quick printable brackets, Customizer-friendly community parts (many Thingiverse/Printables
  sources). Mechy: when adapting an OpenSCAD vendor part, export STL/3MF from the original and keep it in
  `research/<topic>/vendor/`; re-model in build123d only if it needs to be parametric in our assembly.

### 3.5 Choosing
| Need | Use |
|---|---|
| Parametric mechanical parts, STEP out, assemblies, sim inertials | build123d (Mechy default) |
| Existing CadQuery codebase / CQ-editor workflow | CadQuery (interoperable with build123d) |
| Simple community-style printable part, mesh output OK | OpenSCAD |
| Hand-editing by a user, drawings, GD&T | FreeCAD / Onshape, import STEP |

---

## 4. File formats

| Format | What it holds | Units | Use for | Do not use for |
|---|---|---|---|---|
| **STEP** (ISO 10303; AP203/214/242) | Exact B-rep solids, assemblies, names, colours (AP214+), PMI/GD&T (AP242) | Stored in file | CAD exchange, machining, FEA meshing, archive "source of truth" export | Slicing (most slicers need mesh), web viewing |
| **STL** | Triangle soup, no topology, no units, no colour | None (convention mm) | Printing, one file per part | CAD exchange, anything needing units or assembly |
| **3MF** (3MF Consortium) | Mesh + units + objects + colours/materials + build plate + slicer settings (vendor extensions) | Stored (default mm) | Printing with plate layout, multi-material, giving a ready-to-print project | CAD exchange |
| **OBJ** | Mesh + UV/material (MTL) | None | Rendering, legacy | Printing (no units), CAD |
| **glTF 2.0 / GLB** (Khronos) | Scene graph of nodes with transforms, meshes, PBR materials, animation | **Metres, Y-up, right-handed** (spec) | Web viewing, animation of a mechanism (Mechy app viewer) | Printing, CAD |
| **URDF** (ROS) | Tree of links + joints, inertials, visual/collision meshes | m, kg, rad | ROS tooling, MoveIt, PyBullet, Drake import | Closed loops (belts, 4-bars), actuators/tendons |
| **MJCF** (MuJoCo XML) | Bodies, joints, geoms, actuators, tendons, equality constraints, contact params | m, kg, s, rad (angles in degrees unless `<compiler angle="radian"/>`) | MuJoCo sims | Exchange with non-MuJoCo tools |
| **SDF** (Gazebo) | Like URDF + worlds, closed loops | SI | Gazebo, Drake | MuJoCo (convert) |

Rules:
- **STEP is the master export**; everything else is a derivative that can be regenerated. Keep the rebuild
  command next to it.
- **One STL per printed part**, in print orientation if you know it (or document orientation in
  `print_list.csv`). Name files by part ref (`stl/upper_link.stl`).
- **glTF is Y-up**; CAD and MuJoCo are Z-up. The exporter must rotate (-90 deg about X) or the viewer
  must. Check visually once per pipeline change. glTF is metres: scale 0.001 from mm.
- For **animatable GLB**, each moving link must be its own node whose origin sits on its joint axis, with
  the hierarchy mirroring the kinematic tree, so a viewer can set a node rotation = joint angle. Mechy
  has a contract for this (commit "Contract: animatable GLB nodes and sim replay format";
  `docs/architecture/contracts.md`).
- **MJCF angles default to degrees** in `<compiler>`. Many sim bugs are a missing `angle="radian"`.
- **URDF -> MJCF**: MuJoCo can load URDF directly (add a `<mujoco><compiler .../></mujoco>` extension
  block for mesh dirs). Collision meshes from URDF become convex hulls in MuJoCo (MuJoCo collides meshes
  as convex hulls); decompose non-convex parts (e.g. CoACD, V-HACD) or use primitives.
- STL binary vs ASCII: always binary (~5x smaller, same data).
- Tessellation tolerance for printing: chord deviation ~0.01-0.05 mm and angular ~0.1-0.2 rad is
  visually and dimensionally fine for FDM (estimate; FDM resolution ~0.1 mm). Coarser (0.2 mm) visibly
  facets bearing seats and makes holes undersize.

---

## 5. Mesh quality

### 5.1 For 3D printing (slicer input)
A printable mesh must be:
1. **Closed / watertight**: every edge shared by exactly 2 triangles.
2. **Manifold**: no edges with >2 faces, no "bow-tie" vertices, no zero-thickness walls.
3. **Consistently oriented**: normals point outward; signed volume > 0.
4. **No self-intersections** and no internal duplicate shells (overlapping bodies exported as one STL
   without union).
5. **Correct scale**: bounding box in mm matches the design (a 1000x error is the classic mm/m slip).

Automated checks (Python, `trimesh`): `mesh.is_watertight`, `mesh.is_winding_consistent`,
`mesh.is_volume`, `mesh.volume > 0`, `mesh.euler_number` (2 for a closed genus-0 shell; 2 - 2g for g
through-holes), `mesh.bounds`. Also compare mesh volume to B-rep volume: should match within ~0.5%
(estimate; tessellation removes a little volume on convex curves).

Repair tools: PrusaSlicer/Orca built-in repair, Meshmixer, Blender 3D-Print Toolbox, `trimesh.repair`,
`pymeshfix`. Repair is a last resort; fix the CAD so the export is clean.

Printability geometry (FDM, 0.4 mm nozzle, typical community/vendor guidance; see the printing knowledge
file for detail and cross-checks):
- Min wall ~0.8-1.2 mm (2-3 perimeters); structural walls >= 2 mm.
- Overhangs up to ~45 deg without support; bridges up to ~10-20 mm (material and cooling dependent).
- Horizontal holes: teardrop or flat-top them to avoid support.
- Holes print undersize by ~0.1-0.3 mm; clearances between printed mating parts ~0.2-0.4 mm.
- First-layer "elephant foot": 0.3-0.5 mm x 45 deg chamfer on bottom edges.
- **Strength is anisotropic**: Z (inter-layer) tensile strength is often 25-55% of XY for FDM PLA
  (ORNL reports a 50-75% drop; other studies vary; estimate). Orient parts so primary bending stress runs
  along layers, never across them.

### 5.2 For simulation
- **Collision meshes**: MuJoCo uses the convex hull of each mesh geom. A U-shaped cup modelled as one mesh
  collides as a solid block. Use primitives (boxes, capsules, cylinders) or a convex decomposition. Mechy's
  cup is built from wall segments for this reason.
- Keep collision geometry coarse (tens to hundreds of faces); visual meshes can be fine.
- **Inertia from meshes**: MuJoCo's default mesh inertia (`legacy`) overcounts volume for non-convex meshes;
  `inertia="exact"` needs a watertight, well-oriented mesh; `convex` uses the hull (MuJoCo XML reference,
  asset/mesh). Better: compute mass properties in CAD (exact B-rep) and write explicit `<inertial>`
  (Mechy does this: "CAD inertials").
- **FEA meshes** are a different thing (volume elements, section 6). Never FEA-mesh an STL if a STEP
  exists; STL facets create artificial corners and bad element shapes.

---

## 6. FEA fundamentals

### 6.1 What linear static FEA assumes
Small displacements, small strains, linear elastic material, loads that do not change direction, no
contact changes. If any is false (snap fits, large deflection of flexures, contact between parts,
yielding), you need nonlinear analysis, and the linear result can be badly wrong.
Quick test: if max displacement > ~5-10% of the smallest relevant dimension (e.g. beam depth), suspect
geometric nonlinearity (rule of thumb, estimate).

### 6.2 Element types
| Element | Nodes | Use | Watch out |
|---|---|---|---|
| Linear tet (C3D4) | 4 | Filler only | Far too stiff in bending (shear/volumetric locking); needs extremely fine mesh. Avoid for results. |
| Quadratic tet (C3D10) | 10 | **Default for printed/CAD parts**, auto-meshable | Volumetric locking near incompressible (rubber, plasticity) |
| Linear hex (C3D8) | 8 | Rarely; full integration locks in bending | C3D8R reduced integration: hourglass modes, needs several through thickness |
| Quadratic hex (C3D20 / C3D20R) | 20 | Best accuracy per DOF where geometry can be hex-meshed | Needs structured mesh; hard for organic printed parts |
| Shell (S3, S4, S8R) | 3-8 | Thin walls (t < ~1/10 of span) | Must assign thickness; stress at mid-surface vs top/bottom |
| Beam (B31, B32) | 2-3 | Frames, extrusions, shafts | Section properties must be right; no local stress concentrations |

Sources: CalculiX manual element descriptions (C3D10 "behaves very well", C3D20R better per DOF); Abaqus
guidance favouring quadratic reduced-integration elements; NTNU course notes on avoiding C3D4.
Element names here are CalculiX/Abaqus; FreeCAD FEM uses the same CalculiX elements.

### 6.3 Meshing rules of thumb (typical)
- At least **2-3 quadratic elements through the thickness** of any bending member; 4+ with linear hexes.
- Refine where stress gradients are high (fillets, holes, contact patches); elements at a fillet ~1/4 to
  1/8 of the fillet radius for converged peak stress (estimate).
- Element quality: aspect ratio < ~5-10, Jacobian ratio positive (and ideally > 0.5-0.6 scaled Jacobian),
  no inverted elements. Exact thresholds vary by tool.
- Remove features irrelevant to the result (logos, tiny chamfers) before meshing; keep fillets where you
  want stress.

### 6.4 Boundary conditions: where most errors live
- **Fixed supports are infinitely stiff**. Fixing a whole face over-stiffens and creates artificial stress
  at the edge of the fixture. Real bolted joints flex. Read stress away from the fixture (St Venant:
  ~1-2 characteristic dimensions away).
- **Point loads and point constraints produce singularities** (infinite stress in theory). Spread loads
  over a realistic patch; read displacement there, not stress.
- **Rigid body motion**: a static model must have all 6 rigid-body DOF constrained, else the solver
  reports a singular matrix or gives huge displacements. Minimum statically determinate set: 3-2-1 rule.
- **Symmetry**: symmetry plane = zero normal displacement on that plane. Only valid if geometry, loads and
  material are all symmetric. Halve the load if you halve the model only when the load sits on the plane.
- Bolt preload, bearing loads (use a cosine-distributed load or a remote load on a rigid/coupling region),
  and gravity are frequently forgotten or double-counted.
- Units: CalculiX is unitless. A consistent set for mm models: **mm, N, MPa (N/mm^2), tonne (1e3 kg),
  s**; density of PLA = 1.24e-9 t/mm^3. Mixing kg with mm is a classic 1000x error in dynamic results.

### 6.5 Convergence
- Run **at least three meshes** with a constant refinement ratio `r` (e.g. element size h, h/1.5, h/2.25).
- Monitor a quantity that should converge: displacement at a point, reaction force, stress at a smooth
  location, first natural frequency. **Displacement converges first; peak stress last.**
- If peak stress keeps rising with refinement (no plateau), it is a **singularity** (sharp re-entrant
  corner, point load, fixture edge). Add a real fillet or read stress elsewhere (Autodesk, ESRD notes).
- Richardson extrapolation and Grid Convergence Index (Roache), with f1 finest, f3 coarsest:
  - observed order `p = ln((f3 - f2)/(f2 - f1)) / ln(r)`
  - extrapolated `f_ext = f1 + (f1 - f2)/(r^p - 1)`
  - `GCI_fine = 1.25 * |(f1 - f2)/f1| / (r^p - 1)`
  - Accept when GCI < ~2-5% for decisions (Mechy convention, estimate). If p comes out negative or wildly
    off the element's theoretical order (2 for displacement with quadratic elements, roughly), the
    sequence is not in the asymptotic range: refine more.

### 6.6 Verifying FEA against hand calcs
Always build the hand-calc twin:
1. Simplify the part to a beam/plate/tube with the same section at the critical location.
2. Compute deflection and nominal stress (section 10), and peak stress = Kt x nominal using a published
   Kt chart (Peterson's; or Kt = 3 for a small hole in a wide plate in tension).
3. FEA displacement should match beam theory within ~5-10% for a slender member (L/h > ~10). Short deep
   beams add shear deflection: `delta_shear = F L / (k G A)`, k ~ 5/6 for a rectangle.
4. Reaction forces must sum to applied loads (equilibrium check, should be ~exact, 0.1%).
5. If FEA is much **stiffer** than hand calc: linear tets, over-constrained BC. Much **softer**: missing
   constraint, unit error, wrong E (MPa vs GPa), or a part not bonded to its neighbour.

### 6.7 Material inputs for printed parts (typical, verify with your datasheet)
| Material | E (GPa, XY) | Tensile strength (MPa, XY) | Poisson |
|---|---|---|---|
| PLA | ~2.3-3.5 | ~45-60 | ~0.35 |
| PETG | ~1.8-2.2 | ~45-50 | ~0.38 |
| ABS/ASA | ~1.8-2.3 | ~35-45 | ~0.35 |
| PA (nylon), CF-nylon | ~1-2 (dry), CF much higher | ~40-70 | ~0.4 |
Typical ranges from filament datasheets (Prusament, Polymaker, Bambu TDS). Printed parts are porous and
anisotropic: treat FEA as **isotropic with reduced properties** (e.g. E ~70-90% of filament value, Z
strength ~25-50% of XY; estimate) and apply a safety factor >= 2-3 on strength. Creep matters for PLA
under sustained load and above ~50 C.

### 6.8 Common FEA mistakes (checklist)
- Wrong units (MPa vs Pa, mm vs m, kg vs tonne).
- Linear tets used for results.
- One element through thickness.
- Reading stress at a singularity or fixture edge.
- Contact assumed bonded when it can separate (or vice versa).
- Gravity sign/direction wrong; load applied to the wrong face.
- Yield exceeded but linear results quoted (stress > yield means the linear answer is invalid there).
- Buckling ignored for slender compression members (do a linear buckling analysis or Euler hand calc).
- Assembly parts not connected (floating bodies -> singular matrix) or overlapping (double stiffness).
- Modal analysis without mass of attached purchased parts (motors!).

---

## 7. Open FEA tools

| Tool | What it is | Strengths | Limits | Use when |
|---|---|---|---|---|
| **CalculiX (ccx)** | Abaqus-like solver (input deck `.inp`), GPL | Linear/nonlinear statics, contact, modal, buckling, heat; robust; scripted via text decks | Pre/post needs another tool (cgx, FreeCAD, PrePoMax on Windows, meshio + gmsh) | Real part analysis from STEP via gmsh |
| **FreeCAD FEM** | GUI workbench driving gmsh/netgen + CalculiX (or Elmer, Z88) | Mesh STEP directly, GUI BCs, scriptable in Python | GUI-centric; scripting API changes between versions | Interactive studies, user-facing checks |
| **gmsh** | Mesher (Python API) | STEP in (OCC kernel), tets/hexes, size fields, physical groups | Mesher only | Mesh for ccx/scikit-fem/sfepy |
| **scikit-fem** | Pure-Python FE assembly library | Tiny install, forms in Python, tri/quad/tet/hex, elasticity examples | No real mesher (load via meshio), you write the physics | Small custom problems, verification, teaching |
| **SfePy** | Python FE framework | Many physics terms, problem description files | Steeper learning curve | Coupled/multiphysics in Python |
| **FEniCSx (dolfinx)** | High-level variational FE, C++ core | Powerful, parallel | Heavy install | Research-grade custom PDEs |
| **Elmer** | Multiphysics FE | Thermal, EM, fluids | Less mechanical-focused | Multiphysics |

Practical Mechy path for a printed part (not yet in the engine, proposal): build123d -> STEP -> gmsh
(second-order tets, `Mesh.ElementOrder = 2`, size field near holes) -> CalculiX deck (mm, N, MPa) ->
parse `.frd`/`.dat` for displacement and reaction forces -> compare to beam hand calc in a verification
table. For simple beam-like links, **hand calcs alone are often adequate** and should be done first.

Minimal CalculiX deck skeleton (structure only):
```
*INCLUDE, INPUT=mesh.inp          ** nodes, C3D10 elements, NSETs from gmsh
*MATERIAL, NAME=PLA
*ELASTIC
2500., 0.35                       ** MPa, Poisson (estimate for printed PLA)
*DENSITY
1.24e-9                           ** t/mm^3
*SOLID SECTION, ELSET=EALL, MATERIAL=PLA
*STEP
*STATIC
*BOUNDARY
NFIX, 1, 3, 0.
*CLOAD                            ** or *DLOAD for pressure on a face (preferred over point loads)
NLOAD, 3, -10.
*NODE PRINT, NSET=NFIX
RF
*NODE FILE
U
*EL FILE
S
*END STEP
```

---

## 8. Multibody / physics simulation

### 8.1 Engines at a glance
| Engine | Contact model | Strengths | Weaknesses | Typical step |
|---|---|---|---|---|
| **MuJoCo** (Mechy) | Soft convex-optimisation contact (solref/solimp), smooth and invertible | Fast, accurate articulated dynamics, tendons, equality constraints, good docs | Soft contact allows small penetration; mesh collisions are convex hulls | default 2 ms; 0.5-1 ms for stiff contact/impacts |
| **PyBullet** | LCP-style (sequential impulse), ERP/CFM | Easy URDF loading, popular for RL | Maintenance mode; less accurate contact and joint friction; tuning by trial | 1/240 s common (tutorial practice; verify with `getPhysicsEngineParameters()`) |
| **Drake** | Point or hydroelastic contact; discrete SAP / TAMSI solvers | Rigorous, hydroelastic patches, optimisation/control toolbox | Heavier, steeper learning curve | default 1 ms discrete (`MultibodyPlantConfig`) |
| Isaac/PhysX, Genesis, MJX/MJWarp | GPU | Massive parallel RL | Less accurate per-sim | - |

### 8.2 MuJoCo essentials (defaults from the XML reference, stable docs)
- `<option>`: `timestep` 0.002 s, `integrator` Euler (options Euler, RK4, implicit, implicitfast, discrete),
  `cone` pyramidal, `impratio` 1, `solver` Newton, `iterations` 100, `tolerance` 1e-8,
  `noslip_iterations` 0.
- **Integrator choice**: `implicitfast` (implicit in velocity, drops Coriolis/centrifugal terms in the
  derivative) is the recommended general choice for robots with joint damping/actuator gains; it is much
  more stable than Euler with stiff damping. RK4 is accurate for smooth, contact-free dynamics. Mechy uses
  `implicitfast` at 0.5 ms.
- Contact softness: `solref = "timeconst dampratio"` (default `0.02 1`); `solimp` default
  `0.9 0.95 0.001 0.5 2`. **`timeconst` must be >= 2 x timestep** (MuJoCo enforces this unless `refsafe`
  is disabled). So a 10 ms time constant needs dt <= 5 ms; for a stiffer 2 ms contact use dt <= 1 ms.
  Negative solref values (`-stiffness -damping`) specify stiffness/damping directly.
- Restitution (bounce) is not a direct parameter; it emerges from `dampratio`. Calibrate it with a drop
  test (Mechy does this in `cad/mjcf.py`): drop from h1, measure rebound h2, `e = sqrt(h2/h1)`.
  Note the two geoms' solref values are mixed, so calibrate the *pair*.
- `condim`: 1 = frictionless normal only, 3 = normal + 2D sliding friction (default), 4 = + torsional,
  6 = + rolling. Use 4 for balls/objects that must not spin in a gripper/cup; 6 for rolling resistance.
- `friction="slide torsion roll"` (commonly `1 0.005 0.0001` default; verify in reference). Combined
  per contact by max unless priorities set.
- Friction cones: pyramidal default; **elliptic is closer to physical Coulomb friction**. To suppress slip:
  elliptic cone, larger `impratio`, Newton with small tolerance (MuJoCo modelling guide).
- `margin` activates contact before touching (default 0); `gap` subtracts from it. Useful for fast,
  thin objects to avoid tunnelling.
- Joint `armature` = reflected rotor inertia: `J_reflected = J_rotor * N^2` for gear/belt ratio N. A
  NEMA17 rotor is ~50-80 g cm^2 = 5e-6 to 8e-6 kg m^2 (typical datasheet). With N = 5, armature ~1.5e-4
  to 2e-4 kg m^2, often comparable to a light link's inertia; never omit it.
- Joint `damping`, `frictionloss` model bearings/belt drag; get values from a measured coast-down or
  leave small and list as not verified.
- Actuators: `motor` (torque, `gear` = ratio), `position` (PD servo: `kp`, `kv`), `velocity`. A stepper is
  neither; Mechy models it with a pull-out torque curve and a skipped-step detector (README).
- Mesh geoms collide as **convex hulls**.
- Body frames: `pos`/`quat` relative to parent; joint `axis` in body frame. Mechy convention: pitch
  hinges use axis `0 -1 0` so MJCF q equals mechy_core q.

### 8.3 Timestep and stability rules of thumb
- Resolve the fastest dynamics: dt <= ~1/10 of the shortest period of interest (contact, servo loop,
  structural mode in the model). E.g. a PD joint with natural frequency 50 Hz (20 ms period) -> dt <= 2 ms.
- For explicit integration of a spring-mass, stability needs `dt < 2/omega_n` (theoretical bound; use
  far less for accuracy).
- **Tunnelling**: an object moving at v crosses a thin geom of thickness t in one step if `v dt > t`.
  Ball at 10 m/s, dt = 0.5 ms -> 5 mm per step: a 2 mm wall can be tunnelled. Thicken collision geoms or
  reduce dt.
- **Halving test**: rerun with dt/2. Key outputs (catch success, peak torque, final pose) should change
  < ~1-2%. If they change more, you are not converged in time.
- Instability symptoms: NaN/Inf in `qpos`, `qacc` warnings (`mjWARN_BADQACC`), energy growth in a passive
  system, objects jittering at rest, explosions on first contact (interpenetrating initial state).
- Mass ratios > ~100-1000 between connected bodies and very light bodies with stiff contacts are
  ill-conditioned; add armature or merge tiny bodies.

### 8.4 PyBullet notes
- Load URDF with `useFixedBase=True` for arms; default joint motors are active with velocity control,
  call `setJointMotorControl2(..., VELOCITY_CONTROL, force=0)` to make joints free before torque control.
- `setPhysicsEngineParameter(numSolverIterations=..., erp=..., contactERP=...)`; ERP 0.1-0.8 is the
  usual Bullet range (Bullet/UPBGE docs).
- `setTimeStep(1/240)` is common; real-time mode is off by default; `stepSimulation()` advances one step.

### 8.5 Drake notes
- `MultibodyPlant(time_step=0.001)` is the default discrete mode; SAP is stable at larger steps but steps
  must still resolve dynamics (Drake v1.5 release notes).
- Hydroelastic contact gives pressure patches (better for flat-on-flat, grasping); needs compliant
  geometry properties set.
- Use Drake when you need trajectory optimisation, rigorous system modelling, or contact patches.

### 8.6 Sim-to-real gaps for printed, belt-driven arms (list under "Not verified")
Belt stretch (compliance), backlash, stepper missed steps, bearing friction, link flex, cable drag,
inaccurate CoM from infill, contact restitution of real materials, sensor latency.

---

## 9. Tolerance analysis

### 9.1 Methods
| Method | Formula | Use when |
|---|---|---|
| Worst case | `T_total = sum |s_i| T_i` | Safety-critical fits, few parts, must always assemble |
| RSS (root sum square) | `T_total = sqrt(sum (s_i T_i)^2)` | Many independent parts, normally distributed, centred processes |
| Modified RSS | `T_total = Cf * sqrt(sum (s_i T_i)^2)`, Cf ~1.4-1.8 | Processes not perfectly centred |
| Monte Carlo | Sample each dimension from its distribution, evaluate the function | Non-linear stacks (angles, kinematics), non-normal distributions |
`s_i` = sensitivity (dY/dx_i; +/-1 for a linear 1D stack). RSS assumes each `T_i` is a +/-3 sigma band.
Sources: Fortini; Drake (Paul) "Dimensioning and Tolerancing Handbook"; general GD&T references.

Worked mini-example (1D stack): bearing seat depth 7.0 +/- 0.15 (print), bearing width 7.0 +/- 0.05
(datasheet tolerance, estimate), spacer 2.0 +/- 0.15, housing length 16.4 +/- 0.15. Gap = 16.4 - 7.0 - 2.0
- 7.0 = 0.4 mm nominal.
- Worst case: +/- (0.15 + 0.05 + 0.15 + 0.15) = +/-0.50 -> gap -0.10 to 0.90: **may interfere**.
- RSS: sqrt(0.15^2*3 + 0.05^2) = 0.265 -> gap 0.135 to 0.665: assembles at 3 sigma.
- Decision: either accept RSS risk (many prints, independent) or increase nominal gap to 0.55.

### 9.2 Kinematic tolerance (arms)
Position error at the tool from joint angle error: `delta_x ~= L_eff * delta_theta`. Joint angle error
sources: stepper step angle / microstep accuracy (full step 1.8 deg; microstep positional accuracy is much
worse than its resolution under load), belt ratio, backlash, belt stretch `delta = F L / (E A)` of the
belt. Run a Monte Carlo over link length, joint offset and angle errors with the forward kinematics
(500-10 000 samples) and report the 95th percentile tool error.

### 9.3 Tools
- Commercial: Sigmetrix CETOL 6sigma, 3DCS, SolidWorks TolAnalyst.
- Open: no mature open-source 3D stack-up tool known; use a Python Monte Carlo (numpy) over the
  kinematic or 1D stack function, plus a spreadsheet for 1D worst-case/RSS.
- FDM capability: typical dimensional accuracy +/-0.1-0.2 mm on well-tuned printers (estimate); measure a
  calibration print and use measured sigma.

---

## 10. Closed-form results library (for verification twins)

All SI. E Young's modulus [Pa], I second moment of area [m^4], G shear modulus, rho density, A area.

Section properties
- Rectangle b x h (bending about axis parallel to b): `I = b h^3 / 12`, `c = h/2`, `Z = b h^2 / 6`.
- Solid circle diameter d: `I = pi d^4 / 64`, `J = pi d^4 / 32`.
- Tube D outer, d inner: `I = pi (D^4 - d^4) / 64`.

Beams (Euler-Bernoulli, small deflection)
| Case | Max deflection | Max moment |
|---|---|---|
| Cantilever, end load F | `F L^3 / (3 E I)` | `F L` at root |
| Cantilever, uniform load w [N/m] | `w L^4 / (8 E I)` | `w L^2 / 2` |
| Simply supported, centre load F | `F L^3 / (48 E I)` | `F L / 4` |
| Simply supported, uniform w | `5 w L^4 / (384 E I)` | `w L^2 / 8` |
| Fixed-fixed, centre load | `F L^3 / (192 E I)` | `F L / 8` |
Bending stress `sigma = M c / I`. Cantilever end slope `F L^2 / (2 E I)`.

Worked: PLA cantilever, L = 0.1 m, b = 0.01, h = 0.005, E = 3.0e9 Pa (estimate), F = 5 N.
I = 0.01*0.005^3/12 = 1.042e-10 m^4. delta = 5*0.1^3/(3*3e9*1.042e-10) = 5.33e-3 m = 5.3 mm.
sigma = (5*0.1)*0.0025/1.042e-10 = 12.0 MPa. Deflection/depth = 5.3/5 ~ 1: linear theory is
borderline (section 6.1); this is a check case for an FEA pipeline, not a good link design.

Torsion, axial, buckling
- Shaft torsion: `tau = T r / J`, twist `phi = T L / (G J)`.
- Axial: `delta = F L / (E A)`.
- Euler buckling: `P_cr = pi^2 E I / (K L)^2`; K = 1 pinned-pinned, 2 cantilever, 0.5 fixed-fixed,
  0.7 fixed-pinned.

Stress concentration (nominal x Kt)
- Small circular hole in wide plate, uniaxial tension: Kt = 3 (Kirsch solution).
- For fillets/shoulders/grooves use Peterson's charts (cite figure; do not copy tables).

Vibration
- Spring-mass: `f = (1/2pi) sqrt(k/m)`.
- Cantilever first mode: `f1 = (1.875^2 / 2pi) sqrt(E I / (rho A L^4))`; with tip mass M >> beam mass:
  `f ~= (1/2pi) sqrt(3 E I / (L^3 (M + 0.24 m_beam)))`.
- Simple pendulum: `T = 2 pi sqrt(L/g)` (small angle). Physical pendulum: `T = 2 pi sqrt(I_pivot / (m g d))`.

Dynamics / sim twins
- Free fall: `z(t) = z0 + v0 t - g t^2/2`; projectile range on flat ground `R = v^2 sin(2 theta) / g`.
- Bounce: `e = v_out / v_in = sqrt(h2/h1)`.
- Rotating link, static gravity torque: `tau = m g r_cm cos(theta)` (theta from horizontal);
  serial arm joint torque = sum over distal links of `m_i g` x horizontal lever arm to the joint.
- Rigid body about fixed axis: `tau = I alpha`; constant-accel move of angle theta in time t:
  `alpha = 4 theta / t^2` (bang-bang, half accel half decel), peak velocity `2 theta / t`.
- Energy: passive frictionless system conserves `KE + PE`; with damping, energy must monotonically decrease.
- Belt drive: ratio `N = z_driven / z_driver`; GT2 pitch 2 mm; closed-loop belt length for two pulleys
  `L ~= 2C + pi (D1 + D2)/2 + (D2 - D1)^2 / (4C)` (C centre distance, D pitch diameters, `D = z p / pi`).
- Stepper torque at joint: `tau_joint = tau_motor(speed) * N * efficiency`; Mechy uses a 50% safety factor.

Kinematics
- 2-link planar arm forward kinematics `x = L1 cos q1 + L2 cos(q1+q2)`, `y = L1 sin q1 + L2 sin(q1+q2)`;
  verify IK by FK(IK(p)) = p over random reachable points (error < 1e-9 m in double precision).
- Jacobian check: finite-difference `J` vs analytic, relative error < 1e-6.

---

## 11. Writing verification tables

Mechy standard 5 format: `| Check | Expected | Got | PASS/FAIL |`. Make every row reproducible:

Rules
1. **Expected must come from an independent source**: closed form, published benchmark, datasheet, or a
   different tool. Never "expected = previous run of the same code".
2. State the **tolerance** used for PASS (in the Check text or an extra column). Typical (Mechy
   convention, estimate):
   | Kind of check | Tolerance |
   |---|---|
   | Pure math identity (FK/IK round trip, unit conversion) | 1e-9 relative or 1e-6 m |
   | Numerical integration vs analytic (free fall, pendulum, dt small) | <= 0.5-1% |
   | FEA displacement vs beam theory (slender) | <= 5-10% |
   | FEA peak stress vs Kt hand calc | <= 10-15% |
   | Equilibrium (sum reactions vs loads) | <= 0.1-1% |
   | Mass/inertia CAD vs hand (simple shapes) | <= 1% |
   | Sim vs physical test | stated per test; often 10-20% |
   | Convergence (dt halving, mesh GCI) | <= 1-2% change / GCI < 5% |
3. Include **units** in Expected/Got.
4. Include **how many samples** for sweeps (e.g. "500 random poses, max error").
5. FAIL rows stay in the table with a note of what was done. Never delete a failure.
6. Link the script/command that regenerates the table.

Example
```
| Check | Expected | Got | PASS/FAIL |
|---|---|---|---|
| Cantilever tip deflection, F=5 N, PLA 3 GPa (FL^3/3EI) | 5.33 mm | 5.47 mm (C3D10, 3 el thick) | PASS (2.6% < 5%) |
| Sum of reactions = applied load | 5.000 N | 4.998 N | PASS |
| Mesh GCI on tip deflection (r=1.5, 3 meshes) | < 5% | 1.1% | PASS |
| MuJoCo free fall 1.0 s from 2 m, no contact | z=-2.905 m | z=-2.905 m | PASS (|err| 2e-6 m) |
| Static gravity torque J2, 500 random poses vs m g r cos(q) sum | max err < 1% | 0.03% | PASS |
| dt halving: catch success rate | change < 2 pts | 91.0% -> 90.5% | PASS |
| Drop-test restitution of cup liner | e = 0.35 (target) | e = 0.33 | PASS (|err| < 0.05) |
| Ball tunnelling through cup wall at 12 m/s | 0 events | 3 / 200 | FAIL -> wall geom thickened to 4 mm, rerun |
```

---

## 12. Sanity checks for simulation output

Run these automatically after every sim; report failures loudly.

Physical plausibility
- [ ] No NaN/Inf in states; no MuJoCo warnings (`data.warning` counters all zero).
- [ ] Total mass printed equals CAD mass + purchased parts (within 1%). Check `model.body_subtreemass[0]`.
- [ ] Gravity is `0 0 -9.81` in a Z-up world; an unactuated arm falls *down*.
- [ ] At rest with the motors holding, joint torques equal the static gravity torques (hand calc).
- [ ] Passive pendulum test: period matches `2 pi sqrt(I/(m g d))`; energy constant (no damping) or
      decreasing (with damping). Growing energy = integrator/timestep problem.
- [ ] Contact penetration small: max penetration < ~1-5% of the smaller object's size (MuJoCo soft
      contact; estimate). Large values mean solref too soft or dt too large.
- [ ] Contact forces plausible: resting object's normal force sums to m g.
- [ ] Peak joint velocities/accelerations/torques within motor and driver limits (step rate limit in
      `hw/drivers.yaml`).
- [ ] No self-collision unless intended; check `data.contact` pairs list at the home pose is empty.

Numerical
- [ ] dt halving changes key metrics < 1-2%.
- [ ] Results insensitive to solver iterations (double them; metric change < 1%).
- [ ] Random seeds: report mean and spread over seeds; success rates with a confidence interval
      (binomial: `stderr = sqrt(p(1-p)/n)`; 200 throws at p = 0.9 -> +/-2.1 pts, 1 sigma).
- [ ] Monotonic trends make physical sense (heavier payload -> slower; more microsteps -> smoother but
      lower torque margin at speed).

Units and frames
- [ ] Bounding box of the model in metres is the size you expect (a 0.4 m arm, not 400 m).
- [ ] Joint zero pose in sim matches CAD home pose (render both, overlay).
- [ ] Joint axis signs: command +q, the link moves in the direction your kinematics assumes.
- [ ] Angles: radians everywhere internal; MJCF `<compiler angle="radian">` set if any angles are in rad.

Reporting
- Plot time series of q, qdot, torque vs limits; at least one render of the sim at a key frame
  (Mechy standard 10).
- List every parameter that is an estimate (friction, restitution, damping, belt stiffness).

---

## 13. BOM and print-list conventions

### 13.1 print_list.csv (Mechy standard 8; generator: `cad/belt_arm.py`)
Columns used by Mechy: `part, qty, material, orientation, est_grams, est_grams_total, infill, volume_cm3,
stl`. Conventions:
- `part` = stable reference id (snake_case), same as STL basename and CAD label.
- `orientation` = which face is on the bed and why (e.g. "flat face down, layers along link length").
- `est_grams` = volume x effective density; label as estimate; include supports separately if large.
- Add `notes` for supports, inserts (heat-set M3 x 5.7), pause-at-layer for captive nuts, colour.
- Totals row (or summary in the note): total filament grams and estimated print hours (slicer output;
  label "slicer estimate" with profile name).

### 13.2 bom.csv
Recommended columns: `item, description, spec/standard, qty, unit, source (URL or vendor + part no),
unit_cost, notes`. Conventions:
- One row per distinct purchased part, **including every screw, nut, washer, insert, belt, cable tie**.
- Fastener naming: `M3x10 socket head cap screw, ISO 4762 (DIN 912), A2 or 12.9`. Length is measured
  under the head for cap screws and overall for countersunk (ISO 10642).
- Bearings by designation (`608-2RS`: 8x22x7 mm; `F623ZZ`: flanged 3x10x4 mm; check datasheet).
- Belts: profile, width, length, tooth count, open vs closed loop (`GT2 6 mm closed loop 200 mm, 100T`).
- Motors: frame, step angle, rated current, holding torque, shaft (`NEMA17 1.8 deg, 1.5 A, 0.45 N m, 5 mm
  D-shaft`), with datasheet link.
- Electronics: driver model, supply V/A, connectors, wire gauge.
- Add a spares column or +10% on small fasteners (common practice).
- Quantities must be generated from the CAD assembly where possible, not typed; check BOM qty == count of
  instances in the assembly (a cheap automated check).
- Mark placeholder sources/costs as "placeholder" in the cell itself (Mechy standard 6).

### 13.3 Assembly order
Numbered steps, each naming the parts and fasteners used, torque/insert notes, and a "check" (e.g. "joint
rotates freely by hand, no axial play"). Generate a render per major step where possible.

---

## 14. Checklists

### Before CAD export
- [ ] All key dims driven by parameters; flex test (+/-20%) passes.
- [ ] `is_valid()` on every part; no zero-thickness features.
- [ ] Part frames at joint axes; assembly in home pose; interference check over joint sweep.
- [ ] Mass properties computed from B-rep with effective density; purchased masses added.

### After export
- [ ] STEP opens and has expected solid count and bbox (mm).
- [ ] Each STL watertight, positive volume, mesh vs B-rep volume within ~0.5%, bbox matches.
- [ ] GLB: metres, Y-up handled, moving links are separate nodes pivoting at joints.
- [ ] MJCF: compiles, total mass matches, joint axes/signs verified, collision geoms primitive or convex.

### Before trusting FEA
- [ ] Hand-calc twin agrees (section 6.6).
- [ ] Quadratic elements, >= 2-3 through thickness, mesh convergence done.
- [ ] Reactions balance loads; no stress read at singularities/fixtures.
- [ ] Max stress < allowable / safety factor, with anisotropy for printed parts; deflection small enough
      for linear theory.

### Before trusting a dynamics sim
- [ ] Free-fall and pendulum twins pass in the same model setup.
- [ ] dt halving and iteration doubling converge.
- [ ] Static gravity torques match hand calc over random poses.
- [ ] Contact penetration and restitution calibrated and plausible.
- [ ] Estimates listed under "Not verified".

---

## 15. Canonical references

Free
- MuJoCo documentation (modelling guide, XML reference, computation): https://mujoco.readthedocs.io/ (free)
- build123d docs incl. "Tips, Best Practices and FAQ": https://build123d.readthedocs.io/ (free)
- CadQuery docs (selectors, assemblies): https://cadquery.readthedocs.io/ (free)
- OpenSCAD User Manual: https://en.wikibooks.org/wiki/OpenSCAD_User_Manual (free)
- CalculiX manual (element descriptions, input deck): http://www.dhondt.de/ and mirrored at
  https://web.mit.edu/calculix_v2.7/CalculiX/ccx_2.7/doc/ccx/ (free)
- FreeCAD FEM workbench wiki: https://wiki.freecad.org/FEM_Workbench (free)
- gmsh reference manual: https://gmsh.info/doc/texinfo/gmsh.html (free)
- scikit-fem: https://scikit-fem.readthedocs.io/ (free); SfePy: https://sfepy.org/ (free);
  FEniCSx: https://docs.fenicsproject.org/ (free)
- Drake: https://drake.mit.edu/ (MultibodyPlantConfig, discrete solvers docs) (free); MIT Underactuated
  Robotics / Robotic Manipulation course notes by R. Tedrake: https://underactuated.mit.edu/,
  https://manipulation.mit.edu/ (free)
- PyBullet Quickstart Guide: https://pybullet.org/ (free, Google Doc linked from site)
- glTF 2.0 specification (units metres, Y-up): https://registry.khronos.org/glTF/ (free)
- 3MF specification: https://3mf.io/specification/ (free)
- URDF spec (ROS wiki): http://wiki.ros.org/urdf/XML (free)
- trimesh docs (mesh checks): https://trimesh.org/ (free)
- MIT OCW 2.001 Mechanics & Materials I, 2.092 Finite Element Analysis of Solids and Fluids (Bathe):
  https://ocw.mit.edu/ (free)
- ESRD and Autodesk notes on singularities: https://www.esrd.com/why-worry-about-singularities/,
  https://www.autodesk.com/products/fusion-360/blog/quick-tip-singularities-and-simulation/ (free)
- NTNU TMM4175 element notes: https://nilspv.folk.ntnu.no/TMM4175_LEGACY/elements.html (free)
- Abaqus "Selecting continuum elements" (MIT mirror):
  https://abaqus-docs.mit.edu/2017/English/SIMACAEGSARefMap/simagsa-c-ctmselecting.htm (free)
- ORNL z-pinning papers (FFF anisotropy figures): https://impact.ornl.gov/ (free abstracts)
- DoITPoMS FDM page: https://www.doitpoms.ac.uk/tlplib/add_manuf/fdm.php (free)

Paid / books
- Budynas & Nisbett, *Shigley's Mechanical Engineering Design* (beam formulas, failure theories, fatigue).
- Young & Budynas, *Roark's Formulas for Stress and Strain* (closed-form library).
- Pilkey, *Peterson's Stress Concentration Factors* (Kt charts).
- Bathe, *Finite Element Procedures* (free PDF of 2nd ed. offered by the author via MIT/Bathe site).
- Cook, Malkus, Plesha, Witt, *Concepts and Applications of Finite Element Analysis*.
- Roache, *Verification and Validation in Computational Science and Engineering* (GCI).
- ASME V&V 10 (solid mechanics V&V guide), ASME Y14.5 (GD&T) (paid standards).
- Featherstone, *Rigid Body Dynamics Algorithms*; Lynch & Park, *Modern Robotics* (free PDF at
  http://modernrobotics.org).
- Drake, P. (ed.), *Dimensioning and Tolerancing Handbook*; Fortini, *Tolerancing* (stack-up methods).
- NAFEMS benchmarks and "How to" booklets: https://www.nafems.org/ (mostly paid/member).

---

## 16. Gaps / not verified

- MuJoCo `friction` default `1 0.005 0.0001` and `condim` default 3 are from memory; the docs fetch
  confirmed option defaults (timestep, integrator, cone, impratio, solver, iterations, tolerance) and
  solref/solimp defaults, but the geom section was not read in full.
- PyBullet default timestep (1/240 s) is common tutorial practice; not confirmed in the official guide.
  Check with `getPhysicsEngineParameters()`.
- Drake: default discrete `time_step` 0.001 s from `MultibodyPlantConfig` docs; hydroelastic setup details
  not checked against current docs.
- FEA tolerances (5-10% beam, GCI < 5%) and sim tolerances (1-2% dt halving) are Mechy conventions /
  engineering practice, not from a standard.
- FDM material properties and anisotropy ratios vary widely by printer, filament and settings; values
  here are ranges from datasheets and a few studies. Weigh and test prints for real numbers.
- Effective-density rule for infill and the mesh-vs-B-rep 0.5% volume check are estimates.
- Tessellation tolerance recommendations (0.01-0.05 mm) are estimates based on FDM resolution.
- OpenSCAD Manifold backend status depends on version (dev snapshots vs 2021.01 release); check the
  installed version.
- The CalculiX deck shown is a structural skeleton, not a tested input file.
- No open-source 3D tolerance stack-up tool was found; one may exist.
- NEMA17 rotor inertia and mass ranges are typical datasheet values across vendors, not a single
  datasheet; use the specific motor's sheet.
- Fillet mesh-size rule (1/4 to 1/8 of radius) and element quality thresholds are practitioner rules of
  thumb that vary by source and solver.
