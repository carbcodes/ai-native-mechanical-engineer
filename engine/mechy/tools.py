"""Implementations of the `mechy-tools` (contracts 3.1). Small JSON in, small JSON + paths out.

Heavy tools (cad.build, sim.catch) run the `mechy` CLI in a subprocess so the MCP server
stays responsive and multiprocessing is never forked from a threaded server.
"""

from __future__ import annotations

import copy
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

from .events import Events
from .project import Project, load_yaml, save_yaml

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")
VARIANT_RE = re.compile(r"^v\d+[a-z0-9_-]*$")

# MCP tool names. The contract writes them with dots (cad.build); MCP clients such as
# Claude Code only accept [A-Za-z0-9_-] in tool names, so the server exposes underscores.
TOOL_NAMES = ["cad.build", "cad.params_get", "cad.params_set", "sim.catch", "ball.predict", "ik.solve",
              "motor.check", "render.views", "control.gen", "doc.build", "project.summary", "question.ask", "options.present",
              "intake.digest", "intake.pending"]


def mcp_name(tool: str) -> str:
    return tool.replace(".", "_")


class ToolError(Exception):
    pass


def _check_variant(v: str) -> str:
    if not VARIANT_RE.match(v or ""):
        raise ToolError(f"bad variant name {v!r} (expected v<N>)")
    return v


def _check_id(i: str) -> str:
    if not ID_RE.match(i or ""):
        raise ToolError(f"bad id {i!r}")
    return i


def run_cli(project: Project, *args: str, timeout: float = 1800) -> dict:
    """Run `mechy <args> --project <root> --json` and return its final result object."""
    cmd = [sys.executable, "-m", "mechy.cli", *args, "--project", str(project.root), "--json"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=project.root)
    result = None
    for line in r.stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("type") == "result":
            result = ev
    if result is None:
        raise ToolError(f"`mechy {' '.join(args)}` produced no result (exit {r.returncode}): {r.stderr[-800:]}")
    result.pop("type", None)
    result.pop("ts", None)
    return result


# --------------------------------------------------------------------- cad
def cad_build(project: Project, variant: str) -> dict:
    return run_cli(project, "cad", "build", _check_variant(variant))


def cad_params_get(project: Project, variant: str) -> dict:
    _check_variant(variant)
    return {"variant": variant, "path": f"design/{variant}/params.yaml", "params": project.params(variant)}


def _deep_merge(base: Any, patch: Any) -> Any:
    if isinstance(base, dict) and isinstance(patch, dict):
        out = dict(base)
        for k, v in patch.items():
            out[k] = _deep_merge(base.get(k), v) if k in base else v
        return out
    if isinstance(base, list) and isinstance(patch, dict) and all(str(k).isdigit() for k in patch):
        out = list(base)   # {"1": {...}} patches list element 1 (e.g. one joint)
        for k, v in patch.items():
            out[int(k)] = _deep_merge(out[int(k)], v)
        return out
    return copy.deepcopy(patch)


def cad_params_set(project: Project, variant: str, patch: dict, from_variant: str | None = None) -> dict:
    """Deep-merge `patch` into design/<variant>/params.yaml. A new variant starts as a copy of
    `from_variant` (default: the chosen or latest variant). List items can be patched by index:
    {"joints": {"1": {"gear_ratio": 5}}}."""
    _check_variant(variant)
    path = project.variant_dir(variant) / "params.yaml"
    created = not path.exists()
    src = None
    if created:
        src = from_variant or project.chosen() or (project.variants() or [None])[-1]
        if src is None:
            raise ToolError("no variant to copy from; pass from_variant")
        base = project.params(_check_variant(src))
    else:
        base = load_yaml(path)
    new = _deep_merge(base, patch or {})
    new["name"] = variant
    from .arm_model import ArmModel
    ArmModel(new, project.hardware()["motors"])   # validate
    save_yaml(path, new)
    Events(project.root, quiet=True).file_written(path)
    return {"variant": variant, "path": f"design/{variant}/params.yaml", "created": created,
            "copied_from": src}


