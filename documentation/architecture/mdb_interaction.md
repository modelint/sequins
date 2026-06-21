## Model Debugger (MDB) interactive input

Here we look at the commands and interaction modes we need to support for the MDB client.

The two modes of interaction we would like to support are:

1. Fully interactive
2. File input

### Fully interactive

Here we want to run the mdb where it makes interactive api calls into sequins. Our design currently supports limited interaction whereby no rendering occurs until an explicit diagram termination call is recieved.  Upon further reflection, it is apparent that the user will want to see the intermediate output especially if they are manually stepping through a scenario.

### Interactive commands

Let's examine the commands specific to defining the elements of a Sequence Diagram.

    new_diagram( theme='elevator' )

This command is already defined for the layout engine, so nothing new here.

One or more new actors can be introduced.

    add_actor( name='UI' )
    add_actor( name='ASLEV: S1-3', initial_state='NOT REQUESTED')

Note that more actors may be introduced later in the scenario.

The sequence diagram adapter (sd adapter) must translate this input into the corresponding layout engine commands:

    add_string( material='persistent', name='UI' )
    add_string( material='persistent', name='ASLEV: S1-3', bead_color='NOT REQUESTED' )

All actors are persistent by default. The name corresponds to a string name. We can translate the initial_state parameter directly to bead_color. 

    signal( source_actor='UI', dest_actor='ASLEV: S1-3', name='Stop request', time=1.0 )

We need to translate the signal command into the corresponding thread invocation.

    add_thread( material='signal', label='Stop request', from_string='UI', to_string='ASLEV: S1-3', depth=1.0 )

Then we have two state transitions:

    state_entered( actor='ASLEV: S1-3', state='Registering stop', time=1.001 )
    state_entered( actor='ASLEV: S1-3', state='Requesting service', time=1.002 )

Which corresponds to:

    add_bead( material='state', string='ASLEV: S1-3', bead_color='Registering stop', depth=1.001 )
    add_bead( material='state', string='ASLEV: S1-3', bead_color='Requesting service', depth=1.002 )

Then more sd commands translated to layout engine commands as before:

    add_actor( name='R53 / Shaft', initial_state='NO TRANSFER')
    signal( source_actor='ASLEV: S1-3', dest_actor='R53 / Shaft', name='Service requested' )

    state_entered( actor='ASLEV: S1-3', state='REQUESTED', time=1.003 )
    state_entered( actor='R53 / Shaft', state='Search for new destination', time=1.003 )

Then more sd commands translated to layout engine commands as before:

    add_actor( name='Transfer: S1-3', born_and_die=True )

The born_and_die parameter defaults to False, but here it is True, so we translate differently from:

    add_string( material='born and die', name='Transfer: S1-3' )

To:

    signal( source_actor='R53 / Shaft', dest_actor='Transfer: S1-3', name='Execute' )

Then:

    state_entered( actor='Transfer: S1-3', state='WAITING FOR CABIN', time=1.004 )
    state_entered( actor='R53 / Shaft', state='TRANSFER IN PROGRESS', time=1.005 )
    signal( source_actor='Transfer: S1-3', dest_actor='UI', name='Set destination' )

We translate similarily to the remaining commands in layout_engine_api.md

We eventually get:

    End_diagram()

Issued directly to the layout engine without any need for translation from the client.




