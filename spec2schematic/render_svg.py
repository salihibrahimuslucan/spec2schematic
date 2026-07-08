"""Serialize a Drawing to SVG, byte-identically for the same input.

The emitter is deliberately dumb: fixed attribute order, integer
coordinates, LF newlines, no timestamps, no randomness, no floating-point
formatting. If two renders of the same spec ever differ by a byte, that is
a bug — the golden tests depend on it.
"""
from __future__ import annotations

from .layout import DOT_RADIUS, Drawing

_INK = "#1f2430"
_BOX_FILL = "#f4f6fa"
_BAND_FILL = "#e2e7f0"
_OPEN_PIN = "#b3541e"
_FONT = "monospace"


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_svg(drawing: Drawing) -> str:
    w, h = drawing.width, drawing.height
    out: list[str] = []
    out.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">'
    )
    out.append(f'  <title>{_escape(drawing.name)}</title>')
    out.append(f'  <rect x="0" y="0" width="{w}" height="{h}" fill="#ffffff"/>')

    for box in drawing.boxes:
        out.append(
            f'  <rect x="{box.x}" y="{box.y}" width="{box.width}" height="{box.height}" '
            f'fill="{_BOX_FILL}" stroke="{_INK}" stroke-width="1"/>'
        )
        out.append(
            f'  <rect x="{box.x}" y="{box.y}" width="{box.width}" height="{box.title_band}" '
            f'fill="{_BAND_FILL}" stroke="{_INK}" stroke-width="1"/>'
        )

    for seg in drawing.segments:
        color = _OPEN_PIN if seg.net == "" else _INK
        out.append(
            f'  <line x1="{seg.x1}" y1="{seg.y1}" x2="{seg.x2}" y2="{seg.y2}" '
            f'stroke="{color}" stroke-width="1"/>'
        )

    for dot in drawing.dots:
        out.append(f'  <circle cx="{dot.x}" cy="{dot.y}" r="{DOT_RADIUS}" fill="{_INK}"/>')

    for label in drawing.labels:
        out.append(
            f'  <text x="{label.x}" y="{label.y}" font-family="{_FONT}" '
            f'font-size="{label.size}" text-anchor="{label.anchor}" '
            f'fill="{_INK}">{_escape(label.text)}</text>'
        )

    out.append("</svg>")
    return "\n".join(out) + "\n"
