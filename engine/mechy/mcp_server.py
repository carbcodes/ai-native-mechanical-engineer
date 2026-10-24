"""`mechy mcp`: the `mechy-tools` MCP server over stdio (FastMCP).

Tool names use underscores (cad_build) because MCP clients reject dots; contract names map
1:1 (cad.build -> cad_build). Stdout belongs to the MCP protocol, so nothing else prints.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import tools as T
from .project import find_project


def create_server(project_root: str | Path) -> FastMCP:
    proj = find_project(project_root)
    proj.require()
    mcp = FastMCP("mechy-tools", log_level="WARNING", instructions=(
        "Engineering tools for one Mechy project. Prefer these over writing ad hoc code. "
        "Every tool returns small JSON plus project-relative file paths."))

    @mcp.tool()
    def cad_build(variant: str) -> dict:
        """Build design/<variant>: arm.step, arm.stl, arm.glb, arm.xml (MuJoCo), thumb.png, summary.md."""
        return T.cad_build(proj, variant)

    @mcp.tool()
    def cad_params_get(variant: str) -> dict:
        """Read design/<variant>/params.yaml."""
        return T.cad_params_get(proj, variant)

    @mcp.tool()
    def cad_params_set(variant: str, patch: dict[str, Any], from_variant: str | None = None) -> dict:
        """Deep-merge patch into design/<variant>/params.yaml; a new variant copies from_variant
        (default: chosen/latest). Patch list items by index, e.g. {"joints": {"1": {"gear_ratio": 5}}}."""
        return T.cad_params_set(proj, variant, patch, from_variant)

    @mcp.tool()
    def sim_catch(variant: str, throws: int = 200, seed: int = 0, task: str | None = None,
                  microsteps: int | None = None) -> dict:
        """Monte-Carlo catch sweep in MuJoCo; writes sim/<task>/report.json, plots, summary.md."""
        return T.sim_catch(proj, variant, throws, seed, task, microsteps)

    @mcp.tool()
    def ball_predict(points: list[list[float]], t_max: float = 1.5) -> dict:
        """Fit ball flight to (N,4) [t,x,y,z] points (N>=3) and predict its path and landing."""
        return T.ball_predict(proj, points, t_max)

    @mcp.tool()
    def ik_solve(variant: str, target_xyz: list[float], pitch: float | None = None) -> dict:
        """Inverse kinematics for the variant. pitch = hand elevation in degrees (omit to search)."""
        return T.ik_solve(proj, variant, target_xyz, pitch)

    @mcp.tool()
    def motor_check(variant: str, trajectory: list[dict[str, Any]] | None = None,
                    microsteps: int | None = None) -> dict:
        """Stepper headroom per joint; with trajectory [{q_deg:[4], t:s}, ...] plans each segment."""
        return T.motor_check(proj, variant, trajectory, microsteps)

    @mcp.tool()
    def render_views(variant: str) -> dict:
        """Render iso/front/side/top PNGs into design/<variant>/views/."""
        return T.render_views(proj, variant)

    @mcp.tool()
    def control_gen(variant: str, board: str | None = None) -> dict:
        """Generate control/<variant>/: Arduino firmware (config.h from params + hw), host ball
        tracker/planner (mechy_host.py, --dry-run replays sim throws) and a wiring README.
        board: uno_cnc (Uno + CNC Shield V3) or mega_ramps (Mega + RAMPS 1.4); default from hw."""
        return T.control_gen(proj, variant, board)

    @mcp.tool()
    def doc_build(variant: str, only: str | None = None, print_paper: bool = False) -> dict:
        """Write docs/<variant>/build_guide.pdf (cover, BOM, print list, a drawing per printed part,
        numbered assembly steps, belts/homing, wiring, gaps) and report.pdf (requirements vs results,
        catch map, torque margins, decisions). Needs `cad build` first; uses sim and control output when
        present. only: build_guide | report. print_paper: white background for home printing."""
        return T.doc_build(proj, variant, only, print_paper)

    @mcp.tool()
    def project_summary() -> dict:
        """Variants, sim results, task states, open questions and options of this project."""
        return T.project_summary(proj)

    @mcp.tool()
    def question_ask(id: str, text: str, kind: str = "text", choices: list[str] | None = None,
                     image: str | None = None, asked_by: str | None = None) -> dict:
        """Ask the user a question (writes questions/<id>.yaml; the app fills in answer)."""
        return T.question_ask(proj, id, text, kind, choices, image, asked_by)

    @mcp.tool()
    def options_present(id: str, prompt: str, options: list[dict[str, Any]]) -> dict:
        """Show the user options to pick from (writes options/<id>.yaml; the app fills in chosen)."""
        return T.options_present(proj, id, prompt, options)

    @mcp.tool()
    def workspace_note(panel: str, text: str, target: str | None = None, open: bool = True) -> dict:
        """Work alongside the user in the app: pin a short comment (<= 2 sentences) on a workspace
        panel and bring it up. panel: inspiration|cad|options|questions|sim|tasks|docs|parts|
        electronics|loads|manufacturing|history. target: what the panel should show (variant name
        for cad/parts/loads/manufacturing, sim task id for sim, project-relative path for docs)."""
        return T.workspace_note(proj, panel, text, target, open)

    from .intake.register import register_mcp_tools
    register_mcp_tools(mcp, proj)    # intake_digest, intake_pending

    return mcp


def serve(project_root: str | Path | None = None) -> None:
    root = project_root or os.environ.get("MECHY_PROJECT") or os.getcwd()
    create_server(root).run("stdio")
