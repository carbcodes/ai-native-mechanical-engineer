"""Assembly order for the belt_arm generator: which step installs each CAD part and BOM line, the
order parts thread onto each joint shaft, and the step instructions (filled from the design data).

Order (standards rule 8): prepare prints -> base -> turntable -> tower and motors -> drive pulleys and
motor belts -> upper arm -> forearm -> hand -> cup slide -> electronics -> tension and home.
"""

from __future__ import annotations

from collections import Counter, OrderedDict

STEPS = OrderedDict([
    ("prep", "Prepare the printed parts"),
    ("base", "Base"),
    ("turntable", "Turntable"),
    ("tower", "Tower and motors"),
    ("drive", "Drive pulleys and motor belts"),
    ("upper_arm", "Upper arm on the shoulder shaft"),
    ("forearm", "Forearm on the elbow shaft"),
    ("hand", "Hand on the wrist shaft"),
    ("cup", "Cup slide"),
    ("electronics", "Electronics"),
    ("tension", "Tension the belts and home"),
])

# BOM lines that are not CAD parts, by item-name prefix
EXTRA_BOM_STEP = (
    ("M3 brass heat-set insert", "prep"),
    ("M4x12 screw", "base"),
    ("Zip ties", "cup"),
    ("Soft nylon net", "cup"),
    ("EVA foam sheet", "cup"),
    ("A4988", "electronics"),
    ("Arduino", "electronics"),
    ("12 V", "electronics"),
    ("Stepper cable", "electronics"),
    ("3-core sensor cable", "electronics"),
)

# ref_arm (20sffactory): the vendor Assembly Guide's order — socket and turntable first, the
# main body with its three motors, then the whole linkage head, toolhead, electronics, home.
REF_STEPS = OrderedDict([
    ("prep", "Prepare the printed parts"),
    ("base", "Socket and base yaw drive"),
    ("turntable", "Main body, motors and belts"),
    ("arm", "Linkage: shanks, lever, pleuel and levelling links"),
    ("toolhead", "Toolhead"),
    ("electronics", "Electronics"),
    ("home", "Home and calibrate"),
])

REF_EXTRA_BOM_STEP = (
    ("Arduino", "electronics"), ("CNC Shield", "electronics"), ("A4988", "electronics"),
    ("Power supply", "electronics"), ("Electrolytic", "electronics"), ("Stepper cable", "electronics"),
    ("Silicone wire", "electronics"), ("GT2", "turntable"), ("51105", "base"),
    ("F624ZZ", "arm"), ("F686ZZ", "arm"), ("Endstop", "base"),
    ("M2", "base"), ("M3", "arm"), ("M4", "arm"), ("M6", "arm"), ("Servo", "toolhead"),
)


def ref_step_of(part) -> str:
    return getattr(part, "step", "arm") if getattr(part, "step", None) in REF_STEPS else "arm"


_TURNTABLE = ("turntable", "bearing_turntable", "magnet_base", "belt_base")
_DRIVE = ("elbow_drive_pulley", "wrist_drive_pulley", "bearing_elbow_drive", "bearing_wrist_drive",
          "magnet_elbow", "belt_shoulder_motor", "belt_elbow_motor", "belt_wrist_motor")
_ARM_FROM_TURNTABLE = ("shaft_shoulder", "collar_shoulder")
_SLIDE_ON_HAND = ("slide_", "grub_slide")


def step_of(part) -> str:
    """Step id for a belt_arm Part (name, body, kind)."""
    n, body = part.name, part.body
    if body == "cup" or n.startswith(_SLIDE_ON_HAND):
        return "cup"
    if n.startswith(_TURNTABLE):
        return "turntable"
    if body == "base":
        return "base"
    if n.startswith(_ARM_FROM_TURNTABLE):
        return "upper_arm"
    if n.startswith(_DRIVE):
        return "drive"
    if body == "turntable":
        return "tower"
    return body if body in STEPS else "tension"


def bom_item_for_ref(ref: str) -> str | None:
    """BOM item name (bom.csv `item`) of a purchased CAD part ref; None for parts that are not a BOM line."""
    from ..cad.belt_arm import BOM_SPECS, SPRINGS
    if ref in BOM_SPECS:
        return BOM_SPECS[ref][0]
    if ref.startswith("gt2_loop_"):
        return f"GT2 closed-loop belt {ref.split('_')[-1]} mm"
    if ref.startswith("shaft_8x"):
        return f"Steel shaft 8 mm x {ref.split('x')[-1]} mm"
    if ref.startswith("rod_4x"):
        return f"Steel rod 4 mm x {ref.split('x')[-1]} mm"
    for sp in SPRINGS:
        if sp["ref"] == ref:
            return f"Compression spring {sp['id']}"
    return None


