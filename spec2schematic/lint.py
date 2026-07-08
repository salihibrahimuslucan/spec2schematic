"""Geometry and style lint over a laid-out drawing.

ERC answers "is the netlist sound?"; this pass answers "is the picture
readable?". It runs on the drawing primitives, not on the SVG text, so the
same checks gate every output format.

Checks:

- L001: a wire segment passes through the interior of a component box.
- L002: two wire segments overlap collinearly (one drawn on top of another).
- L003: a label collides with another label or with a wire.
- L004: a pin is drawn but connected to nothing.
"""
from __future__ import annotations

from dataclasses import dataclass

from .layout import Box, Drawing, Label, Segment, label_bbox


@dataclass(frozen=True)
class Finding:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def lint(drawing: Drawing) -> list[Finding]:
    """Run all geometry checks and return findings in a stable order."""
    findings: list[Finding] = []
    findings += _wire_through_box(drawing)
    findings += _overlapping_segments(drawing)
    findings += _label_collisions(drawing)
    findings += _open_pins(drawing)
    return findings


def _span_overlap(a1: int, a2: int, b1: int, b2: int) -> bool:
    """True if two 1-D spans share more than a single point."""
    lo = max(min(a1, a2), min(b1, b2))
    hi = min(max(a1, a2), max(b1, b2))
    return hi > lo


def _segment_enters_box(seg: Segment, box: Box) -> bool:
    if seg.vertical:
        return box.x < seg.x1 < box.x + box.width and _span_overlap(
            seg.y1, seg.y2, box.y, box.y + box.height
        )
    return box.y < seg.y1 < box.y + box.height and _span_overlap(
        seg.x1, seg.x2, box.x, box.x + box.width
    )


def _wire_through_box(drawing: Drawing) -> list[Finding]:
    out: list[Finding] = []
    for seg in drawing.segments:
        for box in drawing.boxes:
            if _segment_enters_box(seg, box):
                out.append(
                    Finding(
                        "L001",
                        f"wire '{seg.net}' passes through component '{box.id}'",
                    )
                )
    return out


def _overlapping_segments(drawing: Drawing) -> list[Finding]:
    out: list[Finding] = []
    segs = drawing.segments
    for i, a in enumerate(segs):
        for b in segs[i + 1 :]:
            if a.vertical and b.vertical and a.x1 == b.x1:
                if _span_overlap(a.y1, a.y2, b.y1, b.y2):
                    out.append(
                        Finding(
                            "L002",
                            f"segments of '{a.net}' and '{b.net}' overlap at x={a.x1}",
                        )
                    )
            elif not a.vertical and not b.vertical and a.y1 == b.y1:
                if _span_overlap(a.x1, a.x2, b.x1, b.x2):
                    out.append(
                        Finding(
                            "L002",
                            f"segments of '{a.net}' and '{b.net}' overlap at y={a.y1}",
                        )
                    )
    return out


def _boxes_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _segment_crosses_bbox(seg: Segment, bbox: tuple[int, int, int, int]) -> bool:
    x1, y1, x2, y2 = bbox
    if seg.vertical:
        return x1 < seg.x1 < x2 and _span_overlap(seg.y1, seg.y2, y1, y2)
    return y1 < seg.y1 < y2 and _span_overlap(seg.x1, seg.x2, x1, x2)


def _label_collisions(drawing: Drawing) -> list[Finding]:
    out: list[Finding] = []
    labels: list[tuple[Label, tuple[int, int, int, int]]] = [
        (label, label_bbox(label)) for label in drawing.labels
    ]
    for i, (a, abox) in enumerate(labels):
        for b, bbox in labels[i + 1 :]:
            if _boxes_overlap(abox, bbox):
                out.append(
                    Finding("L003", f"label '{a.text}' collides with label '{b.text}'")
                )
    for label, bbox in labels:
        if label.kind != "net":
            continue  # component/port labels live inside boxes, wires cannot reach them
        for seg in drawing.segments:
            if _segment_crosses_bbox(seg, bbox):
                out.append(
                    Finding("L003", f"label '{label.text}' collides with wire '{seg.net}'")
                )
    return out


def _open_pins(drawing: Drawing) -> list[Finding]:
    out: list[Finding] = []
    for pin in drawing.pins:
        if not pin.wired:
            out.append(
                Finding(
                    "L004",
                    f"pin '{pin.component}.{pin.port}' is drawn but connected to nothing",
                )
            )
    return out
