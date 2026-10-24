"""`mechy doc build <variant>`: docs/<variant>/build_guide.pdf and report.pdf (Typst).

Pipeline: read the project files (collect.py) -> render figures (figures.py: part drawings at true
scale, assembly steps, charts) -> write <doc>.data.json next to a copy of the Typst templates ->
compile with the `typst` Python package (it bundles the Typst compiler, so it works offline on macOS
and Linux with no browser or TeX). The .typ + .data.json + img/ sources stay next to the PDFs, so
`typst compile build_guide.typ` in that folder rebuilds the PDF without the engine.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

from ..events import Events
from ..project import Project
from . import assembly as A
from . import collect as C
from . import figures as F

TEMPLATES = Path(__file__).resolve().parent / "templates"


class DocError(RuntimeError):
    pass


def _font_paths() -> list[str]:
    """matplotlib's bundled DejaVu fonts: a sans and a mono every machine has (Typst falls back to them
    when Inter / JetBrains Mono / Helvetica / Menlo are not installed)."""
    try:
        import matplotlib
        return [str(Path(matplotlib.get_data_path()) / "fonts" / "ttf")]
    except Exception:
        return []


def compile_typst(src: Path, pdf: Path) -> list[str]:
    try:
        import typst
    except ImportError as e:  # pragma: no cover - typst is a dependency
        raise DocError("the `typst` Python package is missing: pip install typst (sources were written to "
                       f"{src.parent})") from e
    try:
        res = typst.compile_with_warnings(str(src), output=str(pdf), root=str(src.parent),
                                          font_paths=_font_paths())
        warns = res[1] if isinstance(res, tuple) else []
    except Exception as e:
        diag = str(getattr(e, "diagnostic", "") or "")
        err = diag[diag.find("error:"):] if "error:" in diag else ""
        raise DocError(f"typst failed on {src.name}: {e}\n{err[:1500]}") from e
    return [str(getattr(w, "message", w)) for w in warns or []]


def pdf_pages(pdf: Path) -> int:
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf)).pages)
    except ImportError:
        return len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))


# ------------------------------------------------------------------ model data
def _design(project: Project, variant: str):
    from ..arm_model import load_arm
    from ..cad.belt_arm import params_hash
    arm = load_arm(project, variant)
    if arm.style == "ref_arm":
        from ..cad.ref_arm import build_design
    elif arm.style == "belt_arm":
        from ..cad.belt_arm import build_design
    else:
        raise DocError(f"{variant} uses style {arm.style!r}; the build guide needs a belt_arm or "
                       "ref_arm design (printable parts, BOM and assembly tree)")
    design = build_design(arm)
    return arm, design, params_hash(arm.params)


def _meshes(arm, design) -> list[dict]:
    if arm.style == "ref_arm":
        return [{"name": n, "kind": p_kind, "v": v, "t": t}
                for (v, t, _rgba, n), p_kind in
                zip(design.posed_meshes(arm.ready_pose()),
                    (p.kind for p in design.parts))]
    from ..cad.build import _glb_parts, _posed_meshes
    parts, origins = _glb_parts(arm, design)
    posed = _posed_meshes(parts, origins, arm.ready_pose())
    kinds = {p.name: p.kind for p in design.parts}
    return [{"name": p["name"].rstrip("_"), "kind": kinds.get(p["name"].rstrip("_"), ""), "v": v, "t": t}
            for p, (v, t, _) in zip(parts, posed)]


# ------------------------------------------------------------------ build guide
def _steps(project, variant, arm, design, bom, meshes, img, ev, task) -> tuple[list[dict], dict]:
    is_ref = arm.style == "ref_arm"
    STEPS = A.REF_STEPS if is_ref else A.STEPS
    step_of = (lambda p: A.ref_step_of(p)) if is_ref else A.step_of
    bom_item = (lambda r, p: p.bom_item) if is_ref else (lambda r, p: A.bom_item_for_ref(r))
    part_step = {p.name: step_of(p) for p in design.parts}
    by_step: dict[str, list] = {s: [] for s in STEPS}
    for p in design.parts:
        by_step[part_step[p.name]].append(p)
    item_steps: dict[str, set] = {}
    for p in design.parts:
        item = bom_item(p.ref, p) if p.kind != "printed" else None
        if item:
            item_steps.setdefault(item, set()).add(part_step[p.name])
    bom_steps = A.assign_bom(bom["rows"], item_steps, STEPS,
                             A.REF_EXTRA_BOM_STEP if is_ref else A.EXTRA_BOM_STEP)
    belts = {b["joint"]: b for b in design.belts}
    home = {h["joint"]: h for h in design.info.get("homing", [])}
    pl = C.print_list(project, variant)
    ctx = {"belts": belts, "homing": home, "slide": design.info.get("slide"),
           "threading": A.shaft_threading(design) if not is_ref else {}, "pieces": pl["pieces"],
           "grams": round(pl["grams"]), "ref_arm": is_ref,
           "material": design.material, "homing_order": design.info.get("homing_order"),
           "inserts": next((r["qty"] for r in bom["rows"] if r["item"].startswith("M3 brass heat-set")), "?")}
    steps, done = [], set()
    ids = list(STEPS)
    for k, sid in enumerate(ids, 1):
        ps = by_step[sid]
        names = {p.name for p in ps}
        printed = Counter(p.ref for p in ps if p.kind == "printed")
        hw = Counter()
        for p in ps:
            if p.kind != "printed":
                it = bom_item(p.ref, p)
                if it is None and not is_ref and A.part_of_bom_item(p.ref):
                    continue                            # e.g. a switch's lever: comes with the switch
                hw[it or p.ref.replace("_", " ")] += 1
        for item, sids in bom_steps.items():           # BOM lines that are not CAD parts
            if sid in sids and item not in item_steps:
                q = next(r["qty"] for r in bom["rows"] if r["item"] == item)
                hw[item] += q
        image, caption = None, ""
        if names or sid == "tension" or sid == "home":
            ev.progress(task, f"rendering step {k}: {STEPS[sid]}", 0.35 + 0.3 * k / len(ids))
            image = f"img/step_{k:02d}_{sid}.png"
            if names:
                F.step_render(meshes, names, done, img.parent / image, explode_m=0.05 if done else 0.0)
                caption = ("BLUE = ADDED IN THIS STEP" + (" (MOVED OUT FOR CLARITY)" if done else "") +
                           " · GREY = ALREADY ASSEMBLED · ARM IN THE READY POSE")
            else:                                       # tension/home: highlight the belts in place
                belts_ = {p.name for p in design.parts if p.kind == "belt"}
                F.step_render(meshes, belts_, done - belts_, img.parent / image, explode_m=0.0, focus=1.0)
                caption = "BLUE = BELTS TO TENSION · ARM IN THE READY POSE"
        steps.append({"n": k, "id": sid, "title": STEPS[sid], "image": image, "caption": caption,
                      "printed": [[r, n] for r, n in printed.items()],
                      "hardware": [[i, n] for i, n in hw.items()],
                      "instructions": (A.ref_step_instructions if is_ref else A.step_instructions)(sid, ctx),
                      "parts": sorted(names),
                      "bom_items": sorted(i for i, s in bom_steps.items() if sid in s)})
        done |= names
    return steps, {"bom_steps": bom_steps, "part_step": part_step, "ctx": ctx}


def build_guide_data(project: Project, variant: str, out: Path, arm, design, meshes, ev, task, meta) -> dict:
    vdir = project.variant_dir(variant)
    img = out / "img"
    bom = C.bom(project, variant)
    pl = C.print_list(project, variant)
    mp = C.mass_props(project, variant)
    reports = C.sim_reports(project, variant)
    ctl = C.control(project, variant)
    if not bom["rows"] or not pl["rows"]:
        raise DocError(f"design/{variant} has no bom.csv / print_list.csv: run `mechy cad build {variant}` first")

    ev.progress(task, "rendering the cover", 0.08)
    F.full_render(meshes, img / "cover.png")
    steps, sinfo = _steps(project, variant, arm, design, bom, meshes, img, ev, task)
    step_of_ref = {}
    for s in steps:
        for r, _ in s["printed"]:
            step_of_ref.setdefault(r, s)

    parts = []
    for k, r in enumerate(pl["rows"]):
        ev.progress(task, f"drawing part {r['part']}", 0.1 + 0.25 * k / len(pl["rows"]))
        stl = vdir / r["stl"]
        if not stl.exists():
            raise DocError(f"{r['stl']} is missing: run `mechy cad build {variant}`")
        dr = F.part_drawing(stl, img / f"part_{r['part']}.svg")
        st = step_of_ref.get(r["part"], {"n": "-", "title": "-"})
        notes = [f"Print {r['qty']} x in {r['material']}, {r['orientation']}. The dashed BED line is the print bed.",
                 f"Overall size {' x '.join(f'{x:.1f}' for x in dr['dims_mm'])} mm in the print orientation "
                 "(measured from the STL).",
                 f"Mass {r['grams']:.1f} g each is computed from volume x density x shell/infill factor "
                 "(estimate until weighed)."]
        parts.append({**r, "ref": r["part"], "drawing": f"img/part_{r['part']}.svg", "dims_mm": dr["dims_mm"],
                      "scale": dr["scale"], "step": st["n"], "step_title": st["title"], "notes": notes})

    s0 = reports[0] if reports else None
    stats = [{"l": "reach", "v": f"{arm.reach:.3f} m", "note": "computed"},
             {"l": "printed parts", "v": f"{pl['pieces']} pcs / {pl['grams']:.0f} g", "note": "estimate"},
             {"l": "purchased parts", "v": f"{bom['lines']} lines / ${bom['total_usd']:.0f}", "note": "estimate"},
             {"l": "assembly", "v": f"{len(steps)} steps"}]
    if s0:
        stats.insert(1, {"l": "simulated catch rate", "v": f"{s0['catch_rate'] * 100:.1f}%",
                         "note": f"{s0['throws']} throws, {s0['_task']}"})
    pk0 = (C.pick_reports(project, variant) or [None])[0]
    if pk0:
        stats.insert(1, {"l": "payload / cycle", "v": f"{pk0['payload_capacity_g']:.0f} g / {pk0['cycle_s']:.1f} s",
                         "note": f"computed, {pk0['_task']}"})
    joints = ", ".join(f"{j['name']} {j['gear_ratio']:g}:1" for j in arm.params["joints"])
    cover_notes = [f"Belt-driven 4-DOF arm ({joints}); every motor sits low, joints turn on 608-2RS / 688-2RS "
                   "bearings, GT2 closed belts.",
                   f"Built from design/{variant}/params.yaml by mechy cad build {variant}; numbers on these "
                   "sheets come from the project files named on each sheet.",
                   "Estimates are labelled. Read the last sheet (checks, not verified, open decisions) before buying."]

    what_where = [
        {"what": "Design parameters", "where": f"design/{variant}/params.yaml", "rebuild": "edit, then the commands below"},
        {"what": "Assembly CAD", "where": f"design/{variant}/arm.step, arm.glb, arm.stl", "rebuild": f"mechy cad build {variant}"},
        {"what": "Printable parts", "where": f"design/{variant}/stl/*.stl ({pl['stls']} files)", "rebuild": f"mechy cad build {variant}"},
        {"what": "Print list", "where": pl["source"], "rebuild": f"mechy cad build {variant}"},
        {"what": "Bill of materials", "where": bom["source"], "rebuild": f"mechy cad build {variant}"},
        {"what": "Mass properties, belts, homing", "where": f"design/{variant}/mass_props.json", "rebuild": f"mechy cad build {variant}"},
    ]
    if s0:
        what_where.append({"what": "Catch simulation", "where": f"sim/{s0['_task']}/report.json",
                           "rebuild": f"mechy sim catch {variant}"})
    if pk0:
        what_where.append({"what": "Pick-and-place study", "where": f"sim/{pk0['_task']}/report.json",
                           "rebuild": f"mechy sim pick {variant}"})
    if ctl["present"]:
        what_where.append({"what": "Firmware, host, wiring", "where": f"control/{variant}/",
                           "rebuild": f"mechy control gen {variant}"})
    what_where += [{"what": "This guide", "where": f"docs/{variant}/build_guide.pdf (.typ, .data.json, img/)",
                    "rebuild": f"mechy doc build {variant}"},
                   {"what": "Design report", "where": f"docs/{variant}/report.pdf", "rebuild": f"mechy doc build {variant}"}]

    sl = design.info.get("slide")
    slide = None
    if sl:
        sp = sl["spring"]
        slide = [["guide", sl["rods"] + "; " + sl["bearings"]],
                 ["springs", f"{sl['n_springs']} x {sp['id']} ({sp['rate_n_per_mm']} N/mm, free {sp['free_mm']:g} mm, "
                             f"min {sp['min_work_mm']} mm; datasheet)"],
                 ["stiffness", f"{sl['k_hw_n_per_m']:.0f} N/m (computed)"],
                 ["travel / preload", f"{sl['travel_m'] * 1000:.0f} mm / {sl['preload_n']:.2f} N (computed)"],
                 ["end stops", sl["end_stops"]],
                 ["brake drag", f"{sl['brake_drag_target_n']} N total (estimate; set with a scale)"],
                 ["rest offset", f"up to {sl['rest_offset_max_mm']} mm behind the front stop after a catch"]]
    mm = mp.get("motor_map", {})
    motor_notes = []
    if mm:
        motor_notes = [mm.get("note", ""), mm.get("formula", ""),
                       "Steps per degree of the motor-side angle at " + str(mm.get("microsteps", "?")) + " microsteps: " +
                       ", ".join(f"{n} {s:g}" for n, s in zip(mm.get("joint_names", []), mm.get("steps_per_deg", [])))]
    tension = [x for x in A.step_instructions("tension", sinfo["ctx"])]

    # checks (standards rule 5 table shape)
    checks = []
    bom_csv_total = round(sum(C.num(r["qty"]) * C.num(r["est_unit_usd"]) for r in C.read_csv(project.variant_dir(variant) / "bom.csv")), 2)
    checks.append({"check": "BOM total on this guide = bom.csv", "expected": f"${bom_csv_total:.2f}",
                   "got": f"${bom['total_usd']:.2f}", "status": "PASS" if abs(bom_csv_total - bom["total_usd"]) < 0.005 else "FAIL"})
    missing = [r["part"] for r in pl["rows"] if not (vdir / r["stl"]).exists()]
    checks.append({"check": "Every print-list part has an STL and a part sheet", "expected": f"{pl['stls']}",
                   "got": f"{len(parts)} sheets, {len(missing)} missing STLs", "status": "PASS" if not missing and len(parts) == pl["stls"] else "FAIL"})
    printed_inst = sum(1 for p in design.parts if p.kind == "printed")
    checks.append({"check": "Printed pieces: print list = CAD", "expected": str(printed_inst), "got": str(pl["pieces"]),
                   "status": "PASS" if printed_inst == pl["pieces"] else "FAIL"})
    covered = sum(len(s["parts"]) for s in steps)
    checks.append({"check": "Every CAD part is installed in exactly one step", "expected": str(len(design.parts)),
                   "got": str(covered), "status": "PASS" if covered == len(design.parts) else "FAIL"})
    unplaced = [i for i, s in sinfo["bom_steps"].items() if not s]
    checks.append({"check": "Every BOM line is used by a step", "expected": f"{bom['lines']} lines",
                   "got": "all" if not unplaced else "missing: " + ", ".join(unplaced),
                   "status": "PASS" if not unplaced else "FAIL"})
    ph = mp.get("params_hash")
    checks.append({"check": "CAD outputs match params.yaml", "expected": meta["params_hash"],
                   "got": f"mass_props.json {ph}", "status": "PASS" if ph == meta["params_hash"] else "FAIL"})
    checks += C.homing_check(mp, ctl)

    nv, od = C.gaps(project, variant, reports)
    for c in checks:
        if c["status"] == "FAIL":
            od.insert(0, {"source": "check", "text": f"{c['check']}: expected {c['expected']}, {c['got']}. Fix "
                          "before building."})
    if not ctl["present"]:
        od.append({"source": "control", "text": f"No firmware yet: run `{ctl['command']}`."})
    printer = [{"k": "material", "v": design.material},
               {"k": "infill", "v": f"{design.infill:.0%} (grid or gyroid)"},
               {"k": "walls / top / bottom", "v": f"{design.shell_mm} mm per face (2 perimeters of a 0.4 mm nozzle)"},
               {"k": "layer height", "v": "0.2 mm (suggested; the CAD does not depend on it)"},
               {"k": "supports", "v": "none expected in the listed orientation (check the bearing bores)"},
               {"k": "nozzle / bed", "v": "PETG: about 235 / 80 C (typical; use your filament's values)"}]
    return {
        "meta": meta,
        "cover": {"image": "img/cover.png", "title": f"{meta['project']} {variant}",
                  "subtitle": "4-DOF belt-driven catching arm", "stats": stats, "notes": cover_notes},
        "reading_notes": ["Sheets are A4 landscape. Part sheets are true to scale when printed at 100% (scale in "
                          "the title block); dimensions are in mm.",
                          "Third-angle projection: TOP above FRONT, RIGHT beside it. The iso view is not to scale.",
                          "Assembly sheets: blue parts are added in that step (moved out a little for clarity).",
                          "Every number is computed, from a datasheet, or labelled an estimate; the source file is "
                          "named on each sheet."],
        "what_where": what_where,
        "bom": {**bom, "notes": [
            "Quantities include the spares named in each spec. Unit prices are estimates for Amazon/AliExpress "
            "parts (not quotes).",
            f"Total = sum of qty x unit price over all {bom['lines']} lines of {bom['source']}."]},
        "print": {**pl, "settings": printer, "notes": [
            f"Grams are computed from each STL's volume x {design.material} density x a shell/infill factor "
            "(estimate until weighed).",
            "Orientation is chosen for strength along the load path and bearing-seat roundness; keep it."]},
        "parts": parts,
        "steps": steps,
        "belts": [{"joint": b["joint"], "pulleys": f"{b['teeth'][0]}T-{b['teeth'][1]}T", "centre_mm": b["centre_mm"],
                   "computed_mm": b["computed_mm"], "standard_mm": b["standard_mm"], "note": b.get("note", "")}
                  for b in design.belts],
        "tension_notes": tension,
        "slide": slide,
        "homing": mp.get("homing", design.info.get("homing", [])),
        "homing_order": list(design.info.get("homing_order") or [h["joint"] for h in mp.get("homing", [])]),
        "motor_notes": [x for x in motor_notes if x],
        "control": ctl,
        "checks": checks,
        "not_verified": nv,
        "open_decisions": od,
    }


# ------------------------------------------------------------------ report
def pick_section(pk: dict, pr: dict, img: Path, reqs: list, findings: list, figs: dict) -> dict:
    """Pick-and-place study (`mechy sim pick`): requirement rows, findings and the three plots."""
    import shutil
    task = pk["_task"]
    for name in pk.get("plots", []):
        shutil.copyfile(pk["_dir"] / name, img / f"pick_{Path(name).name}")
        figs["pick_" + Path(name).stem] = f"img/pick_{Path(name).name}"
    h = pk["headline"]
    cyc_t = pr.get("target_cycle_s")
    peak = max(pk["peak_motor_load"].values())
    reqs.append({"req": "Payload in the work zone", "target": f">= {h['target']:.0f} g" if h.get("target") else "-",
                 "result": f"{h['value']:.0f} g (weakest pose of the cycle)",
                 "status": "PASS" if h.get("meets") else "FAIL", "source": f"sim/{task}/report.json"})
    if cyc_t:
        reqs.append({"req": "Cycle time", "target": f"<= {float(cyc_t):.1f} s",
                     "result": f"{pk['cycle_s']:.2f} s with {pk['design_payload_g']:.0f} g",
                     "status": "PASS" if pk["cycle_s"] <= float(cyc_t) else "FAIL", "source": f"sim/{task}/report.json"})
    reqs.append({"req": "Motor load, whole cycle", "target": "< 100% of pull-out",
                 "result": f"peak {peak * 100:.0f}% ({pk['worst_joint']})",
                 "status": "PASS" if peak < 1.0 else "FAIL", "source": f"sim/{task}/report.json"})
    findings.append(f"Carries {pk['design_payload_g']:.0f} g through a {pk['cycle_s']:.2f} s pick-and-place cycle "
                    f"({pk['picks_per_min']:.0f}/min); peak motor load {peak * 100:.0f}% of pull-out, worst on the "
                    f"{pk['worst_joint']} motor (computed, static torque + stepper curve).")
    findings.append("Motor torque, part masses and gripper time are estimates (see the last sheet).")
    return {"task": task, "payload_g": h["value"], "target_g": h.get("target"), "meets": h.get("meets"),
            "cycle_s": pk["cycle_s"], "picks_per_min": pk["picks_per_min"], "design_g": pk["design_payload_g"],
            "peak": peak, "notes": pk.get("meta", {}).get("estimates", [])}


def report_data(project: Project, variant: str, out: Path, arm, meta, ev, task) -> dict:
    from ..cad.build import torque_budget
    img = out / "img"
    req = project.requirements()
    rc = req.get("catch", {})
    reports = C.sim_reports(project, variant)
    s0 = reports[0] if reports else None
    target = float(rc.get("target_catch_rate", 0.8))
    pk = (C.pick_reports(project, variant) or [None])[0]
    pick_only = bool(pk) and not s0
    pr = req.get("pick", {})
    tb = torque_budget(arm, float(pr.get("payload_kg", 0.2)) if pick_only else float(rc.get("ball_mass_kg", 0.057)))
    figs = {}
    ev.progress(task, "report charts", 0.9)
    margins = [(t["joint"], t["margin"]) for t in tb if t["margin"] is not None]
    F.hbars(margins, img / "torque_margin.svg", ref=1.0, ref_label="BUDGET (50% OF HOLDING x RATIO)", fmt="{:.2f}x")
    figs["torque"] = "img/torque_margin.svg"
    headline, sims, reqs, catch_notes, findings = None, [], [], [], []
    if s0:
        n = int(s0["throws"])
        k = round(s0["catch_rate"] * n)
        lo, hi = C.wilson(k, n)
        st = "PASS" if lo >= target else ("FAIL" if hi < target else "OPEN")
        headline = {"catch_rate": s0["catch_rate"], "ci_low": lo, "ci_high": hi, "target": target, "throws": n,
                    "seed": s0.get("meta", {}).get("seed", "?"), "task": s0["_task"], "status": st}
        th = C.throws(s0)
        F.catch_map(th, arm.reach, arm.base_height, img / "catch_map.svg")
        figs["catch_map"] = "img/catch_map.svg"
        fails = [(kk.replace("_", " "), float(v)) for kk, v in s0.get("failures", {}).items()]
        fails = [("caught", float(k))] + fails
        F.hbars(fails, img / "failures.svg", fmt="{:.0f}", size_mm=(80, 42))
        figs["failures"] = "img/failures.svg"
        catch_notes = [
            "Each mark is one simulated throw at the point where the cup met the ball. Throws with no catch "
            "point (out of reach) are drawn in the top view where the ball landed. Dashed: the arm's reach "
            "(shoulder to cup centre).",
            f"Throws follow requirements.yaml throw: (aim point and spread are assumed), seed {headline['seed']}.",
            f"Skipped steps on ball impact: {s0.get('skip_on_impact_rate', 0) * 100:.0f}% of throws "
            f"(by motor {s0.get('skip_on_impact_by_joint', {})}); the firmware re-homes after those catches.",
        ]
        for r in reports:
            fl = ", ".join(f"{a.replace('_', ' ')} {b}" for a, b in r.get("failures", {}).items() if b)
            sims.append({"task": r["_task"], "throws": r["throws"], "seed": r.get("meta", {}).get("seed", "?"),
                         "catch_rate": r["catch_rate"], "reach_rate": r.get("reach_rate", 0),
                         "skip_on_impact_rate": r.get("skip_on_impact_rate", r.get("skipped_step_rate", 0)),
                         "microsteps": r.get("meta", {}).get("microsteps", "?"), "failures": fl or "none"})
        reqs.append({"req": "Catch rate", "target": f">= {target * 100:.0f}%",
                     "result": f"{s0['catch_rate'] * 100:.1f}% of {n} (95% {lo * 100:.0f}-{hi * 100:.0f}%)",
                     "status": st, "source": f"sim/{s0['_task']}/report.json"})
        if th:
            sp = [float(np.linalg.norm(t["v0"])) for t in th if t.get("v0")]
            vmax = float(rc.get("max_launch_speed_mps", 6.0))
            reqs.append({"req": "Launch speed covered", "target": f"<= {vmax:g} m/s",
                         "result": f"sim throws {min(sp):.1f}-{max(sp):.1f} m/s", "status": "PASS" if max(sp) <= vmax + 1e-9 else "FAIL",
                         "source": f"sim/{s0['_task']}/throws.jsonl"})
            dist = [float(np.hypot(*t["launch"][:2])) for t in th if t.get("launch")]
            reqs.append({"req": "Throw distance", "target": f"{rc.get('throw_distance_m', '?')} m",
                         "result": f"sim launches at {min(dist):.2f}-{max(dist):.2f} m from the base", "status": "INFO",
                         "source": f"sim/{s0['_task']}/throws.jsonl"})
        reqs.append({"req": "Reach rate (target inside reach)", "target": "-",
                     "result": f"{s0.get('reach_rate', 0) * 100:.0f}%", "status": "INFO", "source": f"sim/{s0['_task']}/report.json"})
        findings.append(f"Catches {s0['catch_rate'] * 100:.1f}% of {n} simulated throws against a {target * 100:.0f}% "
                        f"target; the 95% interval is {lo * 100:.0f}-{hi * 100:.0f}% (computed), so "
                        + ("the target is met with margin." if st == "PASS" else
                           "more throws are needed to be sure." if st == "OPEN" else "the target is missed."))
        top = max(((a, b) for a, b in s0.get("failures", {}).items() if b), key=lambda x: x[1], default=None)
        if top:
            findings.append(f"Most failures: {top[0].replace('_', ' ')} ({top[1]} of {n}).")
    elif not pick_only:
        reqs.append({"req": "Catch rate", "target": f">= {target * 100:.0f}%", "result": "not simulated",
                     "status": "OPEN", "source": f"run mechy sim catch {variant}"})
    pick = None
    if pk:
        pick = pick_section(pk, pr, img, reqs, findings, figs)
    cd = float(arm.params.get("catcher", {}).get("diameter_m", 0))
    bd = float(rc.get("ball_diameter_m", 0.067))
    if not pick_only:
        reqs.append({"req": "Ball fits the cup", "target": f"ball {bd * 1000:.0f} mm", "result": f"cup {cd * 1000:.0f} mm inside the liner",
                     "status": "PASS" if cd > bd else "FAIL", "source": f"design/{variant}/params.yaml"})
    for t in tb:
        if t["margin"] is None:
            continue
        reqs.append({"req": f"Torque budget, {t['joint']} motor", "target": ">= 1.0x of 50% budget",
                     "result": f"{t['margin']:.2f}x ({t['gravity_nm']:.3f} of {t['budget_50pct_nm']:.3f} N m)",
                     "status": "PASS" if t["margin"] >= 1.0 else "FAIL", "source": "computed (ArmModel, mass_props.json)"})
    vis = req.get("vision", {})
    reqs.append({"req": "Vision", "target": f"{vis.get('fps', '?')} fps, {float(vis.get('latency_s', 0)) * 1000:.0f} ms",
                 "result": "modelled in the sim (camera noise + latency)", "status": "INFO", "source": "requirements.yaml"})
    worst = min((t for t in tb if t["margin"] is not None), key=lambda t: t["margin"], default=None)
    if worst:
        findings.append(f"Weakest motor: {worst['joint']} at {worst['margin']:.2f}x the 50% torque budget, arm "
                        "stretched horizontally with the " + ("payload" if pick_only else "ball") + " (computed).")

    # where the numbers come from
    hwdir = project.path("hw")
    mot = (project.hardware().get("motors") or [{}])[0]
    drv = (project.hardware().get("drivers") or [{}])[0]
    cat = arm.params.get("catcher", {})
    pl = C.print_list(project, variant)
    bom = C.bom(project, variant)
    est = [] if pick_only else [
        {"quantity": "Catch rate", "value": f"{s0['catch_rate'] * 100:.1f}% ({s0['throws']} throws)" if s0 else "-",
         "label": "computed", "source": f"sim/{s0['_task']}/report.json (MuJoCo + stepper model)" if s0 else "-"}]
    if pick:
        est.append({"quantity": "Payload capacity, cycle time", "value": f"{pk['payload_capacity_g']:.0f} g, {pk['cycle_s']:.2f} s",
                    "label": "computed", "source": f"sim/{pk['_task']}/report.json (static torque + stepper curve)"})
    est += [
        {"quantity": "Motor holding torque", "value": f"{mot.get('holding_torque_nm', '?')} N m", "label": "assumed",
         "source": "hw/motors.yaml: " + (C.yaml_comment(hwdir / "motors.yaml", "holding_torque_nm") or "-")},
        {"quantity": "Motor torque curve", "value": f"{len(mot.get('torque_curve', []))} points", "label": "estimate",
         "source": "hw/motors.yaml: " + (C.yaml_comment(hwdir / "motors.yaml", "torque_curve") or "-")},
        {"quantity": "Step rate cap", "value": f"{drv.get('max_step_rate_hz', 4000)} Hz", "label": "assumed",
         "source": "hw/drivers.yaml: " + (C.yaml_comment(hwdir / "drivers.yaml", "max_step_rate_hz") or "default")},
        {"quantity": "Printed mass", "value": f"{pl['grams']:.0f} g", "label": "computed",
         "source": "volume x density x shell/infill (estimate until weighed)"},
        {"quantity": "Purchased parts", "value": f"${bom['total_usd']:.0f}", "label": "estimate", "source": bom["source"]},
    ]
    if cat.get("compliance") == "spring":
        est += [{"quantity": "Slide spring rate", "value": f"{cat.get('spring_k_n_per_m', '?')} N/m", "label": "datasheet",
                 "source": "RS PRO 821-352 x 2 (mass_props.json slide.spring.source)"},
                {"quantity": "Slide brake drag", "value": f"{cat.get('spring_friction_n', '?')} N", "label": "estimate",
                 "source": "params.yaml catcher.spring_friction_n (sim-only; set on the bench)"}]
    if not pick_only:
        est.append({"quantity": "Cup liner restitution",
                    "value": f"{cat.get('restitution', 0.15 if cat.get('liner') == 'net_pocket' else 0.4)}",
                    "label": "estimate", "source": f"params.yaml catcher.liner = {cat.get('liner', '-')}; drop-test it"})
        est.append({"quantity": "Vision noise", "value": f"{float(vis.get('noise_m', 0.004)) * 1000:.0f} mm",
                    "label": "assumed", "source": "requirements.yaml vision.noise_m"})
    nv, od = C.gaps(project, variant, reports)
    decisions = C.decisions(project)
    return {
        "meta": meta, "title": f"{meta['project']} {variant}", "cover_image": "img/cover.png",
        "headline": headline,
        "stats": [{"l": "reach", "v": f"{arm.reach:.3f} m", "note": "computed"},
                  {"l": "purchased parts", "v": f"${bom['total_usd']:.0f}", "note": "estimate"}],
        "findings": findings, "requirements": reqs, "sims": sims, "figs": figs, "catch_notes": catch_notes,
        "pick": pick,
        "torque": tb,
        "torque_notes": ["Static case: arm stretched horizontally with the ball in the cup, the worst gravity load "
                         "(computed from the CAD masses).",
                         "With belt pass-through each motor holds the motor-side torque C^-T tau, not the joint "
                         "torque (see mass_props.json motor_map).",
                         "Budget = holding torque x ratio x 50% (standards rule 4). Holding torque is assumed until "
                         "the motor model is confirmed."],
        "decisions": decisions, "open_decisions": od, "not_verified": nv, "estimates": est,
        "estimate_notes": ["Labels: COMPUTED = derived by the engine from other files; DATASHEET = vendor figure; "
                           "ASSUMED / ESTIMATE = not measured, change it when you measure."],
    }


# ------------------------------------------------------------------ entry point
def doc_build(project: Project, variant: str, events: Events | None = None, which: str = "all",
              paper: str = "sheet") -> dict:
    """paper: "sheet" (drawing-sheet colour #F5F5F3, the default) or "white" (`--print`, home printers)."""
    from .raster import set_paper
    ev = events or Events(project.root, quiet=True)
    paper_hex = set_paper(paper)
    task = f"doc-{variant}"
    t0 = time.time()
    vdir = project.variant_dir(variant)
    if not (vdir / "params.yaml").exists():
        raise DocError(f"no design/{variant}/params.yaml")
    from ..project import check_variant_style
    check_variant_style(project, variant, "doc build")
    if not ((vdir / "bom.csv").exists() and (vdir / "print_list.csv").exists() and (vdir / "mass_props.json").exists()):
        raise DocError(f"design/{variant} has no bom.csv / print_list.csv / mass_props.json: run "
                       f"`mechy cad build {variant}` first")
    ev.emit("task.started", task=task)
    out = project.path("docs", variant)
    img = out / "img"
    img.mkdir(parents=True, exist_ok=True)
    for old in list(img.glob("*.png")) + list(img.glob("*.svg")):
        old.unlink()                                    # no stale renders from an earlier build
    ev.progress(task, "rebuilding the assembly tree from params.yaml", 0.02)
    arm, design, ph = _design(project, variant)
    meshes = _meshes(arm, design)
    pm = project.meta()
    meta = {"project": str(pm.get("name") or project.root.name), "variant": variant, "date": date.today().isoformat(),
            "params_hash": ph, "paper": paper_hex}
    for name in ("mechy_sheet.typ", "build_guide.typ", "report.typ"):
        shutil.copyfile(TEMPLATES / name, out / name)
    results, warnings = {}, []
    if which in ("all", "build_guide"):
        m = {**meta, "doc": "Build guide", "footer": f"mechy doc build {variant} · mm · third-angle"}
        data = build_guide_data(project, variant, out, arm, design, meshes, ev, task, m)
        (out / "build_guide.data.json").write_text(json.dumps(data, indent=1, default=str))
        ev.progress(task, "typesetting build_guide.pdf", 0.92)
        warnings += compile_typst(out / "build_guide.typ", out / "build_guide.pdf")
        results["build_guide"] = {"pdf": ev.rel(out / "build_guide.pdf"), "pages": pdf_pages(out / "build_guide.pdf"),
                                  "parts": len(data["parts"]), "steps": len(data["steps"]),
                                  "bom_total_usd": data["bom"]["total_usd"],
                                  "checks_failed": [c["check"] for c in data["checks"] if c["status"] == "FAIL"]}
    if which in ("all", "report"):
        if not (img / "cover.png").exists():
            F.full_render(meshes, img / "cover.png")
        m = {**meta, "doc": "Design report", "footer": f"mechy doc build {variant} · SI units"}
        data = report_data(project, variant, out, arm, m, ev, task)
        (out / "report.data.json").write_text(json.dumps(data, indent=1, default=str))
        ev.progress(task, "typesetting report.pdf", 0.97)
        warnings += compile_typst(out / "report.typ", out / "report.pdf")
        results["report"] = {"pdf": ev.rel(out / "report.pdf"), "pages": pdf_pages(out / "report.pdf"),
                             "catch_rate": (data["headline"] or {}).get("catch_rate")}
    for f in sorted(out.glob("*.pdf")) + sorted(out.glob("*.typ")) + sorted(out.glob("*.data.json")):
        ev.file_written(f)
    ev.emit("task.done", task=task, summary=ev.rel(out / "build_guide.pdf"))
    warnings = [w for w in warnings if "unknown font family" not in w]
    return {"variant": variant, "dir": ev.rel(out), "paper": paper, **results, "warnings": warnings[:10],
            "duration_s": round(time.time() - t0, 1)}
