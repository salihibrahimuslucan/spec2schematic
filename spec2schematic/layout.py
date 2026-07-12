"""Deterministic placement and routing: turn a spec into drawing primitives.

Placement puts components in a single row, in spec order, each drawn as a
box with a title band and its ports as pins on the bottom edge. Routing is
channel routing: every net (or cable group) is assigned one horizontal lane
below the row, and each endpoint drops vertically from its pin to the lane.

This geometry encodes the conventions in docs/rendering-notes.md by
construction:

- Nets that share a ``cable`` name are drawn as ONE lane with a
  conductor-count label, entering each component at the midpoint of the
  pins involved — no junction dots at the breakout, and the nets stay
  electrically distinct in the netlist (rule 1).
- Wires live entirely in the channel below the boxes, so they can never
  cross a component body (rule 2).
- A drop crosses other lanes orthogonally, exactly once each, and a
  crossing is only a connection where a junction dot says so (rule 3).

Everything here is integer math over lists in spec order; no sets are
iterated and nothing depends on hash order, so the same spec always
produces the same drawing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .schema import Net, Spec

# Geometry constants (pixels). Changing any of these changes every golden.
MARGIN = 20
BOX_HEIGHT = 60
TITLE_BAND = 18
BOX_GAP = 40
PORT_PITCH = 36
PORT_INSET = 18
PIN_STUB = 10
CHANNEL_GAP = 24
LANE_PITCH = 18
DOT_RADIUS = 3

ID_FONT = 12
TYPE_FONT = 9
PORT_FONT = 7
NET_FONT = 10


def text_width(text: str, size: int) -> int:
    """Approximate rendered width of monospace text, in integer pixels."""
    return (len(text) * size * 62 + 99) // 100


@dataclass(frozen=True)
class Box:
    id: str
    type: str
    x: int
    y: int
    width: int
    height: int
    title_band: int = TITLE_BAND


@dataclass(frozen=True)
class Pin:
    component: str
    port: str
    x: int
    y: int  # bottom edge of the owning box
    wired: bool


@dataclass(frozen=True)
class Segment:
    x1: int
    y1: int
    x2: int
    y2: int
    net: str  # net name, cable name, or "" for an open-pin stub

    @property
    def vertical(self) -> bool:
        return self.x1 == self.x2


@dataclass(frozen=True)
class Dot:
    x: int
    y: int
    net: str


@dataclass(frozen=True)
class Label:
    text: str
    x: int
    y: int  # baseline
    size: int
    anchor: str  # "start" | "middle" | "end"
    kind: str  # "component-id" | "component-type" | "port" | "net"
    origin: str = ""  # spec field this text was read from, e.g. "component:R1.type"


@dataclass
class Drawing:
    name: str
    width: int
    height: int
    boxes: list[Box] = field(default_factory=list)
    pins: list[Pin] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    dots: list[Dot] = field(default_factory=list)
    labels: list[Label] = field(default_factory=list)


@dataclass
class _Group:
    """One routing lane: either a single net or all nets of one cable."""

    kind: str  # "net" | "cable"
    label: str
    nets: list[Net] = field(default_factory=list)


def _group_nets(spec: Spec) -> list[_Group]:
    """Group nets into lanes, in first-occurrence order.

    Plain nets get a lane each; nets sharing a cable name share one lane
    (drawn as a single line) while remaining distinct nets electrically.
    """
    groups: list[_Group] = []
    by_cable: dict[str, _Group] = {}
    for net in spec.nets:
        if net.cable is None:
            groups.append(_Group("net", net.name, [net]))
        elif net.cable in by_cable:
            by_cable[net.cable].nets.append(net)
        else:
            group = _Group("cable", net.cable, [net])
            by_cable[net.cable] = group
            groups.append(group)
    for group in groups:
        if group.kind == "cable":
            group.label = f"{group.label} x{len(group.nets)}"
    return groups


def build_drawing(spec: Spec) -> Drawing:
    """Lay out a spec deterministically. Assumes the spec passed ERC."""
    boxes: list[Box] = []
    labels: list[Label] = []
    pin_pos: dict[tuple[str, str], tuple[int, int]] = {}
    pin_order: list[tuple[str, str]] = []

    x = MARGIN
    for component in spec.components:
        n = len(component.ports)
        pin_span = PORT_PITCH * (n - 1) if n > 1 else 0
        width = max(
            2 * PORT_INSET + pin_span,
            text_width(component.id, ID_FONT) + 12,
            text_width(component.type, TYPE_FONT) + 12,
        )
        box = Box(component.id, component.type, x, MARGIN, width, BOX_HEIGHT)
        boxes.append(box)
        labels.append(
            Label(
                component.id,
                x + width // 2,
                MARGIN + 13,
                ID_FONT,
                "middle",
                "component-id",
                f"component:{component.id}.id",
            )
        )
        labels.append(
            Label(
                component.type,
                x + width // 2,
                MARGIN + TITLE_BAND + 13,
                TYPE_FONT,
                "middle",
                "component-type",
                f"component:{component.id}.type",
            )
        )
        first_pin = x + (width - pin_span) // 2
        bottom = MARGIN + BOX_HEIGHT
        for i, port in enumerate(component.ports):
            px = first_pin + i * PORT_PITCH
            pin_pos[(component.id, port)] = (px, bottom)
            pin_order.append((component.id, port))
            labels.append(
                Label(
                    port, px, bottom - 4, PORT_FONT, "middle", "port",
                    f"component:{component.id}.ports[{i}]",
                )
            )
        x += width + BOX_GAP

    groups = _group_nets(spec)
    segments: list[Segment] = []
    dots: list[Dot] = []
    wired: set[tuple[str, str]] = set()

    for lane, group in enumerate(groups):
        lane_y = MARGIN + BOX_HEIGHT + CHANNEL_GAP + lane * LANE_PITCH
        drops: list[int] = []
        if group.kind == "cable":
            # One drop per component, at the midpoint of the pins the cable
            # serves there; the fan-out to individual pins is implicit at
            # the terminal strip and gets NO junction dot (rule 1).
            xs_by_component: dict[str, list[int]] = {}
            component_order: list[str] = []
            for net in group.nets:
                for endpoint in net.connects:
                    key = (endpoint.component, endpoint.port)
                    px, _ = pin_pos[key]
                    wired.add(key)
                    if endpoint.component not in xs_by_component:
                        xs_by_component[endpoint.component] = []
                        component_order.append(endpoint.component)
                    xs_by_component[endpoint.component].append(px)
            for component in component_order:
                xs = xs_by_component[component]
                drops.append(sum(xs) // len(xs))
        else:
            for endpoint in group.nets[0].connects:
                key = (endpoint.component, endpoint.port)
                px, _ = pin_pos[key]
                wired.add(key)
                drops.append(px)

        drops.sort()
        bottom = MARGIN + BOX_HEIGHT
        for dx in drops:
            segments.append(Segment(dx, bottom, dx, lane_y, group.label))
        segments.append(Segment(drops[0], lane_y, drops[-1], lane_y, group.label))
        if group.kind == "net":
            # A junction dot marks a genuine shared node: only the taps
            # strictly inside the lane span need one.
            for dx in drops[1:-1]:
                dots.append(Dot(dx, lane_y, group.label))
        net_origin = f"net:cable:{group.nets[0].cable}" if group.kind == "cable" else f"net:{group.nets[0].name}"
        labels.append(Label(group.label, drops[0] + 4, lane_y - 4, NET_FONT, "start", "net", net_origin))

    pins = [
        Pin(component, port, *pin_pos[(component, port)], wired=(component, port) in wired)
        for component, port in pin_order
    ]
    bottom = MARGIN + BOX_HEIGHT
    for pin in pins:
        if not pin.wired:
            # Draw the pin so the drawing admits it exists, even unwired.
            segments.append(Segment(pin.x, bottom, pin.x, bottom + PIN_STUB, ""))

    width = MARGIN
    for box in boxes:
        width = max(width, box.x + box.width)
    for segment in segments:
        width = max(width, segment.x1, segment.x2)
    for label in labels:
        width = max(width, label_bbox(label)[2])
    width += MARGIN

    height = MARGIN + BOX_HEIGHT
    if groups:
        height += CHANNEL_GAP + (len(groups) - 1) * LANE_PITCH
    elif any(not pin.wired for pin in pins):
        height += PIN_STUB
    height += MARGIN

    return Drawing(spec.name, width, height, boxes, pins, segments, dots, labels)


def label_bbox(label: Label) -> tuple[int, int, int, int]:
    """Approximate (x1, y1, x2, y2) box of a rendered label."""
    w = text_width(label.text, label.size)
    if label.anchor == "start":
        x1 = label.x
    elif label.anchor == "end":
        x1 = label.x - w
    else:
        x1 = label.x - w // 2
    return (x1, label.y - label.size, x1 + w, label.y + 2)
