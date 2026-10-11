<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# Tasks: Benchmark adapters for other quad meshers

**Input**: `specs/058-benchmark-adapters/spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`
**Prerequisites**: 057 (`ec97ba5`) and 059 (`3b39fbb`) are committed. No task here touches `src/quadmesh/tri2quad.py`. Folds into 0.3.0 (operator ruling 2026-10-10); the CHANGELOG entry sits under [0.3.0]. No spec-move task: the move to DomI is handled elsewhere.
**Format**: `- [ ] Txxx [P?] [USn?] description (path)`. `[P]` means parallelizable (different files, no dependency on an unfinished task).
**Tests**: the spec requests tests (FR-014, FR-015, SC-006), so test tasks are included and come before the code they cover.

## Phase 1: Setup

- [ ] T001 Confirm `ec97ba5` and `3b39fbb` are on `development` (`git log --oneline -3`) and the tree is clean apart from `specs/` and `.specify/`. Stop otherwise.
- [x] T002 Create the package skeleton: `src/quadmesh/benchmark/__init__.py`, `_protocol.py`, `_io.py`, `_metrics.py`, `_runner.py`, `_report.py`, `cli.py`, `adapters/__init__.py` (empty bodies with module docstrings).
- [x] T003 Add to `pyproject.toml` only: `[project.scripts] quadmesh-bench = "quadmesh.benchmark.cli:main"`; `[project.optional-dependencies]` entries `bench-quadriflow = []` (placeholder, see T014) and `bench = ["quadmesh[bench-quadriflow]"]`. No other line changes.

## Phase 2: Foundational (blocks every story)

- [x] T004 Write `tests/test_bench_io.py`: `.msh` 2.2 and `.obj` round trips on the smallest `chilmesh.data` mesh; 1-based offsets, triangle and quad rows, z=0 embedding. Test first; fails until T005.
- [x] T005 Implement `src/quadmesh/benchmark/_io.py`: `write_msh2`, `read_msh2` (types 2 and 3 only), `write_obj`, `read_obj`. T004 green.
- [x] T006 Write `tests/test_bench_contract.py` parametrized over `get_adapters()`: probe shape, skip when not installed or disabled, run succeeds on the smallest bundled mesh, CCW, no zero-area, metadata typed, input immutability (pattern from `tests/test_input_immutability.py`). Residual triangles are reported, never asserted zero, for adapters other than `quadmesh-plus` (FR-017).
- [x] T007 Implement `src/quadmesh/benchmark/_protocol.py`: `Adapter` Protocol, `Availability`, `AdapterOptions`, `AdapterResult`, `register`, `get_adapters`, `install_route` enum and hint generator, `is_disabled(name, disabled, env)` reading `QUADMESH_BENCH_DISABLE` (data-model.md).
- [x] T008 Write `tests/test_bench_packaging.py` (marked `slow`): build a wheel into the scratch dir, assert no path contains `gmsh`, `comiso`, `qex`, `valence`; subprocess import of `quadmesh.benchmark` leaves `gmsh` out of `sys.modules`; parse `pyproject.toml` and assert no `bench*` extra names `gmsh`, `comiso`, `libqex` (R9, R11).
- [x] T009 Write `tests/test_bench_metrics.py`: boundary preservation on an identity output (True, 0), on a shifted boundary vertex (False, 1), residual split interior vs boundary on a hand-built 4-triangle mesh (R5, R6).
- [x] T010 Implement `src/quadmesh/benchmark/_metrics.py`: `row_from_result` using `compute_quality_stats` (`src/quadmesh/quality_report.py:10`), element composition, residual split with the `tests/test_no_interior_tris.py` definition, boundary preservation via `scipy.spatial.cKDTree`. T009 green.

**Checkpoint**: protocol, I/O and metrics exist; adapters can be added one file at a time.

## Phase 3: US1 (P1, MVP), one-command comparison on one mesh

- [x] T011 [US1] Implement `src/quadmesh/benchmark/adapters/quadmesh_plus.py`: wraps `run_pipeline` (`src/quadmesh/pipeline.py:16`) with default options; `install_route=base`, `license_tag=project`, `vertex_order_preserved=True`. Register in `adapters/__init__.py`.
- [x] T012 [P] [US1] Implement `src/quadmesh/benchmark/adapters/greedy_tri_merge.py` per R10 (own code; docstring is a short method paragraph plus the reference-baseline sentence; display name "greedy recombination (baseline)"). `install_route=base`, `license_tag=clean-room`.
- [x] T013 [US1] Write `tests/test_bench_runner.py`: two built-in adapters produce two `ok` rows on a bundled mesh; a fake adapter that raises yields a `failed` row and the others survive; a fake not-installed adapter yields `not installed` with hint and exit 0; `--strict` returns non-zero; `QUADMESH_BENCH_DISABLE` removes a row and `--list` says disabled; a fake adapter that sleeps past `timeout_s=0.1` yields status `timeout`; a mixed tri/quad input against an `accepts_mixed=False` adapter yields `unsupported input` (SC-004, SC-009, FR-011, FR-022, FR-023, spec edge cases).
- [x] T014 [US1] Implement `src/quadmesh/benchmark/_runner.py`: `run_benchmark(meshes, adapters=None, disabled=None, timeout_s=600, strict=False)` with per-adapter try/except and timeout, mesh sha1 (same scheme as `tests/_mesh_provision.py`), `ResultsRecord`. T013 green.
- [x] T015 [US1] Implement `src/quadmesh/benchmark/_report.py`: `to_markdown`, `to_json`, `load_json` per `contracts/cli-and-results.md`.
- [x] T016 [US1] Implement `src/quadmesh/benchmark/cli.py` per `contracts/cli-and-results.md` (`--adapters`, `--disable`, `--out`, `--timeout`, `--strict`, `--list`, `--show-disabled`, `--bundled`). Add `tests/test_bench_cli.py` for `--list` and `--strict` exit codes.
- [x] T017 [US1] Export `run_benchmark`, `get_adapters`, `register`, `AdapterResult`, `BenchmarkRow` from `src/quadmesh/benchmark/__init__.py`; add the subpackage to `docs/MAPPING.md` with one `downstream-api` row asking CHILmesh for OBJ/MSH I/O (R4).

