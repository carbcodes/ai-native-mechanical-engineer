"""Controls generator: config.h numbers, protocol, firmware profile, host dry run, firmware on a PC mock."""

import asyncio
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from conftest import mechy
from mechy.control import profile, protocol
from mechy.control.boards import BOARDS
from mechy.control.generate import control_gen
from mechy.control.mapping import PASS_THROUGH, default_mapping, motor_mapping, parse_mapping
from mechy.core import get_core
from mechy.project import init_project, load_yaml

TESTING = Path(__file__).resolve().parents[1] / "mechy" / "control" / "testing"


# ------------------------------------------------------------------ helpers
@pytest.fixture(scope="module")
def gen(tmp_path_factory):
    """One generated project (uno_cnc) shared by the tests in this module."""
    root = tmp_path_factory.mktemp("control") / "proj"
    proj = init_project(root, example="tennis-catcher", git=False)
    res = control_gen(proj, "v1", board="uno_cnc")
    return proj, res


def c_array(text: str, name: str) -> np.ndarray:
    m = re.search(rf"static const \w+ {name}\[[^\]]*\](?:\[4\])? = (\{{.*?\}});", text, re.S)
    assert m, f"{name} not in config.h"
    nums = re.findall(r"-?\d+(?:\.\d*)?(?:e[-+]?\d+)?", m.group(1))
    return np.array([float(x) for x in nums])


def c_define(text: str, name: str) -> str:
    m = re.search(rf"^#define {name} (\S+)", text, re.M)
    assert m, f"#define {name} missing"
    return m.group(1)


