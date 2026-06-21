## Sequins

No more ugly sequence diagrams!

At last, you can generate well organized, highly readable, and aesthetically pleasing sequence diagrams from
human readable text input.

Sequins is a model diagram layout engine that takes model semantic input as text and outputs svg.
You can display the svg in your browser, previewer or have Sequins produce pdf output.

The problem with many sequence diagram tools and generators is that the layout is difficult to manage,
especially with complex or large scenarios. You typically have to put up with whatever the tools decides
is acceptable. And often this is difficult to follow and really ugly.

I built Sequins for the following reasons:

- Accept text input so that you never actually draw anything and can easily edit the input (like all of my other tools)
- Let the user influence the layout when desired, don't rely 100% on layout algorithms or AI
- It's difficult to analyze a scenario and find potential errors when you have to dig through lots of overlapping lines, or when it is difficult to find the actors, states, or interactions of interest. So you want your layout to make it as easy as possible to understand what's going on in your scenario.
- Beautiful presentation for stakeholders. Rather than just looking at boxes, lines, and text, you can dress up your diagrams with icons, colors, and annotations.
- No more ugly sequence diagrams.  You can define your own themes and color schemes.
- Support a wide variety of open standards including SysML V2 and UML as well as proprietary standards so that you can incorporate Sequins alongside whatever tooling your organization is using.

### Concept

Whereas my other project, [Flatland](https://github.com/modelint/flatland/wiki), applies a spreadsheet metaphor to specify the layout of nodes and connectors across a canvas,
Sequins manages beads on vertically hanging strings connected with threads connecting the beads and strings horizontally. So basically,
a bead curtain metaphor.

In both projects I employ a metaphor to completely separate the modeling semantic rules and standards
from the geometric layout. That way you never, ever, mix visual layout into your models. You can change layouts
without ever affecting your models and even use multiple layouts to view the same model input.

## Installation

Sequins is published to PyPI as **`mi-sequins`**:

```bash
pip install mi-sequins
```

Requires Python ≥ 3.12. Its dependencies — `mi-tabletsvg` (the SVG renderer),
`mi-configurator`, and `PyYAML` — are installed automatically.

On first use, Sequins seeds its theme configuration into `~/.config/sequins/`
(canvas, layout, curtain styles, diagram themes), and `mi-tabletsvg` seeds its own
notation/presentation configuration into `~/.config/mi_tablet/`. Edit those YAML files to
customize themes, colors, and notation; delete a file to have it re-seeded from the
shipped defaults.

## Driving Sequins from your application

A client — such as a model debugger — builds a diagram by calling the **Sequence Diagram
adapter** in sequence-diagram vocabulary (actors, signals, states). The adapter translates
those calls into the layout engine and renders the result (SVG, or PDF — the format follows
the output file's suffix). The import package is `sequins` (the PyPI distribution is
`mi-sequins`):

```python
from sequins.sd_adapter import SequenceDiagramAdapter

sd = SequenceDiagramAdapter("scenario.svg")                    # output path (.pdf also works)
sd.start_diagram(theme="elevator")

sd.add_actor("UI")                                             # external entity (no state machine)
sd.add_actor("ASLEV: S1-3", initial_state="NOT REQUESTED")    # modeled instance
sd.signal("UI", "ASLEV: S1-3", "Stop request", time=1.0)
sd.state_entered("ASLEV: S1-3", "Registering stop", time=1.001)
# ... more actors / signals / states ...

sd.end_diagram()                                              # resolves layout and writes scenario.svg
```

In the default (file-input) mode nothing is drawn until `end_diagram()`.

### Watching a scenario build (interactive mode)

When a user is stepping through a scenario, pass `interactive=True` and the output file is
re-rendered after every command, so a viewer kept open on it shows the diagram grow:

```python
sd = SequenceDiagramAdapter("live.svg", interactive=True)
# ... same calls; live.svg is rewritten after each verb ...
sd.end_diagram()
```

### Command reference

| verb | meaning |
| --- | --- |
| `start_diagram(theme="default")` | begin a diagram under a named theme |
| `add_actor(name, initial_state=None, born_and_die=False)` | introduce an actor (see *Actor kinds*) |
| `state_entered(actor, state, time)` | an actor enters a state (`time` = chronological position) |
| `signal(source_actor, dest_actor, name, time=None)` | a directed signal between actors |
| `implicit_event(source_actor, dest_actor, name, time=None)` | an architecture-generated (implicit) event |
| `actor_deleted(actor)` | delete a born-and-die actor (caps its lifeline) |
| `end_diagram()` | resolve and render the final diagram; returns the output `Path` |

### Actor kinds

The actor's kind is inferred from `add_actor` — you never name an internal material:

- **External entity** (no `initial_state`) — e.g. `UI`, a sensor, an external system. Drawn
  as a bare lifeline with no states.
- **Persistent instance** (`initial_state="…"`) — a modeled instance with a state machine;
  its initial state becomes its first bead.
- **Born-and-die instance** (`born_and_die=True`) — created and deleted within the scenario.
  It must *not* carry an `initial_state`; it stays hidden until its creation signal arrives
  *and* it enters its first state, then `actor_deleted` caps it off.

`time` expresses the scenario's chronological ordering. The layout engine compresses spacing
while preserving order, so exact magnitudes don't matter — only the sequence.

### Themes

`theme=` selects a Diagram Theme from `~/.config/sequins/diagram_theme.yaml` (falling back to
`default` if the name isn't found). A theme bundles a canvas, a layout (spacing rules), a
curtain style (the notation vocabulary), and per-actor settings such as edge placement and
color. Add your own themes there.