**Checkpoint**: `quadmesh-bench --bundled` prints a two-row table per bundled mesh (SC-001).

## Phase 4: US2 (P2), new adapter without touching the runner

- [x] T018 [US2] Add a pass-through test adapter inside `tests/test_bench_contract.py` (registered only during the test) and assert the runner and contract tests include it with zero edits elsewhere (SC-002).
- [ ] T019 [US2] Implement `src/quadmesh/benchmark/adapters/gmsh_blossom.py`: subprocess only, `.geo` script per R2, `Mesh.RecombinationAlgorithm = 1`, probe via `gmsh --version` or `QUADMESH_GMSH`, `install_route=external`, `license_tag=GPL-subprocess`, docstring states GPL stays outside the package. Verify the script variant on the installed binary (`brew install gmsh` on the dev machine) and record the working script in the module. **Note:** PARTIAL, not verified. Code written from R2 with probe and subprocess only; no Gmsh binary on this machine (operator: do not install). The .geo script and the `gmsh job.geo -` batch flag were never run; the docstring says so. Verify on a machine with Gmsh.
- [ ] T020 [P] [US2] Implement `src/quadmesh/benchmark/adapters/quadriflow.py`: subprocess per R3, OBJ round trip with z=0, `vertex_order_preserved=False`, probe via `PATH` or `QUADMESH_QUADRIFLOW`, `install_route=extra:bench-quadriflow`. Check whether a PyPI distribution exists; if yes, fill the `bench-quadriflow` extra in `pyproject.toml`; if not, keep it empty with a comment and the R11 probe message. Operator ruling: extra is `pyquadriflow` on linux/win32 only; adapter prefers the importable module, else PATH executable. Record QuadriFlow's behavior on the open planar bundled meshes in the docstring. **Note:** PARTIAL, not verified. Code written from R3; no QuadriFlow binary, behavior on open planar meshes unknown (docstring says so). PyPI: `pyquadriflow` 0.0.4 exists (MIT, pre-alpha, wheel holds only Linux .so and Windows .dll, no macOS); downloaded to scratch and inspected, not installed. Operator ruling: extra `bench-quadriflow` now `["pyquadriflow; sys_platform == 'linux' or sys_platform == 'win32'"]`; adapter uses the module when importable (call signature read from wheel source, UNVERIFIED, never run), else the executable.
- [ ] T021 [US2] Run `pytest tests/test_bench_contract.py` with Gmsh installed and, if available, QuadriFlow; both external rows pass or skip with a clear reason (SC-003 skew check against `compute_quality_stats` on the saved output file). **Note:** PARTIAL. `pytest tests/test_bench_contract.py` ran: both external rows skip with reason (executable not found). Run with the tools installed is not done; SC-003 skew check not done.

## Phase 5: US5 (P2), opt-in install and opt-out

- [x] T022 [US5] Verify in a fresh venv: `pip install .` then `quadmesh-bench --list` shows base adapters available and the others with their install route text; `pip install ".[bench]"` installs no GPL distribution (`pip list` grep). Record the transcript in `specs/058-benchmark-adapters/checklists/license-and-claims.md` notes. **Note:** Fresh venv in scratch: `pip install .` then `quadmesh-bench --list` shows 2 available, Gmsh and QuadriFlow with install hints; `.[bench]` adds no gmsh/comiso/qex/quadriflow package (17 packages total). Transcript summary in checklists/license-and-claims.md.
- [x] T023 [US5] Add `tests/test_bench_cli.py` cases for `--disable` and `--show-disabled` output. **Note:** Cases already existed in tests/test_bench_cli.py (`test_disable_and_show_disabled`, `test_list_shows_disabled_and_hint`); no new code needed.

## Phase 6: US4 (P3), results table for the release

