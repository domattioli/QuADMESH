# Contributing to QuADMESH

Thanks for your interest in QuADMESH — a Python port of the MATLAB QuADMESH+
algorithm for triangular-to-quadrilateral mesh conversion. This is the
**canonical** contributor guide (day-to-day mechanics). Authoritative project
rules live in [`AGENTS.md`](AGENTS.md); Claude-Code-specific guidance in
[`CLAUDE.md`](CLAUDE.md); project governance in
[`.specify/memory/constitution.md`](.specify/memory/constitution.md) (if present).

## Repo shape

```
src/quadmesh/         Python package (import name: quadmesh)
  ├── cli.py          Command-line interface
  ├── *.py            Core algorithm modules
  └── ...

tests/                pytest suite (~169 tests)
  ├── test_*.py
  ├── conftest.py
  ├── fixtures/       Test data and MATLAB reference outputs
  └── README.md

docs/                 Project documentation
  ├── MAPPING.md      MATLAB → Python function map
  └── sessions/       Per-session development notes

.specify/specs/       Feature specifications (speckit)
  ├── 001-matlab-to-python-port/
  ├── 003-root-reorg/
  └── ...

src/matlab/           Frozen MATLAB reference (read-only, not installable)
scripts/              Development and build tooling
archive/              Legacy files pending removal
```

## Set up a dev environment (canonical)

```bash
git clone https://github.com/domattioli/QuADMESH.git
cd QuADMESH
bash scripts/dev_setup.sh        # venv + editable chilmesh + quadmesh[dev]
. .venv/bin/activate
```

`scripts/dev_setup.sh` is the **single supported setup path**. It handles:
- Python venv creation
- Editable installation of the sibling `../CHILmesh` repository
- Installation of `quadmesh[dev]` with pytest and coverage tools

**Important:** CHILmesh (an external dependency) is not on PyPI and must be
installed from a sibling local checkout. See `scripts/dev_setup.sh` for details.

## Run the tests

```bash
pytest tests/                    # Full suite (169 tests)
pytest tests/ -m "not slow"      # Exclude slow tests
pytest tests/test_cli.py -v      # Single test file
```

**Note on test fixtures:** Test mesh files (`.14` format) are not vendored.
They are provisioned on-demand from the `domattioli/Valence` registry into
gitignored `tests/fixtures/meshes/`. To enable mesh-dependent tests, set:

```bash
GITHUB_TOKEN=<your-pat> python scripts/fetch_fixtures.py
pytest tests/
```

Without a token, mesh-dependent tests skip silently. See
[`tests/fixtures/README.md`](tests/fixtures/README.md) for details.

## Branch policy

- **All work goes on `development`.** Never push to `main` directly.
- Create a PR `development → main` for all changes.
- Delete the branch after merge.
- Commit format: `<type>: <imperative summary>`
  - Types: `fix`, `feat`, `docs`, `chore`, `refactor`, `test`
  - Example: `fix: correct quad-pair ordering in medial axis`. Do **not** use
    `wip`, `fixup!`, `tmp`, or other prefixes.

CI runs on every PR (currently: linting, tests on Python 3.10+).

## Issue → fix workflow

1. Open an issue with reproduction (pytest output, `file:line` refs, sample
   mesh if possible). Use the issue templates in `.github/ISSUE_TEMPLATE/`.
2. Land the fix on a branch referencing the issue.
3. Close the issue with one-line evidence (test run, commit SHA, or command
   output).

## Key technical notes

- **Faithfulness invariant:** The `method="quadmesh+"` algorithm must produce
  zero interior residual triangles (triangles with no boundary edge). This is
  pinned by `tests/test_no_interior_tris.py` and is non-negotiable. See
  [`AGENTS.md`](AGENTS.md) for context.
- **CHILmesh dependency:** The library depends on CHILmesh (≥1.2.1). If you
  encounter API changes in CHILmesh, see [`docs/MAPPING.md`](docs/MAPPING.md)
  for the current state of integration and upstream issues.
- **MATLAB reference:** The original MATLAB QuADMESH+ implementation is frozen
  in `src/matlab/` for reference. Port fidelity is documented in
  `docs/MAPPING.md`.

## When in doubt

[`CLAUDE.md`](CLAUDE.md) contains operational guidance and session history.
[`docs/MAPPING.md`](docs/MAPPING.md) maps MATLAB functions to their Python
equivalents. Open issues track every live backlog item.
