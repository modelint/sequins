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
