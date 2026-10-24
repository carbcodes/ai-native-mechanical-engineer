"""Evaluate the JSON formula tables in this folder (Python stdlib only).

    import formulas as F
    F.evaluate("beam_deflection_cases", "cantilever_end_load", P=10, L=0.3, E=69e9, I=1e-9)
    F.convert(2.5, "kgf*cm", "N*m")
    F.kt_stepped_shaft(D=20e-3, d=10e-3, r=1e-3, load="bending")

Expressions are parsed with `ast` and only arithmetic, numbers, the declared
variables and whitelisted math names are allowed (no attribute access, no calls
other than whitelisted functions), so evaluating them is safe.
"""
import ast
import csv
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FORMULA_FILES = ("moment_of_inertia_formulas", "section_properties",
                 "beam_deflection_cases", "stress_concentration")

_MATH = {"pi": math.pi, "e_const": math.e, "sqrt": math.sqrt, "sin": math.sin,
         "cos": math.cos, "tan": math.tan, "atan": math.atan, "exp": math.exp,
         "log": math.log, "log10": math.log10, "abs": abs, "min": min, "max": max}
_NODES = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Load,
          ast.Call, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd)

_cache = {}


def load(name):
    """Return parsed JSON for a formula file (name without .json)."""
    if name not in _cache:
        with open(os.path.join(HERE, name + ".json"), encoding="utf-8") as f:
            _cache[name] = json.load(f)
    return _cache[name]


def get(name, fid):
    for f in load(name)["formulas"]:
        if f["id"] == fid:
            return f
    raise KeyError(f"{name}: no formula {fid!r}")


def list_formulas():
    return {n: [f["id"] for f in load(n)["formulas"]] for n in FORMULA_FILES}


def compile_expr(expr, allowed_names):
    tree = ast.parse(expr, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, _NODES):
            raise ValueError(f"disallowed syntax {type(node).__name__} in {expr!r}")
        if isinstance(node, ast.Name) and node.id not in allowed_names and node.id not in _MATH:
            raise ValueError(f"unknown name {node.id!r} in {expr!r}")
        if isinstance(node, ast.Call) and not (isinstance(node.func, ast.Name)
                                               and node.func.id in _MATH):
            raise ValueError(f"disallowed call in {expr!r}")
    return compile(tree, "<formula>", "eval")


def eval_expr(expr, **vars):
    code = compile_expr(expr, set(vars))
    return eval(code, {"__builtins__": {}}, {**_MATH, **vars})


def evaluate(name, fid, **vars):
    """Evaluate every output of formula `fid` in file `name`; returns {output: value}."""
    f = get(name, fid)
    missing = set(f["variables"]) - set(vars)
    if missing:
        raise TypeError(f"{fid}: missing variables {sorted(missing)}")
    return {k: eval_expr(o["expr"], **{v: vars[v] for v in f["variables"]})
            for k, o in f["outputs"].items()}


# --- stress concentration helpers --------------------------------------------
def kt_stepped_shaft(D, d, r, load="bending"):
    """Kt for stepped round shaft (nominal stress on d), power-fit A*(r/d)**b.

    A and b are interpolated linearly in D/d; D/d outside the table is clamped.
    Result is never below 1.
    """
    rows = sorted(tuple(row) for row in _kt_rows(load))
    ratio = D / d
    if ratio <= rows[0][0]:
        A, b = rows[0][1], rows[0][2]
    elif ratio >= rows[-1][0]:
        A, b = rows[-1][1], rows[-1][2]
    else:
        for (x0, A0, b0), (x1, A1, b1) in zip(rows, rows[1:]):
            if x0 <= ratio <= x1:
                t = (ratio - x0) / (x1 - x0)
                A, b = A0 + t * (A1 - A0), b0 + t * (b1 - b0)
                break
    return max(1.0, A * (r / d) ** b)


def _kt_rows(kind):
    return load("stress_concentration")["stepped_round_shaft_power_fit"][kind]


def kt_plate_hole(d, W):
    return evaluate("stress_concentration", "plate_central_hole_tension", d=d, W=W)["Kt"]


def kf(Kt, q=1.0):
    return 1 + q * (Kt - 1)


