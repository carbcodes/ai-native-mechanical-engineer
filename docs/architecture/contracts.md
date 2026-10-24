# Mechy internal contracts

The shared interfaces between the three parts of the Mechy app. Every agent working on Mechy reads this first. Change it only on purpose, and update every side that depends on what you changed.

```
app/      SwiftUI macOS app (the windows the user sees)
engine/   Python package `mechy` (CLI, project files, agents, CAD, sim, MCP tools)
core/     C++ library `mechy-core` with Python bindings `mechy_core` (fast math)
site/     (the existing landing page stays at the repo root for now; do not touch it)
```

The app never does engineering itself. It starts `mechy` engine commands, reads the files they write, and shows them. The engine never draws UI.

## 1. Project folder

A Mechy project is one folder and one git repo. Paths are relative to the project root.

```
brief.md              one-page goal, written with the user
requirements.yaml     all target numbers (see 1.1)
decisions.md          one line per decision: "- YYYY-MM-DD: <decision> (why: ...) [evidence](path)"
inspiration/          user files (images, videos, links.yaml)
  notes/<source>.md   one digest per source, <= 300 words
research/<topic>/     summary.md + any files
hw/motors.yaml        motors the user owns (see 1.2)
hw/drivers.yaml       drivers and controller boards
design/v<N>/          one variant per folder:
  params.yaml           arm parameters (see 1.3)
  model.py              build123d script reading params.yaml (optional; default generator used if absent)
  arm.step arm.glb arm.stl
  arm.xml               MuJoCo MJCF generated from params.yaml
  thumb.png             preview render
  summary.md
design/chosen         text file holding the chosen variant name, e.g. "v3"
sim/<task-id>/        report.json (see 3.2), plots/*.png, video.mp4, summary.md
control/              firmware and host control code
docs/                 generated outputs (report.pdf, bom.csv)
tasks/<id>.yaml       task cards (see 2)
tasks/<id>.status.json
questions/<id>.yaml   questions for the user (see 4)
options/<id>.yaml     option sets for the user to pick from (see 5)
.mechy/project.json   {"name", "created", "schema": 1}
.mechy/events.jsonl   append-only event log (see 6)
.mechy/usage.jsonl    one line per agent run: task id, provider, model, duration_s, tokens if known
```

### 1.1 requirements.yaml

```yaml
catch:
  throw_distance_m: 1.8
  ball_diameter_m: 0.067
  ball_mass_kg: 0.057
  max_launch_speed_mps: 6.0
  target_catch_rate: 0.8
vision:
  fps: 60
  latency_s: 0.05
```

### 1.2 hw/motors.yaml

```yaml
motors:
  - id: nema17
    count: 4
    holding_torque_nm: 0.45      # assumed until the user confirms the model
    rotor_inertia_kgm2: 5.4e-6
    max_speed_rps: 10             # usable speed with A4988 at 12 V, approximate
    step_angle_deg: 1.8
    torque_curve:                 # [rev/s, N*m] pull-out torque, approximate
      - [0, 0.45]
      - [2, 0.40]
      - [5, 0.28]
      - [10, 0.12]
drivers:
  - id: a4988
    count: 4
    max_current_a: 2.0
    microsteps: 16
controller: arduino-uno           # unconfirmed
```

### 1.3 design/v<N>/params.yaml (4-DOF catching arm)

```yaml
name: v1
joints:            # order matters: base yaw, shoulder pitch, elbow pitch, wrist pitch
  - {name: base,     axis: z, limit_deg: [-150, 150], gear_ratio: 3.0, motor: nema17}
  - {name: shoulder, axis: y, limit_deg: [-10, 120],  gear_ratio: 4.0, motor: nema17}
  - {name: elbow,    axis: y, limit_deg: [-135, 135], gear_ratio: 3.0, motor: nema17}
  - {name: wrist,    axis: y, limit_deg: [-90, 90],   gear_ratio: 2.0, motor: nema17}
links:
  base_height_m: 0.12
  upper_arm_m: 0.22
  forearm_m: 0.20
  hand_m: 0.06
  link_mass_kg_per_m: 0.35      # printed/tube link mass per metre
  motors_at_base: true          # shoulder, elbow and wrist motors mounted low, belt driven
catcher:
  type: cup                     # cup | net
  diameter_m: 0.11
  depth_m: 0.06
  mass_kg: 0.04
```

