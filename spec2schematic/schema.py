"""Spec model: parse a YAML wiring spec into typed objects.

A spec describes components (each with named ports) and nets (named
connections between component ports). This module handles loading and
structural validation only; electrical rule checks live in ``erc.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class SpecError(ValueError):
    """Raised when a spec file is structurally invalid (bad YAML shape)."""


@dataclass(frozen=True)
class Component:
    id: str
    type: str
    ports: tuple[str, ...]


@dataclass(frozen=True)
class Endpoint:
    """One side of a connection, e.g. ``R1.a`` -> component ``R1``, port ``a``."""

    component: str
    port: str

    @classmethod
    def parse(cls, text: str) -> "Endpoint":
        if text.count(".") != 1:
            raise SpecError(f"endpoint '{text}' must be in 'COMPONENT.PORT' form")
        component, port = text.split(".")
        if not component or not port:
            raise SpecError(f"endpoint '{text}' has an empty component or port")
        return cls(component, port)

    def __str__(self) -> str:
        return f"{self.component}.{self.port}"


@dataclass(frozen=True)
class Net:
    """A named electrical node connecting two or more endpoints.

    ``cable`` optionally names the physical cable this net runs in. Nets
    sharing a cable name stay electrically distinct (separate nets in the
    netlist) but are drawn as a single cable run with a conductor-count
    label — see docs/rendering-notes.md, rule 1.
    """

    name: str
    connects: tuple[Endpoint, ...]
    cable: str | None = None


@dataclass
class Spec:
    name: str
    components: list[Component] = field(default_factory=list)
    nets: list[Net] = field(default_factory=list)


def load_spec(path: str | Path) -> Spec:
    """Load and structurally validate a spec YAML file."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SpecError("spec file must be a YAML mapping at the top level")

    components: list[Component] = []
    for i, item in enumerate(raw.get("components", []) or []):
        if not isinstance(item, dict):
            raise SpecError(f"component #{i} must be a mapping")
        if "id" not in item:
            raise SpecError(f"component #{i} is missing 'id'")
        ports = item.get("ports", []) or []
        if not isinstance(ports, list):
            raise SpecError(f"component '{item['id']}' ports must be a list")
        components.append(
            Component(
                id=str(item["id"]),
                type=str(item.get("type", "unknown")),
                ports=tuple(str(p) for p in ports),
            )
        )

    nets: list[Net] = []
    for i, item in enumerate(raw.get("nets", []) or []):
        if not isinstance(item, dict):
            raise SpecError(f"net #{i} must be a mapping")
        if "name" not in item:
            raise SpecError(f"net #{i} is missing 'name'")
        connects = item.get("connects", []) or []
        if not isinstance(connects, list):
            raise SpecError(f"net '{item['name']}' connects must be a list")
        cable = item.get("cable")
        if cable is not None and not isinstance(cable, str):
            raise SpecError(f"net '{item['name']}' cable must be a string")
        nets.append(
            Net(
                name=str(item["name"]),
                connects=tuple(Endpoint.parse(str(c)) for c in connects),
                cable=cable,
            )
        )

    return Spec(name=str(raw.get("name", "unnamed")), components=components, nets=nets)
