# Tasks: 059 boundary-layer routing

Format: `[ID] [P?] [Story] Description`. Every commit must keep `tests/test_no_interior_tris.py` green.

## Phase 1: Baseline

- [x] T001 Confirm 057 is committed on `development` before any edit (`git log` shows the 057 commit; `git status` clean for 057 files). If not, wait.
- [x] T002 Capture baseline (no new script file; inline pytest/python snippet): run current `tri2quad` defaults on Block_O, annulus_200pts, donut_domain, structuredMesh1 and every other bundled mesh; record tri count, interior-residual count, mean and worst skew into `specs/059-boundary-layer-routing/baseline-quality.md`. Use 058 metric code if landed, else `tests/test_quality.py` helpers.

## Phase 2: Diagnose

- [x] T003 With `:937` flipped locally (not committed), log which `route_leftover_tri` branch (`src/quadmesh/_tri_removal.py:336-359`) each surviving tri took on Block_O/annulus/donut and whether it is in `consumed`. Confirm or reject plan hypothesis; record result in plan.md "Root-cause" section.

## Phase 3: US1 + US2 fix (P1)

- [x] T004 [US1] Add `_is_boundary_layer(li) -> li == 0` helper in `src/quadmesh/tri2quad.py`; use it in `_layer_priority` (`:683`), matcher call (`:915`), routing (`:937`); fix comment `:936` to cite `removeTrianglesFun.m:12` `iLayer == 1`. Verify SC-005: `grep -rn 'nl - 1' src/quadmesh/` shows no boundary predicate.
- [x] T005 [US2] `route_leftover_tri` (`src/quadmesh/_tri_removal.py:308`) returns a converted/unchanged status; in `tri2quad.py:943-958` do not add unchanged tris to `consumed`, so they reach `leftover_idx` and `_remove_boundary_tris` (`:1097`). Keep refused-tri semantics. (Fallback per plan if T003 rejects hypothesis.) Commit together with T004.
- [x] T006 [US1] Remove `xfail(strict=True)` from `tests/test_boundary_layer_index.py`; test passes.
- [x] T007 [P] [US2] Add `tests/test_boundary_routing_quality.py`: 0 tris total on the four named meshes with defaults; 0 interior residual tris on all bundled meshes; a single-layer mesh (`nl == 1`) case gives unchanged output vs baseline.
- [x] T008 [US2] Run `pytest tests/`; the 11 tests failing under naive flip pass. Any changed expectation documented with reason in commit body. FR-011: existing method tests (`quadmesh+`, `layered`, `ValueError` for `matching`/`faithful`) pass unchanged.

## Phase 4: US3 quality gate (P2)

- [x] T009 [US3] Extend T007 test (or `tests/test_quality_regression.py` baselines) with per-mesh asserts against the 059 reference ("after" columns in `baseline-quality.md`; operator ruling 2026-10-10, option c): mean skew >= 0.99 * reference, worst skew >= reference. The structuredMesh1 drop 0.6963 -> 0.6466 is expected. Fill "after" column in `baseline-quality.md`.

## Phase 5: Docs (writing stack: write-like-scientist, asd-ste100-lens)

- [x] T010 [P] `docs/algorithm.md`: remove defect note `:90`; table row `:119` → "same" with `removeTrianglesFun.m:12` cite; describe layer-0 routing + closing pass.
- [x] T011 [P] `docs/MAPPING.md`: map `removeTrianglesFun` onMeshBoundary → `li == 0`; note closing pass as Python addition; note `CM.nLayers == Domain.nLayers` guard not ported (full-domain sweep).
- [x] T012 [P] `CHANGELOG.md` `[0.3.0]` → `### Fixed`: per-layer sweep flagged innermost layer as boundary; now layer 0, invariant and quad purity kept. Edit only that section.

## Phase 6: Absorbed 057 T012/T013 (separate commit; 059 IDs T013/T014 are unrelated to 057 numbering)

- [ ] T013 Replace `merge_tri_pair` use in `src/quadmesh/tri2quad.py` with `chilmesh.quad_from_tri_pair`; delete `src/quadmesh/_topology.py`; `grep -rn _topology src tests` empty; quality table identical to post-T009. If not identical: revert, hand back to CoS, do not block release.
- [x] T014 After 057 commit: rerun `tests/test_dedupe_parity.py` and `tests/fixtures/baselines/`; rebaseline only with CoS approval (approved 2026-10-10, operator ruling option c).

## Phase 7: Release gate (CoS-coordinated, operator)

- [ ] T015 Operator runs `GITHUB_TOKEN=<pat> python scripts/fetch_fixtures.py`, then `pytest tests/` and the T002 quality table on Valence fixtures (ENPAC etc.); 0 interior residual tris, no regression beyond tolerance; sign-off recorded in `baseline-quality.md`. Blocks 0.3.0 tag.

## Dependencies

T001 → T002 → T003 → T004+T005 (one commit) → T006, T007, T008 → T009 → T010-T012 [P] → T013 → T014 → T015.

## Coverage (analyze)

FR-001/002 T004 | FR-003/004 T007 | FR-005 T005, T011 | FR-006 T009 | FR-007 T006 | FR-008 T008 | FR-009 T010, T011 | FR-010 T012 | FR-011 T008 | FR-012 T015 | FR-013 T011 | SC-005 T004 | SC-006 T015
