# Model Debugger (MDB) interaction — the Sequence Diagram adapter

This describes how a client (the model debugger, **mdb**, or any other) drives Sequins using
*sequence-diagram* vocabulary — actors, signals, states — and how the **Sequence Diagram
adapter** (`SequenceDiagramAdapter`) translates that into the layout-engine commands tested in
`layout_engine_api.md`. It also covers **interactive incremental rendering**: emitting an
intermediate SVG as the scenario is built, before `end_diagram` arrives.

## Layering

```
client (mdb) ──▶ SequenceDiagramAdapter ──▶ LayoutEngine ──▶ TabletSVG
                 (sequence-diagram verbs)    (diagram-agnostic)
```

The adapter is a **thin, stateless translator**. It owns the sequence-diagram vocabulary and
the *cadence* of interactive rendering; it holds no buffered scenario state of its own. The
layout engine stays diagram-agnostic — it never learns what an "actor" is.

## Two interaction modes

1. **Fully interactive.** The mdb makes live calls as the user steps through a scenario. An
   intermediate SVG is regenerated after each step so the user can watch the diagram build up,
   well before the scenario completes.
2. **File input.** The whole command stream is replayed at once; nothing is drawn until
   `end_diagram`.

## Command vocabulary and translation

| client verb | layout-engine command |
| --- | --- |
| `start_diagram(theme)` | `start_diagram(theme)` *(pass-through)* |
| `add_actor(name, initial_state=None, born_and_die=False)` | `add_string(material=…, name, bead_color=initial_state)` |
| `state_entered(actor, state, time)` | `add_bead(material='state', string=actor, bead_color=state, depth=time)` |
| `signal(source_actor, dest_actor, name, time=None)` | `add_thread(material='signal', label=name, from_string=source, to_string=dest, depth=time)` |
| `implicit_event(source_actor, dest_actor, name, time=None)` | `add_thread(material='implicit event', label=name, from_string=source, to_string=dest, depth=time)` |
| `actor_deleted(actor)` | `end_string(string=actor)` |
| `end_diagram()` | `end_diagram()` *(pass-through)* |

`start_diagram` and `end_diagram` pass straight through; everything between translates.
`time` maps directly to `depth` (`None` is allowed — a beaded source takes its depth from its
projecting bead, so only bare-string sources actually need it).

### Material inference (in `add_actor`)

The client never names a String *material*; the adapter infers it. Order matters — the
`born_and_die` flag wins over the presence of an initial state:

```
if born_and_die:        material = 'born and die'    # beaded, bounded
elif initial_state:     material = 'persistent'       # beaded, unbounded
else:                   material = 'external'          # bare (no beads)
```

This is semantically sound, not just a heuristic: in Shlaer-Mellor a modeled instance always
*has* a current state (the mdb can always supply one when it introduces the actor), whereas an
external entity has no state machine and never can. So "no `initial_state` ⇒ external/bare"
falls out of the semantics.

`initial_state` is translated straight to `bead_color`, adding the actor's top bead. Externals
that the theme pins to several positions (e.g. `UI` at both edges) need nothing special — the
engine reads the pin positions from the theme when it sees `material='external'`.

### Implicit events vs signals

An implicit (architecture-generated / polled) event is a genuinely different notation from a
directed signal — dashed line, no explicit emitter intent — so it gets its own verb,
`implicit_event()`, mirroring `signal()`. The mdb knows which it is emitting at the source.

### Actor deletion

A born-and-die actor's deletion is `actor_deleted(actor)`, translating to `end_string`, which
caps the bottom of the bounded String with the death knot. It is only meaningful for a
born-and-die actor; deleting a persistent or external actor is a client error.

## Walkthrough (start of the elevator scenario)

