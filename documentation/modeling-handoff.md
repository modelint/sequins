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
- (The code-side API note in `documentation/architecture/layout_engine_api.md` was already
  generalized in the tightening pass.)

**Tie-break (resolved, Leon):** when a single Thread connects *two* String-Colored strings, the
override reverts to the **emanate-only** policy — the **source (`from`) string's** color wins.
This can't arise in the elevator example (only *bare* strings are overridden today, and there is
no bare→bare threading); it becomes possible once a *beaded* string is overridden and threads to
another colored string. So document the rule as: a Thread takes the color of a String-Colored
string at *either* end; if *both* ends are colored, the source string's color is used.
