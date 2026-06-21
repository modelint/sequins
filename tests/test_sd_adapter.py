"""Tests for the Sequence Diagram adapter (client vocabulary -> layout-engine translation).

Translation tests inspect the engine's (pristine) population directly, so they need no SVG
output. The two rendering tests write to a tmp file and use the same TabletSVG metrics the
other layout tests rely on.
"""
from __future__ import annotations

import pytest

from sequins.sd_adapter import SequenceDiagramAdapter


def _started(out="unused.svg", **kw) -> SequenceDiagramAdapter:
    a = SequenceDiagramAdapter(out, **kw)
    a.start_diagram(theme="elevator")
    return a


def test_material_inference_and_initial_state_bead():
    a = _started()
    a.add_actor(name="UI")                                       # no state -> external
    a.add_actor(name="ASLEV: S1-3", initial_state="NOT REQUESTED")  # state -> persistent
    a.add_actor(name="Transfer: S1-3", born_and_die=True)        # flag wins -> born and die
    d = a._engine.diagram

    mats = {s.name: s.material.name for s in d.strings}
    assert mats == {"UI": "external", "ASLEV: S1-3": "persistent", "Transfer: S1-3": "born and die"}
    # initial_state translated to the actor's top bead
    aslev = d.strings_named("ASLEV: S1-3")[0]
    assert [b.color_name for b in aslev.beads] == ["NOT REQUESTED"]
    # external with no initial_state carries no bead
    assert all(not s.beads for s in d.strings_named("UI"))


def test_born_and_die_rejects_initial_state():
    a = _started()
    with pytest.raises(ValueError, match="cannot have an initial_state"):
        a.add_actor(name="Transfer: S1-3", born_and_die=True, initial_state="WAITING")


def test_signal_and_implicit_event_translation():
    a = _started()
    a.add_actor(name="UI")
    a.add_actor(name="ASLEV: S1-3", initial_state="NOT REQUESTED")
    a.add_actor(name="Door: S1", initial_state="CLOSED")
    a.signal(source_actor="UI", dest_actor="ASLEV: S1-3", name="Stop request", time=1.0)
    a.implicit_event(source_actor="Door: S1", dest_actor="UI", name="Door opening")
    threads = {t.label: t for t in a._engine.diagram.threads}

    sig = threads["Stop request"]
    assert sig.material.name == "signal"
    assert sig.from_name == "UI" and sig.to_name == "ASLEV: S1-3" and sig.depth == 1.0
    imp = threads["Door opening"]
    assert imp.material.name == "implicit event"
    assert imp.depth is None  # time omitted


def test_state_entered_translation():
    a = _started()
    a.add_actor(name="ASLEV: S1-3", initial_state="NOT REQUESTED")
    a.state_entered(actor="ASLEV: S1-3", state="Registering stop", time=1.001)
    beads = a._engine.diagram.strings_named("ASLEV: S1-3")[0].beads
    assert [(b.color_name, b.depth) for b in beads] == [
        ("NOT REQUESTED", 0.0), ("Registering stop", 1.001),
    ]


def test_actor_deleted_caps_born_and_die_only():
    a = _started()
    a.add_actor(name="ASLEV: S1-3", initial_state="NOT REQUESTED")
    a.add_actor(name="Transfer: S1-3", born_and_die=True)

    a.actor_deleted("Transfer: S1-3")
    assert a._engine.diagram.strings_named("Transfer: S1-3")[0].lower_bounded is True

    with pytest.raises(ValueError, match="only valid for a born-and-die"):
        a.actor_deleted("ASLEV: S1-3")
    with pytest.raises(ValueError, match="unknown actor"):
        a.actor_deleted("Nope")


def test_end_diagram_renders_and_leaves_population_pristine(tmp_path):
    out = tmp_path / "diagram.svg"
    a = SequenceDiagramAdapter(out)
    a.start_diagram(theme="elevator")
    a.add_actor(name="UI")
    a.add_actor(name="ASLEV: S1-3", initial_state="NOT REQUESTED")
    a.signal(source_actor="UI", dest_actor="ASLEV: S1-3", name="Stop request", time=1.0)
    a.state_entered(actor="ASLEV: S1-3", state="Registering stop", time=1.001)
    assert not out.exists()  # file-input mode: nothing drawn until end_diagram

    p = a.end_diagram()
    assert p == out and out.stat().st_size > 0
    assert all(s.x is None for s in a._engine.diagram.strings)  # canonical never resolved


def test_interactive_writes_a_frame_per_verb(tmp_path):
    out = tmp_path / "live.svg"
    a = SequenceDiagramAdapter(out, interactive=True)
    a.start_diagram(theme="elevator")
    assert not out.exists()  # start_diagram does not snapshot

    a.add_actor(name="ASLEV: S1-3", initial_state="NOT REQUESTED")
    assert out.exists()  # a frame appeared after the first visible verb
    first = out.read_bytes()

    a.state_entered(actor="ASLEV: S1-3", state="Registering stop", time=1.001)
    assert out.read_bytes() != first  # the frame was rewritten
