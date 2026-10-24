"""Run: python3 -I build_catalogue.py. Builds designs.csv + designs/<id>.json from hand-compiled records + GitHub metadata (meta/*.json)."""
import csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
META = os.path.join(HERE, "raw", "_github_meta")
OUT = HERE
TODAY = "2026-10-23"

def meta(repo):
    p = os.path.join(META, repo.replace("/", "__") + ".json")
    if not os.path.exists(p):
        return {}
    return json.load(open(p))

# value_type per brief: datasheet | standard | handbook_typical | estimate
# here "datasheet" = numbers stated by the project's own repo/docs (read this session);
# "estimate" = compiler's own knowledge or derived numbers, not read from a source this session.
R = []
def add(**k):
    R.append(k)

# ---------------- ROBOT ARMS ----------------
add(id="ar4_mk5", name="Annin Robotics AR4 (MK5)", category="robot_arm",
    repo="ycheng517/ar4_ros_driver", repo_url="https://github.com/ycheng517/ar4_ros_driver",
    docs_url="https://www.anninrobotics.com/downloads",
    licence="UNCLEAR (hardware/CAD); MIT (ROS2 driver + URDF)", licence_file="LICENSE (ar4_ros_driver, MIT)",
    licence_notes="anninrobotics.com download page offers STL/manual/software but states no licence. Older Chris-Annin/Annin-Robot-Project repo is GPL-3.0; Chris-Annin/AR2 has no LICENSE. 'AR4' is a registered trademark of Chris Annin. Ask before redistributing CAD.",
    reuse="urdf_yes_mit; cad_unclear_ask_annin",
    dof=6, reach_mm=629, payload_claimed_kg=1.88, payload_measured_kg=None, mass_kg=12.2, repeatability_mm=0.25,
    payload_note="Vendor: 4.15 lb payload, 24.75 in reach, 27 lb mass, 198 W (converted to SI).",
    motors="NEMA 17/23 steppers with encoders (StepperOnline package; models in build manual)",
    drivers="Stepper drivers from StepperOnline package; Teensy 4.1 motion controller + Arduino Nano/Mega aux board",
    reductions="Planetary/belt per axis (see AR4-MK5 build manual; not read this session)",
    bearings="Not read this session (see build manual BOM)",
    materials="Machined aluminium structure (or printed), PETG printed covers",
    bom_cost_value=1888, bom_cost_currency="USD",
    bom_cost_note="Kit prices: combo kit from $1,189 + StepperOnline motor/driver/PSU $699 (excl. gripper $139, printed parts $299.98).",
    cad_formats="STL (print files); STEP/other CAD not confirmed", urdf="yes (xacro, ar4_ros_driver)", mjcf="no",
    maturity="high: many builds since AR2 era, active forum, ROS2 drivers by two groups",
    weaknesses="Licence of CAD not stated; open-loop-style steppers with homing switches (MK5 adds hall sensors); heavy (12 kg) for payload; aluminium machining needed unless kit bought.",
    mechy_use="Benchmark for an aluminium/stepper industrial-style 6-axis arm; use its DH tables and kinematic sheet as reference.",
    raw_files="raw/ar4/ar_macro.xacro; raw/ar4/LICENSE",
    source_url="https://www.anninrobotics.com/", value_type="datasheet")

add(id="parol6", name="PAROL6 desktop robot arm (Source Robotics)", category="robot_arm",
    repo="Source-Robotics/PAROL6-Desktop-robot-arm", repo_url="https://github.com/Source-Robotics/PAROL6-Desktop-robot-arm",
    docs_url="https://github.com/Source-Robotics/PAROL-docs",
    licence="GPL-3.0", licence_file="LICENSE (GPL-3.0 text)",
    licence_notes="Copyleft: derived CAD/firmware must stay GPL-3.0 if distributed. README: 'Project is under GPLv3 Licence'.",
    reuse="yes_copyleft",
    dof=6, reach_mm=400, payload_claimed_kg=1.0, payload_measured_kg=None, mass_kg=5.5, repeatability_mm=0.1,
    payload_note="Docs: 1 kg near the base, 0.5 kg across the full workspace; reach 400 mm with standard gripper.",
    motors="NEMA17 steppers: 1x 17HS08-1004S (16 Ncm), 3x 17HS16-2004S1 (45 Ncm), 2x 17HS24-2104S (65 Ncm)",
    drivers="6x TMC5160 on PAROL6 control board, 24 V 5 A PSU (12-50 V input range)",
    reductions="J1 belt 6.4:1; J2 planetary 20:1; J3 planetary 20:1 x belt 38:42 = 18.095:1; J4 belt 4:1; J5 belt 4:1; J6 planetary 10:1 (EG17 precision planetaries)",
    bearings="AXK3552 thrust needle (J1); 5x NSK HR32906J tapered (J3-J5); 4x NSK HR32907J tapered (J1-J2); 3x8x4 and 3x10x4 idler bearings",
    materials="3D printed (PLA/PETG per build docs) structure; HTD3M belts 6 mm",
    bom_cost_value=None, bom_cost_currency="USD",
    bom_cost_note="DIY BOM total not stated in BOM.md; sold assembled/kit on source-robotics.com (price not read this session).",
    cad_formats="STL (repo); STEP via website/releases (not confirmed)", urdf="yes (PAROL6-ROS2-MOVEIT repo)", mjcf="no (not found)",
    maturity="high: 3.4k stars, active 2026, commercial kit, Discord + forum",
    weaknesses="Stepper open-loop (homing via inductive sensors); low payload across workspace; GPL copyleft on derivatives.",
    mechy_use="Closest open base for an industrial-style printed 6-axis desktop arm; reuse joint layout, tapered-bearing joints and belt/planetary ratios.",
    raw_files="raw/parol6/BOM.md; raw/parol6/LICENSE",
    source_url="https://github.com/Source-Robotics/PAROL-docs/blob/main/docs/index.md", value_type="datasheet")

add(id="bcn3d_moveo", name="BCN3D Moveo", category="robot_arm",
    repo="BCN3D/BCN3D-Moveo", repo_url="https://github.com/BCN3D/BCN3D-Moveo", docs_url="https://github.com/BCN3D/BCN3D-Moveo",
    licence="MIT", licence_file="LICENSE (MIT)", licence_notes="Permissive. Based on Andreas Hoelldorfer's BetaBots arm.",
    reuse="yes_permissive",
    dof=5, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="No official payload/reach in repo. Community reports a few hundred grams (not verified). 5 axes + servo gripper.",
    motors="Steppers: SM42HT47-1684 NEMA17, 17HS19-1684S-PG5 (5:1 planetary NEMA17), SM57HT112-3004A NEMA23, SM35HT36-1004A NEMA14, SM42HT33-1334 NEMA17; 13 kg-cm hobby servo gripper",
    drivers="TB6560 stepper drivers, Arduino Mega 2560 + RAMPS 1.4, 24 V 320 W PSU",
    reductions="T5 timing belts/pulleys (14T, 10T) on printed large pulleys + one 5:1 planetary; exact per-joint ratios in user manual",
    bearings="608ZZ, 625ZZ, 624ZZ, 623ZZ, sintered bushings 5x8x10, 8x12x20; chrome steel rods",
    materials="3D printed PLA, wood base 550x550x16 mm",
    bom_cost_value=None, bom_cost_currency="EUR", bom_cost_note="BOM PDF lists parts without prices; community estimates ~400 EUR (estimate).",
    cad_formats="SLDPRT, SLDASM, STL", urdf="community (jesseweisberg/moveo_ros, not first-party)", mjcf="no",
    maturity="medium: 2k stars, widely built in schools, repo unmaintained since 2022",
    weaknesses="Open-loop steppers, belt backlash, flexible printed links, no official specs, old TB6560 drivers.",
    mechy_use="Simple educational 5-axis baseline with permissive licence; good starting point to modify freely.",
    raw_files="raw/bcn3d_moveo/BCN3D Moveo BOM.pdf; raw/bcn3d_moveo/LICENSE",
    source_url="https://github.com/BCN3D/BCN3D-Moveo/blob/master/BOM/BCN3D%20Moveo%20BOM.pdf", value_type="datasheet")

