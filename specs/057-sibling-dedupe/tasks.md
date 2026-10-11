<!-- provenance: author=domattioli model=claude-opus-5-5 effort=low date=2026-10-10 skill=speckit-tasks repo=quadmesh session=unknown -->
# Tasks: Remove functionality duplicated in sibling packages

**Input**: `specs/057-sibling-dedupe/spec.md`, `plan.md`
**Prerequisite**: feature 056 is implemented and merged to `development` before T001. Do not edit files that 056 owns (spec FR-018).
**Format**: `- [ ] Txxx [P?] [USn?] description (path)`. `[P]` means the task can run in parallel, because it touches different files with no dependency.

## Phase 1: Setup

- [x] T001 Confirm 056 has landed (`git log development` shows its commit) and that `pyproject.toml` / `__init__.py` already say 0.3.0. Stop if not.
- [x] T002 Create the environment: `bash scripts/dev_setup.sh` (`scripts/dev_setup.sh`); confirm `pip show chilmesh` reports >=1.5.0.
- [x] T003 Record the baseline: run `pytest tests/` and save the pass/skip counts to the scratchpad. Also snapshot `inspect.signature` for every public name (used by T016).

## Phase 2: Foundational (blocks US1 to US4)

- [x] T004 Edit `pyproject.toml` `dependencies` only: `chilmesh>=1.5.0`, add `matplotlib>=3.6`; keep the `plot` extra for back-compat (FR-009).
- [x] T005 Write `tests/test_dedupe_parity.py`: for each available fixture (chilmesh-bundled plus Valence when a token is set), snapshot `compute_quality_stats` and `n_elems` after `run_pipeline` on the current code. Store the baseline JSON under `tests/fixtures/baselines/dedupe_057.json`. Test written first; it must pass on unmodified code.

## Phase 3: US1, smoothing and compaction delegate to CHILmesh (P1, MVP)

- [x] T006 [US1] Spike: compare `_balendran_smooth(mesh)` with `mesh.copy().direct_smoother()` points on every fixture; record the max abs difference. Decide R3 (≤1e-6 → delegate; else keep). Note the result in a comment in `tests/test_dedupe_parity.py`.
- [x] T007 [US1] Replace the body of `remove_unused_vertices` with a `submesh`-based shim; keep the early return; reattach `grid_name` if `submesh` drops it (`src/quadmesh/remove_unused.py`).
- [x] T008 [US1] If T006 passed: route `fem_smoother(method="fem")` through `direct_smoother`, keep the compaction, the #107 single-pass short-circuit, and the revert-on-exception; delete `_balendran_smooth`; update `tests/test_smoother.py:60`, which patches `pp._balendran_smooth` (`src/quadmesh/post_process.py`). If T006 failed: no code change; go to T020.
- [x] T009 [US1] Run `pytest tests/test_no_interior_tris.py tests/test_smoother.py tests/test_quality_regression.py tests/test_parity.py tests/test_dedupe_parity.py`. All pass (SC-001, SC-002).
- [x] T010 [US1] Time post-process on Test_Case_1, Block_O, and Mixed_Test against the T003 baseline; the run must stay within +10% (plan Performance Goals). If it does not, pass `compute_layers=False` in the shim.

## Phase 4: US2, thin shims replaced with direct calls (P2)

- [x] T011 [P] [US2] Inline `ccw_edges_around_vert` at `src/quadmesh/identify_edges.py:23` as `mesh.ccw_edges_around_vert`.
- [ ] T012 SKIPPED (coordinator: do not touch tri2quad.py, another worker) [P] [US2] Inline `merge_tri_pair` at `src/quadmesh/tri2quad.py:822` as `chilmesh.quad_from_tri_pair`.
- [ ] T013 SKIPPED (depends on T012) [US2] Delete `src/quadmesh/_topology.py` after T011 and T012; `grep -rn _topology src tests` returns nothing.
- [x] T014 [US2] In `src/quadmesh/repair.py:222` `_merge_tri_pairs_to_quads`, call `chilmesh.quads_from_tri_pairs` if the vertex order matches on the `tests/test_repair.py` cases; otherwise leave it and add a MAPPING row (T020).
- [x] T015 [US2] Change the `two_part_smoother` warning to name removal in 0.4.0 (`src/quadmesh/post_process.py:318`) (FR-007).
- [x] T016 [US2] Run the full `pytest tests/`; the counts must match T003 (plus the new tests). Add `tests/test_public_api_057.py`: every name in `quadmesh.__all__` plus `create_quad_domain` and `run_pipeline` imports, and their signatures match a snapshot taken at T003 (FR-003).

