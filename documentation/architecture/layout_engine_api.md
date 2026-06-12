## Layout Engine API

Here we will walk through the layout engine commands necessary to start the elevator example:

    Start_diagram( client='mdb', theme='elevator' )

This initial command give us two keys we use to locate a Diagram Theme in the `diagram_themes.yaml` file.
If found, we use it. If not, we set the default theme. Next we compute the Curtain Diagram.Origin, Size and Rod Height with Compressed set to the default (True)

    Add_string( material='persistent', name=‘ASLEV: S1-3', bead=‘NOT REQUESTED' )

Here we create our first String instance. Since a top bead is specified, we know that the absolute depth of that bead must be zero. We also know that this must be a Beaded String. This command creates an unbounded string by default. The string name is not found in the Diagram Theme, so we aren't applying any String Settings.  We set the position of that String to 1 computing all coordinate values.

We aren't going to attempt to draw anything until we get a render diagram command, so we are free to move beads and strings around as necessary as the create commands arrive.

And whenever a new bead is specified we check for an existing Bead Color, if not found, create a new one. So in this case, we'll create a new instance of Bead Color named 'NOT REQUESTED'.

    Add_string( material='external', name='UI', beaded=False )

We look for the name in the Curtain Diagram's theme, find it and create two instances of Bare String because two positions are specified in the mdb's elevator theme and the beaded parameter is false. Both are unbounded by default.

