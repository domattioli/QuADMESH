# Tasks: Hierarchical Smoothing Routine

**Input**: Design documents from `.specify/specs/056-hierarchical-smoother/`
**Prerequisites**: plan.md, spec.md (clarified ×5), research.md, data-model.md, contracts/api.md

**Tests**: Constitution Principle III mandates test-first per module → test tasks included.

**Organization**: Grouped by user story (US1 = fast opt-in smoothing at parity, US2 = quality lift via converged patches, US3 = strategy comparison report).

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [x] T001 Verify dev env: `. .venv/bin/activate && python -c "import chilmesh, quadmesh; print(chilmesh.__version__)"`; run `pytest tests/ -q -x --co -q | tail -3` to confirm collection green before any edit (baseline state)

## Phase 2: Foundational (blocking for all stories)

- [x] T002 Create `src/quadmesh/hierarchical_smooth.py` with module docstring (caveman style, spec/issue refs), imports, and `select_region(mesh, policy="skew", *, frac=0.075, layers=(0,), dev=2, dilate=True) -> np.ndarray` implementing the three policies per contracts/api.md + research.md R3/R4: skew (worst-frac by `element_quality("skew")`, id tie-break, 1-ring dilation via Vert2Elem), layer (from `mesh.layers`; ValueError if layers absent), valence (interior-vertex valence deviation ≥ dev, 1-ring dilation). Pure, deterministic, sorted-unique output.
- [x] T003 Add patch construction to `src/quadmesh/hierarchical_smooth.py`: `_build_patches(mesh, elem_ids, min_interior=4) -> list[Patch]` — connected components over Edge2Elem (BFS seeded ascending elem id), tiny-component merge-or-skip, per-patch vertex compaction (new→old `vert_map`), submesh `CHILmesh(conn_sub, pts_sub, compute_layers=False, compute_adjacencies=True, build_spatial_indices=False, validate=False)`, `free_mask` = NOT on submesh `boundary_edges()`. `Patch` as lightweight dataclass per data-model.md.
- [x] T004 [P] Write unit tests in `tests/test_hierarchical_smooth.py` for T002+T003 on an inline synthetic quad grid with an injected distorted band (no fixtures needed): policy determinism (two calls bitwise-equal), skew policy selects the distorted band, empty selection case (`frac` tiny + perfect grid), layer ValueError on layer-less mesh, patch components disjoint, free_mask excludes rim + true boundary, min_interior merge/skip.

## Phase 3: User Story 1 — fast opt-in hierarchical smoothing at parity (P1) 🎯 MVP

**Goal**: `hierarchical_smoother()` default plan (local-FEM-only) + `post_process_routine(hierarchical=True)` supplement composition; parity quality; invariant + determinism; default paths untouched.

**Independent test**: `pytest tests/test_hierarchical_smooth.py -q` green on synthetic meshes; fixture-gated integration case runs when token present; full existing suite green with opt-in absent.

- [x] T005 [US1] Add patch solve loop to `src/quadmesh/hierarchical_smooth.py`: `_solve_patch(patch, eps=1e-3, max_patch_iter=10) -> int` — iterate `post_process._balendran_smooth(patch.submesh)`, apply coords, halt on patch-mean-skew improvement < eps or cap, best-so-far revert on worsening pass (FR-007); returns iterations used. Assert pinned rows unchanged (debug-level check cheap enough to keep).
- [x] T006 [US1] Add orchestrator `hierarchical_smoother(...)` per contracts/api.md to `src/quadmesh/hierarchical_smooth.py`: selection → fallback check (frac > fallback_frac → `fem_smoother(n_iter=3)`, fell_back=True, FR-012) → patches → per-patch solve (ascending patch order) → write-back via vert_map[free_mask] → `_fix_bowties` (FR-010) → optional `HierarchicalResult` (timings dict: selection/patch_build/solves/total; n_selected/n_patches/patch_iters). Empty selection skips FEM stage (FR-013). Export from `src/quadmesh/__init__.py`.
- [x] T007 [US1] Wire supplement composition into `src/quadmesh/post_process.py::post_process_routine`: new kwargs `hierarchical=False, hierarchical_opts=None`; truthy → run `hierarchical_smoother(mesh, **opts_subset)` then `fem_smoother(mesh, n_iter=hierarchical_opts.get("n_global", 1))` in place of the existing `fem_smoother(mesh, n_iter=n_smooth_iter)` call; False → code path and call sequence byte-identical to today (SC-005). Mirror kwarg passthrough in `src/quadmesh/pipeline.py::run_pipeline`.
- [x] T008 [US1] Extend `tests/test_hierarchical_smooth.py`: synthetic end-to-end — hierarchical output boundary coords bitwise-equal to input boundary (FR-008); non-selected coords bitwise-equal on default plan (FR-003); determinism (two runs bitwise-identical, SC-006); post_process_routine(hierarchical=False) output equals pre-change snapshot on a synthetic mesh; hierarchical=True path returns valid mesh (no zero-area elems, no orphan verts).
- [x] T009 [US1] Fixture-gated integration test in `tests/test_hierarchical_smooth.py` (skip w/o fixtures, repo pattern): Test_Case_1 through tri2quad + `post_process_routine(hierarchical=True)` → `test_no_interior_tris` invariant helpers pass (FR-009/SC-004); mean/median skew ≥ baseline−0.005 and sub-0.30 count ≤ baseline (SC-002) vs freshly measured `fem_smoother(n_iter=3)` baseline on a deep-copied snapshot (R6).

