## Layout Engine API

Here we will walk through the layout engine commands necessary to start the elevator example:

    Start_diagram( theme='elevator' )

This initial command gives us the key we use to locate a Diagram Theme in the `diagram_theme.yaml` file.
If found, we use it. If not, we set the default theme. Next we compute the Curtain Diagram.Origin, Size and Rod Height with Compressed set to the default (True)

    Add_string( material='persistent', name='ASLEV: S1-3', bead_color='NOT REQUESTED' )

Here we create our first String instance. Since a top bead is specified, we know that the absolute depth of that bead must be zero. The 'persistent' material is beaded and unbounded, so this is an unbounded Beaded String. The string name is not found in the Diagram Theme, so we aren't applying any String Settings.  We set the position of that String to 1 computing all coordinate values.

We aren't going to attempt to draw anything until we get a render diagram command, so we are free to move beads and strings around as necessary as the create commands arrive.

And whenever a new bead is specified we check for an existing Bead Color, if not found, create a new one. So in this case, we'll create a new instance of Bead Color named 'NOT REQUESTED'.

    Add_string( material='external', name='UI' )

We look for the name in the Curtain Diagram's theme and find it. The elevator theme specifies two positions for UI, so we create two instances of Bare String — the 'external' material is not beaded. Both are unbounded.

Note that the position of the initial Beaded String moves from 1 to 2.

    Add_thread( material='signal', label='Stop request', from_string='UI', to_string='ASLEV: S1-3', depth=1.0 )

The from string is a Bare String, so we need to create a Thread from Bare String instance and connect it below the
lowest Bead in the target Beaded String, which happens to be 'NOT REQUESTED' (the final gap placement is resolved by depth at End_diagram, not fixed at arrival time). A String Color is specified for the UI string in the Diagram Theme, so the Thread is recolored to match it. A Thread takes the color of a String-Colored string it connects to at *either* end — incoming as well as outgoing. If a Thread connects two String-Colored strings, the source (from) string's color wins (the emanate-only fallback).

    Add_bead( material='state', string='ASLEV: S1-3', bead_color='Registering stop', depth=1.001 )
    Add_bead( material='state', string='ASLEV: S1-3', bead_color='Requesting service', depth=1.002 )

Note the very small depth increment. Since it is so small it will have no effect on vertical spacing either in absolute or compressed mode since the combined Layout attributes will yield the actual spacing.

    Add_string( material='persistent', name='R53 / Shaft', bead_color='NO TRANSFER' )

Nothing new here, process like the previous similar command. This gives us another Beaded String at position 3. And since no depth is specified, assume it is 0, i.e. top of the String.

    Add_thread( material='signal', label='Service requested', from_string='ASLEV: S1-3', to_string='R53 / Shaft' )

Since the source is a Beaded String, the thread is projected from the face of the lowest Bead on that String which will be Bead with Sequence 3.

The following commands follow with no additional features.

    Add_bead( material='state', string='ASLEV: S1-3', bead_color='REQUESTED', depth=1.003 )
    Add_bead( material='state', string='R53 / Shaft', bead_color='Search for new destination', depth=1.003 )

And now we have a bounded string. It does not specify a topmost bead and it does not specify a depth. The depth will be determined by the first incoming thread:

    Add_string( material='born and die', name='Transfer: S1-3' )

    Add_thread( material='signal', label='Execute', from_string='R53 / Shaft', to_string='Transfer: S1-3' )

The depth of the above Thread is taken from its source Bead and becomes the depth of the target bounded String.

No extra features in these commands:

    Add_bead( material='state', string='Transfer: S1-3', bead_color='WAITING FOR CABIN', depth=1.004 )
    Add_bead( material='state', string='R53 / Shaft', bead_color='TRANSFER IN PROGRESS', depth=1.005 )
    Add_thread( material='signal', label='Set destination', from_string='Transfer: S1-3', to_string='UI' )

The small increments in time are a result of state transitions happening in compute time. They are not waiting on input from the outside world. For this exercise we'll just specify an increment by .001 for each.

