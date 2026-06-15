"""Population-phase tests: the Add_* commands build the right curtain metamodel.

No geometry is asserted here -- that's the layout pass. These pin down structure: counts,
the UI multi-position fan-out, top-bead placement, bounded ends, and the bare-vs-beaded
origin / depth contract for threads.
"""
from __future__ import annotations

from elevator_script import populate

from sequins.layout_engine import LayoutEngine


def build():
    return populate(LayoutEngine()).diagram


def test_string_count_and_ui_fan_out():
    d = build()
    # 8 distinct names; UI occupies two theme positions -> 9 String instances.
    assert len(d.strings) == 9
    ui = d.strings_named("UI")
    assert len(ui) == 2
    assert {p.pinned.boundary for p in ui} == {"L", "R"}
    assert all(s.color == "lime" for s in ui)
    assert all(not s.beaded and not s.bounded for s in ui)


def test_bead_count_and_top_beads():
    d = build()
    beads = [b for s in d.strings for b in s.beads]
    # 32 Add_bead commands + 4 Add_string top beads (ASLEV, R53, Cabin, Door).
    assert len(beads) == 36
    top_beads = [b for b in beads if b.depth == 0.0]
    assert {b.string.name for b in top_beads} == {"ASLEV: S1-3", "R53 / Shaft", "Cabin: S1", "Door: S1"}
    # Bead sequence is derived from creation order within its String.
    aslev = d.strings_named("ASLEV: S1-3")[0]
    assert [b.sequence for b in aslev.beads] == list(range(len(aslev.beads)))
    assert aslev.beads[0].color_name == "NOT REQUESTED"  # the top bead


def test_bounded_string_ends():
    d = build()
    transfer = d.strings_named("Transfer: S1-3")[0]
    assert transfer.beaded and transfer.bounded
    assert transfer.material.top_end == "create delete"
    assert transfer.material.bottom_end == "create delete"
    assert transfer.lower_bounded  # end_string was called


def test_thread_count_and_origin_depth_contract():
    d = build()
    assert len(d.threads) == 28
    for t in d.threads:
        if t.depth is None:
            # Beaded origin: bound (unique) and beaded; depth comes from a bead at layout.
            assert t.from_string is not None and t.from_string.beaded, t.label
        else:
            # Bare origin: either an unbound multi-position UI, or a bound non-beaded edge.
            assert t.from_string is None or not t.from_string.beaded, t.label


def test_ui_endpoints_defer_binding():
    d = build()
    # Every thread touching UI leaves that endpoint unbound for the layout pass to pick.
    ui_threads = [t for t in d.threads if "UI" in (t.from_name, t.to_name)]
    assert ui_threads
    for t in ui_threads:
        if t.from_name == "UI":
            assert t.from_string is None
        if t.to_name == "UI":
            assert t.to_string is None
