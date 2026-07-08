import sys
from pathlib import Path

import pytest

from spec2schematic.layout import build_drawing
from spec2schematic.render_dxf import MissingDxfDependencyError, render_dxf
from spec2schematic.schema import load_spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

ezdxf = pytest.importorskip("ezdxf")


def test_dxf_roundtrip_entity_counts(tmp_path):
    drawing = build_drawing(load_spec(EXAMPLES / "divider.yaml"))
    out = tmp_path / "divider.dxf"
    render_dxf(drawing, out)

    doc = ezdxf.readfile(out)
    msp = doc.modelspace()
    assert len(msp.query("LWPOLYLINE")) == len(drawing.boxes)
    # one band divider line per box, plus every wire segment
    assert len(msp.query("LINE")) == len(drawing.boxes) + len(drawing.segments)
    assert len(msp.query("CIRCLE")) == len(drawing.dots)
    assert len(msp.query("TEXT")) == len(drawing.labels)


def test_dxf_flips_y_axis(tmp_path):
    drawing = build_drawing(load_spec(EXAMPLES / "divider.yaml"))
    out = tmp_path / "divider.dxf"
    render_dxf(drawing, out)

    doc = ezdxf.readfile(out)
    ys = [p[1] for poly in doc.modelspace().query("LWPOLYLINE") for p in poly.get_points()]
    # boxes sit at the TOP of the SVG page, so in DXF (y up) their top edge
    # must land at height - MARGIN, i.e. near the top of the sheet
    from spec2schematic.layout import BOX_HEIGHT, MARGIN

    assert max(ys) == drawing.height - MARGIN
    assert min(ys) == drawing.height - MARGIN - BOX_HEIGHT


def test_missing_ezdxf_gives_actionable_error(tmp_path, monkeypatch):
    drawing = build_drawing(load_spec(EXAMPLES / "divider.yaml"))
    monkeypatch.setitem(sys.modules, "ezdxf", None)  # simulate: not installed
    with pytest.raises(MissingDxfDependencyError, match=r"pip install spec2schematic\[dxf\]"):
        render_dxf(drawing, tmp_path / "x.dxf")
