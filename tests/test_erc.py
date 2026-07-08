from spec2schematic.erc import check, has_errors
from spec2schematic.schema import Component, Endpoint, Net, Spec


def _ep(text):
    return Endpoint.parse(text)


def test_clean_spec_has_no_errors():
    spec = Spec(
        name="ok",
        components=[
            Component("R1", "resistor", ("a", "b")),
            Component("R2", "resistor", ("a", "b")),
        ],
        nets=[
            Net("N1", (_ep("R1.a"), _ep("R2.a"))),
            Net("N2", (_ep("R1.b"), _ep("R2.b"))),
        ],
    )
    assert not has_errors(check(spec))


def test_duplicate_id_flagged():
    spec = Spec(
        name="dup",
        components=[
            Component("R1", "resistor", ("a", "b")),
            Component("R1", "resistor", ("a", "b")),
        ],
        nets=[],
    )
    codes = {i.code for i in check(spec)}
    assert "E001" in codes


def test_unknown_component_and_port():
    spec = Spec(
        name="bad",
        components=[Component("R1", "resistor", ("a", "b"))],
        nets=[Net("N1", (_ep("R9.a"), _ep("R1.z")))],
    )
    codes = {i.code for i in check(spec)}
    assert "E002" in codes  # unknown component R9
    assert "E003" in codes  # unknown port R1.z


def test_dangling_net():
    spec = Spec(
        name="dangle",
        components=[Component("R1", "resistor", ("a", "b"))],
        nets=[Net("N1", (_ep("R1.a"),))],
    )
    codes = {i.code for i in check(spec)}
    assert "E004" in codes
