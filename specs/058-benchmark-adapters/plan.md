<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# Implementation Plan: Benchmark adapters for other quad meshers

**Branch**: `development` (no feature branch) | **Date**: 2026-10-10 | **Spec**: `specs/058-benchmark-adapters/spec.md`
**Input**: Feature specification from `specs/058-benchmark-adapters/spec.md` (Clarified 2026-10-10)

## Summary

Add a `quadmesh.benchmark` subpackage: an adapter protocol (triangulation in, quad mesh plus metadata out, availability probe, license tag), a registry, a runner that produces a comparison table from `compute_quality_stats` plus topology and timing columns, and a `quadmesh-bench` console script. First slice: QuADMESH+ reference row, built-in greedy tri-merge, QuadriFlow (MIT) through its executable, Gmsh Blossom-Quad (GPL) through a generated `.geo` script run by the user-installed `gmsh` binary. A packaging test proves the wheel carries no GPL and no Valence code. A claim test ties README and description wording to registered, offline-tested adapters. Results for the release go to `docs/benchmarks/0.3.0/results.{md,json}`; the README claim lands in the same change as that table. Target release 0.3.0. No edit to `src/quadmesh/tri2quad.py` (feature 059 owns it).

## Technical Context

**Language/Version**: Python >=3.10 (`pyproject.toml:10`)
**Primary Dependencies**: numpy, scipy, chilmesh>=1.5.0, matplotlib (already declared). New hard dependencies: none (spec FR-013).
**Optional extras (new entries in `pyproject.toml`; 057 committed as `ec97ba5`)**: `bench-quadriflow` (QuadriFlow route, see R3 and R11), `bench` = union of every permissive `bench-*` extra. Gmsh has no extra by rule (FR-013): the `gmsh-blossom` adapter ships as a thin wrapper and activates only when `gmsh` is on `PATH` or `QUADMESH_GMSH` points at it.
**External executables (user-installed, probed on `PATH` or through env vars `QUADMESH_GMSH`, `QUADMESH_QUADRIFLOW`)**: `gmsh` (GPL-2.0+), `quadriflow` (MIT)
**Runtime opt-out (FR-023)**: `--disable NAME,...`, `run_benchmark(disabled=...)`, env `QUADMESH_BENCH_DISABLE=name,name`. Disabled adapters are skipped before `probe()`.
**Storage**: files. Input `.14` through CHILmesh; interchange `.msh` v2 ASCII (Gmsh) and `.obj` (QuadriFlow) written and read by small adapter-local I/O helpers; results `results.md` + `results.json`
**Testing**: pytest. Contract tests parametrized over the registry; external adapters skip when the probe reports not installed; packaging test builds a wheel into the scratch dir and inspects its file list and imports
**Target Platform**: PyPI sdist and wheel; macOS and Linux CI (`.github/workflows/tests.yml`)
**Project Type**: single library plus CLI (`src/quadmesh/`)
**Performance Goals**: runner overhead (metrics, table) under 50 percent of direct QuADMESH+ runtime on the largest `chilmesh.data` mesh (SC-008); per-adapter timeout default 600 s
**Constraints**: zero new hard dependencies; no `import gmsh`, no vendored GPL; no Valence code; `tri2quad.py` untouched; `pyproject.toml` dependency lines untouched until 057 merges and then only new keys (`[project.scripts]` entry `quadmesh-bench`)
**Scale/Scope**: about 10 new source files under `src/quadmesh/benchmark/`, 7 new test files, 1 results folder, README section, description string

## Constitution Check