add(id="thor", name="Thor (AngelLM)", category="robot_arm",
    repo="AngelLM/Thor", repo_url="https://github.com/AngelLM/Thor", docs_url="http://thor.angel-lm.com/documentation/",
    licence="CC-BY-SA-4.0", licence_file="LICENSE (CC BY-SA 4.0 text)", licence_notes="Attribution + share-alike; commercial use allowed.",
    reuse="yes_sharealike",
    dof=6, reach_mm=None, payload_claimed_kg=0.75, payload_measured_kg=0.75, mass_kg=None, repeatability_mm=None,
    payload_note="Author lifted 750 g incl. tool with arm stretched horizontally (worst case). Height stretched 624.15 mm (not reach).",
    motors="Steppers: 1x NEMA17 40 mm (40 Ncm) art.1; 3x NEMA17 34 mm with 5:1 reduction (121.2 Ncm) art.2-3; 3x 34 mm (26 Ncm) art.4-6",
    drivers="ThorControlPCB (Arduino Mega shield) or commercial boards; GRBL / RepRapFirmware",
    reductions="3D printed gears, GT2 belts/pulleys, 5:1 geared steppers on art.2-3; yaw-roll-roll-yaw-roll-yaw",
    bearings="See BOM page (not fully read)",
    materials="PLA/PETG 3-4 kg + ABS 0.5 kg",
    bom_cost_value=350, bom_cost_currency="EUR", bom_cost_note="FAQ: components ~350 EUR, excl. printer; ~200 h printing.",
    cad_formats="FCStd (FreeCAD source), STEP, STL", urdf="yes (Thor-ROS repo, not read)", mjcf="no",
    maturity="medium-high: 1.6k stars, forum + Discord, used in schools",
    weaknesses="Printed gears wear/backlash, open-loop steppers, low payload, long print time.",
    mechy_use="Best FreeCAD-native arm; editable parametric source for adapting.",
    raw_files="", source_url="http://thor.angel-lm.com/faq/", value_type="datasheet")

add(id="so101", name="SO-100 / SO-101 (TheRobotStudio + Hugging Face)", category="robot_arm",
    repo="TheRobotStudio/SO-ARM100", repo_url="https://github.com/TheRobotStudio/SO-ARM100", docs_url="https://huggingface.co/docs/lerobot/so101",
    licence="Apache-2.0", licence_file="LICENSE (Apache 2.0)", licence_notes="Permissive incl. patent grant.",
    reuse="yes_permissive",
    dof=6, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="5 DOF + gripper (counted 6 servos). No official payload; servo stall 16.5 kg-cm at 6 V (7.4 V version) or 30 kg-cm (12 V version). Community quotes ~0.2-0.5 kg (estimate).",
    motors="6x Feetech STS3215 serial bus servos (follower 1/345 gear); leader uses mixed 1/345, 1/191, 1/147 gears",
    drivers="Waveshare serial bus servo driver board, 5 V or 12 V PSU",
    reductions="Inside servos: 1:345 (follower), 1:191 / 1:147 (leader joints)",
    bearings="Servo internal only",
    materials="PLA+ printed; TPU 95A fingertips (variants)",
    bom_cost_value=121.94, bom_cost_currency="USD", bom_cost_note="Follower arm $121.94 (US), leader+follower $229.88; excl. printing.",
    cad_formats="STEP, STL, 3MF, Onshape (.part)", urdf="yes (SO100, SO101)", mjcf="yes (SO101 scene.xml)",
    maturity="very high: 7.9k stars, LeRobot default arm, thousands built",
    weaknesses="Hobby servo backlash and low torque; plastic horns; no real payload rating; position-only control.",
    mechy_use="Cheapest well-simulated arm with URDF+MJCF; ideal for learning pipelines and quick sims.",
    raw_files="raw/so101/so101_new_calib.urdf; raw/so101/scene.xml; raw/so101/so100.urdf; raw/so101/LICENSE",
    source_url="https://github.com/TheRobotStudio/SO-ARM100", value_type="datasheet")

add(id="koch_v1_1", name="Koch low-cost robot arm (v1 / v1.1)", category="robot_arm",
    repo="AlexanderKoch-Koch/low_cost_robot", repo_url="https://github.com/AlexanderKoch-Koch/low_cost_robot", docs_url="https://github.com/jess-moss/koch-v1-1",
    licence="MIT (v1); Apache-2.0 (v1.1 fork)", licence_file="LICENSE (MIT) / jess-moss/koch-v1-1 LICENSE (Apache 2.0)", licence_notes="Both permissive.",
    reuse="yes_permissive",
    dof=6, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="5 DOF + gripper. No payload stated; XL330 servos are weak (estimate <0.2 kg).",
    motors="Follower: 2x Dynamixel XL430-W250 + 4x XL330-M288; leader: 6x XL330-M077",
    drivers="Waveshare serial bus servo driver board; 12 V PSU + 5 V step-down for XL330",
    reductions="Inside Dynamixel servos", bearings="Servo internal + idler wheels",
    materials="PLA+/ABS/PETG printed",
    bom_cost_value=258, bom_cost_currency="USD", bom_cost_note="v1 follower $258, leader $183; v1.1 follower $278, leader $199.",
    cad_formats="STEP, STL, F3Z (v1); SLDPRT/SLDASM, STEP, STL (v1.1)", urdf="yes (v1 simulation)", mjcf="yes (v1 scene.xml)",
    maturity="high: 3.4k + 735 stars; supported by LeRobot; superseded by SO-101 for cost",
    weaknesses="Expensive per torque vs Feetech; low payload; no longer the LeRobot default.",
    mechy_use="Reference for Dynamixel-based teleop leader/follower arms.",
    raw_files="raw/koch_v1/low-cost-arm.urdf; raw/koch_v1/scene.xml; raw/koch_v1/LICENSE",
    source_url="https://github.com/AlexanderKoch-Koch/low_cost_robot", value_type="datasheet")

add(id="arctos", name="Arctos 6-axis arm", category="robot_arm",
    repo="Arctos-Robotics/ROS", repo_url="https://github.com/Arctos-Robotics/ROS", docs_url="https://arctosrobotics.com/",
    licence="MIT (ROS packages + URDF/STL meshes); CAD files sold commercially", licence_file="LICENSE (MIT, ROS repo)",
    licence_notes="Full CAD (Fusion 360, STEP, 3MF) is a paid download from arctosrobotics.com - not open. Only URDF/meshes and firmware are MIT.",
    reuse="partial (URDF/firmware only)",
    dof=6, reach_mm=600, payload_claimed_kg=2.0, payload_measured_kg=None, mass_kg=10, repeatability_mm=None,
    payload_note="Vendor homepage: reach 600 mm, payload 2 kg, weight 10 kg (claimed, not independently measured).",
    motors="NEMA17/NEMA23 steppers (open-loop kit) or closed-loop MKS SERVO42/57 style (closed-loop kit)",
    drivers="Arduino Mega + CNC shield (GRBL), or CAN closed-loop drivers; vendor CLMD (TMC2209 FOC + CAN)",
    reductions="Cycloidal + planetary + belt (per vendor docs; not read)", bearings="Not read",
    materials="3D printed (PETG/PLA)",
    bom_cost_value=231, bom_cost_currency="USD", bom_cost_note="Vendor: kits 'starting at $231' (partial kit; full kit higher).",
    cad_formats="URDF meshes STL (open); Fusion 360/STEP/3MF/STL (paid)", urdf="yes (arctos.urdf)", mjcf="no",
    maturity="medium: commercial kit with community, ROS1/ROS2 packages",
    weaknesses="CAD not open source; claimed payload unverified; ROS repo targets Melodic.",
    mechy_use="URDF reference only; do not copy CAD.",
    raw_files="raw/arctos/arctos.urdf; raw/arctos/LICENSE",
    source_url="https://arctosrobotics.com/", value_type="datasheet")