## 2. Task cards (tasks/<id>.yaml)

```yaml
id: T014-shoulder-torque          # T<nnn>-<slug>
role: sim                         # planner | research | concept | cad | sim | controls | docs
provider: claude                  # claude | codex | none (pure code task)
tier: strong                      # strong | fast
goal: One sentence.
inputs: [design/v3/params.yaml, hw/motors.yaml]
tools: [sim.run, motor.check]     # MCP tool names the worker may call
outputs: [sim/T014/report.json]
depends_on: [T012-cad-v3]
done_when: One checkable sentence.
```

`tasks/<id>.status.json`: `{"state": "queued|running|done|failed|blocked", "started": iso, "finished": iso, "summary": "sim/T014/summary.md", "error": null}`.

Every worker must write `summary.md` (<= 300 words: what was done, key numbers, open issues) next to its outputs. The planner reads summaries, not raw outputs.

## 3. Engine CLI (`mechy`)

All commands take `--project <dir>` (default: cwd) and, with `--json`, print one JSON object per line to stdout (events, see 6) and a final `{"type": "result", ...}` line. Exit code 0 on success.

| Command | Does |
|---|---|
| `mechy init <dir> [--example tennis-catcher]` | Create a project folder (with example files) |
| `mechy cad build <variant>` | params.yaml -> arm.step, arm.glb, arm.stl, arm.xml, thumb.png |
| `mechy sim catch <variant> [--throws 200] [--seed 0]` | Run the catch sweep, write sim/<task-id>/ |
| `mechy agent run <task-id>` | Run one task card through its provider CLI |
| `mechy plan` | Run the planner on brief/requirements, write task cards |
| `mechy run` | Scheduler: run all ready task cards, in parallel up to `--jobs` |
| `mechy mcp` | Start the `mechy-tools` MCP server over stdio |
| `mechy doctor` | Check claude/codex CLIs, logins, Python deps, mechy_core |

### 3.1 MCP tools (`mechy-tools`)

`cad.build(variant)`, `cad.params_get(variant)`, `cad.params_set(variant, patch)`, `sim.catch(variant, throws, seed)`, `ball.predict(points)`, `ik.solve(variant, target_xyz, pitch)`, `motor.check(variant, trajectory?)`, `render.views(variant)`, `project.summary()`, `question.ask(...)`, `options.present(...)`. Every tool returns small JSON plus file paths, never large blobs.

### 3.2 sim/<task-id>/report.json

```json
{
  "variant": "v1",
  "throws": 200,
  "catch_rate": 0.74,
  "reach_rate": 0.81,
  "skipped_step_rate": 0.06,
  "mean_margin_s": 0.08,
  "failures": {"out_of_reach": 12, "too_slow": 25, "skipped_steps": 12, "bounced_out": 3},
  "worst_joint": "shoulder",
  "plots": ["plots/catch_map.png", "plots/joint_torque.png"],
  "video": "video.mp4"
}
```

## 4. Questions (questions/<id>.yaml)

```yaml
id: Q003-throw-height
asked_by: T001-planner
text: How high will the ball be when it's thrown?
kind: choice                 # choice | number | text | image
choices: [Underhand from waist, Overhand from shoulder, Not sure]
image: inspiration/notes/throw.png   # optional
answer: null                 # app writes the answer here
```

## 5. Option sets (options/<id>.yaml)

```yaml
id: O002-arm-layout
prompt: Pick an arm layout
options:
  - id: v1
    title: Belt-driven, motors at base
    image: design/v1/thumb.png
    model: design/v1/arm.glb
    stats: {catch_rate: 0.74, reach_m: 0.48, cost_usd: 35}
  - id: v2
    ...
chosen: null                 # app writes the chosen option id
feedback: null               # app writes free-text tweak requests
```

## 6. Events (.mechy/events.jsonl and --json stdout)

One JSON object per line: `{"ts": iso, "type": ..., ...}`. Types:
`task.started {task}`, `task.progress {task, message, fraction?}`, `task.done {task, summary}`, `task.failed {task, error}`, `file.written {path}`, `question.asked {id}`, `options.presented {id}`, `agent.output {task, text}` (short), `result {...}`.

The app tails `events.jsonl` to update panels; it also watches the folder for file changes.

