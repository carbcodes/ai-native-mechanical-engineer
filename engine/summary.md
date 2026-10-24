# engine/ summary

**Built.** Python package `mechy` (CLI `mechy`) with: `init` (example tennis-catcher project, git,
event log); `cad build` (build123d arm -> STEP/STL/GLB, MJCF matching mechy_core's joint
conventions exactly, matplotlib thumbnail); `sim catch` (vision noise/latency -> ball_fit ->
intercept search -> IK -> plan_batch with gravity -> MuJoCo with a stepper pull-out model, 4
processes); `mcp` (11 FastMCP tools); `agent run`, `plan` (reads inbox/), `run` (parallel
scheduler), `doctor`. Uses `mechy_core` when installed, else a pure-Python port that matches it
to 1e-9. 20 pytest tests pass (19 + 1 skip with the fallback forced); 32 after round 2.

**v1 results** (200 throws, seed 0, ~16 s on 4 cores):
- 16 microsteps (4000 steps/s cap = 1.25 rev/s): catch rate **53.5%**, reach 92%, too slow 20,
  out of reach 16, bounced out 57, mean margin 0.18 s.
- 8 microsteps (2.5 rev/s): catch **53.5%**, too slow 1, bounced out 76.
- Test variant with a 90 mm deep cup (v1 is 60 mm, shallower than the 67 mm ball): **76.5%**.
  The cup depth is the main v1 problem; the step rate cap is the second.
- Steppers skip on ball impact in ~80% of throws (never during the move). Shoulder is the
  worst joint (mean peak 46% of pull-out torque before contact).

**Approximate / open issues.**
- One-shot plan after 0.2 s of tracking; no re-planning.
- Cup contact softness (restitution ~0.3, foam-lined) and the stepper model are tuned
  guesses, not measured. No belts, backlash or spin.
- Throw distribution (aim point and spread in requirements.yaml `throw:`) is assumed.
- No headless GL: no video.mp4, thumbnails via matplotlib.
- codex CLI flags are assumed (not installed); the claude adapter is not run against a real
  account. Both are tested only through the fake provider and the argv they build.

## Changelog

**Round 2 (2026-10-23): conventional belt arm.**
- New generator `style: belt_arm` (`mechy/cad/belt_arm.py`, default for the tennis-catcher v1;
  `style: simple` still builds). It follows the 20sffactory / Thor pattern: a printed base with the
  base NEMA 17 and a 51105 thrust bearing, GT2 20T driving a printed 90T turntable ring, a tower with
  the three other motors low, printed pulleys of `round(20 x gear_ratio)` teeth, closed belts sized to
  stock loops (the motor centre distance is solved for the stock length), 608-2RS / 688-2RS on 8 mm
  shafts, twin-plate upper arm, hollow box forearm, fork hand, and a windowed cup with a liner. The
  elbow and wrist use belt pass-through, so the motors set absolute link pitch.
- `cad build` writes stl/<part>.stl (16 printable parts, 23 pieces), print_list.csv (grams =
  volume x density x shell/infill factor), bom.csv (26 lines down to screws, about $114
  estimated), mass_props.json, and a colour-per-part GLB. The MJCF uses the solids' mass, COM and
  inertia, and `ArmModel` uses the same values. A test checks gravity torque and joint inertia
  against MuJoCo at 25 random poses.