| Principle | Status |
|---|---|
| I. Faithful port | PASS. QuADMESH+ output is read, never modified (FR-018). The faithfulness gate applies to the QuADMESH+ row only (FR-017). |
| II. Depend on chilmesh, no reinvention | PASS with one new spoke: adapter-local `.msh` and `.obj` writers/readers. CHILmesh has `.14` I/O only (`CHILmesh.py:2844,1525`). Documented in research R4; a `downstream-api` note in `docs/MAPPING.md` asks CHILmesh for OBJ/MSH I/O later. |
| III. Test-first per module | PASS. Contract tests (T006) and the packaging test (T008) are written before the external adapters. |
| IV. Layered implementation | PASS. Protocol and registry, then built-in adapters, then external adapters, then runner, then CLI, then docs. |
| V. 0-based indexing | PASS. Interchange formats are 1-based (`.msh`, `.obj`); conversion is confined to the I/O helpers and covered by round-trip tests. |
| VI. Caveman docs | Docstrings terse. Public text (README, results.md) uses the writing stack per spec FR-016. |
| Scope section lists MATLAB folders only | Justified extension. The constitution predates the benchmark idea; 002 (`spec.md:128`) already planned the harness as a separate spec. No constitution amendment needed; the harness adds no tri→quad algorithm of its own except the greedy floor, which is a baseline, not a product feature. |

Post-design re-check: PASS.

## Phase 0: Research (decisions)

Full text in `research.md`. Summary:

| # | Decision | Rationale |
|---|---|---|
| R1 | Adapter is a `Protocol` with `name`, `family`, `license_tag`, `citation`, `probe()`, `run(mesh, options) -> AdapterResult`; registry is a module-level dict filled by decorator `@register`. | One file and one decorator per adapter (SC-002). |
| R2 | Gmsh reached by writing `in.msh` + a `.geo` script (`Merge "in.msh"; RecombineMesh; Save "out.msh";`) and running `gmsh -0 script.geo` as a subprocess. | `RecombineMesh` is a `.geo` command, so no Python API import is needed. `Mesh.RecombinationAlgorithm` 1 selects Blossom. GPL stays outside the package. |
| R3 | QuadriFlow reached by its executable (`quadriflow -i in.obj -o out.obj -f <faces>`), planar mesh embedded with z=0. | MIT allows vendoring, but building C++ in the wheel is out of scope; executable keeps the base install dependency-free. The adapter records `vertex_order_preserved=False` and boundary-change counts because QuadriFlow remeshes rather than recombines. Known risk: QuadriFlow targets closed surfaces; open planar domains may fail or distort the boundary. The row reports that honestly. |
| R4 | Adapter-local `.msh` v2 ASCII and `.obj` writers/readers in `benchmark/_io.py`. | No CHILmesh support; formats are small. Round-trip tests guard 1-based offsets. |
| R5 | Boundary-vertex preservation: compare input boundary vertex coordinate set with output boundary vertex coordinate set, tolerance 1e-9 relative to bounding-box diagonal; report two counts: input boundary vertices with no match in the output (lost) and output boundary vertices with no match in the input (added). Boundary of output found with CHILmesh boundary edges. | Works for remeshers that renumber vertices. |
| R6 | Residual triangles split into interior and boundary using the same definition as `tests/test_no_interior_tris.py` (interior = no domain-boundary edge). | Keeps one definition across the project. |
| R7 | Results record is JSON with schema version, package version, date, mesh name, mesh sha1 (git-blob style as in `tests/_mesh_provision.py`), tool versions, rows. Markdown table generated from the JSON. | Diffable across releases (US4). |
| R8 | Claim test parses README and `pyproject.toml` description for adapter display names from the registry; every match must be registered and either run in offline CI or be followed in the text by "(requires user-installed tool)". | FR-015, SC-005. |
| R9 | Packaging test builds a wheel with `python -m build --wheel` into the scratch dir, lists files, asserts no path contains `gmsh`, `comiso`, `qex`, `valence`, and that `import quadmesh.benchmark` does not import `gmsh`. | SC-006. |
| R11 | Install routes: base (QuADMESH+, greedy tri-merge), per-adapter extra `bench-<name>`, aggregate `bench`, external executable (GPL). Each adapter declares `install_route`; the probe message is generated from it. `tests/test_bench_packaging.py` reads `[project.optional-dependencies]` and asserts no `bench*` extra lists a GPL distribution (`gmsh`, `comiso`, `libqex`). | Operator ruling 2026-10-10: users choose what to install; GPL never via pip. |
| R10 | Greedy tri-merge: scan triangles in index order, merge with the unmerged neighbor across the shared edge that gives the best skew for the resulting quad, never merge across a domain-boundary edge, leave the rest as triangles. Own code; docstring cites the 002 catalog row (`specs/002-quadmeshing-algorithm-survey/spec.md:80`) and Owen 1999 only as survey context. | Sanity floor per 002; no boundary vertex changes, so the preservation column reads true. |

