"""The runtime curtain metamodel -- the scenario content built by the layout-engine API.

This is the *content* side of ``sequins.xcm`` (Element and its String / Bead / Thread
subtypes, plus the Curtain Diagram that owns them).  Instances here are created by the
``Add_*`` commands and remain mutable: nothing is placed until ``End_diagram``, so the
layout pass is free to fill in the computed fields (positions, depths, sizes, knots).

Relational-to-OO notes worth keeping in mind:

* Surrogate ``Element ID`` keys are gone -- objects reference each other directly.
* OR2 (String Position) and OR17 (Bead Sequence) are ordering, captured as list index
  rather than stored numbers.
* The Beaded/Bare (R3) and Bounded/Unbounded (R20) splits are predicates off the
  material, so String stays a single class.
* The Thread-from-Bead / from-Bare-String lattice (R8/R9/R10/R26) is left as computed
  geometry on Thread rather than a subclass tree; the knot/gap fields are filled by the
  layout pass.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sequins.geometry import Coordinate, Distance, Position, RectSize
from sequins.theme import (
    BeadMaterial,
    ColorName,
    DiagramTheme,
    StringMaterial,
    StringPosition,
    ThreadMaterial,
)


@dataclass(kw_only=True)
class Element:
    """Root of the curtain metamodel (model: Element, R13).

    Relationally, Element exists mostly to host the surrogate ``Element ID`` and the
    common ``Override color``; we keep only the override here and let object identity do
    the rest.
    """

    override_color: ColorName | None = None


@dataclass(kw_only=True)
class Bead(Element):
    """A state adornment on a Beaded String (model: Bead, R5/R14)."""

    string: "String"
    color_name: str  # model: Bead Color Name (R14); the Bead Color is reference data
    material: BeadMaterial
    depth: Distance  # the depth supplied to Add_bead; the global chronological axis

    # --- filled by the layout pass ---
    compressed_depth: Distance | None = None
    absolute_depth: Distance | None = None
    center: Position | None = None
    size: RectSize | None = None

    @property
    def sequence(self) -> int:
        """OR17 ordering within the String -- derived, not stored."""
        return self.string.beads.index(self)


@dataclass(kw_only=True)
class String(Element):
    """A vertical lifeline hung from the rod (model: String, R1/R3).

    A String at multiple theme positions (e.g. UI at both L and R) is represented by one
    String instance per position, so ``name`` is not unique on its own -- (name, position)
    is.  ``beaded``/``bounded`` read straight off the material.
    """

    name: str
    material: StringMaterial
    color: ColorName | None = None  # resolved from the theme's String Color, if any
    pinned: StringPosition | None = None  # theme edge-pin (L/R + offset); None == interior
    beads: list[Bead] = field(default_factory=list)  # R5, ordered == OR17 Sequence

    # --- filled by the layout pass ---
    position: int | None = None  # OR2 left-to-right ordering
    x: Coordinate | None = None
    y_top: Coordinate | None = None
    y_bottom: Coordinate | None = None
    lower_bounded: bool = False  # set when End_string caps the bottom of a bounded String

    @property
    def beaded(self) -> bool:
        return self.material.beaded

    @property
    def bounded(self) -> bool:
        return self.material.bounded

    @property
    def lowest_bead(self) -> Bead | None:
        """The deepest bead currently on the String (by depth), or None."""
        return max(self.beads, key=lambda b: b.depth, default=None)


@dataclass(kw_only=True)
class Thread(Element):
    """A horizontal interaction between two Strings (model: Thread, R7).

    Whether this is a Thread *from a Bead* (origin is beaded -> projects from a bead face,
    R26) or *from a Bare String* (origin carries no beads -> needs an explicit depth) is a
    predicate over the resolved endpoints, computed at layout time, not a subclass.

    Endpoints are requested by *name* (``from_name``/``to_name``).  A name that resolves to
    a single String is bound immediately; a multi-position external (e.g. UI at L and R)
    stays unbound until the layout pass picks the nearer instance by distance -- the lazy
    resolution the spec calls for.
    """

    from_name: str
    to_name: str
    material: ThreadMaterial
    label: str  # opaque text, never parsed by the engine
    depth: Distance | None = None  # required only when the origin is a Bare String
    from_string: String | None = None  # bound now if unique, else at layout
    to_string: String | None = None

    # source_bead is recorded at population (issue time): the lowest bead on a beaded
    # origin when the thread was added (R26). The rest are filled by the layout pass.
    source_bead: Bead | None = None
    color: ColorName | None = None  # matches a String-Colored endpoint, if any
    height: Distance | None = None  # the thread's y-level on the curtain
    fixed_knot: int = 0  # offset for fanning multiple threads off one bead face

    @property
    def from_bead(self) -> bool:
        """True when this Thread emanates from a bead rather than a bare string.

        Requires the source endpoint to be bound (always true for a beaded origin, which
        is unique; bare multi-position origins bind during the layout pass)."""
        if self.from_string is None:
            raise ValueError(f"Thread source {self.from_name!r} not yet bound")
        return self.from_string.beaded


@dataclass(kw_only=True)
class CurtainDiagram:
    """The aggregate root for one diagram (model: Curtain Diagram, R15/R22).

    Owns the ordered Strings (position == index) and the Threads, references the resolved
    Diagram Theme, and holds the canvas-level results computed at End_diagram.
    """

    theme: DiagramTheme
    compressed: bool = True
    strings: list[String] = field(default_factory=list)
    threads: list[Thread] = field(default_factory=list)

    # --- filled by the layout pass ---
    origin: Position | None = None
    size: RectSize | None = None
    rod_height: Distance | None = None

    def strings_named(self, name: str) -> list[String]:
        """All String instances sharing a name (one per theme position)."""
        return [s for s in self.strings if s.name == name]
