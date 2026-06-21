"""The adapter-driven elevator must reproduce the engine-driven reference diagram.

Renders the same scenario two ways -- the engine fixture (``elevator_script.populate``) and
the client fixture (``elevator_adapter_script.drive``) -- and asserts the SVGs are identical.
This is the end-to-end proof that the SequenceDiagramAdapter's translation is faithful.
"""
from __future__ import annotations

from elevator_adapter_script import drive
from elevator_script import populate

from sequins.layout_engine import LayoutEngine
from sequins.render import render
from sequins.sd_adapter import SequenceDiagramAdapter


def test_adapter_reproduces_engine_diagram(tmp_path):
    engine_svg = tmp_path / "engine.svg"
    e = LayoutEngine()
    populate(e)
    render(e.end_diagram(), engine_svg)

    adapter_svg = tmp_path / "adapter.svg"
    drive(SequenceDiagramAdapter(adapter_svg)).end_diagram()

    assert adapter_svg.read_bytes() == engine_svg.read_bytes()
