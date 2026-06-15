"""Knots & gaps (layout sub-pass #6): fanning (R26 fixed knot) and slip knots (R11)."""
from __future__ import annotations

from elevator_script import populate

from sequins.layout_engine import LayoutEngine


def build():
    e = LayoutEngine()
    populate(e)
    e.end_diagram()
    return e.diagram


def _threads(d, label):
    return [t for t in d.threads if t.label == label]


def test_fanning_spreads_threads_sharing_a_bead_face():
    # OPENING projects two 'Door opening' threads on the same side; they must not overlap.
    d = build()
    fan = _threads(d, "Door opening")
    assert len(fan) == 2
    sep = d.theme.layout.min_thread_separation
    ys = sorted(t.from_point.y for t in fan)
    # Evenly split around the bead center, one min-separation apart.
    assert ys[1] - ys[0] == sep
    center = fan[0].source_bead.center.y
    assert (ys[0] + ys[1]) / 2 == center
    # Symmetric integer notches; each thread stays horizontal.
    assert sorted(t.fixed_knot for t in fan) == [-1, 1]
    assert all(t.from_point.y == t.to_point.y for t in fan)


def test_lone_thread_keeps_center_knot():
    # A thread that is the only one off its source bead is unfanned (knot 0, no shift).
    d = build()
    t = _threads(d, "Lock")[0]  # sole thread from its source bead face
    assert t.fixed_knot == 0
    assert t.from_point.y == t.source_bead.center.y


def test_slip_knot_records_blocking_bead_above():
    # 'Stop request' lands in the gap above ASLEV's 'Registering stop' (below NOT REQUESTED).
    d = build()
    t = _threads(d, "Stop request")[0]
    assert t.blocking_bead is not None
    assert t.blocking_bead.color_name == "Registering stop"
    assert t.blocking_bead in t.to_string.beads
    # The thread sits above the blocking bead (shallower -> larger y).
    assert t.to_point.y > t.blocking_bead.center.y


def test_no_slip_knot_on_external_target():
    # A thread terminating on a bare (external) String has no blocking bead.
    d = build()
    t = _threads(d, "Go to floor( dest floor: 3 )")[0]
    assert not t.to_string.beaded
    assert t.blocking_bead is None
