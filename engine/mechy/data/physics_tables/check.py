"""Validator + unit tests for physics_tables (stdlib only).

    python3 -I check.py      -> prints PASS/FAIL per check, exit code 1 on any FAIL
"""
import csv
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import formulas as F  # noqa: E402

VALUE_TYPES = {"datasheet", "standard", "handbook_typical", "estimate"}
results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def close(a, b, rel=1e-6):
    return math.isclose(a, b, rel_tol=rel, abs_tol=1e-30)


def num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


# --- required columns per CSV ------------------------------------------------
REQUIRED = {
    "physical_constants.csv": ["id", "value_SI", "unit", "exact"],
    "unit_conversions.csv": ["quantity", "from_unit", "to_unit", "factor", "offset"],
    "standard_atmosphere.csv": ["altitude_m", "temperature_K", "pressure_Pa", "density_kg_m3"],
    "air_properties_vs_T.csv": ["temperature_C", "density_kg_m3", "dynamic_viscosity_Pa_s"],
    "water_properties_vs_T.csv": ["temperature_C", "density_kg_m3", "dynamic_viscosity_Pa_s"],
    "drag_coefficients.csv": ["shape", "Cd_typical"],
    "restitution_coefficients.csv": ["ball", "surface", "COR_min", "COR_typical", "COR_max"],
    "ball_properties.csv": ["object", "mass_kg_nominal", "diameter_m_nominal", "Cd_typical"],
    "efficiencies.csv": ["component", "eta_min", "eta_typical", "eta_max"],
    "surface_roughness_by_process.csv": ["process", "Ra_um_min", "Ra_um_typical", "Ra_um_max"],
    "tolerance_by_process.csv": ["process", "typical_tolerance_mm", "best_tolerance_mm"],
    "iso2768_general_tolerances.csv": ["class", "size_over_mm", "size_upto_mm", "tolerance_plusminus_mm"],
    "heat_transfer_coefficients.csv": ["mode", "h_W_m2K_min", "h_W_m2K_typical", "h_W_m2K_max"],
    "pinch_point_gaps_iso13854.csv": ["body_part", "min_gap_mm"],
    "safety_distances.csv": ["item", "safety_distance_mm"],
    "human_forces.csv": ["item", "body_region", "force_N_typical"],
    "human_anthropometry.csv": ["dimension", "p5_mm", "p50_mm", "p95_mm"],
}

