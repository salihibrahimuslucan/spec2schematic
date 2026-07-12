"""Content-fidelity checks: does the drawing say what the spec says?

``lint.py`` answers "is the picture readable?" (geometry). This module
answers a different question: "is the picture telling the truth?". Every
visible label in a ``Drawing`` carries an ``origin`` string pointing back at
the exact spec field it was read from (see ``layout.Label.origin``). That
lets these checks catch the classic way a schematic tool drifts from the
netlist it claims to draw: a renderer that quietly prints a baked-in string
for a component type or rating instead of reading it from the spec. Once
that happens, the drawing keeps rendering fine and every geometry lint stays
clean — nothing in the picture itself looks wrong, because the check that
would catch it was never run.

Checks:

- P001: a spec component, port, or net has no corresponding label in the
  drawing (something the spec describes was silently dropped from the
  picture).
- P002: a label's origin does not resolve to a real field of the spec that
  produced the drawing (the traceability claim itself is wrong, e.g. after
  a copy-paste edit to layout code).
"""
from __future__ import annotations

from dataclasses import dataclass

from .layout import Drawing
from .schema import Spec


@dataclass(frozen=True)
class Finding:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def check(spec: Spec, drawing: Drawing) -> list[Finding]:
    """Run all provenance checks and return findings in a stable order."""
    findings: list[Finding] = []
    findings += _coverage(spec, drawing)
    findings += _origin_integrity(spec, drawing)
    return findings


def _coverage(spec: Spec, drawing: Drawing) -> list[Finding]:
    """P001: every component, port, and net in the spec must be drawn."""
    out: list[Finding] = []
    drawn_origins = {label.origin for label in drawing.labels}

    for component in spec.components:
        if f"component:{component.id}.id" not in drawn_origins:
            out.append(Finding("P001", f"component '{component.id}' has no id label"))
        for i, port in enumerate(component.ports):
            if f"component:{component.id}.ports[{i}]" not in drawn_origins:
                out.append(Finding("P001", f"port '{component.id}.{port}' has no label"))

    for net in spec.nets:
        origin = f"net:cable:{net.cable}" if net.cable else f"net:{net.name}"
        if origin not in drawn_origins:
            out.append(Finding("P001", f"net '{net.name}' has no label"))
    return out


_VALID_PREFIXES = ("component:", "net:")


def _origin_integrity(spec: Spec, drawing: Drawing) -> list[Finding]:
    """P002: every label's origin must resolve to a real spec field."""
    component_ids = {c.id for c in spec.components}
    net_names = {n.name for n in spec.nets}
    cable_names = {n.cable for n in spec.nets if n.cable}

    out: list[Finding] = []
    for label in drawing.labels:
        origin = label.origin
        if not origin or not origin.startswith(_VALID_PREFIXES):
            out.append(Finding("P002", f"label '{label.text}' has no traceable origin"))
            continue
        if origin.startswith("net:cable:"):
            cable = origin[len("net:cable:"):]
            if cable not in cable_names:
                out.append(
                    Finding("P002", f"label '{label.text}' origin '{origin}' "
                                     f"names unknown cable '{cable}'")
                )
        elif origin.startswith("net:"):
            name = origin[len("net:"):]
            if name not in net_names:
                out.append(
                    Finding("P002", f"label '{label.text}' origin '{origin}' "
                                     f"names unknown net '{name}'")
                )
        elif origin.startswith("component:"):
            comp_id = origin[len("component:"):].split(".", 1)[0]
            if comp_id not in component_ids:
                out.append(
                    Finding("P002", f"label '{label.text}' origin '{origin}' "
                                     f"names unknown component '{comp_id}'")
                )
    return out