- New catcher parameters: `liner` (eva_foam | net_pocket) and `restitution`. The MJCF calibrates
  the cup contact damping to that restitution with a MuJoCo drop test. Also `entry_offset_deg`
  (aim off-axis; it didn't help with a dead liner, so the default is 0).
- Fixed a sim bug: the hand capsule's tip poked 10 mm into the cup. That gave balls a dead,
  non-bouncy landing spot and inflated every earlier catch rate. With the fix, the old simple v1 with a
  90 mm cup scores 55% (16 microsteps), not 76.5%.
- Thumbnails are now a numpy z-buffer render with outlines, saved through matplotlib (the old
  painter's sort mis-ordered overlapping parts).
- v1 is now: ratios 4.5 / 7 / 5 / 2, links 0.22 / 0.22 / 0.08 m, shoulder height 0.18 m, cup
  110 x 90 mm with a net pocket, 4 microsteps. **91% catches** (200 throws, seed 0; 85.8% on 400
  throws, seed 1). Failures: out of reach 15, too slow 1, bounced out 2. The worst static torque
  margin is the shoulder at 1.13x the 50% budget, arm stretched horizontally.
- The catch rate depends on the liner restitution (estimated, not measured): 0.10 -> 91.5%,
  0.15 -> 91%, 0.20 -> 87.5%, 0.25 -> 82.5%, 0.30 -> 67.5%, EVA foam 0.40 -> 39%.
- Still open: the elbow/wrist motor coupling isn't modelled in the sim. Steppers skip on ball
  impact in 67% of throws, so they need re-homing or a closed loop after a catch. Belt stretch,
  printed tooth accuracy and infill masses are unverified. Drop-test the net pocket.

**Round 3 (2026-10-23): animatable GLB, replay, belt coupling, soft catch, homing.**

| What | Where |
|---|---|
| Animatable GLB writer | `mechy/cad/glb.py` (used by `cad build` for belt_arm and simple) |
| Coupled motor mapping | `ArmModel.motor_map()`, `to_motor` / `from_motor`, `motor_load_inertia`, `motor_gravity_torque` |
| Soft catch (give, spring) | `mechy/sim/catch.py` `plan_give`; `catcher.compliance: spring` in `mechy/cad/mjcf.py` |
| Replay | `sim/<task>/replay.json` (contracts 11) |
| Homing | belt_arm CAD, `bom.csv`, `mass_props.json` -> `homing`, design summary.md |

- `arm.glb` is now written directly (no OCC glTF writer). It has nodes `arm` (root; turns z-up into
  glTF y-up) > `base` > `turntable` > `upper_arm` > `forearm` > `hand` > `cup_center`. Each body's origin is
  on its joint axis, and every part is a named mesh node under its body with its colour kept. The file's rest
  rotations are the ready pose, so a static viewer looks the same as before; `scene.extras` lists the axes and
  rest q. Tests check node world positions against `fk` at 11 poses, and part meshes against the posed
  CAD solids (2 mm). A custom `model.py` still exports the old flat GLB.
- `mechy sim catch` writes `replay.json`: 3-5 throws (a clean catch, a catch that lost steps on impact,
  then one of each failure type present) at 100 Hz, with q, the ball, the predicted path, the catch point
  and the decision and catch times. The MJCF is now rebuilt from the params on every sim run, so sim-only
  settings don't need a CAD rebuild. Masses still come from `mass_props.json`.
- **Belt pass-through is modelled.** Motor-side coordinate a = C q, with a = (q0, q1, q1+q2, q1+q2+q3), and
  motor angle = ratio x a. Planning runs in a-space: speed caps per motor, inertia = diag(C^-T M C^-1),
  gravity = C^-T tau. The MuJoCo stepper model applies C^T (ratio x tau_motor). This was checked against
  MuJoCo's full mass matrix and bias forces at 25 random poses (1e-4), plus a closed-form moment balance
  at q = 0. The mapping and step counts are in `mass_props.json` -> `motor_map` and in the report meta.
  Effect: the shoulder motor's worst static load drops from 1.41 to 0.84 N m (margin 1.13x -> 1.87x). The
  impact load moves to the elbow motor.
- Homing, one sensor per joint, with the order base, shoulder, elbow, wrist:
  - base: A3144 hall on a printed post, 5x2 magnet in the turntable, sets q0 = 0;
  - shoulder: KW12-3 on the tower plate, tab on the upper arm, sets q1 = 120 deg;
  - elbow: A3144 in the motor spine, magnet in the elbow drive pulley, sets a2 = q1+q2 = 0. The
    pass-through lets the sensor stay on the turntable.
  - wrist: KW12-3 on the forearm, tab on the hand fork, sets q3 = -90 deg. This is the only lead that runs
    along the arm.

  The BOM adds 2 switches, 3 halls (1 spare), 4 magnets (2 spare), M2 screws and sensor cable.
- **Soft catch, measured (100-200 throws, seed 0):**

| Config | Catch | Skip on impact |
|---|---|---|
| Round 2 v1 (independent joints) | 91% | 67% |
| Coupled, no give (**v1 now**, 200 throws) | 92.5% | 75% (elbow 135 of 150) |
| + give 0.06 m, run-up 0.03 m (cup 0.43 m/s at impact) | 92% | 91% |
| + give from rest (run-up 5 mm) | 93% | 79% |
| Spring cup, k 200 N/m, 50 mm travel, zeta 1 | 93% | 45% |
| Spring + give | 93% | 60-67% |
| hand_m 0.13 + spring (200 throws) / without spring | 93% / 93% | 39% / 74% |
| EVA foam liner (e 0.40): no spring / spring | 54% / 93% | 88% / 65% |
| Liner e 0.30: no spring / spring | 80% / 93% | 83% / 60% |

  The open-loop give makes skipping worse. At impact the elbow motor runs near its 5 rev/s cap, where
  pull-out torque is lower, and these motors can't move the cup faster than about 0.5 m/s against a 4.3 m/s ball.
  An energy check shows why: a stepper slips after it absorbs about T_po/50 = 0.009 J, while the ball puts
  about 0.3 J into the elbow motor's side. So `catcher.give_m` defaults to 0 (not the requested 0.05-0.08). The
  option and its planner stay for faster motors. A sprung cup is the effective fix. It halves the
  skips and makes the catch rate insensitive to the liner restitution, which is still not measured. But
  50 mm of travel needs the hand about 50 mm longer (hand_m about 0.13), and the slide isn't drawn. That is
  an open decision, so v1 is unchanged. Clean catches cluster near the base, where the elbow lever arm is short.
- v1 now: **92.5%** (200 throws, seed 0; 87.3% on 400 throws, seed 1, was 85.8%). Failures are
  out of reach 15. Skip on impact 75%, so firmware must re-home after a catch (hall/switch homing above).
  Shoulder ratio 5 (instead of 7) now passes the torque budget at 1.34x and still catches 92%. It was not
  adopted, because speed isn't limiting (0 too-slow).

Not verified: the KW12-3 trip angles and hall trigger repeatability; magnet pocket fit in the printed
pulley; spring-cup hardware (not designed); the stepper slip energy model (sinusoidal approximation);
rotor-inertia cross terms of the coupling (ignored).

Open decisions: ~~sprung cup carriage vs. re-homing after most catches~~ (drawn in round 3b as v2, below);
shoulder 5:1 vs 7:1; closed-loop steppers (e.g. MKS SERVO42) as an alternative fix for skips.

**Round 3b (2026-10-23): the sprung cup is drawn (example variant v2).**

| What | Where |
|---|---|
| Slide CAD, spring pick, BOM rows | `mechy/cad/belt_arm.py` (`_slide_layout`, `_slide_plate`, `_cup_lugs`, `_add_slide_hardware`, `SPRINGS`) |
| `cup_slide` GLB node | `mechy/cad/glb.py` (`write_glb(slide=...)`, `body_transforms` / `node_world(slide_m=...)`) |
| Spring preload + friction brake in the MJCF | `mechy/cad/mjcf.py` (`springref` = drawn preload, `frictionloss` = `catcher.spring_friction_n`) |
| Example v2 | `examples/tennis_catcher/design/v2/params.yaml` (v1 unchanged), decision line in its decisions.md |
| Tests | `tests/test_belt_arm.py` (5 new) |

- With `catcher.compliance: spring` the belt_arm generator now draws the slide. The cup shell gets two lugs, and
  the hand's cross plate becomes a bar with two rod bosses:
  - Guide: two 4 mm hardened rods (98 mm, cut from 100 mm stock) cantilevered from the hand bosses (M3 grub
    screw into a heat-set insert), and LM4UU bearings pressed into the lugs on the cup shell (rod pitch 134 mm,
    clear of the 121 mm cup).
  - Springs: one stock spring on each rod, **RS PRO 821-352** (stainless 302, wire 0.5 mm, OD 6.8 mm, free
    length 65 mm, 0.11 N/mm, min working length 17.4 mm at 5.47 N; datasheet, RS Components). The two in parallel
    give 220 N/m. Each sits in a 14.5 mm pocket in a boss and pushes on the lug's rear face. Rest length is
    62.9 mm (2.1 mm = 0.46 N preload), so full travel ends at 17.9 mm, just above the 17.4 mm minimum.
  - Stops: the rear stop is a 12.7 x 3.5 mm self-adhesive rubber bumper on the plate under the cup bottom. The front
    stop is a 4 mm shaft collar on each rod with an NBR O-ring (4 x 1.5 mm) as a cushion.
  - Damper: a felt pad in each lug's brake block, pressed on the rod by an M3 set screw. Set it to about 1.5 N
    drag per rod.
  - Cup parts (shell + lugs, liner, LM4UU, felt, brake screws) are the MJCF `cup` body on the `cup_slide`
    joint and sit under the GLB node `cup_slide` (child of `hand`, at the cup centre at rest; `extras` give the
    axis +x, range [-0.045, 0] m). `cup_center` stays on the hand at fk(q).
  - The spring can't do 50 mm: 65 - 17.4 = 47.6 mm max deflection, so v2 uses 45 mm and the generator clamps
    and warns above about 46 mm. hand_m 0.08 -> 0.125 (the minimum that clears the wrist hub with 45 mm travel
    plus the bumper; the generator warns with the required value).
- **Finding: the spring needs a real damper.** The earlier "zeta 1" sim result assumed a viscous damper the
  hardware doesn't have. LM4UU + spring alone is roughly undamped, and the spring throws the ball back out
  (200 throws, seed 0):

| Slide damping | Catch | Bounced out | Skip on impact |
|---|---|---|---|
| viscous zeta 1.0 (old assumption) | 93% | 3 | 40% |
| viscous zeta 0.3 / 0.2 / 0.1 | 94% / 52.5% / 31.5% | 1 / 84 / 126 | 26.5% / 26.5% / 30.5% |
| zeta 0.05 + friction 0.5 / 1 / 2 N | 29% / 42.5% / 89.5% | 131 / 104 / 10 | 30% / 25.5% / 22.5% |
| **zeta 0.05 + friction 3 N (v2)** | **93.5%** | 2 | **24%** |
| zeta 0.05 + friction 4 / 6 N | 93% / 93% | 3 / 3 | 24.5% / 30.5% |

  Coulomb friction from 3 to 6 N is a flat plateau. Viscous damping falls off a cliff between zeta 0.3 and 0.2,
  and a hobbyist can't build a friction-free viscous damper of about 2.5 N s/m cheaply. So v2 uses the
  adjustable felt brake (`catcher.spring_friction_n: 3.0`, a sim-only key). Cost: the brake can hold the cup up to
  (3 - 0.46) / 220 = 11.5 mm behind its front stop after a catch. That offset is along the cup axis, which
  costs about 3 ms of timing at 4.3 m/s (estimate; not simulated, because each sim throw starts at the stop).
- **v2 vs v1** (computed; sims with 4 microsteps, 200 throws seed 0, and 400 throws seed 1):

| | v1 | v2 |
|---|---|---|
| Catch, 200 / seed 0 | 92.5% | 93.5% |
| Catch, 400 / seed 1 | 87.3% | 92.2% |
| Skip on impact, seed 0 | 75% (elbow 135) | 24% (elbow 36) |
| Skip on impact, seed 1 | 73.8% | 26.3% |
| Failures, seed 0 | out of reach 15 | out of reach 10, too slow 1, bounced out 2 |
| Torque margin (50% budget) shoulder / elbow / wrist | 1.87 / 2.34 / 5.16 | 1.70 / 1.99 / 2.75 |
| Hand / cup body mass | 47 / 67 g | 75 / 78 g |
| Moving mass / total | 0.449 / 2.241 kg | 0.488 / 2.280 kg |
| Reach | 0.52 m | 0.565 m |
| Printed / purchased | 723 g / ~$117 | 734 g / ~$128 (38 BOM lines) |
| EVA foam liner (e 0.40) | 54% (round 3) | 92.5% (skip 42.5%) |

  The longer hand (+45 mm) costs margin but every motor stays above 1.7x the 50% budget. It also adds reach,
  which accounts for most of the out-of-reach drop (15 -> 10).
- Verification (tests): catalogue rate x (free - min working) = load at min, within 6% (0.11 x 47.6 = 5.24
  vs 5.47 N, PASS). Spring pair = sim k (220 = 220, PASS). Rest length - travel >= min working (17.9 >= 17.4,
  PASS). The cup bottom reaches the bumper exactly at full travel (< 0.05 mm, PASS). MJCF stiffness, springref
  (= preload), range, frictionloss and cup mass equal the CAD values (PASS). Passive force at -20 mm =
  k (preload + 0.02) (PASS). ArmModel gravity torque = MuJoCo at 10 random poses with the slide body (PASS).
  GLB `cup_slide` at fk(q) for 6 poses, and at -45 mm it is 45 mm back along the hand axis (PASS).

Not verified: the felt-brake drag (estimate, set and measure it with a luggage scale); LM4UU mass (2.5 g,
estimate); the bench behaviour of 4 mm cantilevered rods under ball side loads (12 N/mm per rod, computed);
the cup's rest offset after a catch; Coulomb friction as MuJoCo `frictionloss` (no stiction model).

Open decisions: friction brake (v2) vs. a bought low-friction air dashpot (needs zeta >= 0.3, about 2.5 N s/m;
Airpot-type, not sized) vs. closed-loop steppers; make v2 the chosen variant (`design/chosen` still says v1).

**Inspiration intake (2026-10-23): pictures, links and videos -> digests.**
- New package `mechy/intake/` (`from mechy.intake import digest, digest_all, pending`).
  `digest(project, source)` takes a YouTube/video URL, a web page URL, an image URL, or a local
  video/image/.html path and writes `inspiration/<slug>/source.json` (url, title, duration, licence
  when known, keyframe list, transcript origin) plus, by kind:
  - video (yt-dlp for URLs, ffprobe/ffmpeg for all): captions or auto-captions in English or the
    original language (no audio download when captions exist), a <= 360p video (gitignored),
    up to 12 keyframes in `frames/` (strongest scene cuts >= 0.25 spread apart, filled evenly
    over long shots), `contact.jpg`, `transcript.txt` (`[m:ss] text`, roll-up captions de-duplicated).
    faster-whisper transcribes only if it is installed and there are no captions; sidecar
    `.vtt/.srt` next to a local video is used first.
  - web page: title, description, main text (`page.txt`, trafilatura when installed, else a
    stdlib parser that skips nav/footer), licence (rel=license / CC text), embedded videos, up to
    6 EXIF-free images (icons, logos and < 120 px skipped).
  - image: EXIF-free copy (orientation applied; GPS/camera data dropped) + 320 px thumbnail. A
    file outside the project is not copied in, only the clean copy.
- `inspiration/notes/<slug>.md` is a deterministic skeleton (<= 220 words, so the research agent
  has room within the 300-word limit): What | Where table, keyframe table (time, frame path),
  mechanism keyword counts and transcript/page excerpts (gear, belt, stepper, servo, bearing,
  linkage, torque, catch, motor, pulley ...), and `TODO(research)` lines. A note edited after the
  last digest is never overwritten (new skeleton goes to `inspiration/<slug>/note.skeleton.md`)
  unless `force=True`. URL sources set `digested: <note path>` in `inspiration/links.yaml` (the
  entry is added if missing). `pending()` lists undigested links and media files dropped at the top
  of `inspiration/`; `digest_all()` digests them.
- Wiring is ready in `mechy/intake/register.py` (not yet in cli.py / mcp_server.py):
  `add_intake_parser` + `run_intake_cli` (`mechy intake add|all|pending`) and
  `register_mcp_tools` (`intake_digest`, `intake_pending`).
- Prompts: research completes the TODO(research) lines from the contact sheet, keyframes and
  transcript, cites timestamps/frames, and respects the licence; the planner reads
  `inspiration/notes/*.md`, digests pending sources first, and makes the first research card
  complete them. `pyproject.toml` has an `intake` extra (yt-dlp, trafilatura, pillow).
- Tests: `tests/test_intake.py` (17 + 1 live test skipped unless `MECHY_NET_TESTS=1`) use an
  ffmpeg testsrc clip with a scene cut, a sine track and a sidecar VTT, a generated JPEG with
  EXIF/GPS, and a local HTML page served from 127.0.0.1 (which also runs yt-dlp's generic
  downloader offline). Keyframe times are checked against the testsrc counter in the frames.

Not verified: live YouTube (this build environment's proxy answers 403 to youtube.com and most
sites, so only the local-server paths ran); faster-whisper (not installed here); HEIC photos (needs
pillow-heif or macOS `sips`, untested).

**Round 4 (2026-10-23): documents generator (`mechy doc build`).**

| What | Where |
|---|---|
| Generator | `mechy/docgen/` (`build.py` pipeline, `collect.py` project data, `assembly.py` step tree, `figures.py`, `raster.py`, `templates/*.typ`) |
| CLI / MCP | `mechy doc build <variant> [--only build_guide\|report]`; MCP `doc_build` (`tools.doc_build`) |
| Output | `docs/<variant>/build_guide.pdf`, `report.pdf`, plus `*.typ`, `*.data.json`, `img/` (sources) |
| Tests | `tests/test_docgen.py` (8) |

- PDFs come from Typst through the `typst` Python package (it bundles the compiler; wheels for macOS arm64/x86
  and Linux, no browser, TeX or network). The data goes to `<doc>.data.json`, and the `.typ` templates read it,
  so text from the project is never parsed as markup. `typst compile build_guide.typ` in docs/<variant>/ rebuilds
  without the engine. Fonts: Inter / JetBrains Mono / Helvetica / Menlo when installed, else matplotlib's DejaVu
  (passed as a font path, so every machine has one). New dependencies: `typst`, `pillow` (already pulled in by
  matplotlib), and `pypdf` for the dev tests. `mechy doctor` lists typst.
- Drawing-sheet look (ui-style.md): A4 landscape, paper colour, a double border with zone markers, a faint dot grid,
  and a title block on every page (project, variant, sheet title, scale, date, sheet n/N, read from per-sheet
  metadata). Labels and tables are monospace with hairline rules, and notes are numbered [1] [2].
- Build guide (example v2: 38 pages): cover render; contents plus What | Where with rebuild commands; BOM
  (38 lines, 211 pieces, $127.52, equal to bom.csv); print list with printer settings and grams (26 pieces,
  734.5 g); one sheet per printed STL (19). Each part sheet has FRONT/TOP/RIGHT in third-angle projection at a
  standard scale (true size on A4 at 100%), the iso view, overall dimensions measured from the STL, and the bed
  line. Then 11 assembly steps: prep, base, turntable, tower/motors, drive pulleys and motor belts, upper arm,
  forearm, hand, cup slide, electronics, tension and home. Each step has a render (new parts blue and moved out,
  zoomed when small), its printed parts, its hardware counts, and instructions filled from the design: belt loops,
  homing sensors, slide numbers, and the order parts thread onto each shaft (computed from the solids). After
  that: a belts/tensioning/homing sheet (from mass_props.json and the design's belts), wiring + Vref + flashing +
  calibration (parsed from control/<variant>/README.md, or a note to run `control gen`), and a checks / Not
  verified / Open decisions sheet built from the summaries, design/chosen and unanswered questions/options.
- Report (example v2: 7 pages): requirements vs results. Catch rate 92% of 50 throws with a Wilson 95% interval
  of 81-97% (computed), so it PASSES against the 80% target. Also launch-speed coverage, cup fit, and per-motor
  torque budgets (1.70 / 1.99 / 2.75x). Then a catch map (top + side, reach circle), outcome bars, torque-margin
  chart, decisions.md as a table, open decisions, not-verified items, and a "where the numbers come from" table
  (computed / datasheet / assumed / estimate, with the source file or YAML comment).
- Renderer: `docgen/raster.py` is a scanline z-buffer, vectorised over triangles (2600x2000 px of the full
  assembly, about 98k triangles, in ~4.5 s). It does orthographic views with exact world-to-pixel frames (for
  true-scale drawings) and draws ink outlines at part boundaries, depth steps and 32 deg creases. `cad/render.py`
  is unchanged. A full `doc build` takes ~50 s on 4 cores.
- **Finding (from the new checks):** the firmware's homing disagrees with the CAD sensors. control/v2/README.md
  homes base at its -150 deg limit and elbow at its -135 deg limit with switches, but the CAD draws a hall + magnet
  index at q0 = 0 (base) and a hall at a2 = q1 + q2 = 0 (elbow, motor-side angle). Shoulder (120 deg) and wrist
  (-90 deg) match. The guide shows both as FAIL and lists them first under Open decisions. `control gen` should
  read `mass_props.json` -> `homing` (not touched here: out of scope).

Not verified: printing at 100% on a real printer (the SVG drawings are sized in mm, and Typst places them at that
width); the belt-deflection rule of thumb (~1/64 of the span, labelled an estimate); PETG insert and nozzle
temperatures (typical values, labelled); rendering on macOS (same wheels and fonts fall back, but not run there).

Open decisions: fix the homing mismatch in `control gen` (use the CAD's hall index for base and elbow) or
change the CAD to limit switches; whether docs should be white paper for home printing (the sheet fill is the
ui-style paper #F5F5F3); `provider: none` task cards cannot run `doc.build` yet (agents/runner.py not touched).

**Round 4b (2026-10-24): intake wired in, homing follows the CAD sensors, `--print` paper.**

| What | Where |
|---|---|
| Intake CLI / MCP / tools | `cli.py` (`mechy intake add\|all\|pending`), `mcp_server.py` (`intake_digest`, `intake_pending`), `tools.py` TOOL_NAMES |
| Auto-digest before plan/run | `agents/runner.py` `digest_pending` (used by `run_planner` and `scheduler.run_all`; `--no-intake`) |
| `provider: none` tools | `agents/runner.py` `_run_none`: + `intake.digest` (once), `control.gen`, `doc.build` |
| Homing table | `control/config.py` `derive_homing`, `belt_arm_homing_rows`; `control/firmware.py`; `templates/mechy_arm.ino` homing |
| Docs paper | `docgen/raster.py` `set_paper`; `mechy doc build --print`; `templates/mechy_sheet.typ` reads `meta.paper` |
| Doctor | `doctor.py` `docs` and `intake` sections |
| Contract | `docs/architecture/contracts.md` section 12 |

- Intake: `mechy plan` and `mechy run` digest pending sources (links.yaml, media in inspiration/) before planning / running
  cards; failures are reported under `intake.errors` and never fail the command. The planner card and `research` cards
  get `intake.digest` / `intake.pending`.
- **Homing fix.** `control gen` now reads `mass_props.json` `homing` (or the same belt_arm table when the file is missing or
  stale): base = A3144 hall index at q0 = 0, shoulder = KW12-3 at its upper limit (120 deg), elbow = hall index at the
  elbow motor's angle a2 = q1 + q2 = 0, wrist = KW12-3 at its lower limit (-90 deg). Order shoulder > elbow > wrist >
  base (the CAD's `homing_order` changed to match: the arm lifts clear first, and the elbow index needs q1 known).
  Firmware homing per joint: limit switch = one sweep toward it, clear, slow edge (as before). Index sensor = bounded
  sweeps both ways: with a position estimate (homed before) straight toward the sensor, else first toward the side
  of the sensor with the smaller range (worst overrun past a limit = that side + 10 deg), then back by that + the
  other side + 10 deg; then cleared and crossed slowly in HOME_DIR, and the centre of its window (mean of the two
  debounced edges) is the home. Motor-space sensors (elbow) solve q2 from a2 and the homed q1.
- Tests (firmware on the PC mock, hall window 0.12 rad): homing from 4 start poses, including both sides of each index
  and starting inside a window, ends at the ready pose within 2.5 steps; firmware STATUS agrees with the truth; re-homing
  from the estimate takes 30 s from the ready pose (first homes 28-67 s); a dead elbow hall gives `ERR HOME_FAIL joint=2`
  after exactly the computed bounded sweeps. Config from a mass_props table, params overrides, and the order check.
- Docgen: the homing check compares angle, coordinate (q_j vs a_k) and sensor kind. On a scratch project (example,
  `cad build v2`, `control gen v2`, `doc build v2`): all 4 homing rows PASS, `checks_failed` is empty (was base and elbow
  FAIL), 38 pages. `--print` pages are #FFFFFF (sampled from the rendered PDF), default pages #F5F5F3.
- `mechy doctor` reports typst (python package and optional CLI) and the intake extras (yt-dlp, trafilatura,
  ffmpeg/ffprobe, faster-whisper, pillow) without failing when optional ones are missing.

Not verified: homing on the real arm (hall window width, A3144 hysteresis, magnet polarity; the mock window is
symmetric); the base's first sweep can turn up to 160 deg past a limit if it starts at the far end (README warns to turn
it near 0 by hand before the first HOME after power-up); a dead index sensor can drive a joint up to the larger side past
the sensor before HOME_FAIL; live YouTube intake (proxy).

Open decisions: whether the elbow should home with the forearm level from the shoulder's raised pose (a2 = 0 means
q2 = -120 deg there; collision with the tower not checked); end stops vs. stall for joints that overrun.
