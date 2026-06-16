# Layout Pass Design Sketch (#3)

Status: **largely implemented.** This started as the plan we talked through before coding the
resolution step; it's now kept current as a record of what `layout.py` (the `Layout` class)
and `render.py` actually do. Built: the full pipeline (#1–#8), including #6 (fanning,
slip-knot blocking-bead recording, arrowheads, bounded-String knots), label-driven bead
sizing/wrapping + bead-label centering (#5), and content-driven spans (#2) — both through the
text-measurement seam. Still open: absolute depth mode and span congestion weighting (below).

## Where it sits

`end_diagram()` is the trigger. By then the curtain metamodel is fully populated (Strings,
Beads, Threads) but every geometry field is `None` and multi-position thread endpoints are
unbound. `Layout(diagram).resolve()` fills:

- `String.position` (OR2), `.x`, `.y_top`, `.y_bottom`
- `Bead.compressed_depth`, `.absolute_depth`, `.center`, `.size`
- `Thread.from_string`/`.to_string` (bind deferred UI), `.color`, `.height`, `.source_bead`,
  `.fixed_knot`
- `CurtainDiagram.origin`, `.size`, `.rod_height`

Rendering is a **separate** pass: `render.py` walks the resolved model and emits TabletSVG
primitives. (`source_bead` is recorded earlier still, at population time — see #6.)

## Two axes

**Horizontal = String order (OR2).** A discrete left-to-right ordering, then an x per slot.

**Vertical = depth.** A single global chronological axis shared by *all* strings — two beads
at the same depth on different strings share a y (e.g. `REQUESTED`@1.003 on ASLEV and
`Search for new destination`@1.003 on R53 align). Depth increases **downward**; Tablet is
y-up, so the final mapping inverts. Sequins owns that flip (in #8, the single conversion point).

- **Compressed mode (default):** depth is treated as *ordinal*. Collapse the raw values to
  evenly spaced rows so the tiny compute-time `.001` steps and the big wait-for-event jumps
  (1.011 → 5.000 → 8.000 …) all render at the same minimal pitch. This is why the doc says
  the `.001` increments "have no effect on vertical spacing." **Implemented.**
- **Absolute mode:** row gap ∝ raw depth delta (with a min floor), preserving real-time gaps.
  Not exercised by the elevator example. **Deferred** — its spacing must distinguish near-instant
  compute-time `.001` steps from real-time integer jumps, which needs its own design.

## Sub-pass pipeline

Ordered by dependency; `Layout.resolve()` runs them in this order (with #7 between #3 and #5).
Each notes the **rule**, the **v1 simplification as built**, and any remaining **open Qs**.

### 1. String positions (OR2) — no geometry yet  ·  *built (`_assign_positions`)*
Partition strings into left-pinned / interior / right-pinned by `String.pinned`:

- **left-pinned** (`boundary == 'L'`): sort by **ascending** offset (0 = leftmost edge).
- **interior** (`pinned is None`): keep **creation order**.
- **right-pinned** (`boundary == 'R'`): sort by **descending** offset (0 = rightmost edge,
  larger offset = further inward/left).

Concatenate → assign `position` 1..N. Verified against the reference:
`UI(L) · ASLEV · R53 · Transfer · Cabin · Door · TRANS(R-2) · SIO(R-1) · UI(R-0)` — exactly
the rendered order. So the right-edge offsets read "rank inward from the right."

### 2. String x-coordinates  ·  *built, uniform & label-driven (`_assign_x`)*
One **global, uniform** span between every adjacent string (so the diagram stays evenly
ruled); first string inset half a bead.

- **Rule:** the span clears adjacent beads and is wide enough that *every* message label —
  anchored `Target string label gap` (30px) off its destination and running back toward the
  source — clears the source bead it springs from by at least `Min bead edge gap` (20px). Both
  are configurable `Layout` attributes. This is the **horizontal lever**: the fallback when
  vertical opening (#4) can't help, because a too-wide label clips a bead at its own row.
- **Built:** `span = max(min string span, bead width + min thread separation, max over threads
  of (target gap + label width + ½ source bead + bead gap) / gaps crossed)`. A thread crossing `g` gaps has
  `g` spans of room, so multi-gap threads rarely bind; the driver is a long label across a
  single gap. Threads are bound (#3) first; labels measured via the *Text seam*. Elevator →
  209px uniform (driven by `Cabin at destination`). Going uniform replaced an earlier per-gap
  span; congestion weighting stays deferred.

### 3. Bind deferred endpoints (UI)  ·  *built (`_bind_endpoints`)*
For each thread endpoint still `None`, choose the same-named instance whose `x` is nearest
the *other* endpoint's `x`. Needs step 2. Verified: `Stop request` from UI binds to **UI-L**
(|111−300|=189 ≪ |1402−300|), matching the reference. (Shortest distance only; congestion
weighting deferred. Exact ties → first by position, a v1 artifact of uniform spacing.)

### 4. Global depth axis → y  ·  *built, compressed only (`_build_depth_axis`)*
Collect the depth of every Bead and every **bare-origin** thread (beaded-origin threads
inherit their source bead's depth, already in the set). Sort unique ascending → stack rows
downward with a **per-gap** spacing (runs after #5 so real bead heights are known).

- **Compressed (built):** the gap between two adjacent rows is
  `½ taller bead above + separation + ½ taller bead below`, where
  `separation = max(min bead separation, label height need)`:
  - **Beads clear each other** using *actual* heights — two stacked 2-line (wrapped) beads
    keep their `min bead separation`, where a single uniform pitch sized for standard beads
    would let them collide. Standard rows reduce to the old `standard height + min bead
    separation` (45px); tall rows open to 52/59px in the elevator.
  - **Labels fit (the vertical lever, first choice):** a thread's message label rides in the
    gap *above* its row; the gap opens further if the label needs more height than the bead
    separation already gives. Short labels fit the standard gap, so this only bites for
    tall/wrapped labels (none yet — thread-label wrapping is deferred).
- **Absolute:** gap ∝ Δdepth, floored at the compressed gap. **Deferred** (see Two axes).
- The actual y is assigned in #8; this pass fills `Bead.compressed_depth` and
  `Thread.height` (the thread's depth distance down the axis).

### 5. Bead sizing  ·  *built, label-driven (`_size_beads`)*
- **Rule:** a bead fits its state label, wrapping the label and growing as needed.
- **Built:** the label word-wraps so each line fits the material's `standard size` *width*
  (the wrap boundary); a bead grows taller for the extra lines (`min bead separation` keeps
  rows clear regardless). Width is **uniform** across the diagram — the widest wrapped line
  plus `bead text padding` (horizontal), floored at `min bead size` width — so bead edges
  line up like the reference. Height per bead = wrapped block + vertical padding, floored at
  `standard size` height. Reproduces the reference closely: uniform width 156 (ref 150.89),
  single-line height 25, wrapped (2-line) height 39.3 (ref 39.39). Labels are measured and
  rendered through the *Text seam*; `render._draw_beads` centers the wrapped block on the
  bead center (the `_centered_pin` recipe). Single unbreakable words wider than the boundary
  are left to overflow (none in the elevator). **Open:** per-material `bead text padding` is
  one shared value; tune in `layout.yaml`.

### 6. Knots & gaps  ·  *built*
- **Source (R26):** a beaded-origin thread projects from the **lowest bead on its from-string
  at issue time** = `from_string.beads[-1]` when the command arrived. *Population-time
  knowledge* (creation order, not recoverable from depths at the end) — so `add_thread`
  records `thread.source_bead`. **Built** (facade addition made).
- **Fanning (R26 Fixed knot) — built (`_fan_source_knots`):** Threads sharing a Bead *face*
  (same source bead + same side) are spread to symmetric integer notches centered on the face
  (n=2 → −1,+1; n=3 → −2,0,+2). Each thread shifts as a whole (both endpoints) to stay
  horizontal; a lone thread keeps knot 0. Adjacent notches are spaced
  `LABEL_LINE_CLEARANCE + label height + LABEL_LINE_CLEARANCE` (≥ `min thread separation`) so a
  thread's message label clears the line above it — otherwise a long upper thread line would
  cross the lower thread's label (the `Check for active floor service` → `Stop serviced` /
  `Cabin arrived` case). Also exercised by the two `Door opening` threads off `OPENING`.
- **Target gap (slip knot) — built (`_slip_knot_gaps`):** each thread terminating on a beaded
  String records the Bead it sits *above* (R11 *slip knot blocking bead*) = the nearest Bead
  below its landing. The compressed depth axis already keeps every thread one row above its
  target's response bead (no depth ever coincides with a target bead in the elevator), so no y
  moves — this pins down the blocking Bead the model (Thread to Bead Gap) calls for. `None`
  means it lands above the topmost Bead (a bounded String's top). *If a future case put a
  thread's row on a target bead, this is where we'd clamp it up into the gap.*
- **Bounded ends (built):** `render._draw_end_knots` places the material's `top_end`/
  `bottom_end` knot symbols (`create delete`) — birth at every bounded String's `y_top`,
  death at `y_bottom` only once `End_string` has marked it dead (`lower_bounded`). The burst
  pins by its bottom center and reaches upward, so `_frame_and_place._death_knot_y` drops a
  dead String's `y_bottom` below its deepest Bead — far enough that the *top* of the burst
  (its measured height, via `text.symbol_top_extent`) clears the Bead by `min bead
  separation`; the boundary line continues down to meet it. (Birth needs no such drop: a
  String is born at its birth *thread*, already shallower than its first Bead.)
- **Arrowheads (built):** `render._draw_arrowheads` tips a `target lifeline` symbol into each
  thread's target, oriented by travel direction (rightward 270° / leftward 90° — the glyph is
  tip-down) and colored to match the thread. The tip (and the thread line end) stop
  `_ARROW_TARGET_GAP` (2px) short of the lifeline via `render._arrow_tip`, so they don't
  overlap it; `to_point` stays the true terminus for label/knot logic. Drawn from the placed
  (fanned) `from_point`/`to_point`, so it lives in render, not the layout pass.

### 7. Thread color match (String Color)  ·  *built (`_match_thread_colors`)*
`thread.color` = the color of a String-Colored endpoint it touches at **either** end; if both
ends are colored, **source (from) wins**. An explicit Thread `Override color` beats the match.
Runs after #3 so UI is bound; `render` passes it (and `String` color) as `color_override`
(needs TabletSVG ≥ 1.5.0). Reference: UI threads lime, TRANS aqua, SIO magenta.
**NB:** this rule isn't formalized in `sequins.xcm` yet — `Thread` carries only `Material` —
so the rule currently lives in the `_match_thread_colors` docstring.

### 8. Canvas frame + y-flip  ·  *built (`_frame_and_place`)*
The single place model depth (downward) becomes Tablet y-up. From the string x-extent and
depth y-extent: `rod_height` = strings' `y_top`; `size` = content bbox + `Canvas.padding`
(dark = top150/bottom100/left25/right25); `origin` = lower-left. Sets every `Bead.center`,
each `Thread.from_point`/`to_point` (horizontal at the thread row), and each String's
`y_top`/`y_bottom` (persistent strings hang rod→bottom; bounded strings float between their
shallowest and deepest events).

## Cross-cutting

**Coordinate flip.** Computed depth grows downward from the rod, converted to Tablet's y-up
**once**, in #8's `y_at(distance)`. One conversion point, clearly owned, per the Tablet contract.

**Text measurement seam.** Steps 2 and 5 want string widths. **Built** as
`sequins/text.py::TextMeasure` — a thin wrapper over TabletSVG's `TextElement.text_block_size`
(Pillow font metrics, with a 0.6× char-width fallback when a typeface isn't configured),
keyed on Sequins' asset names. Built once per layout pass from the active theme (drawing type
= Curtain Style name; presentation mirrors the Canvas), so measured sizes match what `render`
draws. Provides `block_size`, `line_width`, `wrap` (greedy word wrap), and
`symbol_top_extent`. `render._draw_beads` uses it to center the wrapped block on the bead
center (the `_centered_pin` recipe in `TabletSVG/issues/seq_diagram_test_issues.md`); #2/#4
use it to reserve span/row space for labels.

**Message-label placement.** Drawn in `render._draw_threads`, not the layout pass. Each label
**hugs its destination String**: its near edge sits the configurable `Target string label gap`
(30px) off the target, on the side the thread arrives from, riding `LABEL_LINE_CLEARANCE` (4px)
above the line. (`Target string label gap` and `Min bead edge gap` are `Layout` model
attributes read from config; the vertical `LABEL_LINE_CLEARANCE` stays a constant in `layout.py`,
shared with `render` so the space #2/#4 reserve matches what's drawn.) Two levers keep labels
clear of beads — **vertical** gap opening (#4, first
choice) for labels squeezed between stacked beads, and **uniform horizontal** widening (#2,
fallback) for labels too wide to clear a neighbouring bead. Wrapping long thread labels is
deferred (they're short in practice).

**Symbol names — confirmed.** `target lifeline` and `create delete` check out against
`~/.config/mi_tablet/symbols.yaml` (group "Starr sequence diagram");
`Symbol(layer, name, pin, angle, color_override)` with angle 0=up/90=right/180=down/270=left,
pin = bottom-center, and `color_override` available.

## Decisions (resolved during implementation)

1. **v1 spacing from minimums** (topologically correct, not text-tight) — chosen. Text
   measurement to match reference pixel gaps stays deferred.
2. **`thread.source_bead` recorded at population time** — yes, `add_thread` sets it from
   `from_string.beads[-1]` for a beaded, bound origin.
3. **`Thread.Height`** = the thread's y-level (its depth distance down the axis); the model's
   naming was just loose. Filled in #4, used in #8.
4. **Module shape** — a `Layout` **class** holding the shared scratch (depth-row map, position
   order, span, widest bead), mutating the `CurtainDiagram` in place.
5. **Build order** — **vertical-axis-first** (depth axis #4 before the horizontal passes), since
   it's the conceptual core and easiest to unit-test against bead depths.
