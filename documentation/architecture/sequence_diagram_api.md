## Seq Diagram API

The Sequins Diagram Layout domain does not include any semantics specific to a sequence diagramming.

So we need a thin layer in our application to mediate between the two. Imagine the top layer as the _sequence diagram interface_ which feeds our _layout engine_.

The sequence diagram interface will translate sequence diagramming terminology to corresponding layout commands.

Input to the sequence diagramming layer for our elevator example might look like this:

    Start sequence diagram( client=‘mdb’, theme=‘elevator’ )

This initial command give us two keys we use to locate a Diagram Theme in the `diagram_themes.yaml` file.
If found, we use it. If not, we set the default theme. Next we compute the Curtain Diagram.Origin, Size and Rod Height with Compressed set to the default (True)

    Add actor( type=internal, actor=‘ASLEV: S1’, state=‘NOT REQUESTED’, time=0)

We translate this next command into a layout command:

    Create beaded string( name=‘ASLEV: S1’, top bead=‘NOT REQUESTED’, absolute depth=0 )

Note that a beaded string is created with an initial bead since, in the sequence diagramming semantics, an internal actor always starts off with a state. This is a modeling rule not modeled in the Sequins domain. The layout engine lets us specify an optional top bead.

We will need a linear function to translate time to depth values as well as a way of representing the time value. For now assume that time is expressed in seconds such as 0.0 s or 23.4 s.  All sequence diagrams will provide a time value with each new bead.

Here's a similar command pair:

    Add actor( type=internal, actor=‘R53 / Shaft’, state=‘NO TRANSFER’ )
    Create beaded string( name=‘R53 / Shaft’, top bead=‘ASLEV: S1’ )

Now a signal is emitted:

    Add signal( name=‘Stop request’, from=‘UI’, to=‘ASLEV: S1-3’)
Since the corresponding string is

Add state( name=‘Registering stop’, actor=‘ASLEV:S1-3’)
Add state( name=‘Requesting service’, actor=‘ASLEV:S1-3’)
Add signal( name=‘Service requested’, from=‘ASLEV: S1-3’, to=‘R53 / Shaft’)
Add state( name=’Search for new destination’, actor=‘R53 / Shaft’)
Add state( name=‘REQUESTED’, actor=‘ASLEV: S1-3’)
Add create signal( name=‘Execute’, from=‘R53 / Shaft’, to=‘Transfer: S1-3’)
