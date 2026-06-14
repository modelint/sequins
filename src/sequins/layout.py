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
from sequins.geometry import Distance


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

    def resolve(self) -> CurtainDiagram:
        """Run every implemented sub-pass, in dependency order."""
        self._build_depth_axis()
        self._assign_positions()
        self._assign_x()
        self._bind_endpoints()
        # TODO: bead sizing (#5), knots & gaps (#6), color match (#7), canvas frame (#8)
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