## Phase 5: US4, dependencies declared (P3)

- [ ] ~~T017~~ SKIPPED (operator ruling 2026-10-10: no Valence code on consumer machines; spec FR-010/FR-011). Original: [US4] Edit `pyproject.toml` `[project.optional-dependencies]`: `admesh = ["admesh2D>=1.0"]`; append `valence-domains>=<floor>` to `dev`. Set `<floor>` to the lowest version on PyPI that ships `valence_domains.manifest`; run `pip index versions valence-domains` (network allowed for the implementer) and check that it installs in the dev environment (FR-010, FR-011).
- [ ] ~~T018~~ SKIPPED (operator ruling 2026-10-10: no Valence code on consumer machines; spec FR-010/FR-011). Original: [US4] Add `pre_smooth: bool = False` to `run_pipeline`; lazy-import `admesh.quad_prep.smooth_for_quadrangulation`, and raise `ImportError` with the hint `pip install quadmesh[admesh]`; add a test that skips when admesh is absent (`src/quadmesh/pipeline.py`, `tests/test_pipeline_presmooth.py`).
- [ ] ~~T019~~ SKIPPED (operator ruling 2026-10-10: no Valence code on consumer machines; spec FR-010/FR-011). Original: [US4] In `tests/_mesh_provision.py`, when `valence_domains` imports, check every local `MANIFEST` key against the Valence manifest and raise a named error if one is missing; without it, use the local `MANIFEST` alone. Keep the SHA-1 pins and the download path. Add a unit test for both paths (FR-010, R8).

## Phase 6: US3, gaps tracked (P2)

- [x] T020 [US3] Add a "Sibling delegation (057)" table to `docs/MAPPING.md` with all 18 inventory rows, their disposition, and `downstream-api` for partial rows 6, 8, 9, 14, 15, 16, 17 (plus row 3 if T006 failed) (FR-008, SC-004).
- [x] T021 [US3] Save the final Valence `fetch_mesh` request text to `specs/057-sibling-dedupe/valence-fetch-mesh-request.md` (copied from the spec draft). Do not file it.

## Phase 7: US5, release-artifact hygiene (P2)

- [x] T022 [P] [US5] Extend `.release-ignore.toml` `[extend].exclude` with `experiments/`, `facts.yml`, `scripts/onstart_local.sh` (FR-014).
- [x] T023 [US5] Regenerate the blocks: `python ~/Projects/DomI/skills/release-integrity/scripts/release_ignore.py generate` (writes `.gitattributes`, `.zenodoignore`, `MANIFEST.in`); then `generate --check` exits 0 (FR-013). Fix the missing end marker in `MANIFEST.in` if the generator does not.
- [x] T024 [P] [US5] Replace the `/home/user/Valence/...` default in `scripts/exp_refuse_boundary_merge.py:156` with a path relative to the sibling checkout (R10).
- [x] T025 [P] [US5] Reword the path in `docs/benchmarks/refuse-boundary-merge-real-meshes.md:8` (R10).
- [ ] T026 [US5] Build and verify: `rm -rf dist && python -m build`; `git archive HEAD | tar t`; `release_ignore.py verify` on all three exits 0; the wheel and sdist member lists match FR-017; the grep for `/Users/` and `/home/[a-z]` over shipped files is empty (SC-006, SC-007).

## Phase 7b: Constitution sync (after T017)

