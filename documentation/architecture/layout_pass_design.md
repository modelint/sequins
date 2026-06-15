# Layout Pass Design Sketch (#3)

Status: **largely implemented.** This started as the plan we talked through before coding the
resolution step; it's now kept current as a record of what `layout.py` (the `Layout` class)
and `render.py` actually do. Built: the full vertical/horizontal pipeline (#1–#5, #7, #8) plus
#6 *in part* (arrowheads + bounded-String knots). Still open are the items called out below —
text-tight spacing, slip-knot gaps + fanning, absolute depth mode, and bead-label centering.

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

### 2. String x-coordinates  ·  *built v1 (`_assign_x`)*
Walk positions left→right, accumulating an inter-string span per gap.

- **Rule (full):** each gap fits its content — the widest bead that sits on the bounding
  strings plus the longest thread label crossing the gap — never below `min string span`.
- **v1 (built):** uniform span = `max(min string span, widest bead + min thread separation)`,
  first string inset half a bead. A correct topology, not text-tight. The reference gaps run
  103–189px; matching them needs text measurement (see *Text seam*), deferred per the
  "basics first, defer weighting" call.

### 3. Bind deferred endpoints (UI)  ·  *built (`_bind_endpoints`)*
For each thread endpoint still `None`, choose the same-named instance whose `x` is nearest
the *other* endpoint's `x`. Needs step 2. Verified: `Stop request` from UI binds to **UI-L**
(|111−300|=189 ≪ |1402−300|), matching the reference. (Shortest distance only; congestion
weighting deferred. Exact ties → first by position, a v1 artifact of uniform spacing.)

### 4. Global depth axis → y  ·  *built, compressed only (`_build_depth_axis`)*
Collect the depth of every Bead and every **bare-origin** thread (beaded-origin threads
inherit their source bead's depth, already in the set). Sort unique ascending → assign rows.

- **Compressed (built):** uniform row pitch = `standard bead height + min bead separation`
  (any two adjacent rows clear a bead; thin threads fit trivially). Per-string non-overlap
  then comes for free — consecutive beads on one string are separated by many global rows.
- **Absolute:** pitch ∝ Δdepth, floored at the compressed pitch. **Deferred** (see Two axes).
- The actual y is assigned in #8; this pass fills `Bead.compressed_depth` and
  `Thread.height` (the thread's depth distance down the axis).

### 5. Bead sizing  ·  *built v1 (`_size_beads`)*
- **Rule:** width/height between `min bead size` and the material's `standard size`, grown to
  fit the state label.
- **v1 (built):** every bead = `standard size` (50×25). The minimums won't fit labels;
  standard does. The long states (`WAITING FOR REQUESTS TO CLEAR`) prove real metrics are
  eventually required (text seam). **Open:** text-tight growth + bead-label centering.

### 6. Knots & gaps  ·  *partly built*
- **Source (R26):** a beaded-origin thread projects from the **lowest bead on its from-string
  at issue time** = `from_string.beads[-1]` when the command arrived. *Population-time
  knowledge* (creation order, not recoverable from depths at the end) — so `add_thread`
  records `thread.source_bead`. **Built** (facade addition made).
- **Bounded ends (built):** `render._draw_end_knots` places the material's `top_end`/
  `bottom_end` knot symbols (`create delete`) — birth at every bounded String's `y_top`,
  death at `y_bottom` only once `End_string` has marked it dead (`lower_bounded`).
- **Arrowheads (built):** `render._draw_arrowheads` tips a `target lifeline` symbol into each
  thread's target, oriented by travel direction (rightward 90° / leftward 270°) and colored to
  match the thread. Drawn from the placed `from_point`/`to_point`, so it lives in render, not
  the layout pass.
- **Target gap (slip knot) — DEFERRED:** the thread should meet a beaded to-string in the *gap*
  bounded above by the deepest bead with `depth ≤ thread depth` (the "slip knot blocking bead",
  R11); if the natural y lands on a bead row, slip into the adjacent gap. v1 lands the thread
  on the target's x at the thread row, accepting possible bead-row overlap.
- **Fanning — DEFERRED:** threads sharing one bead face should spread via `fixed_knot` (+1/−1/…).
- Both deferred items are layout-pass work (they move where a thread lands) and need the gap
  model; the arrowhead/knot rendering above will then follow the adjusted points for free.

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

**Text measurement seam.** Steps 2 and 5 want string widths. Proposed single
`measure_text(text, asset) -> width` interface: v1 = rough char-width estimate; v2 = Tablet's
real font metrics. **Still open** — not yet built (v1 uses fixed standard sizes/spans). Pairs
with bead-label centering (the `_centered_pin` recipe in
`TabletSVG/issues/seq_diagram_test_issues.md`).

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