def part_of_bom_item(ref: str) -> bool:
    """A drawn sub-part of a bought part (KW12-3_lever belongs to the KW12-3 switch)."""
    from ..cad.belt_arm import BOM_SPECS
    return any(ref.startswith(k + "_") for k in BOM_SPECS)


def assign_bom(bom_rows: list[dict], part_steps: dict[str, set], steps_order=None,
               extra=None) -> dict[str, list[str]]:
    """BOM item -> steps that use it. part_steps maps BOM item names (from CAD refs) to step ids."""
    steps_order = list(steps_order or STEPS)
    extra = extra if extra is not None else EXTRA_BOM_STEP
    out = {}
    for r in bom_rows:
        item = r["item"]
        steps = sorted(part_steps.get(item, set()), key=steps_order.index)
        if not steps:
            steps = [s for pre, s in extra if item.startswith(pre)][:1]
        out[item] = steps
    return out


def shaft_threading(design, tol_mm: float = 6.0) -> dict[str, list[str]]:
    """Parts on each joint shaft (shoulder, elbow, wrist) in order from -y to +y, at q = 0."""
    axes = {"shoulder": design.origins["upper_arm"], "elbow": design.origins["forearm"],
            "wrist": design.origins["hand"]}
    out = {}
    for joint, o in axes.items():
        hits = []
        for p in design.parts:
            if p.kind in ("fastener", "belt", "sensor", "magnet") or p.ref.startswith(("shaft_8x", "rod_4x")):
                continue
            bb = p.shape.bounding_box()
            if bb.min.X - tol_mm <= o[0] <= bb.max.X + tol_mm and bb.min.Z - tol_mm <= o[2] <= bb.max.Z + tol_mm:
                hits.append(((bb.min.Y + bb.max.Y) / 2, p.name))
        out[joint] = [n for _, n in sorted(hits)]
    return out


def _count(names) -> list[list]:
    return [[k, v] for k, v in Counter(names).items()]


def ref_step_instructions(step: str, ctx: dict) -> list[str]:
    """Vendor-style assembly steps for ref_arm (the 20sffactory guide order, adapted to the parts
    that actually ship)."""
    if step == "prep":
        return [
            f"Print every part in the print list ({ctx.get('pieces', '?')} pieces, about "
            f"{ctx.get('grams', '?')} g {ctx.get('material', 'PLA')}) in the listed orientation.",
            "Clean every bearing bore (F624ZZ / F686ZZ press fits) with a drill bit until a bearing "
            "presses in by hand; do not hammer printed seats.",
            "Print the 140 mm shank calibrator too - it sets the homing steps in the last step.",
        ]
    if step == "base":
        return [
            "Seat the 51105 thrust bearing in the socket and press the socket into its stand.",
            "Mount the yaw NEMA 17 inside the socket with its 20T pulley (set screw on the flat).",
            "Fit the Z endstop microswitch and wire it to the shield's Z limit header (D11).",
        ]
    if step == "turntable":
        return [
            "Loop the base GT2 belt over the rotategear and lower the main body onto the 51105.",
            "Mount the two arm NEMA 17s on the main body (Y = lower shank, X = upper/lever), 20T "
            "pulleys on both, belts looped but not tensioned.",
            "Bolt on the endstop bracket and stabilizer; fit the Y and X endstop switches.",
        ]
    if step == "arm":
        return [
            "Shoulder S: lower shank + lower 90T gear + lever + upper 90T gear share the S axis "
            "(F624ZZ bearings). Free rotation, no play.",
            "Pleuel: lever end L to the upper shank's drive pin (F624ZZ); it must stay parallel "
            "to the lower shank.",
            "Elbow E: lower shank + upper shank + triplate on one axis (F686ZZ).",
            "Lower levelling link: B0 on the main body to the triplate's rear pin; upper levelling "
            "link (BAM part) triplate T2 to the manipulator T3.",
            "Wrist W: manipulator on the upper shank end (F686ZZ). The linkage keeps it level.",
        ]
    if step == "toolhead":
        return [
            "Cup: bolt the cup flange to the manipulator plate (M3 into the printed flange; the "
            "cup opening points straight up).",
            "Stick the foam liner ring inside the cup wall.",
        ]
    if step == "electronics":
        return [
            "Plug the three A4988 drivers into X/Y/Z (EN to EN), set MS1/MS2/MS3 jumpers for the "
            "chosen microsteps and Vref BEFORE connecting the belts (wiring sheet).",
            "Motors: X = upper arm, Y = lower arm, Z = yaw. Endstops to the matching limit headers.",
            "100 uF capacitor across the shield's motor power input, 24 V supply, Arduino on USB. "
            "Never unplug a motor with the supply on.",
            "Flash the generated firmware (flashing steps on the wiring sheet).",
        ]
    if step == "home":
        return [
            "Mount the shank calibrator and set X_HOME_STEPS / Y_HOME_STEPS / Z_HOME_STEPS per the "
            "control README (the generated values are estimates until calibrated).",
            "Home order: shoulder, elbow, base (the wrist is passive - the linkage levels it).",
            "Send HOME with a hand on the power switch; each joint must stop cleanly at its endstop.",
        ]
    return []


