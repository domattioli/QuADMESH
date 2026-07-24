# Session 034 — 2026-07-24 (rotation hour-16)

## What changed
- **#98 measured at-scale on real ADCIRC meshes → CLOSED** (`d68cf6c`,
  development; rolling PR #115 rolled; #98 comment + close). The deferred
  "needs Valence read-PAT" validation gate was void — the real `.14` meshes are
  present in the Valence sibling checkout (`/home/user/Valence/registry_data/meshes/`),
  same pattern the #116 zoom-out audit flagged (blocker was access, not drainage).
- New `scripts/exp_refuse_boundary_merge.py` (measurement harness) +
  `docs/benchmarks/refuse-boundary-merge-real-meshes.md` (evidence). Additive
  only; no product/locked-module/faithfulness change.
- **#97 advanced** (comment, advance-only, no label flip): scoped its
  leftover-reduction next-steps against the #98 result (leftover-count ≠
  boundary-quality now that connectivity levers are dead).

## Key decisions / findings
- **Both connectivity-only boundary levers for #98/#90 are negative at full scale.**
  - Lever A `refuse_boundary_merge` (option A): **complete no-op** on all 6 meshes
    incl. WNAT_Onur (246k tris) — Δgeo_total = 0, skew bit-identical. Falsifies
    the session-031 at-scale hypothesis: the #90 ≥2-boundary-edge degenerate quads
    are manufactured by the **main per-layer pairing merge**, not the leftover
    handler option A intercepts.
  - Lever B boundary-only conditioning (`layers=[0]`, PR #94 machinery, run
    transiently — not merged, PR #94 stays "do NOT promote"): **flat-to-harmful**
    (Block_O 274→290, LakeErie 1684→1812 geo-tris; skew ↓). Connectivity rewiring
    can't fix a boundary-following quad whose shape is fixed by the domain polygon.
- **Conclusion:** #98's connectivity-only boundary hypothesis is negative; the
  live lever for the #90 quality tail is **geometric** (tangential boundary slide
  / geometric acceptance on the pairing merge), tracked in #90.
- Faithfulness invariant (0 interior geometric tris) held on every measured row.

## Verification
- Faithfulness gate `test_no_interior_tris` **36 passed** at HEAD before the run.
- `exp_refuse_boundary_merge.py` exit 0 on all 6 meshes; per-mesh interior-invariant
  audit PASS. C++ chilmesh backend (`chilmesh_cpp` 0.6.0.dev0) built in-container
  for at-scale speed (bit-equivalent to pure-Python).
- 1 Haiku dispatch (the measurement harness); orchestrator fixed the import,
  reviewed, and ran/verified before commit. Within budget.

## What comes next
- **#90 geometric lever** is now the sole live path for the boundary-quality tail:
  a point-moving op (tangential boundary slide with per-step validity guard, or a
  geometric acceptance criterion on the pairing merge). Non-trivial; needs its own
  spec/session. Any fix must not end in a global FEM pass (session-033: erasure).
- **#97 headroom bound** (per-layer optimal-matching vs every-other heuristic):
  scoped-and-ready, small/medium meshes only (max_weight_matching ≈47 s on one
  18k-node layer → infeasible at WNAT/ENPAC scale; report where computable).
- **#116** (needs-operator): spec-001 Draft / SC-007 MATLAB oracle / #109 CI-token
  decisions still owed by operator.
- Queue state: no clean `status: ready` code slice remains after #21 (closed
  2026-07-23) and #98 (closed today) — the two deliverables #116 flagged as
  wrongly-skipped are both resolved.

## Introspect (R5, consumer deposit → rolling PR #115 block)
- Dispatches used: 1 of 3 (measurement harness). Slice outcome: #98 measured +
  closed; #97 advanced. Smooth session, no tool failures.
- Pain (self-inflicted, minor): dispatched the harness with the wrong import
  (`from quadmesh.tri2quad import tri2quad`) — the public surface is
  `from quadmesh import tri2quad` (re-exported in `__init__`). Caught on first
  run, fixed inline (<30 lines, per budget). Lesson: confirm the package's public
  import surface before spec'ing a subagent. Not skill-worthy (#203 → note only).
- Pattern reinforced (matches #116): "queue drained" was false again — the #98
  blocker was mesh access, and the meshes were in the Valence sibling all along.
  Consumer sessions should probe the sibling checkout before deferring a
  real-mesh slice on a PAT gate.
