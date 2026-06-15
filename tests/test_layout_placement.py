"""Placement tests (layout sub-passes #5 bead sizing, #8 centers/frame/y-flip)."""
from __future__ import annotations

from elevator_script import populate

from sequins.layout_engine import LayoutEngine


def build():
    e = LayoutEngine()
    populate(e)
    e.end_diagram()
    return e.diagram


def test_beads_wrap_and_share_uniform_width():
    d = build()
    beads = [b for s in d.strings for b in s.beads]
    std = beads[0].material.standard_size

    # Width is uniform across the diagram (widest wrapped line + padding), never below standard.
    widths = {b.size.width for b in beads}
    assert len(widths) == 1
    assert widths.pop() >= std.width

    # A short single-word label stays one line at the standard height.
    opening = next(b for b in beads if b.color_name == "OPENING")
    assert opening.lines == ["OPENING"]
    assert opening.size.height == std.height

    # A label too wide for the bead wraps onto multiple lines and grows taller.
    waiting = next(b for b in beads if b.color_name == "WAITING FOR REQUESTS TO CLEAR")
    assert len(waiting.lines) > 1
    assert waiting.size.height > std.height


def test_canvas_frame():
    d = build()
    assert d.origin.x == 0.0 and d.origin.y == 0.0
    assert d.size.width > 0 and d.size.height > 0
    padding = d.theme.canvas.padding
    # Rod sits one top-padding below the canvas top.
    assert d.rod_height == d.size.height - padding.top
    # Interior closes on the bottom padding: the deepest bead lands a bottom gutter above it.
    deepest = min(b.center.y for s in d.strings for b in s.beads)
    assert deepest == padding.bottom + d.theme.layout.string_bottom_gutter


def test_depth_maps_to_descending_y():
    d = build()
    aslev = d.strings_named("ASLEV: S1-3")[0]
    top = next(b for b in aslev.beads if b.color_name == "NOT REQUESTED" and b.depth == 0.0)
    later = next(b for b in aslev.beads if b.color_name == "Registering stop")
    # Deeper depth -> lower on the canvas (smaller y).
    assert top.depth < later.depth
    assert top.center.y > later.center.y
    # The top bead (depth 0) sits a top gutter below the rod.
    assert top.center.y == d.rod_height - d.theme.layout.string_top_gutter
    # Bead x rides its string.
    assert top.center.x == aslev.x


def test_persistent_string_hangs_full_curtain():
    d = build()
    aslev = d.strings_named("ASLEV: S1-3")[0]
    assert not aslev.bounded
    assert aslev.y_top == d.rod_height
    assert aslev.y_bottom == d.theme.canvas.padding.bottom


def test_bounded_string_floats_between_birth_and_death():
    d = build()
    transfer = d.strings_named("Transfer: S1-3")[0]
    assert transfer.bounded
    # Floats below the rod and above the interior bottom.
    assert transfer.y_top < d.rod_height
    assert transfer.y_bottom > d.theme.canvas.padding.bottom
    # Born at its first incoming thread ('Execute'@1.003), not at the rod.
    assert transfer.y_top > transfer.y_bottom
