# Session 032 — 2026-06-21 (rotation hour-19, maintenance track)

## What changed
- **`feat: add opt-in refuse_boundary_merge flag (#98 option A)`** (`5f588f8`,
  development). Executed the slice sessions 030/031 deferred on timeout. Default-OFF
  flag threaded `cli → pipeline → tri2quad_routine → _quadmesh_plus_per_layer →
  route_leftover_tri`. ON: leftover boundary tris with `n_bdy ∈ (2,3)` emit as
  boundary triangles (mixed tri/quad) instead of degenerate ~180° quads.
  Files: `_tri_removal.py`, `tri2quad.py`, `pipeline.py`, `cli.py`,
  `tests/test_no_interior_tris.py` (new `test_refuse_boundary_merge_keeps_invariant`),
  `tests/test_unification_api_contract.py` (param-list sync).
- Code dispatched to Haiku subagents per coding-dispatch policy; orchestrator
  reviewed full diff + verified offline before commit.

## Key decisions / findings
- **FINDING reframes #98 — option A is a near no-op on the offline fixtures.**
  Block_O **unchanged (273)**; structuredMesh1 20→19. Block_O's boundary
  degenerate quads are NOT leftovers: count is invariant under `point_insert=False`
  **and** `remove_boundary_tris=False` → they're manufactured by the **main
  per-layer pairing merge** (two boundary tris → one ~180° quad), upstream of
  `route_leftover_tri`. The session-031 "93% from `_tri_removal.py:347`" claim was
  WNAT/ENPAC-scale (#90); it does NOT generalize to offline-testable meshes.
- **Shipped anyway, honestly.** Flag is correct, harmless (default OFF
  byte-identical), and is the at-scale lever (#90, PAT-gated). The honest negative
  offline result is pinned by a gate test to prevent re-characterization churn
  (the session-030 anti-pattern). Did NOT claim a quality win that does not exist
  offline (#168 honesty).
- **Default OFF = byte-identical.** Baseline gate (Block_O 273, structuredMesh1 20,
  interior 0) unchanged. Faithfulness invariant (zero interior tris) holds under
  the flag ON too.
- **#48 CLOSED (2026-06-18)** → maintenance track = issue queue (top = #98,
  `status: ready`). No checklist comment on closed #48 (consistent w/ session-031).
- **`.domi-pin` current** — `0a96f17` == DomI `main` HEAD (sibling clone
  `/home/user/DomI`), manifest `b5dd8ad…`. No `/sync`.

## Verification
- `QUADMESH_NO_FETCH=1 pytest tests/` (offline) → **87 passed / 55 skipped** at
  `5f588f8` (+2 from new flag-ON test; was 85/55). No regression.
- `pytest tests/test_no_interior_tris.py` → **16 passed / 18 skipped** (faithfulness
  + both #98 gates green).
- Full diff reviewed by orchestrator; refused_idx defined on all reachable paths
  (only `method=="layered"` reaches the assembly; both sub-branches set it).

## What comes next
- **The real offline frontier is the pairing-merge acceptance criterion**: reject
  a merge whose resulting quad has a ≥~178° corner and route both tris to leftover
  instead. This (not leftover routing) is what governs Block_O's 273. Overlaps
  PR #96 (Monte-Carlo which-tris-get-routed). Multi-file, gate-able offline on
  Block_O/structuredMesh1 → speckit + Haiku, fresh budget.
- Operator/auto-mode call still open: make a mixed-mesh contract (A/merge-reject
  default ON) vs guarded geometric slide (B, all-quad). Both deviate from MATLAB
  port; both faithful re: interior invariant. See #98 thread.
- At-scale WNAT/ENPAC validation of option A still needs the Valence read PAT
  (standing gate, unchanged).
