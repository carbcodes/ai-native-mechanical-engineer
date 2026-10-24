"""Validator for reference_designs (stdlib only). Run: python3 -I check.py"""
import csv, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REQ = ["id", "name", "category", "repo_url", "licence", "licence_file", "reuse", "dof", "reach_mm",
       "payload_claimed_kg", "payload_measured_kg", "mass_kg", "repeatability_mm", "motors", "drivers",
       "reductions", "bearings", "materials", "bom_cost_value", "bom_cost_currency", "cad_formats", "urdf",
       "mjcf", "maturity", "known_weaknesses", "source_url", "value_type"]
VALUE_TYPES = {"datasheet", "standard", "handbook_typical", "estimate"}
CATS = {"robot_arm", "gripper", "legged", "actuator_qdd", "actuator_driver", "actuator_cycloidal",
        "actuator_capstan", "actuator_planetary", "actuator_harmonic", "pan_tilt", "launcher", "catcher",
        "motion_corexy", "motion_cartesian", "motion_cnc", "conveyor"}
errors = []

def num(v):
    return None if v in ("", None) else float(v)

rows = list(csv.DictReader(open(os.path.join(HERE, "designs.csv"), newline="")))
if not rows:
    errors.append("designs.csv empty")
missing = [c for c in REQ if c not in rows[0]]
if missing:
    errors.append(f"designs.csv missing columns {missing}")
ids = set()
for r in rows:
    i = r["id"]
    if i in ids:
        errors.append(f"duplicate id {i}")
    ids.add(i)
    if r["value_type"] not in VALUE_TYPES:
        errors.append(f"{i}: bad value_type {r['value_type']}")
    if r["category"] not in CATS:
        errors.append(f"{i}: bad category {r['category']}")
    if r["category"] != "conveyor" and not r["repo_url"].startswith("https://github.com/"):
        errors.append(f"{i}: repo_url not a GitHub URL")
    if not r["source_url"].startswith("http"):
        errors.append(f"{i}: source_url missing")
    if not r["licence"]:
        errors.append(f"{i}: licence empty")
    try:
        dof = num(r["dof"]); reach = num(r["reach_mm"]); pc = num(r["payload_claimed_kg"])
        pm = num(r["payload_measured_kg"]); m = num(r["mass_kg"]); rep = num(r["repeatability_mm"])
        cost = num(r["bom_cost_value"])
    except ValueError as e:
        errors.append(f"{i}: non-numeric value {e}"); continue
    if dof is not None and not (0 < dof <= 30):
        errors.append(f"{i}: dof out of range {dof}")
    if reach is not None and not (10 <= reach <= 3000):
        errors.append(f"{i}: reach_mm implausible {reach}")
    for nm, v, hi in (("payload_claimed_kg", pc, 50), ("payload_measured_kg", pm, 50), ("mass_kg", m, 100),
                      ("repeatability_mm", rep, 5), ("bom_cost_value", cost, 50000)):
        if v is not None and not (0 < v <= hi):
            errors.append(f"{i}: {nm} out of range {v}")
    if pc is not None and pm is not None and pm > pc * 1.5:
        errors.append(f"{i}: measured payload far above claimed")
    if m is not None and pc is not None and r["category"] == "robot_arm" and pc > m:
        errors.append(f"{i}: arm payload > own mass (suspicious)")
    if cost is not None and r["bom_cost_currency"] not in ("USD", "EUR"):
        errors.append(f"{i}: bad currency")
    # licence file must sit next to any downloaded raw file
    for f in [x.strip() for x in r.get("raw_files", "").split(";") if x.strip()]:
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            errors.append(f"{i}: raw file missing {f}")
        elif os.path.getsize(p) > 2 * 1024 * 1024:
            errors.append(f"{i}: raw file > 2 MB {f}")
        d = os.path.dirname(p)
        if not any(n.lower().startswith("licen") for n in os.listdir(d)):
            errors.append(f"{i}: no LICENSE next to {f}")
        if r["reuse"].startswith(("reference_only", "non_commercial")):
            errors.append(f"{i}: raw files downloaded although licence forbids reuse")

# per-design JSONs
jdir = os.path.join(HERE, "designs")
jfiles = {f[:-5] for f in os.listdir(jdir) if f.endswith(".json")}
if jfiles != ids:
    errors.append(f"JSON/CSV id mismatch: only_json={sorted(jfiles-ids)} only_csv={sorted(ids-jfiles)}")
for f in sorted(jfiles):
    try:
        j = json.load(open(os.path.join(jdir, f + ".json")))
        for k in ("id", "licence", "repo_url", "value_type", "units"):
            if k not in j:
                errors.append(f"{f}.json missing {k}")
    except Exception as e:
        errors.append(f"{f}.json unreadable: {e}")

# every raw/<design>/ dir has a licence; metadata JSONs load
for d in os.listdir(os.path.join(HERE, "raw")):
    p = os.path.join(HERE, "raw", d)
    if os.path.isdir(p) and not d.startswith("_"):
        if not any(n.lower().startswith("licen") for n in os.listdir(p)):
            errors.append(f"raw/{d}: no LICENSE file")
for f in os.listdir(os.path.join(HERE, "raw", "_github_meta")):
    if f.endswith(".json"):
        try:
            json.load(open(os.path.join(HERE, "raw", "_github_meta", f)))
        except Exception as e:
            errors.append(f"_github_meta/{f}: {e}")

total = 0
for root, _, files in os.walk(HERE):
    total += sum(os.path.getsize(os.path.join(root, x)) for x in files)
if total > 20 * 1024 * 1024:
    errors.append(f"folder {total/1e6:.1f} MB > 20 MB")

print(f"{len(rows)} designs, {len(jfiles)} JSONs, folder {total/1e6:.2f} MB")
if errors:
    print("FAIL"); [print(" -", e) for e in errors]; sys.exit(1)
print("PASS")