add(id="openarm_v2", name="OpenArm 2.0 (Enactic)", category="robot_arm",
    repo="enactic/openarm_hardware", repo_url="https://github.com/enactic/openarm_hardware", docs_url="https://docs.openarm.dev/hardware/",
    licence="CERN-OHL-S-2.0 (hardware); Apache-2.0 (description/software)", licence_file="LICENSE.txt (CERN-OHL-S v2) / openarm_description LICENSE.txt (Apache 2.0)",
    licence_notes="Strongly reciprocal hardware licence: modified hardware designs must be released under same licence if distributed.",
    reuse="yes_copyleft",
    dof=7, reach_mm=None, payload_claimed_kg=4.1, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Nominal 4.1 kg (held 1 min at worst posture), peak 6.0 kg (3 s move + 1 s hold); includes end effector. 7 DOF per arm, bimanual.",
    motors="Damiao DM-J8009P-2EC (20 Nm rated/40 Nm peak, 9:1), DM-J4340 (9/27 Nm, 40:1), DM-J4310-2EC (3/7 Nm, 10:1); 24 V",
    drivers="Integrated Damiao drivers, CAN bus, dual 14-bit magnetic encoders",
    reductions="In motor modules: 9:1 (8009P), 40:1 (4340), 10:1 (4310)",
    bearings="Cross-roller bearings in cantilevered joints (per docs)",
    materials="MiSUMi aluminium frame pillars, machined/printed links",
    bom_cost_value=6500, bom_cost_currency="USD", bom_cost_note="README: $6,500 for complete bimanual system.",
    cad_formats="STEP, STL (Google Drive + GitHub releases)", urdf="yes (xacro, v1 + v2)", mjcf="yes (openarm_mujoco repo, not downloaded)",
    maturity="high and growing: 3.6k stars, active Oct 2026, commercial + DIY",
    weaknesses="Expensive vs printed arms; Damiao supply dependency; 4340 joints not backdrivable QDD.",
    mechy_use="Reference for backdrivable, CAN-QDD humanoid arm with honest payload definitions.",
    raw_files="raw/openarm/v2.urdf; raw/openarm/LICENSE.txt",
    source_url="https://docs.openarm.dev/hardware/openarm-2.0/general", value_type="datasheet")

add(id="faze4", name="Faze4 6-axis arm (Source Robotics)", category="robot_arm",
    repo="Source-Robotics/Faze4-Robotic-arm", repo_url="https://github.com/Source-Robotics/Faze4-Robotic-arm", docs_url="https://faze4-robotic-arm-docs.readthedocs.io/en/latest/",
    licence="CERN-OHL-S-2.0 (LICENSE file); README says MIT", licence_file="LICENSE (CERN-OHL-S v2)",
    licence_notes="Conflict: LICENSE file is CERN-OHL-S-2.0 but README ends 'Project is under MIT Licence'. Treat as CERN-OHL-S (stricter) until clarified.",
    reuse="yes_copyleft",
    dof=6, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=15, repeatability_mm=None,
    payload_note="Docs: weight 14-15 kg; ~1000 parts. Payload not stated in docs read.",
    motors="6 NEMA steppers (StepperOnline; data in docs 'Stepper data')",
    drivers="External stepper drivers, Teensy 3.5, Faze4 distribution PCB V2",
    reductions="J1 15:1 cycloidal x 5:3 belt = 25:1; J2 27:1 cycloidal; J3 15:1 cycloidal; J4 11:1 cycloidal x 28:26 belt = 11.85:1; J5 11:1 cycloidal; J6 19.19:1 planetary",
    bearings="See BOM xlsx (raw/faze4)",
    materials="3D printed; HTD 5M belts 10 mm (490, 430, 285 mm)",
    bom_cost_value=1000, bom_cost_currency="USD", bom_cost_note="README: '<1000 dollars'.",
    cad_formats="STEP, STL", urdf="yes", mjcf="no",
    maturity="medium: 912 stars, predecessor of PAROL6, less active",
    weaknesses="Heavy (15 kg), many parts, printed cycloidal wear; licence ambiguity.",
    mechy_use="Reference for printed cycloidal reducers in an arm with spherical wrist.",
    raw_files="raw/faze4/Final_light_assembly_URDF.urdf; raw/faze4/BOM_7_11_2023.xlsx; raw/faze4/LICENSE",
    source_url="https://github.com/Source-Robotics/Faze4-Robotic-arm/blob/master/docs/B_Design_decisions.rst", value_type="datasheet")

add(id="lerobot_lekiwi", name="LeRobot (software) + LeKiwi mobile manipulator", category="robot_arm",
    repo="SIGRobotics-UIUC/LeKiwi", repo_url="https://github.com/SIGRobotics-UIUC/LeKiwi", docs_url="https://github.com/huggingface/lerobot",
    licence="Apache-2.0 (LeKiwi hardware and LeRobot software)", licence_file="LICENSE.txt (Apache 2.0); huggingface/lerobot LICENSE (Apache 2.0)",
    licence_notes="Permissive.", reuse="yes_permissive",
    dof=9, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="SO-101 arm (5+1) on 3-omniwheel base (3 STS3215 wheel servos). No payload stated.",
    motors="Feetech STS3215 (arm + 3 wheel servos), 5 V or 12 V versions",
    drivers="Waveshare bus servo board, Raspberry Pi 5",
    reductions="Servo internal; 4 in VEX omni wheels direct", bearings="Servo internal",
    materials="PLA printed stacked base plates (20 mm hole grid)",
    bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="BOM.md lists subtotals per section (e.g. 12 V servo set $108.5); see raw/lekiwi/BOM.md.",
    cad_formats="STL, STEP", urdf="yes", mjcf="no (LeRobot sims elsewhere)",
    maturity="very high for LeRobot (28k stars); LeKiwi 1.5k stars",
    weaknesses="Same servo limits as SO-101; small base.",
    mechy_use="Reference for low-cost mobile manipulator and the LeRobot data/teleop stack.",
    raw_files="raw/lekiwi/LeKiwi.urdf; raw/lekiwi/BOM.md; raw/lekiwi/LICENSE.txt",
    source_url="https://github.com/SIGRobotics-UIUC/LeKiwi", value_type="datasheet")

# ---------------- GRIPPERS ----------------
add(id="ssg48_gripper", name="SSG-48 adaptive electric gripper", category="gripper",
    repo="Source-Robotics/SSG-48-adaptive-electric-gripper", repo_url="https://github.com/Source-Robotics/SSG-48-adaptive-electric-gripper", docs_url="https://source-robotics.github.io/SSG48-gripper-docs/",
    licence="Apache-2.0", licence_file="LICENSE (Apache 2.0)", licence_notes="Permissive.", reuse="yes_permissive",
    dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="48 mm stroke (from name). Force/position control via Spectral micro BLDC driver over CAN.",
    motors="Small BLDC (see BOM)", drivers="Spectral micro BLDC driver (CAN, 24 V)", reductions="Not read", bearings="See BOM",
    materials="3D printed", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="Not stated.",
    cad_formats="STEP, STL", urdf="yes", mjcf="yes (scene.xml)", maturity="medium: 184 stars, commercial product",
    weaknesses="Motor sourcing difficult (README suggests MSG instead).", mechy_use="Parallel gripper with force control and sim models.",
    raw_files="raw/ssg48_gripper/BOM.md; raw/ssg48_gripper/LICENSE",
    source_url="https://github.com/Source-Robotics/SSG-48-adaptive-electric-gripper", value_type="datasheet")

