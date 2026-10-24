"""Validator for the standard_parts dataset (stdlib only). Run: python3 -I check.py"""
import csv
import glob
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VALUE_TYPES = {"datasheet", "standard", "handbook_typical", "estimate"}
NONNEG_SUFFIX = ("_mm", "_kN", "_N", "_kg", "_kg_per_m", "_MPa", "_GPa", "_rpm", "_mm2", "_mm4", "_mm3", "_Nm",
                 "_N_per_mm", "_um_abs")
errors = []


def err(msg):
    errors.append(msg)


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def check_csv(path):
    name = os.path.basename(path)
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        err(f"{name}: no rows")
        return 0
    cols = rows[0].keys()
    for c in ("source_url", "value_type"):
        if c not in cols:
            err(f"{name}: missing column {c}")
    for i, r in enumerate(rows, 2):
        if r.get("value_type") not in VALUE_TYPES:
            err(f"{name}:{i} bad value_type {r.get('value_type')!r}")
        if not r.get("source_url"):
            err(f"{name}:{i} empty source_url")
        for c, v in r.items():
            x = num(v)
            if x is None or "dev" in c or "deviation" in c or c.startswith(("temp_", "g6_", "h6_")):
                continue
            if c.endswith(NONNEG_SUFFIX) and x < 0:
                err(f"{name}:{i} negative {c}={v}")
        g = lambda c: num(r.get(c))
        # geometry / physics sanity
        if g("d_mm") is not None and g("D_mm") is not None and not g("d_mm") < g("D_mm"):
            err(f"{name}:{i} bore >= OD")
        if g("C_kN") and g("C0_kN") and not (0.2 < g("C0_kN") / g("C_kN") < 3):
            err(f"{name}:{i} odd C0/C ratio")
        if g("flange_D_mm") and not g("flange_D_mm") > g("D_mm"):
            err(f"{name}:{i} flange not larger than OD")
        if g("tensile_strength_min_MPa") and g("yield_strength_min_MPa") > g("tensile_strength_min_MPa"):
            err(f"{name}:{i} yield > UTS")
        if g("proof_stress_MPa") and g("proof_stress_MPa") > g("yield_strength_min_MPa"):
            err(f"{name}:{i} proof > yield")
        if name.startswith("threads"):
            d, P = g("d_mm"), g("pitch_mm")
            if not (g("bolt_minor_dia_d3_mm") < g("nut_minor_dia_D1_mm") < g("pitch_dia_d2_mm") < d):
                err(f"{name}:{i} thread diameters out of order")
            if not (d - 1.3 * P < g("tap_drill_mm") < d - 0.8 * P):
                err(f"{name}:{i} tap drill implausible")
        if name.startswith("fasteners_iso4762"):
            if not (g("clearance_close_mm") < g("clearance_normal_mm") < g("clearance_loose_mm")):
                err(f"{name}:{i} clearance order")
            if not (g("proof_load_8_8_kN") < g("proof_load_10_9_kN") < g("proof_load_12_9_kN")):
                err(f"{name}:{i} proof load order")
            if not g("counterbore_dia_mm") > g("head_dia_dk_mm"):
                err(f"{name}:{i} counterbore smaller than head")
        if name == "timing_pulleys.csv":
            pd = g("teeth") * g("pitch_mm") / math.pi
            if abs(pd - g("pitch_dia_mm")) > 0.01 or not g("outside_dia_mm") < pd:
                err(f"{name}:{i} pulley diameter mismatch")
        if name == "timing_belt_closed_loops.csv":
            if abs(g("pitch_length_mm") / g("pitch_mm") - g("teeth")) > 1e-6:
                err(f"{name}:{i} length not multiple of pitch")
        if name.startswith("extrusions"):
            if abs(g("area_mm2") * 2.7e-3 - g("mass_kg_per_m")) > 0.15 * g("mass_kg_per_m"):
                err(f"{name}:{i} mass/area mismatch")
            solid = g("width_mm") * g("height_mm") ** 3 / 12
            if not 0.2 * solid < g("Ixx_mm4") < solid:
                err(f"{name}:{i} Ixx implausible")
        if name.startswith("retaining_rings"):
            ext = r["type"].startswith("external")
            if ext != (g("groove_dia_d2_mm") < g("nominal_dia_d1_mm")):
                err(f"{name}:{i} groove dia wrong side")
            if not g("groove_width_m_mm") > g("ring_thickness_s_mm"):
                err(f"{name}:{i} groove narrower than ring")
        if name.startswith("keys") and not g("hub_keyway_depth_t2_mm") < g("key_height_h_mm") \
                > g("shaft_keyway_depth_t1_mm"):
            err(f"{name}:{i} keyway depth >= key height")
        if name == "linear_rails.csv" and not g("C0_kN") >= g("C_kN") * 0.9:
            err(f"{name}:{i} C0 < C")
        if name.startswith("lead_screws") and not (0 < g("efficiency_mu0_2") < g("efficiency_mu0_1") < 1):
            err(f"{name}:{i} efficiency order")
        if name.startswith("springs_compression") and not g("solid_length_mm") < g("free_length_mm"):
            err(f"{name}:{i} solid >= free length")
        if name.startswith("spring_wire") and not g("G_GPa") < g("E_GPa"):
            err(f"{name}:{i} G >= E")
        if g("mass_kg") is not None and g("mass_kg") <= 0:
            err(f"{name}:{i} non-positive mass")
    return len(rows)


