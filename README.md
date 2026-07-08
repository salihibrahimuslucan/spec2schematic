# spec2schematic

Turn a small YAML **wiring spec** into a checked, deterministic schematic — the same
engineering pipeline used in production CAD tooling, distilled into a clean, dependency-light
open-source core.

> Status: early. The spec model, electrical rule checks (ERC) and CLI report are in place and
> tested. Deterministic SVG rendering and a golden-image test gate are next (see Roadmap).

## What it does

    YAML spec  ->  netlist  ->  ERC (rule gate)  ->  [ SVG / DXF renderer ]

You describe components and how their ports connect. The tool loads and structurally validates
the spec, builds a netlist, and runs electrical rule checks that catch the mistakes wiring specs
actually have — duplicate parts, references to parts or ports that don't exist, nets that don't
connect anything, and floating ports. Errors are meant to block a drawing; warnings are advisory.

## Design principles

- **Deterministic** — the same input always produces the same output, so results are diffable and
  testable (golden tests, once rendering lands).
- **Rule-gated** — nothing invalid should reach a drawing; the ERC pass is a gate, not a suggestion.
- **Small and readable** — no framework, minimal dependencies; every module is meant to be read
  end to end.

## Quickstart

```bash
pip install -e ".[dev]"
python -m spec2schematic.cli examples/divider.yaml
python -m pytest -q
```

Example output:

```
spec: voltage-divider
  3 components, 3 nets
  net VIN+: VIN.pos, R1.a
  net MID: R1.b, R2.a
  net GND: VIN.neg, R2.b
ERC: clean
```

## Spec format

```yaml
name: voltage-divider
components:
  - id: VIN
    type: source
    ports: [pos, neg]
  - id: R1
    type: resistor
    ports: [a, b]
  - id: R2
    type: resistor
    ports: [a, b]
nets:
  - name: MID
    connects: [R1.b, R2.a]
```

An endpoint is written `COMPONENT.PORT` (e.g. `R1.a`).

## Rule checks

| Code | Severity | Meaning                                        |
|------|----------|------------------------------------------------|
| E001 | error    | duplicate component id                         |
| E002 | error    | net references a component that doesn't exist  |
| E003 | error    | net references a port the component doesn't have |
| E004 | error    | net connects fewer than two endpoints          |
| W001 | warning  | a declared port is not connected to any net    |

## Roadmap

- [x] Spec model + structural validation
- [x] ERC rule checks (E001–E004, W001) + CLI report
- [x] Continuous integration (GitHub Actions, pytest)
- [ ] Deterministic SVG renderer (diagram inline in this README)
- [ ] Golden-image test gate (freeze output, diff on change)
- [ ] DXF export via `ezdxf`
- [ ] Lint gate that refuses to render a spec with ERC errors

## Build journal

**2026-07-08 — foundation.**
Built test-first, with LLM assistance under a harness I own: I design the pipeline and the rules,
drive an AI to implement each step, and gate every change behind ERC and tests before it lands. The
commit history is the honest record of that process. Today's foundation — the typed spec model,
four ERC error checks plus a floating-port warning, a CLI report, and a green CI pipeline.

## License

MIT — see [LICENSE](LICENSE).
