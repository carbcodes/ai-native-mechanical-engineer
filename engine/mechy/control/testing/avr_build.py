"""Compile a generated sketch for a real AVR without the Arduino IDE (tests and CI).

Uses `arduino-cli` when it and its arduino:avr core are installed; otherwise avr-gcc plus a
checkout of github.com/arduino/ArduinoCore-avr given by $MECHY_ARDUINO_CORE (the same flags
arduino-builder uses). Returns {"ok", "tool", "flash", "ram", "log"} or None when neither is set up.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

MCU = {"arduino:avr:uno": ("atmega328p", "standard", "ARDUINO_AVR_UNO"),
       "arduino:avr:mega": ("atmega2560", "mega", "ARDUINO_AVR_MEGA2560")}


def available() -> str | None:
    if shutil.which("arduino-cli"):
        r = subprocess.run(["arduino-cli", "core", "list"], capture_output=True, text=True)
        if "arduino:avr" in r.stdout:
            return "arduino-cli"
    core = os.environ.get("MECHY_ARDUINO_CORE")
    if shutil.which("avr-g++") and core and (Path(core) / "cores" / "arduino" / "Arduino.h").exists():
        return "avr-gcc"
    return None


def _size(elf: Path) -> tuple[int, int]:
    r = subprocess.run(["avr-size", "-A", str(elf)], capture_output=True, text=True, check=True)
    sec = {m.group(1): int(m.group(2)) for m in re.finditer(r"^\.(\w+)\s+(\d+)", r.stdout, re.M)}
    return sec.get("text", 0) + sec.get("data", 0), sec.get("data", 0) + sec.get("bss", 0)


def compile_sketch(sketch_dir: str | Path, fqbn: str, out_dir: str | Path | None = None) -> dict | None:
    tool = available()
    sketch_dir = Path(sketch_dir)
    if tool is None:
        return None
    if tool == "arduino-cli":
        r = subprocess.run(["arduino-cli", "compile", "--fqbn", fqbn, str(sketch_dir)],
                           capture_output=True, text=True)
        m = re.search(r"uses (\d+) bytes .*?\n.*?Global variables use (\d+) bytes", r.stdout, re.S)
        return {"ok": r.returncode == 0, "tool": tool, "flash": int(m.group(1)) if m else None,
                "ram": int(m.group(2)) if m else None, "log": (r.stdout + r.stderr)[-3000:]}
    core = Path(os.environ["MECHY_ARDUINO_CORE"])
    mcu, variant, board_def = MCU[fqbn]
    out = Path(out_dir or tempfile.mkdtemp(prefix="mechy-avr-"))
    out.mkdir(parents=True, exist_ok=True)
    common = [f"-mmcu={mcu}", "-DF_CPU=16000000L", "-DARDUINO=10819", f"-D{board_def}", "-DARDUINO_ARCH_AVR",
              "-Os", "-ffunction-sections", "-fdata-sections", "-flto",
              f"-I{core / 'cores' / 'arduino'}", f"-I{core / 'variants' / variant}", f"-I{sketch_dir}"]
    cxx = ["avr-g++", *common, "-std=gnu++11", "-fpermissive", "-fno-exceptions", "-fno-threadsafe-statics",
           "-Wall", "-Wextra"]
    cc = ["avr-gcc", *common, "-std=gnu11"]
    log, objs = [], []

    def run(cmd):
        r = subprocess.run(cmd, capture_output=True, text=True)
        log.append(" ".join(cmd[:2]) + " ...\n" + r.stdout + r.stderr)
        return r.returncode == 0

    ino = next(sketch_dir.glob("*.ino"))
    sk = out / (ino.stem + ".ino.cpp")
    sk.write_text("#include <Arduino.h>\n#line 1 \"" + ino.name + "\"\n" + ino.read_text())
    ok = run([*cxx, "-c", str(sk), "-o", str(out / "sketch.o")])
    sketch_log = log[-1]
    objs.append(out / "sketch.o")
    for src in sorted((core / "cores" / "arduino").iterdir()):
        if src.suffix not in (".c", ".cpp", ".S"):
            continue
        o = out / (src.name + ".o")
        tool_cmd = cxx if src.suffix == ".cpp" else (cc if src.suffix == ".c" else
                                                     ["avr-gcc", *common, "-x", "assembler-with-cpp"])
        ok &= run([*[a for a in tool_cmd if not a.startswith("-W")], "-w", "-c", str(src), "-o", str(o)])
        objs.append(o)
    elf = out / (ino.stem + ".elf")
    ok &= run(["avr-gcc", f"-mmcu={mcu}", "-Os", "-flto", "-fuse-linker-plugin", "-Wl,--gc-sections",
               "-o", str(elf), *map(str, objs), "-lm"])
    flash, ram = _size(elf) if ok else (None, None)
    return {"ok": ok, "tool": tool, "flash": flash, "ram": ram, "elf": str(elf) if ok else None,
            "warnings": [l for l in sketch_log.splitlines() if "warning" in l],
            "log": "\n".join(log)[-3000:]}