add(id="msg_gripper", name="MSG compliant stepper gripper", category="gripper",
    repo="Source-Robotics/MSG-compliant-AI-stepper-gripper", repo_url="https://github.com/Source-Robotics/MSG-compliant-AI-stepper-gripper", docs_url="",
    licence="CERN-OHL-S-2.0", licence_file="LICENSE (CERN-OHL-S v2)", licence_notes="Strongly reciprocal.", reuse="yes_copyleft",
    dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Repo description: adjustable grip size up to 200 mm, force feedback.",
    motors="One NEMA17: 17HS08-1004S, 17HS16-2004S1 or 17HS24-2104S", drivers="STEPFOC stepper controller (FOC, CAN)",
    reductions="Not read", bearings="See BOM", materials="3D printed", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="Not stated.",
    cad_formats="STEP, STL, 3MF", urdf="yes", mjcf="yes", maturity="low-medium: 70 stars",
    weaknesses="New design; stepper mass at wrist.", mechy_use="Wide-stroke gripper using standard NEMA17.",
    raw_files="raw/msg_gripper/BOM.md; raw/msg_gripper/LICENSE",
    source_url="https://github.com/Source-Robotics/MSG-compliant-AI-stepper-gripper", value_type="datasheet")

add(id="yale_openhand", name="Yale OpenHand (Model T42, O, Q etc.)", category="gripper",
    repo="grablab/openhand-hardware", repo_url="https://github.com/grablab/openhand-hardware", docs_url="https://www.eng.yale.edu/grablab/openhand/",
    licence="CC-BY-NC-3.0", licence_file="LICENSE.md (CC BY-NC 3.0 Unported)", licence_notes="NON-COMMERCIAL. GitHub reports NOASSERTION. Do not use in commercial products.",
    reuse="non_commercial_only",
    dof=None, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Underactuated tendon-driven fingers with compliant flexure joints; specs vary per model.",
    motors="Dynamixel servos (MX/XM series typical)", drivers="Dynamixel bus", reductions="Tendon/pulley", bearings="Flexure joints (cast urethane)",
    materials="3D printed + cast urethane joints/pads", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="Not stated.",
    cad_formats="SLDPRT, SLDASM, STEP, IGES, STL", urdf="no", mjcf="no", maturity="medium: long-lived academic project, 242 stars",
    weaknesses="NC licence; casting process; SolidWorks-centric.", mechy_use="Concept reference for underactuated grippers only.",
    raw_files="", source_url="https://github.com/grablab/openhand-hardware", value_type="datasheet")

add(id="umi_gripper", name="UMI handheld gripper (Universal Manipulation Interface)", category="gripper",
    repo="real-stanford/universal_manipulation_interface", repo_url="https://github.com/real-stanford/universal_manipulation_interface", docs_url="https://umi-gripper.github.io/",
    licence="MIT (code repo)", licence_file="LICENSE (MIT)", licence_notes="Hardware CAD published via project site/Onshape; its licence not read this session.",
    reuse="code_yes_hardware_check",
    dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Handheld data-collection gripper with GoPro + fin-ray fingers; robot version uses WSG-50 or similar.",
    motors="None (handheld) / robot-side commercial gripper", drivers="-", reductions="Rack/linkage", bearings="-",
    materials="3D printed, TPU fin-ray fingers", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="Not read.",
    cad_formats="STL (in repo, assets); Onshape (site)", urdf="no", mjcf="no", maturity="high in research (1.6k stars)",
    weaknesses="Not an actuated gripper; hardware licence unverified.", mechy_use="Fin-ray finger and data-collection reference.",
    raw_files="", source_url="https://github.com/real-stanford/universal_manipulation_interface", value_type="estimate")

add(id="yubi_gripper", name="Toyota YUBI gripper / glove", category="gripper",
    repo="Toyota/yubi-hw", repo_url="https://github.com/Toyota/yubi-hw", docs_url="https://github.com/Toyota/yubi-hw",
    licence="CERN-OHL-W-2.0", licence_file="LICENSE (CERN-OHL-W v2, Copyright 2026 Toyota Motor Corporation)", licence_notes="Weakly reciprocal.",
    reuse="yes_weak_copyleft",
    dof=None, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Gripper + data-collection glove; Dynamixel version BOM included.",
    motors="Dynamixel servos (see BOM)", drivers="Dynamixel bus", reductions="Not read", bearings="See BOM",
    materials="3D printed", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="See raw BOM.",
    cad_formats="STEP, STL", urdf="no", mjcf="no", maturity="low-medium: 185 stars, 2026",
    weaknesses="New; specs not documented in README.", mechy_use="Modern open gripper from a major OEM.",
    raw_files="raw/yubi_gripper/YUBI Gripper_DYNAMIXEL_BOM.md; raw/yubi_gripper/LICENSE",
    source_url="https://github.com/Toyota/yubi-hw", value_type="datasheet")

# ---------------- LEGGED ----------------
add(id="odri_solo12", name="ODRI Solo-8 / Solo-12 quadruped + actuator module", category="legged",
    repo="open-dynamic-robot-initiative/open_robot_actuator_hardware", repo_url="https://github.com/open-dynamic-robot-initiative/open_robot_actuator_hardware", docs_url="https://open-dynamic-robot-initiative.github.io/",
    licence="BSD-3-Clause", licence_file="LICENSE (BSD 3-Clause, NYU + Max Planck)", licence_notes="Permissive.", reuse="yes_permissive",
    dof=12, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=2.2, repeatability_mm=None,
    payload_note="Solo12 ~2.2 kg (from ODRI paper, from memory - verify). Also Bolt biped, TriFinger.",
    motors="T-Motor Antigravity MN4004 KV300 brushless (from memory)", drivers="BLMC uDriver (TI LaunchPad-based) + Master Board (SPI/Ethernet/WiFi)",
    reductions="2-stage timing belt 9:1 (from memory)", bearings="Deep-groove bearings in printed shell (see build docs)",
    materials="3D printed (SLS/FDM) shells", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="Not read.",
    cad_formats="STEP, FCStd, EASM, STL", urdf="yes (robot_properties_solo xacro)", mjcf="no",
    maturity="high in research: 1.5k stars, used by many labs; repo static since 2022",
    weaknesses="Belt transmission compliance; custom electronics; low torque per joint.",
    mechy_use="Best documented open torque-controlled actuator module + leg designs.",
    raw_files="raw/odri_solo12/solo12.urdf.xacro; raw/odri_solo12/leg.xacro; raw/odri_solo12/license.txt",
    source_url="https://open-dynamic-robot-initiative.github.io/", value_type="estimate")

add(id="stanford_pupper", name="Stanford Pupper", category="legged",
    repo="stanfordroboticsclub/StanfordQuadruped", repo_url="https://github.com/stanfordroboticsclub/StanfordQuadruped", docs_url="https://pupper.readthedocs.io/en/latest/",
    licence="MIT (software); hardware docs repo has no LICENSE", licence_file="LICENSE (MIT, StanfordQuadruped)",
    licence_notes="stanfordroboticsclub/Pupper (build docs) has no licence file -> all rights reserved by default.",
    reuse="software_yes_hardware_unclear",
    dof=12, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Docs: 12 servos (3 per leg), Raspberry Pi 4, PS4 controller. StanfordQuadruped README also lists 400 W GIM4305 brushless motors and ~$1000 BOM for a BLDC variant (unclear which robot; not resolved).",
    motors="Hobby servos (3 per leg)", drivers="Raspberry Pi 4 PWM", reductions="Servo internal", bearings="-",
    materials="Carbon fibre plates / printed parts", bom_cost_value=950, bom_cost_currency="USD", bom_cost_note="Docs: about $900-$1000.",
    cad_formats="Not in repo", urdf="no (PyBullet sim exists)", mjcf="no", maturity="high: 1.8k stars; Mini Pupper commercial derivative",
    weaknesses="Servo-based, not torque controlled; hardware licence unclear.", mechy_use="Simple quadruped gait reference.",
    raw_files="", source_url="https://pupper.readthedocs.io/en/latest/", value_type="datasheet")

