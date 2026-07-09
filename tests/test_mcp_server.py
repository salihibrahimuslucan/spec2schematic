from __future__ import annotations

from pathlib import Path

import pytest

from mcp_server.server import generate_schematic, list_examples

VALID_SPEC = """
name: mcp-smoke
components:
  - id: R1
    type: resistor
    ports: [a, b]
  - id: R2
    type: resistor
    ports: [a, b]
nets:
  - name: MID
    connects: [R1.b, R2.a]
"""

BROKEN_SPEC = """
name: mcp-broken
components:
  - id: R1
    type: resistor
    ports: [a, b]
nets:
  - name: BAD
    connects: [R1.a, R2.b]
"""


def test_list_examples_returns_repo_examples():
    examples = list_examples()
    names = {ex["name"] for ex in examples}
    assert {"divider", "dol_starter", "tank_level"} <= names
    for ex in examples:
        assert ex["spec_yaml"].strip()


def test_generate_schematic_writes_svg_and_dxf():
    result = generate_schematic(VALID_SPEC)
    assert set(result.keys()) == {"svg_path", "dxf_path", "lint"}
    svg_path = Path(result["svg_path"])
    assert svg_path.exists()
    assert "<svg" in svg_path.read_text(encoding="utf-8")
    assert result["dxf_path"] is not None
    assert Path(result["dxf_path"]).exists()
    assert isinstance(result["lint"], list)


def test_generate_schematic_raises_readable_error_on_erc_failure():
    with pytest.raises(ValueError, match="ERC failed"):
        generate_schematic(BROKEN_SPEC)