def host_module(proj, variant="v1"):
    path = proj.path("control", variant, "host", "mechy_host.py")
    spec = importlib.util.spec_from_file_location(f"mechy_host_{variant}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def strip_c(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    src = re.sub(r'"(?:\\.|[^"\\])*"', '""', src)
    return re.sub(r"'(?:\\.|[^'\\])'", "''", src)


def synthetic_replay(proj, n=12, seed=3) -> dict:
    """Throws like the sim's (requirements throw: section), flight only, contracts 11 format."""
    mc = get_core()
    req = proj.requirements()
    c, t = req["catch"], req["throw"]
    rng = np.random.default_rng(seed)
    throws = []
    for i in range(n):
        az = rng.uniform(-0.15, 0.15)
        d = c["throw_distance_m"] + rng.normal(0, 0.08)
        p0 = np.array([d * math.cos(az), d * math.sin(az), t["launch_height_m"] + rng.normal(0, 0.05)])
        aim = np.asarray(t["aim_center_m"]) + rng.normal(0, 1, 3) * np.asarray(t["aim_spread_m"]) * 0.6
        aim[2] = max(aim[2], 0.15)
        T = rng.uniform(*t["flight_time_s"])
        v0 = (aim - p0) / T + np.array([0, 0, 0.5 * 9.81 * T])
        for _ in range(3):
            tr = mc.ball_predict(p0, v0, dt=0.002, t_max=T, mass=c["ball_mass_kg"], diameter=c["ball_diameter_m"])
            v0 = v0 + (aim - tr[-1, 1:]) / T
        tr = mc.ball_predict(p0, v0, dt=0.01, t_max=T + 0.1, mass=c["ball_mass_kg"], diameter=c["ball_diameter_m"])
        throws.append({"id": i, "outcome": "caught", "t": tr[:, 0].tolist(), "q": [[0, 0, 0, 0]] * len(tr),
                       "ball": tr[:, 1:].tolist(), "predicted": tr[:, 1:].tolist(), "catch_point": aim.tolist()})
    return {"variant": "v1", "dt": 0.01, "joint_names": ["base", "shoulder", "elbow", "wrist"], "throws": throws}


# ------------------------------------------------------------------ config.h numbers
def test_config_h_matches_params(gen):
    proj, res = gen
    params = proj.params("v1")
    drv = load_yaml(proj.path("hw", "drivers.yaml"))["drivers"][0]
    h = proj.path("control", "v1", "firmware", "mechy_arm", "config.h").read_text()
    ms = drv["microsteps"]
    expect = [200 * ms * round(20 * j["gear_ratio"]) / 20 / (2 * math.pi) for j in params["joints"]]
    assert np.allclose(c_array(h, "STEPS_PER_RAD"), expect, rtol=1e-6)
    assert np.allclose(res["steps_per_rad"], expect, rtol=1e-4)
    assert expect[0] == pytest.approx(800 * 4.5 / (2 * math.pi))          # 4 usteps, 20T -> 90T
    lim = np.radians([j["limit_deg"] for j in params["joints"]])
    m = math.radians(2.0)
    assert np.allclose(c_array(h, "Q_MIN"), lim[:, 0] + m, atol=1e-6)
    assert np.allclose(c_array(h, "Q_MAX"), lim[:, 1] - m, atol=1e-6)
    # belt_arm: pass-through mapping, inverse consistent
    M = c_array(h, "MAP_M").reshape(4, 4)
    Minv = c_array(h, "MAP_MINV").reshape(4, 4)
    assert np.allclose(M, PASS_THROUGH) and np.allclose(M @ Minv, np.eye(4), atol=1e-6)
    # caps never exceed the driver step-rate cap; all positive
    v = c_array(h, "V_MAX_STEPS")
    a = c_array(h, "A_MAX_STEPS")
    assert np.all(v > 0) and np.all(v <= drv["max_step_rate_hz"] + 1e-6) and np.all(a > 0)
    assert c_define(h, "MICROSTEPS") == str(ms)
    assert c_define(h, "MAX_STEP_RATE_HZ") == str(drv["max_step_rate_hz"])
    # homing: every joint once; belt_arm sensors as the CAD draws them (no mass_props here):
    # base hall at q0 = 0, shoulder switch at its upper limit, elbow hall at a2 = q1+q2 = 0, wrist at lower
    order = c_array(h, "HOME_ORDER").astype(int)
    assert sorted(order) == [0, 1, 2, 3]
    assert list(order).index(1) < list(order).index(2)          # elbow index needs the shoulder homed
    hdir = c_array(h, "HOME_DIR")
    hpos = c_array(h, "HOME_POS")
    assert list(c_array(h, "HOME_KIND").astype(int)) == [1, 0, 1, 0]
    assert list(c_array(h, "HOME_COORD").astype(int)) == [255, 255, 2, 255]
    assert np.allclose(hpos, [0, lim[1, 1], 0, lim[3, 0]], atol=1e-6)
    assert hdir[1] == 1 and hdir[3] == -1
    ready = c_array(h, "READY_POSE")
    assert np.all(ready >= c_array(h, "Q_MIN")) and np.all(ready <= c_array(h, "Q_MAX"))


def test_caps_follow_core_motor_model(gen):
    """Firmware caps come from the same torque model as mechy_core: its 90-degree move is never
    faster than mechy_core's optimum, and within 35% of it."""
    proj, _ = gen
    cfg = json.loads(proj.path("control", "v1", "host", "host_config.json").read_text())
    for mo in cfg["motors"]:
        assert mo["t90_firmware_s"] >= mo["t90_core_s"] * 0.999
        assert mo["t90_firmware_s"] <= mo["t90_core_s"] * 1.35
        # constant acceleration is torque-feasible at the top speed (safety 0.7, gravity included)
        spec = cfg["motor_specs"][cfg["joint_names"].index(mo["name"])]
        rps = mo["v_max_motor_rps"]
        T = 0.7 * float(np.interp(rps, *np.asarray(spec["torque_curve"]).T)) - mo["gravity_torque_nm"] / mo["gear_ratio"]
        J = spec["rotor_inertia_kgm2"] + mo["load_inertia_kgm2"] / mo["gear_ratio"] ** 2
        assert mo["a_max_motor_rad_s2"] * J <= T * (1 + 1e-6)


def test_mapping_default_and_override():
    belt = {"style": "belt_arm", "joints": [{"name": n} for n in ("base", "shoulder", "elbow", "wrist")]}
    simple = {**belt, "style": "simple"}
    assert np.allclose(default_mapping(belt), PASS_THROUGH)
    assert np.allclose(default_mapping(simple), np.eye(4))
    M, src = motor_mapping(belt, {"motor_mapping": {"elbow": ["shoulder", "elbow"]}})
    assert "mass_props" in src and np.allclose(M[2], [0, 1, 1, 0]) and np.allclose(M[3], [0, 0, 0, 1])
    assert np.allclose(parse_mapping({"matrix": np.eye(4).tolist()}), np.eye(4))
    assert np.allclose(parse_mapping({"motors": {"wrist": {"shoulder": 1, "elbow": 1, "wrist": 1}}})[3], [0, 1, 1, 1])
    with pytest.raises(ValueError):
        parse_mapping([[1, 0, 0, 0]] * 4)            # singular
    # pass-through kinematics: holding the elbow/wrist motors keeps forearm and cup pitch fixed
    q = np.array([0.1, 0.5, -0.7, 0.3])
    th = PASS_THROUGH @ q
    q2 = np.linalg.solve(PASS_THROUGH, th + np.array([0, 0.2, 0, 0]))   # shoulder motor only
    assert q2[1] == pytest.approx(q[1] + 0.2) and q2[1] + q2[2] == pytest.approx(q[1] + q[2])
    assert q2[1] + q2[2] + q2[3] == pytest.approx(q.sum() - q[0])


def test_mapping_override_reaches_config(gen):
    from mechy.arm_model import load_arm
    from mechy.control.config import derive
    proj, _ = gen
    arm = load_arm(proj, "v1")
    cfg = derive(arm, proj.params("v1"), proj.hardware(), "mega_ramps", proj.requirements(),
                 {"motor_mapping": np.eye(4).tolist()})
    assert np.allclose(cfg["mapping"], np.eye(4)) and "mass_props" in cfg["mapping_source"]
    assert [m["socket"] for m in cfg["motors"]] == ["X", "Y", "Z", "E0"]


# ------------------------------------------------------------------ protocol
def test_protocol_round_trip():
    q = [0.12345, -1.5, 2.25, 0.0]
    line = protocol.encode_move(q, 0.4321)
    assert line.endswith(b"\n") and b"*" in line and len(line) <= protocol.MAX_LINE + 1
    cmd, args = protocol.decode_command(line)
    assert cmd == "MOVE" and np.allclose(args, [*q, 0.4321], atol=1e-5)
    for c, a in [("HOME", ()), ("STOP", ()), ("STATUS", ()), ("PING", ()), ("ENABLE", (1,)),
                 ("SETPOS", (0.1, 0.2, -0.3, 0.4))]:
        cmd, args = protocol.decode_command(protocol.encode(c, *a))
        assert cmd == c and np.allclose(args, a)
        assert protocol.decode_command(protocol.encode(c, *a, with_checksum=False))[0] == c
    bad = line.replace(b"0.4321", b"0.4322")
    with pytest.raises(protocol.ProtocolError, match="CHECKSUM"):
        protocol.decode_command(bad)
    with pytest.raises(protocol.ProtocolError):
        protocol.encode("MOVE", 1, 2)
    with pytest.raises(protocol.ProtocolError):
        protocol.encode_move(q, 0)
    # worst-case line length fits the firmware buffer
    assert len(protocol.encode_move([-2.61799, -2.61799, -2.61799, -2.61799], 12.34567)) <= protocol.MAX_LINE + 1
    r = protocol.parse_reply("OK MOVE T=0.4120 stretched=1")
    assert r["kind"] == "OK" and r["what"] == "MOVE" and r["T"] == pytest.approx(0.412) and r["stretched"] == 1
    st = protocol.parse_reply(protocol.encode_reply_status("IDLE", True, [0, 1.2, -1.3, 0.7], [0, 5, -6, 7], "0100"))
    assert st["kind"] == "STATUS" and st["homed"] == 1 and st["steps"] == [0, 5, -6, 7] and st["sw"] == "0100"
    assert np.allclose(st["q"], [0, 1.2, -1.3, 0.7])
    e = protocol.parse_reply("ERR LIMIT joint=2")
    assert e["kind"] == "ERR" and e["what"] == "LIMIT" and e["joint"] == 2


# ------------------------------------------------------------------ profile model
def test_profile_respects_caps_and_time():
    rng = np.random.default_rng(1)
    vmax = np.array([2500, 2000, 3300, 4000.0])
    amax = np.array([10000, 6700, 22000, 90000.0])
    for _ in range(300):
        D = rng.integers(-3000, 3000, 4) * (rng.random(4) < 0.85)
        T_req = float(rng.uniform(0.01, 2.0))
        pl = profile.plan(D, T_req, vmax, amax, 20000, 20)
        if not np.any(D):
            assert pl["T"] == 0
            continue
        assert pl["T"] >= T_req - 1e-9 or pl["T"] >= T_req - 1e-3     # rounded up to whole updates
        assert np.all(pl["peak_rate_hz"] <= vmax * (1 + 1e-4))
        assert np.all(pl["peak_acc"] <= amax * (1 + 1e-4))
        tmin = profile.min_duration(D, vmax, amax)
        assert pl["T"] >= tmin - 1e-3
        if T_req > tmin + 0.01:
            assert not pl["stretched"] and pl["T"] - T_req < 0.0011
        assert np.allclose(profile.sample(pl, D, pl["T"]), D) and np.allclose(profile.sample(pl, D, 0), 0)


# ------------------------------------------------------------------ generated files
def test_generated_files_and_ino_structure(gen):
    proj, res = gen
    d = proj.path("control", "v1")
    for f in ["firmware/mechy_arm/mechy_arm.ino", "firmware/mechy_arm/config.h", "host/mechy_host.py",
              "host/host_config.json", "host/camera.json", "README.md", "summary.md"]:
        assert (d / f).exists(), f
    ino = (d / "firmware/mechy_arm/mechy_arm.ino").read_text()
    h = (d / "firmware/mechy_arm/config.h").read_text()
    for src in (ino, h):
        s = strip_c(src)
        assert s.count("{") == s.count("}") and s.count("(") == s.count(")") and s.count("[") == s.count("]")
    for i in range(4):
        for k in ("STEP{}_PIN", "STEP{}_PORT", "STEP{}_BIT", "DIR{}_PIN", "EN{}_PIN", "SWITCH{}_PIN"):
            c_define(h, k.format(i))
    for name in ("TICK_HZ", "TICKS_PER_UPDATE", "STEP_PULSE_US", "N_ENABLE_PINS", "ESTOP_PIN", "SWITCH_ACTIVE_LOW",
                 "HOME_FAST", "HOME_SLOW", "HOME_BACKOFF", "MECHY_VARIANT", "MECHY_BOARD", "PROTOCOL_VERSION"):
        c_define(h, name)
    # every config identifier the sketch uses is defined in config.h
    defined = set(re.findall(r"#define (\w+)", h)) | set(re.findall(r"static const \w+ (\w+)\[", h))
    used = set(re.findall(r"\b([A-Z][A-Z0-9_]{2,})\b", strip_c(ino)))
    local = set(re.findall(r"#define (\w+)", ino)) | set(re.findall(r"static const \w+ (\w+)\[", ino)) | {"NULL", "ST_IDLE", "ST_MOVING", "ST_HOMING", "ST_ESTOP", "H_SEEK1", "H_SEEK2", "H_CLEAR", "H_EXIT",
                                                       "H_BACKOFF", "H_SLOW", "H_READY", "STATE_NAMES"}
    avr = {"ISR", "TIMER1_COMPA_vect", "SREG", "TCCR1A", "TCCR1B", "TCNT1", "OCR1A", "TIMSK1", "TIFR1", "OCF1A",
           "WGM12", "CS10", "OCIE1A", "HIGH", "LOW", "OUTPUT", "INPUT", "INPUT_PULLUP", "F_CPU", "PORTD", "PORTB"}
    assert used - defined - local - avr == set()
    readme = (d / "README.md").read_text()
    assert "Vref" in readme and "D12" in readme and "arduino-cli compile" in readme and "Not verified" in readme
    assert "8-10 k steps/s" in readme and "8-10 k steps/s" in ino      # Uno step ceiling stated
    assert (d / "summary.md").read_text().startswith("# Control v1 summary")


def test_camera_json_not_overwritten(gen):
    proj, _ = gen
    cam = proj.path("control", "v1", "host", "camera.json")
    d = json.loads(cam.read_text())
    d["fx"] = 1234.5
    cam.write_text(json.dumps(d))
    control_gen(proj, "v1", board="uno_cnc")
    assert json.loads(cam.read_text())["fx"] == 1234.5


# ------------------------------------------------------------------ host
def test_host_camera_model_round_trip(gen):
    proj, _ = gen
    host = host_module(proj)
    cfg = host.load_config(proj.path("control", "v1", "host", "host_config.json"))
    cam = host.MonoCamera(cfg["camera_default"], cfg["catch"]["ball_diameter_m"])
    for p in ([1.5, 0.1, 0.8], [0.6, -0.2, 0.4], [2.0, 0.3, 1.1]):
        u, v, r = cam.arm_to_pixel(p)
        assert np.allclose(cam.pixel_to_arm(u, v, r), p, atol=1e-9)
    with pytest.raises(NotImplementedError):
        host.StereoCamera()


def test_host_dry_run_moves_within_limits_and_caps(gen):
    proj, _ = gen
    sys.modules.pop("cv2", None)
    host = host_module(proj)
    cfg = host.load_config(proj.path("control", "v1", "host", "host_config.json"))
    replay = synthetic_replay(proj)
    out = host.run_dry(cfg, replay, seed=0, verbose=False)
    assert "cv2" not in sys.modules and "serial" not in sys.modules     # heavy imports stay lazy
    assert out["throws"] == len(replay["throws"])
    assert out["planned"] >= 0.6 * out["throws"], [r["reason"] for r in out["rows"]]
    soft = np.asarray(cfg["soft_limits_rad"])
    M = np.asarray(cfg["mapping"])
    spr = np.array([m["steps_per_rad"] for m in cfg["motors"]])
    vmax = np.array([m["v_max_steps"] for m in cfg["motors"]])
    amax = np.array([m["a_max_steps"] for m in cfg["motors"]])
    q_prev = np.asarray(cfg["ready_pose_rad"])
    n_moves = 0
    for line in out["commands"]:
        cmd, a = protocol.decode_command(line)
        if cmd != "MOVE":
            continue
        q = np.asarray(a[:4])
        assert np.all(q >= soft[:, 0] - 1e-6) and np.all(q <= soft[:, 1] + 1e-6), line
        D = np.round(spr * (M @ q)) - np.round(spr * (M @ q_prev))
        pl = profile.plan(D, a[4], vmax, amax, cfg["tick_hz"], cfg["ticks_per_update"])
        assert np.all(pl["peak_rate_hz"] <= cfg["max_step_rate_hz"] * (1 + 1e-4))
        assert np.all(pl["peak_rate_hz"] <= vmax * (1 + 1e-4)) and np.all(pl["peak_acc"] <= amax * (1 + 1e-4))
        q_prev = q
        n_moves += 1
    assert n_moves == 2 * out["planned"]            # catch move + return to ready per planned throw
    for r in out["rows"]:
        if r["planned"]:
            assert r["stretched"] == 0 and r["reply_T"] <= r["T_move"] + 1e-3   # arrives in time
            assert r["cup_to_ball_m"] < 0.05, r     # cup centre within 5 cm of the true ball
    assert out["mean_cup_to_ball_m"] < 0.03


def test_host_cli_dry_run(gen, tmp_path):
    proj, _ = gen
    rp = tmp_path / "replay.json"
    rp.write_text(json.dumps(synthetic_replay(proj, n=3)))
    host = proj.path("control", "v1", "host", "mechy_host.py")
    r = subprocess.run([sys.executable, str(host), "--dry-run", str(rp), "--log", str(tmp_path / "log.jsonl")],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    res = json.loads(r.stdout)
    assert res["throws"] == 3 and len((tmp_path / "log.jsonl").read_text().splitlines()) == 3


# ------------------------------------------------------------------ firmware on a PC (mocked AVR)
def _harness(gen_dir: Path, out: Path) -> Path:
    exe = out / "harness"
    r = subprocess.run(["g++", "-O2", "-Wall", "-Wextra", "-Werror", f"-I{TESTING / 'arduino_mock'}", f"-I{gen_dir}",
                        str(TESTING / "harness.cpp"), "-o", str(exe)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return exe


def _run(exe: Path, script: list[str], t_end: float, q0, tmp: Path, env: dict | None = None) -> tuple[list, dict]:
    import os
    sp = tmp / "script.txt"
    sp.write_text("\n".join(script) + "\n")
    r = subprocess.run([str(exe), str(sp), str(t_end), *map(str, q0)], capture_output=True, text=True, timeout=180,
                       env={**os.environ, **(env or {})})
    assert r.returncode == 0, r.stderr
    lines, res = [], {}
    for l in r.stdout.splitlines():
        if l.startswith("RESULT"):
            k, *v = l.split()[1:]
            res[k] = [float(x) for x in v]
        else:
            t, msg = l.split(" ", 1)
            lines.append((float(t), msg))
    return lines, res


needs_gpp = pytest.mark.skipif(shutil.which("g++") is None, reason="g++ not installed")


@needs_gpp
@pytest.mark.parametrize("board", ["uno_cnc", "mega_ramps"])
def test_firmware_homing_and_moves_on_mock(gen, tmp_path, board):
    proj, _ = gen
    if board != "uno_cnc":
        control_gen(proj, "v1", board=board)
    fw = proj.path("control", "v1", "firmware", "mechy_arm")
    cfg = json.loads(proj.path("control", "v1", "host", "host_config.json").read_text())
    try:
        exe = _harness(fw, tmp_path)
    finally:
        if board != "uno_cnc":
            control_gen(proj, "v1", board="uno_cnc")
    ready = np.asarray(cfg["ready_pose_rad"])
    target = [0.5, 0.6, -0.8, 0.9]
    script = ["0.01 PING", "0.02 MOVE 0 1 0 0 1", "0.03 HOME"]
    lines, res = _run(exe, script, 90, [0.3, 0.9, -0.5, 0.2], tmp_path)
    msgs = [m for _, m in lines]
    assert msgs[0].startswith(f"MECHY READY variant=v1 board={board}")
    assert "OK PONG" in msgs and "ERR NOT_HOMED" in msgs and "OK HOME" in msgs and "DONE HOME" in msgs, msgs
    spr = np.array([m["steps_per_rad"] for m in cfg["motors"]])
    step_rad = 1.0 / spr.min()
    assert np.allclose(res["q_true"], ready, atol=2.5 * step_rad), (res["q_true"], ready)   # found the switches
    assert res["pos"] == res["phys"]                    # firmware's step count = pulses on the pins

    # timed moves from a declared pose
    M = np.asarray(cfg["mapping"])
    vmax = np.array([m["v_max_steps"] for m in cfg["motors"]])
    amax = np.array([m["a_max_steps"] for m in cfg["motors"]])
    D = np.round(spr * (M @ target)) - np.round(spr * (M @ ready))
    pl_fast = profile.plan(D, 0.2, vmax, amax, cfg["tick_hz"], cfg["ticks_per_update"])
    pl_slow = profile.plan(-D, 1.5, vmax, amax, cfg["tick_hz"], cfg["ticks_per_update"])
    setpos = protocol.encode("SETPOS", *ready).decode().strip()
    script = [f"0.01 {setpos}", "0.02 " + protocol.encode_move(target, 0.2).decode().strip(), "0.03 STATUS",
              "1.50 " + protocol.encode_move(ready, 1.5).decode().strip(),
              "3.50 MOVE 0 3 0 0 1", "3.60 MOVE 0 1 0 0 1*00", "3.70 FOO", "3.80 " + protocol.encode_move(target, 2).decode().strip(),
              "4.20 STOP", "4.30 STATUS"]
    lines, res = _run(exe, script, 5, ready, tmp_path)
    ok = [(t, m) for t, m in lines if m.startswith("OK MOVE")]
    done = [t for t, m in lines if m == "DONE MOVE"]
    T1 = float(re.search(r"T=([\d.]+)", ok[0][1]).group(1))
    assert "stretched=1" in ok[0][1] and T1 == pytest.approx(pl_fast["T"], abs=2e-3)   # python model = firmware
    assert done[0] - 0.02 == pytest.approx(T1, abs=0.01)                                # arrives on time
    T2 = float(re.search(r"T=([\d.]+)", ok[1][1]).group(1))
    assert "stretched=0" in ok[1][1] and T2 == pytest.approx(pl_slow["T"], abs=2e-3) == pytest.approx(1.5, abs=2e-3)
    assert done[1] - 1.50 == pytest.approx(1.5, abs=0.01)
    msgs = [m for _, m in lines]
    assert any(m.startswith("STATUS state=MOVING") for m in msgs)
    assert "ERR LIMIT joint=1" in msgs and "ERR CHECKSUM" in msgs and "ERR UNKNOWN FOO" in msgs and "OK STOP" in msgs
    assert len(done) == 2                                                               # the stopped move never finishes
    for i in range(4):
        assert res[f"rate{i}"][0] <= vmax[i] * 1.06 + 400                               # 5 ms windows, 1-step jitter


@needs_gpp
@pytest.mark.parametrize("q0", [
    [-2.4, -0.1, 2.0, -1.4],      # base far below its index, forearm far above level, wrist near its switch
    [2.4, 2.0, 0.3, 1.4],         # base far above, shoulder near its switch, forearm just above level
    [0.04, 0.5, -2.2, 0.0],       # base starting inside its index window; elbow beyond a2 = 0 on the low side
])
def test_firmware_index_homing_from_both_sides(gen, tmp_path, q0):
    """Mid-range hall indexes (base q0 = 0, elbow a2 = q1+q2 = 0) are found from either side with
    bounded sweeps; every joint ends where config.h says its sensor is, then at the ready pose."""
    proj, _ = gen
    cfg = json.loads(proj.path("control", "v1", "host", "host_config.json").read_text())
    exe = _harness(proj.path("control", "v1", "firmware", "mechy_arm"), tmp_path)
    lines, res = _run(exe, ["0.01 HOME", "120 STATUS"], 120.5, q0, tmp_path)
    msgs = [m for _, m in lines]
    assert "DONE HOME" in msgs, msgs
    step_rad = 1.0 / min(m["steps_per_rad"] for m in cfg["motors"])
    assert np.allclose(res["q_true"], cfg["ready_pose_rad"], atol=2.5 * step_rad), (res["q_true"], q0)
    # firmware's own estimate agrees with the truth
    st = protocol.parse_reply(next(m for m in msgs if m.startswith("STATUS")))
    assert np.allclose(st["q"], res["q_true"], atol=2.5 * step_rad + 1e-4)
    # a re-home uses the position estimate: the index joints go straight to their sensors, so from the
    # ready pose it takes the same ~30 s whatever the first start was (first homes here: 28-67 s)
    t_first = next(t for t, m in lines if m == "DONE HOME")
    lines2, res2 = _run(exe, ["0.01 HOME", "200 HOME"], 200 + t_first + 60, q0, tmp_path)
    done = [t for t, m in lines2 if m == "DONE HOME"]
    assert len(done) == 2 and done[1] - 200 < 33.0, (done, t_first)
    assert np.allclose(res2["q_true"], cfg["ready_pose_rad"], atol=2.5 * step_rad)


@needs_gpp
def test_firmware_homing_fails_bounded_without_sensor(gen, tmp_path):
    """A dead elbow hall: the firmware sweeps a bounded distance both ways, then reports HOME_FAIL."""
    proj, _ = gen
    exe = _harness(proj.path("control", "v1", "firmware", "mechy_arm"), tmp_path)
    lines, res = _run(exe, ["0.01 HOME"], 120, [0.0, 1.0, -0.5, 0.0], tmp_path, env={"MOCK_DEAD_SENSOR": "2"})
    msgs = [m for _, m in lines]
    assert "ERR HOME_FAIL joint=2" in msgs and "DONE HOME" not in msgs, msgs
    t_fail = next(t for t, m in lines if m == "ERR HOME_FAIL joint=2")
    assert t_fail < 100
    # bounded: shoulder homed at its switch puts the elbow index at q2 = -q1; first sweep toward the
    # smaller side (+, s - Q_MIN + margin), then back by that + (Q_MAX - s) + margin, and stop
    h = proj.path("control", "v1", "firmware", "mechy_arm", "config.h").read_text()
    qmin, qmax = c_array(h, "Q_MIN")[2], c_array(h, "Q_MAX")[2]
    margin = float(c_define(h, "HOME_MARGIN").rstrip("f"))
    s = -res["q_true"][1]
    expect = -0.5 + (s - qmin + margin) - ((s - qmin + margin) + (qmax - s) + margin)
    assert res["q_true"][2] == pytest.approx(expect, abs=0.01)


def test_homing_reads_mass_props_table(gen):
    """control gen takes the sensor table from mass_props.json and applies params overrides."""
    from mechy.arm_model import load_arm
    from mechy.control.config import derive
    proj, _ = gen
    arm = load_arm(proj, "v1")
    mp = {"homing": [
        {"joint": "base", "sensor": "A3144 hall + 5x2 magnet", "homes": "q0 = 0", "home_deg": 5.0, "coordinate": "q0"},
        {"joint": "shoulder", "sensor": "KW12-3 microswitch", "homes": "", "home_deg": 118.0, "coordinate": "q1 = a1"},
        {"joint": "elbow", "sensor": "A3144 hall + 5x2 magnet", "homes": "", "home_deg": -10.0, "coordinate": "a2 = q1+q2"},
        {"joint": "wrist", "sensor": "KW12-3 microswitch", "homes": "", "home_deg": -88.0, "coordinate": "q3"}],
        "homing_order": ["shoulder", "elbow", "wrist", "base"]}
    params = proj.params("v1")
    h = derive(arm, params, proj.hardware(), "uno_cnc", proj.requirements(), mp)["homing"]
    assert h["kind"] == ["index", "limit", "index", "limit"] and h["coord_motor"] == [None, None, 2, None]
    assert np.allclose(np.degrees(h["pos_rad"]), [5, 118, -10, -88]) and h["dir"][1] == 1 and h["dir"][3] == -1
    assert "mass_props" in h["source"]
    params["control"] = {"home_pos_deg": {"shoulder": 117.0}, "home_side": {"base": "min"}}
    h = derive(arm, params, proj.hardware(), "uno_cnc", proj.requirements(), mp)["homing"]
    assert math.degrees(h["pos_rad"][1]) == pytest.approx(117.0) and h["dir"][0] == -1
    params["control"] = {"homing_order": ["elbow", "shoulder", "wrist", "base"]}
    with pytest.raises(ValueError, match="shoulder must home before"):
        derive(arm, params, proj.hardware(), "uno_cnc", proj.requirements(), mp)


@needs_gpp
def test_host_commands_drive_firmware_mock(gen, tmp_path):
    """End to end: the host's dry-run MOVE lines, fed to the real sketch on the PC mock, reach each
    catch pose (true joint angles) by the time the host planned for."""
    proj, _ = gen
    host = host_module(proj)
    cfg = host.load_config(proj.path("control", "v1", "host", "host_config.json"))
    out = host.run_dry(cfg, synthetic_replay(proj, n=4, seed=11), seed=0, verbose=False)
    moves = [r for r in out["rows"] if r["planned"]]
    assert moves
    exe = _harness(proj.path("control", "v1", "firmware", "mechy_arm"), tmp_path)
    ready = np.asarray(cfg["ready_pose_rad"])
    step_rad = 1.0 / min(m["steps_per_rad"] for m in cfg["motors"])
    for r in moves:
        script = ["0.01 " + protocol.encode("SETPOS", *ready).decode().strip(), f"0.02 {r['command']}"]
        lines, res = _run(exe, script, 0.02 + r["T_move"] + 0.2, ready, tmp_path)
        done = [t for t, m in lines if m == "DONE MOVE"]
        assert done and done[0] - 0.02 <= r["T_move"] + 0.002, lines
        assert np.allclose(res["q_true"], r["q"], atol=1.5 * step_rad + 1e-4), (res["q_true"], r["q"])


# ------------------------------------------------------------------ real AVR build (optional)
def test_avr_compile(gen, tmp_path):
    from mechy.control.testing import avr_build
    if avr_build.available() is None:
        pytest.skip("no arduino-cli with arduino:avr, and no avr-gcc + $MECHY_ARDUINO_CORE")
    proj, _ = gen
    for board in BOARDS:
        control_gen(proj, "v1", board=board)
        r = avr_build.compile_sketch(proj.path("control", "v1", "firmware", "mechy_arm"), BOARDS[board]["fqbn"],
                                     tmp_path / board)
        assert r["ok"], r["log"]
        assert r["flash"] < BOARDS[board]["flash_bytes"] and r["ram"] < 0.75 * BOARDS[board]["ram_bytes"], r
        assert not r.get("warnings"), r["warnings"]
    control_gen(proj, "v1", board="uno_cnc")


def test_isr_load_on_simavr(gen, tmp_path):
    """Real ATmega328P timing: step-interrupt CPU load idle and with all motors at their caps."""
    from mechy.control.testing import avr_build
    if avr_build.available() is None or shutil.which("simavr") is None:
        pytest.skip("needs an AVR build (arduino-cli or avr-gcc + $MECHY_ARDUINO_CORE) and simavr")
    proj, _ = gen
    fw = proj.path("control", "v1", "firmware", "mechy_arm")
    sk = tmp_path / "isr_load"
    sk.mkdir()
    shutil.copy(TESTING / "isr_load.ino", sk / "isr_load.ino")
    shutil.copy(fw / "mechy_arm.ino", sk / "mechy_arm_impl.h")
    shutil.copy(fw / "config.h", sk / "config.h")
    r = avr_build.compile_sketch(sk, "arduino:avr:uno", tmp_path / "out")
    assert r and r["ok"], r and r["log"]
    try:
        p = subprocess.run(["simavr", "-m", "atmega328p", "-f", "16000000", r["elf"]], capture_output=True,
                           text=True, timeout=150)
        out = p.stdout + p.stderr
    except subprocess.TimeoutExpired as e:      # simavr never exits on its own; the line is printed by then
        out = (e.stdout or b"").decode() + (e.stderr or b"").decode()
    m = re.search(r"SELFTEST base=(\d+) idle=(\d+) busy=(\d+) T=[\d.]+ rates=([-\d,]+)", out)
    assert m, out[-500:]
    base, idle, busy = (int(m.group(i)) for i in (1, 2, 3))
    rates = [int(x) for x in m.group(4).split(",")]
    cfg = json.loads(proj.path("control", "v1", "host", "host_config.json").read_text())
    assert 1 - idle / base < 0.02                   # interrupt is off while idle
    assert 1 - busy / base < 0.40                   # ~28% measured with 4 motors at 2-4 k steps/s
    for got, mo in zip(rates, cfg["motors"]):
        assert got == pytest.approx(mo["v_max_steps"], rel=0.03)


# ------------------------------------------------------------------ CLI and MCP
def test_cli_control_gen(tmp_path):
    root = tmp_path / "p"
    init_project(root, example="tennis-catcher", git=False)
    code, events, res = mechy("control", "gen", "v1", "--board", "mega_ramps", "--project", str(root))
    assert code == 0 and res["ok"], res
    assert res["board"] == "mega_ramps" and res["dir"] == "control/v1"
    written = {e["path"] for e in events if e["type"] == "file.written"}
    assert "control/v1/firmware/mechy_arm/config.h" in written and set(res["files"]) <= written
    h = (root / "control/v1/firmware/mechy_arm/config.h").read_text()
    assert c_define(h, "STEP0_PIN") == "54" and c_define(h, "STEP3_PORT") == "PORTA"
    log = [json.loads(l) for l in (root / ".mechy/events.jsonl").read_text().splitlines()]
    assert any(e["type"] == "file.written" and e["path"].endswith("config.h") for e in log)
    code, _, res = mechy("control", "gen", "v9", "--project", str(root))
    assert code == 1 and res["ok"] is False and "v9" in res["error"]


def test_mcp_control_gen(gen):
    from mechy.mcp_server import create_server
    proj, _ = gen
    s = create_server(proj.root)
    res = asyncio.run(s.call_tool("control_gen", {"variant": "v1", "board": "uno_cnc"}))
    content = res[0] if isinstance(res, tuple) else res
    out = json.loads(content[0].text)
    assert out["ok"] and out["board"] == "uno_cnc" and len(out["steps_per_rad"]) == 4
