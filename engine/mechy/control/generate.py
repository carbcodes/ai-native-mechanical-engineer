"""`mechy control gen <variant> [--board uno_cnc|mega_ramps]` -> control/<variant>/."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

from ..events import Events
from ..project import Project, write_json
from .boards import board_for_controller, get_board
from .config import derive
from .firmware import TEMPLATES, firmware_source, render_config_h
from .protocol import PROTOCOL_VERSION

TRACKER_DEFAULT = {"hsv_lower": [25, 90, 90], "hsv_upper": [45, 255, 255], "min_radius_px": 3,
                   "min_circle_fill": 0.5,
                   "note": "estimate for optic-yellow tennis balls indoors; tune with --tune-hsv"}


def camera_default(fps: float) -> dict:
    w, h, fov = 640, 480, 60.0
    f = (w / 2) / math.tan(math.radians(fov / 2))
    return {"placeholder": True,
            "note": "PLACEHOLDER: 60 deg FOV guess, camera 0.3 m behind the arm base at 0.5 m height "
                    "looking along +x at the thrower. Run --calibrate and measure the pose.",
            "index": 0, "width": w, "height": h, "fps": fps, "fx": f, "fy": f, "cx": w / 2, "cy": h / 2,
            "dist": [0, 0, 0, 0, 0],
            "R_arm_from_cam": [[0, 0, 1], [-1, 0, 0], [0, -1, 0]],
            "t_arm_from_cam": [-0.3, 0.0, 0.5], "frame_latency_s": 0.01}


def _mass_props_raw(project: Project, variant: str, params: dict) -> dict | None:
    """design/<v>/mass_props.json (for its motor mapping) unless it was built from other params."""
    f = project.variant_dir(variant) / "mass_props.json"
    if not f.exists():
        return None
    try:
        mp = json.loads(f.read_text())
    except (ValueError, OSError):
        return None
    if mp.get("params_hash") and params.get("style") == "belt_arm":
        try:
            from ..cad.belt_arm import params_hash
            if mp["params_hash"] != params_hash(params):
                return None                     # stale: the default mapping from params applies
        except Exception:  # noqa: BLE001 - CAD module unavailable: trust the file
            pass
    return mp


def control_gen(project: Project, variant: str, board: str | None = None, events: Events | None = None,
                command: str | None = None) -> dict:
    from ..arm_model import load_arm
    from ..project import check_variant_style
    check_variant_style(project, variant, "control gen")
    ev = events or Events(project.root, quiet=True)
    task = f"control-{variant}"
    hw = project.hardware()
    board = board or board_for_controller(hw.get("controller"))
    get_board(board)
    params = project.params(variant)
    ev.progress(task, f"deriving control numbers for {variant} on {board}")
    arm = load_arm(project, variant)
    cfg = derive(arm, params, hw, board, project.requirements(), _mass_props_raw(project, variant, params))
    cmd = command or f"mechy control gen {variant} --board {board}"
    cfg["generated_by"] = cmd

    out = project.path("control", variant)
    fw = out / "firmware" / "mechy_arm"
    host = out / "host"
    fw.mkdir(parents=True, exist_ok=True)
    host.mkdir(parents=True, exist_ok=True)
    written = []

    def put(path: Path, text: str):
        path.write_text(text)
        ev.file_written(path)
        written.append(path)

    put(fw / "mechy_arm.ino", firmware_source())
    put(fw / "config.h", render_config_h(cfg, cmd))
    host_cfg = dict(cfg)
    host_cfg["tracker"] = {**TRACKER_DEFAULT, **((params.get("control") or {}).get("tracker") or {})}
    host_cfg["camera_default"] = camera_default(cfg["vision"]["fps"])
    host_cfg["protocol_version"] = PROTOCOL_VERSION
    write_json(host / "host_config.json", host_cfg)
    ev.file_written(host / "host_config.json")
    written.append(host / "host_config.json")
    shutil.copyfile(TEMPLATES / "mechy_host.py", host / "mechy_host.py")
    ev.file_written(host / "mechy_host.py")
    written.append(host / "mechy_host.py")
    cam = host / "camera.json"
    if not cam.exists():          # never overwrite a calibration
        write_json(cam, host_cfg["camera_default"])
        ev.file_written(cam)
        written.append(cam)
    replays = sorted(p for p in project.path("sim").glob("*/replay.json"))
    put(out / "README.md", render_readme(cfg, replays, project))
    put(out / "summary.md", render_summary(cfg, variant))
    rel = [ev.rel(p) for p in written]
    m = cfg["motors"]
    return {"variant": variant, "board": board, "files": rel, "dir": f"control/{variant}",
            "summary": f"control/{variant}/summary.md",
            "steps_per_rad": [round(x["steps_per_rad"], 3) for x in m],
            "v_max_steps": [round(x["v_max_steps"], 1) for x in m],
            "a_max_steps": [round(x["a_max_steps"], 1) for x in m],
            "max_step_rate_hz": cfg["max_step_rate_hz"], "microsteps": cfg["microsteps"],
            "mapping_source": cfg["mapping_source"], "warnings": cfg["warnings"]}


# ------------------------------------------------------------------ README
def _deg(x):
    return f"{math.degrees(x):.1f}"


def home_cell(h: dict, i: int) -> str:
    """'max limit switch, q1 = 120.0 deg' or 'hall index, a2 = q1+q2 = 0.0 deg' (docgen parses this)."""
    what = "hall index" if h["kind"][i] == "index" else ("min" if h["dir"][i] < 0 else "max") + " limit switch"
    return f"{what}, {h['coord'][i]} = {_deg(h['pos_rad'][i])} deg"


def render_readme(cfg: dict, replays: list[Path], project: Project) -> str:
    v, b = cfg["variant"], cfg["board"]
    m = cfg["motors"]
    h = cfg["homing"]
    cur = cfg["current"]
    L: list[str] = []
    a = L.append
    a(f"# Control: {v} on {cfg['board_title']}")
    a("")
    a(f"Generated by `{cfg['generated_by']}`. Rebuild with the same command after changing "
      f"`design/{v}/params.yaml` or `hw/*.yaml`. Do not hand-edit `config.h`; calibration values go in "
      "params.yaml under `control:` (see Calibration).")
    a("")
    a("| What | Where |")
    a("|---|---|")
    a("| Firmware (Arduino sketch, no libraries) | `firmware/mechy_arm/mechy_arm.ino` |")
    a("| Generated pins and numbers | `firmware/mechy_arm/config.h` |")
    a("| Host: camera tracking, planning, serial | `host/mechy_host.py` |")
    a("| Host settings (generated) | `host/host_config.json` |")
    a("| Camera intrinsics and pose (yours, never overwritten) | `host/camera.json` |")
    a("")
    a("## Wiring")
    a("")
    a(f"Board: **{cfg['board_title']}**. One A4988 per joint, microstep jumpers "
      f"**{cfg['microstep_jumpers']}** on every driver ({cfg['microsteps']} microsteps, from hw/drivers.yaml).")
    a("")
    a("| Joint | Driver socket | STEP | DIR | EN | Motor drives | Homing switch pin | Switch at |")
    a("|---|---|---|---|---|---|---|---|")
    for i, mo in enumerate(m):
        a(f"| {i} {mo['name']} | {mo['socket']} | D{mo['step_pin']} | D{mo['dir_pin']} | D{mo['enable_pin']} | "
          f"{mo['drives']} | {mo['switch_label']} | {home_cell(h, i)} |")
    notes = [mo["slot_note"] for mo in m if mo.get("slot_note")]
    for n in notes:
        a(f"\n- {n[0].upper() + n[1:]}.")
    a("")
    a("- **Switches**: " + ("normally-open microswitches between the signal pin and GND; the firmware "
                            "enables the internal pull-up and reads LOW = pressed."
                            if h["switch_active_low"] else
                            "switches drive the pin HIGH when pressed (external pull-down needed)."))
    a("  Hall sensors (A3144, open collector) wire the same way: signal to the pin, GND, and +5 V to VCC; "
      "the magnet's south face toward the sensor's marked face.")
    a(f"  Homing source: {h['source']}. A limit switch closes at the angle in the table; an index (hall) "
      "sensor is centred on it (the firmware finds both edges of its window and takes the middle). "
      + "".join(f"`{c}` is motor {c[1]}'s angle, not a joint angle. " for c in h["coord"] if c.startswith("a"))
      + f"Optional e-stop: a normally-open button to GND on {cfg['estop_label']}; pressing it halts all motors "
      "and the firmware refuses moves until reset.")
    a("- **Motor coils**: A4988 pins 1A/1B to one coil, 2A/2B to the other (check coil pairs with a "
      "multimeter: ~1-3 ohm within a pair). A reversed motor is fixed in software (`dir_invert`), "
      "not by swapping wires.")
    a("- **Power**: 12-24 V DC into the shield's motor supply terminal (VMOT), sized for 4 x "
      f"{cur['set_a']:.1f} A peaks: a 12 V 5 A or 24 V 3 A supply. 24 V gives more torque at speed "
      "(the torque curve in hw/motors.yaml assumes 12 V). Put a 100 uF electrolytic across VMOT on "
      "each driver if the board lacks one. Never connect or disconnect a motor while VMOT is on: it "
      "destroys the A4988. The Arduino is powered from USB; grounds are shared through the shield.")
    a("")
    a("### Driver current (Vref)")
    a("")
    a("A4988 current limit: I = Vref / (8 x Rs), so **Vref = I x 8 x Rs**. Read Rs off the two "
      "resistors next to the chip (R050 = 0.050 ohm, R068 = 0.068, R100 = 0.100).")
    a("")
    rated = (f"{cur['motor_rated_a']:.2f} A (from hw/motors.yaml rated_current_a)" if cur["rated_known"] else
             f"{cur['motor_rated_a']:.2f} A (**estimate**: typical NEMA 17; add `rated_current_a` to "
             "hw/motors.yaml from your motor's datasheet)")
    a(f"Motor rated current: {rated}. Set limit: **{cur['set_a']:.2f} A** per phase "
      f"(rated, capped at 1.5 A: the A4988 needs a heat sink and a fan above ~{cur['uncooled_a']:.0f} A).")
    a("")
    a("| Rs (ohm) | Vref (V) |")
    a("|---|---|")
    for rs, vref in cur["vref_by_rs"].items():
        a(f"| {rs} | {vref:.3f} |")
    a("")
    a("Measure Vref between the trim pot's metal top and GND with VMOT on and the motor connected; turn "
      "with a ceramic screwdriver. Less current than rated lowers torque roughly in proportion; the "
      "speed and acceleration caps below assume the motor delivers its datasheet torque.")
    a("")
    a("## Numbers in config.h")
    a("")
    a("| Joint | Pulley | Steps/rev (motor) | Steps/rad | V max (steps/s) | A max (steps/s^2) | "
      "90 deg move, firmware | 90 deg, mechy_core |")
    a("|---|---|---|---|---|---|---|---|")
    for mo in m:
        a(f"| {mo['name']} | 20T -> {mo['pulley_teeth']}T ({mo['gear_ratio']:g}:1) | {mo['steps_per_rev_motor']:.0f} | "
          f"{mo['steps_per_rad']:.2f} | {mo['v_max_steps']:.0f} | {mo['a_max_steps']:.0f} | "
          f"{mo['t90_firmware_s']:.3f} s | {mo['t90_core_s']:.3f} s |")
    a("")
    a(f"Speed/acceleration caps are computed, not measured: torque curve from hw/motors.yaml x safety "
      f"{cfg['safety']}, minus the worst-case static gravity torque on that motor, accelerating the rotor plus "
      f"the worst-case load inertia ({cfg['load_source']}). The step rate is capped at {cfg['max_step_rate_hz']:.0f} steps/s per motor "
      "(hw/drivers.yaml). The firmware uses a constant acceleration that is safe at its top speed, so it is a "
      "little slower than mechy_core's varying-acceleration plan (last two columns).")
    a("")
    a(f"Joint->motor mapping ({cfg['mapping_source']}): motor angle = M x joint angles, M = "
      f"`{cfg['mapping']}`." + (" The elbow motor sets the forearm's absolute pitch and the wrist motor the "
                                "cup's, so moving the shoulder alone also turns the elbow and wrist motors."
                                if cfg["mapping"][3][1] else ""))
    a("")
    a(f"Step-rate ceiling: the firmware steps from a {cfg['tick_hz']} Hz timer interrupt, one step per motor per "
      "tick at most. On a 16 MHz AVR (Uno or Mega) the realistic ceiling with all four motors stepping is about "
      "8-10 k steps/s per motor (~50 us jitter). 16 microsteps at 10 rev/s would need 32 k steps/s: not "
      "possible, which is why hw/drivers.yaml uses few microsteps.")
    a("")
    a("## Flashing")
    a("")
    a("Arduino IDE: open `firmware/mechy_arm/mechy_arm.ino` (config.h opens as a second tab), pick "
      f"the board ({cfg['fqbn']}) and port, Upload. Or with arduino-cli:")
    a("")
    a("```bash")
    a("arduino-cli core install arduino:avr")
    a(f"arduino-cli compile --fqbn {cfg['fqbn']} firmware/mechy_arm")
    a(f"arduino-cli upload -p /dev/ttyACM0 --fqbn {cfg['fqbn']} firmware/mechy_arm   # COMx on Windows")
    a("```")
    a("")
    a(f"Then open a serial monitor at {cfg['serial_baud']} baud, newline line endings. The board prints "
      f"`MECHY READY variant={v} board={b} proto={PROTOCOL_VERSION}`.")
    a("")
    a("## Serial protocol")
    a("")
    a("| Command | Reply | Does |")
    a("|---|---|---|")
    a("| `HOME` | `OK HOME`, later `DONE HOME` or `ERR HOME_FAIL joint=j` | home "
      + " -> ".join(h["order_names"]) + ", then go to the ready pose |")
    a("| `MOVE q0 q1 q2 q3 t` | `OK MOVE T=<s> stretched=0/1`, later `DONE MOVE` | joint angles in rad "
      "(mechy_core convention), arrive in t s; stretched=1 means t was too short and T is what it takes |")
    a("| `STOP` | `OK STOP` | stop now (no ramp; at speed the motors may skip: re-home) |")
    a("| `STATUS` | `STATUS state=.. homed=.. q=.. steps=.. sw=..` | joint angles, motor steps, switches |")
    a("| `SETPOS q0 q1 q2 q3` | `OK SETPOS` | declare the current pose (bench tests without switches) |")
    a("| `ENABLE 0/1` | `OK ENABLE` | release / energise the motors (0 also clears homed) |")
    a("| `PING` | `OK PONG` | |")
    a("")
    a("Errors: `ERR CHECKSUM|PARSE|UNKNOWN|BUSY|NOT_HOMED|LIMIT joint=j|HOME_FAIL joint=j|ESTOP`. "
      "The host appends `*HH` (XOR checksum); lines typed without it are accepted. A MOVE is refused "
      "while another move or homing runs (no blending yet).")
    a("")
    a("## Calibration (in this order, motors unloaded first if you can)")
    a("")
    a("1. **Vref** on every driver (table above), VMOT on, before connecting the arm's belts.")
    a("2. **Direction**: `SETPOS 0 0 0 0` then `MOVE 0.2 0 0 0 2` and check the base turns "
      "counter-clockwise seen from above (+yaw). For each pitch joint, a positive move must raise the link. "
      "With belt pass-through, test the elbow with `MOVE 0 0 0.2 0 2` (only the forearm should rise). "
      "If a joint turns the wrong way set `control: {dir_invert: {<joint>: true}}` in params.yaml and regenerate.")
    a("3. **Steps per rad**: command a 90 degree move (1.5708 rad) and measure the angle with a protractor or "
      "phone inclinometer. A different angle means the pulley teeth or microstep jumpers do not match "
      "params.yaml / hw/drivers.yaml; fix those files, not config.h.")
    a("4. **Switches**: `STATUS` shows `sw=` bits (base, shoulder, elbow, wrist); press each switch by hand "
      "and check the right bit flips to 1.")
    a("5. **Homing**: `HOME` homes " + " -> ".join(h["order_names"]) + ". Keep a hand on the power switch the "
      "first time. A limit switch is approached at the fast speed, then crossed slowly. An index sensor in "
      "mid-range is found with bounded sweeps: first toward the side of the sensor with the smaller range (or "
      "straight toward it when the firmware was homed before), then back across the whole range; nothing found "
      "gives `ERR HOME_FAIL joint=j`. Then measure each joint's real angle at its sensor (in the coordinate in "
      "the wiring table) and put it in params.yaml `control: {home_pos_deg: {shoulder: 118.5, ...}}`. "
      "Other knobs: `home_side` (approach direction), `home_kind` (limit | index), `homing_order`, "
      "`home_speed_dps`, `home_backoff_deg`, `home_window_deg`, `home_margin_deg`, `soft_margin_deg`.")
    a("6. **Speed**: run `MOVE` between two poses with t = 0.3 s and increase until a motor skips "
      "(re-home after each skip and compare `STATUS`). Lower `max_step_rate_hz` in hw/drivers.yaml or the "
      "torque curve in hw/motors.yaml if the computed caps are too optimistic.")
    a("7. **Camera**: `python host/mechy_host.py --calibrate` with a printed 9x6 chessboard (25 mm squares) "
      "for the intrinsics; then measure the camera position and orientation relative to the arm base and edit "
      "`R_arm_from_cam` / `t_arm_from_cam` in host/camera.json (the default is a placeholder). Check by "
      "holding the ball at a measured point.")
    a("8. **Ball colour**: `python host/mechy_host.py --tune-hsv`, copy the printed HSV range into params.yaml "
      "`control: {tracker: {hsv_lower: [...], hsv_upper: [...]}}` and regenerate.")
    a("")
    a("## Host")
    a("")
    a("```bash")
    if replays:
        rp = replays[0].relative_to(project.root)
        a(f"python host/mechy_host.py --dry-run ../../{rp}    # replay sim throws, no hardware")
    else:
        a("python host/mechy_host.py --dry-run ../../sim/<task>/replay.json   # after `mechy sim catch`")
    a("python host/mechy_host.py --port /dev/ttyACM0 --show   # live")
    a("```")
    a("")
    a("Needs `pip install -e <repo>/engine` (mechy.core), and for live use `pip install opencv-python pyserial`. "
      "Depth comes from one camera and the ball's known diameter: its error grows with distance "
      "(dZ = 2 Z^2 / (fx D) per pixel of radius: ~5 cm at 1 m and ~21 cm at 2 m with the placeholder 640 px "
      "camera; the fit over many frames averages some of it out). Use a higher resolution or stereo if the "
      "dry run / real catches show depth errors. Stereo is a placeholder class.")
    a("")
    a("## Not verified")
    a("")
    a("- Nothing here has run on real hardware yet. The firmware logic is tested on a PC with a mocked AVR "
      "(see engine tests); timing on the real Uno is estimated, not measured.")
    a("- Speed/acceleration caps rest on an approximate torque curve and estimated masses.")
    a("- Sensor positions come from the CAD (or the joint limits); measure them (Calibration 5). The hall "
      "window width and A3144 hysteresis are not modelled beyond a symmetric window.")
    a("- Camera model and HSV range are placeholders until calibrated.")
    return "\n".join(L) + "\n"


def render_summary(cfg: dict, variant: str) -> str:
    m = cfg["motors"]
    L = [f"# Control {variant} summary", "",
         "| What | Where |", "|---|---|",
         f"| Firmware | control/{variant}/firmware/mechy_arm/ (mechy_arm.ino, config.h) |",
         f"| Host | control/{variant}/host/mechy_host.py, host_config.json, camera.json |",
         f"| Wiring, flashing, calibration | control/{variant}/README.md |", "",
         f"Decision: {cfg['board_title']}, {cfg['microsteps']} microsteps, timer-interrupt synchronised "
         f"trapezoids (no libraries), line protocol with checksums; joint->motor mapping {cfg['mapping_source']}.",
         "",
         "Numbers (computed from params/hw): steps/rad "
         + ", ".join(f"{x['name']} {x['steps_per_rad']:.1f}" for x in m)
         + "; speed caps (steps/s) " + ", ".join(f"{x['v_max_steps']:.0f}" for x in m)
         + "; accel caps (steps/s^2) " + ", ".join(f"{x['a_max_steps']:.0f}" for x in m)
         + "; 90 deg move firmware vs core (s) "
         + ", ".join(f"{x['t90_firmware_s']:.2f}/{x['t90_core_s']:.2f}" for x in m) + ".",
         f"Step ceiling: {cfg['tick_hz']} Hz tick, ~8-10 k steps/s per motor realistic on a 16 MHz AVR; capped "
         f"at {cfg['max_step_rate_hz']:.0f}.", ""]
    if cfg["warnings"]:
        L += ["Warnings: " + "; ".join(cfg["warnings"]), ""]
    L += ["Not verified", "- No real hardware run; firmware tested on a PC mock only.",
          "- Torque curve, masses, switch positions, camera pose and HSV range are estimates/placeholders.",
          "- No re-planning during a move (MOVE while moving is refused); STOP has no ramp.", "",
          "Open decisions",
          "- Confirm the controller board (hw/drivers.yaml says arduino-uno, unconfirmed) and motor rated current.",
          "- Single camera + ball diameter depth vs stereo.", ""]
    return "\n".join(L)
