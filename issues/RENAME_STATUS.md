# Rename: Sequence → Sequins

Rename completed 2026-05-28. Verify the items below when reopening in PyCharm.

## Completed

- [x] Project folder: `PyCharm/Sequence` → `PyCharm/Sequins`
- [x] Git remote: `modelint/sequence.git` → `modelint/sequins.git`
- [x] `.idea/misc.xml`: SDK name → `Python 3.14 (Sequins)`
- [x] `.idea/modules.xml`: module ref → `Sequins.iml`
- [x] `.idea/Sequence.iml` renamed → `Sequins.iml`
- [x] `.idea/Sequins.iml`: jdkName → `Python 3.14 (Sequins)`
- [x] New venv created: `Environments/Sequins` (Python 3.14, same packages as old `Environments/Sequence`)

## Needs action in PyCharm after reopening

- [ ] **Register the new interpreter**: Settings → Project → Python Interpreter
  → Add → Existing environment → `/Users/starr/SDEV/Environments/Sequins/bin/python3.14`
  → Name it `Python 3.14 (Sequins)` to match the `.idea` files

## Needs a decision (project-name strings in source)

These contain "Sequence" as a display/description string — not a path or config key.
Decide whether to update them to "Sequins":

- `README.md` line 1: `## Sequence Diagram Generator`
- `src/seq/__main__.py` line 2: `Blueprint Sequence Diagram Generator`
- `src/seq/__main__.py` line 18: `_progname = 'Blueprint Model Sequence Diagram Generator'`

## Needs a decision (pyproject.toml)

`pyproject.toml` currently has `name = "mi-tabletsvg"` — this appears to be a copy
from the TabletSVG project and has not been updated for this project.
The correct package name (e.g. `mi-sequins` or `sequins`) needs to be set here,
along with description, keywords, and repository URL.

## Needs a decision (.bumpversion.cfg)

`.bumpversion.cfg` references `src/sequin/__init__.py` but the actual package
directory is `src/seq/`. Verify the intended package name and update accordingly.

## Stale .idea file (safe to ignore)

`.idea/workspace.xml` still contains the old path and URL — PyCharm regenerates
this file on open, so no manual fix needed.
