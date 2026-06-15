"""Measurement seam -- the single place Sequins asks TabletSVG how big notation is.

The layout pass needs real string widths to size beads to their labels (#5), to widen
inter-String spans so beads and message labels don't collide (#2), and the vertical extent
of knot symbols to place them clear of beads (#6/#8).  TabletSVG already owns the font
metrics (Pillow-backed via ``TextElement.text_block_size``, with a 0.6x char-width fallback
when a typeface isn't configured) and the symbol geometry; this wraps both behind a small
interface keyed on Sequins' notation names so the rest of the engine never touches Tablet
internals.

A ``TextMeasure`` is built once per layout pass from the active Diagram Theme: the Tablet
*drawing type* is the Curtain Style name, and the *presentation* mirrors the Canvas
(``dark`` -> ``dark``, ``light`` -> ``default``) -- the same pairing ``render`` feeds the
Tablet, so measured sizes match what is actually drawn.
"""
from __future__ import annotations

from tabletsvg.graphics.symbol import Symbol
from tabletsvg.graphics.text_element import TextElement
from tabletsvg.presentation import Presentation
from tabletsvg.styledb import StyleDB

from sequins.geometry import Distance, RectSize
from sequins.theme import Canvas, DiagramTheme

#: Sequins Canvas name -> Tablet presentation (kept in step with ``render._PRESENTATION``).
_PRESENTATION = {"light": "default", "dark": "dark"}


def presentation_name(canvas: Canvas) -> str:
    """The Tablet presentation a Canvas renders under."""
    return _PRESENTATION.get(canvas.name, "default")


def symbol_top_extent(drawing_type: str, name: str) -> Distance:
    """How far a symbol's geometry reaches *above* its (bottom-center) pin, in tablet units.

    A symbol pins by its bottom center and its component vertices are offsets from that pin
    (y up); this returns the largest such y so the layout pass can leave room for a knot
    (e.g. keep the ``create delete`` burst's top clear of the deepest bead)."""
    Symbol.load_symbol_defs()  # idempotent; also done when a Tablet is built
    components = Symbol.symbol_defs[drawing_type][name]
    tops: list[float] = []
    for cdef in components.values():
        kind, shape = next(iter(cdef.items()))
        if kind in ("polyline", "polygon"):
            tops += [vertex[1] for vertex in shape]
        elif kind == "circle":
            tops.append(shape["center"][1] + shape["radius"])
    return max(tops, default=0.0)


class TextMeasure:
    """Measures text in a Theme's presentation, so layout can size to real labels."""

    def __init__(self, drawing_type: str, presentation: str):
        StyleDB.load_config_files()  # idempotent; also done when a Tablet is built
        self._presentation = Presentation(name=presentation, drawing_type=drawing_type)

    @classmethod
    def for_theme(cls, theme: DiagramTheme) -> "TextMeasure":
        return cls(theme.curtain_style.name, presentation_name(theme.canvas))

    def block_size(self, asset: str, lines: list[str]) -> RectSize:
        """The rendered size of a multi-line text block in the asset's style."""
        size = TextElement.text_block_size(self._presentation, asset, list(lines))
        return RectSize(width=size.width, height=size.height)

    def line_width(self, asset: str, line: str) -> Distance:
        """The rendered width of a single line in the asset's style."""
        return self.block_size(asset, [line]).width

    def wrap(self, asset: str, text: str, max_width: Distance) -> list[str]:
        """Greedily word-wrap ``text`` so every line fits ``max_width`` in the asset's style.

        Splits on whitespace; a single word wider than ``max_width`` is left on its own
        (overflowing) line rather than broken mid-word. Always returns at least one line."""
        words = text.split()
        if not words:
            return [text]
        lines: list[str] = []
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if self.line_width(asset, trial) <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines
