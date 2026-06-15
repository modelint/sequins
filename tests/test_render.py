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
    # 9 lifeline names + 36 state names + 28 message labels.
    assert svg.count("<text") == 73


def test_string_colors_reach_the_svg(tmp_path):
    # Thread color match (#7): the elevator theme's String Colors resolve onto the lines.
    e = LayoutEngine()
    populate(e)
    out = render(e.end_diagram(), tmp_path / "elevator.svg")
    svg = out.read_text()
    assert "rgb(142,250,0)" in svg  # lime  (UI)
    assert "rgb(66,148,247)" in svg  # aqua  (TRANS)
    assert "rgb(255,64,255)" in svg  # magenta (SIO)
