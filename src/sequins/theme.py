"""Presentation layer -- the immutable value objects loaded from configuration.

These mirror the *specification* side of ``sequins.xcm`` (Canvas, Layout, Curtain Style,
Material and its subtypes, Diagram Theme, and the per-String settings).  They carry no
behavior beyond lookup; they are loaded once from the four ``configuration/*.yaml`` files
(loading lives in a separate module so this stays free of YAML concerns) and then treated
as read-only reference data while a diagram is built.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from sequins.geometry import Distance, Padding, RectSize

ColorName = str
EndName = str


# --------------------------------------------------------------------------- materials
# R4 splits Material into Bead / String / Thread Material; R12 binds each to a Curtain
# Style.  Since exactly one Curtain Style is active per diagram, the (Name, Curtain style)
# identifier collapses to Name within a loaded CurtainStyle, so these need only carry Name.

@dataclass(frozen=True, slots=True)
class StringMaterial:
    """A String's material (model: String Material + R20 Bounded/Unbounded).

    ``beaded`` and ``bounded`` are the two predicates that, in the model, drive the R3 and
    R20 generalizations; here they are just attributes a String reads, so no subclassing.
    A bounded material names the knot styles to cap each end with.
    """

    name: str
    beaded: bool
    top_end: EndName | None = None
    bottom_end: EndName | None = None

    @property
    def bounded(self) -> bool:
        return self.top_end is not None or self.bottom_end is not None


@dataclass(frozen=True, slots=True)
class BeadMaterial:
    """A Bead's material (model: Bead Material) with its min and standard sizes."""

    name: str
    min_size: RectSize
    standard_size: RectSize


@dataclass(frozen=True, slots=True)
class ThreadMaterial:
    """A Thread's material (model: Thread Material).

    ``arrow_asset`` is the Tablet symbol notation drawn at the target end (e.g.
    ``target lifeline``).
    """

    name: str
    arrow_asset: str


Material = StringMaterial | BeadMaterial | ThreadMaterial


@dataclass(frozen=True, slots=True)
class CurtainStyle:
    """The notation vocabulary for one kind of diagram (model: Curtain Style, R12)."""

    name: str
    string_materials: Mapping[str, StringMaterial]
    bead_materials: Mapping[str, BeadMaterial]
    thread_materials: Mapping[str, ThreadMaterial]

    def string_material(self, name: str) -> StringMaterial:
        return self.string_materials[name]

    def bead_material(self, name: str) -> BeadMaterial:
        return self.bead_materials[name]

    def thread_material(self, name: str) -> ThreadMaterial:
        return self.thread_materials[name]


# ------------------------------------------------------------------------------ canvas
@dataclass(frozen=True, slots=True)
class Canvas:
    """The full rendered area and how the diagram is padded within it (model: Canvas)."""

    name: str
    background_color: ColorName
    padding: Padding


# ------------------------------------------------------------------------------ layout
@dataclass(frozen=True, slots=True)
class Layout:
    """Relative spacing minimums within a Curtain Diagram (model: Layout)."""

    name: str
    string_top_gutter: Distance
    string_bottom_gutter: Distance
    min_bead_separation: Distance
    min_string_span: Distance
    min_bead_size: RectSize
    min_thread_separation: Distance
    #: Space between a target String and the near edge of a thread's message label.
    target_string_label_gap: Distance
    #: Minimum gap between a bead edge and any thread label text.
    min_bead_edge_gap: Distance
    #: Padding between a bead's wrapped label and the bead edge (horizontal / vertical).
    bead_text_pad_h: Distance
    bead_text_pad_v: Distance


# ---------------------------------------------------------------------- string settings
# A Diagram Theme may carry per-String overrides.  The model spreads these across String
# Setting / String Color / String Appearance / String Position (keyed by String Name +
# theme + a Setting discriminator).  For a single loaded theme that whole structure
# collapses to: "for this String Name, what color and which positions?"

@dataclass(frozen=True, slots=True)
class StringPosition:
    """One placement of a String (model: String Position).

    ``boundary`` is 'L' or 'R' (model type ``L_R``); ``offset`` is the rank inward from
    that edge (model: Offset).  A name may resolve to several positions (e.g. UI at L and
    R), which is why a String Name is not unique on its own.
    """

    boundary: str
    offset: int = 0


@dataclass(frozen=True, slots=True)
class StringSetting:
    """The collapsed per-String presentation for one Diagram Theme (model: String Setting
    + String Color + String Appearance + String Position)."""

    name: str
    color: ColorName | None = None
    positions: tuple[StringPosition, ...] = ()


# ------------------------------------------------------------------------- diagram theme
@dataclass(frozen=True, slots=True)
class DiagramTheme:
    """A named bundle of Canvas + Layout + Curtain Style + per-String settings
    (model: Diagram Theme, R16/R18/R19)."""

    name: str
    canvas: Canvas
    layout: Layout
    curtain_style: CurtainStyle
    string_settings: Mapping[str, StringSetting]

    def setting_for(self, string_name: str) -> StringSetting | None:
        return self.string_settings.get(string_name)
