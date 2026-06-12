## Layout Engine API

Here we will walk through the layout engine commands necessary to start the elevator example:

    Create_curtain_diagram( client='mdb', theme='elevator' )

This initial command give us two keys we use to locate a Diagram Theme in the `diagram_themes.yaml` file.
If found, we use it. If not, we set the default theme. Next we compute the Curtain Diagram.Origin, Size and Rod Height with Compressed set to the default (True)

    Create_string( name=‘ASLEV: S1-3’, bead=‘NOT REQUESTED’ )

Here we create our first String instance. Since a top bead is specified, we know that the absolute depth of that bead must be zero. We also know that this must be a Beaded String. This command creates an unbounded string by default. The string name is not found in the Diagram Theme, so we aren't applying any String Settings.  We set the position of that String to 1 computing all coordinate values.

We aren't going to attempt to draw anything until we get a render diagram command, so we are free to move beads and strings around as necessary as the create commands arrive.

And whenever a new bead is specified we check for an existing Bead Color, if not found, create a new one. So in this case, we'll create a new instance of Bead Color named 'NOT REQUESTED'.

    Create_string( name='UI', beaded=False )

We look for the name in the Curtain Diagram's theme, find it and create two instances of Bare String because two positions are specified in the mdb's elevator theme and the beaded parameter is false. Both are unbounded by default.

Note that the position of the initial Beaded String moves from 1 to 2.

    Add_thread( material=‘signal',  label='Stop request', from=‘UI’, to=‘ASLEV: S1-3’, depth=1.0 )

The from string is a Bare String, so we need to create a Thread from Bare String instance and connected it below the 
lowest Bead in the target Beaded String, which happens to be 'NOT REQUESTED'. Since a String Color is specified for the UI string in the Diagram Theme, the Thread will match its color.

    Add_bead( string='ASLEV: S1-3’, bead_color='Registering stop', depth=1.001 )

Note the very small depth increment. Since it is so small it will have no effect on vertical spacing either in absolute or compressed mode since the combined Layout attributes will yield the actual spacing.

    Create_string( name=‘R53 / Shaft’, bead=‘NO TRANSFER' )

Nothing new here, process like the previous similar command. This gives us another Beaded String at position 3. And since no depth is specified, assume it is 0, i.e. top of the String.

    Add_thread( material=‘signal', label='Service requested', from=‘ASLEV: S1-3’, to=‘R53 / Shaft’ )

Since the source is a Beaded String, the thread is projected from the face of the lowest Bead on that String which will be Bead with Sequence 3.

Here the from string is

    Add_bead( string='ASLEV: S1-3’, bead_color='REQUESTED', depth=1.003 )
    Add_bead( string=‘R53 / Shaft’, bead_color='Search for new destination', depth=1.003 )
    


Add create signal( name=‘Execute’, from=‘R53 / Shaft’, to=‘Transfer: S1-3’)
