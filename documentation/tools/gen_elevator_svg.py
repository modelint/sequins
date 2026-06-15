"""Generate the elevator Curtain Diagram SVG end-to-end.

Runs the full pipeline -- population (the canonical elevator script) -> layout pass ->
TabletSVG render. Requires the user's ``mi_tablet`` Tablet configuration.

Usage:
    python documentation/tools/gen_elevator_svg.py [output.svg]   (default: working/elevator.svg)
"""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root / "tests"))  # the canonical elevator script lives with the tests

from elevator_script import populate  # noqa: E402
from sequins.layout_engine import LayoutEngine  # noqa: E402
from sequins.render import render  # noqa: E402


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else str(_root / "working" / "elevator.svg")
    Path(out).parent.mkdir(parents=True, exist_ok=True)  # working/ is gitignored; may not exist
    engine = LayoutEngine()
    populate(engine)
    render(engine.end_diagram(), out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