- [x] T024 [US4] Run `quadmesh-bench --bundled --out docs/benchmarks/0.3.0` on the dev machine with Gmsh installed (and QuadriFlow if available); commit `results.md` and `results.json`. Footer: tool versions, date, package version, reproduce command, QuadriFlow boundary caveat (R3), QuADMESH+ point-insertion note (R5). **Note:** Files produced by `quadmesh-bench --bundled --out docs/benchmarks/0.3.0`; NOT committed (operator). Gmsh and QuadriFlow rows read 'not installed'.
- [~] T025 (PARTIAL) [US4] Writing stack on `docs/benchmarks/0.3.0/results.md` prose (footer and any caption): `write-like-scientist` voice 1-10, Golden rule G1-G17, `asd-ste100-lens`, then tell scan (Haiku scan plus Sonnet correction per `write-like-scientist/references/ai-tells-scan.md`) with a fact add/drop audit. Tables and numbers are exempt from voice edits. **Note:** Prose in results.md (Notes block, generated from `_report.NOTES`): voice rules, G1-G17 by eye, STE lens, `banned_words.py` exit 0. PARTIAL: manual review only. The Haiku tell scan and Sonnet correction pass were NOT run. Fact audit: no fact added beyond table values and R3/R5; none dropped.

## Phase 7: US3 (P2), honest README and description claims

- [x] T026 [US3] Write `tests/test_bench_claims.py` per R8: display names from the registry scanned in `README.md` and the `pyproject.toml` description; each hit registered; external-tool adapters marked "requires user-installed tool"; README benchmark section present only if `docs/benchmarks/<version>/results.md` exists (FR-015, FR-021). Test first; it passes trivially before T027 because README names nothing yet. **Note:** Written; negative check (removing 'requires user-installed tool') fails `test_external_adapters_marked`, restored, green.
- [x] T027 [US3] Draft the README "Benchmark" section after "Performance" (`README.md`): what the harness is, the adapters that have an `ok` row in `docs/benchmarks/0.3.0/results.md` (if QuadriFlow was not installed for T024, the README does not name it as benchmarked; it may list it as an available adapter marked "requires user-installed tool"), install routes (`quadmesh[bench-quadriflow]`, `quadmesh[bench]`, Gmsh installed separately), opt-out, reproduce command, link to `docs/benchmarks/0.3.0/results.md`. Update the `pyproject.toml` `description` to add the harness clause naming only those adapters. Add a `CHANGELOG.md` 0.3.0 entry. **Note:** README Benchmark section after Performance, Share section untouched; names QuADMESH+ as benchmarked (greedy baseline appears only as a table row), Gmsh and QuadriFlow as 'requires user-installed tool'. Description clause and CHANGELOG 0.3.0 entry added.
- [~] T028 (PARTIAL) [US3] Writing stack on the T027 text in order: voice 1-10, G1-G17, `asd-ste100-lens`, tell scan with fact add/drop audit. Record the scan result in `checklists/license-and-claims.md`. **Note:** Same stack as T025 on README text: banned_words exit 0, one G2 clipped negative tail fixed by hand. PARTIAL: manual review only. The Haiku tell scan and Sonnet correction pass were NOT run. Recorded in checklist.
- [x] T029 [US3] Run `pytest tests/test_bench_claims.py tests/test_release_metadata.py`; both green. **Note:** `pytest tests/test_bench_claims.py tests/test_release_metadata.py`: 8 passed, 1 skipped (no .zenodo.json).

## Phase 8: Polish

- [x] T030 [P] Run the full suite: `pytest tests/` and `pytest --runslow tests/test_bench_packaging.py`; all green or skipped with reason. **Note:** `pytest tests/`: 188 passed, 69 skipped. Packaging test (`--runslow`) run from the scratch venv: 3 passed. Packaging test needed an allow-list for `adapters/gmsh_blossom.py` (own wrapper code).
- [x] T031 [P] Timing check (SC-008): runner overhead under 50 percent of direct QuADMESH+ runtime on the largest bundled mesh; note the numbers in `checklists/license-and-claims.md`. **Note:** Measured; SC-008 relaxed by operator ruling and PASSES: overhead about 40% on Block_O (0.385 s direct vs 0.538 s via run_benchmark). Numbers in checklist.
- [x] T032 Fill `specs/058-benchmark-adapters/checklists/license-and-claims.md` with evidence per item (commands run and outputs); the lead verifies independently before accepting. **Note:** Checklist filled with evidence and honest status; lead must verify.

## Dependencies

- Phase 1 → Phase 2 → US1 (Phase 3). US2 needs T007 and T014. US5 needs T016 and T020. US4 needs US1 and at least one external adapter (T019). US3 needs US4 (claim lands only with results, FR-021). Polish last.
- Parallel sets: T011 with T012; T019 with T020; T030 with T031.

## Implementation strategy

MVP is Phase 1 to 3: a working harness with two built-in rows and no external tool. Then Gmsh, then QuadriFlow, then install/opt-out verification, then results, then README text. The README claim is the last code-adjacent change and never precedes the results table.

## Counts

32 tasks. US1: 7. US2: 4. US5: 2. US4: 2. US3: 4. Setup 3, foundational 7, polish 3. Parallel pairs: 3.