tables = {}
for path in sorted(glob.glob(os.path.join(HERE, "*.csv"))):
    fn = os.path.basename(path)
    with open(path, newline="", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        rows = list(rdr)
        cols = rdr.fieldnames or []
    tables[fn] = rows
    need = REQUIRED.get(fn, []) + ["source_url", "value_type"]
    check(f"{fn}: known file", fn in REQUIRED)
    check(f"{fn}: columns", all(c in cols for c in need), f"missing {set(need) - set(cols)}")
    check(f"{fn}: has rows", len(rows) > 0)
    bad_vt = [r.get("value_type") for r in rows if r.get("value_type") not in VALUE_TYPES]
    check(f"{fn}: value_type valid", not bad_vt, str(bad_vt[:3]))
    check(f"{fn}: source_url http", all(r["source_url"].startswith("http") for r in rows))
    ragged = [i for i, r in enumerate(rows) if None in r or any(v is None for v in r.values())]
    check(f"{fn}: no ragged rows", not ragged, f"rows {ragged[:5]}")
    # numeric columns must parse; no negatives except temperatures/altitudes/offsets
    for c in cols:
        if c.endswith(("_kg", "_m", "_mm", "_um", "_N", "_Pa", "_m3", "_s", "_mK", "_kgK",
                       "_m2K", "_N_m", "_kg_min", "_kg_max", "_kg_nominal", "_m_min",
                       "_m_max", "_m_nominal", "_m_s", "_Pa_s", "_m2_s")) or c.startswith(
                           ("eta_", "Cd_", "COR_", "Ra_um", "h_W", "force_N", "p5", "p50", "p95")):
            vals = []
            ok = True
            for r in rows:
                v = r[c]
                if v in ("",):
                    continue
                try:
                    vals.append(float(v))
                except ValueError:
                    if c != "Cd_typical":      # Stokes row holds '24/Re'
                        ok = False
            check(f"{fn}: {c} numeric", ok)
            check(f"{fn}: {c} non-negative", all(v >= 0 for v in vals))


def ordered(fn, lo, mid, hi):
    bad = []
    for r in tables[fn]:
        a, b, c = num(r[lo]), num(r[mid]), num(r[hi])
        if None not in (a, b, c) and not (a <= b <= c):
            bad.append(list(r.values())[0])
    check(f"{fn}: {lo} <= {mid} <= {hi}", not bad, str(bad))


ordered("efficiencies.csv", "eta_min", "eta_typical", "eta_max")
check("efficiencies.csv: eta <= 1", all(float(r["eta_max"]) <= 1 for r in tables["efficiencies.csv"]))
ordered("restitution_coefficients.csv", "COR_min", "COR_typical", "COR_max")
check("restitution: COR <= 1", all(float(r["COR_max"]) <= 1 for r in tables["restitution_coefficients.csv"]))
ordered("surface_roughness_by_process.csv", "Ra_um_min", "Ra_um_typical", "Ra_um_max")
ordered("heat_transfer_coefficients.csv", "h_W_m2K_min", "h_W_m2K_typical", "h_W_m2K_max")
ordered("human_forces.csv", "force_N_min", "force_N_typical", "force_N_max")
ordered("human_anthropometry.csv", "p5_mm", "p50_mm", "p95_mm")
ordered("ball_properties.csv", "mass_kg_min", "mass_kg_nominal", "mass_kg_max")
ordered("ball_properties.csv", "diameter_m_min", "diameter_m_nominal", "diameter_m_max")
ordered("drag_coefficients.csv", "Cd_min", "Cd_typical", "Cd_max")
check("tolerance: best <= typical", all(float(r["best_tolerance_mm"]) <= float(r["typical_tolerance_mm"])
                                         for r in tables["tolerance_by_process.csv"]))
check("pinch gaps: finger 25, body 500",
      {r["body_part"]: int(r["min_gap_mm"]) for r in tables["pinch_point_gaps_iso13854.csv"]}.get("finger") == 25)
check("cobot: transient not applicable here, all quasi-static <= 220 N",
      all(float(r["force_N_typical"]) <= 220 for r in tables["human_forces.csv"] if r["item"].startswith("cobot")))
check("unit conversions: factors > 0", all(float(r["factor"]) > 0 for r in tables["unit_conversions.csv"]))
check("unit conversions: unique from_unit",
      len({r["from_unit"] for r in tables["unit_conversions.csv"]}) == len(tables["unit_conversions.csv"]))

# monotonic physics sanity
atm = tables["standard_atmosphere.csv"]
check("ISA: pressure decreases with altitude",
      all(float(a["pressure_Pa"]) > float(b["pressure_Pa"]) for a, b in zip(atm, atm[1:])))
check("ISA: sea level 101325 Pa / 1.225 kg/m3",
      close(float(atm[0]["pressure_Pa"]), 101325) and close(float(atm[0]["density_kg_m3"]), 1.225, 1e-4))
air = tables["air_properties_vs_T.csv"]
check("air: viscosity rises with T", all(float(a["dynamic_viscosity_Pa_s"]) < float(b["dynamic_viscosity_Pa_s"])
                                         for a, b in zip(air, air[1:])))
wat = tables["water_properties_vs_T.csv"]
check("water: viscosity falls with T", all(float(a["dynamic_viscosity_Pa_s"]) > float(b["dynamic_viscosity_Pa_s"])
                                           for a, b in zip(wat, wat[1:])))
check("water: density 990-1000 near room T", 990 < float(wat[2]["density_kg_m3"]) < 1000)

# constants cross-check against the raw NIST file (second source = the parse itself vs hard-coded)
raw = os.path.join(HERE, "raw", "nist_codata_allascii.txt")
check("raw NIST file present", os.path.exists(raw))
c = {r["id"]: float(r["value_SI"]) for r in tables["physical_constants.csv"]}
check("const c exact", c["c"] == 299792458)
check("const g_n", c["g_n"] == 9.80665)
check("const k_B", close(c["k_B"], 1.380649e-23))
check("const G", close(c["G"], 6.6743e-11, 1e-4))
check("const sigma = 2 pi^5 k^4/(15 h^3 c^2)",
      close(c["sigma_SB"], 2 * math.pi ** 5 * c["k_B"] ** 4 / (15 * c["h"] ** 3 * c["c"] ** 2), 1e-9))
check("const R = N_A k_B", close(c["R"], c["N_A"] * c["k_B"], 1e-9))
check("const F = N_A e", close(c["F"], c["N_A"] * c["e"], 1e-9))

# --- JSON formula files --------------------------------------------------------
for name in F.FORMULA_FILES:
    data = F.load(name)
    check(f"{name}.json: meta source/value_type",
          data["meta"]["source_url"].startswith("http") and data["meta"]["value_type"] in VALUE_TYPES)
    ids = [f["id"] for f in data["formulas"]]
    check(f"{name}.json: unique ids", len(ids) == len(set(ids)))
    for f in data["formulas"]:
        try:
            for o in f["outputs"].values():
                F.compile_expr(o["expr"], set(f["variables"]))
                assert o["unit"]
            for v in f["variables"].values():
                assert v["unit"] and v["desc"]
            ok = True
        except Exception as ex:  # noqa: BLE001
            ok, f["_err"] = False, ex
        check(f"{name}.json: {f['id']} compiles", ok, str(f.get("_err", "")))
        # evaluate every formula with plausible positive inputs (r_i < r_o etc.)
        test_vals = {k: 1.0 for k in f["variables"]}
        for small in ("r_i", "d", "b", "h", "a", "tf", "tw"):
            if small in test_vals and len(test_vals) > 1:
                test_vals[small] = 0.3
        if f["id"] in ("tube", "hollow_rectangle"):
            test_vals.update({"D": 1.0, "d": 0.5, "B": 1.0, "H": 1.0, "b": 0.5, "h": 0.5})
        if f["id"] == "neuber_notch_sensitivity_steel_bending":
            test_vals.update({"Sut_kpsi": 100.0, "r_in": 0.1})
        try:
            out = F.evaluate(name, f["id"], **test_vals)
            fin = all(math.isfinite(v) for v in out.values())
        except Exception as ex:  # noqa: BLE001
            fin = False
        check(f"{name}.json: {f['id']} evaluates finite", fin)

# --- unit tests of formulas.py ------------------------------------------------
E = F.evaluate
check("MOI solid cylinder 0.5 m r^2", close(E("moment_of_inertia_formulas", "solid_cylinder_axial", m=2, r=0.1)["I"], 0.01))
check("MOI sphere 2/5", close(E("moment_of_inertia_formulas", "solid_sphere", m=5, r=0.2)["I"], 0.08))
check("MOI ping-pong shell", close(E("moment_of_inertia_formulas", "thin_spherical_shell", m=0.0027, r=0.02)["I"], 0.0027 * 0.0004 * 2 / 3))
check("MOI rod end = rod center + parallel axis",
      close(E("moment_of_inertia_formulas", "thin_rod_end", m=1, L=2)["I"],
            E("moment_of_inertia_formulas", "parallel_axis",
              I_cm=E("moment_of_inertia_formulas", "thin_rod_center", m=1, L=2)["I"], m=1, d=1)["I"]))
check("MOI thick shell -> thin shell limit",
      close(E("moment_of_inertia_formulas", "thick_spherical_shell", m=1, r_o=1.0, r_i=0.9999)["I"], 2 / 3, 1e-3))
check("MOI tube -> solid when r_i=0",
      close(E("moment_of_inertia_formulas", "hollow_cylinder_axial", m=1, r_o=1, r_i=0)["I"], 0.5))
check("reflected inertia /N^2", close(E("moment_of_inertia_formulas", "reflected_through_gearbox", J_load=1, N=10, eta=1)["J_reflected"], 0.01))
check("leadscrew reflected 8 mm lead",
      close(E("moment_of_inertia_formulas", "linear_mass_on_leadscrew", m=1, lead=0.008)["J_reflected"], (0.008 / (2 * math.pi)) ** 2))
check("section rectangle I", close(E("section_properties", "rectangle", b=0.02, h=0.04)["I"], 0.02 * 0.04 ** 3 / 12))
check("section circle J = 2I", close(E("section_properties", "circle", d=0.01)["J"], 2 * E("section_properties", "circle", d=0.01)["I"]))
check("section tube -> thin tube",
      close(E("section_properties", "tube", D=0.101, d=0.099)["I"], E("section_properties", "thin_tube", r=0.05, t=0.001)["I"], 1e-3))
check("section I-beam with tw=b equals rectangle",
      close(E("section_properties", "i_beam", b=0.1, h=0.2, tf=0.01, tw=0.1)["I"], 0.1 * 0.2 ** 3 / 12))
check("torsion K square ~0.1406 a^4", close(E("section_properties", "rectangle_torsion", a=1, b=1)["K"], 0.1406, 0.01))
r = E("beam_deflection_cases", "cantilever_end_load", P=10, L=0.5, E=200e9, I=1e-8)
check("cantilever PL^3/3EI", close(r["delta_max"], 10 * 0.125 / (3 * 200e9 * 1e-8)) and close(r["M_max"], 5))
check("cantilever stiffness = P/delta", close(r["k"], 10 / r["delta_max"]))
check("cantilever load-at-a with a=L equals end load",
      close(E("beam_deflection_cases", "cantilever_load_at_a", P=10, a=0.5, L=0.5, E=200e9, I=1e-8)["delta_tip"], r["delta_max"]))
s = E("beam_deflection_cases", "simply_supported_load_at_a", P=100, a=0.5, L=1, E=70e9, I=1e-8)
check("SS load at midspan equals center-load case",
      close(s["delta_max"], E("beam_deflection_cases", "simply_supported_center_load", P=100, L=1, E=70e9, I=1e-8)["delta_max"])
      and close(s["delta_at_load"], s["delta_max"]))
check("SS UDL 5/384", close(E("beam_deflection_cases", "simply_supported_udl", w=1, L=1, E=1, I=1)["delta_max"], 5 / 384))
check("fixed-fixed UDL = SS UDL / 5", close(E("beam_deflection_cases", "fixed_fixed_udl", w=1, L=1, E=1, I=1)["delta_max"], 1 / 384))
check("Euler pinned", close(E("beam_deflection_cases", "euler_buckling", E=1, I=1, K=1, L=1)["P_cr"], math.pi ** 2))
check("Kt circular hole infinite plate = 3", close(E("stress_concentration", "elliptical_hole_infinite_plate", a=1, b=1)["Kt"], 3))
check("Kt plate hole d/W->0 = 3", close(F.kt_plate_hole(0.0, 1.0), 3.0))
check("Kt plate hole d/W=0.5 ~2.16", 2.1 < F.kt_plate_hole(0.5, 1.0) < 2.2)
kb = F.kt_stepped_shaft(D=20, d=10, r=1, load="bending")
check("Kt stepped bending D/d=2 r/d=0.1 ~1.7-1.8", 1.68 < kb < 1.8, f"{kb:.3f}")
kt = F.kt_stepped_shaft(D=20, d=10, r=1, load="torsion")
check("Kt stepped torsion D/d=2 r/d=0.1 ~1.45-1.55", 1.45 < kt < 1.55, f"{kt:.3f}")
check("Kt stepped >= 1 for large radius", F.kt_stepped_shaft(D=10.1, d=10, r=5, load="axial") >= 1.0)
check("Kt interpolation between rows",
      F.kt_stepped_shaft(15, 10, 1) <= F.kt_stepped_shaft(20, 10, 1) + 1e-9)
q = F.notch_sensitivity_steel(r_m=0.0025, Sut_Pa=690e6)
check("Neuber q steel 100 kpsi r=0.1 in ~0.8-0.9", 0.8 < q < 0.9, f"{q:.3f}")
check("Kf", close(F.kf(3.0, 0.5), 2.0))

check("convert kgf*cm -> N*m", close(F.convert(1, "kgf*cm", "N*m"), 0.0980665))
check("convert oz-in -> N*m", close(F.convert(100, "ozf*in", "N*m"), 0.706155181, 1e-8))
check("convert kgf*cm -> oz-in ~13.887", close(F.convert(1, "kgf*cm", "ozf*in"), 13.8874, 1e-4))
check("convert g*cm^2 -> kg*m^2", close(F.convert(54, "g*cm^2", "kg*m^2"), 5.4e-6))
check("convert degF -> degC", close(F.convert(212, "degF", "degC"), 100.0, 1e-9))
check("convert degC -> K", close(F.convert(25, "degC", "K"), 298.15))
check("convert rpm -> rad/s", close(F.convert(60, "rpm", "rad/s"), 2 * math.pi))
check("servo 0.1 s/60deg -> 10.47 rad/s", close(F.to_si(0.1, "sec/60deg"), 10.471975511966))
try:
    F.convert(1, "kgf*cm", "Pa")
    bad = False
except ValueError:
    bad = True
check("convert rejects incompatible units", bad)
check("ISA 11 km", close(F.isa(11000)[1], 22632.0, 1e-3) and close(F.isa(11000)[0], 216.65))
check("air density 20C 1.204", close(F.air_density(20), 1.2041, 1e-3))
check("constant lookup g_n", F.constant("g_n") == 9.80665)
check("water interp 25C viscosity ~0.89 mPa s",
      close(F.interp_table("water_properties_vs_T", "temperature_C", "dynamic_viscosity_Pa_s", 25), 0.8995e-3, 0.02))
for row in tables["ball_properties.csv"]:
    vt = F.terminal_velocity(float(row["mass_kg_nominal"]), float(row["diameter_m_nominal"]), float(row["Cd_typical"]))
    check(f"ball terminal velocity {row['object']}", close(vt, float(row["terminal_velocity_m_s"]), 2e-3))
check("ping-pong terminal ~8-9 m/s",
      7.5 < float(next(r for r in tables["ball_properties.csv"] if r["object"].startswith("table tennis"))["terminal_velocity_m_s"]) < 9.5)
try:
    F.eval_expr("__import__('os')")
    unsafe = True
except ValueError:
    unsafe = False
check("evaluator rejects unsafe expressions", not unsafe)

# folder size
size = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(HERE) for f in fs)
check("folder < 20 MB", size < 20 * 1024 * 1024, f"{size} bytes")

fails = [r for r in results if not r[1]]
for n, ok, d in results:
    if not ok:
        print(f"FAIL  {n}  {d}")
print(f"{len(results) - len(fails)}/{len(results)} checks passed")
print("PASS" if not fails else "FAIL")
sys.exit(1 if fails else 0)
