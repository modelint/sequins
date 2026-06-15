"""Render a resolved Curtain Diagram to SVG via TabletSVG.

Draws lifelines, state beads (rectangle + name), thread lines + message labels, with
String Color / thread color match on the lines (#7), plus target arrowheads and
bounded-string birth/death knots (#6). Thread endpoints already carry the fanning offset
and slip-knot placement resolved by the layout pass, so this just follows the points.

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
from tabletsvg.graphics.symbol import Symbol
from tabletsvg.graphics.text_element import TextBlockCorner, TextElement
from tabletsvg.tablet import Tablet

from sequins.curtain import CurtainDiagram

DRAWING_TYPE = "Starr sequence diagram"

#: Sequins Canvas name -> Tablet presentation
_PRESENTATION = {"light": "default", "dark": "dark"}
#: Sequins Thread material name -> Tablet line asset
_THREAD_LINE_ASSET = {"signal": "signal", "implicit event": "implicit ext event"}
#: Arrowhead angle by travel direction (keyed on "to the right"). The `target lifeline`
#: glyph has its tip at the bottom -- its natural orientation points *down*, so it reads
#: 180deg off the usual 0=up/90=right convention: 270 points it right, 90 points it left.
_ARROW_ANGLE = {True: 270, False: 90}


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
    _draw_arrowheads(layer, diagram)
    _draw_end_knots(layer, diagram)

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
            # Center the wrapped label (the layout pass split it to fit) in the bead: pin
            # the block's lower-left so its measured box is centered on the bead center.
            lines = bead.lines or [bead.color_name]
            block = TextElement.text_block_size(layer.Presentation, "state name", lines)
            TextElement.pin_block(
                layer,
                asset="state name",
                text=lines,
                pin=Position(
                    x=bead.center.x - block.width / 2,
                    y=bead.center.y - block.height / 2,
                ),
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


def _draw_arrowheads(layer, diagram: CurtainDiagram) -> None:
    """Tip an arrowhead (`target lifeline`) into each thread's target String.

    The arrow points in the direction of travel (from -> to) and matches the thread color.
    v1 lands it on the target String's x at the thread y; slip-knot target gaps (R11) and
    fanning (`fixed_knot`) -- which nudge that landing off a bead row -- are deferred."""
    for thread in diagram.threads:
        going_right = thread.to_point.x >= thread.from_point.x
        Symbol(
            layer,
            name="target lifeline",
            pin=Position(x=thread.to_point.x, y=thread.to_point.y),
            angle=_ARROW_ANGLE[going_right],
            color_override=thread.color,
        )


def _draw_end_knots(layer, diagram: CurtainDiagram) -> None:
    """Knot the ends of bounded Strings (the create/delete burst).

    The birth knot caps the top of every bounded String; the death knot caps the bottom
    only once ``End_string`` has marked the String dead. Each end's symbol is named by the
    material (``top_end``/``bottom_end``)."""
    for string in diagram.strings:
        if not string.bounded:
            continue
        knot_color = string.override_color or string.color
        if string.material.top_end:
            Symbol(
                layer,
                name=string.material.top_end,
                pin=Position(x=string.x, y=string.y_top),
                color_override=knot_color,
            )
        if string.lower_bounded and string.material.bottom_end:
            Symbol(
                layer,
                name=string.material.bottom_end,
                pin=Position(x=string.x, y=string.y_bottom),
                color_override=knot_color,
            )