def check_iso286(path):
    with open(path) as f:
        d = json.load(f)
    n = len(d["size_ranges_mm"])
    for k in ("source_url", "value_type", "holes", "shafts", "IT_grades_um"):
        if k not in d:
            err(f"iso286: missing {k}")
    if d.get("value_type") not in VALUE_TYPES:
        err("iso286: bad value_type")
    for g, vals in d["IT_grades_um"].items():
        if len(vals) != n or vals != sorted(vals):
            err(f"iso286: {g} not monotonic / wrong length")
    grades = sorted(d["IT_grades_um"], key=lambda s: int(s[2:]))
    for a, b in zip(grades, grades[1:]):
        if any(x >= y for x, y in zip(d["IT_grades_um"][a], d["IT_grades_um"][b])):
            err(f"iso286: {a} not < {b}")
    count = 0
    for group in ("holes", "shafts"):
        for code, lims in d[group].items():
            if len(lims) != n:
                err(f"iso286: {code} wrong length")
            for i, (up, lo) in enumerate(lims):
                count += 1
                if not up > lo:
                    err(f"iso286: {code} range {i} upper <= lower")
                grade = "IT" + code.lstrip("ABCDEFGHJKLMNPRSTUVXYZabcdefghjklmnprstuvxyz").lstrip("s")
                it = d["IT_grades_um"].get(grade)
                if it and abs((up - lo) - it[i]) > 1e-9:
                    err(f"iso286: {code} range {i} width != {grade}")
    # spot checks against printed ISO 286-2 tables
    idx = 4  # 18-30 mm
    expect = {"g6": [-7, -20], "p6": [35, 22], "k6": [15, 2], "f7": [-20, -41], "s6": [48, 35]}
    for c, v in expect.items():
        if d["shafts"][c][idx] != v:
            err(f"iso286: {c} 18-30 expected {v} got {d['shafts'][c][idx]}")
    if d["holes"]["H7"][idx] != [21, 0]:
        err("iso286: H7 18-30 expected [21,0]")
    return count


def main():
    total = {}
    for p in sorted(glob.glob(os.path.join(HERE, "*.csv"))):
        total[os.path.basename(p)] = check_csv(p)
    js = os.path.join(HERE, "iso286_fits.json")
    if os.path.exists(js):
        total["iso286_fits.json (limit entries)"] = check_iso286(js)
    else:
        err("iso286_fits.json missing")
    for k, v in total.items():
        print(f"  {k}: {v}")
    size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(HERE) for f in fs)
    if size > 20e6:
        err(f"folder too large: {size} bytes")
    if errors:
        for e in errors:
            print("  ERROR", e)
        print(f"FAIL ({len(errors)} errors)")
        raise SystemExit(1)
    print(f"PASS ({len(total)} files, {sum(total.values())} rows/entries, {size/1e3:.0f} kB)")


if __name__ == "__main__":
    main()
