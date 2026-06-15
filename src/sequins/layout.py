"""The layout pass -- resolves a populated Curtain Diagram into geometry.

Built incrementally (see ``documentation/architecture/layout_pass_design.md``), vertical
axis first.  A ``Layout`` instance owns the scratch tables (the depth-row map, later the
span table) that several sub-passes read, and mutates the diagram in place.

Implemented so far: the **depth axis** (sub-pass #4) in *compressed* mode.  Absolute mode
is deferred -- its spacing must distinguish near-instant compute-time steps (the ``.001``
increments) from real elapsed time (the integer jumps), which needs its own design.
"""
from __future__ import annotations

from sequins.curtain import CurtainDiagram, String, Thread
from sequins.geometry import Distance, Position, RectSize


class Layout:
    """Resolves one Curtain Diagram's geometry."""

    def __init__(self, diagram: CurtainDiagram):
        self.diagram = diagram
        #: raw chronological depth -> distance downward from the top of the axis (compressed)
        self._compressed: dict[float, Distance] = {}
        #: uniform row pitch in compressed mode
        self._pitch: Distance = 0.0
        #: Strings in left-to-right (OR2 position) order
        self._ordered: list[String] = []
        #: uniform inter-String span (v1)
        self._span: Distance = 0.0
        #: widest standard bead, for insets/frame
        self._widest_bead: Distance = 0.0

    def resolve(self) -> CurtainDiagram:
        """Run every implemented sub-pass, in dependency order."""
        self._build_depth_axis()
        self._assign_positions()
        self._assign_x()
        self._bind_endpoints()
        self._match_thread_colors()
        self._size_beads()
        self._frame_and_place()
        # TODO: knots & gaps (#6)
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
        """Place Strings at uniform x spans (v1).

        The span clears a standard bead between neighbours; text-tight, thread-label-driven
        spacing is deferred. The first String is inset by half a bead so beads don't bleed
        into the canvas padding."""
        layout = self.diagram.theme.layout
        bead_materials = self.diagram.theme.curtain_style.bead_materials.values()
        widest_bead = max(m.standard_size.width for m in bead_materials)
        self._span = max(layout.min_string_span, widest_bead + layout.min_thread_separation)
        self._widest_bead = widest_bead

        first_x = self.diagram.theme.canvas.padding.left + widest_bead / 2
        for index, string in enumerate(self._ordered):
            string.x = first_x + index * self._span

    # ------------------------------------------------------------ bind endpoints (#3)
    def _bind_endpoints(self) -> None:
        """Bind multi-position endpoints (e.g. UI) left unbound during population.

        Pick the same-named instance whose x is nearest the other endpoint's x. On a tie
        (uniform v1 spacing can produce exact ties) the first by position wins -- a real
        spacing model will break such ties naturally."""
        for thread in self.diagram.threads:
            if thread.from_string is None:
                thread.from_string = self._nearest(thread.from_name, thread.to_string)
            if thread.to_string is None:
                thread.to_string = self._nearest(thread.to_name, thread.from_string)

    def _nearest(self, name: str, other: String | None) -> String:
        candidates = self.diagram.strings_named(name)
        if other is None or other.x is None:
            return candidates[0]
        return min(candidates, key=lambda c: abs(c.x - other.x))

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
        """Size every bead to its material's standard size (v1).

        The minimums won't fit state labels; standard size does. Growing a bead to a long
        label needs text measurement and is deferred."""
        for string in self.diagram.strings:
            for bead in string.beads:
                bead.size = bead.material.standard_size

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
        half_bead = self._widest_bead / 2
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
