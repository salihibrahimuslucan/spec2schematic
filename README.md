# spec2schematic

Turn a small YAML **wiring spec** into a checked, deterministic schematic. You describe
components and how their ports connect; the tool validates the spec, runs electrical rule
checks, and renders a laid-out drawing as SVG (or DXF). The same input always produces the
same bytes, so every drawing is diffable, testable, and frozen behind a golden gate.

<p align="center">
  <img src="tests/golden/divider.svg" alt="Rendered schematic of the voltage divider example" width="420">
</p>

The image above is not a screenshot — it is [one of the golden files](tests/golden/) the test
suite compares against byte-for-byte, so the README can never drift from what the code emits.

## Quickstart

```bash
pip install -e ".[dev]"

# print the netlist and run electrical rule checks
spec2schematic check examples/divider.yaml

# render a schematic (deterministic: same spec, same bytes)
spec2schematic render examples/divider.yaml -o divider.svg

# geometry lint over the rendered drawing
spec2schematic lint examples/*.yaml

python -m pytest
```

DXF export is an optional extra:

```bash
pip install -e ".[dxf]"
spec2schematic render examples/dol_starter.yaml -o dol_starter.dxf
```

## Architecture

```
 spec.yaml
    |
    v
 schema.py ---> Spec: components, ports, nets (+ optional cable grouping)
    |
    v
 erc.py ------> electrical rule gate  (E001..E004, W001; errors block rendering)
    |
    v
 layout.py ---> Drawing: boxes, pins, wire segments, junction dots, labels
    |                     |
    |                     +--> lint.py: geometry lint (L001..L004)
    v
 render_svg.py --> .svg   byte-stable, golden-tested
 render_dxf.py --> .dxf   optional, via ezdxf
```

Both renderers consume the exact same `Drawing`, so SVG and DXF always agree on geometry.
The lint pass also runs on the `Drawing`, not on the output text, so one set of checks gates
every format.

## Spec format

```yaml
name: voltage-divider
components:
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

An endpoint is written `COMPONENT.PORT`. Nets may name a shared `cable`; those nets stay
electrically distinct but are drawn as a single line with a conductor-count label
(see [docs/rendering-notes.md](docs/rendering-notes.md)). Example specs:
a [voltage divider](examples/divider.yaml), a [DOL motor starter](examples/dol_starter.yaml)
control circuit, and a [tank level control](examples/tank_level.yaml).

## Rule checks

Electrical (block or warn before any drawing):

| Code | Severity | Meaning                                           |
|------|----------|---------------------------------------------------|
| E001 | error    | duplicate component id                            |
| E002 | error    | net references a component that doesn't exist     |
| E003 | error    | net references a port the component doesn't have  |
| E004 | error    | net connects fewer than two endpoints             |
| W001 | warning  | a declared port is not connected to any net       |

Geometry (lint over the laid-out drawing):

| Code | Meaning                                             |
|------|-----------------------------------------------------|
| L001 | a wire passes through a component body              |
| L002 | two wire segments overlap collinearly               |
| L003 | a label collides with another label or with a wire  |
| L004 | a pin is drawn but connected to nothing             |

## Testing

The project is developed with heavy test automation: unit tests over every module, CLI
tests, a determinism test that renders in subprocesses under different `PYTHONHASHSEED`
values and requires byte-identical output, and a golden gate — the rendered SVG of every
example is committed and compared byte-for-byte on each run. To change the renderer you
must re-freeze the goldens (`python -m pytest --update-goldens`) and justify the diff in
the commit. CI runs the suite on Python 3.11 and 3.12 and lints every example.

## Build journal — mistakes & turnbacks

An honest log of the wrong turns, kept because the reasons matter more than the fixes.

**I drew a two-conductor cable as two separate lines, and the drawing got worse as it got
more correct.** Each conductor rendered as its own parallel run, which doubled the wire
count of every cable and buried the actual topology in clutter. The turnback was realizing
the drawing and the netlist don't have to use the same representation: the netlist keeps
every conductor as a distinct net (shorting them would be a lie about the circuit), while
the drawing shows one line per cable with a conductor-count label, breaking out at the
connector. One artifact, two views, each honest in its own language.

**My first wires went straight through component blocks.** The router connected pin to pin
by the shortest orthogonal path, and the shortest path is frequently through the body of a
component — electrically meaningless, visually wrong, and unreadable on paper. Instead of
patching detours case by case, I changed where wires are allowed to exist: all routing now
lives in a channel below the component row, each net on its own lane, with only vertical
drops from pins into the channel. Wires can no longer cross a body because the geometry
gives them no way to. The lint pass (L001) still checks it, but as a tripwire, not as the
mechanism.

**I cut rails at multiple points before adopting the single clean cut.** When a wire tapped
a shared rail, early output touched the rail wherever it was convenient — multiple contact
points, ambiguous junctions, and drawings that read as if every crossing were a connection.
The convention now is one tap, one junction dot, and a dot only where it is load-bearing: if
removing it would change which nets are connected, it stays; anything else is a short waiting
to be misread. Crossings without dots are just crossings.

**The golden gate came from getting burned by "harmless" rendering tweaks.** Adjust one
layout constant and an unrelated drawing quietly reshuffles — and nothing fails, because
nothing was watching the picture itself. Now the rendered output of every example is frozen
in the repo, tests compare byte-for-byte,
and the update path is deliberately manual: re-freeze, look at the diff, and say in the
commit why the new picture is right. Determinism is what makes this workable — no
timestamps, no floats, no hash-order dependence (there is a test that renders under
different `PYTHONHASHSEED` values and demands identical bytes). An output you can't diff
is an output you can't review.

## Roadmap

- [x] Spec model + structural validation
- [x] ERC rule checks (E001–E004, W001) + CLI report
- [x] Continuous integration (GitHub Actions, pytest on 3.11/3.12)
- [x] Deterministic SVG renderer with channel routing
- [x] Golden-image test gate (freeze output, justify every diff)
- [x] DXF export via `ezdxf` (optional extra)
- [x] Geometry lint gate (L001–L004) wired into CLI and CI
- [ ] Multi-row placement for larger specs
- [ ] Wire numbering and terminal-strip tables

## License

MIT — see [LICENSE](LICENSE).
