"""Line-based serial protocol between mechy_host.py and mechy_arm.ino (protocol 1).

Host -> firmware, one ASCII line each, '\\n' terminated, optional NMEA-style checksum
`*HH` (XOR of every byte before '*', two upper-case hex digits; the firmware rejects a line
whose checksum is wrong and accepts lines without one, for typing in a serial monitor):

    HOME                         home every joint on its switch, then go to the ready pose
    MOVE q0 q1 q2 q3 t           joint angles (rad, contracts 7.1 convention), arrive in t s
    STOP                         stop all motors now (no deceleration)
    STATUS                       report state, joint angles, motor steps, switch bits
    SETPOS q0 q1 q2 q3           declare the current pose (bench tests without switches)
    ENABLE 0|1                   release / energise the drivers
    PING

Firmware -> host:

    MECHY READY variant=v1 board=uno_cnc proto=1
    OK MOVE T=0.4120 stretched=0     (T = the duration the firmware will actually take)
    OK HOME | OK STOP | OK SETPOS | OK ENABLE | OK PONG
    DONE MOVE | DONE HOME
    ERR <CODE> [detail]              codes: CHECKSUM PARSE UNKNOWN BUSY NOT_HOMED LIMIT HOME_FAIL ESTOP
    STATUS state=IDLE homed=1 q=0.0000,1.2217,-1.3963,0.6981 steps=0,1088,-339,-170 sw=0000
"""

from __future__ import annotations

PROTOCOL_VERSION = 1
COMMANDS = {"HOME": 0, "MOVE": 5, "STOP": 0, "STATUS": 0, "SETPOS": 4, "ENABLE": 1, "PING": 0}
ERROR_CODES = ("CHECKSUM", "PARSE", "UNKNOWN", "BUSY", "NOT_HOMED", "LIMIT", "HOME_FAIL", "ESTOP")
MAX_LINE = 95     # firmware line buffer is 96 bytes including the terminator


class ProtocolError(ValueError):
    pass


def checksum(body: str) -> str:
    c = 0
    for b in body.encode("ascii"):
        c ^= b
    return f"{c:02X}"


def _fmt(x) -> str:
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return str(x)
    s = f"{float(x):.5f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def encode(cmd: str, *args, with_checksum: bool = True) -> bytes:
    cmd = cmd.upper()
    if cmd not in COMMANDS:
        raise ProtocolError(f"unknown command {cmd}")
    if len(args) != COMMANDS[cmd]:
        raise ProtocolError(f"{cmd} takes {COMMANDS[cmd]} arguments, got {len(args)}")
    body = " ".join([cmd, *(_fmt(a) for a in args)])
    line = f"{body}*{checksum(body)}" if with_checksum else body
    if len(line) > MAX_LINE:
        raise ProtocolError(f"line too long ({len(line)} > {MAX_LINE})")
    return (line + "\n").encode("ascii")


def encode_move(q, t_arrive: float, with_checksum: bool = True) -> bytes:
    q = [float(x) for x in q]
    if len(q) != 4:
        raise ProtocolError("MOVE needs 4 joint angles")
    if not t_arrive > 0:
        raise ProtocolError("MOVE needs t > 0")
    return encode("MOVE", *q, float(t_arrive), with_checksum=with_checksum)


def decode_command(line: bytes | str) -> tuple[str, list[float]]:
    """Parse a host command the way the firmware does (used by tests and the dry-run link)."""
    s = line.decode("ascii") if isinstance(line, bytes) else line
    s = s.strip()
    if "*" in s:
        body, cs = s.rsplit("*", 1)
        if cs.upper() != checksum(body):
            raise ProtocolError("CHECKSUM")
    else:
        body = s
    parts = body.split()
    if not parts:
        raise ProtocolError("PARSE")
    cmd = parts[0].upper()
    if cmd not in COMMANDS:
        raise ProtocolError("UNKNOWN")
    if len(parts) - 1 != COMMANDS[cmd]:
        raise ProtocolError("PARSE")
    try:
        args = [float(a) for a in parts[1:]]
    except ValueError as e:
        raise ProtocolError("PARSE") from e
    return cmd, args


def parse_reply(line: bytes | str) -> dict:
    """Firmware line -> {"kind": OK|DONE|ERR|STATUS|READY|LOG, "what": ..., fields...}."""
    s = (line.decode("ascii", "replace") if isinstance(line, bytes) else line).strip()
    parts = s.split()
    if not parts:
        return {"kind": "EMPTY"}
    head = parts[0]
    out: dict = {"raw": s}
    if head in ("OK", "DONE", "ERR"):
        out["kind"] = head
        out["what"] = parts[1] if len(parts) > 1 else ""
        rest = parts[2:]
    elif head == "STATUS":
        out["kind"] = "STATUS"
        rest = parts[1:]
    elif head == "MECHY" and len(parts) > 1 and parts[1] == "READY":
        out["kind"] = "READY"
        rest = parts[2:]
    else:
        out["kind"] = "LOG"
        return out
    extra = []
    for p in rest:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k] = _value(k, v)
        else:
            extra.append(p)
    if extra:
        out["detail"] = " ".join(extra)
    return out


def _value(k: str, v: str):
    if "," in v or k in ("q", "steps"):
        try:
            return [float(x) if k == "q" else int(float(x)) for x in v.split(",")]
        except ValueError:
            return v
    if k in ("sw",):
        return v
    try:
        f = float(v)
        return int(f) if f.is_integer() and "." not in v else f
    except ValueError:
        return v


def encode_reply_status(state: str, homed: bool, q, steps, sw: str) -> str:
    """The firmware's STATUS line (used by the dry-run link to answer like the board)."""
    qs = ",".join(f"{float(x):.4f}" for x in q)
    ss = ",".join(str(int(x)) for x in steps)
    return f"STATUS state={state} homed={int(bool(homed))} q={qs} steps={ss} sw={sw}"
