"""Generate the elevator Curtain Diagram SVG via the *adapter* (client) path.

The adapter-driven twin of ``gen_elevator_svg.py``: runs the elevator scenario in client
(sequence-diagram) vocabulary through ``SequenceDiagramAdapter`` instead of issuing layout-
engine commands directly. The final SVG is identical to the engine-driven one (see
``tests/test_adapter_elevator.py``).

Usage:
    python documentation/tools/gen_elevator_svg_adapter.py [output.svg] [--interactive]

    --interactive   rewrite the output file after every verb, so a viewer kept open on it
                    shows the diagram build up (Transfer stays hidden until its creation
                    signal and first state). Default: render only once, at end_diagram.
"""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "src"))
sys.path.insert(0, str(_root / "tests"))  # the elevator fixtures live with the tests

from elevator_adapter_script import drive  # noqa: E402
from sequins.sd_adapter import SequenceDiagramAdapter  # noqa: E402


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--interactive"]
    interactive = "--interactive" in sys.argv[1:]
    out = args[0] if args else str(_root / "working" / "elevator_adapter.svg")
    Path(out).parent.mkdir(parents=True, exist_ok=True)  # working/ is gitignored; may not exist

    adapter = SequenceDiagramAdapter(out, interactive=interactive)
    drive(adapter)
    adapter.end_diagram()
    how = "built interactively into" if interactive else "wrote"
    print(f"{how} {out}")


if __name__ == "__main__":
    main()