def render_views(project: Project, variant: str) -> dict:
    from .arm_model import load_arm
    from .cad.geometry import build_arm
    from .cad.render import render_parts_png, tessellate_parts
    _check_variant(variant)
    arm = load_arm(project, variant)
    _, parts = build_arm(arm)
    meshes = tessellate_parts(parts)
    out = project.variant_dir(variant) / "views"
    out.mkdir(exist_ok=True)
    ev = Events(project.root, quiet=True)
    files = []
    for view in ("iso", "front", "side", "top"):
        p = render_parts_png(meshes, out / f"{view}.png", view, size_px=520, title=f"{variant} {view}")
        ev.file_written(p)
        files.append(ev.rel(p))
    return {"variant": variant, "files": files}


# --------------------------------------------------------------------- sim
def sim_catch(project: Project, variant: str, throws: int = 200, seed: int = 0, task: str | None = None,
              microsteps: int | None = None) -> dict:
    args = ["sim", "catch", _check_variant(variant), "--throws", str(int(throws)), "--seed", str(int(seed))]
    if task:
        args += ["--task", _check_id(task)]
    if microsteps:
        args += ["--microsteps", str(int(microsteps))]
    return run_cli(project, *args)


def ball_predict(project: Project | None, points: list, t_max: float = 1.5) -> dict:
    from .core import get_core
    mc = get_core()
    req = project.requirements().get("catch", {}) if project else {}
    mass, dia = float(req.get("ball_mass_kg", 0.057)), float(req.get("ball_diameter_m", 0.067))
    pts = np.asarray(points, float)
    fit = mc.ball_fit(pts, mass=mass, diameter=dia)
    tr = mc.ball_predict(fit["p0"], fit["v0"], dt=0.01, t_max=t_max, mass=mass, diameter=dia, t0=fit["t0"])
    below = np.where(tr[:, 3] <= dia / 2)[0]
    land = tr[below[0]] if len(below) else None
    step = max(1, len(tr) // 15)
    return {"p0": np.round(fit["p0"], 4).tolist(), "v0": np.round(fit["v0"], 4).tolist(), "t0": fit["t0"],
            "residual_m": round(float(fit["residual"]), 5),
            "landing": None if land is None else {"t": round(float(land[0]), 3), "xyz": np.round(land[1:], 3).tolist()},
            "path": np.round(tr[::step], 3).tolist()}


def ik_solve(project: Project, variant: str, target_xyz: list, pitch: float | None = None) -> dict:
    """pitch in degrees (hand elevation above horizontal); None tries -60..90 and returns the first."""
    from .arm_model import load_arm
    arm = load_arm(project, _check_variant(variant))
    ca = arm.core_arm()
    pitches = [pitch] if pitch is not None else list(range(30, 91, 10)) + list(range(20, -61, -10))
    for p in pitches:
        q = ca.ik(np.asarray(target_xyz, float), math.radians(p), seed=arm.ready_pose())
        if q is not None:
            fk, fp = ca.fk(q)
            return {"reachable": True, "pitch_deg": p, "q_deg": np.round(np.degrees(q), 2).tolist(),
                    "joints": arm.joint_names, "fk_xyz": np.round(fk, 4).tolist(),
                    "gravity_torque_nm": np.round(arm.gravity_torque(q), 3).tolist()}
    return {"reachable": False, "reach_m": arm.reach, "tried_pitch_deg": pitches}


def motor_check(project: Project, variant: str, trajectory: list | None = None, microsteps: int | None = None) -> dict:
    """Without a trajectory: static and speed headroom per joint. With one: list of waypoints
    {"q_deg": [4], "t": seconds allowed to reach it from the previous one}; plans each segment."""
    from .arm_model import load_arm
    from .core import get_core
    mc = get_core()
    arm = load_arm(project, _check_variant(variant), microsteps)
    motors = arm.core_motors()
    hold = np.array([float(m["torque_curve"][0][1]) for m in arm.motor_specs])
    gstat = arm.gravity_torque_max()
    out: dict = {
        "variant": variant, "joints": arm.joint_names, "gear_ratio": arm.gear.tolist(),
        "microsteps": arm.microsteps, "max_motor_rps": [round(arm.max_speed_rps(i), 3) for i in range(4)],
        "max_joint_speed_dps": [round(math.degrees(m.max_joint_speed), 1) for m in motors],
        "gravity_frac_of_holding_stretched": np.round(gstat / arm.gear / hold, 3).tolist(),
    }
    J = arm.load_inertia()
    out["time_90deg_s"] = [round(float(mc.plan_move(np.zeros(4), np.eye(4)[i] * math.pi / 2, motors, J, 10.0,
                                                     load_torque=gstat)["t_per_joint"][i]), 3) for i in range(4)]
    if trajectory:
        segs = []
        q_prev = arm.ready_pose()
        for wp in trajectory:
            q = np.radians(np.asarray(wp["q_deg"], float))
            Jl = np.maximum(arm.load_inertia(q_prev), arm.load_inertia(q))
            tl = np.maximum(arm.gravity_torque(q_prev), arm.gravity_torque(q))
            r = mc.plan_move(q_prev, q, motors, Jl, float(wp["t"]), load_torque=tl)
            segs.append({"feasible": bool(r["feasible"]), "t_needed": round(float(r["t_needed"]), 3),
                         "t_avail": float(wp["t"]), "limiting_joint": arm.joint_names[int(r["limiting_joint"])],
                         "peak_torque_frac": [round(float(x), 3) if math.isfinite(x) else None for x in r["peak_torque_frac"]]})
            q_prev = q
        out["segments"] = segs
        out["feasible"] = all(s["feasible"] for s in segs)
    return out


# ----------------------------------------------------------------- control
def control_gen(project: Project, variant: str, board: str | None = None) -> dict:
    """Write control/<variant>/ (firmware, host, README); runs the CLI in a subprocess."""
    args = ["control", "gen", _check_variant(variant)]
    if board:
        if board not in ("uno_cnc", "mega_ramps"):
            raise ToolError("board must be uno_cnc or mega_ramps")
        args += ["--board", board]
    return run_cli(project, *args, timeout=900)


# ----------------------------------------------------------------- docs
def doc_build(project: Project, variant: str, only: str | None = None, print_paper: bool = False) -> dict:
    """Write docs/<variant>/build_guide.pdf and report.pdf (+ Typst sources); runs the CLI in a subprocess.
    print_paper: white background for home printing instead of the drawing-sheet paper colour."""
    args = ["doc", "build", _check_variant(variant)]
    if only:
        if only not in ("build_guide", "report"):
            raise ToolError("only must be build_guide or report")
        args += ["--only", only]
    if print_paper:
        args += ["--print"]
    return run_cli(project, *args, timeout=1200)


# ----------------------------------------------------------------- intake
def intake_digest(project: Project, source: str, force: bool = False) -> dict:
    from .intake.register import intake_digest_tool
    return intake_digest_tool(project, source, force)


def intake_pending(project: Project) -> dict:
    from .intake.register import intake_pending_tool
    return intake_pending_tool(project)


def intake_digest_all(project: Project, **kw) -> dict:
    """Digest every pending source (links.yaml + media dropped in inspiration/); never raises."""
    from .intake import digest_all
    return digest_all(project, **kw)


# ----------------------------------------------------------------- project
def project_summary(project: Project) -> dict:
    meta = project.meta()
    variants = []
    for v in project.variants():
        d = project.variant_dir(v)
        variants.append({"name": v, "files": sorted(p.name for p in d.iterdir() if p.is_file()),
                         "summary": f"design/{v}/summary.md" if (d / "summary.md").exists() else None})
    sims = []
    for rp in sorted(project.path("sim").glob("*/report.json")):
        try:
            r = json.loads(rp.read_text())
        except json.JSONDecodeError:
            continue
        sims.append({"task": rp.parent.name, "variant": r.get("variant"), "catch_rate": r.get("catch_rate"),
                     "reach_rate": r.get("reach_rate"), "throws": r.get("throws"),
                     "summary": f"sim/{rp.parent.name}/summary.md"})
    tasks = []
    for tp in sorted(project.path("tasks").glob("*.yaml")):
        card = load_yaml(tp) or {}
        sp = tp.with_name(tp.stem + ".status.json")
        st = json.loads(sp.read_text()) if sp.exists() else {"state": "queued"}
        tasks.append({"id": card.get("id", tp.stem), "role": card.get("role"), "state": st.get("state"),
                      "summary": st.get("summary")})

    def open_items(folder: str, key: str):
        res = []
        for p in sorted(project.path(folder).glob("*.yaml")):
            d = load_yaml(p) or {}
            res.append({"id": d.get("id", p.stem), key: d.get(key), "path": f"{folder}/{p.name}"})
        return res

    return {"name": meta.get("name"), "chosen": project.chosen(), "variants": variants, "sims": sims,
            "tasks": tasks, "questions": open_items("questions", "answer"),
            "options": open_items("options", "chosen"),
            "requirements": project.requirements(), "brief": "brief.md"}


def question_ask(project: Project, id: str, text: str, kind: str = "text", choices: list | None = None,
                 image: str | None = None, asked_by: str | None = None) -> dict:
    _check_id(id)
    if kind not in ("choice", "number", "text", "image"):
        raise ToolError("kind must be choice|number|text|image")
    if kind == "choice" and not choices:
        raise ToolError("choice questions need choices")
    q: dict = {"id": id, "asked_by": asked_by, "text": text, "kind": kind}
    if choices:
        q["choices"] = list(choices)
    if image:
        q["image"] = image
    q["answer"] = None
    path = project.path("questions", f"{id}.yaml")
    if path.exists():
        old = load_yaml(path) or {}
        if old.get("answer") is not None:
            raise ToolError(f"question {id} is already answered: {old['answer']!r}")
    save_yaml(path, q)
    ev = Events(project.root, quiet=True)
    ev.file_written(path)
    ev.emit("question.asked", id=id)
    return {"id": id, "path": f"questions/{id}.yaml"}


def options_present(project: Project, id: str, prompt: str, options: list) -> dict:
    _check_id(id)
    if not options or not all(isinstance(o, dict) and o.get("id") for o in options):
        raise ToolError("options must be a non-empty list of {id, title, image?, model?, stats?}")
    path = project.path("options", f"{id}.yaml")
    save_yaml(path, {"id": id, "prompt": prompt, "options": options, "chosen": None, "feedback": None})
    ev = Events(project.root, quiet=True)
    ev.file_written(path)
    ev.emit("options.presented", id=id)
    return {"id": id, "path": f"options/{id}.yaml", "count": len(options)}


WORKSPACE_PANELS = ("inspiration", "cad", "options", "questions", "sim", "tasks", "docs", "parts",
                    "electronics", "loads", "manufacturing", "history")


def workspace_note(project: Project, panel: str, text: str, target: str | None = None,
                   open: bool = True) -> dict:
    """Pin a short comment on a workspace panel in the app (and bring the panel up)."""
    if panel not in WORKSPACE_PANELS:
        raise ToolError(f"panel must be one of {', '.join(WORKSPACE_PANELS)}")
    text = (text or "").strip()
    if not text:
        raise ToolError("text is empty")
    fields: dict = {"panel": panel, "text": text[:400], "open": bool(open)}
    if target:
        fields["target"] = target
    Events(project.root, quiet=True).emit("workspace.note", **fields)
    return {"panel": panel, "pinned": True}
