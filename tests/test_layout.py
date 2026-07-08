from pathlib import Path

from spec2schematic.layout import BOX_HEIGHT, MARGIN, build_drawing
from spec2schematic.schema import Component, Endpoint, Net, Spec, load_spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _ep(text):
    return Endpoint.parse(text)


def _pair_spec(cable=None):
    return Spec(
        name="pair",
        components=[
            Component("J1", "connector", ("p1", "p2")),
            Component("J2", "connector", ("p1", "p2")),
        ],
        nets=[
            Net("SIG+", (_ep("J1.p1"), _ep("J2.p1")), cable=cable),
            Net("SIG-", (_ep("J1.p2"), _ep("J2.p2")), cable=cable),
        ],
    )


def test_components_placed_in_row_in_spec_order():
    drawing = build_drawing(load_spec(EXAMPLES / "divider.yaml"))
    assert [box.id for box in drawing.boxes] == ["VIN", "R1", "R2"]
    xs = [box.x for box in drawing.boxes]
    assert xs == sorted(xs)
    assert all(box.y == MARGIN for box in drawing.boxes)


def test_pins_sit_on_bottom_edge():
    drawing = build_drawing(load_spec(EXAMPLES / "divider.yaml"))
    for pin in drawing.pins:
        box = next(b for b in drawing.boxes if b.id == pin.component)
        assert pin.y == box.y + box.height
        assert box.x < pin.x < box.x + box.width


def test_all_segments_are_orthogonal():
    drawing = build_drawing(load_spec(EXAMPLES / "divider.yaml"))
    for seg in drawing.segments:
        assert seg.x1 == seg.x2 or seg.y1 == seg.y2


def test_wires_stay_below_component_row():
    drawing = build_drawing(load_spec(EXAMPLES / "divider.yaml"))
    row_bottom = MARGIN + BOX_HEIGHT
    for seg in drawing.segments:
        assert min(seg.y1, seg.y2) >= row_bottom


def test_plain_nets_get_one_lane_each():
    drawing = build_drawing(_pair_spec(cable=None))
    lane_ys = {seg.y1 for seg in drawing.segments if not seg.vertical}
    assert len(lane_ys) == 2


def test_cabled_nets_share_a_single_lane():
    drawing = build_drawing(_pair_spec(cable="W1"))
    horizontal = [seg for seg in drawing.segments if not seg.vertical]
    assert len(horizontal) == 1
    assert horizontal[0].net == "W1 x2"


def test_cable_lane_has_conductor_count_label_and_no_dots():
    drawing = build_drawing(_pair_spec(cable="W1"))
    net_labels = [lab for lab in drawing.labels if lab.kind == "net"]
    assert [lab.text for lab in net_labels] == ["W1 x2"]
    assert drawing.dots == []


def test_cable_drop_lands_on_pin_midpoint():
    drawing = build_drawing(_pair_spec(cable="W1"))
    j1 = [pin for pin in drawing.pins if pin.component == "J1"]
    mid = (j1[0].x + j1[1].x) // 2
    drops = [seg for seg in drawing.segments if seg.vertical]
    assert mid in {seg.x1 for seg in drops}


def test_junction_dots_only_on_interior_taps():
    spec = Spec(
        name="tap",
        components=[
            Component("A", "part", ("p",)),
            Component("B", "part", ("p",)),
            Component("C", "part", ("p",)),
        ],
        nets=[Net("BUS", (_ep("A.p"), _ep("B.p"), _ep("C.p")))],
    )
    drawing = build_drawing(spec)
    assert len(drawing.dots) == 1  # only B's tap, strictly inside the span
    horizontal = [seg for seg in drawing.segments if not seg.vertical]
    dot = drawing.dots[0]
    assert horizontal[0].x1 < dot.x < horizontal[0].x2


def test_unwired_pin_gets_open_stub():
    spec = Spec(
        name="open",
        components=[Component("A", "part", ("used", "spare")), Component("B", "part", ("used",))],
        nets=[Net("N1", (_ep("A.used"), _ep("B.used")))],
    )
    drawing = build_drawing(spec)
    spare = next(pin for pin in drawing.pins if pin.port == "spare")
    assert not spare.wired
    stubs = [seg for seg in drawing.segments if seg.net == ""]
    assert len(stubs) == 1
    assert stubs[0].x1 == spare.x


def test_drawing_is_reproducible():
    spec = load_spec(EXAMPLES / "divider.yaml")
    assert build_drawing(spec) == build_drawing(load_spec(EXAMPLES / "divider.yaml"))