## Project Structure

### Documentation (this feature)

```text
specs/058-benchmark-adapters/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── adapter-protocol.md
│   └── cli-and-results.md
├── checklists/
│   ├── requirements.md
│   └── license-and-claims.md
└── tasks.md
```

### Source Code (repository root)

```text
src/quadmesh/benchmark/
├── __init__.py          # public: run_benchmark, registry, AdapterResult, BenchmarkRow
├── _protocol.py         # Adapter Protocol, AdapterResult, register(), get_adapters()
├── _io.py               # write_msh2/read_msh2, write_obj/read_obj (1-based conversion)
├── _metrics.py          # row_from_result(): compute_quality_stats + topology + boundary preservation
├── _runner.py           # run_benchmark(meshes, adapters, timeout, strict) -> ResultsRecord
├── _report.py           # to_markdown(record), to_json(record), load_json()
├── cli.py               # quadmesh-bench entry point
└── adapters/
    ├── __init__.py      # imports each adapter module so @register fires
    ├── quadmesh_plus.py # wraps run_pipeline; reference row
    ├── greedy_tri_merge.py
    ├── gmsh_blossom.py  # subprocess only; license_tag "GPL-subprocess"
    └── quadriflow.py    # subprocess; license_tag "MIT-external"

tests/
├── test_bench_contract.py     # parametrized over registry
├── test_bench_io.py           # msh/obj round trips
├── test_bench_metrics.py      # boundary preservation, residual split
├── test_bench_runner.py       # failure isolation, strict mode, not-installed row, timeout, unsupported input
├── test_bench_cli.py          # --list, --strict, --disable, --show-disabled
├── test_bench_claims.py       # README/description names vs registry
└── test_bench_packaging.py    # wheel file list, no GPL/Valence imports

docs/benchmarks/0.3.0/
├── results.md
└── results.json

THIRD_PARTY_NOTICES.md         # created only if permissive code is vendored; the 0.3.0 slice vendors nothing, so no file
```

**Structure Decision**: a subpackage keeps the harness importable (`from quadmesh.benchmark import run_benchmark`) and lets the wheel exclude nothing special; adapters are one file each. `scripts/bench_quadmesh_plus.py` stays as is.

## Ownership and collision guards

- `src/quadmesh/tri2quad.py`: never edited. 059 is committed (`3b39fbb`); the QuADMESH+ adapter inherits its behavior through `run_pipeline`.
- `pyproject.toml`: 057 is committed (`ec97ba5`). 058 adds `[project.scripts] quadmesh-bench = "quadmesh.benchmark.cli:main"` and the `bench-*` and `bench` extras. Nothing else in the file changes.
- `README.md`: new "Benchmark" section only, inserted after "Performance"; status line untouched. 056 is done, so the file is free, but version strings stay 0.3.0 until release.
- `docs/MAPPING.md`: one `downstream-api` row (OBJ/MSH I/O in CHILmesh).
- `CHANGELOG.md`: a 0.3.0 `Added` entry; the entry sits under the 0.3.0 heading.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| New file-format I/O (spoke on principle II) | Gmsh and QuadriFlow do not read `.14` | Asking CHILmesh first delays 0.3.0; the helpers are under 150 lines and a `downstream-api` row asks for the upstream version |
