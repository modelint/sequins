"""Thread color match (layout sub-pass #7).

A Thread takes the color of a String-Colored endpoint: source (``from``) wins, the target
(``to``) is the fallback, and a Thread between two uncolored Strings stays uncolored.
"""
from __future__ import annotations

from elevator_script import populate

from sequins.layout_engine import LayoutEngine


def build():
    e = LayoutEngine()
    populate(e)
    e.end_diagram()
    return e.diagram


def _thread(d, label):
    return next(t for t in d.threads if t.label == label)


def test_source_string_color_wins():
    # 'Stop request' emanates from UI (lime) into ASLEV (uncolored) -> lime.
    d = build()
    assert _thread(d, "Stop request").color == "lime"


def test_target_color_used_when_source_uncolored():
    # 'Set destination' runs Transfer (uncolored) -> UI (lime); the target supplies the color.
    d = build()
    assert _thread(d, "Set destination").color == "lime"


def test_trans_colored_thread():
    # 'Go to floor(...)' runs Cabin (uncolored) -> TRANS (aqua).
    d = build()
    assert _thread(d, "Go to floor( dest floor: 3 )").color == "aqua"


def test_uncolored_thread_between_bare_strings():
    # 'Service requested' runs ASLEV -> R53 / Shaft, neither colored -> presentation default.
    d = build()
    assert _thread(d, "Service requested").color is None


def test_override_color_beats_endpoint_match():
    # An explicit Element Override color on a Thread wins over the endpoint match.
    d = build()
    t = _thread(d, "Stop request")
    t.override_color = "magenta"
    from sequins.layout import Layout

    Layout(d)._match_thread_colors()
    assert t.color == "magenta"
