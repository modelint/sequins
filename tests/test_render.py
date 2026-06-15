"""Render smoke test: the full pipeline emits a structurally complete SVG.

Integration-level -- exercises the real TabletSVG and the user's ``mi_tablet`` config.
"""
from __future__ import annotations

from elevator_script import populate

from sequins.layout_engine import LayoutEngine
from sequins.render import render


def test_render_elevator_svg(tmp_path):
    e = LayoutEngine()
    populate(e)
    diagram = e.end_diagram()

    out = render(diagram, tmp_path / "elevator.svg")
    assert out.exists()

    svg = out.read_text()
    assert "<svg" in svg
    # 9 lifelines + 28 threads.
    assert svg.count("<line") == 37
    # 36 beads + the background rectangle.
    assert svg.count("<rect") == 37
    # 9 lifeline names + 28 message labels + state-name lines: 36 beads, 4 of which carry
    # a label too wide for the bead and wrap onto a second line (#5) -> 40 state-name lines.
    assert svg.count("<text") == 77


def test_string_colors_reach_the_svg(tmp_path):
    # Thread color match (#7): the elevator theme's String Colors resolve onto the lines.
    e = LayoutEngine()
    populate(e)
    out = render(e.end_diagram(), tmp_path / "elevator.svg")
    svg = out.read_text()
    assert "rgb(142,250,0)" in svg  # lime  (UI)
    assert "rgb(66,148,247)" in svg  # aqua  (TRANS)
    assert "rgb(255,64,255)" in svg  # magenta (SIO)


def test_knots_and_arrowheads_drawn(tmp_path):
    # #6: a target arrowhead per thread, plus birth+death knots on the one bounded String.
    e = LayoutEngine()
    populate(e)
    out = render(e.end_diagram(), tmp_path / "elevator.svg")
    svg = out.read_text()
    # 28 arrowhead polylines + 2 knots x 6 spokes = 40 polylines.
    assert svg.count("<polyline") == 40
    # Transfer is born and dies (End_string'd) -> 2 create/delete bursts -> 2 center dots.
    assert svg.count("<circle") == 2


def test_arrowhead_leaves_a_gap_to_the_target_string():
    # The arrow tip (and thread line end) stop short of the lifeline by _ARROW_TARGET_GAP.
    from sequins.render import _ARROW_TARGET_GAP, _arrow_tip

    e = LayoutEngine()
    populate(e)
    d = e.end_diagram()
    for t in d.threads:
        tip = _arrow_tip(t)
        assert abs(t.to_string.x - tip.x) == _ARROW_TARGET_GAP
        # The tip sits between source and target (pulled back toward the source), not past it.
        assert abs(tip.x - t.from_point.x) < abs(t.to_string.x - t.from_point.x)