add(id="mini_pupper", name="Mini Pupper (MangDang)", category="legged",
    repo="mangdangroboticsclub/mini_pupper", repo_url="https://github.com/mangdangroboticsclub/mini_pupper", docs_url="",
    licence="Apache-2.0 (repo)", licence_file="LICENSE (Apache 2.0)", licence_notes="Main repo is README only; hardware CAD in other repos - licence not checked.",
    reuse="check_subrepos", dof=12, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Mini Pupper 4: proprietary 3-DoF coreless smart servo joints.",
    motors="Proprietary coreless smart servos", drivers="Onboard", reductions="Servo internal", bearings="-", materials="Printed/moulded",
    bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="Commercial kit.", cad_formats="Not in main repo", urdf="sim repos (MuJoCo/Isaac)", mjcf="yes (mini_pupper_4_sim, not checked)",
    maturity="medium-high: 1.2k stars, commercial", weaknesses="Actuators proprietary.", mechy_use="Only for sim/RL reference.",
    raw_files="", source_url="https://github.com/mangdangroboticsclub/mini_pupper", value_type="datasheet")

add(id="petoi_opencat", name="Petoi OpenCat (Bittle / Nybble)", category="legged",
    repo="PetoiCamp/OpenCat-Quadruped-Robot", repo_url="https://github.com/PetoiCamp/OpenCat-Quadruped-Robot", docs_url="https://docs.petoi.com/",
    licence="MIT (firmware)", licence_file="LICENSE (MIT)", licence_notes="Firmware/software MIT; Bittle/Nybble frames are commercial products (not open CAD).",
    reuse="software_only", dof=9, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Bittle: 9 DOF (8 leg + 1 head); Nybble: 11 DOF.",
    motors="Petoi P1S/P1L hobby servos", drivers="NyBoard (ATmega328P) or BiBoard (ESP32)", reductions="Servo internal", bearings="-",
    materials="Injection-moulded (commercial)", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="Commercial kit.",
    cad_formats="STL (2 files only)", urdf="yes (bittle_simple.urdf)", mjcf="no", maturity="high: 5.5k stars, commercial",
    weaknesses="No open mechanical CAD; tiny servos.", mechy_use="Servo gait firmware reference.",
    raw_files="", source_url="https://github.com/PetoiCamp/OpenCat-Quadruped-Robot", value_type="datasheet")

add(id="mit_mini_cheetah_sw", name="MIT Mini Cheetah (software) + clones", category="legged",
    repo="mit-biomimetics/Cheetah-Software", repo_url="https://github.com/mit-biomimetics/Cheetah-Software", docs_url="",
    licence="MIT (software)", licence_file="LICENSE (MIT)", licence_notes="Only control software is released; the Mini Cheetah mechanical CAD is NOT in this repo. Ben Katz's actuator design is described in his MIT thesis (2018).",
    reuse="software_only", dof=12, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=9, repeatability_mm=None,
    payload_note="Mini Cheetah ~9 kg, actuators ~17 Nm peak with 6:1 planetary (from Katz thesis/ICRA 2019, from memory - verify).",
    motors="Custom outrunner BLDC (T-motor based) QDD", drivers="Ben Katz motor controller (STM32, CAN)", reductions="6:1 single-stage planetary (from memory)", bearings="Cross-roller / thin-section (from memory)",
    materials="Machined aluminium", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-",
    cad_formats="-", urdf="community (mini-cheetah-gazebo-urdf)", mjcf="community", maturity="very high influence: 3.3k stars; dormant since 2023",
    weaknesses="No official hardware files; clones vary.", mechy_use="MPC/WBC controller reference; actuator concept (6:1 QDD) via OpenTorque/SpryDrive.",
    raw_files="", source_url="https://github.com/mit-biomimetics/Cheetah-Software", value_type="estimate")

# ---------------- ACTUATORS ----------------
add(id="opentorque_actuator", name="OpenTorque Actuator (Gabrael Levine)", category="actuator_qdd",
    repo="G-Levine/OpenTorque-Actuator", repo_url="https://github.com/G-Levine/OpenTorque-Actuator", docs_url="",
    licence="CC-BY-SA-4.0", licence_file="LICENSE (CC BY-SA 4.0 text; GitHub shows NOASSERTION)", licence_notes="Share-alike.", reuse="yes_sharealike",
    dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Printed planetary QDD for legged robots; torque not in repo README (community quotes ~16-20 Nm peak at ~4.4:1, estimate).",
    motors="Herlea X8318S KV100 (or Turnigy Multistar 9235 100KV)", drivers="ODrive (typical; not in BOM)", reductions="Printed planetary (ratio not in README)",
    bearings="THK RA8008 cross-roller bearing; 3x 625ZZ", materials="3D printed; M5x30 dowel pins as planet shafts",
    bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="BOM CSV without prices.",
    cad_formats="STEP, STL", urdf="n/a", mjcf="n/a", maturity="medium: 443 stars; basis for many clones (SpryDrive etc.); unmaintained since 2019",
    weaknesses="Printed gear wear; no published test data in repo.", mechy_use="Template for printed QDD joint.",
    raw_files="raw/opentorque_actuator/Bill of Materials.csv; raw/opentorque_actuator/LICENSE",
    source_url="https://github.com/G-Levine/OpenTorque-Actuator", value_type="datasheet")

add(id="sprydrive", name="SpryDrive QDD actuator", category="actuator_qdd",
    repo="bbokser/sprydrive", repo_url="https://github.com/bbokser/sprydrive", docs_url="",
    licence="MIT", licence_file="LICENSE (MIT)", licence_notes="Permissive.", reuse="yes_permissive",
    dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Output backlash ~0.13 deg (author); 7:1 gear ratio.",
    motors="Herlea X8318S or Turnigy 9235 outrunner", drivers="ODrive / similar FOC", reductions="7:1 VersaPlanetary metal gearbox (modified)",
    bearings="Bearing in printed output plate (see BoM)", materials="PLA/ABS/PETG/nylon printed frame + 6061 Al 0.125 in laser-cut plates",
    bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="See raw BoM xlsx.",
    cad_formats="STEP, DXF", urdf="n/a", mjcf="n/a", maturity="low: 40 stars", weaknesses="Requires machining/arbor press.",
    mechy_use="Metal-gear QDD with measured backlash.", raw_files="raw/sprydrive/SpryDrive BoM.xlsx; raw/sprydrive/LICENSE",
    source_url="https://github.com/bbokser/sprydrive", value_type="datasheet")

add(id="moteus", name="mjbots moteus controllers (r4 / c1 / n1 / x1)", category="actuator_driver",
    repo="mjbots/moteus", repo_url="https://github.com/mjbots/moteus", docs_url="https://mjbots.com/",
    licence="Apache-2.0", licence_file="LICENSE (Apache 2.0)", licence_notes="Firmware and hardware design files.", reuse="yes_permissive",
    dof=None, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="FOC BLDC controller with CAN-FD; r4.11 ~10-44 V, ~100 A peak phase (from memory - verify on mjbots.com).",
    motors="Any BLDC (mj5208, qdd100 etc.)", drivers="itself", reductions="n/a", bearings="n/a", materials="PCB",
    bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="Retail on mjbots.com (not read).",
    cad_formats="KiCad, Eagle (brd/sch), STEP", urdf="n/a", mjcf="n/a", maturity="high: 1.35k stars, active", weaknesses="Proprietary-sourcing of boards; small company.",
    mechy_use="Driver choice for QDD joints.", raw_files="", source_url="https://github.com/mjbots/moteus", value_type="estimate")

