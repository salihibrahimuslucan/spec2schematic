from pathlib import Path

from spec2schematic.layout import Box, Drawing, Label, Pin, Segment, build_drawing
from spec2schematic.lint import lint
from spec2schematic.schema import load_spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _empty_drawing(**kwargs) -> Drawing:
    defaults = dict(name="t", width=400, height=300)
    defaults.update(kwargs)
    return Drawing(**defaults)


def _codes(drawing):
    return [finding.code for finding in lint(drawing)]


def test_wire_through_box_flagged():
    drawing = _empty_drawing(
        boxes=[Box("K1", "part", 100, 20, 80, 60)],
        segments=[Segment(140, 0, 140, 200, "N1")],  # straight through K1
    )
    assert "L001" in _codes(drawing)


def test_wire_touching_box_edge_is_clean():
    drawing = _empty_drawing(
        boxes=[Box("K1", "part", 100, 20, 80, 60)],
        segments=[Segment(140, 80, 140, 200, "N1")],  # starts ON the bottom edge
    )
    assert "L001" not in _codes(drawing)


def test_overlapping_collinear_segments_flagged():
    drawing = _empty_drawing(
        segments=[Segment(50, 100, 200, 100, "N1"), Segment(120, 100, 300, 100, "N2")],
    )
    assert "L002" in _codes(drawing)


def test_orthogonal_crossing_is_clean():
    drawing = _empty_drawing(
        segments=[Segment(50, 100, 200, 100, "N1"), Segment(120, 50, 120, 150, "N2")],
    )
    assert "L002" not in _codes(drawing)


def test_colliding_labels_flagged():
    drawing = _empty_drawing(
        labels=[
            Label("LONG_NAME", 50, 100, 10, "start", "net"),
            Label("OTHER", 60, 102, 10, "start", "net"),
        ],
    )
    assert "L003" in _codes(drawing)


def test_wire_through_net_label_flagged():
    drawing = _empty_drawing(
        labels=[Label("BUS", 50, 100, 10, "start", "net")],
        segments=[Segment(58, 0, 58, 200, "N9")],
    )
    assert "L003" in _codes(drawing)


def test_open_pin_flagged():
    drawing = _empty_drawing(
        pins=[Pin("K1", "spare", 140, 80, wired=False)],
    )
    codes = _codes(drawing)
    assert codes == ["L004"]


def test_examples_lint_clean():
    for spec_path in sorted(EXAMPLES.glob("*.yaml")):
        drawing = build_drawing(load_spec(spec_path))
        assert lint(drawing) == [], f"{spec_path.name} has lint findings"