def step_instructions(step: str, ctx: dict) -> list[str]:
    """Numbered instructions for a step. ctx: belts (by joint), homing (by joint), slide, threading,
    print settings, counts."""
    belts = ctx.get("belts", {})
    home = ctx.get("homing", {})
    th = ctx.get("threading", {})
    sl = ctx.get("slide") or {}

    def belt(j):
        b = belts.get(j)
        return f"{b['standard_mm']} mm loop ({b['teeth'][0]}T-{b['teeth'][1]}T)" if b else "belt"

    def thread(j):
        return " > ".join(th.get(j, [])) or "see the render"

    if step == "prep":
        return [
            f"Print every part in the print list ({ctx.get('pieces', '?')} pieces, about "
            f"{ctx.get('grams', '?')} g {ctx.get('material', 'PETG')}) in the listed orientation.",
            "Clean the 8 mm bores and the 22 / 16 mm bearing seats with a drill bit or reamer until a bearing "
            "presses in by hand with light force. Do not hammer printed seats.",
            f"Melt the M3 heat-set inserts ({ctx.get('inserts', '?')} incl. spares) into every screw boss that "
            "takes an M3 from the far side (tower, spine, spacers, pulleys, base plate, slide bosses and lugs). "
            "Soldering iron at about 230 C for PETG (estimate; use your insert vendor's figure).",
            "Test-fit all bearings and shafts before assembly; a bore that is tight now gets tighter when the "
            "part is clamped.",
        ]
    if step == "base":
        h = home.get("base", {})
        return [
            "Screw the base shell to the base plate (M3x10 into the plate's inserts).",
            "Mount the base NEMA 17 shaft-up under the deck with 4 x M3x10. Leave the screws finger-tight: the "
            "slotted mount tensions the base belt in the last step.",
            "Push the GT2 20T pulley onto the motor shaft, set screw on the shaft flat, flange up, level with "
            "the turntable ring (checked in step 2).",
            "Press the 8 x 35 mm shaft into the deck centre and seat the 51105 thrust bearing on the deck "
            "(grooved washer down, shaft washer up).",
            f"Homing: glue the A3144 hall sensor into the printed post ({h.get('mount', 'base deck')}), flat face "
            "toward the turntable, and run its lead out of the base.",
            "Fix the base to the table with 4 x M4x12 + washers through the base plate.",
        ]
    if step == "turntable":
        return [
            "Glue a 5x2 magnet into the pocket on the turntable underside, south pole facing down (toward the "
            "A3144). Check with the sensor powered: its output goes LOW over the magnet.",
            "Press the 608-2RS into the turntable hub.",
            f"Loop the base belt ({belt('base')}) around the turntable's pulley ring, lower the turntable onto "
            "the thrust bearing over the shaft, then pull the belt over the motor pulley.",
            "Turn the turntable by hand through +-150 deg: it must turn freely with no rubbing on the base shell.",
        ]
    if step == "tower":
        h = home.get("shoulder", {})
        return [
            "Screw the two tower plates and the motor spine to the turntable (M3x16 into inserts).",
            "Mount the shoulder motor on the -y tower plate (body outboard) with 4 x M3x10, and the elbow and "
            "wrist motors on the two faces of the spine with M3x16. Leave all motor screws finger-tight in "
            "their slots for belt tensioning.",
            "Fit a GT2 20T pulley on each motor shaft (set screw on the flat) and line it up with its belt plane.",
            f"Homing: screw the KW12-3 switch to the tower plate with 2 x M2x10 ({h.get('mount', '')}); it is "
            "tripped by the tab on the upper arm. Press the elbow A3144 into its pocket in the spine.",
            "Route the three motor cables and the sensor leads down the spine to the base, leaving a service "
            "loop for +-150 deg of yaw.",
        ]
    if step == "drive":
        return [
            "Press two 688-2RS into each compound drive pulley (elbow and wrist). They turn freely on the "
            "shoulder shaft.",
            "Glue a 5x2 magnet into the elbow drive pulley pocket, south pole toward the spine's A3144.",
            f"Hang the motor belts loosely: shoulder {belt('shoulder')}, elbow {belt('elbow')}, wrist "
            f"{belt('wrist')}. Each loops over its motor pulley now and over its driven pulley in the next step.",
        ]
    if step == "upper_arm":
        return [
            "Press a 608-2RS into each upper-arm plate at the shoulder, and screw the plates together with the "
            "six spacers (M3x10 each side).",
            "Screw the shoulder pulley to the -y plate (M3x16) and the shoulder homing tab to the +y plate.",
            f"Slide the 8 x 110 mm shoulder shaft through, threading in this order (-y to +y): {thread('shoulder')}. "
            "Engage the three motor belts on their driven pulleys as the shaft passes.",
            "Lock the shaft with the two 8 mm collars against the tower plates; the arm must swing freely.",
            f"Fit the two upper-arm belts ({belt('elbow_upper')}) on the drive pulleys' 40T halves, then the "
            "8 x 70 mm elbow shaft and the wrist idler (two 688-2RS) at the elbow. Full order on the elbow shaft "
            f"(-y to +y; the forearm parts come in the next step): {thread('elbow')}.",
        ]
    if step == "forearm":
        h = home.get("wrist", {})
        return [
            "Press the two 608-2RS into the forearm's elbow bosses and screw the forearm pulley to it (M3x16).",
            "Slide the forearm onto the elbow shaft between the upper-arm plates (order above) and clamp the "
            "elbow collars.",
            f"Loop the forearm belt ({belt('wrist_fore')}) over the wrist idler's second 40T and along the "
            "forearm, then push in the 8 x 61 mm wrist shaft.",
            f"Homing: screw the wrist KW12-3 to the forearm with 2 x M2x10 ({h.get('mount', '')}); run its lead "
            "along the arm to the turntable (the only lead that runs along the arm).",
        ]
    if step == "hand":
        return [
            "Press the two 608-2RS into the hand fork cheeks and screw the hand pulley to the fork (M3x16).",
            f"Fit the fork on the wrist shaft, threading: {thread('wrist')}. Engage the forearm belt on the hand "
            "pulley.",
            "Screw the wrist homing tab to the +y cheek with an M2x10 so it trips the forearm switch at the "
            "lower wrist limit.",
        ]
    if step == "cup":
        out = []
        if sl:
            sp = sl.get("spring", {})
            out += [
                "Press an LM4UU into each lug of the cup shell. Put a 5 mm felt pad in each lug's brake hole and "
                "an M3x6 set screw behind it, just touching.",
                f"Slide a spring ({sp.get('id', 'spring')}) onto each 4 mm rod, push the rods through the lugs into "
                "the hand bosses and clamp them with the M3x6 grub screws.",
                "Fit an O-ring then a 4 mm shaft collar on each rod tip as the front stop; stick the rubber bumper "
                "on the hand plate under the cup bottom (rear stop).",
                f"Travel check: push the cup back by hand; it must reach the bumper at {sl.get('travel_m', 0) * 1000:.0f} "
                f"mm with the springs above their {sp.get('min_work_mm', '?')} mm minimum length, and spring back "
                "to the collars.",
                f"Brake: tighten each felt screw until pulling the cup back takes about "
                f"{sl.get('brake_drag_target_n', 3)} N in total (luggage scale; estimate from the sim). The cup may "
                f"then rest up to {sl.get('rest_offset_max_mm', '?')} mm behind the collars after a catch.",
            ]
        out.append("Fit the liner: sew the net as a slack pocket and zip-tie it to the cup ribs (or stick the EVA "
                   "liner in for an eva_foam variant).")
        return out
    if step == "electronics":
        return [
            "Plug the four A4988 drivers into the CNC shield (check the orientation: EN pin to EN), set the "
            "microstep jumpers and Vref per the wiring sheet BEFORE connecting the belts.",
            "Connect each motor to its driver socket and the homing sensors to the limit headers (wiring table).",
            "Power the shield from the 12 V supply; the Arduino from USB. Never plug or unplug a motor with "
            "the supply on.",
            "Flash the firmware (flashing steps on the wiring sheet).",
        ]
    if step == "tension":
        out = []
        for j in ("base", "shoulder", "elbow", "wrist"):
            b = belts.get(j)
            if b:
                out.append(f"{j}: slide the motor in its slots until the {b['standard_mm']} mm belt deflects about "
                           f"{max(2.0, b['centre_mm'] * 0.016):.1f} mm under a light finger press mid-span "
                           "(about 1/64 of the span, a common GT2 rule of thumb; estimate), then tighten.")
        out.append("Link belts (520 mm): stock loops sized exactly to the 220 mm centre distance; take up slack "
                   "with the slotted shaft holes (+-3 mm) before clamping the collars.")
        order = ctx.get("homing_order") or list(home)
        out.append("Home in this order: " + ", ".join(order) + ". Send HOME with a hand on the power switch and "
                   "check each joint stops at its sensor (table on the belts and homing sheet).")
        return out
    return []
