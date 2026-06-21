"""The elevator scenario in *client* (sequence-diagram) vocabulary.

The adapter-driven twin of ``elevator_script.py``: the same scenario, same command order,
expressed in the verbs a client (e.g. the model debugger) speaks -- ``add_actor`` / ``signal``
/ ``state_entered`` / ``implicit_event`` / ``actor_deleted`` -- which the
``SequenceDiagramAdapter`` translates into the layout-engine commands the other fixture issues
directly. Keeping the two in lock-step is what lets ``test_adapter_elevator`` prove the
translation reproduces the reference diagram exactly.

``drive`` runs the client command stream (no ``end_diagram``); the caller triggers the render
with ``adapter.end_diagram()``, mirroring ``populate``'s split.
"""
from __future__ import annotations

from sequins.sd_adapter import SequenceDiagramAdapter


def drive(a: SequenceDiagramAdapter) -> SequenceDiagramAdapter:
    """Run the full elevator client command stream against ``a`` and return it."""
    a.start_diagram(theme="elevator")

    a.add_actor(name="ASLEV: S1-3", initial_state="NOT REQUESTED")
    a.add_actor(name="UI")
    a.signal(source_actor="UI", dest_actor="ASLEV: S1-3", name="Stop request", time=1.0)
    a.state_entered(actor="ASLEV: S1-3", state="Registering stop", time=1.001)
    a.state_entered(actor="ASLEV: S1-3", state="Requesting service", time=1.002)

    a.add_actor(name="R53 / Shaft", initial_state="NO TRANSFER")
    a.signal(source_actor="ASLEV: S1-3", dest_actor="R53 / Shaft", name="Service requested")
    a.state_entered(actor="ASLEV: S1-3", state="REQUESTED", time=1.003)
    a.state_entered(actor="R53 / Shaft", state="Search for new destination", time=1.003)

    a.add_actor(name="Transfer: S1-3", born_and_die=True)
    a.signal(source_actor="R53 / Shaft", dest_actor="Transfer: S1-3", name="Execute")
    a.state_entered(actor="Transfer: S1-3", state="WAITING FOR CABIN", time=1.004)
    a.state_entered(actor="R53 / Shaft", state="TRANSFER IN PROGRESS", time=1.005)
    a.signal(source_actor="Transfer: S1-3", dest_actor="UI", name="Set destination")

    a.add_actor(name="Cabin: S1", initial_state="PICKUP DROPOFF")
    a.signal(source_actor="Transfer: S1-3", dest_actor="Cabin: S1", name="New transfer")
    a.state_entered(actor="Cabin: S1", state="Are we already there?", time=1.005)
    a.state_entered(actor="Cabin: S1", state="SECURING DOORS", time=1.006)
    a.add_actor(name="Door: S1", initial_state="CLOSED")

    a.signal(source_actor="Cabin: S1", dest_actor="Door: S1", name="Lock")
    a.state_entered(actor="Door: S1", state="LOCKED", time=1.007)
    a.signal(source_actor="Door: S1", dest_actor="Cabin: S1", name="Doors secure")
    a.state_entered(actor="Cabin: S1", state="READY TO GO", time=1.008)
    a.signal(source_actor="Cabin: S1", dest_actor="Transfer: S1-3", name="Ready to go")
    a.state_entered(actor="Transfer: S1-3", state="Dispatching cabin", time=1.009)
    a.signal(source_actor="Transfer: S1-3", dest_actor="Cabin: S1", name="Go")
    a.state_entered(actor="Transfer: S1-3", state="CABIN IN MOTION", time=1.010)
    a.state_entered(actor="Cabin: S1", state="Requesting transport", time=1.010)

    a.add_actor(name="TRANS")
    a.signal(source_actor="Cabin: S1", dest_actor="TRANS", name="Go to floor( dest floor: 3 )")
    a.state_entered(actor="Cabin: S1", state="MOVING", time=1.011)

    a.signal(source_actor="TRANS", dest_actor="Cabin: S1", name="Passing floor( floor: 1)", time=5.000)
    a.state_entered(actor="Cabin: S1", state="Update location", time=5.001)
    a.signal(source_actor="Cabin: S1", dest_actor="UI", name="Passing floor( floor: 1)")
    a.state_entered(actor="Cabin: S1", state="MOVING", time=5.002)

    a.signal(source_actor="TRANS", dest_actor="Cabin: S1", name="Passing floor( floor: 2)", time=8.000)
    a.state_entered(actor="Cabin: S1", state="Update location", time=8.001)
    a.signal(source_actor="Cabin: S1", dest_actor="UI", name="Passing floor( floor: 2)")
    a.state_entered(actor="Cabin: S1", state="MOVING", time=8.002)

    a.signal(source_actor="TRANS", dest_actor="Cabin: S1", name="Passing floor( floor: 3)", time=11.000)
    a.state_entered(actor="Cabin: S1", state="Update location", time=11.001)
    a.signal(source_actor="Cabin: S1", dest_actor="UI", name="Passing floor( floor: 3)")
    a.state_entered(actor="Cabin: S1", state="MOVING", time=11.002)

    a.signal(source_actor="TRANS", dest_actor="Cabin: S1", name="Arrived at floor", time=15.000)
    a.state_entered(actor="Cabin: S1", state="PICKUP DROPOFF", time=15.001)
    a.signal(source_actor="Cabin: S1", dest_actor="Door: S1", name="Unlock")
    a.signal(source_actor="Cabin: S1", dest_actor="Transfer: S1-3", name="Cabin at destination")

    a.state_entered(actor="Door: S1", state="OPENING", time=15.002)
    a.state_entered(actor="Transfer: S1-3", state="Cabin at destination", time=15.002)

    a.add_actor(name="SIO")
    a.implicit_event(source_actor="Door: S1", dest_actor="UI", name="Door opening")
    a.implicit_event(source_actor="Door: S1", dest_actor="SIO", name="Door opening")
    a.signal(source_actor="SIO", dest_actor="Door: S1", name="Door opened", time=18.000)
    a.state_entered(actor="Door: S1", state="OPEN", time=18.001)
    a.implicit_event(source_actor="Door: S1", dest_actor="UI", name="Door opened")

    a.state_entered(actor="Transfer: S1-3", state="Check for cabin reversal", time=15.003)
    a.state_entered(actor="Transfer: S1-3", state="Check for active floor service", time=15.004)
    a.signal(source_actor="Transfer: S1-3", dest_actor="ASLEV: S1-3", name="Stop serviced")
    a.signal(source_actor="Transfer: S1-3", dest_actor="UI", name="Cabin arrived( shaft:S1, direction: up )")
    a.state_entered(actor="Transfer: S1-3", state="WAITING FOR REQUESTS TO CLEAR", time=15.005)

    a.state_entered(actor="ASLEV: S1-3", state="Clear stop request", time=15.005)
    a.implicit_event(source_actor="ASLEV: S1-3", dest_actor="UI", name="Clear stop request")
    a.state_entered(actor="ASLEV: S1-3", state="NOT REQUESTED", time=15.006)
    a.signal(source_actor="ASLEV: S1-3", dest_actor="Transfer: S1-3", name="Requests cleared")

    a.state_entered(actor="Transfer: S1-3", state="Delete", time=15.007)
    a.signal(source_actor="Transfer: S1-3", dest_actor="R53 / Shaft", name="Transfer completed")

    a.actor_deleted(actor="Transfer: S1-3")

    a.state_entered(actor="ASLEV: S1-3", state="Search for new destination", time=15.008)
    a.state_entered(actor="ASLEV: S1-3", state="NO TRANSFER", time=15.015)

    return a
