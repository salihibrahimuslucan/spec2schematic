"""MCP server wrapping the spec2schematic core.

Tools:
- generate_schematic(spec_yaml) -> writes SVG + DXF to a temp dir, returns their
  paths plus lint findings.
- list_examples() -> the repo's example specs (name + YAML text).

Run standalone:  python mcp_server/server.py
Add to Claude Code:  claude mcp add spec2schematic -- python mcp_server/server.py
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

import yaml
from mcp.server.fastmcp import FastMCP

from spec2schematic.erc import check, has_errors
from spec2schematic.layout import build_drawing
from spec2schematic.lint import lint
from spec2schematic.render_dxf import MissingDxfDependencyError, render_dxf
from spec2schematic.render_svg import render_svg
from spec2schematic.schema import Spec, SpecError, load_spec

REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "examples"

mcp = FastMCP("spec2schematic")


def _parse_spec_text(spec_yaml: str) -> Spec:
    fd, tmp_name = tempfile.mkstemp(suffix=".yaml")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        tmp_path.write_text(spec_yaml, encoding="utf-8")
        return load_spec(tmp_path)
    except (SpecError, OSError, yaml.YAMLError) as exc:
        raise ValueError(f"spec error: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)


def _check_erc(spec: Spec) -> list[str]:
    issues = check(spec)
    if has_errors(issues):
        errors = "; ".join(str(issue) for issue in issues if issue.severity == "error")
        raise ValueError(f"ERC failed: {errors}")
    return [str(issue) for issue in issues]


@mcp.tool()
def generate_schematic(spec_yaml: str) -> dict[str, Any]:
    """Render a YAML wiring spec to SVG and DXF files, plus lint findings.

    Returns a dict with ``svg_path`` and ``dxf_path`` (files written to a temp
    directory) and ``lint`` (ERC warnings + geometry lint findings, as strings).
    Raises ValueError with a readable message if the spec is malformed or has
    ERC errors.
    """
    spec = _parse_spec_text(spec_yaml)
    warnings = _check_erc(spec)
    drawing = build_drawing(spec)
    findings = [str(f) for f in lint(drawing)]

    out_dir = Path(tempfile.mkdtemp(prefix="spec2schematic_"))
    svg_path = out_dir / f"{spec.name}.svg"
    svg_path.write_text(render_svg(drawing), encoding="utf-8", newline="\n")

    dxf_path = out_dir / f"{spec.name}.dxf"
    try:
        render_dxf(drawing, dxf_path)
        dxf_path_str: str | None = str(dxf_path)
    except MissingDxfDependencyError:
        dxf_path_str = None

    return {
        "svg_path": str(svg_path),
        "dxf_path": dxf_path_str,
        "lint": warnings + findings,
    }


@mcp.tool()
def list_examples() -> list[dict[str, str]]:
    """List the repo's example specs as {name, spec_yaml} objects."""
    return [
        {"name": path.stem, "spec_yaml": path.read_text(encoding="utf-8")}
        for path in sorted(EXAMPLES_DIR.glob("*.yaml"))
    ]


if __name__ == "__main__":
    mcp.run()
