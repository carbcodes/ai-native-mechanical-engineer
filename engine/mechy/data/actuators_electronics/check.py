"""Validator for the actuators_electronics dataset. Stdlib only. Run: python3 -I check.py"""
import csv, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
VALUE_TYPES = {"datasheet", "standard", "handbook_typical", "estimate"}
VERIFICATION = {"fetched", "recalled"}
UNIT_SUFFIX = re.compile(r"_(Nm|A|V|kg|mm|mm2|ohm|mH|uH|gcm2|rpm|rps|deg|bits|MHz|kHz|Hz|kB|MB|W|pct|Ah|Wh|N|mA|s|20C|mm_s|"
                         r"per_A|per_V|per_rtHz|per_kg|per_km_20C|g|dps|C_A)$")
TEXT_COLS = {"logic_V"}          # unit-suffixed but holds ranges like "3.3-5"
SIGNED_OK = {"range_min"}
EXPECTED = {  # file -> minimum row count
    "stepper_motors.csv": 30, "stepper_torque_speed_estimates.csv": 100, "closed_loop_steppers.csv": 5,
    "bldc_gimbal_motors.csv": 15, "qdd_actuators.csv": 8, "servos.csv": 20, "brushed_gearmotors.csv": 80,
    "linear_actuators.csv": 8, "solenoids.csv": 4, "motor_drivers.csv": 20, "mcu_boards.csv": 12,
    "encoders.csv": 8, "imus.csv": 5, "sensors_other.csv": 15, "power_supplies.csv": 10,
    "dc_dc_converters.csv": 8, "battery_cells.csv": 10, "wire_ampacity_awg.csv": 10,
    "wire_ampacity_metric.csv": 8, "connectors.csv": 15,
}
errors = []

def err(f, i, msg):
    errors.append(f"{f}:{i}: {msg}")

def is_numeric_col(c):
    if c in TEXT_COLS:
        return False
    base = re.sub(r"_(min|max)$", "", c)
    return bool(UNIT_SUFFIX.search(c) or UNIT_SUFFIX.search(base))

def num(row, c):
    v = (row.get(c) or "").strip()
    return float(v) if v else None

def le(f, i, row, a, b):
    x, y = num(row, a), num(row, b)
    if x is not None and y is not None and x > y + 1e-9:
        err(f, i, f"{a}={x} > {b}={y}")

def check_csv(f):
    path = os.path.join(HERE, f)
    with open(path, newline="") as fh:
        rd = csv.DictReader(fh)
        cols = rd.fieldnames or []
        rows = list(rd)
    for req in ("source_url", "value_type"):
        if req not in cols:
            err(f, 1, f"missing required column {req}")
    if len(set(cols)) != len(cols):
        err(f, 1, "duplicate column names")
    numeric = [c for c in cols if is_numeric_col(c)]
    for i, row in enumerate(rows, start=2):
        if None in row:
            err(f, i, f"too many fields: {row[None]}")
        if row.get("value_type") not in VALUE_TYPES:
            err(f, i, f"bad value_type {row.get('value_type')!r}")
        if "verification" in cols and row.get("verification") not in VERIFICATION:
            err(f, i, f"bad verification {row.get('verification')!r}")
        if not (row.get("source_url") or "").strip():
            err(f, i, "empty source_url")
        for c in numeric:
            v = (row.get(c) or "").strip()
            if not v:
                continue
            try:
                x = float(v)
            except ValueError:
                err(f, i, f"{c}={v!r} not numeric"); continue
            if x < 0 and c not in SIGNED_OK:
                err(f, i, f"{c}={x} negative")
        # cross-field sanity
        le(f, i, row, "supply_min_V", "supply_max_V")
        le(f, i, row, "supply_max_V", "abs_max_V")
        le(f, i, row, "input_min_V", "input_max_V")
        le(f, i, row, "output_min_V", "output_max_V")
        le(f, i, row, "board_input_V_min", "board_input_V_max")
        le(f, i, row, "continuous_current_A", "peak_current_A")
        le(f, i, row, "rated_current_A", "peak_current_A")
        le(f, i, row, "rated_torque_Nm", "peak_torque_Nm")
        le(f, i, row, "output_A_practical", "output_A_rated")
        le(f, i, row, "min_V", "nominal_V"); le(f, i, row, "nominal_V", "max_V")
        le(f, i, row, "range_min", "range_max")
        le(f, i, row, "current_per_contact_A", "burst_current_A")
        le(f, i, row, "nec_60C_A", "nec_75C_A"); le(f, i, row, "nec_75C_A", "nec_90C_A")
        for c in ("holding_torque_Nm", "mass_kg", "stall_torque_Nm", "capacity_Ah", "area_mm2"):
            x = num(row, c) if c in cols else None
            if x is not None and x <= 0:
                err(f, i, f"{c} must be > 0")
        if f == "stepper_motors.csv":
            t, m = num(row, "holding_torque_Nm"), num(row, "mass_kg")
            if t and m and not (0.02 < t / m < 4.0):
                err(f, i, f"torque/mass {t/m:.2f} N.m/kg implausible for a hybrid stepper")
            if num(row, "step_angle_deg") not in (0.9, 1.8):
                err(f, i, "step angle not 0.9/1.8")
        if f == "battery_cells.csv":
            v, ah, wh, m = (num(row, k) for k in ("nominal_V", "capacity_Ah", "energy_Wh", "mass_kg"))
            if v and ah and wh and abs(v * ah - wh) > 0.06 * wh:
                err(f, i, f"energy_Wh {wh} != V*Ah {v*ah:.2f}")
            se = num(row, "specific_energy_Wh_per_kg")
            if wh and m and se and abs(wh / m - se) > 0.1 * se:
                err(f, i, f"specific energy {se} inconsistent with {wh/m:.0f}")
            if se and se > 300:
                err(f, i, "specific energy > 300 Wh/kg implausible for listed chemistries")
        if f == "power_supplies.csv":
            v, a, w = (num(row, k) for k in ("output_V", "output_A", "output_W"))
            if v and a and w and abs(v * a - w) > 0.05 * w:
                err(f, i, f"output_W {w} != V*A {v*a:.1f}")
        if f == "wire_ampacity_awg.csv":
            d, ar = num(row, "diameter_mm"), num(row, "area_mm2")
            if abs(3.14159265 * d * d / 4 - ar) > 0.01 * ar + 0.002:
                err(f, i, "area inconsistent with diameter")
    exp = EXPECTED.get(f)
    if exp and len(rows) < exp:
        err(f, 0, f"only {len(rows)} rows, expected >= {exp}")
    return len(rows)

def main():
    files = sorted(x for x in os.listdir(HERE) if x.endswith((".csv", ".json")))
    for f in EXPECTED:
        if f not in files:
            err(f, 0, "missing file")
    total = 0
    for f in files:
        try:
            if f.endswith(".json"):
                with open(os.path.join(HERE, f)) as fh:
                    json.load(fh)
                print(f"  {f}: valid JSON")
            else:
                n = check_csv(f); total += n
                print(f"  {f}: {n} rows")
        except Exception as e:  # noqa: BLE001
            err(f, 0, f"failed to load: {e}")
    if errors:
        print("\n".join(errors))
        print(f"FAIL ({len(errors)} problems)")
        sys.exit(1)
    print(f"PASS ({total} rows in {len(files)} files)")

if __name__ == "__main__":
    main()
