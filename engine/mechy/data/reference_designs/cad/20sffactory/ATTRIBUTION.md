# Attribution

This directory vendors parts of the **20sffactory Community Robot Arm** — the Robot Arm v1.2 by
20sffactory (community robot arm, "robotArm"), original design by **Florin Tobler**.

- Source: github.com/20sffactory/community_robot_arm (vendored at commit `6c2f573`)
- License: **CC BY 4.0** (see LICENSE). CAD files and docs are free to share and adapt with
  attribution. The vendor Arduino firmware is GPL-3.0 — mechy's generated firmware is written
  from scratch and only shares the pin mapping and homing sequence.
- `stl/`: the printable STLs the arm uses (140 mm shank kit variants where the kit offers them);
  the rail module parts are excluded.
- `stl/pleuel_bend_upper_140.stl` is **BAM-made**: the vendor 140 mm
  kit ships no upper levelling link, so this part was stretched from the vendor 120 mm part. Same
  license (CC BY 4.0).
- `assembly.json`: tessellated solids of the vendor `robot_arm.step` (name, centre, volume,
  quantized vertices/triangles, pivot cylinders), produced by `make_assembly_json.py` from BAM's
  `step_parts.json`.