def notch_sensitivity_steel(r_m, Sut_Pa):
    """Neuber q for steel in bending, SI inputs (converted to the fit's in/kpsi)."""
    return evaluate("stress_concentration", "neuber_notch_sensitivity_steel_bending",
                    r_in=r_m / 0.0254, Sut_kpsi=Sut_Pa / 6894757.29316836)["q"]


# --- tables -----------------------------------------------------------------
def read_csv(name):
    with open(os.path.join(HERE, name if name.endswith(".csv") else name + ".csv"),
              newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _units():
    if "_units" not in _cache:
        _cache["_units"] = {r["from_unit"]: r for r in read_csv("unit_conversions")}
    return _cache["_units"]


def to_si(value, unit):
    """Convert value in `unit` (a from_unit in unit_conversions.csv) to its SI unit."""
    r = _units()[unit]
    if unit == "sec/60deg":           # inverse unit: time per 60 degrees
        return float(r["factor"]) / value
    return value * float(r["factor"]) + float(r["offset"])


def from_si(value, unit):
    r = _units()[unit]
    if unit == "sec/60deg":
        return float(r["factor"]) / value
    return (value - float(r["offset"])) / float(r["factor"])


def convert(value, from_unit, to_unit):
    """Convert between two units of the same quantity (either may be the SI unit)."""
    u = _units()
    si_from = value if from_unit not in u else to_si(value, from_unit)
    if to_unit in u:
        if from_unit in u and u[from_unit]["to_unit"] != u[to_unit]["to_unit"]:
            raise ValueError(f"incompatible units {from_unit} -> {to_unit}")
        return from_si(si_from, to_unit)
    if from_unit in u and u[from_unit]["to_unit"] != to_unit:
        raise ValueError(f"{from_unit} converts to {u[from_unit]['to_unit']}, not {to_unit}")
    return si_from


def constant(cid):
    for r in read_csv("physical_constants"):
        if r["id"] == cid:
            return float(r["value_SI"])
    raise KeyError(cid)


def isa(h_m):
    """ISA temperature K, pressure Pa, density kg/m^3 at geometric-ish altitude h (<= 32 km)."""
    R, g0, T0, p0 = 287.05287, 9.80665, 288.15, 101325.0
    if h_m <= 11000:
        T = T0 - 0.0065 * h_m
        p = p0 * (T / T0) ** (g0 / (0.0065 * R))
    else:
        p11 = p0 * (216.65 / T0) ** (g0 / (0.0065 * R))
        if h_m <= 20000:
            T = 216.65
            p = p11 * math.exp(-g0 * (h_m - 11000) / (R * T))
        else:
            p20 = p11 * math.exp(-g0 * 9000 / (R * 216.65))
            T = 216.65 + 0.001 * (h_m - 20000)
            p = p20 * (T / 216.65) ** (-g0 / (0.001 * R))
    return T, p, p / (R * T)


def air_density(T_C=20.0, p_Pa=101325.0):
    return p_Pa / (287.05287 * (T_C + 273.15))


def interp_table(name, xcol, ycol, x):
    """Linear interpolation in a CSV table (e.g. water_properties_vs_T)."""
    rows = sorted(((float(r[xcol]), float(r[ycol])) for r in read_csv(name)))
    if not rows[0][0] <= x <= rows[-1][0]:
        raise ValueError(f"{x} outside {rows[0][0]}..{rows[-1][0]}")
    for (x0, y0), (x1, y1) in zip(rows, rows[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0) if x1 > x0 else y0


# --- ballistics -------------------------------------------------------------
def drag_force(v, Cd, area, rho=None):
    rho = air_density() if rho is None else rho
    return 0.5 * rho * Cd * area * v * v


def terminal_velocity(m, d, Cd, rho=None, g=9.80665):
    rho = air_density() if rho is None else rho
    return math.sqrt(2 * m * g / (rho * Cd * math.pi * d * d / 4))


def rebound_speed(v_in, cor):
    return cor * v_in


def flight_time_vacuum(v0, angle_rad, g=9.80665):
    """Time to return to launch height ignoring drag."""
    return 2 * v0 * math.sin(angle_rad) / g
