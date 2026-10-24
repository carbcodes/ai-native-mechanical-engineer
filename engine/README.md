# mechy engine

Python package `mechy`: project files, CAD, simulation, MCP tools and agent runner for the
Mechy app. Contract: `docs/architecture/contracts.md`.

```bash
cd engine && uv venv .venv && uv pip install --python .venv/bin/python -e '.[dev]' ../core
.venv/bin/mechy init ~/catcher --example tennis-catcher
cd ~/catcher
mechy cad build v1                 # arm.step/.stl/.glb/.xml + thumb.png
mechy sim catch v1 --throws 200    # sim/catch-v1/report.json, plots, summary.md
mechy sim catch v1 --microsteps 8 --task catch-v1-8us
mechy init ~/pickarm --example bam-arm   # BAM pick-and-place arm (20sffactory parallel linkage, 140 mm shanks)
mechy sim pick v1                  # sim/pick-v1/: payload map, cycle time, motor load, replay (contracts 13)
mechy control gen v1 --board uno_cnc   # control/v1/: Arduino firmware, host tracker, wiring README
python control/v1/host/mechy_host.py --dry-run sim/catch-v1/replay.json   # host loop, no hardware
mechy doc build v1                 # docs/v1/build_guide.pdf + report.pdf (Typst sources kept)
mechy plan && mechy run --jobs 3   # planner, then the scheduler
mechy doctor
.venv/bin/python -m pytest         # tests (MECHY_FORCE_FALLBACK=1 to skip mechy_core)
```

Every command takes `--project` and `--json` (before or after its own arguments). With
`--json`, stdout is one event per line, ending with `{"type": "result", "ok": ...}`.

## Pieces
- `project.py`, `events.py`: folder layout (contracts 1), `.mechy/events.jsonl`, git.
- `core.py` / `fallback_core.py`: uses the C++ `mechy_core` when it imports, otherwise a
  pure-Python port with the same API and numbers (contracts 7 and 7.1; tests compare them).
- `arm_model.py`: params + hardware -> masses, pose-dependent inertia and gravity torque,
  step-rate-limited motor speed (`max_step_rate_hz` in hw/drivers.yaml, default 4000).
- `cad/`: build123d generators selected by params `style`: `belt_arm.py` (printable belt-driven
  arm: stl/, print_list.csv, bom.csv, mass_props.json) and `geometry.py` (`simple` blocks), MJCF
  (`mjcf.py`, CAD inertials + liner restitution calibrated by a drop test), z-buffer renders.
  MJCF joint values equal mechy_core's `q` (pitch hinges use axis `0 -1 0`).
- `sim/pick.py` + `sim/style.py`: `mechy sim pick`, a seconds-long static + cycle study for the parallel-linkage
  arm (payload over the workspace, min-jerk pick-and-place cycle against the stepper curve, replay.json for the
  CAD panel); `style.py` is the shared drafting-sheet plot look. See contracts section 13.
- `sim/catch.py`: camera model -> `ball_fit` -> intercept search -> `Arm.ik` ->
  `plan_batch` (gravity included) -> MuJoCo with a stepper model (sinusoidal pull-out
  torque, skipped step = lag over 2 full steps). Runs on all cores.
- `control/`: `mechy control gen` (MCP `control_gen`). `config.py` derives config.h numbers from
  params + hw (steps/rad = 200 x microsteps x round(20 x ratio)/20 / 2pi; speed/accel caps from the
  torque curve x 0.7 minus stretched-arm gravity, like mechy_core); `mapping.py` joint->motor
  matrix (belt_arm pass-through: elbow motor = q1+q2, wrist = q1+q2+q3; `motor_mapping` in
  mass_props.json overrides); `boards.py` Uno + CNC Shield V3 and Mega + RAMPS 1.4 pins;
  `profile.py` Python twin of the firmware's synchronised trapezoid; `protocol.py` line protocol
  with XOR checksums; `templates/` the sketch and host script. `testing/` holds a mocked AVR
  layer + `harness.cpp` that runs the real sketch on the PC (homing against simulated switches,
  move timing), and `avr_build.py` (real ATmega build via arduino-cli, or avr-gcc plus
  `MECHY_ARDUINO_CORE=<ArduinoCore-avr checkout>`; the test skips otherwise).
- `docgen/`: `mechy doc build <variant>` (MCP `doc_build`, `--only build_guide|report`). `collect.py`
  reads bom.csv, print_list.csv, mass_props.json, sim reports, decisions.md, the summaries' "Not
  verified" / "Open decisions" lists and control/<variant>/README.md; `assembly.py` puts every CAD part
  and BOM line into one numbered step (prep, base, turntable, tower/motors, drive belts, upper arm,
  forearm, hand, cup slide, electronics, tension and home), with the parts threaded on each shaft in
  order; `raster.py` is a scanline z-buffer (ortho or perspective, ink outlines at part boundaries,
  depth steps and creases); `figures.py` draws each printed STL in third-angle projection at a
  standard scale (true to scale on A4 at 100%), the step renders and the charts; `templates/*.typ`
  hold the drawing-sheet layout (title block with project, variant, sheet n/N, date and scale on every
  page). PDFs are made by the `typst` Python package, which bundles the Typst compiler: no browser,
  TeX or network, same wheels on macOS (arm64/x86) and Linux. Fonts fall back to matplotlib's DejaVu
  when Inter / JetBrains Mono / Helvetica / Menlo are missing. Output: docs/<variant>/ with the PDFs,
  `*.typ`, `*.data.json` and img/; `typst compile build_guide.typ` there rebuilds a PDF after a hand
  edit of the data. The guide ends with a checks table (BOM totals, part and step coverage, stale CAD,
  firmware homing angles vs the CAD sensors).
- `tools.py`, `mcp_server.py`: `mechy-tools` over stdio. Tool names use `_` instead of
  `.` (`cad.build` -> `cad_build`) because MCP clients reject dots.
- `agents/`: task cards, providers (claude, codex, fake), runner, scheduler, planner.
  Env: `MECHY_PROVIDER`, `MECHY_CLAUDE_BIN`, `MECHY_CODEX_BIN`, `MECHY_FAKE_PROVIDER=1`.
  `provider: none` cards run `cad.build` / `sim.catch` / `render.views` directly.
- `prompts/`: role prompts.

No headless GL here, so thumbnails use matplotlib and no `video.mp4` is written (`"video": null`).