add(id="odrive", name="ODrive (v3.6 open hardware; S1/Pro firmware closed)", category="actuator_driver",
    repo="odriverobotics/ODrive", repo_url="https://github.com/odriverobotics/ODrive", docs_url="https://docs.odriverobotics.com/",
    licence="MIT", licence_file="LICENSE.md (MIT)", licence_notes="Repo = v3.x firmware/tools. ODrive S1/Pro are closed hardware/firmware.",
    reuse="yes_permissive (v3 only)", dof=None, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="v3.6: dual-axis, 24/56 V variants (from memory).", motors="Any BLDC", drivers="itself", reductions="n/a", bearings="n/a", materials="PCB",
    bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-", cad_formats="(v3 hardware files elsewhere)", urdf="n/a", mjcf="n/a",
    maturity="very high: 3.8k stars", weaknesses="v3 discontinued; new hardware closed.", mechy_use="Common driver in QDD/capstan projects.",
    raw_files="", source_url="https://github.com/odriverobotics/ODrive", value_type="estimate")

add(id="xrobots_cycloidal", name="XRobots cycloidal drive", category="actuator_cycloidal",
    repo="XRobots/CycloidalDrive", repo_url="https://github.com/XRobots/CycloidalDrive", docs_url="",
    licence="MIT", licence_file="LICENSE (MIT)", licence_notes="Permissive.", reuse="yes_permissive",
    dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="STEP files only, no specs.", motors="Not stated", drivers="-", reductions="Cycloidal (ratio in CAD)", bearings="-",
    materials="3D printed", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-", cad_formats="STEP", urdf="n/a", mjcf="n/a",
    maturity="medium: 226 stars (James Bruton)", weaknesses="No docs.", mechy_use="Printable cycloid geometry.",
    raw_files="", source_url="https://github.com/XRobots/CycloidalDrive", value_type="datasheet")

add(id="sirojudin_cycloidal", name="3D-printed cycloidal actuator (sirojudinMunir)", category="actuator_cycloidal",
    repo="sirojudinMunir/3D-printed-cycloidal-actuator", repo_url="https://github.com/sirojudinMunir/3D-printed-cycloidal-actuator", docs_url="",
    licence="MIT", licence_file="LICENSE (MIT)", licence_notes="Permissive.", reuse="yes_permissive",
    dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="STL + xlsx; specs not in README.", motors="BLDC (not stated)", drivers="-", reductions="Cycloidal", bearings="-",
    materials="3D printed", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-", cad_formats="STL", urdf="n/a", mjcf="n/a",
    maturity="low-medium: 215 stars", weaknesses="STL only (no editable CAD).", mechy_use="Printable cycloidal actuator.",
    raw_files="", source_url="https://github.com/sirojudinMunir/3D-printed-cycloidal-actuator", value_type="datasheet")

add(id="aaedmusa_internal_cycloidal", name="Internal cycloidal actuator (Aaed Musa)", category="actuator_cycloidal",
    repo="aaedmusa/Internal-Cycloidal-Actuator", repo_url="https://github.com/aaedmusa/Internal-Cycloidal-Actuator", docs_url="",
    licence="NONE (no LICENSE file)", licence_file="none", licence_notes="All rights reserved by default. Reference/idea only; do not copy files.",
    reuse="reference_only", dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Compact cycloidal inside BLDC for legged robots.", motors="BLDC", drivers="ODrive (typical)", reductions="Cycloidal", bearings="-",
    materials="3D printed", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="BOM.xlsx in repo.", cad_formats="STEP (zip)", urdf="n/a", mjcf="n/a",
    maturity="medium: 315 stars", weaknesses="No licence.", mechy_use="Idea reference only.", raw_files="",
    source_url="https://github.com/aaedmusa/Internal-Cycloidal-Actuator", value_type="datasheet")

add(id="aaedmusa_capstan", name="Capstan drive test stand (Aaed Musa)", category="actuator_capstan",
    repo="aaedmusa/Capstan-Drive", repo_url="https://github.com/aaedmusa/Capstan-Drive", docs_url="",
    licence="NONE (no LICENSE file)", licence_file="none", licence_notes="All rights reserved by default. Reference only.",
    reuse="reference_only", dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=0.852, repeatability_mm=None,
    payload_note="Rope reducer: low backlash, high transparency; 852 g, PLA.", motors="Eagle Power 90KV BLDC", drivers="ODrive S1",
    reductions="Capstan (rope) - ratio in CAD", bearings="-", materials="PLA + rope", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="BOM xlsx in repo.",
    cad_formats="STEP", urdf="n/a", mjcf="n/a", maturity="medium: 654 stars", weaknesses="No licence; rope creep/tensioning.",
    mechy_use="Concept reference for backlash-free reducer.", raw_files="", source_url="https://github.com/aaedmusa/Capstan-Drive", value_type="datasheet")

add(id="wolf_actuator", name="WOLF Wolfrom planetary actuator (Anthrobotics)", category="actuator_planetary",
    repo="Anthrobotics/wolf-actuator", repo_url="https://github.com/Anthrobotics/wolf-actuator", docs_url="",
    licence="CC-BY-SA-4.0", licence_file="LICENSE (CC BY-SA 4.0)", licence_notes="Share-alike.", reuse="yes_sharealike",
    dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=1.55, repeatability_mm=None,
    payload_note="Theoretical 80 Nm cont / 120 Nm peak; tested peak 90 Nm; earlier test ~40.8 Nm continuous; 24-52 V; D 202.3 mm x H 67 mm.",
    motors="Eaglepower 8318 100KV BLDC", drivers="Not stated (ODrive-class)", reductions="Wolfrom planetary, 2 ring gears, 12 planets, no carrier",
    bearings="2x printed modular bearings (WOLF edition)", materials="Polysonic PLA (fully printed test unit)",
    bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-", cad_formats="STEP, STL", urdf="n/a", mjcf="n/a",
    maturity="low: 77 stars", weaknesses="Printed bearings; Wolfrom low efficiency/backdrivability.", mechy_use="High-ratio printed actuator with measured torque.",
    raw_files="", source_url="https://github.com/Anthrobotics/wolf-actuator", value_type="datasheet")

add(id="hassler_strain_wave", name="3D printed strain wave gear (Hassler Engineering)", category="actuator_harmonic",
    repo="HasslerEngineering/3D-Printed-Strain-Wave-Gear", repo_url="https://github.com/HasslerEngineering/3D-Printed-Strain-Wave-Gear", docs_url="https://hackaday.io/project/120377-3d-printed-strain-wave-gear",
    licence="NONE (no LICENSE file)", licence_file="none", licence_notes="All rights reserved by default. Reference only.",
    reuse="reference_only", dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Hackaday Prize 2018 entry.", motors="NEMA17 (typical)", drivers="-", reductions="Strain wave", bearings="-",
    materials="3D printed (flexspline TPU/nylon typical)", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-",
    cad_formats="SLDPRT, SLDASM, STEP, STL", urdf="n/a", mjcf="n/a", maturity="low: 11 stars", weaknesses="No licence; printed flexspline fatigue.",
    mechy_use="Concept only.", raw_files="", source_url="https://github.com/HasslerEngineering/3D-Printed-Strain-Wave-Gear", value_type="datasheet")

