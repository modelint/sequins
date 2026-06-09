# Sequins — Project Guide

Sequins is a tool to generate **UML / SysML v2-style sequence diagrams**, primarily for
Shlaer-Mellor Executable UML (xUML) scenarios where **states are integrated into the
lifelines**. This file is the portable, version-controlled mirror of the working context.
(Machine-local memory under `~/.claude/projects/.../memory/` may be more current.)

## Architecture (two layers)

- **Model layer** — an Executable UML class model at `documentation/models/sequins.xcm`
  (`.xcm` = executable class model) defining the geometry/layout abstractions. **This file
  is ground truth.**
- **Drawing layer** — `tablet-svg` (pkg `tabletsvg`), Leon's own SVG renderer, local at
  `/Users/starr/SDEV/Python/PyCharm/TabletSVG`, GitHub `modelint/tablet-svg`. Sequins computes
  *what* notation goes *where*; Tablet's YAML maps notation → graphics and renders.

The model uses a **beaded-curtain metaphor**, deliberately separating layout geometry from
sequence-diagram semantics: vertical `String`s (lifelines) hung from a `Rod`, adorned with
`Bead`s (states), connected by horizontal `Thread`s (interactions), anchored by knots.

## Reading the model (Shlaer-Mellor xUML notation)

- Multiplicity: `1` exactly one, `M` many (UML `1..*`), `1c` zero-or-one (`0..1`),
  `Mc` zero-or-more (`*`). `c` = *conditional* ONLY in the Relationships section.
- `{I}` identifier (≈ primary key), `{I2}` secondary identifier (≈ candidate key).
- `{Rn}` = referential attribute on relationship *n* (≈ foreign-key component).
- In an attribute tag, `{Rnc}` — the `c` does NOT mean conditional; it flags an **additional
  constraint** on relationship *n*, documented under "Constraints" on that relationship's wiki page.

## Documentation / ground truth

- **`documentation/models/sequins.xcm`** — the model. Wins over everything else.
- **Wiki** — `https://github.com/modelint/sequins/wiki`, local at `/Users/starr/SDEV/GitHub/sequins.wiki`.
  Describes each class/relationship/attribute. **Only pages linked from `_Sidebar.md` are live;**
  unlinked `.md` files are discarded leftovers. If wiki and `.xcm` disagree, `.xcm` wins.
- **`documentation/mint.sequins.tn.2.svg`** — canonical target output (elevator scenario),
  the visual spec Sequins + Tablet should reproduce (it's essentially the `dark` presentation).
- **File formats** — `.xcm` grammar + naming conventions in `documentation/notation/xcm-format.md`;
  the `.mls` layout grammar is documented in the Flatland wiki at
  `/Users/starr/SDEV/GitHub/flatland-model-diagram-editor.wiki`.

## Tablet integration contract

Construct: `Tablet(size, output_file, drawing_type="Starr sequence diagram",
presentation="dark", layer="diagram", background_color="tungsten")`; draw on
`t.layers['diagram']`; finish with `t.render()` (format from file suffix).

Primitives take `layer` + an `asset` (the notation name = Sequins `Material` name):
- `RectangleSE.add(layer, asset='state', lower_left, size, color_usage=None)` — beads
- `LineSegment.add(layer, asset, from_here, to_there, color_override=None)` — strings & threads
- `TextElement.pin_block(layer, asset, text, pin, corner, align, color_override=None)` — labels
- `Symbol(layer, name, pin, angle=0, color_override=None)` — arrowheads / knots

Assets for "Starr sequence diagram" / "dark" (see `tabletsvg/configuration/drawing_types.yaml`
+ `symbols.yaml`): shape.rectangle `state`; shape.line `lifeline` (double), `signal`,
`ext event`, `implicit ext event` (dashed); text `state name`, `lifeline name`, `message`;
symbols `target lifeline` (open arrow), `create delete` (knot burst for bounded-string ends).
Dark colors: nickel `#929292` (strings/beads), tungsten `#424242` (bg).

**Coordinate flip:** Tablet coords are lower-left origin, **y-up**; the model expresses bead
position as depth **downward from the rod**. Sequins owns the conversion. (Tablet docstrings
still say "Qt" — stale wording from the Qt→SVG migration.)

**Color overrides** implement `Element.Override color` and `Curtain Diagram.Thread color match`
via the `color_override` / `color_usage` params.

## Status & next steps

- **Phase:** model + target + drawing layer fully understood; **no Sequins code yet.**
- **Next:** architecture/implementation planning — pipeline (input → populate model instances →
  layout engine → drive Tablet), how to populate the metamodel (relation to Flatland; possibly
  PyRAL), config/library storage, MVP scope.
- The `.xcm` is **structure only**; the layout *engine* (compute compressed depth preserving
  global chronological order, place fixed/slip knots, size beads, honor Layout minimums) is
  **behavior we design fresh**.
- Open items: confirm `Symbol(name=...)` strings against `Symbol.load_symbol_defs()`; reuse the
  `_centered_pin` recipe (`TabletSVG/issues/seq_diagram_test_issues.md`) for centering bead labels.

## Conventions

- **Model-driven prompting:** Leon's workflow/experiment — Claude reads the model, asks questions,
  flags inconsistencies; Leon fixes the model. He presents on this, so the dialog is preserved in
  `documentation/model-prompting-session.md` (clean transcript), regenerated by
  `documentation/tools/gen_session_md.py` (no args = latest session). Commit/push only when asked.
- Default working branch: `refine`.
