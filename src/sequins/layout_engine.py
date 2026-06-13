"""The layout-engine facade -- the public command API.

These methods are the function-call surface described in
``documentation/architecture/layout_engine_api.md`` (the spec's ``Start_diagram`` etc. map
to the snake_case methods here).  They *populate* the curtain metamodel and nothing more:
per the lazy-resolution contract, no geometry is computed and nothing is drawn until
``end_diagram``, which will later drive the layout pass and TabletSVG.
"""
from __future__ import annotations

from pathlib import Path

from sequins.config import load_themes
from sequins.curtain import Bead, CurtainDiagram, String, Thread
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
        d.threads.append(
            Thread(
                from_name=from_string,
                to_name=to_string,
                material=thread_material,
                label=label,
                depth=depth,
                from_string=self._bind(d, from_string),
                to_string=self._bind(d, to_string),
            )
        )

    def end_string(self, string: str) -> None:
        """Cap the bottom of a bounded String (its lower boundary / knot)."""
        self._unique_string(self._require_diagram(), string).lower_bounded = True

    def end_diagram(self) -> CurtainDiagram:
        """Signal that all input has arrived; returns the populated diagram.

        Resolution (layout pass, step #3) and rendering (TabletSVG, step #4) hang here."""
        return self._require_diagram()

    # ------------------------------------------------------------------ helpers
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