Note that the position of the initial Beaded String moves from 1 to 2.

    Add_thread( material=‘signal', label='Stop request', from=‘UI', to=‘ASLEV: S1-3', depth=1.0 )

The from string is a Bare String, so we need to create a Thread from Bare String instance and connected it below the 
lowest Bead in the target Beaded String, which happens to be 'NOT REQUESTED'. Since a String Color is specified for the UI string in the Diagram Theme, the Thread will match its color.

    Add_bead( material='state', string='ASLEV: S1-3', bead_color='Registering stop', depth=1.001 )
    Add_bead( material='state', string='ASLEV: S1-3', bead_color='Requesting service', depth=1.002 )

Note the very small depth increment. Since it is so small it will have no effect on vertical spacing either in absolute or compressed mode since the combined Layout attributes will yield the actual spacing.

    Add_string( material='persistent', name=‘R53 / Shaft', bead=‘NO TRANSFER' )

Nothing new here, process like the previous similar command. This gives us another Beaded String at position 3. And since no depth is specified, assume it is 0, i.e. top of the String.

    Add_thread( material=‘signal', label='Service requested', from='ASLEV: S1-3', to='R53 / Shaft' )

Since the source is a Beaded String, the thread is projected from the face of the lowest Bead on that String which will be Bead with Sequence 3.

The following commands follow with no addditional features.

    Add_bead( material='state', string='ASLEV: S1-3', bead_color='REQUESTED', depth=1.003 )
    Add_bead( material='state', string=‘R53 / Shaft', bead_color='Search for new destination', depth=1.003 )

And now we have a bounded string. It does not specify a topmost bead and it does not specify a depth. The depth will be determined by the first incoming thread:

    Add_string( material='born and die', name='Transfer: S1-3', bounded=True )

    Add_thread( material=‘signal', label='Execute', from=‘R53 / Shaft', to='Transfer: S1-3' )

The depth of the above Thread is taken from its source Bead and becomes the depth of the target bounded String.

No extra features in these commands:

    Add_bead( material='state', string='Transfer: S1-3', bead_color='WAITING FOR CABIN', depth=1.004 )
    Add_bead( material='state', string=‘R53 / Shaft', bead_color='TRANSFER IN PROGRESS', depth=1.005 )
    Add_thread( material=‘signal', label='Set destination', from=Transfer: S1-3', to='UI' )

The small increments in time are a result of state transitions happening in compute time. They are not waiting on input from the outside world. For this exercise we'll just specify an increment by .001 for each.

The UI String name is present in two positions. To which do we draw the Thread? We draw toward the nearest position which is right most UI position at the moment. But as the diagram widens, the leftmost UI position will actually end up being closer. Another reason why we don't attempt rendering until directed.

    Add_string( material='persistent', string=‘Cabin: S1', bead_color='PICKUP DROPOFF' )
    Add_thread( material=‘signal', label='New transfer', from='Transfer: S1-3', to='Cabin: S1' )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='Are we already there?', depth=1.005 )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='SECURING DOORS', depth=1.006 )
    Add_string( material='persistent', string=‘Door: S1', bead_color='CLOSED' )

    Add_thread( material=‘signal', label='Lock', from=‘Cabin: S1', to='Door: S1' )
    Add_bead( material='state', string=‘Door: S1', bead_color='LOCKED', depth=1.007 )
    Add_thread( material=‘signal', label='Doors secure', from=‘Door: S1', to='Cabin: S1' )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='READY TO GO', depth=1.008 )
    Add_thread( material=‘signal', label='Ready to go', from=‘Cabin: S1', to='Transfer: S1-3' )
    Add_bead( material='state', string='Transfer: S1-3', bead_color='Dispatching cabin', depth=1.009 )
    Add_thread( material=‘signal', label='Go', from=Transfer: S1-3', to='Cabin: S1' )
    Add_bead( material='state', string=‘Transfer: S1-3', bead_color='CABIN IN MOTION', depth=1.010 )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='Requesting transport', depth=1.010 )

    Add_string( material='external', name='TRANS', beaded=False )
    Add_thread( material=‘signal', label='Go to floor( dest floor: 3 )', from=‘Cabin: S1', to='TRANS' )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='MOVING', depth=1.011 )

    Add_thread( material=‘signal', label='Passing floor( floor: 1)', from=‘TRANS', to=‘Cabin: S1', depth=5.000 )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='Update location', depth=5.001 )
    Add_thread( material=‘signal', label='Passing floor( floor: 1)', from=‘Cabin: S1', to='UI' )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='MOVING', depth=5.002 )

    Add_thread( material=‘signal', label='Passing floor( floor: 2)', from=‘TRANS', to=‘Cabin: S1', depth=8.000 )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='Update location', depth=8.001 )
    Add_thread( material=‘signal', label='Passing floor( floor: 2)', from=‘Cabin: S1', to='UI' )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='MOVING', depth=8.002 )

    Add_thread( material=‘signal', label='Passing floor( floor: 3)', from=‘TRANS', to=‘Cabin: S1', depth=11.000 )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='Update location', depth=11.001 )
    Add_thread( material=‘signal', label='Passing floor( floor: 3)', from=‘Cabin: S1', to='UI' )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='MOVING', depth=11.002 )

    Add_thread( material=‘signal', label='Arrived at floor', from=‘TRANS', to='Cabin: S1', depth=15.000 )
    Add_bead( material='state', string=‘Cabin: S1', bead_color='PICKUP DROPOFF', depth=15.001 )
    Add_thread( material=‘signal', label='Unlock', from=‘Cabin: S1', to='Door: S1' )
    Add_thread( material=‘signal', label='Cabin at destination', from=‘Cabin: S1', to='Transfer: S1-3' )

    Add_bead( material='state', string=‘Door: S1', bead_color='OPENING', depth=15.002 )
    Add_bead( material='state', string=‘Transfer: S1-3', bead_color='Cabin at destination', depth=15.002 )

Here's something new. Two Threads projecting from the same Bead (right face). We should evenly space them with
knots set to +1 and -1:

    Add_thread( material=‘implicit event', label='Door opening', from=‘Door: S1', to='UI' )
    Add_thread( material=‘implicit event', label='Door opening', from=‘Door: S1', to='SIO' )
    Add_thread( material=‘signal', label='Door opened', from=‘SIO', to='Door: S1', depth=18.000 )
    Add_bead( material='state', string=‘Door: S1', bead_color='OPEN', depth=18.001 )
    Add_thread( material=‘implicit event', label='Door opened', from=‘Door: S1', to='UI' )

    Add_bead( material='state', string=‘Transfer: S1-3', bead_color='Check for cabin reversal', depth=15.003 )
    Add_bead( material='state', string=‘Transfer: S1-3', bead_color='Check for active floor service', depth=15.004 )
    Add_thread( material=‘signal', label='Stop serviced', from=‘Transfer: S1-3', to='ASLEV: S1-3' )
    Add_thread( material=‘signal', label='Cabin arrived( shaft:S1, direction: up )', from=‘Transfer: S1-3', to='ASLEV: S1-3' )
    Add_bead( material='state', string=‘Transfer: S1-3', bead_color='WAITING FOR REQUESTS TO CLEAR', depth=15.005 )
    
    Add_bead( material='state', string=‘ASLEV: S1-3', bead_color='Clear stop request', depth=15.005 )
    Add_thread( material=‘implicit event', label='Clear stop request', from=‘ASLEV: S1-3', to='UI' )
    Add_bead( material='state', string=‘ASLEV: S1-3', bead_color='NOT REQUESTED', depth=15.006 )
    Add_thread( material=‘signal', label='Requests cleared', from=‘ASLEV: S1-3', to='Transfer: S1-3' )

    Add_bead( material='state', string=‘Transfer: S1-3', bead_color='Delete', depth=15.007 )
    Add_thread( material=‘signal', label='Transfer completed', from='Transfer: S1-3', to='R53 / Shaft' )

Here we put the lower boundary on the bounded String:

    End_string( string=‘Transfer: S1-3' )

    Add_bead( material='state', string=‘ASLEV: S1-3', bead_color='Search for new destination', depth=15.008 )
    Add_bead( material='state', string=‘ASLEV: S1-3', bead_color='NO TRANSFER', depth=15.015 )

We get this command when all the input has been sent:

    End_diagram( )

At this point we can resolve all placements and begin rendering the diagram using TabletSVG.