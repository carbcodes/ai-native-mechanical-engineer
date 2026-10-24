"""The `drone` example and `style: quad_frame` CAD build."""

import json

import pytest
import yaml

from conftest import mechy
from mechy.project import init_project


@pytest.fixture(scope="module")
def drone(tmp_path_factory):
    root = tmp_path_factory.mktemp("drone") / "proj"
    proj = init_project(root, example="drone")
    code, _, res = mechy("cad", "build", "v1", "--project", str(root))
    assert code == 0 and res["ok"], res
    return proj


def test_drone_example_layout(tmp_path):
    root = tmp_path / "d"
    code, _, res = mechy("init", str(root), "--example", "drone", "--name", "Quad", "--json")
    assert code == 0 and res["ok"] and res["example"] == "drone" and res["name"] == "Quad"
    for f in ["brief.md", "requirements.yaml", "decisions.md", "hw/propulsion.yaml",
              "hw/motors.yaml", "hw/drivers.yaml", "inspiration/links.yaml",
              "design/v1/params.yaml", "design/chosen"]:
        assert (root / f).is_file(), f
    params = yaml.safe_load((root / "design/v1/params.yaml").read_text())
    assert params["style"] == "quad_frame" and params["wheelbase_mm"] == 220
    req = yaml.safe_load((root / "requirements.yaml").read_text())
    assert req["flight"]["thrust_to_weight_min"] == 3.0


def test_blank_init_goal(tmp_path):
    root = tmp_path / "b"
    code, _, res = mechy("init", str(root), "--goal", "Build a drawbot.", "--json")
    assert res["ok"] and res["example"] is None
    assert "## Goal\n\nBuild a drawbot.\n" in (root / "brief.md").read_text()


def test_example_goal_appends_user_notes(tmp_path):
    root = tmp_path / "d"
    mechy("init", str(root), "--example", "drone", "--goal", "Carry a GoPro.")
    assert "## User notes\n\nCarry a GoPro.\n" in (root / "brief.md").read_text()


def test_quad_build_outputs(drone):
    d = drone.variant_dir("v1")
    for f in ("model.step", "model.stl", "model.glb", "mass_props.json", "thumb.png",
              "summary.md", "print_list.csv", "bom.csv"):
        assert (d / f).is_file() and (d / f).stat().st_size > 50, f
    assert (d / "model.glb").read_bytes()[:4] == b"glTF"
    stls = sorted((d / "stl").glob("*.stl"))
    assert {p.stem for p in stls} == {"arm", "bottom_plate", "top_plate"}
    mp = json.loads((d / "mass_props.json").read_text())
    assert mp["frame_mass_kg"] < mp["auw_kg"] < 1.0


def test_quad_stats(drone):
    code, _, res = mechy("cad", "build", "v1", "--project", str(drone.root))
    s = res["stats"]
    assert s["style"] == "quad_frame" and s["wheelbase_mm"] == 220
    assert s["thrust_to_weight"] > 1 and s["thrust_to_weight"] >= 3.0
    assert s["prop_tip_gap_mm"] > 0 and "prop_to_frame_gap_mm" in s
    assert 0 < s["hover_thrust_fraction"] < 1
    assert s["arm_root_safety_factor"] > 1
    txt = (drone.variant_dir("v1") / "summary.md").read_text()
    assert "estimates" in txt and "thrust/weight" in txt


def test_sim_control_doc_clean_error(drone):
    for args in (("sim", "catch", "v1"), ("control", "gen", "v1"), ("doc", "build", "v1")):
        code, _, res = mechy(*args, "--project", str(drone.root))
        assert code == 1 and res["ok"] is False
        assert "not available" in res["error"] and "quad_frame" in res["error"]
        assert "Traceback" not in res["error"]
