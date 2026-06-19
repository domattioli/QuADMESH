# Session 027 — 2026-06-19 (rotation hour-3, maintenance track)

## What changed
- **New bench `scripts/bench_boundary_layer.py`** (`963aed0`, feat, additive/read-only).
  Reproduces #90's boundary-layer artifact offline on the two PAT-free meshes
  (Block_O + structuredMesh1, chilmesh.data fallback). Reports geometric-triangle
  counts (total/interior/boundary) + a bad-quad boundary-contact breakdown.
  Serves #98's baseline metrics without pulling the rejected whole-mesh
  conditioning machinery (PR #94). Does **not** touch the locked sweep.

## Key decisions / findings
- **#48 closed (completed 2026-06-18)** → maintenance track. Worked the issue
  queue; #98 (`status: ready`, top actionable code item) was the target.
- **T019 is a no-op offline — corrects prior handoff guidance.**
  `_quadmesh_plus_per_layer` returns `leftover_idx == 0` on BOTH Block_O and
  structuredMesh1 (the T017/T018 greedy matcher saturates them). So the unwired
  `handle_isolated_tris` (T019, defined `_tri_removal.py:360`, **never called**)
  and any isolated-tri/leftover-routing change has **zero effect** on the only
  offline-testable meshes. Validating T019 genuinely needs the Valence PAT meshes
  (Test_Case_*/WNAT/ENPAC) where leftovers exist. The handoff/README "T019
  startable offline" is technically true but **not verifiable offline** — flagged
  on #98. (Did NOT edit CLAUDE.md/README to correct this — routine-doc edits are
  operator-gated per /act-autonomously; recorded on #98 + here instead.)
- **min=0.000 quads are the known #90/#98 boundary geometric-triangle artifact**,
  not a fixable point-placement bug: in-sweep `edge_bisection`/`edge_insertion`
  turn a leftover tri into a "quad" by adding a collinear midpoint → 180° corner →
  skew 0. No point placement fixes a 3-vtx tri → 4-vtx quad without changing
  geometry or pairing with a neighbour. That's exactly #98's premise.
- **Chose "rederive minimal bench" (handoff option B) over cherry-picking PR #94.**
  The conditioning machinery (`precondition.py`, `bench_conditioning.py`) still
  lives only on the non-promoted draft branch `claude/mesh-quality-preprocessing-wplrz2`.
  Whether to cherry-pick it or rewrite a boundary-layer-restricted pass remains
  an **operator/auto-mode architectural call** — left open, flagged on #98.
- Coding-dispatch policy honored: bench script written + bug-fixed by Haiku
  subagents; orchestrator specced, reviewed, verified before commit.
- `.domi-pin` current (`e369b5c` == DomI `main` HEAD via sibling `/home/user/DomI`).
  No `/sync` needed. No DomI bug found → no hub-loop issue filed.

## Verification
- `bash scripts/dev_setup.sh` OK → `QUADMESH_NO_FETCH=1 pytest
  tests/test_no_interior_tris.py` → **12 passed / 18 skipped** at HEAD `963aed0`
  (unchanged; bench is additive).
- `python -m py_compile scripts/bench_boundary_layer.py` OK.
- Bench output (default 0.3): Block_O mean=0.542 min=0.000 bad=303/2743,
  geo-tri total=273 interior=**0** boundary=273, ≥2-bdy-edge bad = 276 (91.1%).
  structuredMesh1 mean=0.696 bad=20/340, 100% of bad ≥2-bdy-edges, interior geo=0.
  Threshold flag consistency bug (header vs bucket denominator) caught in review +
  fixed; 0.3 output byte-identical, 0.5 now consistent (buckets sum 100%).

## What comes next
- **#98 conditioning experiment** still needs a PAT-equipped (or hosted-runner)
  session — leftovers/isolated-tris only exist on Test_Case_*/WNAT/ENPAC, absent
  from chilmesh.data. Use the new bench for before/after once those meshes load.
- Operator decision: cherry-pick PR #94 conditioning machinery onto `development`
  vs rewrite a boundary-layer-restricted pass.
- T019 wiring is only worth attempting alongside a PAT mesh that actually has
  isolated leftovers; do not wire it blind (no offline signal).

## Branch / PR state
- Branch `development` @ `963aed0`, pushed; rolling PR #100 (`development → main`)
  body updated with this batch. No new branch, no new PR.

## Open chilmesh issues
- None new. The five filed API issues (#132/#133/#134/#138/#139) remain closed +
  consumed.

## Introspection (R5)
- **What worked:** Verify-don't-assume paid off — measured `leftover_idx == 0`
  before wiring T019, avoiding a blind no-op change to the sweep. Baselining first
  turned a vague "quality tuning" roadmap line into a concrete, evidence-backed #98
  comment + reusable bench.
- **Pain (recurring):** Valence cross-repo read PAT gate. The chilmesh fallback
  makes the faithfulness gate + bench run offline on 2 meshes, but those 2 meshes
  have **zero leftovers**, so the entire leftover/isolated-tri/conditioning
  problem space (#98, T019, #90 at scale) is invisible offline. The offline
  meshes validate the invariant but cannot exercise the quality-improvement code.
  - *matrix-row:* `repo=QuADMESH | pain=valence-pat-gate | freq=recurring | impact=offline-meshes-have-zero-leftovers→conditioning/T019/#98-unexercisable-offline (invariant gate runs, quality-improvement path does not) | fix=operator: add Valence read PAT secret to autonomous env (CI piece closed in #93)`