The UI String name is present in two positions, so we draw the Thread to the nearer one by horizontal distance — here, the left UI is nearer to Transfer. Because positions can still shift as more Strings are added, this is resolved at render time, which is another reason we don't draw until directed. (More advanced placement — weighing adjacent-thread congestion as well as distance — is deferred; for now, shortest distance wins.)

    Add_string( material='persistent', name='Cabin: S1', bead_color='PICKUP DROPOFF' )
    Add_thread( material='signal', label='New transfer', from_string='Transfer: S1-3', to_string='Cabin: S1' )
    Add_bead( material='state', string='Cabin: S1', bead_color='Are we already there?', depth=1.005 )
    Add_bead( material='state', string='Cabin: S1', bead_color='SECURING DOORS', depth=1.006 )
    Add_string( material='persistent', name='Door: S1', bead_color='CLOSED' )

    Add_thread( material='signal', label='Lock', from_string='Cabin: S1', to_string='Door: S1' )
    Add_bead( material='state', string='Door: S1', bead_color='LOCKED', depth=1.007 )
    Add_thread( material='signal', label='Doors secure', from_string='Door: S1', to_string='Cabin: S1' )
    Add_bead( material='state', string='Cabin: S1', bead_color='READY TO GO', depth=1.008 )
    Add_thread( material='signal', label='Ready to go', from_string='Cabin: S1', to_string='Transfer: S1-3' )
    Add_bead( material='state', string='Transfer: S1-3', bead_color='Dispatching cabin', depth=1.009 )
    Add_thread( material='signal', label='Go', from_string='Transfer: S1-3', to_string='Cabin: S1' )
    Add_bead( material='state', string='Transfer: S1-3', bead_color='CABIN IN MOTION', depth=1.010 )
    Add_bead( material='state', string='Cabin: S1', bead_color='Requesting transport', depth=1.010 )

    Add_string( material='external', name='TRANS' )
    Add_thread( material='signal', label='Go to floor( dest floor: 3 )', from_string='Cabin: S1', to_string='TRANS' )
    Add_bead( material='state', string='Cabin: S1', bead_color='MOVING', depth=1.011 )

    Add_thread( material='signal', label='Passing floor( floor: 1)', from_string='TRANS', to_string='Cabin: S1', depth=5.000 )
    Add_bead( material='state', string='Cabin: S1', bead_color='Update location', depth=5.001 )
    Add_thread( material='signal', label='Passing floor( floor: 1)', from_string='Cabin: S1', to_string='UI' )
    Add_bead( material='state', string='Cabin: S1', bead_color='MOVING', depth=5.002 )

    Add_thread( material='signal', label='Passing floor( floor: 2)', from_string='TRANS', to_string='Cabin: S1', depth=8.000 )
    Add_bead( material='state', string='Cabin: S1', bead_color='Update location', depth=8.001 )
    Add_thread( material='signal', label='Passing floor( floor: 2)', from_string='Cabin: S1', to_string='UI' )
    Add_bead( material='state', string='Cabin: S1', bead_color='MOVING', depth=8.002 )

    Add_thread( material='signal', label='Passing floor( floor: 3)', from_string='TRANS', to_string='Cabin: S1', depth=11.000 )
    Add_bead( material='state', string='Cabin: S1', bead_color='Update location', depth=11.001 )
    Add_thread( material='signal', label='Passing floor( floor: 3)', from_string='Cabin: S1', to_string='UI' )
    Add_bead( material='state', string='Cabin: S1', bead_color='MOVING', depth=11.002 )

    Add_thread( material='signal', label='Arrived at floor', from_string='TRANS', to_string='Cabin: S1', depth=15.000 )
    Add_bead( material='state', string='Cabin: S1', bead_color='PICKUP DROPOFF', depth=15.001 )
    Add_thread( material='signal', label='Unlock', from_string='Cabin: S1', to_string='Door: S1' )
    Add_thread( material='signal', label='Cabin at destination', from_string='Cabin: S1', to_string='Transfer: S1-3' )

    Add_bead( material='state', string='Door: S1', bead_color='OPENING', depth=15.002 )
    Add_bead( material='state', string='Transfer: S1-3', bead_color='Cabin at destination', depth=15.002 )

Here's something new. Two Threads projecting from the same Bead (right face). We should evenly space them with
knots set to +1 and -1:

    Add_string( material='external', name='SIO' )
    Add_thread( material='implicit event', label='Door opening', from_string='Door: S1', to_string='UI' )
    Add_thread( material='implicit event', label='Door opening', from_string='Door: S1', to_string='SIO' )
    Add_thread( material='signal', label='Door opened', from_string='SIO', to_string='Door: S1', depth=18.000 )
    Add_bead( material='state', string='Door: S1', bead_color='OPEN', depth=18.001 )
    Add_thread( material='implicit event', label='Door opened', from_string='Door: S1', to_string='UI' )

    Add_bead( material='state', string='Transfer: S1-3', bead_color='Check for cabin reversal', depth=15.003 )
    Add_bead( material='state', string='Transfer: S1-3', bead_color='Check for active floor service', depth=15.004 )
    Add_thread( material='signal', label='Stop serviced', from_string='Transfer: S1-3', to_string='ASLEV: S1-3' )
    Add_thread( material='signal', label='Cabin arrived( shaft:S1, direction: up )', from_string='Transfer: S1-3', to_string='ASLEV: S1-3' )
    Add_bead( material='state', string='Transfer: S1-3', bead_color='WAITING FOR REQUESTS TO CLEAR', depth=15.005 )

    Add_bead( material='state', string='ASLEV: S1-3', bead_color='Clear stop request', depth=15.005 )
    Add_thread( material='implicit event', label='Clear stop request', from_string='ASLEV: S1-3', to_string='UI' )
    Add_bead( material='state', string='ASLEV: S1-3', bead_color='NOT REQUESTED', depth=15.006 )
    Add_thread( material='signal', label='Requests cleared', from_string='ASLEV: S1-3', to_string='Transfer: S1-3' )

    Add_bead( material='state', string='Transfer: S1-3', bead_color='Delete', depth=15.007 )
    Add_thread( material='signal', label='Transfer completed', from_string='Transfer: S1-3', to_string='R53 / Shaft' )

Here we put the lower boundary on the bounded String:

    End_string( string='Transfer: S1-3' )

    Add_bead( material='state', string='ASLEV: S1-3', bead_color='Search for new destination', depth=15.008 )
    Add_bead( material='state', string='ASLEV: S1-3', bead_color='NO TRANSFER', depth=15.015 )

We get this command when all the input has been sent:

    End_diagram( )

At this point we can resolve all placements and begin rendering the diagram using TabletSVG.
