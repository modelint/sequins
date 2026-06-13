# Modeling / Wiki update for the modeling agent

From a review of the desired output (`documentation/mint.sequins.tn.2.svg/.png`) against the model.

## String Color overrides threads at BOTH ends (not just emanating)

**Decision (Leon, diagram is authoritative):** a `String Color` override colors every `Thread`
**connected to that string at either endpoint** — incoming *and* outgoing — not only the threads
emanating *from* it.

Evidence in the reference diagram: threads *to* UI (`Set destination`, `Passing floor`) are
green like UI; the thread *to* TRANS (`Go to floor`) is blue like TRANS; the thread *to* SIO
(`Door opening`) is magenta like SIO — i.e. the colored endpoint wins regardless of direction.

**Wording to fix (currently says "emanating", which is too narrow):**
- Wiki **String Color** page — "any Threads emanating from the String" → threads connected at
  *either* end (in or out).
- Wiki **R23** page — "the color shared by the String and its emanating Threads" → same broadening.
- (Also queued on the code side: the API note in `documentation/architecture/layout_engine_api.md`
  near the first `Add_thread` only mentions a *from*-UI thread; will be generalized on the doc pass.)

**Open question for Leon (not exercised by this example):** when a single Thread connects *two*
String-Colored strings, which color wins? Needs a tie-break rule before this is fully specified.
