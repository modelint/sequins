# TabletSVG handoff — universal `color_override`

**From:** Sequins (the layout engine that drives TabletSVG)
**To:** the TabletSVG agent
**Repo to edit:** `/Users/starr/SDEV/Python/PyCharm/TabletSVG` (pkg `tabletsvg`, GitHub `modelint/tablet-svg`)

## Goal

Make a **`color_override` parameter available on *every* drawn primitive**, with one
uniform name, signature shape, and value semantics. The override was originally added for a
few special cases; the intent has always been to expose it for any drawn element. Sequins
needs it to implement two model rules (see "Why Sequins needs this" below).

## Current state (verified against the repo on 2026-06-15)

Already implemented and resolving through `CrayonBox.resolve_color`:

| Primitive | Entry point(s) | Param | Target attribute |
|---|---|---|---|
| `LineSegment` | `add` | `color_override` | `stroke` |
| `TextElement` | `add_line`, `pin_block`, `add_block` | `color_override` | `fill` |
| `Symbol` | `__init__` | `color_override` | `stroke` |

**Gaps to close:**

- **`RectangleSE.add`** — takes `color_usage` (a *semantic indirection*: usage-name →
  color-name via `color_usages.yaml`), **not** `color_override`. This is the main
  inconsistency. Add a direct `color_override` here too (keep `color_usage` for
  back-compat — see precedence decision below). Override the **fill**.
- **`CircleSE.add`** — no override. Add `color_override` (fill).
- **`PolygonSE.add`** (closed) — add `color_override` (fill).
- **`PolygonSE.add_open`** — add `color_override` (stroke, like a line).
- **`Image`** — N/A (no color).

## The contract Sequins depends on

1. **Name & signature:** keyword param `color_override: str | None = None`, added as the
   **last** parameter so existing positional calls are unaffected.
2. **No-op when omitted:** with `color_override=None` the output must be **byte-identical**
   to today's. This is non-negotiable — Sequins' render smoke test currently asserts exact
   element counts and will diff the SVG.
3. **Value semantics = `CrayonBox.resolve_color`:** the value is either a key in
   `colors.yaml` (→ that color's rgb) or any raw CSS color string (passthrough). Use the
   same `resolve_color` path already used by `LineSegment`/`Symbol`/`TextElement` so all
   primitives behave identically. Do **not** route `color_override` through the
   `color_usages.yaml` indirection.
4. **Target attribute by primitive:** stroke for stroked shapes (line, open polygon,
   symbol), fill for filled shapes (rectangle, closed polygon, circle) and text — matching
   the table above.

## Decision needed — rectangle `color_override` vs `color_usage`

`RectangleSE.add` will then accept both. Proposed precedence (please confirm or adjust):

> If both are supplied, **`color_override` wins** (it is the explicit, direct color).
> `color_usage` remains the semantic default. If only `color_usage` is given, behavior is
> unchanged.

## Why Sequins needs this

Two rules in the Sequins model (`documentation/models/sequins.xcm`) require per-element
color, applied at render time in `src/sequins/render.py`:

- **`Curtain Diagram.Thread color match` (R23)** — each Thread is drawn in its endpoint
  String's color (in the elevator example: UI lime green, Transfer aqua, SIO magenta). This
  is a `LineSegment` color, and the *installed* package doesn't expose it yet (see below).
- **`Element.Override color`** — any String/Bead/Thread can carry an explicit color
  overriding the presentation default. This needs the override on `LineSegment` (strings),
  `RectangleSE` (beads), and `TextElement` (labels) uniformly.

## ⚠️ Installed package is behind the repo

Sequins runs the **installed** `tabletsvg` in its venv
(`/Users/starr/SDEV/Environments/Sequins/lib/python3.14/site-packages/tabletsvg`), and that
copy is **older than the repo** — its `LineSegment.add` does **not** yet have
`color_override`. So the deliverable includes:

- Bump the package version (`pyproject.toml`).
- Reinstall into the Sequins venv (e.g. `pip install -e .` from the TabletSVG repo, or
  rebuild+install) so Sequins picks up both the existing line/text/symbol overrides **and**
  the new rectangle/circle/polygon ones.

## Acceptance criteria

- [ ] `color_override: str | None = None` present (last param) on `RectangleSE.add`,
      `CircleSE.add`, `PolygonSE.add`, `PolygonSE.add_open`; already-present on
      `LineSegment.add`, `TextElement.{add_line,pin_block,add_block}`, `Symbol.__init__`.
- [ ] Each resolves via `CrayonBox.resolve_color` (colors.yaml key **or** raw CSS).
- [ ] Omitting it yields byte-identical SVG to the prior version (regression guard).
- [ ] Per-primitive unit test: an override sets the expected `stroke`/`fill` to the
      resolved color.
- [ ] Rectangle `color_override` + `color_usage` precedence implemented as confirmed above.
- [ ] Version bumped and reinstalled into the Sequins venv.

## Note for both sides — color-name resolution gotcha

Sequins' theme colors (from `diagram_theme.yaml`) include names like `lime green`. As raw
CSS that is **invalid** (CSS is `limegreen`, no space); `aqua` and `magenta` are valid CSS.
So either these names must exist as keys in the active presentation's `colors.yaml`, or
Sequins must normalize them before passing. This is a Sequins-side concern, flagged here so
the TabletSVG agent doesn't try to "fix" unknown color names inside `resolve_color` — the
current fallback-to-raw-CSS behavior is correct and should stay.
