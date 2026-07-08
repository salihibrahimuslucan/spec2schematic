"""Electrical rule checks (ERC) over a loaded spec.

These are deterministic, order-stable checks that catch the kinds of
mistakes a wiring spec commonly has: duplicate parts, references to parts
or ports that don't exist, and nets that don't actually connect anything.
Errors block a valid drawing; warnings are advisory.
"""
from __future__ import annotations

from dataclasses import dataclass

from .schema import Spec


@dataclass(frozen=True)
class Issue:
    severity: str  # "error" or "warning"
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity.upper()} {self.code}] {self.message}"


def check(spec: Spec) -> list[Issue]:
    """Run all rule checks and return the issues in a stable order."""
    issues: list[Issue] = []
    issues += _duplicate_component_ids(spec)
    issues += _unknown_references(spec)
    issues += _dangling_nets(spec)
    issues += _floating_ports(spec)
    return issues


def has_errors(issues: list[Issue]) -> bool:
    return any(issue.severity == "error" for issue in issues)


def _duplicate_component_ids(spec: Spec) -> list[Issue]:
    seen: set[str] = set()
    out: list[Issue] = []
    for component in spec.components:
        if component.id in seen:
            out.append(Issue("error", "E001", f"duplicate component id '{component.id}'"))
        seen.add(component.id)
    return out


def _unknown_references(spec: Spec) -> list[Issue]:
    ports_by_component = {c.id: set(c.ports) for c in spec.components}
    out: list[Issue] = []
    for net in spec.nets:
        for endpoint in net.connects:
            if endpoint.component not in ports_by_component:
                out.append(
                    Issue(
                        "error",
                        "E002",
                        f"net '{net.name}' references unknown component '{endpoint.component}'",
                    )
                )
            elif endpoint.port not in ports_by_component[endpoint.component]:
                out.append(
                    Issue(
                        "error",
                        "E003",
                        f"net '{net.name}' references unknown port '{endpoint}'",
                    )
                )
    return out


def _dangling_nets(spec: Spec) -> list[Issue]:
    out: list[Issue] = []
    for net in spec.nets:
        if len(net.connects) < 2:
            out.append(
                Issue("error", "E004", f"net '{net.name}' connects fewer than 2 endpoints")
            )
    return out


def _floating_ports(spec: Spec) -> list[Issue]:
    connected = {(ep.component, ep.port) for net in spec.nets for ep in net.connects}
    out: list[Issue] = []
    for component in spec.components:
        for port in component.ports:
            if (component.id, port) not in connected:
                out.append(
                    Issue("warning", "W001", f"port '{component.id}.{port}' is not connected to any net")
                )
    return out