add(id="matt_ceck_strain_wave", name="StrainWaveDrive (Matt-Ceck63)", category="actuator_harmonic",
    repo="Matt-Ceck63/StrainWaveDrive", repo_url="https://github.com/Matt-Ceck63/StrainWaveDrive", docs_url="",
    licence="NONE (no LICENSE file)", licence_file="none", licence_notes="All rights reserved by default.", reuse="reference_only",
    dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Ratio 100:1 (200-tooth flexspline vs 202-tooth ring).", motors="Stepper", drivers="-", reductions="Strain wave 100:1", bearings="-",
    materials="3D printed", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-", cad_formats="F3D, STEP, STL", urdf="n/a", mjcf="n/a",
    maturity="low: 6 stars", weaknesses="No licence; author notes flexspline issues.", mechy_use="Concept only.", raw_files="",
    source_url="https://github.com/Matt-Ceck63/StrainWaveDrive", value_type="datasheet")

add(id="galileo_planetary", name="Galileo planetary extruder gearsets (Voron)", category="actuator_planetary",
    repo="JaredC01/Galileo", repo_url="https://github.com/JaredC01/Galileo", docs_url="",
    licence="GPL-3.0", licence_file="LICENSE (GPL-3.0)", licence_notes="Copyleft.", reuse="yes_copyleft",
    dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Compact printed planetary for extruders, 7.5:1 (Clockwork variant).", motors="NEMA14/17 pancake", drivers="-", reductions="Planetary 7.5:1",
    bearings="-", materials="3D printed (ABS/ASA)", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-", cad_formats="F3D, STEP, STL", urdf="n/a", mjcf="n/a",
    maturity="medium: 292 stars", weaknesses="Low torque (extruder scale).", mechy_use="Small printed planetary for grippers/wrists.",
    raw_files="", source_url="https://github.com/JaredC01/Galileo", value_type="datasheet")

# ---------------- PAN-TILT, LAUNCHERS ----------------
add(id="isaac879_pan_tilt", name="isaac879 Pan-Tilt-Slider mount", category="pan_tilt",
    repo="isaac879/Pan-Tilt-Mount", repo_url="https://github.com/isaac879/Pan-Tilt-Mount", docs_url="",
    licence="MIT", licence_file="LICENSE (MIT)", licence_notes="Permissive.", reuse="yes_permissive",
    dof=3, reach_mm=None, payload_claimed_kg=1.0, payload_measured_kg=1.0, mass_kg=None, repeatability_mm=None,
    payload_note="Author tested 'just over 1 kg' (Canon 250D + lens + mic). Speeds ~20 deg/s pan, 15 deg/s tilt, 20 mm/s slider at 1/16 step.",
    motors="3x NEMA17 steppers", drivers="TMC2208, Arduino Nano, 12 V or 3S LiPo", reductions="GT2 belts (36T slider pulley); pan/tilt belt ratios in CAD",
    bearings="See CAD", materials="3D printed + 2040 V-slot", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-",
    cad_formats="STEP, STL", urdf="no", mjcf="no", maturity="medium: 514 stars; dormant since 2021", weaknesses="Slow (MCU-limited); open loop with hall homing.",
    mechy_use="Belt-driven pan-tilt baseline with hall-effect homing.", raw_files="",
    source_url="https://github.com/isaac879/Pan-Tilt-Mount", value_type="datasheet")

add(id="aimy_ball_launcher", name="AIMY table tennis ball launcher (MPI-IS)", category="launcher",
    repo="intelligent-soft-robots/ball_launcher_hardware", repo_url="https://github.com/intelligent-soft-robots/ball_launcher_hardware", docs_url="",
    licence="BSD-3-Clause", licence_file="LICENSE (BSD 3-Clause)", licence_notes="Permissive.", reuse="yes_permissive",
    dof=None, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Open-source table-tennis ball launcher (three-wheel type, from memory); see paper/PDF drawings in repo.",
    motors="BLDC wheel motors (not read)", drivers="-", reductions="Direct-drive flywheels (estimate)", bearings="-", materials="Machined + printed",
    bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-", cad_formats="STEP, PDF drawings", urdf="no", mjcf="no",
    maturity="low: 11 stars, research lab", weaknesses="Sparse docs.", mechy_use="Only reputable open launcher found.", raw_files="",
    source_url="https://github.com/intelligent-soft-robots/ball_launcher_hardware", value_type="estimate")

add(id="bjr_juggling_robot", name="BJR ball juggling robot (EverydayDynamics)", category="catcher",
    repo="EverydayDynamics/bjr", repo_url="https://github.com/EverydayDynamics/bjr", docs_url="",
    licence="MIXED: software MIT/Apache-2.0; hardware no licence", licence_file="software/*/LICENSE-MIT, LICENSE-APACHE (no top-level LICENSE)",
    licence_notes="Mechanical STEP and KiCad files have no licence -> reference only.", reuse="software_only",
    dof=None, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Ball juggling robot (catch + throw); Rust control.", motors="Not read", drivers="Custom KiCad boards", reductions="-", bearings="-", materials="-",
    bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-", cad_formats="STEP, STP, KiCad", urdf="no", mjcf="no",
    maturity="low: 20 stars", weaknesses="Little docs; hardware unlicensed.", mechy_use="Catch/throw dynamics reference.", raw_files="",
    source_url="https://github.com/EverydayDynamics/bjr", value_type="datasheet")

# ---------------- MOTION SYSTEMS ----------------
add(id="voron_2_4", name="Voron 2.4 (CoreXY, flying gantry)", category="motion_corexy",
    repo="VoronDesign/Voron-2", repo_url="https://github.com/VoronDesign/Voron-2", docs_url="https://docs.vorondesign.com/",
    licence="GPL-3.0", licence_file="LICENSE (GPL-3.0)", licence_notes="Copyleft; Voron name/logo policies apply.", reuse="yes_copyleft",
    dof=3, reach_mm=350, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Build volumes 250/300/350 mm cube (from memory). reach_mm = largest XY travel.",
    motors="NEMA17 steppers (2x A/B 0.9 deg recommended, 4x Z)", drivers="TMC2209/5160 on Klipper boards", reductions="GT2 belts 9 mm (AB), 6 mm (Z), 80:16 Z gear (from memory)",
    bearings="MGN9/MGN12 linear rails, F695 idler bearings", materials="ABS/ASA printed + 2020 extrusion",
    bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="Typically $1,000-1,500 (estimate).", cad_formats="F3D, STEP, STL, DXF", urdf="no", mjcf="no",
    maturity="very high: 4.6k stars, huge community", weaknesses="Many parts; quad gantry levelling complexity.", mechy_use="Proven CoreXY belt path + rail sizing.",
    raw_files="", source_url="https://github.com/VoronDesign/Voron-2", value_type="estimate")

add(id="voron_trident", name="Voron Trident (CoreXY, 3-point Z)", category="motion_corexy",
    repo="VoronDesign/Voron-Trident", repo_url="https://github.com/VoronDesign/Voron-Trident", docs_url="https://docs.vorondesign.com/",
    licence="GPL-3.0", licence_file="LICENSE (GPL-3.0 text; GitHub API reports none)", licence_notes="Verified by reading LICENSE.", reuse="yes_copyleft",
    dof=3, reach_mm=350, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="250/300/350 mm variants (from memory).", motors="NEMA17 (2 AB + 3 Z lead-screw)", drivers="TMC2209", reductions="GT2 belts; T8 lead screws on Z",
    bearings="MGN9/MGN12 rails", materials="ABS/ASA + 2020", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-",
    cad_formats="F3D, STEP, STL, DXF", urdf="no", mjcf="no", maturity="high: 1.1k stars", weaknesses="-", mechy_use="Simpler fixed-gantry CoreXY.",
    raw_files="", source_url="https://github.com/VoronDesign/Voron-Trident", value_type="estimate")

