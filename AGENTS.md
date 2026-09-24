# QuADMESH

QuADMESH is a Python port of QuADMESH+, a layer-ordered algorithm that converts triangular meshes into quadrilateral meshes for 2D shallow-water models. The maintained package is Python. The original MATLAB implementation is frozen for reference.

## Hard rules

The QuADMESH+ faithfulness invariant is non-negotiable: `tri2quad` must leave zero interior residual triangles. An interior residual triangle has no domain-boundary edge. Boundary triangles may remain in intermediate or explicitly configured output. `tests/test_no_interior_tris.py` enforces this invariant.

`method="quadmesh+"` is the canonical and default method. `method="layered"` is its supported alias. The removed `"matching"` and `"faithful"` values must raise `ValueError`.

The per-layer implementation is named `_quadmesh_plus_per_layer`. Do not use "faithful" as a method name. It may describe port fidelity.

## Repository layout

- `src/quadmesh/`: maintained Python package and CLI.
- `tests/`: pytest suite and fixture provisioning support.
- `docs/MAPPING.md`: MATLAB-to-Python function map and CHILmesh integration notes.
- `archive/matlab/`: frozen MATLAB reference. It is not installable.
- `scripts/`: setup, fixture, benchmark, diagnostic, and repository health tools.

## Setup, test, and run

```bash
bash scripts/dev_setup.sh
. .venv/bin/activate
pytest tests/
python -m quadmesh.cli input.14 -o output.14
# Optional: provision private Valence fixtures.
GITHUB_TOKEN=<pat> python scripts/fetch_fixtures.py
```

`scripts/dev_setup.sh` creates `.venv`, installs the sibling `../CHILmesh` checkout in editable mode, and installs `quadmesh[dev]`. CHILmesh is not available from PyPI.

## Testing and data

The `.14` fixtures are not vendored. They are fetched from the private `domattioli/Valence` registry into the gitignored `tests/fixtures/meshes/` directory and checked against pinned git blob hashes. Access requires `GITHUB_TOKEN` or `GH_TOKEN` with cross-repository read permission.

Without that token, Valence-dependent tests skip. The faithfulness gate also uses meshes bundled with `chilmesh.data` when those files are available. See `tests/fixtures/README.md` for the fixture protocol.

## Project conventions

CHILmesh is an external dependency. Use its public APIs, including `ccw_edges_around_vert` and `CHILmesh(compute_adjacencies=...)`. The previously filed CHILmesh API issues are closed; do not re-file them. `two_part_smoother` is deprecated in favor of `fem_smoother`. The `tri2quad(aggressive=)` option is reserved for future integration with `merge_elements`.

Use `docs/MAPPING.md` to check MATLAB parity and current port coverage before changing algorithm behavior.

## Branch policy

The default working branch is `development`. Releases go through a pull request from `development` to `main`. Never push directly to `main` and never force push.

## Repo-local labels

| Label | Meaning |
|---|---|
| `downstream-api` | Tracks CHILmesh API changes required by QuADMESH. |

## Related repositories

`domattioli/CHILmesh` provides mesh data structures, smoothing, and quality analysis. `domattioli/ADMESH` provides adaptive mesh generation. `domattioli/Valence` is the authoritative test-mesh registry.

## Governance
This repo is a downstream consumer of `domattioli/DomI`.
Universal git, coding dispatch, secrets, session lifecycle, and communication rules live in DomI `.claude/policies/`.
`scripts/instructions_on_start.sh` checks `.domi-pin` drift at session start.
Spec-kit artifacts for this repo live in DomI `specs/consumers/quadmesh/`, never in a local `.specify/` directory.
