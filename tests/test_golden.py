"""Golden-image gate: rendered SVG must match the frozen files byte-for-byte.

The goldens encode the drawing conventions on purpose (see
docs/rendering-notes.md). If a change to the renderer diffs a golden, the
diff is either intended — re-freeze with

    python -m pytest --update-goldens

and justify it in the commit message — or it is a regression.
"""
from pathlib import Path

import pytest

from spec2schematic.layout import build_drawing
from spec2schematic.render_svg import render_svg
from spec2schematic.schema import load_spec

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "tests" / "golden"

CASES = [
    ROOT / "examples" / "divider.yaml",
    ROOT / "examples" / "dol_starter.yaml",
    ROOT / "examples" / "tank_level.yaml",
    ROOT / "tests" / "data" / "cable_pair.yaml",
]


@pytest.mark.parametrize("spec_path", CASES, ids=lambda p: p.stem)
def test_rendered_svg_matches_golden(spec_path, update_goldens):
    rendered = render_svg(build_drawing(load_spec(spec_path))).encode("utf-8")
    golden = GOLDEN / f"{spec_path.stem}.svg"

    if update_goldens:
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_bytes(rendered)
        pytest.skip(f"golden re-frozen: {golden.name}")

    assert golden.exists(), (
        f"golden {golden.name} is missing; freeze it with: python -m pytest --update-goldens"
    )
    assert rendered == golden.read_bytes(), (
        f"{golden.name} differs from the rendered output; if the change is intended, "
        "re-freeze with: python -m pytest --update-goldens"
    )