add(id="voron_0", name="Voron 0.2 (small CoreXY)", category="motion_corexy",
    repo="VoronDesign/Voron-0", repo_url="https://github.com/VoronDesign/Voron-0", docs_url="https://docs.vorondesign.com/",
    licence="GPL-3.0", licence_file="LICENSE (GPL-3.0)", licence_notes="Copyleft.", reuse="yes_copyleft",
    dof=3, reach_mm=120, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="120 mm cube (from memory).", motors="NEMA14/17", drivers="TMC2209", reductions="GT2 belts", bearings="MGN7/MGN9 rails",
    materials="ABS + 1515 extrusion", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-", cad_formats="F3D, STEP, STL, DXF", urdf="no", mjcf="no",
    maturity="high: 1.7k stars", weaknesses="Small volume.", mechy_use="Compact CoreXY stage reference.", raw_files="",
    source_url="https://github.com/VoronDesign/Voron-0", value_type="estimate")

add(id="prusa_mk3s", name="Original Prusa i3 MK3S (bed-slinger Cartesian)", category="motion_cartesian",
    repo="prusa3d/Original-Prusa-i3", repo_url="https://github.com/prusa3d/Original-Prusa-i3", docs_url="https://help.prusa3d.com/",
    licence="GPL-2.0 (LICENSE file text)", licence_file="LICENSE (GPL v2)", licence_notes="Prusa trademark not licensed.", reuse="yes_copyleft",
    dof=3, reach_mm=250, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Build volume 250x210x210 mm (from memory).", motors="NEMA17 steppers", drivers="TMC2130 (Einsy Rambo)", reductions="GT2 belts XY, TR8 lead screws Z",
    bearings="LM8UU linear bearings on 8 mm rods", materials="PETG printed + aluminium frame", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-",
    cad_formats="SCAD, STEP, STL, DXF", urdf="no", mjcf="no", maturity="very high (1.7k stars; millions of machines)", weaknesses="Bed-slinger limits speed.",
    mechy_use="Parametric OpenSCAD parts; simple Cartesian.", raw_files="", source_url="https://github.com/prusa3d/Original-Prusa-i3", value_type="estimate")

add(id="mpcnc_primo", name="MPCNC Primo (V1 Engineering)", category="motion_cnc",
    repo="V1EngineeringInc/MPCNC_Primo", repo_url="https://github.com/V1EngineeringInc/MPCNC_Primo", docs_url="https://www.v1e.com/",
    licence="CC-BY-NC-SA-4.0 (stated in README; no LICENSE file)", licence_file="README licence section", licence_notes="NON-COMMERCIAL; V1 grants extra permissions on its licence page (e.g. selling machines you build).",
    reuse="non_commercial_only", dof=3, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Size set by user-cut conduit tubes.", motors="NEMA17 steppers", drivers="SKR Pro / Rambo", reductions="GT2 belts XY, T8 lead screws Z",
    bearings="608 bearings rolling on 25.4 mm conduit", materials="PLA/PETG printed + steel/stainless conduit", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-",
    cad_formats="STL", urdf="no", mjcf="no", maturity="high community (V1 forum)", weaknesses="Tube flex limits rigidity; NC licence.",
    mechy_use="Low-cost gantry idea only.", raw_files="", source_url="https://github.com/V1EngineeringInc/MPCNC_Primo", value_type="datasheet")

add(id="printnc", name="PrintNC (steel tube CNC)", category="motion_cnc",
    repo="threedesigns/printNC", repo_url="https://github.com/threedesigns/printNC", docs_url="https://wiki.printnc.info/",
    licence="CC-BY-4.0", licence_file="LICENSE.md (CC BY 4.0)", licence_notes="Attribution only; commercial OK.", reuse="yes_permissive",
    dof=3, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="Epoxy-filled steel box frame; size configurable.", motors="NEMA23/34 closed-loop steppers (typical)", drivers="-", reductions="Ball screws (SFU1605/1610)",
    bearings="HGR20 linear rails (typical)", materials="Welded/bolted steel tube + printed brackets", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-",
    cad_formats="STL, 3MF (more on wiki/Onshape)", urdf="no", mjcf="no", maturity="medium: 277 stars, active community", weaknesses="Heavy; requires drilling steel.",
    mechy_use="Rigid frame reference.", raw_files="", source_url="https://github.com/threedesigns/printNC", value_type="estimate")

add(id="simplecore", name="SimpleCore DIY CoreXY", category="motion_corexy",
    repo="rolohaun/SimpleCore", repo_url="https://github.com/rolohaun/SimpleCore", docs_url="",
    licence="NONE (no LICENSE file)", licence_file="none", licence_notes="All rights reserved by default.", reuse="reference_only",
    dof=3, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="-", motors="NEMA17", drivers="Klipper boards", reductions="GT2 belts", bearings="Linear rails", materials="Printed + extrusion",
    bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="-", cad_formats="F3Z, STEP, STL, 3MF", urdf="no", mjcf="no", maturity="low-medium: 299 stars",
    weaknesses="No licence.", mechy_use="Use Voron instead.", raw_files="", source_url="https://github.com/rolohaun/SimpleCore", value_type="estimate")

# conveyors: none found, recorded as gap row
add(id="conveyor_gap", name="Conveyor (no reputable open design found)", category="conveyor",
    repo="", repo_url="", docs_url="",
    licence="n/a", licence_file="none", licence_notes="GitHub searches returned only student Arduino projects with 0-1 stars. Use standard parts (2020 extrusion, GT2/flat belt, 608 idlers) and design in-house, or search Printables/Thingiverse with licence check.",
    reuse="n/a", dof=1, reach_mm=None, payload_claimed_kg=None, payload_measured_kg=None, mass_kg=None, repeatability_mm=None,
    payload_note="GAP", motors="", drivers="", reductions="", bearings="", materials="", bom_cost_value=None, bom_cost_currency="USD", bom_cost_note="",
    cad_formats="", urdf="no", mjcf="no", maturity="none", weaknesses="", mechy_use="Design from standard parts.", raw_files="",
    source_url="https://github.com/search?q=conveyor+belt+arduino", value_type="estimate")

COLS = ["id","name","category","repo_url","docs_url","licence","licence_file","licence_notes","reuse","dof","reach_mm","payload_claimed_kg",
        "payload_measured_kg","mass_kg","repeatability_mm","payload_note","motors","drivers","reductions","bearings","materials","bom_cost_value",
        "bom_cost_currency","bom_cost_note","cad_formats","urdf","mjcf","github_stars","github_forks","last_push","maturity","known_weaknesses","mechy_use",
        "raw_files","source_url","value_type","checked_date"]

os.makedirs(os.path.join(OUT, "designs"), exist_ok=True)
with open(os.path.join(OUT, "designs.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS)
    w.writeheader()
    for r in R:
        m = meta(r["repo"]) if r["repo"] else {}
        row = dict(r)
        row["github_stars"] = m.get("stars", "")
        row["github_forks"] = m.get("forks", "")
        row["last_push"] = (m.get("pushed") or "")[:10]
        row["known_weaknesses"] = r["weaknesses"]
        row["checked_date"] = TODAY
        w.writerow({k: ("" if row.get(k) is None else row.get(k)) for k in COLS})
        j = dict(row)
        j.pop("weaknesses", None)
        j["github_license_spdx"] = m.get("spdx")
        j["github_file_extensions"] = m.get("ext")
        j["github_description"] = m.get("desc")
        j["units"] = {"reach_mm": "mm", "payload_claimed_kg": "kg", "payload_measured_kg": "kg", "mass_kg": "kg", "repeatability_mm": "mm"}
        json.dump(j, open(os.path.join(OUT, "designs", r["id"] + ".json"), "w"), indent=1, ensure_ascii=False)
print(len(R), "designs written")
