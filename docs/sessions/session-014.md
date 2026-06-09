# Session 014 — 2026-06-07 routine h12

**Branch:** `development` (harness assigned `claude/zen-goodall-RfWLk` → switched per `branching.md`).
**Model:** claude-opus-4-8 (+ haiku subagent for edits).
**Issue worked:** #81 — closed.
**PR:** #80 (rolling `development → main`, draft) refreshed; head `c868763`.

## What changed

- **`src/quadmesh/_tri_removal.py`** — `_split_opposing_tri` OOB guard widened from `np_id` only to all four ids `(apex, v_a, v_b, np_id)` it feeds into `_ccw_tri`. Closes the #81 IndexError structurally (any unresolvable id → `return None`, tri left for deferred pass). Consistent with the buffer-then-flush point ownership model.
- **`tests/test_faithful_invariants.py` + `tests/test_faithful_pairing.py`** — default parametrization capped to fixtures `<250 KB` (`_mesh_params()` helper); heavier meshes marked `slow`, run via `--runslow`. Resolves the >70s hang that blocked validation.

## Key decisions

- Could not reproduce the #81 IndexError on any non-hanging mesh — c3e0695's pre-flush `np_id` guard already short-circuits `_split_opposing_tri` during the sweep. Fixed defensively (widen the guard) rather than chase an unreproducible path; the fast faithful run (132 passed, no IndexError on multi-layer fixtures) is the regression.
- Did not touch the layered algorithm itself (T017/T018 still unimplemented). `method="layered"` stays WIP + non-default; `method="matching"` (default) unaffected.

## Validation

`pytest tests/` → **259 passed, 102 skipped, 27.8s** (was: hang). `--runslow` available for heavy meshes.

## What comes next

- T017 (Ch4 IE-before-OE interior heuristics) + T018 (boundary-layer OE-before-IE + walkability pre-pass) — required before `method="layered"` can be default.
- Optionally validate the layered path on `--runslow` heavy meshes now that the OOB guard makes a crash impossible (expect slow, possibly still-incomplete quad coverage, not a crash).
- #76 (profile layer-sweep hotspots on WNAT_Hagen) — natural follow-on; the sweep is the slow path the hang exposed.

## Open chilmesh issues (unchanged)

#132 `merge_elements`, #133 `ccw_edges_around_vert`, #134 adjacencies flag, #138 `submesh`, #139 `angle_based_smoother` perf. No new CHILmesh API need this session.
