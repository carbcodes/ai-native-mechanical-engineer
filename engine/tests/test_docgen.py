"""Documents: `mechy doc build` writes the build guide and report PDFs from the project files."""

import csv
import json

import numpy as np
import pytest

from conftest import mechy
from mechy.cad.build import cad_build
from mechy.control.generate import control_gen
from mechy.docgen import collect as C
from mechy.docgen import doc_build
from mechy.docgen.assembly import STEPS
from mechy.docgen.raster import read_stl
from mechy.project import init_project
from mechy.sim.catch import run_catch


@pytest.fixture(scope="module")
def docs(tmp_path_factory):
    """Example v2: cad build, a short sim, control gen, then doc build (shared by this module)."""
    root = tmp_path_factory.mktemp("docs") / "proj"
    proj = init_project(root, example="tennis-catcher", git=False)
    cad_build(proj, "v2")
    run_catch(proj, "v2", throws=12, seed=0, workers=2)
    control_gen(proj, "v2")
    res = doc_build(proj, "v2")
    out = proj.path("docs", "v2")
    guide = json.loads((out / "build_guide.data.json").read_text())
    report = json.loads((out / "report.data.json").read_text())
    return proj, res, out, guide, report


def _pdf_text(pdf):
    pypdf = pytest.importorskip("pypdf")
    r = pypdf.PdfReader(str(pdf))
    return [p.extract_text() or "" for p in r.pages]


def test_pdfs_produced(docs):
    proj, res, out, guide, report = docs
    for name in ("build_guide", "report"):
        pdf = out / f"{name}.pdf"
        assert pdf.read_bytes()[:5] == b"%PDF-"
        assert (out / f"{name}.typ").exists() and (out / f"{name}.data.json").exists()
    # cover + contents + BOM + print list + 19 parts + 11 steps + belts + wiring + calibration + checks
    n_min = 4 + len(guide["parts"]) + len(STEPS) + 3
    assert res["build_guide"]["pages"] >= n_min
    assert res["report"]["pages"] >= 6
    pages = _pdf_text(out / "build_guide.pdf")
    assert len(pages) == res["build_guide"]["pages"]
    assert all("SHEET" in p.upper() and "V2" in p.upper() for p in pages)        # title block on every page


def test_bom_totals_match_csv(docs):
    proj, res, out, guide, report = docs
    rows = list(csv.DictReader(open(proj.variant_dir("v2") / "bom.csv")))
    total = sum(float(r["qty"]) * float(r["est_unit_usd"]) for r in rows)
    assert guide["bom"]["lines"] == len(rows)
    assert guide["bom"]["pieces"] == sum(int(r["qty"]) for r in rows)
    assert guide["bom"]["total_usd"] == pytest.approx(total, abs=0.005)
    assert res["build_guide"]["bom_total_usd"] == pytest.approx(total, abs=0.005)
    text = "\n".join(_pdf_text(out / "build_guide.pdf"))
    assert f"{total:.2f}" in text
    assert f"TOTAL: {len(rows)} LINES" in text
    for r in rows:                                     # every BOM line is printed
        assert r["item"].split()[0] in text


def test_every_printed_part_has_a_sheet(docs):
    typst = pytest.importorskip("typst")
    proj, res, out, guide, report = docs
    vdir = proj.variant_dir("v2")
    printed = [r["part"] for r in csv.DictReader(open(vdir / "print_list.csv"))]
    sheets = json.loads(typst.query(str(out / "build_guide.typ"), "<sheet>", field="value", root=str(out)))
    tags = [s.get("tag") for s in sheets]
    for part in printed:
        assert tags.count(f"part {part}") == 1, part
    for p in guide["parts"]:
        assert (out / p["drawing"]).exists()
        v, _ = read_stl(vdir / "stl" / f"{p['ref']}.stl")
        assert np.allclose(p["dims_mm"], np.round(v.max(0) - v.min(0), 1), atol=0.06)
        assert p["scale"] != "NTS" and isinstance(p["step"], int)
    scales = {s["tag"]: s["scale"] for s in sheets if (s.get("tag") or "").startswith("part ")}
    assert all(":" in sc for sc in scales.values())


