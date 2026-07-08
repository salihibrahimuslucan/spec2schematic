"""Command-line interface: check, render, and lint wiring specs.

Exit codes: 0 = clean, 1 = findings (ERC errors or lint findings),
2 = usage error / unreadable spec.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .erc import check, has_errors
from .layout import build_drawing
from .lint import lint
from .render_dxf import MissingDxfDependencyError, render_dxf
from .render_svg import render_svg
from .schema import Spec, SpecError, load_spec


def _load(path: str) -> Spec | None:
    try:
        return load_spec(path)
    except (SpecError, FileNotFoundError, OSError) as exc:
        print(f"spec error: {exc}")
        return None


def _cmd_check(args: argparse.Namespace) -> int:
    spec = _load(args.spec)
    if spec is None:
        return 2

    print(f"spec: {spec.name}")
    print(f"  {len(spec.components)} components, {len(spec.nets)} nets")
    for net in spec.nets:
        ends = ", ".join(str(ep) for ep in net.connects)
        cable = f" (cable {net.cable})" if net.cable else ""
        print(f"  net {net.name}{cable}: {ends}")

    issues = check(spec)
    if not issues:
        print("ERC: clean")
        return 0

    print(f"ERC: {len(issues)} issue(s)")
    for issue in issues:
        print(f"  {issue}")
    return 1 if has_errors(issues) else 0


def _cmd_render(args: argparse.Namespace) -> int:
    spec = _load(args.spec)
    if spec is None:
        return 2

    issues = check(spec)
    if has_errors(issues):
        for issue in issues:
            print(f"  {issue}")
        print("render blocked: fix ERC errors first")
        return 1

    out = Path(args.output)
    suffix = out.suffix.lower()
    drawing = build_drawing(spec)
    if suffix == ".svg":
        out.write_text(render_svg(drawing), encoding="utf-8", newline="\n")
    elif suffix == ".dxf":
        try:
            render_dxf(drawing, out)
        except MissingDxfDependencyError as exc:
            print(f"error: {exc}")
            return 2
    else:
        print(f"error: unsupported output format '{suffix or out.name}' (use .svg or .dxf)")
        return 2
    print(f"wrote {out}")
    return 0


def _cmd_lint(args: argparse.Namespace) -> int:
    rc = 0
    for path in args.specs:
        spec = _load(path)
        if spec is None:
            return 2

        issues = check(spec)
        findings = [] if has_errors(issues) else lint(build_drawing(spec))
        errors = [issue for issue in issues if issue.severity == "error"]

        if not errors and not findings:
            print(f"{path}: lint clean")
            continue
        rc = 1
        print(f"{path}: {len(errors) + len(findings)} finding(s)")
        for issue in errors:
            print(f"  {issue}")
        for finding in findings:
            print(f"  {finding}")
    return rc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="spec2schematic",
        description="Turn a YAML wiring spec into checked, deterministic schematics.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="print the netlist and run electrical rule checks")
    p_check.add_argument("spec", help="path to a spec YAML file")
    p_check.set_defaults(func=_cmd_check)

    p_render = sub.add_parser("render", help="render a spec to SVG or DXF")
    p_render.add_argument("spec", help="path to a spec YAML file")
    p_render.add_argument("-o", "--output", required=True, help="output file (.svg or .dxf)")
    p_render.set_defaults(func=_cmd_render)

    p_lint = sub.add_parser("lint", help="run ERC plus geometry lint over rendered specs")
    p_lint.add_argument("specs", nargs="+", help="spec YAML files to lint")
    p_lint.set_defaults(func=_cmd_lint)

    try:
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        return 2 if exc.code not in (0, None) else 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
