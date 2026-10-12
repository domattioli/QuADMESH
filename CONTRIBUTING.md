# Contributing to QuADMESH

QuADMESH is a Python port of the MATLAB QuADMESH+ algorithm for
triangular-to-quadrilateral mesh conversion. This is the canonical contributor
guide (day-to-day mechanics). Authoritative project rules live in
[`AGENTS.md`](AGENTS.md). The maintainer keeps the project constitution private.

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
  └── MAPPING.md      MATLAB → Python function map

DomI/specs/consumers/quadmesh/specs/       Feature specifications (speckit)
  ├── 001-matlab-to-python-port/
  ├── 003-root-reorg/
  └── ...

scripts/              Development and build tooling
archive/matlab/       Frozen MATLAB QuADMESH+ original (read-only, not installable)
```

## Set up a dev environment (canonical)

```bash
git clone https://github.com/domattioli/QuADMESH.git
cd QuADMESH
bash scripts/dev_setup.sh        # venv + quadmesh[dev] (chilmesh from PyPI)
. .venv/bin/activate
```

`scripts/dev_setup.sh` is the single supported setup path. It does three things:
- Python venv creation
- Installation of `quadmesh[dev]` with pytest and coverage tools, which pulls `chilmesh` from PyPI
- Optional: an editable install of a local CHILmesh checkout when `QUADMESH_CHILMESH_SRC=<path>` is set

See `scripts/dev_setup.sh` for details.

## Run the tests

```bash
pytest tests/                    # Full suite (169 tests)
pytest tests/ -m "not slow"      # Exclude slow tests
pytest tests/test_cli.py -v      # Single test file
```

Test mesh files (`.14` format) are not vendored. Meshes come through Valence into
gitignored `tests/fixtures/meshes/`. To enable mesh-dependent tests, run:

```bash
VALENCE_TOKEN=<your-token> python scripts/fetch_fixtures.py
pytest tests/
```

Without a token, mesh-dependent tests skip silently. See
[`tests/fixtures/README.md`](tests/fixtures/README.md) for details.

## Branch policy

- All work goes on `development`. Never push to `main` directly.
- Create a PR `development → main` for all changes.
- Delete the branch after merge.
- Commit format: `<type>: <imperative summary>`
  - Types: `fix`, `feat`, `docs`, `chore`, `refactor`, `test`
  - Example: `fix: correct quad-pair ordering in medial axis`. Do not use
    `wip`, `fixup!`, `tmp`, or other prefixes.

CI runs on every PR (currently: linting, tests on Python 3.10+).

## Issue → fix workflow

1. Open an issue with reproduction (pytest output, `file:line` refs, sample
   mesh if possible). Use the issue templates in `.github/ISSUE_TEMPLATE/`.
2. Land the fix on a branch referencing the issue.
3. Close the issue with one-line evidence (test run, commit SHA, or command
   output).

## Key technical notes

- Faithfulness invariant: the `method="quadmesh+"` algorithm must produce
  zero interior residual triangles (triangles with no boundary edge).
  `tests/test_no_interior_tris.py` pins this, and it is non-negotiable. See
  [`AGENTS.md`](AGENTS.md) for context.
- CHILmesh dependency: the library depends on CHILmesh (≥1.2.1). For CHILmesh
  API changes, see [`docs/MAPPING.md`](docs/MAPPING.md) for the current state of
  integration and upstream issues.
- MATLAB reference: the original MATLAB QuADMESH+ implementation is frozen in
  `archive/matlab/`. `docs/MAPPING.md` documents port fidelity.

## When in doubt

[`AGENTS.md`](AGENTS.md) contains operational guidance.
[`docs/MAPPING.md`](docs/MAPPING.md) maps MATLAB functions to their Python
equivalents. Open issues track every live backlog item.

## Share your mesh

If you have a fort.14 mesh you can share, open an issue in this repository (https://github.com/domattioli/quadmesh/issues/new). Choose a license, name the generator, and describe the region and resolution. See [docs/share-your-mesh.md](docs/share-your-mesh.md) for details.