**Checkpoint**: US1 = shippable MVP.

## Phase 4: User Story 2 — quality lift from converged patches (P2)

- [x] T010 [US2] Verify + tune convergence affordability in `src/quadmesh/hierarchical_smooth.py`: ensure defaults (eps=1e-3, max_patch_iter=10) let patches run past 3 effective passes when improving; add regression test asserting ≥1 synthetic patch case iterates >3 and mesh-wide mean skew after hierarchical strictly exceeds the 3-pass-global result on the distorted-band synthetic mesh (SC-003 analog at unit scale).
- [ ] T011 [US2] Add fixture-gated SC-003 check to the bench path (T012's script, `--assert-quality-lift` flag) so the strict-lift claim is measured on ≥1 real mesh, recorded in the results JSON.

## Phase 5: User Story 3 — strategy comparison report (P3)

- [x] T012 [US3] Create `scripts/bench_hierarchical_smooth.py` per contracts/api.md: pipeline-to-pre-smoothing snapshot once per mesh, deep-copy per variant; variants = policies {skew, layer, valence} × orderings {local-only, local+cheap, cheap+local} plus baseline `fem_smoother(n_iter=3)` and supplement (pre-pass + n_global=1); BenchRecord rows (wall_s end-to-end per Q2, mean/median skew, sub030_count, invariant_pass, speedup_vs_baseline) → `<out>.md` + `<out>.json`; nonzero exit if any variant fails the invariant.
- [x] T013 [US3] Implement guarded cheap-global stage in `src/quadmesh/hierarchical_smooth.py` (`stage_plan` support incl. `"cheap_global"` complement-scope truss/Laplacian with whole-stage skew revert guard per research.md R7; FR-005/FR-006 orderings) + unit test: guard reverts a deliberately-degrading cheap pass.
- [x] T014 [US3] Run bench ladder: Test_Case_1 + Block_O (+ WNAT_Onur if fixture token present); write results to `output/hier_smooth_bench_<mesh>.{md,json}`; record recommended default (policy + ordering) with numbers in spec.md Decision log section (append); note SC-001 status (met/unmet/deferred-to-token-session).

## Phase 6: Polish

- [x] T015 Run full suite `pytest tests/ -q`; fix regressions; `bash -n` new script; update `docs/MAPPING.md` only if post_process public surface changed (kwargs count → yes, one row note).
- [x] T016 Update README "Status & Roadmap"/pipeline docs snippet with the opt-in (one short paragraph, caveman) + spec-056 pointer; commit chain per repo discipline.

## Dependencies

- Phase 2 → everything.
- US1 (T005–T009) → US2 (T010–T011) and US3 bench meaning (baseline comparisons).
- T013 before full T012 sweep variants incl. cheap orderings (T012 can land with local-only variants first if needed).
- T014 last in US3.

## Parallel opportunities

- T004 ∥ T005 (tests for foundational vs solver dev, different files).
- T010 ∥ T012 skeleton.
- Within T012, per-mesh runs are independent.

## Implementation strategy

MVP = Phases 1–3 (US1). US2 is a defaults-verification + assertion increment. US3 converts the
experiment into evidence and picks the shipped default. Fixture-token-less containers: all
synthetic tests + Test_Case_1-independent logic still land; WNAT_Onur gate defers to a
token-equipped session and is recorded as such in T014.
