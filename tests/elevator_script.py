"""The canonical elevator scenario, transcribed verbatim from
``documentation/architecture/layout_engine_api.md``.

This is the reference input for the layout engine: a reusable fixture for population tests
now and the layout pass later. Keep it in step with the spec doc.
"""
from __future__ import annotations

from sequins.layout_engine import LayoutEngine


def populate(e: LayoutEngine) -> LayoutEngine:
    """Run the full elevator command stream against ``e`` and return it."""
    e.start_diagram(theme="elevator")

    e.add_string(material="persistent", name="ASLEV: S1-3", bead_color="NOT REQUESTED")
    e.add_string(material="external", name="UI")
    e.add_thread(material="signal", label="Stop request", from_string="UI", to_string="ASLEV: S1-3", depth=1.0)
    e.add_bead(material="state", string="ASLEV: S1-3", bead_color="Registering stop", depth=1.001)
    e.add_bead(material="state", string="ASLEV: S1-3", bead_color="Requesting service", depth=1.002)

    e.add_string(material="persistent", name="R53 / Shaft", bead_color="NO TRANSFER")
    e.add_thread(material="signal", label="Service requested", from_string="ASLEV: S1-3", to_string="R53 / Shaft")
    e.add_bead(material="state", string="ASLEV: S1-3", bead_color="REQUESTED", depth=1.003)
    e.add_bead(material="state", string="R53 / Shaft", bead_color="Search for new destination", depth=1.003)

    e.add_string(material="born and die", name="Transfer: S1-3")
    e.add_thread(material="signal", label="Execute", from_string="R53 / Shaft", to_string="Transfer: S1-3")
    e.add_bead(material="state", string="Transfer: S1-3", bead_color="WAITING FOR CABIN", depth=1.004)
    e.add_bead(material="state", string="R53 / Shaft", bead_color="TRANSFER IN PROGRESS", depth=1.005)
    e.add_thread(material="signal", label="Set destination", from_string="Transfer: S1-3", to_string="UI")

    e.add_string(material="persistent", name="Cabin: S1", bead_color="PICKUP DROPOFF")
    e.add_thread(material="signal", label="New transfer", from_string="Transfer: S1-3", to_string="Cabin: S1")
    e.add_bead(material="state", string="Cabin: S1", bead_color="Are we already there?", depth=1.005)
    e.add_bead(material="state", string="Cabin: S1", bead_color="SECURING DOORS", depth=1.006)
    e.add_string(material="persistent", name="Door: S1", bead_color="CLOSED")

    e.add_thread(material="signal", label="Lock", from_string="Cabin: S1", to_string="Door: S1")
    e.add_bead(material="state", string="Door: S1", bead_color="LOCKED", depth=1.007)
    e.add_thread(material="signal", label="Doors secure", from_string="Door: S1", to_string="Cabin: S1")
    e.add_bead(material="state", string="Cabin: S1", bead_color="READY TO GO", depth=1.008)
    e.add_thread(material="signal", label="Ready to go", from_string="Cabin: S1", to_string="Transfer: S1-3")
    e.add_bead(material="state", string="Transfer: S1-3", bead_color="Dispatching cabin", depth=1.009)
    e.add_thread(material="signal", label="Go", from_string="Transfer: S1-3", to_string="Cabin: S1")
    e.add_bead(material="state", string="Transfer: S1-3", bead_color="CABIN IN MOTION", depth=1.010)
    e.add_bead(material="state", string="Cabin: S1", bead_color="Requesting transport", depth=1.010)

    e.add_string(material="external", name="TRANS")
    e.add_thread(material="signal", label="Go to floor( dest floor: 3 )", from_string="Cabin: S1", to_string="TRANS")
    e.add_bead(material="state", string="Cabin: S1", bead_color="MOVING", depth=1.011)

    e.add_thread(material="signal", label="Passing floor( floor: 1)", from_string="TRANS", to_string="Cabin: S1", depth=5.000)
    e.add_bead(material="state", string="Cabin: S1", bead_color="Update location", depth=5.001)
    e.add_thread(material="signal", label="Passing floor( floor: 1)", from_string="Cabin: S1", to_string="UI")
    e.add_bead(material="state", string="Cabin: S1", bead_color="MOVING", depth=5.002)

    e.add_thread(material="signal", label="Passing floor( floor: 2)", from_string="TRANS", to_string="Cabin: S1", depth=8.000)
    e.add_bead(material="state", string="Cabin: S1", bead_color="Update location", depth=8.001)
    e.add_thread(material="signal", label="Passing floor( floor: 2)", from_string="Cabin: S1", to_string="UI")
    e.add_bead(material="state", string="Cabin: S1", bead_color="MOVING", depth=8.002)

    e.add_thread(material="signal", label="Passing floor( floor: 3)", from_string="TRANS", to_string="Cabin: S1", depth=11.000)
    e.add_bead(material="state", string="Cabin: S1", bead_color="Update location", depth=11.001)
    e.add_thread(material="signal", label="Passing floor( floor: 3)", from_string="Cabin: S1", to_string="UI")
    e.add_bead(material="state", string="Cabin: S1", bead_color="MOVING", depth=11.002)

    e.add_thread(material="signal", label="Arrived at floor", from_string="TRANS", to_string="Cabin: S1", depth=15.000)
    e.add_bead(material="state", string="Cabin: S1", bead_color="PICKUP DROPOFF", depth=15.001)
    e.add_thread(material="signal", label="Unlock", from_string="Cabin: S1", to_string="Door: S1")
    e.add_thread(material="signal", label="Cabin at destination", from_string="Cabin: S1", to_string="Transfer: S1-3")

    e.add_bead(material="state", string="Door: S1", bead_color="OPENING", depth=15.002)
    e.add_bead(material="state", string="Transfer: S1-3", bead_color="Cabin at destination", depth=15.002)

    e.add_string(material="external", name="SIO")
    e.add_thread(material="implicit event", label="Door opening", from_string="Door: S1", to_string="UI")
    e.add_thread(material="implicit event", label="Door opening", from_string="Door: S1", to_string="SIO")
    e.add_thread(material="signal", label="Door opened", from_string="SIO", to_string="Door: S1", depth=18.000)
    e.add_bead(material="state", string="Door: S1", bead_color="OPEN", depth=18.001)
    e.add_thread(material="implicit event", label="Door opened", from_string="Door: S1", to_string="UI")

    e.add_bead(material="state", string="Transfer: S1-3", bead_color="Check for cabin reversal", depth=15.003)
    e.add_bead(material="state", string="Transfer: S1-3", bead_color="Check for active floor service", depth=15.004)
    e.add_thread(material="signal", label="Stop serviced", from_string="Transfer: S1-3", to_string="ASLEV: S1-3")
    e.add_thread(material="signal", label="Cabin arrived( shaft:S1, direction: up )", from_string="Transfer: S1-3", to_string="ASLEV: S1-3")
    e.add_bead(material="state", string="Transfer: S1-3", bead_color="WAITING FOR REQUESTS TO CLEAR", depth=15.005)

    e.add_bead(material="state", string="ASLEV: S1-3", bead_color="Clear stop request", depth=15.005)
    e.add_thread(material="implicit event", label="Clear stop request", from_string="ASLEV: S1-3", to_string="UI")
    e.add_bead(material="state", string="ASLEV: S1-3", bead_color="NOT REQUESTED", depth=15.006)
    e.add_thread(material="signal", label="Requests cleared", from_string="ASLEV: S1-3", to_string="Transfer: S1-3")

    e.add_bead(material="state", string="Transfer: S1-3", bead_color="Delete", depth=15.007)
    e.add_thread(material="signal", label="Transfer completed", from_string="Transfer: S1-3", to_string="R53 / Shaft")

    e.end_string(string="Transfer: S1-3")

    e.add_bead(material="state", string="ASLEV: S1-3", bead_color="Search for new destination", depth=15.008)
    e.add_bead(material="state", string="ASLEV: S1-3", bead_color="NO TRANSFER", depth=15.015)

    e.end_diagram()
    return e
