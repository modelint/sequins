"""The Sequence Diagram adapter -- a client-facing facade over the layout engine.

Translates *sequence-diagram* vocabulary (actors, signals, states) -- the verbs a client
such as the model debugger (mdb) speaks -- into the diagram-agnostic ``LayoutEngine``
commands, and adds interactive incremental rendering. See
``documentation/architecture/mdb_interaction.md`` for the full contract.

The adapter is a thin, stateless translator: it forwards each verb in arrival order and
holds no buffered scenario state of its own. The born-and-die *birth gate* (hiding a
not-yet-created actor) lives in the engine's snapshot projection, not here.
"""
from __future__ import annotations

from pathlib import Path

from sequins.layout_engine import LayoutEngine

# Materials a client actor / interaction maps to (names must match the curtain style).
_PERSISTENT = "persistent"
_EXTERNAL = "external"
_BORN_AND_DIE = "born and die"
_SIGNAL = "signal"
_IMPLICIT_EVENT = "implicit event"
_STATE = "state"


class SequenceDiagramAdapter:
    """Drives a ``LayoutEngine`` from sequence-diagram commands.

    In **interactive** mode an intermediate SVG is (re)written to ``output_file`` after every
    verb except ``start_diagram``, so a client stepping through a scenario can watch the
    diagram build up. In **file-input** mode (the default) nothing is drawn until
    ``end_diagram``.
    """

    def __init__(
        self,
        output_file: str | Path,
        *,
        interactive: bool = False,
        config_dir: Path | None = None,
    ):
        self._engine = LayoutEngine(config_dir)
        self._output_file = Path(output_file)
        self._interactive = interactive

    # ------------------------------------------------------------------ verbs
    def start_diagram(self, theme: str = "default") -> None:
        """Begin a diagram under the named theme (pass-through to the engine)."""
        self._engine.start_diagram(theme=theme)

    def add_actor(
        self,
        name: str,
        initial_state: str | None = None,
        born_and_die: bool = False,
    ) -> None:
        """Introduce an actor as a String, inferring its material.

        ``born_and_die`` wins; else a supplied ``initial_state`` marks a modeled
        (persistent) instance; else an external entity (a bare String). A born-and-die actor
        must not carry an ``initial_state`` -- its first state arrives via ``state_entered``
        after its creation signal."""
        if born_and_die and initial_state is not None:
            raise ValueError(
                f"born-and-die actor {name!r} cannot have an initial_state; its first state "
                "arrives via state_entered after its creation signal"
            )
        material = (
            _BORN_AND_DIE if born_and_die
            else _PERSISTENT if initial_state is not None
            else _EXTERNAL
        )
        self._engine.add_string(material=material, name=name, bead_color=initial_state)
        self._frame()

    def state_entered(self, actor: str, state: str, time: float) -> None:
        """Record an actor entering a state -- a bead at ``time`` depth."""
        self._engine.add_bead(material=_STATE, string=actor, bead_color=state, depth=time)
        self._frame()

    def signal(
        self, source_actor: str, dest_actor: str, name: str, time: float | None = None
    ) -> None:
        """A directed signal from one actor to another -- a signal thread."""
        self._engine.add_thread(
            material=_SIGNAL, label=name,
            from_string=source_actor, to_string=dest_actor, depth=time,
        )
        self._frame()

    def implicit_event(
        self, source_actor: str, dest_actor: str, name: str, time: float | None = None
    ) -> None:
        """An architecture-generated (implicit) event -- a dashed implicit-event thread."""
        self._engine.add_thread(
            material=_IMPLICIT_EVENT, label=name,
            from_string=source_actor, to_string=dest_actor, depth=time,
        )
        self._frame()

    def actor_deleted(self, actor: str) -> None:
        """Delete a born-and-die actor -- cap its String with the death knot."""
        self._require_born_and_die(actor)
        self._engine.end_string(string=actor)
        self._frame()

    def end_diagram(self) -> Path:
        """All input received: render the final, complete diagram. Returns the path."""
        return self._engine.render(self._output_file)

    # ------------------------------------------------------------------ helpers
    def _frame(self) -> None:
        """Write an intermediate frame in interactive mode (a no-op otherwise)."""
        if self._interactive:
            self._engine.render(self._output_file)

    def _require_born_and_die(self, actor: str) -> None:
        matches = self._engine.diagram.strings_named(actor) if self._engine.diagram else []
        if not matches:
            raise ValueError(f"actor_deleted references unknown actor {actor!r}")
        if not all(s.bounded for s in matches):
            raise ValueError(
                f"actor_deleted is only valid for a born-and-die actor, not {actor!r}"
            )
