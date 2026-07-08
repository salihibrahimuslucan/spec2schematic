# Rendering notes

Design notes for the deterministic renderer on the roadmap. The ERC gate decides
whether a spec _may_ be drawn; these notes are about drawing it _well_ — the
conventions a generated schematic needs so that a human reading it interprets the
picture the same way the netlist means it.

They are written down first, before the renderer, because the hard part of
schematic rendering is not emitting lines — it is emitting lines that read
unambiguously. A wire that is electrically correct but drawn ambiguously is a
bug, and the reader has no way to know the netlist disagrees with the picture.

## 1. A two-conductor cable is one line, not a shared node

A differential pair, or any two-signal cable (say `A+` / `A-`), runs between two
connectors as a single cable in the drawing — but the two conductors are
**distinct nets** and must never be joined.

The trap: feeding both destination pins from one shared wire with a junction dot.
A junction dot means _"these are the same node."_ Put one where a `+` and a `-`
meet and you have drawn a short — even though the netlist keeps them separate,
the _drawing_ now lies.

Convention:

- Draw the cable as a single line for its run.
- Break it out to the two pins **at the connector**, landing on the midpoint
  between them; the fan-out to each pin is implicit at the terminal strip.
- **No junction dot at the breakout.** A dot is reserved for a genuine shared
  node (e.g. a rail tap). The two conductors of a cable are not a shared node.

Rule of thumb: if removing a dot would change which nets are connected, it is
load-bearing and must stay; a dot that only _looks_ connected is a short waiting
to be misread.

## 2. Route around a block, never through it

A wire leaving a port should reach its destination through open channels — never
across the body, title band, or label graphics of a component.

A port sits on an edge and faces outward: a bottom port exits downward, a top
port upward. Honour that first move, then detour through the gaps between blocks.
A wire that goes _"up"_ out of a bottom port and straight through the component
it just left is legal in the netlist and unreadable on paper.

Convention:

- Leave the port in its facing direction for a short stub.
- Travel in the open lane between blocks (there is almost always one; the
  placement step should reserve it).
- Turn toward the destination only in open space.

## 3. Cross rails cleanly, once

Signals often must cross shared power or bus rails. A crossing is fine; a
crossing is not a connection unless a dot says so.

- Cross a rail **orthogonally, once**, in open space above or below the dense
  terminal band — not inside it.
- Do not run a shared horizontal _through_ a row of terminals: it reads as
  tapping every pin it passes, the same short-by-drawing failure as rule 1.
- Put the single turn toward the destination on the far side of the rails it
  crosses, so the final drop into the connector touches nothing on the way.

## Why this belongs in a golden gate

Every rule above is a deterministic geometry decision: given the same spec and
placement, the same wire is drawn the same way, every time. That is what makes a
golden-image test meaningful — the frozen output encodes these conventions, and
any diff is either an intended change (re-freeze it, and say why in the commit)
or a regression (one of these rules just broke). The renderer's job is to make
the conventions automatic; the golden gate's job is to keep them from silently
eroding.
