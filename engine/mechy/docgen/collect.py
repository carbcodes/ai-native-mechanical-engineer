"""Read what the other engine commands wrote (bom.csv, print_list.csv, mass_props.json, summaries,
sim reports, control README) into plain data for the documents. Nothing here invents numbers: every
value comes from a project file, and each list keeps the file it came from."""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path

from ..project import Project, load_yaml


def read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def num(x, default=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def plain(text: str) -> str:
    """Markdown inline -> plain text (the documents set their own emphasis)."""
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = text.replace("**", "").replace("`", "")
    return re.sub(r"\s+", " ", text).strip()


# ------------------------------------------------------------------ markdown
def md_tables(text: str) -> list[dict]:
    """Every pipe table in a markdown text: {"heading", "header", "rows"} (heading = nearest # line above)."""
    out, heading, lines = [], "", text.splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("#"):
            heading = ln.lstrip("#").strip()
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?\s*:?-{2,}", lines[i + 1].strip()):
            def cells(s):
                return [plain(c) for c in s.strip().strip("|").split("|")]
            header = cells(ln)
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            out.append({"heading": heading, "header": header, "rows": rows})
            continue
        i += 1
    return out


def md_section(text: str, names: tuple[str, ...]) -> list[str]:
    """Items under a 'Not verified' / 'Open decisions' style section: a heading or a line starting with
    one of `names`, followed by bullets (or the rest of the paragraph). Returns plain-text items."""
    lines = text.splitlines()
    items: list[str] = []
    for i, raw in enumerate(lines):
        key = raw.strip().lstrip("#").strip().strip("*").strip()
        low = key.lower()
        name = next((n for n in names if low.startswith(n)), None)
        if not name:
            continue
        rest = key[len(name):].lstrip(" :*").strip()
        para = [rest] if rest else []
        j = i + 1
        bullets: list[str] = []
        while j < len(lines):
            s = lines[j]
            if not s.strip():
                if bullets or para:
                    break
                j += 1
                continue
            if s.lstrip().startswith("#"):
                break
            if re.match(r"^\s*[-*] ", s):
                bullets.append(s.strip()[2:])
            elif bullets and s.startswith("  "):
                bullets[-1] += " " + s.strip()
            elif bullets:
                break
            else:
                para.append(s.strip())
            j += 1
        if bullets:
            items += [plain(b) for b in bullets]
        if para:
            p = plain(" ".join(para))
            # "a; b; c." paragraphs become separate items
            items += [x.strip().rstrip(".") + "." for x in re.split(r";\s+(?=[a-z])", p) if x.strip()]
    return [x for x in items if x.strip(" .-").lower() not in ("", "none")]


def md_code_blocks(text: str) -> list[str]:
    return [m.group(1).strip("\n") for m in re.finditer(r"```[a-z]*\n(.*?)```", text, re.S)]


def md_numbered(text: str, heading_prefix: str) -> list[str]:
    """Numbered list items under the first heading that starts with heading_prefix."""
    m = re.search(rf"^#+\s*{re.escape(heading_prefix)}.*$", text, re.M | re.I)
    if not m:
        return []
    body = text[m.end():]
    nxt = re.search(r"^#+\s", body, re.M)
    body = body[: nxt.start()] if nxt else body
    items: list[str] = []
    for ln in body.splitlines():
        mm = re.match(r"^\s*\d+\.\s+(.*)", ln)
        if mm:
            items.append(mm.group(1))
        elif items and ln.startswith("   ") and ln.strip():
            items[-1] += " " + ln.strip()
    return [plain(x) for x in items]


def md_paragraphs_under(text: str, heading_prefix: str) -> list[str]:
    m = re.search(rf"^#+\s*{re.escape(heading_prefix)}.*$", text, re.M | re.I)
    if not m:
        return []
    body = text[m.end():]
    nxt = re.search(r"^#+\s", body, re.M)
    body = body[: nxt.start()] if nxt else body
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    return [plain(p) for p in re.split(r"\n\s*\n", body) if p.strip() and not p.strip().startswith("|")]


# ------------------------------------------------------------------ project data
def bom(project: Project, variant: str) -> dict:
    rows = read_csv(project.variant_dir(variant) / "bom.csv")
    out = []
    for k, r in enumerate(rows, 1):
        q, u = int(num(r.get("qty"))), num(r.get("est_unit_usd"))
        out.append({"line": k, "item": r.get("item", ""), "qty": q, "spec": r.get("spec", ""),
                    "used_for": r.get("used_for", ""), "source": r.get("source", ""),
                    "unit_usd": round(u, 2), "ext_usd": round(q * u, 2)})
    return {"rows": out, "lines": len(out), "pieces": sum(r["qty"] for r in out),
            "total_usd": round(sum(r["ext_usd"] for r in out), 2), "source": f"design/{variant}/bom.csv"}


def print_list(project: Project, variant: str) -> dict:
    rows = read_csv(project.variant_dir(variant) / "print_list.csv")
    out = []
    for r in rows:
        out.append({"part": r["part"], "qty": int(num(r.get("qty"), 1)), "material": r.get("material", ""),
                    "orientation": r.get("orientation", ""), "grams": num(r.get("est_grams")),
                    "grams_total": num(r.get("est_grams_total")), "infill": r.get("infill", ""),
                    "volume_cm3": num(r.get("volume_cm3")), "stl": r.get("stl", f"stl/{r['part']}.stl")})
    return {"rows": out, "stls": len(out), "pieces": sum(r["qty"] for r in out),
            "grams": round(sum(r["grams_total"] for r in out), 1), "source": f"design/{variant}/print_list.csv"}


def mass_props(project: Project, variant: str) -> dict:
    p = project.variant_dir(variant) / "mass_props.json"
    return json.loads(p.read_text()) if p.exists() else {}


def sim_reports(project: Project, variant: str) -> list[dict]:
    """report.json of every sim task for this variant, the default task (catch-<variant>) first,
    then newest first."""
    out = []
    for rp in project.path("sim").glob("*/report.json"):
        try:
            r = json.loads(rp.read_text())
        except json.JSONDecodeError:
            continue
        if r.get("variant") != variant or r.get("kind") == "pick":
            continue                                    # pick-and-place reports have their own helper
        r["_task"] = rp.parent.name
        r["_dir"] = rp.parent
        r["_mtime"] = rp.stat().st_mtime
        out.append(r)
    out.sort(key=lambda r: (r["_task"] != f"catch-{variant}", -r["_mtime"]))
    return out


def pick_reports(project: Project, variant: str) -> list[dict]:
    """report.json of every `mechy sim pick` task for this variant, newest first."""
    out = []
    for rp in project.path("sim").glob("*/report.json"):
        try:
            r = json.loads(rp.read_text())
        except json.JSONDecodeError:
            continue
        if r.get("variant") != variant or r.get("kind") != "pick":
            continue
        r["_task"], r["_dir"], r["_mtime"] = rp.parent.name, rp.parent, rp.stat().st_mtime
        out.append(r)
    out.sort(key=lambda r: -r["_mtime"])
    return out


def throws(report: dict) -> list[dict]:
    p = Path(report["_dir"]) / "throws.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval of a rate k/n (computed)."""
    if n <= 0:
        return 0.0, 1.0
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def decisions(project: Project) -> list[dict]:
    p = project.path("decisions.md")
    if not p.exists():
        return []
    out = []
    for ln in p.read_text().splitlines():
        m = re.match(r"^\s*-\s*(\d{4}-\d{2}-\d{2}):\s*(.*)$", ln)
        if not m:
            continue
        body = m.group(2)
        ev = re.search(r"\[evidence\]\(([^)]+)\)", body)
        body = re.sub(r"\s*\[evidence\]\([^)]+\)", "", body).strip()
        why = re.search(r"\(why:\s*(.*)\)\s*$", body)
        text = body[: why.start()] if why else body
        out.append({"date": m.group(1), "text": plain(text), "why": plain(why.group(1)) if why else "",
                    "evidence": ev.group(1) if ev else ""})
    return out


def summaries(project: Project, variant: str, reports: list[dict]) -> list[tuple[str, str]]:
    """(project-relative path, text) of the summaries that describe this variant."""
    paths = [f"design/{variant}/summary.md"] + [f"sim/{r['_task']}/summary.md" for r in reports[:1]] + \
        [f"control/{variant}/summary.md", f"control/{variant}/README.md"]
    out = []
    for rel in paths:
        p = project.path(rel)
        if p.exists():
            out.append((rel, p.read_text()))
    return out


def gaps(project: Project, variant: str, reports: list[dict]) -> tuple[list[dict], list[dict]]:
    """("Not verified" items, "Open decisions" items), each {"source", "text"}, de-duplicated."""
    nv, od, seen = [], [], set()
    for rel, text in summaries(project, variant, reports):
        for item in md_section(text, ("not verified", "open issues")):
            if item.lower() not in seen:
                seen.add(item.lower())
                nv.append({"source": rel, "text": item})
        for item in md_section(text, ("open decisions", "warnings / open decisions")):
            if item.lower() not in seen:
                seen.add(item.lower())
                od.append({"source": rel, "text": item})
    chosen = project.chosen()
    if chosen != variant:
        od.append({"source": "design/chosen", "text": f"design/chosen says {chosen or 'nothing'}; this document "
                   f"describes {variant}. Choose it (write {variant} to design/chosen) before building."})
    for folder, key in (("questions", "answer"), ("options", "chosen")):
        for p in sorted(project.path(folder).glob("*.yaml")):
            d = load_yaml(p) or {}
            if d.get(key) is None:
                od.append({"source": f"{folder}/{p.name}", "text": plain(str(d.get("text") or d.get("prompt") or p.stem))})
    return nv, od


def yaml_comment(path: Path, key: str) -> str:
    """Inline comment after `key:` in a YAML file (labels like 'assumed' or 'estimate' live there)."""
    if not path.exists():
        return ""
    for ln in path.read_text().splitlines():
        m = re.match(rf"^\s*-?\s*{re.escape(key)}\s*:[^#]*#\s*(.*)$", ln)
        if m:
            return m.group(1).strip()
    return ""


def control(project: Project, variant: str) -> dict:
    p = project.path("control", variant, "README.md")
    if not p.exists():
        return {"present": False, "command": f"mechy control gen {variant}"}
    text = p.read_text()
    tables = md_tables(text)
    wiring = next((t for t in tables if t["heading"].lower().startswith("wiring")), None)
    vref = next((t for t in tables if "vref" in t["heading"].lower()), None)
    title = next((ln.lstrip("# ").strip() for ln in text.splitlines() if ln.startswith("# ")), "")
    flashing = md_paragraphs_under(text, "Flashing")
    codes = []
    m = re.search(r"^#+\s*Flashing.*?(?=^#+\s)", text, re.M | re.S)
    if m:
        codes = md_code_blocks(m.group(0))
    bullets = []
    m = re.search(r"^## Wiring.*?(?=^#+\s)", text, re.M | re.S)
    if m:
        bullets = [plain(b) for b in re.findall(r"^- (.*(?:\n  .*)*)", m.group(0), re.M)]
    return {"present": True, "source": f"control/{variant}/README.md", "title": plain(title),
            "wiring": wiring, "vref": vref, "wiring_notes": bullets, "flashing": flashing, "code": codes,
            "calibration": md_numbered(text, "Calibration")}


def homing_check(mp: dict, ctl: dict) -> list[dict]:
    """Compare the CAD homing sensors (mass_props.json homing) with the firmware's switch angles (control
    README wiring table). Rows in the standards verification-table shape."""
    rows = []
    w = ctl.get("wiring") if ctl.get("present") else None
    if not w or not mp.get("homing"):
        return rows
    hdr = [h.lower() for h in w["header"]]
    try:
        jcol, scol = hdr.index("joint"), next(i for i, h in enumerate(hdr) if h.startswith("switch at"))
    except (ValueError, StopIteration):
        return rows
    fw = {}
    for r in w["rows"]:
        name = r[jcol].split()[-1]
        cell = r[scol]
        m = re.search(r"(-?\d+(?:\.\d+)?)\s*deg", cell)
        c = re.search(r"\b([qa]\d)\s*=", cell)
        if m:
            fw[name] = (float(m.group(1)), cell, c.group(1) if c else None)

    def coords(text: str) -> set:
        """'q1 = a1' -> {q1, a1}; 'a2 = q1+q2' -> {a2}; 'q3 (then ...)' -> {q3}."""
        head = text.split("(")[0]
        toks = re.findall(r"[qa]\d", head)
        if not toks:
            return set()
        rhs = head.split("=", 1)[1] if "=" in head else ""
        return set(toks) if len(re.findall(r"[qa]\d", rhs)) == 1 and "+" not in rhs else {toks[0]}

    joints = ("base", "shoulder", "elbow", "wrist")
    for h in mp["homing"]:
        j = h["joint"]
        if j not in fw:
            continue
        cad = float(h.get("home_deg", float("nan")))
        angle, cell, fw_coord = fw[j]
        if fw_coord is None and j in joints:       # older READMEs name no coordinate: the joint angle
            fw_coord = f"q{joints.index(j)}"
        is_hall = "hall" in str(h.get("sensor", "")).lower()
        fw_index = "index" in cell.lower() or "hall" in cell.lower()
        ok = abs(angle - cad) < 0.5 and fw_coord in coords(str(h.get("coordinate", ""))) and is_hall == fw_index
        rows.append({"check": f"{j} home: CAD sensor vs firmware switch angle",
                     "expected": f"{h['homes']} ({h['sensor']})", "got": f"firmware: {cell}",
                     "status": "PASS" if ok else "FAIL"})
    return rows