def test_assembly_steps_cover_every_part(docs):
    from mechy.arm_model import load_arm
    from mechy.cad.belt_arm import build_design
    proj, res, out, guide, report = docs
    design = build_design(load_arm(proj, "v2"))
    names = [p.name for p in design.parts]
    in_steps = [n for s in guide["steps"] for n in s["parts"]]
    assert sorted(in_steps) == sorted(names)                  # each CAD part exactly once
    assert [s["id"] for s in guide["steps"]] == list(STEPS)
    ids = [s["id"] for s in guide["steps"]]
    assert ids.index("base") < ids.index("turntable") < ids.index("tower") < ids.index("drive") \
        < ids.index("upper_arm") < ids.index("forearm") < ids.index("hand") < ids.index("cup")
    bom_items = {r["item"] for r in guide["bom"]["rows"]}
    assert bom_items == {i for s in guide["steps"] for i in s["bom_items"]}   # every BOM line has a step
    for s in guide["steps"]:
        assert s["instructions"], s["id"]
        if s["parts"]:
            assert (out / s["image"]).exists()
    check = {c["check"]: c["status"] for c in guide["checks"]}
    assert check["Every CAD part is installed in exactly one step"] == "PASS"
    assert check["BOM total on this guide = bom.csv"] == "PASS"
    assert check["CAD outputs match params.yaml"] == "PASS"


def test_guide_and_report_content(docs):
    proj, res, out, guide, report = docs
    assert guide["control"]["present"] and guide["control"]["wiring"]["rows"]
    assert len(guide["homing"]) == 4 and guide["belts"]
    # control gen reads the CAD homing table, so the guide's CAD-vs-firmware homing checks all pass
    home = [c for c in guide["checks"] if " home: " in c["check"]]
    assert len(home) == 4 and all(c["status"] == "PASS" for c in home), home
    assert not [c for c in res["build_guide"]["checks_failed"] if " home: " in c]
    assert guide["not_verified"] and guide["open_decisions"]
    sim = json.loads(proj.path("sim", "catch-v2", "report.json").read_text())
    assert report["headline"]["catch_rate"] == sim["catch_rate"]
    lo, hi = report["headline"]["ci_low"], report["headline"]["ci_high"]
    assert lo <= sim["catch_rate"] <= hi
    assert any(r["req"] == "Catch rate" for r in report["requirements"])
    assert {t["joint"] for t in report["torque"]} == {"base", "shoulder", "elbow", "wrist"}
    assert len(report["decisions"]) >= 5 and all("[evidence]" not in d["why"] for d in report["decisions"])
    assert any(e["label"] == "estimate" for e in report["estimates"])
    text = "\n".join(_pdf_text(out / "report.pdf"))
    assert "Requirements vs results" in text and "Torque margins" in text


def test_wilson_interval():
    lo, hi = C.wilson(46, 50)
    assert lo == pytest.approx(0.8113, abs=1e-3) and hi == pytest.approx(0.9685, abs=1e-3)   # published formula
    assert C.wilson(0, 0) == (0.0, 1.0)


def test_md_sections():
    text = ("# X\n\nNot verified: belt stretch; printed teeth (estimate).\n\nOpen decisions\n- one\n- two\n  more\n"
            "- none\n\n## Not verified\n\n- firmware on hardware\n")
    assert C.md_section(text, ("not verified",)) == ["belt stretch.", "printed teeth (estimate).",
                                                    "firmware on hardware"]
    assert C.md_section(text, ("open decisions",)) == ["one", "two more"]


def test_cli_needs_cad_first(project):
    code, _, res = mechy("doc", "build", "v2", "--project", str(project.root))
    assert code == 1 and not res["ok"] and "cad build v2" in res["error"]


def test_print_paper_is_white(docs):
    """`--print` (paper="white"): white pages and render backgrounds; the default stays the sheet colour."""
    proj, res, out, guide, report = docs
    assert guide["meta"]["paper"] == "#F5F5F3" and res["paper"] == "sheet"
    r = doc_build(proj, "v2", which="report", paper="white")
    assert r["paper"] == "white"
    assert json.loads((out / "report.data.json").read_text())["meta"]["paper"] == "#FFFFFF"
    from mechy.docgen.raster import paper, set_paper
    assert paper() == (1.0, 1.0, 1.0)
    set_paper("sheet")
    with pytest.raises(ValueError):
        set_paper("pink")
