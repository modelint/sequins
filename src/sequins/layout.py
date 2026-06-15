"""The layout pass -- resolves a populated Curtain Diagram into geometry.

Built incrementally (see ``documentation/architecture/layout_pass_design.md``), vertical
axis first.  A ``Layout`` instance owns the scratch tables (the depth-row map, the uniform
bead width) that several sub-passes read, and a ``TextMeasure`` for real label metrics, and
mutates the diagram in place.

The full pipeline (#1-#8) is implemented in *compressed* depth mode, including label-driven
bead sizing/wrapping (#5) and content-driven spans (#2). Absolute depth mode is deferred --
its spacing must distinguish near-instant compute-time steps (the ``.001`` increments) from
real elapsed time (the integer jumps), which needs its own design.
"""
from __future__ import annotations

from collections import defaultdict

from sequins.curtain import Bead, CurtainDiagram, String, Thread
from sequins.geometry import Distance, Position, RectSize
from sequins.text import TextMeasure


class Layout:
    """Resolves one Curtain Diagram's geometry."""

    def __init__(self, diagram: CurtainDiagram):
        self.diagram = diagram
        #: text metrics in the diagram's presentation (sizes beads, widens spans)
        self._measure = TextMeasure.for_theme(diagram.theme)
        #: raw chronological depth -> distance downward from the top of the axis (compressed)
        self._compressed: dict[float, Distance] = {}
        #: uniform row pitch in compressed mode
        self._pitch: Distance = 0.0
        #: Strings in left-to-right (OR2 position) order
        self._ordered: list[String] = []
        #: uniform bead width (label-driven), for spans/insets/frame
        self._bead_width: Distance = 0.0

    def resolve(self) -> CurtainDiagram:
        """Run every implemented sub-pass, in dependency order."""
        self._build_depth_axis()    # #4
        self._size_beads()          # #5 -- sets the uniform bead width #2/#8 rely on
        self._assign_positions()    # #1
        self._bind_endpoints()      # #3 -- before #2 so span crossing is known
        self._assign_x()            # #2 -- per-gap, label-driven
        self._match_thread_colors()  # #7
        self._frame_and_place()     # #8
        self._fan_source_knots()    # #6
        self._slip_knot_gaps()      # #6
        return self.diagram

    # ---------------------------------------------------------------- depth axis (#4)
    def _build_depth_axis(self) -> None:
        """Map the global chronological depth axis to compressed row distances.

        Every Bead and every bare-origin Thread contributes a depth (beaded-origin Threads
        ride their source bead's depth, already present).  Distinct depths become evenly
        spaced rows; equal depths on different Strings share a row, so they align."""
        layout = self.diagram.theme.layout
        bead_materials = self.diagram.theme.curtain_style.bead_materials.values()
        tallest_bead = max(m.standard_size.height for m in bead_materials)
        # A row pitch that clears a standard bead guarantees per-String non-overlap, since
        # consecutive beads on any one String are separated by >= one global row.
        self._pitch = tallest_bead + layout.min_bead_separation

        depths = sorted(self._depth_events())
        self._compressed = {depth: rank * self._pitch for rank, depth in enumerate(depths)}

        for string in self.diagram.strings:
            for bead in string.beads:
                bead.compressed_depth = self._compressed[bead.depth]

        for thread in self.diagram.threads:
            thread.height = self.compressed_level(self._thread_depth(thread))

    def compressed_level(self, depth: float) -> Distance:
        """The compressed distance (downward from the axis top) for a raw depth."""
        return self._compressed[depth]

    # ------------------------------------------------------------ string order (#1)
    def _assign_positions(self) -> None:
        """Order Strings left-to-right (OR2): left-pinned, interior, right-pinned.

        Left pins sort by ascending offset (0 = left edge); right pins by descending
        offset (0 = right edge, larger = further inward); interiors keep creation order."""
        strings = self.diagram.strings
        left = sorted(
            (s for s in strings if s.pinned and s.pinned.boundary == "L"),
            key=lambda s: s.pinned.offset,
        )
        right = sorted(
            (s for s in strings if s.pinned and s.pinned.boundary == "R"),
            key=lambda s: -s.pinned.offset,
        )
        interior = [s for s in strings if s.pinned is None]  # creation order preserved

        self._ordered = [*left, *interior, *right]
        for index, string in enumerate(self._ordered, start=1):
            string.position = index

    # ------------------------------------------------------------ string x (#2)
    def _assign_x(self) -> None:
        """Place Strings at per-gap x spans driven by content.

        Each gap is widened to clear the (uniform) beads on its bounding Strings and to fit
        the longest message label of any Thread crossing it, never below ``min string span``.
        Threads are bound by now (#3), so each gap knows exactly which labels cross it. The
        first String is inset by half a bead so beads don't bleed into the canvas padding."""
        layout = self.diagram.theme.layout
        margin = layout.min_thread_separation
        bead_floor = self._bead_width + margin  # adjacent beads (centered) clear each other
        pos_of = {id(s): i for i, s in enumerate(self._ordered)}

        # Longest message label crossing each gap k (between ordered[k] and ordered[k+1]).
        gaps = max(len(self._ordered) - 1, 0)
        longest_label = [0.0] * gaps
        for thread in self.diagram.threads:
            lo, hi = sorted((pos_of[id(thread.from_string)], pos_of[id(thread.to_string)]))
            if lo == hi:
                continue
            width = self._measure.line_width("message", thread.label)
            for k in range(lo, hi):
                longest_label[k] = max(longest_label[k], width)

        x = self.diagram.theme.canvas.padding.left + self._bead_width / 2
        self._ordered[0].x = x
        for k in range(gaps):
            span = max(layout.min_string_span, bead_floor, longest_label[k] + 2 * margin)
            x += span
            self._ordered[k + 1].x = x

    # ------------------------------------------------------------ bind endpoints (#3)
    def _bind_endpoints(self) -> None:
        """Bind multi-position endpoints (e.g. UI) left unbound during population.

        Pick the same-named instance whose OR2 position is nearest the other endpoint's
        position. Position stands in for x here (x isn't assigned until #2, which needs the
        bound endpoints to know which labels cross each gap) -- and since x increases
        monotonically with position, nearest-by-position is the same choice as nearest-by-x.
        On a tie the first by position wins."""
        for thread in self.diagram.threads:
            if thread.from_string is None:
                thread.from_string = self._nearest(thread.from_name, thread.to_string)
            if thread.to_string is None:
                thread.to_string = self._nearest(thread.to_name, thread.from_string)

    def _nearest(self, name: str, other: String | None) -> String:
        candidates = self.diagram.strings_named(name)
        if other is None or other.position is None:
            return candidates[0]
        return min(candidates, key=lambda c: abs(c.position - other.position))

    # ------------------------------------------------------ thread color match (#7)
    def _match_thread_colors(self) -> None:
        """Color each Thread to match a String-Colored endpoint.

        Endpoints are bound by now (#3). A Thread inherits the color of an endpoint that
        carries a String Color; a same-named bare endpoint (no color) contributes none.
        Precedence: an explicit ``Override color`` on the Thread wins; otherwise the source
        (``from``) String's color, then the target (``to``) String's. Absent all three the
        color stays ``None`` and the Thread renders in the presentation default.

        The model doesn't yet formalize this match (Thread carries only Material); the rule
        follows the reference diagram, where Threads take their emanating String's color
        with the source winning ties."""
        for thread in self.diagram.threads:
            thread.color = (
                thread.override_color
                or (thread.from_string.color if thread.from_string else None)
                or (thread.to_string.color if thread.to_string else None)
            )

    # ------------------------------------------------------------ bead sizing (#5)
    def _size_beads(self) -> None:
        """Wrap each bead's label and size every bead to fit it.

        The label wraps onto as many lines as it takes for each line to fit the material's
        standard-size *width* (the wrap boundary); a bead then grows taller for the extra
        lines. Width is **uniform** across the diagram -- the widest wrapped line plus
        horizontal padding -- so bead edges line up like the reference. Sets the uniform
        width ``_assign_x`` and ``_frame_and_place`` read."""
        layout = self.diagram.theme.layout
        pad_h, pad_v = layout.bead_text_pad_h, layout.bead_text_pad_v
        beads = [b for s in self.diagram.strings for b in s.beads]

        blocks: dict[int, RectSize] = {}
        widest_line = 0.0
        for bead in beads:
            bead.lines = self._measure.wrap("state name", bead.color_name, bead.material.standard_size.width)
            blocks[id(bead)] = self._measure.block_size("state name", bead.lines)
            widest_line = max(widest_line, blocks[id(bead)].width)

        self._bead_width = max(layout.min_bead_size.width, widest_line + 2 * pad_h)
        for bead in beads:
            block = blocks[id(bead)]
            height = max(bead.material.standard_size.height, block.height + 2 * pad_v)
            bead.size = RectSize(width=self._bead_width, height=height)

    # ------------------------------------------------- centers, frame, y-flip (#8)
    def _frame_and_place(self) -> None:
        """Size the canvas and convert depth distances to Tablet (x, y-up) coordinates.

        This is the single point where the model's downward depth becomes Tablet's y-up
        space. The rod sits a top gutter above the depth axis; depth grows downward, so a
        deeper event maps to a smaller y. The interior bottom lands exactly on the bottom
        padding, so the frame closes consistently."""
        layout = self.diagram.theme.layout
        padding = self.diagram.theme.canvas.padding
        beads = [b for s in self.diagram.strings for b in s.beads]

        # Deepest occupied distance down the axis (beads and threads alike).
        max_depth = max(
            [b.compressed_depth for b in beads] + [t.height for t in self.diagram.threads],
            default=0.0,
        )
        half_bead = self._bead_width / 2
        rightmost = max(self.diagram.strings, key=lambda s: s.x)

        width = rightmost.x + half_bead + padding.right
        height = (
            padding.bottom
            + layout.string_top_gutter
            + max_depth
            + layout.string_bottom_gutter
            + padding.top
        )
        self.diagram.size = RectSize(width=width, height=height)
        self.diagram.origin = Position(x=0.0, y=0.0)  # canvas lower-left

        rod_y = height - padding.top
        self.diagram.rod_height = rod_y
        axis_top_y = rod_y - layout.string_top_gutter

        def y_at(distance: Distance) -> float:
            return axis_top_y - distance  # depth grows downward -> y decreases

        for bead in beads:
            bead.center = Position(x=bead.string.x, y=y_at(bead.compressed_depth))

        # v1: threads run horizontally at their depth level; #6 will offset for bead faces,
        # slip-knot gaps, and fanning.
        for thread in self.diagram.threads:
            thread_y = y_at(thread.height)
            thread.from_point = Position(x=thread.from_string.x, y=thread_y)
            thread.to_point = Position(x=thread.to_string.x, y=thread_y)

        interior_bottom_y = padding.bottom
        for string in self.diagram.strings:
            if string.bounded:
                # A born-and-die String floats between its shallowest and deepest events.
                events = [b.compressed_depth for b in string.beads]
                events += [
                    t.height
                    for t in self.diagram.threads
                    if t.from_string is string or t.to_string is string
                ]
                string.y_top = y_at(min(events))
                string.y_bottom = y_at(max(events))
            else:
                # A persistent String hangs the full curtain, rod to interior bottom.
                string.y_top = rod_y
                string.y_bottom = interior_bottom_y

    # ---------------------------------------------------- fanning / fixed knot (#6, R26)
    def _fan_source_knots(self) -> None:
        """Spread Threads that emanate from the same Bead face so they don't overlap.

        Per R26 / Fixed knot, Threads projecting from one Bead attach along that Bead's
        side; the default knot (0) is the face center. Threads sharing a side are fanned to
        symmetric integer notches centered on the face (n=2 -> -1,+1; n=3 -> -2,0,+2), each
        notch worth half a ``min thread separation`` so adjacent Threads clear that minimum.
        Each Thread shifts as a whole (both endpoints) to stay horizontal; a lone Thread
        keeps the center (knot 0, no offset)."""
        half_sep = self.diagram.theme.layout.min_thread_separation / 2
        groups: dict[tuple[int, str], list[Thread]] = defaultdict(list)
        for thread in self.diagram.threads:
            if thread.source_bead is not None:
                side = "R" if thread.to_string.x >= thread.from_string.x else "L"
                groups[(id(thread.source_bead), side)].append(thread)

        for threads in groups.values():
            n = len(threads)
            if n == 1:
                continue
            for i, thread in enumerate(threads):
                notch = 2 * i - (n - 1)  # symmetric integers: n=2 -> -1,+1; n=3 -> -2,0,+2
                thread.fixed_knot = notch
                dy = notch * half_sep
                thread.from_point = Position(x=thread.from_point.x, y=thread.from_point.y + dy)
                thread.to_point = Position(x=thread.to_point.x, y=thread.to_point.y + dy)

    # ------------------------------------------------------- slip knot gaps (#6, R11)
    def _slip_knot_gaps(self) -> None:
        """Record the Bead each Thread is slip-knotted *above* on a beaded target (R11).

        A Thread terminating on a beaded String connects in the gap above a designated Bead
        -- the nearest Bead below its landing (the deepest Bead whose center sits below the
        thread). It stays below the next-higher Bead. The compressed depth axis already keeps
        every thread one row above its target's response bead, so no y moves here in v1; this
        pins down the blocking Bead the model (Thread to Bead Gap) calls for. ``None`` means
        the thread lands above the topmost Bead (near a bounded String's top)."""
        for thread in self.diagram.threads:
            if not thread.to_string.beaded:
                continue
            y = thread.to_point.y
            below = [b for b in thread.to_string.beads if b.center.y < y]
            thread.blocking_bead = max(below, key=lambda b: b.center.y, default=None)

    def _depth_events(self) -> set[float]:
        bead_depths = {b.depth for s in self.diagram.strings for b in s.beads}
        bare_thread_depths = {t.depth for t in self.diagram.threads if t.depth is not None}
        return bead_depths | bare_thread_depths

    @staticmethod
    def _thread_depth(thread: Thread) -> float:
        """A thread's depth: its own (bare origin) or its projecting bead's (beaded)."""
        if thread.depth is not None:
            return thread.depth
        if thread.source_bead is not None:
            return thread.source_bead.depth
        raise ValueError(
            f"Thread {thread.label!r} from {thread.from_name!r} has neither a depth nor a "
            "source bead -- a beaded origin must carry a bead at issue time"
        )
