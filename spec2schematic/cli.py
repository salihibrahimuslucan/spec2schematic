"""Command-line entry point: check a spec and report its netlist + ERC.

Exit codes: 0 = clean, 1 = ERC errors, 2 = usage / bad spec file.
"""
from __future__ import annotations

import sys

from .erc import check, has_errors
from .schema import SpecError, load_spec


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python -m spec2schematic.cli <spec.yaml>")
        return 2

    try:
        spec = load_spec(argv[0])
    except (SpecError, FileNotFoundError) as exc:
        print(f"spec error: {exc}")
        return 2

    print(f"spec: {spec.name}")
    print(f"  {len(spec.components)} components, {len(spec.nets)} nets")
    for net in spec.nets:
        ends = ", ".join(str(ep) for ep in net.connects)
        print(f"  net {net.name}: {ends}")

    issues = check(spec)
    if not issues:
        print("ERC: clean")
        return 0

    print(f"ERC: {len(issues)} issue(s)")
    for issue in issues:
        print(f"  {issue}")
    return 1 if has_errors(issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
