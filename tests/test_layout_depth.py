"""Depth-axis tests (layout sub-pass #4, compressed mode).

Asserts the vertical axis in isolation: pitch, monotonicity, cross-String alignment of
equal depths, and that thread y-levels track their source depth.
"""
from __future__ import annotations

from elevator_script import populate

from sequins.layout import Layout
from sequins.layout_engine import LayoutEngine


def build():
    e = LayoutEngine()
    populate(e)
    e.end_diagram()  # triggers the layout pass
    return e.diagram


def test_base_row_gap_is_standard_height_plus_separation():
    d = build()
    L = d.theme.layout
    levels = sorted({b.compressed_depth for s in d.strings for b in s.beads}
                    | {t.height for t in d.threads})
    gaps = [round(b - a, 6) for a, b in zip(levels, levels[1:])]
    std_h = max(m.standard_size.height for m in d.theme.curtain_style.bead_materials.values())
    # Standard rows keep the base pitch (25 + 20); rows holding a tall wrapped bead open wider.
    assert min(gaps) == std_h + L.min_bead_separation == 45.0
    assert max(gaps) > min(gaps)


def test_consecutive_beads_keep_min_separation():
    # The axis is bead-height aware: even two adjacent 2-line beads clear the min separation
    # (a uniform pitch sized for standard beads would let them collide).
    d = build()
    sep = d.theme.layout.min_bead_separation
    for s in d.strings:
        bs = sorted(s.beads, key=lambda b: -b.center.y)  # shallow -> deep
        for a, b in zip(bs, bs[1:]):
            clear = (a.center.y - a.size.height / 2) - (b.center.y + b.size.height / 2)
            assert clear >= sep - 1e-6


def test_compressed_depth_is_monotonic_in_depth():
    d = build()
    beads = sorted((b for s in d.strings for b in s.beads), key=lambda b: b.depth)
    levels = [b.compressed_depth for b in beads]
    assert levels == sorted(levels)
    assert beads[0].compressed_depth == 0.0  # shallowest event at the top of the axis


def test_equal_depths_share_a_row_across_strings():
    d = build()
    aslev = d.strings_named("ASLEV: S1-3")[0]
    r53 = d.strings_named("R53 / Shaft")[0]
    # REQUESTED@1.003 (ASLEV) and Search for new destination@1.003 (R53) align.
    a = next(b for b in aslev.beads if b.color_name == "REQUESTED")
    r = next(b for b in r53.beads if b.color_name == "Search for new destination")
    assert a.depth == r.depth == 1.003
    assert a.compressed_depth == r.compressed_depth


def test_rows_are_strictly_ordered_and_clear():
    d = build()
    levels = sorted({b.compressed_depth for s in d.strings for b in s.beads}
                    | {t.height for t in d.threads})
    gaps = [round(b - a, 6) for a, b in zip(levels, levels[1:])]
    # Distinct rows, each at least the base pitch apart (compressed, but never overlapping).
    assert all(g >= 45.0 for g in gaps)


def test_thread_height_tracks_source_depth():
    d = build()
    layout = Layout(d)
    layout.resolve()
    by_label = {t.label: t for t in d.threads}
    # Beaded origin: 'Service requested' projects from ASLEV's lowest bead at issue,
    # 'Requesting service'@1.002.
    assert by_label["Service requested"].source_bead.depth == 1.002
    assert by_label["Service requested"].height == layout.compressed_level(1.002)
    # Bare origin: 'Stop request' from UI carries its own depth 1.0. The axis top is the
    # depth-0 top beads, so 1.0 is rank 1 (one pitch down).
    assert by_label["Stop request"].depth == 1.0
    assert layout.compressed_level(0.0) == 0.0
    assert by_label["Stop request"].height == layout.compressed_level(1.0) == 45.0
