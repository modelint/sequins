"""Render a resolved Curtain Diagram to SVG via TabletSVG.

Minimal v1: lifelines, state beads (rectangle + name), and thread lines + message labels,
with String Color / thread color match applied to the lines (#7). Adornments handled by
later sub-passes -- arrowheads (`target lifeline`) and bounded-string end knots
(`create delete`) -- are not drawn yet.

Sequins works entirely in Tablet's y-up, lower-left-origin coordinates (the layout pass
already owns the one depth->y flip), so positions pass straight through; Tablet handles the
device conversion. Asset names are the notation names in the user's ``mi_tablet`` config
("Starr sequence diagram" drawing type, `default`/`dark` presentations).
"""
from __future__ import annotations

from pathlib import Path

from tabletsvg.geometry_types import HorizAlign, Position, Rect_Size
from tabletsvg.graphics.line_segment import LineSegment
from tabletsvg.graphics.rectangle_se import RectangleSE
from tabletsvg.graphics.text_element import TextBlockCorner, TextElement
from tabletsvg.tablet import Tablet

from sequins.curtain import CurtainDiagram

DRAWING_TYPE = "Starr sequence diagram"

#: Sequins Canvas name -> Tablet presentation
_PRESENTATION = {"light": "default", "dark": "dark"}
#: Sequins Thread material name -> Tablet line asset
_THREAD_LINE_ASSET = {"signal": "signal", "implicit event": "implicit ext event"}


def render(diagram: CurtainDiagram, output_file: str | Path) -> Path:
    """Draw a resolved diagram to ``output_file`` (format from the suffix); returns the path."""
    canvas = diagram.theme.canvas
    tablet = Tablet(
        size=Rect_Size(height=diagram.size.height, width=diagram.size.width),
        output_file=Path(output_file),
        drawing_type=DRAWING_TYPE,
        presentation=_PRESENTATION.get(canvas.name, "default"),
        layer="diagram",
        background_color=canvas.background_color,
    )
    layer = tablet.layers["diagram"]

    _draw_strings(layer, diagram)
    _draw_beads(layer, diagram)
    _draw_threads(layer, diagram)

    tablet.render()
    return Path(output_file)


def _draw_strings(layer, diagram: CurtainDiagram) -> None:
    for string in diagram.strings:
        LineSegment.add(
            layer,
            asset="lifeline",
            from_here=Position(x=string.x, y=string.y_bottom),
            to_there=Position(x=string.x, y=string.y_top),
            color_override=string.override_color or string.color,
        )
        # Name each lifeline at the rod, above the curtain.
        TextElement.pin_block(
            layer,
            asset="lifeline name",
            text=[string.name],
            pin=Position(x=string.x, y=diagram.rod_height + 8),
            corner=TextBlockCorner.LL,
            align=HorizAlign.CENTER,
        )


def _draw_beads(layer, diagram: CurtainDiagram) -> None:
    for string in diagram.strings:
        for bead in string.beads:
            size = Rect_Size(height=bead.size.height, width=bead.size.width)
            lower_left = Position(
                x=bead.center.x - bead.size.width / 2,
                y=bead.center.y - bead.size.height / 2,
            )
            RectangleSE.add(layer, asset="state", lower_left=lower_left, size=size)
            TextElement.pin_block(
                layer,
                asset="state name",
                text=[bead.color_name],
                pin=Position(x=bead.center.x, y=bead.center.y),
                corner=TextBlockCorner.LL,
                align=HorizAlign.CENTER,
            )


def _draw_threads(layer, diagram: CurtainDiagram) -> None:
    for thread in diagram.threads:
        LineSegment.add(
            layer,
            asset=_THREAD_LINE_ASSET[thread.material.name],
            from_here=Position(x=thread.from_point.x, y=thread.from_point.y),
            to_there=Position(x=thread.to_point.x, y=thread.to_point.y),
            color_override=thread.color,
        )
        midpoint = Position(
            x=(thread.from_point.x + thread.to_point.x) / 2,
            y=thread.from_point.y + 4,
        )
        TextElement.pin_block(
            layer,
            asset="message",
            text=[thread.label],
            pin=midpoint,
            corner=TextBlockCorner.LL,
            align=HorizAlign.CENTER,
        )
