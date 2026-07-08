from pathlib import Path

from spec2schematic.layout import build_drawing
from spec2schematic.render_svg import render_svg
from spec2schematic.schema import Component, Endpoint, Net, Spec, load_spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_svg_is_well_formed_xml():
    import xml.etree.ElementTree as ET

    svg = render_svg(build_drawing(load_spec(EXAMPLES / "divider.yaml")))
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


def test_svg_contains_components_and_nets():
    svg = render_svg(build_drawing(load_spec(EXAMPLES / "divider.yaml")))
    for text in ("VIN", "R1", "R2", "MID", "GND"):
        assert f">{text}<" in svg


def test_render_is_deterministic_in_process():
    spec_path = EXAMPLES / "divider.yaml"
    first = render_svg(build_drawing(load_spec(spec_path)))
    second = render_svg(build_drawing(load_spec(spec_path)))
    assert first == second


def test_svg_has_no_timestamp_or_float_noise():
    svg = render_svg(build_drawing(load_spec(EXAMPLES / "divider.yaml")))
    assert "date" not in svg.lower()
    assert "e-0" not in svg  # no scientific-notation floats


def test_labels_are_xml_escaped():
    spec = Spec(
        name="esc",
        components=[
            Component("A<B", "part&co", ("p",)),
            Component("C", "part", ("p",)),
        ],
        nets=[Net("N<1>", (Endpoint("A<B", "p"), Endpoint("C", "p")))],
    )
    svg = render_svg(build_drawing(spec))
    assert "A&lt;B" in svg
    assert "part&amp;co" in svg
    assert "N&lt;1&gt;" in svg
    assert "<B" not in svg.replace("&lt;B", "")
