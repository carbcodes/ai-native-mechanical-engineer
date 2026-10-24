"""Validator for the materials dataset. Stdlib only. Run: python3 -I check.py"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VALUE_TYPES = {"datasheet", "standard", "handbook_typical", "estimate"}
errors = []


def err(f, row, msg):
    errors.append(f"{f}:{row}: {msg}")


def num(v):
    if v is None or v == "":
        return None
    return float(v)


def load(name, required):
    path = os.path.join(HERE, name)
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    with open(path, newline="", encoding="utf-8") as fh:
        header = next(csv.reader(fh))
    for c in required + ["source_url", "value_type"]:
        if c not in header:
            err(name, 1, f"missing column {c}")
    ids = set()
    for i, r in enumerate(rows, start=2):
        if None in r or any(v is None for v in r.values()):
            err(name, i, "wrong number of fields")
            continue
        if r.get("id") in ids:
            err(name, i, f"duplicate id {r.get('id')}")
        ids.add(r.get("id"))
        if r["value_type"] not in VALUE_TYPES:
            err(name, i, f"bad value_type {r['value_type']}")
        if not r["source_url"].startswith("http"):
            err(name, i, "source_url not a URL")
        for c in header:
            if c.endswith(("_MPa", "_GPa", "_C", "_kg_m3", "_pct", "_K", "_V", "_s", "_V_vs_SCE", "_m2")) or c in ("poisson_ratio", "mu_static", "mu_kinetic", "hardness_value", "cost_tier"):
                try:
                    num(r[c])
                except ValueError:
                    err(name, i, f"{c} not numeric: {r[c]!r}")
    return rows


def rng(name, i, r, col, lo, hi):
    v = num(r[col])
    if v is not None and not (lo <= v <= hi):
        err(name, i, f"{col}={v} outside [{lo},{hi}]")


def check_materials():
    f = "materials.csv"
    req = ["id", "name", "category", "density_kg_m3", "youngs_modulus_GPa", "shear_modulus_GPa", "poisson_ratio",
           "yield_strength_MPa", "uts_MPa", "elongation_pct", "hardness_value", "hardness_scale",
           "endurance_limit_MPa", "cte_um_per_m_K", "thermal_conductivity_W_per_m_K", "max_service_temp_C",
           "hdt_0_45MPa_C", "hdt_1_8MPa_C", "tg_C", "melting_point_C", "cost_tier", "notes"]
    rows = load(f, req)
    for i, r in enumerate(rows, start=2):
        if None in r:
            continue
        if num(r["density_kg_m3"]) is None:
            err(f, i, "density required")
        rng(f, i, r, "density_kg_m3", 50, 23000)
        rng(f, i, r, "youngs_modulus_GPa", 0.0005, 1200)
        rng(f, i, r, "poisson_ratio", 0.0, 0.5)
        rng(f, i, r, "elongation_pct", 0, 1000)
        rng(f, i, r, "cost_tier", 1, 5)
        rng(f, i, r, "thermal_conductivity_W_per_m_K", 0.01, 500)
        rng(f, i, r, "cte_um_per_m_K", -15, 400)
        for c in ("yield_strength_MPa", "uts_MPa", "flexural_strength_MPa", "compressive_strength_MPa", "endurance_limit_MPa"):
            rng(f, i, r, c, 0, 7000)
        y, u, e = num(r["yield_strength_MPa"]), num(r["uts_MPa"]), num(r["endurance_limit_MPa"])
        if y is not None and u is not None and y > u * 1.001:
            err(f, i, f"yield {y} > UTS {u}")
        if e is not None and u is not None and e > u:
            err(f, i, f"endurance {e} > UTS {u}")
        E, G, nu = num(r["youngs_modulus_GPa"]), num(r["shear_modulus_GPa"]), num(r["poisson_ratio"])
        if E and G and nu is not None and r["category"] in ("metal",):
            G_iso = E / (2 * (1 + nu))
            if abs(G - G_iso) / G_iso > 0.12:
                err(f, i, f"G={G} inconsistent with E/(2(1+nu))={G_iso:.1f}")
        h45, h18 = num(r["hdt_0_45MPa_C"]), num(r["hdt_1_8MPa_C"])
        if h45 is not None and h18 is not None and h18 > h45:
            err(f, i, "HDT@1.8MPa > HDT@0.45MPa")
        if num(r["hardness_value"]) is not None and not r["hardness_scale"]:
            err(f, i, "hardness_value without hardness_scale")
    return rows


def check_am():
    f = "am_materials.csv"
    req = ["id", "brand", "product", "process", "density_kg_m3", "tensile_strength_XY_MPa", "tensile_strength_Z_MPa",
           "tensile_modulus_XY_GPa", "elongation_XY_pct", "hdt_0_45MPa_C", "cost_tier", "printability_notes"]
    rows = load(f, req)
    for i, r in enumerate(rows, start=2):
        if None in r:
            continue
        rng(f, i, r, "density_kg_m3", 500, 3000)
        rng(f, i, r, "tensile_strength_XY_MPa", 0.5, 1500)
        xy, z = num(r["tensile_strength_XY_MPa"]), num(r["tensile_strength_Z_MPa"])
        if xy is not None and z is not None and z > xy * 1.05:
            err(f, i, f"Z strength {z} > XY {xy}")
        lo, hi = num(r["nozzle_temp_min_C"]), num(r["nozzle_temp_max_C"])
        if lo is not None and hi is not None and lo > hi:
            err(f, i, "nozzle min > max")
    return rows


def check_other():
    out = {}
    rows = load("galvanic_anodic_index.csv", ["id", "material_group", "anodic_index_V"])
    for i, r in enumerate(rows, start=2):
        rng("galvanic_anodic_index.csv", i, r, "anodic_index_V", 0, 2.5)
    out["galvanic_anodic_index.csv"] = rows
    f = "galvanic_seawater_potentials.csv"
    rows = load(f, ["id", "material", "potential_min_V_vs_SCE", "potential_max_V_vs_SCE"])
    for i, r in enumerate(rows, start=2):
        if num(r["potential_min_V_vs_SCE"]) > num(r["potential_max_V_vs_SCE"]):
            err(f, i, "min > max potential")
    out[f] = rows
    f = "friction_pairs.csv"
    rows = load(f, ["id", "material_a", "material_b", "condition", "mu_static", "mu_kinetic"])
    for i, r in enumerate(rows, start=2):
        rng(f, i, r, "mu_static", 0.0005, 2.0)
        rng(f, i, r, "mu_kinetic", 0.0005, 2.0)
    out[f] = rows
    f = "bushing_pv_limits.csv"
    rows = load(f, ["id", "material", "max_pressure_dynamic_MPa", "max_velocity_m_s", "max_PV_MPa_m_s", "mu_typical", "max_temp_C"])
    for i, r in enumerate(rows, start=2):
        p, v, pv = num(r["max_pressure_dynamic_MPa"]), num(r["max_velocity_m_s"]), num(r["max_PV_MPa_m_s"])
        if pv is not None and p is not None and v is not None and pv > p * v * 1.001:
            err(f, i, f"PV {pv} exceeds P*V {p * v}")
        ps = num(r["max_pressure_static_MPa"])
        if ps is not None and p is not None and p > ps:
            err(f, i, "dynamic pressure > static")
        rng(f, i, r, "mu_typical", 0.0005, 1.0)
    out[f] = rows
    with open(os.path.join(HERE, "galvanic_rules.json"), encoding="utf-8") as fh:
        g = json.load(fh)
    for k in ("max_anodic_index_difference_V", "source_url", "value_type"):
        if k not in g:
            err("galvanic_rules.json", 0, f"missing key {k}")
    return out


def main():
    m = check_materials()
    a = check_am()
    o = check_other()
    print(f"materials.csv: {len(m)} rows")
    print(f"am_materials.csv: {len(a)} rows")
    for k, v in o.items():
        print(f"{k}: {len(v)} rows")
    if errors:
        for e in errors:
            print("ERROR", e)
        print("FAIL")
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()