## 7. mechy_core Python API (C++ via pybind11)

All units SI, angles in radians. Arrays are numpy float64.

```python
import mechy_core as mc

# Ball flight with quadratic drag. points: (N,4) [t, x, y, z]; N >= 3.
fit = mc.ball_fit(points, mass=0.057, diameter=0.067)   # -> dict(p0, v0, t0, residual)
traj = mc.ball_predict(p0, v0, dt=0.002, t_max=2.0, mass=0.057, diameter=0.067)  # (M,4)
hit = mc.ball_intercept(traj, center, radius)           # first point inside sphere -> dict(t, p, v) | None

# 4-DOF arm kinematics. arm = mc.Arm(base_height, upper, fore, hand, limits=(4,2))
q = arm.ik(target_xyz, hand_pitch)        # -> (4,) or None if unreachable
p, pitch = arm.fk(q)
ok = arm.reachable(target_xyz, hand_pitch)

# Stepper-limited motion. motor: mc.Stepper(torque_curve (K,2) [rev/s, N*m], gear_ratio, rotor_inertia)
prof = mc.plan_move(q0, q1, motors, load_inertia (4,), t_avail)  # -> dict(feasible, t_needed, t_per_joint (4,), peak_torque_frac (4,))
batch = mc.plan_batch(q0, Q1 (N,4), motors, load_inertia, T_avail (N,))  # vectorised, multithreaded
```

### 7.1 Additions from the core implementation (authoritative over the sketch above)

- `ball_predict(..., t0=0.0)` so output times continue from `fit["t0"]`. `ball_fit`, `ball_predict`, `ball_intercept` accept `cd`, `rho`, `g`. `ball_fit` also returns `iterations`.
- Arm conventions (the MJCF must match): q0 = base yaw; q1 = shoulder elevation above horizontal; q2, q3 relative to the previous link, positive = up. Hand pitch = q1+q2+q3 in the arm's vertical plane, pointing away from the base axis. Positive elevation is rotation about the arm-plane −y axis, so a +y MuJoCo hinge needs its sign flipped. IK never returns poses leaning back over the base. `ik(target, pitch, seed=None)` picks the in-limit solution nearest `seed`. `Arm()` defaults to v1 values; `limits=None` means section 1.3 limits; `.limits` property.
- `Stepper(torque_curve, gear_ratio, rotor_inertia, max_speed_rps=None)` with `torque_at(rps)` and `max_joint_speed`.
- `plan_move` / `plan_batch` take `safety=0.7` and optional `load_torque` (static per-joint torque, e.g. gravity) and return `limiting_joint`. `load_inertia` is joint-side (kg·m² about each joint axis), computed by the caller per pose: pass (N,4) to `plan_batch`. `plan_batch` returns a dict of arrays, accepts `q0`/`load_inertia` as (4,) or (N,4), `T_avail` scalar or (N,), and `threads=`.
- `min_move_time()` added. `Arm` and `Stepper` pickle (multiprocessing-safe).
- Helpers: `mc.default_arm()`, `mc.default_motors()`, `mc.NEMA17_TORQUE_CURVE`.
- Open: 10 rev/s at 16 microsteps = 32k steps/s per motor, beyond an Arduino Uno driving 4 motors; real step-rate cap is unknown.

## 8. App–engine additions (from the app implementation)

1. `inbox/<yyyyMMdd-HHmmss>.md`: requests typed in the app's agent bar (front matter: `from`, `created`). `mechy plan` reads unprocessed inbox files and marks them processed (e.g. moves them to `inbox/done/`).
2. `inspiration/links.yaml`: `links: [{url, title?, added}]`.
3. Global flags `--project <dir>` and `--json` must be accepted after the subcommand and its arguments (`mechy cad build v1 --project X --json`).
4. Provider settings via env: `MECHY_PROVIDER=auto|claude|codex`, `MECHY_CLAUDE_BIN`, `MECHY_CODEX_BIN`.
5. `.mechy/viewer/` is an app-owned cache; the project `.gitignore` lists it.
6. A final `result` event with `ok: false` and `error` means failure even if the exit code is 0. Successful results carry `ok: true`.

## 9. Engine additions (from the engine implementation)