- [x] T026a Amend `.specify/memory/constitution.md`. Line 56: change `chilmesh >= 0.4.0` to `chilmesh >= 1.5.0` (the floor set in T004). Line 18: replace the fixture path `03_CHILMesh_Test_Cases/01_.14_Files` with the current one, which is Valence-provisioned `tests/fixtures/meshes/` with a fallback to chilmesh-bundled `chilmesh/data`, per `tests/_mesh_provision.py:16-31`. Line 56 area: list `matplotlib >= 3.6` as required (FR-009). Bump the version from 0.1.0 to 0.2.0 (MINOR: guidance materially changed, no principle removed) and set Last Amended to the edit date (line 69). Prepend a Sync Impact Report HTML comment per `speckit-constitution` conventions: the version change, the modified sections (III, VI, Dependencies), and the templates checked. Principle VI ("Caveman Docs"): rewrite it so that human-facing docs (README, docs/, docstrings shown to users, issue and PR text) use the writing stack in order: `write-like-scientist` voice rules 1-10, then Golden rule G1-G17, then `asd-ste100-lens` STE + ADHD, then the tell scan. Caveman style stays for agent-facing files and terminal output (operator ruling 2026-10-10). The version stays at 0.2.0 (MINOR, a guidance change). The constitution itself is agent-facing, so the writing stack is not run on this task's edit.

## Phase 8: Writing stack (FR-020, after all content tasks)

Run per document: `docs/MAPPING.md` (057 section), `docs/benchmarks/refuse-boundary-merge-real-meshes.md` (edited line and paragraph), `specs/057-sibling-dedupe/valence-fetch-mesh-request.md`, the docstrings and warnings touched in T007, T008, T015, and T018, and `tests/fixtures/README.md` if T019 edits it.

- [x] T027 Voice: apply `write-like-scientist` rules 1-10 to each document listed above.
- [x] T028 Golden rule: remove G1-G17 tells from each document.
- [x] T029 Lens: apply `asd-ste100-lens` STE + ADHD to each document; keep technical terms (API names, file paths, version numbers) verbatim; the Golden rule wins on conflict.
- [x] T030 Tell scan last: Haiku scan, then Sonnet correction per `~/Projects/DomI/skills/write-like-scientist/references/ai-tells-scan.md`, with a fact add/drop audit; record 0 hard tells per document (SC-008). Rerun the tests if any docstring changed.

## Phase 9: Polish

- [x] T031 Run the full `pytest tests/`, with `--runslow` if available; confirm the no-interior-triangle gate was exercised (SC-001); confirm that `method="matching"` and `method="faithful"` still raise `ValueError` (FR-002); measure the net LOC change in `src/quadmesh/` with `git diff --stat` (SC-003).
- [ ] T032 Conventional commits on `development` (no push to `main`; no force push), one per phase.
- [ ] T033 Move specs to DomI: `bash ~/Projects/DomI/skills/speckit-pipeline/scripts/move_specs_to_domi.sh --apply`. This is the only move task across 056 and 057. Run it only after both implementations are done; it copies all of `specs/` (056 and 057) before it removes `.specify/` and `specs/` (plan R11). Confirm the DomI copy contains `specs/consumers/quadmesh/056-*` and `057-*`.

## Dependencies

T001 → T002 → T003 → T004, T005 → US1 (T006 → T007 → T008 → T009 → T010) → US2 → US4. US3 (T020) needs the T006 and T014 outcomes. T026a runs after T004 and T017. US5 (T022 to T026) depends only on T001 and can run in parallel with US1 to US4. Phase 8 runs after T020, T021, T025, and all docstring edits. T033 runs last.

## Parallel examples

- After T005, run T022, T024, and T025 in parallel with T006.
- Inside US2, T011 and T012 can run together.

## Implementation strategy

MVP = US1 (T001 to T010): the largest duplicate is removed behind a parity gate. Then US2 and US4 (mechanical), US3 (docs), US5 (release hygiene, independent), the writing stack, and the move.
