"""Serialize a Drawing to DXF via the optional ``ezdxf`` dependency.

The DXF backend consumes the exact same Drawing the SVG backend does, so
both formats always agree on geometry. ``ezdxf`` is an optional extra:

    pip install spec2schematic[dxf]
"""
from __future__ import annotations

from pathlib import Path

from .layout import DOT_RADIUS, Drawing

LAYER_COMPONENT = "COMPONENT"
LAYER_WIRE = "WIRE"
LAYER_TEXT = "TEXT"

# DXF text height that visually matches an SVG font size (rough cap height).
_TEXT_SCALE = 0.72


class MissingDxfDependencyError(RuntimeError):
    """Raised when DXF export is requested but ezdxf is not installed."""


def _require_ezdxf():
    try:
        import ezdxf
    except ImportError as exc:
        raise MissingDxfDependencyError(
            "DXF export requires the optional 'ezdxf' dependency; "
            "install it with: pip install spec2schematic[dxf]"
        ) from exc
    return ezdxf


def render_dxf(drawing: Drawing, path: str | Path) -> None:
    """Write the drawing as a DXF file (R2010)."""
    ezdxf = _require_ezdxf()
    from ezdxf.enums import TextEntityAlignment

    align = {
        "start": TextEntityAlignment.LEFT,
        "middle": TextEntityAlignment.CENTER,
        "end": TextEntityAlignment.RIGHT,
    }

    doc = ezdxf.new("R2010")
    doc.layers.add(LAYER_COMPONENT, color=5)
    doc.layers.add(LAYER_WIRE, color=7)
    doc.layers.add(LAYER_TEXT, color=8)
    msp = doc.modelspace()

    def y(v: int) -> int:
        # SVG's y axis points down, DXF's points up.
        return drawing.height - v

    for box in drawing.boxes:
        top, bottom = y(box.y), y(box.y + box.height)
        band = y(box.y + box.title_band)
        msp.add_lwpolyline(
            [
                (box.x, top),
                (box.x + box.width, top),
                (box.x + box.width, bottom),
                (box.x, bottom),
            ],
            close=True,
            dxfattribs={"layer": LAYER_COMPONENT},
        )
        msp.add_line(
            (box.x, band), (box.x + box.width, band), dxfattribs={"layer": LAYER_COMPONENT}
        )

    for seg in drawing.segments:
        msp.add_line(
            (seg.x1, y(seg.y1)), (seg.x2, y(seg.y2)), dxfattribs={"layer": LAYER_WIRE}
        )

    for dot in drawing.dots:
        msp.add_circle((dot.x, y(dot.y)), DOT_RADIUS, dxfattribs={"layer": LAYER_WIRE})

    for label in drawing.labels:
        text = msp.add_text(
            label.text,
            dxfattribs={"layer": LAYER_TEXT, "height": label.size * _TEXT_SCALE},
        )
        text.set_placement((label.x, y(label.y)), align=align[label.anchor])

    doc.saveas(Path(path))