```
start_diagram(theme='elevator')                          → start_diagram(theme='elevator')

add_actor(name='UI')                                     → add_string(material='external', name='UI')
add_actor(name='ASLEV: S1-3', initial_state='NOT REQUESTED')
                                                         → add_string(material='persistent', name='ASLEV: S1-3',
                                                                      bead_color='NOT REQUESTED')

signal(source_actor='UI', dest_actor='ASLEV: S1-3', name='Stop request', time=1.0)
                                                         → add_thread(material='signal', label='Stop request',
                                                                      from_string='UI', to_string='ASLEV: S1-3', depth=1.0)

state_entered(actor='ASLEV: S1-3', state='Registering stop', time=1.001)
                                                         → add_bead(material='state', string='ASLEV: S1-3',
                                                                    bead_color='Registering stop', depth=1.001)
state_entered(actor='ASLEV: S1-3', state='Requesting service', time=1.002)
                                                         → add_bead(... bead_color='Requesting service', depth=1.002)

add_actor(name='R53 / Shaft', initial_state='NO TRANSFER')
signal(source_actor='ASLEV: S1-3', dest_actor='R53 / Shaft', name='Service requested')
state_entered(actor='ASLEV: S1-3', state='REQUESTED', time=1.003)
state_entered(actor='R53 / Shaft', state='Search for new destination', time=1.003)

add_actor(name='Transfer: S1-3', born_and_die=True)      → add_string(material='born and die', name='Transfer: S1-3')
signal(source_actor='R53 / Shaft', dest_actor='Transfer: S1-3', name='Execute')
                                                         → add_thread(material='signal', label='Execute',
                                                                      from_string='R53 / Shaft', to_string='Transfer: S1-3')
state_entered(actor='Transfer: S1-3', state='WAITING FOR CABIN', time=1.004)
…
end_diagram()                                            → end_diagram()
```

The remaining commands follow the same patterns as `layout_engine_api.md`.

## Interactive incremental rendering

Today the pipeline is lazy and terminal: `end_diagram` runs the layout pass, which fills the
curtain objects with computed geometry *in place*. To render mid-stream and keep accepting
commands, we must not re-resolve those same objects (some passes are not idempotent — e.g.
fanning adds an offset to a thread endpoint).

### Snapshot mechanism

> **snapshot** = *project* the live population to its drawable subset → *deep-copy* that subset
> (sharing the immutable theme / material reference objects) → *resolve* the copy → *render* it.

- The population graph stays a **pure, append-only log** of the client's trace; no layout pass
  ever mutates it.
- Each snapshot resolves a **throwaway copy**, so the in-place-mutating layout pass never has an
  idempotency problem.
- The reference data (Diagram Theme, Materials, String Positions) is immutable, so the copy
  shares it rather than duplicating it.

### Born-and-die birth gate (the projection)

A born-and-die String is **born** ⇔ it has **at least one incoming thread** *and* **at least
one bead**:

- the *first incoming thread* fixes its birth depth (a born-and-die String has no depth-0 top
  and no explicit depth — the mdb guarantees such an instance is always created by an incoming
  signal);
- the *first bead* gives it vertical extent (zero beads ⇒ a degenerate zero-height stub).

Until a born-and-die String is born it is **hidden, along with every thread incident to it**.
This is enforced by the **snapshot projection**, not the adapter and not the core layout pass —
so the adapter stays a thin translator and the population stays a faithful log. Dropping the
unborn String also drops its incoming creation thread, so the String and its creation signal
**appear together** in the first frame where both birth conditions hold. At `end_diagram` every
born-and-die String is long since born, so the projection is a no-op for the final render.

Persistent and external Strings are born on arrival (a persistent actor always arrives with its
`initial_state` bead; an external needs no beads), so the gate only ever affects born-and-die.

### Cadence and output

- **Interactive mode:** snapshot after every verb except `start_diagram`, overwriting a single
  live file. (The birth gate decides whether anything actually appears; a born-and-die
  `add_actor` produces no visible change until birth.) A viewer kept open on the live file
  auto-reloads on each write.
- **File-input mode:** no intermediate snapshots; render once at `end_diagram`.

Intermediate frames **reflow** as the diagram grows (Strings shift, spans widen, the canvas
grows), since placement is relative and resolved globally. This is accepted for a debug
watch-along; stable / absolute placement is deferred.

### Known implementation risk

The layout pass must tolerate **partial** diagrams. The projection removes the main offender
(unborn born-and-die Strings), but a snapshot can still present, say, a beaded String carrying
only its initial bead. Snapshot resolution must not assume a complete scenario.