1. MCP tool names use underscores on the wire (`cad_build`); task cards keep dotted names and the adapter maps `cad.build` to `mcp__mechy-tools__cad_build`.
2. `report.json` `failures` adds `missed` (ball never touched the cup) so catches + failures = throws. Extra fields: `skip_before_contact_rate`, `mean_peak_torque_frac`, `mean_pred_err_m`, `meta`. `skipped_step_rate` counts skips at any time, including on ball impact.
3. `mechy sim catch <variant> --task <id> --microsteps <n>`; task id defaults to `catch-<variant>`.
4. Drivers live in `hw/drivers.yaml` (wins over any `drivers:` in motors.yaml); `max_step_rate_hz` (default 4000) is on the driver entry.
5. `requirements.yaml` adds `vision.noise_m`, `vision.observe_s` and a `throw:` section (launch height, flight time, aim point, spread).
6. `cad.params_set` takes `from_variant`; `sim.catch` takes `task`, `microsteps`; `ik.solve` takes `pitch` in degrees.
7. Planner writes its summary to `tasks/summary.md`.

## 10. Belt-arm generator additions (round 2)

- params.yaml: `style: belt_arm | simple` (default `simple` when absent; new designs use `belt_arm`), `catcher.liner: eva_foam | net_pocket`, `catcher.restitution` (estimate unless measured), `catcher.entry_offset_deg`, optional `belt_arm:` block (material, infill, wall_mm, ...). Pulley teeth = round(20 × gear_ratio).
- Variant folder adds `stl/<part>.stl`, `print_list.csv`, `bom.csv`, `mass_props.json` (MuJoCo masses/inertias come from the solids).
- report.json `meta` adds `style`, `liner`, `cup_restitution`, `masses_from_cad`.

## 11. Sim replay and animatable GLB (round 3)

- `arm.glb` scene graph has one node per moving body, named exactly `base`, `turntable` (rotates by q0 about +z), `upper_arm` (child of turntable, q1), `forearm` (child of upper_arm, q2), `hand` (child of forearm, q3, includes the cup). Each node's local origin sits on its joint axis, so the viewer animates by setting the node's rotation about its joint axis (z for the turntable; the arm-plane pitch axis for the others, sign per section 7.1). Other parts are children of the body they move with. GLB units are metres.
- `sim/<task-id>/replay.json`: a few representative throws (at least 1 caught, 1 failed when available):
```json
{"variant": "v1", "dt": 0.01, "joint_names": ["base", "shoulder", "elbow", "wrist"],
 "joint_axes": {"turntable": [0,0,1], "upper_arm": [0,-1,0], "forearm": [0,-1,0], "hand": [0,-1,0]},
 "throws": [{"id": 17, "outcome": "caught", "t": [...], "q": [[q0,q1,q2,q3], ...],
             "ball": [[x,y,z], ...], "predicted": [[x,y,z], ...], "catch_point": [x,y,z]}]}
```
  Angles in radians, positions in metres, world frame = arm base frame (z up, +x toward the thrower).
- (round 3) GLB root node `arm` converts z-up to glTF y-up; chain `arm > base > turntable > upper_arm > forearm > hand > cup_center`. The file's rest pose is the ready pose (nodes carry non-zero rest rotations); viewers read rest angles from the node rotations. A custom model.py still exports a flat GLB.
- (round 3) belt_arm coupling: motor-side angle a = (q0, q1, q1+q2, q1+q2+q3), motor angle = ratio × a; written to `mass_props.json` as `motor_map` with a `homing` table.

## 12. Intake, docs paper and homing sensors (round 4b)

