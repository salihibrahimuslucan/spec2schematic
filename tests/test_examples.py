from pathlib import Path

import pytest

from spec2schematic.erc import check, has_errors
from spec2schematic.schema import load_spec

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_examples_directory_has_expected_specs():
    names = sorted(p.name for p in EXAMPLES.glob("*.yaml"))
    assert names == ["divider.yaml", "dol_starter.yaml", "tank_level.yaml"]


@pytest.mark.parametrize("path", sorted(EXAMPLES.glob("*.yaml")), ids=lambda p: p.stem)
def test_example_is_erc_clean(path):
    issues = check(load_spec(path))
    assert not has_errors(issues)
    assert issues == []  # no warnings either: every declared port is wired


def test_dol_starter_seal_in_parallels_start_button():
    spec = load_spec(EXAMPLES / "dol_starter.yaml")
    nets = {net.name: {str(ep) for ep in net.connects} for net in spec.nets}
    # the contactor's aux contact bridges the two sides of the START button
    assert {"START.3", "K1.13"} <= nets["START_IN"]
    assert {"START.4", "K1.14"} <= nets["COIL"]


def test_tank_level_high_float_breaks_the_latch():
    spec = load_spec(EXAMPLES / "tank_level.yaml")
    nets = {net.name: {str(ep) for ep in net.connects} for net in spec.nets}
    # everything downstream of the supply goes through the high float (NC)
    assert "LSH.1" in nets["L1"]
    assert {"LSH.2", "LSL.1", "K1.13"} <= nets["LEVEL"]
