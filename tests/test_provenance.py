from dataclasses import replace
from pathlib import Path

from spec2schematic.layout import build_drawing
from spec2schematic.provenance import check
from spec2schematic.schema import load_spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _codes(spec, drawing):
    return [finding.code for finding in check(spec, drawing)]


def test_every_example_is_provenance_clean():
    for path in EXAMPLES.glob("*.yaml"):
        spec = load_spec(path)
        drawing = build_drawing(spec)
        assert check(spec, drawing) == [], f"{path.name}: {check(spec, drawing)}"


def test_dropped_component_label_is_flagged():
    spec = load_spec(EXAMPLES / "divider.yaml")
    drawing = build_drawing(spec)
    # Simulate a renderer bug: the id label for R2 never got produced.
    kept = [label for label in drawing.labels if label.origin != "component:R2.id"]
    drawing.labels[:] = kept
    assert "P001" in _codes(spec, drawing)


def test_hardcoded_label_with_no_origin_is_flagged():
    spec = load_spec(EXAMPLES / "divider.yaml")
    drawing = build_drawing(spec)
    for i, label in enumerate(drawing.labels):
        if label.origin == "component:R1.type":
            # Simulate the exact failure this check exists for: a renderer
            # that prints a baked-in string instead of reading the spec.
            drawing.labels[i] = _with_origin(label, "")
            break
    assert "P002" in _codes(spec, drawing)


def test_origin_pointing_at_unknown_component_is_flagged():
    spec = load_spec(EXAMPLES / "divider.yaml")
    drawing = build_drawing(spec)
    for i, label in enumerate(drawing.labels):
        if label.origin == "component:R1.type":
            drawing.labels[i] = _with_origin(label, "component:R99.type")
            break
    assert "P002" in _codes(spec, drawing)


def test_clean_drawing_has_no_findings():
    spec = load_spec(EXAMPLES / "divider.yaml")
    drawing = build_drawing(spec)
    assert check(spec, drawing) == []


def _with_origin(label, origin):
    return replace(label, origin=origin)
