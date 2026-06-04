# Introspect Corpus — 2026-06-04T12Z

session_id: f1edcd31-af54-4db2-8e32-7569bbc3bcf1
repo: domattioli/QuADMesh
branch: daily-maintenance
date: 2026-06-04T12Z
model: claude-sonnet-4-6

## What changed

- **fix: regression 39bac0e** (`src/quadmesh/_tri_removal.py`, commit `c3e0695`)
  - `_split_opposing_tri` now returns `None` early when `np_id >= domain.points.shape[0]`
  - Removed the combined-pts-array logic introduced in `39bac0e`
  - Removed docstring paragraph erroneously describing the `work` param as required for buffered midpoints
  - Net: 4 lines added, 12 deleted

- **chore: PR #65 description updated** to reflect 2026-06-04T12Z session

- **chore: `development` branch created** from `daily-maintenance` at `c3e0695` per `branching.md` migration (DomI #196; `daily-maintenance` deprecated 2026-06-02)

## Root cause analysis (regression 39bac0e)

`edge_bisection` buffers the new midpoint in `work._extra_pts` (returns `np_id >= domain.points.shape[0]`). `_split_opposing_tri` is then called with that `np_id`. Before `39bac0e`, `_ccw_tri(…, domain.points)` with an out-of-bounds index raised `IndexError`, caught by `except Exception: pass` in `_faithful_per_layer`, effectively skipping the split. `39bac0e` made the function succeed using a combined pts array — which caused it to:
1. Overwrite `domain.connectivity_list[opp_id]` in an already-consumed layer
2. Append a new row `tri2` to `domain.connectivity_list`

Neither modification was tracked in `consumed`, so 54 orphan boundary tris appeared in the final mesh on `Test_Case_1.14`. Fix: early return.

## Test results

- `test_no_interior_tris.py`: 18/18 pass (all 3 `test_tri2quad_faithful_path` parametrizations pass)
- Fast suite: 240 pass, 4 skip, 0 fail

## Issues addressed

None from the open backlog (no `status: ready` issues besides #21 and #46 which remain deferred). Regression was a blocking test failure discovered during routine fast-suite run.

## Blockers / open

- `daily-maintenance` branch deprecated per DomI `branching.md` (issue #196 2026-06-02). `development` now exists. Future sessions should push to `development` directly. No existing PR for `development → main`; operator should open one or retarget #65.
- CH4 IE-before-OE interior heuristics (T017) and boundary OE-before-IE + walkability pre-pass (T018) still not implemented; `method="faithful"` must not be made default until those land.

## Pain points

- Subagent (Haiku) was dispatched to implement the fix per CLAUDE.md coding-dispatch rule. Worked well; completed in ~5 min. The `_split_opposing_tri` combined-pts approach from `39bac0e` was a well-intentioned change that hit an edge case in the layer-ordering invariant — a design note in the code or a targeted test for "no orphan tris after _split_opposing_tri" would have caught this at commit time.
