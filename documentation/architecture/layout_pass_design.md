# Layout Pass Design Sketch (#3)

Status: **draft for discussion** — nothing here is built yet. This is the plan we agreed to
talk through before coding the resolution step.

## Where it sits

`end_diagram()` is the trigger. By then the curtain metamodel is fully populated (Strings,
Beads, Threads) but every geometry field is `None` and multi-position thread endpoints are
unbound. The layout pass fills:

- `String.position` (OR2), `.x`, `.y_top`, `.y_bottom`
- `Bead.compressed_depth`, `.absolute_depth`, `.center`, `.size`
- `Thread.from_string`/`.to_string` (bind deferred UI), `.color`, `.height`, `.source_bead`,
  `.fixed_knot`
- `CurtainDiagram.origin`, `.size`, `.rod_height`

Then step #4 walks the resolved model and emits TabletSVG primitives.

## Two axes

**Horizontal = String order (OR2).** A discrete left-to-right ordering, then an x per slot.

**Vertical = depth.** A single global chronological axis shared by *all* strings — two beads
at the same depth on different strings share a y (e.g. `REQUESTED`@1.003 on ASLEV and
`Search for new destination`@1.003 on R53 align). Depth increases **downward**; Tablet is
y-up, so the final mapping inverts. Sequins owns that flip.

- **Compressed mode (default):** depth is treated as *ordinal*. Collapse the raw values to
  evenly spaced rows so the tiny compute-time `.001` steps and the big wait-for-event jumps
  (1.011 → 5.000 → 8.000 …) all render at the same minimal pitch. This is why the doc says
  the `.001` increments "have no effect on vertical spacing."
- **Absolute mode:** row gap ∝ raw depth delta (with a min floor), preserving real-time gaps.
  Not exercised by the elevator example but must drop in at the same seam.

## Sub-pass pipeline

Ordered by dependency. Each notes the **rule**, the **v1 simplification**, and **open Qs**.

### 1. String positions (OR2) — no geometry yet
Partition strings into left-pinned / interior / right-pinned by `String.pinned`:

- **left-pinned** (`boundary == 'L'`): sort by **ascending** offset (0 = leftmost edge).
- **interior** (`pinned is None`): keep **creation order**.
- **right-pinned** (`boundary == 'R'`): sort by **descending** offset (0 = rightmost edge,
  larger offset = further inward/left).

Concatenate → assign `position` 1..N. Verified against the reference:
`UI(L) · ASLEV · R53 · Transfer · Cabin · Door · TRANS(R-2) · SIO(R-1) · UI(R-0)` — exactly
the rendered order. So the right-edge offsets read "rank inward from the right."

### 2. String x-coordinates
Walk positions left→right, accumulating an inter-string span per gap.

- **Rule (full):** each gap fits its content — the widest bead that sits on the bounding
  strings plus the longest thread label crossing the gap — never below `min string span`.
- **v1:** uniform pitch ≥ `min string span` (a correct topology, not text-tight). The
  reference gaps run 103–189px; matching them needs text measurement (see *Text seam*),
  which I'd defer per your "basics first, defer weighting" call.
- Then `x` per string from the cumulative spans + left canvas padding.

### 3. Bind deferred endpoints (UI)
For each thread endpoint still `None`, choose the same-named instance whose `x` is nearest
the *other* endpoint's `x`. Needs step 2. Verified: `Stop request` from UI binds to **UI-L**
(|111−300|=189 ≪ |1402−300|), matching the reference. (Shortest distance only, per your
ruling; congestion weighting deferred.)

### 4. Global depth axis → y
Collect the depth of every Bead and every **bare-origin** thread (beaded-origin threads
inherit their source bead's depth, already in the set). Sort unique ascending → assign rows.

- **Compressed:** uniform row pitch = `standard bead height + min bead separation` (any two
  adjacent rows clear a bead; thin threads fit trivially). Per-string non-overlap then comes
  for free — consecutive beads on one string are separated by many global rows.
- **Absolute:** pitch ∝ Δdepth, floored at the compressed pitch.
- Top of axis sits below the rod by `string top gutter`; bottom adds `string bottom gutter`.
- Fill `Bead.compressed_depth`/`.absolute_depth`; `Bead.center = (string.x, y(depth))`.

### 5. Bead sizing
- **Rule:** width/height between `min bead size` and the material's `standard size`, grown to
  fit the state label.
- **v1:** `standard size` (50×25), or a char-count width estimate via the text seam. The long
  states (`WAITING FOR REQUESTS TO CLEAR`) prove real metrics are eventually required.

### 6. Knots & gaps
- **Source (R26):** a beaded-origin thread projects from the **lowest bead on its from-string
  at issue time** = `from_string.beads[-1]` when the command arrived. *This is population-time
  knowledge* (creation order, not recoverable from depths at the end) — so step #2/the facade
  should record `thread.source_bead` in `add_thread`. **Small facade addition flagged below.**
- **Target gap (slip knot):** the thread meets a beaded to-string in the *gap* bounded above
  by the deepest bead with `depth ≤ thread depth` (the "slip knot blocking bead", R11). If the
  natural y lands on a bead row, slip into the adjacent gap.
- **Fanning:** threads sharing one bead face spread via `fixed_knot` (+1/−1/…), per the doc's
  two-threads-from-one-bead case.
- **Bounded ends:** place the `top_end`/`bottom_end` knot symbols at `y_top` and (after
  `end_string`) `y_bottom`.

### 7. Thread color match (R23 / String Color)
`thread.color` = the color of a String-Colored endpoint it touches at **either** end. If both
ends are colored, **source (from) wins** (the emanate-only fallback). Must run after step 3
so UI is bound. Reference: UI threads lime, TRANS aqua, SIO magenta.

### 8. Canvas frame
From the string x-extent and depth y-extent: `rod_height` = strings' `y_top`; `size` = content
bbox + `Canvas.padding` (dark = top150/bottom100/left25/right25); `origin` = lower-left.

## Cross-cutting

**Coordinate flip.** Internally I'd compute depth growing downward from the rod, then convert
to Tablet's y-up once, at the boundary into step #4's `y(depth)` (or a single final transform).
One conversion point, clearly owned, per the Tablet contract.

**Text measurement seam.** Steps 2 and 5 need string widths. Propose a single
`measure_text(text, asset) -> width` interface: v1 = rough char-width estimate; v2 = backed by
Tablet's real font metrics. **Open: does Tablet expose a measurement call, or do we estimate?**
(Already on the open-items list alongside confirming `Symbol` names and the `_centered_pin`
recipe.)

## Decisions / open questions for Leon

1. **v1 spacing from minimums** (topologically correct, not text-tight) vs. invest in text
   measurement now to match the reference pixel gaps. I lean minimums-first.
2. **`thread.source_bead` recorded at population time** — agree to a small `add_thread`
   addition (`from_string.beads[-1]` for a beaded, bound origin)? It's genuinely issue-time
   knowledge.
3. **`Thread.Height` attribute** — model has it but its meaning is unclear to me. The thread's
   y-level? Its arrowhead clearance? What did you intend?
4. **Module shape** — one `layout.py` orchestrator calling the eight sub-passes as functions,
   each taking/mutating the `CurtainDiagram`? Or a `Layout` class holding scratch state (the
   sorted depth rows, the position partition)? I lean a `Layout` class — the depth-axis map and
   span table are shared scratch several passes read.
5. **Build order** — top-to-bottom (positions → x → … → frame), or vertical-axis-first since
   it's the conceptual core and the easiest to unit-test against bead depths?
