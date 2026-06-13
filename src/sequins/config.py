"""Configuration loading -- turns the four ``configuration/*.yaml`` files into the
immutable ``theme`` value objects.

Loading goes through ``mi_config.Config`` (the same mechanism Tablet and Flatland use): on
first run it seeds ``~/.config/sequins/`` from the in-repo ``configuration/`` directory and
thereafter reads the user's copy, so end users can override the shipped defaults.  We load
each file as a raw dict (``nt_type=None``) and shape it here, because our files nest beyond
what ``Config``'s flat namedtuple path handles.
"""
from __future__ import annotations

from pathlib import Path

from mi_config.config import Config

from sequins.geometry import Padding, RectSize
from sequins.theme import (
    BeadMaterial,
    Canvas,
    CurtainStyle,
    DiagramTheme,
    Layout,
    StringMaterial,
    StringPosition,
    StringSetting,
    ThreadMaterial,
)

#: The in-repo seed/fallback library (sibling of the package: ``src/configuration``).
DEFAULT_CONFIG_DIR = Path(__file__).resolve().parent.parent / "configuration"

#: Config files we load, in dependency order; None == load as a raw dict, shaped below.
_FILES = {"canvas": None, "layout": None, "curtain_style": None, "diagram_theme": None}


def load_themes(config_dir: Path | None = None) -> dict[str, DiagramTheme]:
    """Load every Diagram Theme, keyed by name (always includes ``default``)."""
    cfg = Config(
        app_name="sequins",
        lib_config_dir=config_dir or DEFAULT_CONFIG_DIR,
        fspec=_FILES,
        ext="yaml",
    )
    raw = cfg.loaded_data
    canvases = _canvases(raw["canvas"])
    layouts = _layouts(raw["layout"])
    styles = _curtain_styles(raw["curtain_style"])
    return _themes(raw["diagram_theme"], canvases, layouts, styles)


def _canvases(d: dict) -> dict[str, Canvas]:
    return {
        name: Canvas(
            name=name,
            background_color=v["color"],
            padding=Padding(top=v["top"], bottom=v["bottom"], left=v["left"], right=v["right"]),
        )
        for name, v in d.items()
    }


def _layouts(d: dict) -> dict[str, Layout]:
    return {
        name: Layout(
            name=name,
            string_top_gutter=v["string top gutter"],
            string_bottom_gutter=v["string bottom gutter"],
            min_bead_separation=v["min bead separation"],
            min_string_span=v["min string span"],
            min_bead_size=RectSize(**v["min bead size"]),
            min_thread_separation=v["min thread separation"],
        )
        for name, v in d.items()
    }


def _curtain_styles(d: dict) -> dict[str, CurtainStyle]:
    styles: dict[str, CurtainStyle] = {}
    for name, v in d.items():
        mats = v["materials"]
        string_materials = {
            n: StringMaterial(
                name=n,
                beaded=sm["beaded"],
                top_end=(sm["bounded"] or {}).get("top") if sm["bounded"] else None,
                bottom_end=(sm["bounded"] or {}).get("bottom") if sm["bounded"] else None,
            )
            for n, sm in mats["strings"].items()
        }
        bead_materials = {
            n: BeadMaterial(
                name=n,
                min_size=RectSize(**bm["min size"]),
                standard_size=RectSize(**bm["standard size"]),
            )
            for n, bm in mats["beads"].items()
        }
        thread_materials = {
            n: ThreadMaterial(name=n, arrow_asset=asset) for n, asset in mats["threads"].items()
        }
        styles[name] = CurtainStyle(
            name=name,
            string_materials=string_materials,
            bead_materials=bead_materials,
            thread_materials=thread_materials,
        )
    return styles


def _themes(
    d: dict,
    canvases: dict[str, Canvas],
    layouts: dict[str, Layout],
    styles: dict[str, CurtainStyle],
) -> dict[str, DiagramTheme]:
    themes: dict[str, DiagramTheme] = {}
    for name, v in d.items():
        settings = {
            sname: StringSetting(
                name=sname,
                color=sv.get("color"),
                positions=_parse_positions(sv.get("positions", "")),
            )
            for sname, sv in v.get("string layout", {}).items()
        }
        themes[name] = DiagramTheme(
            name=name,
            canvas=canvases[v["canvas"]],
            layout=layouts[v["layout"]],
            curtain_style=styles[v["curtain style"]],
            string_settings=settings,
        )
    return themes


def _parse_positions(spec: str) -> tuple[StringPosition, ...]:
    """Parse a positions string like ``"L, R"`` or ``"R-2"`` into StringPositions.

    A token is a boundary letter (L/R) and an optional ``-N`` offset inward from that edge
    (the ``-`` is a separator, not a minus). Bare ``L`` means offset 0 (the edge itself).
    """
    out: list[StringPosition] = []
    for token in (t.strip() for t in spec.split(",")):
        if not token:
            continue
        boundary = token[0].upper()
        digits = token[1:].lstrip("-")
        out.append(StringPosition(boundary=boundary, offset=int(digits) if digits else 0))
    return tuple(out)
