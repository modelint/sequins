"""The layout-engine facade -- the public command API.

These methods are the function-call surface described in
``documentation/architecture/layout_engine_api.md`` (the spec's ``Start_diagram`` etc. map
to the snake_case methods here).  They *populate* the curtain metamodel and nothing more:
per the lazy-resolution contract, no geometry is computed and nothing is drawn until
``end_diagram``, which will later drive the layout pass and TabletSVG.
"""
from __future__ import annotations

import copy
from pathlib import Path

from sequins.config import load_themes
from sequins.curtain import Bead, CurtainDiagram, String, Thread
from sequins.layout import Layout
from sequins.theme import BeadMaterial, DiagramTheme


class LayoutEngine:
    """Builds one Curtain Diagram from a stream of Add_* commands."""

    def __init__(self, config_dir: Path | None = None):
        self._themes: dict[str, DiagramTheme] = load_themes(config_dir)
        self.diagram: CurtainDiagram | None = None

    # ------------------------------------------------------------------ commands
    def start_diagram(self, theme: str = "default") -> None:
        """Begin a diagram under the named theme, falling back to ``default``."""
        resolved = self._themes.get(theme) or self._themes["default"]
        self.diagram = CurtainDiagram(theme=resolved, compressed=True)

    def add_string(self, material: str, name: str, bead_color: str | None = None) -> None:
        """Create the String(s) for ``name``.

        A theme that pins ``name`` to several positions (e.g. UI at L and R) yields one
        String per position; otherwise a single interior String. ``bead_color`` adds a top
        bead at depth 0 (only meaningful for a beaded material)."""
        d = self._require_diagram()
        style = d.theme.curtain_style
        string_material = style.string_material(material)
        setting = d.theme.setting_for(name)
        pins = list(setting.positions) if setting and setting.positions else [None]
        color = setting.color if setting else None

        for pin in pins:
            s = String(name=name, material=string_material, color=color, pinned=pin)
            if bead_color is not None:
                s.beads.append(
                    Bead(string=s, color_name=bead_color, material=self._top_bead_material(d), depth=0.0)
                )
            d.strings.append(s)

    def add_bead(self, material: str, string: str, bead_color: str, depth: float) -> None:
        """Adorn a beaded String with a state bead at ``depth``."""
        d = self._require_diagram()
        s = self._unique_string(d, string)
        bead_material = d.theme.curtain_style.bead_material(material)
        s.beads.append(Bead(string=s, color_name=bead_color, material=bead_material, depth=depth))

    def add_thread(
        self,
        material: str,
        label: str,
        from_string: str,
        to_string: str,
        depth: float | None = None,
    ) -> None:
        """Connect two Strings with an interaction.

        ``depth`` is supplied only when the origin is a bare String; from a beaded String
        the depth is taken from its projecting bead at layout time. Endpoints that resolve
        to a single String are bound now; multi-position endpoints stay unbound for the
        layout pass to pick by distance."""
        d = self._require_diagram()
        thread_material = d.theme.curtain_style.thread_material(material)
        from_str = self._bind(d, from_string)
        to_str = self._bind(d, to_string)
        # R26: a beaded origin projects from the lowest bead present *now* (issue time) --
        # creation-order knowledge that can't be recovered from depths at end_diagram.
        source_bead = (
            from_str.beads[-1]
            if from_str is not None and from_str.beaded and from_str.beads
            else None
        )
        d.threads.append(
            Thread(
                from_name=from_string,
                to_name=to_string,
                material=thread_material,
                label=label,
                depth=depth,
                from_string=from_str,
                to_string=to_str,
                source_bead=source_bead,
            )
        )

    def end_string(self, string: str) -> None:
        """Cap the bottom of a bounded String (its lower boundary / knot)."""
        self._unique_string(self._require_diagram(), string).lower_bounded = True

    def end_diagram(self) -> CurtainDiagram:
        """Signal that all input has arrived; resolve geometry and return the diagram.

        Resolves the canonical population *in place* and returns it -- the terminal call.
        For an intermediate frame during population use :meth:`render`, which never touches
        the canonical diagram."""
        return Layout(self._require_diagram()).resolve()

    def render(self, output_file: str | Path) -> Path:
        """Draw the *current* population to ``output_file`` and return the path.

        This is the interactive-snapshot entry point: it can be called any number of times
        while commands are still arriving. The canonical population stays a pure,
        append-only log -- a throwaway *copy* is projected to its drawable subset, resolved,
        and rendered, so the in-place-mutating layout pass never re-runs on live objects.
        Must be called before :meth:`end_diagram` (which resolves the canonical in place)."""
        from sequins.render import render as render_diagram  # lazy: keeps TabletSVG out of
        #                                                       population/layout-only tests

        snapshot = self._drawable_snapshot(self._require_diagram())
        Layout(snapshot).resolve()
        return render_diagram(snapshot, output_file)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _drawable_snapshot(d: CurtainDiagram) -> CurtainDiagram:
        """A fresh, resolvable copy of ``d`` holding only its currently-drawable elements.

        The mutable String/Bead/Thread graph is deep-copied; the immutable reference data
        (theme, materials, string positions) is *shared* via a pre-seeded memo so it isn't
        duplicated and is never mutated. Unborn born-and-die Strings -- and every thread
        incident to them -- are dropped (the birth gate, see ``mdb_interaction.md``)."""
        memo: dict[int, object] = {id(d.theme): d.theme}
        for s in d.strings:
            memo[id(s.material)] = s.material
            if s.pinned is not None:
                memo[id(s.pinned)] = s.pinned
            for b in s.beads:
                memo[id(b.material)] = b.material
        for t in d.threads:
            memo[id(t.material)] = t.material
        snap = copy.deepcopy(d, memo)

        # Born-and-die == beaded & bounded. It is born once it has an incoming thread (sets
        # its birth depth) and at least one bead (gives it extent); until then, hide it.
        unborn = {
            id(s)
            for s in snap.strings
            if s.beaded and s.bounded
            and not (s.beads and any(t.to_string is s for t in snap.threads))
        }
        if unborn:
            snap.threads = [
                t for t in snap.threads
                if id(t.from_string) not in unborn and id(t.to_string) not in unborn
            ]
            snap.strings = [s for s in snap.strings if id(s) not in unborn]
        return snap
    def _require_diagram(self) -> CurtainDiagram:
        if self.diagram is None:
            raise RuntimeError("start_diagram must be called before any other command")
        return self.diagram

    def _unique_string(self, d: CurtainDiagram, name: str) -> String:
        """Resolve a name expected to denote exactly one String (beaded/bounded targets)."""
        matches = d.strings_named(name)
        if len(matches) != 1:
            raise ValueError(f"expected exactly one String named {name!r}, found {len(matches)}")
        return matches[0]

    def _bind(self, d: CurtainDiagram, name: str) -> String | None:
        """Bind a thread endpoint: the String if unique, None if multi-position (deferred)."""
        matches = d.strings_named(name)
        if not matches:
            raise ValueError(f"Thread references unknown String {name!r} -- Add_string it first")
        return matches[0] if len(matches) == 1 else None

    def _top_bead_material(self, d: CurtainDiagram) -> BeadMaterial:
        """The bead material for an Add_string top bead.

        Add_string carries no bead material, so we use the curtain style's sole bead
        material (sequence diagrams define just ``state``)."""
        materials = list(d.theme.curtain_style.bead_materials.values())
        if len(materials) != 1:
            raise ValueError("a top bead needs an explicit material when the style has several")
        return materials[0]
