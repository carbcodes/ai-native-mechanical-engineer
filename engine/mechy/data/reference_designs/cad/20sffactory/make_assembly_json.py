"""Regenerate assembly.json from BAM's step_parts.json (run once, not at build time):

    python3 make_assembly_json.py <path-to>/step_parts.json

step_parts.json is the tessellation of the vendor robot_arm.step (20sffactory Community Robot Arm,
CC BY 4.0) with every solid named by matching its volume/bbox to the vendor STLs and its cylindrical
faces listed (exact pivot axes). This script keeps each solid's name, centre, volume and mesh
(quantized to 0.02 mm, int16, base64) plus the named pivot cylinders, and drops everything else
(case/enclosure parts are filtered out by name match in ref_arm.py anyway — here we keep every
solid that carries or neighbours a named pivot, plus the named STLs' matches).
"""
import base64
import json
import struct
import sys


def pack(p):
    v = p["v"]
    lo = [min(c[i] for c in v) for i in range(3)]
    q = [int(round((c[i] - lo[i]) / 0.02)) for c in v for i in range(3)]
    t = [k for tri in p["t"] for k in tri]
    return {
        "name": p["name"], "vol": p["vol"], "center": p["center"], "cyl": p.get("cyl", []),
        "min": lo, "v": base64.b64encode(struct.pack(f"<{len(q)}H", *q)).decode(),
        "t": base64.b64encode(struct.pack(f"<{len(t)}I", *t)).decode(),
    }


def main(src, dst):
    P = json.load(open(src))
    solids = [pack(p) for p in P]
    json.dump({"meta": {"source": "20sffactory robot_arm.step (commit 6c2f573), tessellated via "
                                "FreeCAD 0.5/0.5 deflection; vertices quantized 0.02 mm",
                        "units": "mm",
                        "frame": "z up; pitch joint axes along +/-y; yaw axis vertical (z)",
                        "pack": "v = uint16[(x-minx)/0.02, ...] per vertex; t = uint32 tri indices"},
               "solids": solids}, open(dst, "w"), separators=(",", ":"))
    print(len(solids), "solids")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "assembly.json")
