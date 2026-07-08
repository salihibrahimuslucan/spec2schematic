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