- CLI: `mechy intake add <url-or-file>... [--force] [--no-transcribe] [--no-video] [--max-frames N]`, `mechy intake all`, `mechy intake pending` (result: `{pending: [...], count}`). `mechy plan` and `mechy run` digest pending inspiration first (links.yaml entries without a live `digested` note, media dropped at the top of `inspiration/`); `--no-intake` skips it. Their result adds `intake: {digested: [note paths], errors: [{source, error}]}` when anything was pending, and the events show a `task.*` sequence with `task: "intake"`. A failed digest never fails the plan/run.
- Tools: `intake.digest {source, force?}` and `intake.pending {}` (MCP `intake_digest`, `intake_pending`) are in TOOL_NAMES; the planner card and every `research` card may call them. `provider: none` cards can run `intake.digest` (once, `digest_all`), `control.gen` (card key `board` optional) and `doc.build` (card keys `only`, `print_paper` optional) per variant named in their `design/`, `control/` or `docs/` paths.
- `mechy doc build <v> [--only build_guide|report] [--print]`: `--print` gives white pages and render backgrounds for home printers; the default stays the drawing-sheet paper `#F5F5F3`. MCP `doc_build` takes `print_paper`. `<doc>.data.json` `meta.paper` holds the hex colour; result `paper: sheet|white`.
- `mechy doctor` adds `docs {typst_python, typst_cli, ready}` and `intake {yt-dlp, trafilatura, ffmpeg, ffprobe, faster-whisper, pillow, videos_ready, pages_ready, images_ready}` (optional extras; they never make `ok` false).
- Homing: `control gen` takes each joint's sensor from `design/<v>/mass_props.json` `homing` (`sensor`, `home_deg`, `coordinate`) and `homing_order` (belt_arm CAD: shoulder, elbow, wrist, base); without a current mass_props it uses the same belt_arm table; `simple` style keeps limit switches at DEFAULT_HOME. params `control:` overrides: `home_pos_deg` (in the sensor's coordinate), `home_side` (approach direction), `home_kind` (`limit` | `index`), `homing_order`, `home_window_deg`, `home_margin_deg`. config.h adds `HOME_KIND[4]` (0 limit switch, 1 index), `HOME_COORD[4]` (255 = joint angle q_j, k = motor k's angle a_k = M[k]·q), `HOME_WINDOW`, `HOME_MARGIN`; `HOME_POS` is in the sensor coordinate. A sensor on a_k requires the other joints in row k of M to home first (control gen refuses otherwise). host_config.json `homing` adds `kind`, `coord_motor`, `coord`, `sensor`, `source`. The control README "Switch at" cell reads `hall index, a2 = q1+q2 = 0.0 deg` or `max limit switch, q1 = 120.0 deg`; docgen's homing check compares angle, coordinate and sensor kind with the CAD.

## 13. Pick-and-place sim (`mechy sim pick`)

- CLI: `mechy sim pick <variant> [--task <id>] [--payload <kg>] [--microsteps n]`; default task `pick-<variant>`; MCP tool `sim_pick`. `ref_arm` (`parallel_level`) designs only.
- `requirements.yaml` `pick:` block: `payload_kg`, `pick_xyz_m`, `place_xyz_m` (arm base frame, z = tool height above the table plane), `lift_m`, `target_cycle_s`, `target_payload_kg`, `usable_torque_fraction` (default 0.5). A project with `pick:` and no `catch:` is a pick project (the app runs this sim for "Run sim" and the Make-it pipeline).
- `sim/<task>/report.json` is the catch report's shape (`variant`, `failures: {}`, `worst_joint`, `plots`, `video`, `replay`) plus: `kind: "pick"`, `headline {label, value, unit, target, meets}` (payload capacity in g: the weakest pose of the cycle against the usable torque budget), `metrics [{label, value, meets?}]` (shown beside the headline), `payload_capacity_g`, `design_payload_g`, `cycle_s`, `picks_per_min`, `peak_motor_load` (fraction of pull-out torque, per motor), `static_budget_nm`, `reach_table_m`, `capacity_at_waypoints_g`, `segments`, `meta.estimates`. `catch_rate` is absent.
- Plots: `plots/workspace.png` (payload map over the reachable r-z plane with the arm at the pick and place), `plots/cycle.png`, `plots/payload_budget.png`. Shared look: `mechy/sim/style.py` (also used by the catch plots).
- `replay.json` follows section 11 with one throw, `outcome: "placed"`, `ball` = the payload (tray, then on the tool, then in the bin) and a top-level `ball_diameter_m` (the viewer draws a sphere of that size; default 0.067). Docgen: the report PDF shows the payload headline and a pick-and-place sheet; the guide gets a stat row.
- Model: static holding torque per motor `C^-T tau_q` (CAD masses + payload) against `usable x holding x ratio`; cycle = min-jerk joint moves (down, grasp 0.15 s, up, carry, down, release 0.15 s, up, return) limited by the driver step-rate speed cap and by half the pull-out torque left after gravity; load along the cycle = (gravity + inertia x acceleration) / pull-out torque at the current speed. No belt stretch, backlash or arm flex. Verified against BAM `analysis/sizing.py` (`tests/test_pick.py`).
