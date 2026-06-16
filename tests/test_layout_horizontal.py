"""Horizontal-axis tests (layout sub-passes #1 positions, #2 x, #3 endpoint binding)."""
from __future__ import annotations

from elevator_script import populate

from sequins.layout_engine import LayoutEngine


def build():
    e = LayoutEngine()
    populate(e)
    e.end_diagram()  # triggers the layout pass
    return e.diagram


def test_position_order_matches_reference():
    d = build()
    order = [s.name for s in sorted(d.strings, key=lambda s: s.position)]
    assert order == [
        "UI",            # UI-L, left edge
        "ASLEV: S1-3",
        "R53 / Shaft",
        "Transfer: S1-3",
        "Cabin: S1",
        "Door: S1",
        "TRANS",         # R-2
        "SIO",           # R-1
        "UI",            # UI-R, right edge
    ]
    ui = sorted(d.strings_named("UI"), key=lambda s: s.position)
    assert ui[0].pinned.boundary == "L" and ui[1].pinned.boundary == "R"


def test_x_strictly_increases_with_position():
    d = build()
    by_pos = sorted(d.strings, key=lambda s: s.position)
    xs = [s.x for s in by_pos]
    assert all(b > a for a, b in zip(xs, xs[1:]))
    assert by_pos[0].x > 0  # inset from the canvas edge


def test_spans_are_uniform_and_label_driven():
    # #2: one global span everywhere (the horizontal lever is uniform), wide enough to clear
    # beads and grown so labels clear their source bead.
    d = build()
    by_pos = sorted(d.strings, key=lambda s: s.position)
    gaps = {round(b.x - a.x, 6) for a, b in zip(by_pos, by_pos[1:])}
    assert len(gaps) == 1  # uniform
    span = gaps.pop()
    bead_width = max(b.size.width for s in d.strings for b in s.beads)
    assert span >= max(d.theme.layout.min_string_span, bead_width)


def test_labels_clear_their_source_beads():
    # The uniform span is sized so every destination-anchored label clears the source bead
    # it springs from by at least the configurable Min bead edge gap (the horizontal lever).
    from sequins.text import TextMeasure

    d = build()
    target_gap = d.theme.layout.target_string_label_gap
    bead_gap = d.theme.layout.min_bead_edge_gap
    m = TextMeasure.for_theme(d.theme)
    for t in d.threads:
        if t.source_bead is None:
            continue
        w = m.line_width("message", t.label)
        if t.to_point.x >= t.from_point.x:  # going right: source bead on the left
            label_far = t.to_point.x - target_gap - w
            src_edge = t.source_bead.center.x + t.source_bead.size.width / 2
            assert label_far - src_edge >= bead_gap - 1e-6
        else:  # going left: source bead on the right
            label_far = t.to_point.x + target_gap + w
            src_edge = t.source_bead.center.x - t.source_bead.size.width / 2
            assert src_edge - label_far >= bead_gap - 1e-6


def test_deferred_ui_endpoints_bound_to_nearest():
    d = build()
    ui_left = min(d.strings_named("UI"), key=lambda s: s.x)
    ui_right = max(d.strings_named("UI"), key=lambda s: s.x)
    threads = {(t.from_name, t.to_name, t.label): t for t in d.threads}

    # Stop request: UI -> ASLEV (pos 2). UI-L is far nearer.
    assert threads[("UI", "ASLEV: S1-3", "Stop request")].from_string is ui_left
    # Set destination: Transfer (pos 4) -> UI. UI-L nearer (3 spans vs 5).
    assert threads[("Transfer: S1-3", "UI", "Set destination")].to_string is ui_left

    # No endpoint is left unbound after the pass.
    assert all(t.from_string is not None and t.to_string is not None for t in d.threads)
