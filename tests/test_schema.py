from pathlib import Path

import pytest

from spec2schematic.schema import Endpoint, SpecError, load_spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_loads_valid_spec():
    spec = load_spec(EXAMPLES / "divider.yaml")
    assert spec.name == "voltage-divider"
    assert len(spec.components) == 3
    assert len(spec.nets) == 3


def test_endpoint_parse_roundtrip():
    ep = Endpoint.parse("R1.a")
    assert ep.component == "R1"
    assert ep.port == "a"
    assert str(ep) == "R1.a"


def test_bad_endpoint_raises():
    with pytest.raises(SpecError):
        Endpoint.parse("R1a")  # no dot separator


def test_net_cable_defaults_to_none():
    spec = load_spec(EXAMPLES / "divider.yaml")
    assert all(net.cable is None for net in spec.nets)


def test_net_cable_parsed(tmp_path):
    path = tmp_path / "cable.yaml"
    path.write_text(
        "name: cabled\n"
        "components:\n"
        "  - {id: A, type: connector, ports: [p1, p2]}\n"
        "  - {id: B, type: connector, ports: [p1, p2]}\n"
        "nets:\n"
        "  - {name: SIG+, connects: [A.p1, B.p1], cable: W1}\n"
        "  - {name: SIG-, connects: [A.p2, B.p2], cable: W1}\n",
        encoding="utf-8",
    )
    spec = load_spec(path)
    assert [net.cable for net in spec.nets] == ["W1", "W1"]
    # conductors stay distinct nets even when they share a cable
    assert spec.nets[0].name != spec.nets[1].name


def test_net_cable_must_be_string(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "name: bad\n"
        "components:\n"
        "  - {id: A, type: connector, ports: [p1]}\n"
        "nets:\n"
        "  - {name: N1, connects: [A.p1], cable: [not, a, string]}\n",
        encoding="utf-8",
    )
    with pytest.raises(SpecError):
        load_spec(path)
