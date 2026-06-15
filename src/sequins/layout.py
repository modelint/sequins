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
from sequins.text import TextMeasure, symbol_top_extent

#: Fixed (non-configurable) gaps for bounded-String knots, in points.
_KNOT_GAP = 2.0           # between a bounded String's line end and its knot burst
_BIRTH_THREAD_DROP = 4.0  # the birth thread touches this far below the line's beginning

#: Message-label placement, shared with ``render`` so reserved space matches what's drawn.
LABEL_TARGET_GAP = 30.0     # gap between the destination String and the label's near edge
LABEL_LINE_CLEARANCE = 4.0  # a label rides this far above its thread line


class Layout:
    """Resolves one Curtain Diagram's geometry."""

    def __init__(self, diagram: CurtainDiagram):
        self.diagram = diagram
        #: text metrics in the diagram's presentation (sizes beads, widens spans)
        self._measure = TextMeasure.for_theme(diagram.theme)
        #: raw chronological depth -> distance downward from the top of the axis (compressed)
        self._compressed: dict[float, Distance] = {}
        #: Strings in left-to-right (OR2 position) order
        self._ordered: list[String] = []
        #: uniform bead width (label-driven), for spans/insets/frame
        self._bead_width: Distance = 0.0
        #: uniform inter-String span (label-driven), set in #2
        self._span: Distance = 0.0

    def resolve(self) -> CurtainDiagram:
        """Run every implemented sub-pass, in dependency order."""
        self._size_beads()          # #5 first -- bead sizes feed the axis (#4) and spans (#2)
        self._build_depth_axis()    # #4
        self._assign_positions()    # #1
        self._bind_endpoints()      # #3 -- before #2 so span crossing is known
        self._assign_x()            # #2 -- uniform, label-driven
        self._match_thread_colors()  # #7
        self._frame_and_place()     # #8
        self._fan_source_knots()    # #6
        self._slip_knot_gaps()      # #6
        return self.diagram

    # ---------------------------------------------------------------- depth axis (#4)
    def _build_depth_axis(self) -> None:
        """Map the global chronological depth axis to compressed row distances.

        Every Bead and every bare-origin Thread contributes a depth (beaded-origin Threads
        ride their source bead's depth, already present); equal depths on different Strings
        share a row, so they align. Rows are stacked downward with a per-gap spacing rather
        than a single pitch:

        - **Beads clear each other.** The gap between two adjacent rows is at least
          ``half the taller bead above + min bead separation + half the taller bead below``,
          so consecutive Beads on any one String keep their separation even when a row carries
          a tall (wrapped, multi-line) Bead -- a uniform pitch sized for standard Beads would
          let two stacked 2-line Beads collide.
        - **Labels fit (compressed mode's first lever).** A Thread's message label rides in
          the gap *above* its row; the gap opens further if that label needs more height than
          the bead separation already provides. (Short labels fit the standard gap, so this
          only bites for tall/wrapped labels.)

        Bead sizes are set by now (#5), so real heights are available."""
        layout = self.diagram.theme.layout
        standard_height = max(
            m.standard_size.height for m in self.diagram.theme.curtain_style.bead_materials.values()
        )
        # Tallest Bead present at each depth (a thread-only depth falls back to standard).
        height_at: dict[float, Distance] = {}
        for string in self.diagram.strings:
            for bead in string.beads:
                height_at[bead.depth] = max(height_at.get(bead.depth, 0.0), bead.size.height)
        # Vertical room the deepest-at-a-row Thread labels need above their line.
        label_need_at: dict[float, Distance] = defaultdict(float)
        for thread in self.diagram.threads:
            need = LABEL_LINE_CLEARANCE + self._measure.block_size("message", [thread.label]).height
            label_need_at[self._thread_depth(thread)] = max(
                label_need_at[self._thread_depth(thread)], need
            )

        depths = sorted(self._depth_events())
        self._compressed = {}
        cursor: Distance = 0.0
        prev: float | None = None
        for depth in depths:
            if prev is not None:
                h_above = height_at.get(prev, standard_height)
                h_below = height_at.get(depth, standard_height)
                separation = max(layout.min_bead_separation, label_need_at.get(depth, 0.0))
                cursor += h_above / 2 + separation + h_below / 2
            self._compressed[depth] = cursor
            prev = depth

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
        """Place Strings at a single uniform span, widened so labels clear their source Bead.

        Spacing is the same between every adjacent String (the horizontal lever is global, so
        the diagram stays evenly ruled). The span clears adjacent beads and is grown so that
        *every* message label -- anchored ``LABEL_TARGET_GAP`` off its destination and running
        back toward the source -- clears the source Bead it springs from. A Thread spanning
        ``g`` gaps has ``g`` spans of room, so its requirement is ``(gap + label +
        half source bead) / g``; the binding case is a long label across a single gap. (This
        is the fallback lever: vertical opening (#4) handles labels squeezed between stacked
        beads; widening Strings handles labels too wide to clear a neighbouring bead.) The
        first String is inset half a bead so beads don't bleed into the canvas padding.

        Threads are bound by now (#3), so each carries its resolved endpoints."""
        layout = self.diagram.theme.layout
        pos_of = {id(s): i for i, s in enumerate(self._ordered)}

        span = max(layout.min_string_span, self._bead_width + layout.min_thread_separation)
        for thread in self.diagram.threads:
            gaps_crossed = abs(pos_of[id(thread.from_string)] - pos_of[id(thread.to_string)])
            if gaps_crossed == 0:
                continue
            label_width = self._measure.line_width("message", thread.label)
            source_half = thread.source_bead.size.width / 2 if thread.source_bead else 0.0
            span = max(span, (LABEL_TARGET_GAP + label_width + source_half) / gaps_crossed)
        self._span = span

        x = self.diagram.theme.canvas.padding.left + self._bead_width / 2
        for index, string in enumerate(self._ordered):
            string.x = x + index * span

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
                self._place_bounded_ends(string)
            else:
                # A persistent String hangs the full curtain, rod to interior bottom.
                string.y_top = rod_y
                string.y_bottom = interior_bottom_y

    def _place_bounded_ends(self, string: String) -> None:
        """Place a born-and-die String's line ends and its birth/death knot pins.

        Beads and thread endpoints are placed by now, so this works in y-up space.

        **Top (birth).** If the String is born by an incoming Thread (the shallowest event),
        the line begins ``_BIRTH_THREAD_DROP`` above where that Thread touches -- so the
        Thread lands just inside the live line -- and the birth burst's bottom sits
        ``_KNOT_GAP`` above the line's beginning. Otherwise the line begins at the shallowest
        event.

        **Bottom (death).** While alive, the line stops at the deepest event. Once
        ``End_string`` caps it, the death burst hangs below the deepest Bead with its *top* a
        compressed bead gap (``min bead separation``) clear of that Bead; the line then
        terminates ``_KNOT_GAP`` above the burst top (it no longer runs through the burst)."""
        threads = self.diagram.threads
        bead_ys = [b.center.y for b in string.beads]
        incoming_ys = [t.to_point.y for t in threads if t.to_string is string]
        touch_ys = bead_ys + incoming_ys + [t.from_point.y for t in threads if t.from_string is string]

        # --- top / birth ---
        shallowest_bead_y = max(bead_ys, default=float("-inf"))
        birth_y = max(incoming_ys, default=None)
        if birth_y is not None and birth_y >= shallowest_bead_y:
            string.y_top = birth_y + _BIRTH_THREAD_DROP  # line begins above the birth thread
        else:
            string.y_top = max(touch_ys)
        if string.material.top_end:
            string.top_knot_y = string.y_top + _KNOT_GAP  # burst bottom sits above the line

        # --- bottom / death ---
        layout = self.diagram.theme.layout
        if string.lower_bounded and string.material.bottom_end and string.beads:
            deepest = min(string.beads, key=lambda b: b.center.y)
            bead_bottom = deepest.center.y - deepest.size.height / 2
            burst_top = symbol_top_extent(self.diagram.theme.curtain_style.name, string.material.bottom_end)
            symbol_top_y = bead_bottom - layout.min_bead_separation  # a bead gap clear of the bead
            string.bottom_knot_y = symbol_top_y - burst_top
            string.y_bottom = symbol_top_y + _KNOT_GAP  # line terminates above the burst
        else:
            string.y_bottom = min(touch_ys)

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
