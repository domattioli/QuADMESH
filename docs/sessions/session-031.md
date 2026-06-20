# Session 031 — 2026-06-20 (rotation hour-11, maintenance track)

## What changed
- **No code change.** Verified-green + located the #90/#98 boundary frontier in
  code + posted a concrete design-fork finding on #98. Docs-only (this handoff).

## Key decisions / findings
- **#48 CLOSED (2026-06-18)** → maintenance track = issue queue (top = #98,
  `status: ready`). No slice to claim; #48 closed → no checklist comment.
- **Verified rolling PR #100 genuinely green at HEAD `0df4204`** (honest
  re-verification, not a claim relay): `bash scripts/dev_setup.sh` OK →
  `QUADMESH_NO_FETCH=1 pytest tests/` → **85 passed / 55 skipped** (55 =
  PAT-gated `.14` fixtures). Faithfulness + boundary geo-tri gate:
  `test_no_interior_tris.py` → **14 passed / 18 skipped**. Invariant holds.
- **NEW code-located finding on #98** (not re-measurement — broke the
  characterize-the-same-numbers churn session-030 flagged). The #90 degenerate
  ≥2-boundary-edge quads (93% of bad) are manufactured at ONE branch:
  `src/quadmesh/_tri_removal.py:347-349` — `on_mesh_boundary and n_bdy in (2,3)`
  → `edge_insertion` forms a quad with 2–3 edges on the boundary polygon →
  near-180° degenerate.
- **Design fork named** (operator/scientific call; neither violates zero-INTERIOR
  invariant — thesis permits boundary tris):
  - **A** refuse the merge → leave a *boundary triangle*. One-branch change;
    removes degenerate quads BUT yields mixed tri/quad output w/ many boundary
    tris (ENPAC ~20k vs thesis "≤1 typical"). Offline-gateable.
  - **B** validator-guarded tangential boundary slide → keep all-quad (the #18/Q4
    lever; unguarded → edge crossings, reverted). Larger.
  - #94 topology conditioning ruled out (proven no-op).
- **Recommended implementable slice** (autonomous-safe, no contract change):
  ship **A as opt-in flag, default OFF** (mirrors #94 `precondition`) so the
  quality-vs-mixed-mesh cost is measurable offline before any default change.
  Multi-file thread (CLI→pipeline→tri2quad→_quadmesh_plus_per_layer→
  route_leftover_tri) → speckit + Haiku → **deferred on timeout discipline**
  (~20 tool calls this rotation). Next rotation executes in fresh budget.
- **`.domi-pin` current** — `0a96f17` == DomI `main` HEAD (sibling clone
  `/home/user/DomI`), manifest `b5dd8ad…` unchanged. No `/sync` needed.
- Docs-only → orchestrator work; Haiku coding-dispatch not triggered.

## Verification
- `pytest tests/` (offline) → 85 passed / 55 skipped at `0df4204`. No regression.
- `pytest tests/test_no_interior_tris.py` → 14 passed / 18 skipped (gate green).

## What comes next
- **Execute the recommended slice: opt-in `refuse_boundary_merge` flag (option
  A), default OFF.** Inject at `_tri_removal.py:347-349`; thread the flag through
  pipeline/CLI. Gate with `test_boundary_geo_tri_baseline` (total drops, interior
  stays 0). Speckit + Haiku; fresh session budget.
- Operator/auto-mode call: make A default (mixed-mesh contract) vs do B (guarded
  geometric slide, all-quad). Both deviate from MATLAB port; both faithful re:
  interior invariant. See #98 thread for the located injection point + fork.
- At-scale WNAT/ENPAC validation still needs the Valence read PAT (unchanged
  standing gate — noted, not re-flagged).
