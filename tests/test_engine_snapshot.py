"""Snapshot / partial-diagram tests for interactive rendering.

``LayoutEngine.render()`` draws an intermediate frame from the *current* population without
mutating it: it projects to the drawable subset (hiding unborn born-and-die strings + their
incident threads) and resolves a throwaway copy. These tests exercise that projection and
the partial-diagram resolve directly, so they need no SVG output -- only the same TabletSVG
text/symbol metrics the other layout tests already use.
"""
from __future__ import annotations

from sequins.layout import Layout
from sequins.layout_engine import LayoutEngine


def _through_transfer_birth_signal() -> LayoutEngine:
    """Populate up to Transfer's creation signal but *before* its first state.

    At this point Transfer (born and die) has an incoming thread (Execute) but no bead, so
    it is not yet born."""
    e = LayoutEngine()
    e.start_diagram(theme="elevator")
    e.add_string(material="persistent", name="ASLEV: S1-3", bead_color="NOT REQUESTED")
    e.add_string(material="external", name="UI")
    e.add_thread(material="signal", label="Stop request", from_string="UI", to_string="ASLEV: S1-3", depth=1.0)
    e.add_bead(material="state", string="ASLEV: S1-3", bead_color="Registering stop", depth=1.001)
    e.add_string(material="persistent", name="R53 / Shaft", bead_color="NO TRANSFER")
    e.add_thread(material="signal", label="Service requested", from_string="ASLEV: S1-3", to_string="R53 / Shaft")
    e.add_bead(material="state", string="R53 / Shaft", bead_color="Search for new destination", depth=1.003)
    e.add_string(material="born and die", name="Transfer: S1-3")
    e.add_thread(material="signal", label="Execute", from_string="R53 / Shaft", to_string="Transfer: S1-3")
    return e


def test_unborn_born_and_die_is_hidden():
    e = _through_transfer_birth_signal()
    snap = LayoutEngine._drawable_snapshot(e.diagram)
    # Incoming thread but no bead yet -> unborn -> the string is hidden ...
    assert "Transfer: S1-3" not in [s.name for s in snap.strings]
    # ... and its creation signal is dropped in the same frame.
    assert "Execute" not in [t.label for t in snap.threads]
    # The canonical population keeps both (it's an append-only log).
    assert "Transfer: S1-3" in [s.name for s in e.diagram.strings]
    assert "Execute" in [t.label for t in e.diagram.threads]


def test_birth_reveals_string_and_creation_thread():
    e = _through_transfer_birth_signal()
    e.add_bead(material="state", string="Transfer: S1-3", bead_color="WAITING FOR CABIN", depth=1.004)
    snap = LayoutEngine._drawable_snapshot(e.diagram)
    assert "Transfer: S1-3" in [s.name for s in snap.strings]
    assert "Execute" in [t.label for t in snap.threads]


def test_partial_snapshot_resolves_and_leaves_canonical_pristine():
    e = _through_transfer_birth_signal()
    e.add_bead(material="state", string="Transfer: S1-3", bead_color="WAITING FOR CABIN", depth=1.004)
    snap = LayoutEngine._drawable_snapshot(e.diagram)
    Layout(snap).resolve()  # the layout pass must tolerate a partial diagram
    assert all(s.x is not None for s in snap.strings)
    # The snapshot resolved a copy: the canonical population was never placed.
    assert all(s.x is None for s in e.diagram.strings)


def test_snapshot_shares_reference_data_but_copies_the_graph():
    e = _through_transfer_birth_signal()
    snap = LayoutEngine._drawable_snapshot(e.diagram)
    assert snap.theme is e.diagram.theme
    orig = e.diagram.strings[0]
    copied = next(s for s in snap.strings if s.name == orig.name)
    assert copied is not orig            # the String instance is a fresh copy ...
    assert copied.material is orig.material  # ... but its material is shared, not duplicated
