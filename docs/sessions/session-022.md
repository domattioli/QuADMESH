# Session 022 — 2026-06-16 (hour-11 rotation, maintenance track)

## What changed
- **Faithfulness gate hardened** (`38029a7`, `development`). The non-negotiable
  invariant is "zero interior residual triangles." The existing gate checked
  *topological* interior tris only — a quad with a ~180° corner (4 distinct
  indices, but geometrically a triangle) slipped through. Ported
  `test_no_interior_geometric_tris` from the experimental conditioning branch
  (`claude/mesh-quality-preprocessing-wplrz2`, PR #94 / #98): detects the flat
  corner, classifies boundary-vs-interior by edge incidence, asserts **zero
  interior geometric tris** (boundary ones allowed, same as residual boundary
  tris). Verified passing on development output before commit.
- **`Block_O.14` added to the gate's FIXTURES.** Provisions offline via the
  `chilmesh.data` fallback (session-021's #93 fix), so the full faithfulness
  gate now executes on a second, richer mesh (2743 elems) in CI-without-PAT
  instead of only `structuredMesh1`. Verified Block_O: 0 interior tris,
  quad-pure, 0 bowties, conforming, 0 interior geometric tris.
- **PR #96 retargeted** base `main` → `development` per `branching.md` (author
  had invited it; `main` as a feature-PR base violates the development→main
  flow).
- Rolling PR **#95** body refreshed; checklist comment posted on MADMESHing#48.

## Key decisions
- **Did NOT port `test_no_degenerate_quads` from #94.** Its bound
  (`aspect<0.01` count ≤ max(5, 1% elems)) only holds on that branch's unshipped
  CCW-reorder + leftover-deferral boundary-quality fixes. On `development` the
  near-degenerate quads (Block_O 274, structuredMesh1 20) are **boundary**
  180°-corner quads — which the invariant *permits*. Porting it would gate
  `development` red on unmerged research (#90/#98 territory). Only the interior
  geometric check is invariant-faithful on the current tree.
- **Block_O is a legitimate offline gate fixture** — it is one of the two meshes
  `chilmesh` ships byte-exact, sha-verified against the pinned Valence manifest;
  reusing it offline is not re-vendoring (cache stays gitignored).

## Verification
- Env: `dev_setup.sh` OK; chilmesh editable from `/home/user/CHILmesh` + `quadmesh[dev]`.
- `QUADMESH_NO_FETCH=1 pytest tests/test_no_interior_tris.py` → **8 passed / 22 skipped** (was 5 passed).
- `QUADMESH_NO_FETCH=1 pytest tests/` → **97 passed / 72 skipped** (was 93/67).
- `test_no_interior_geometric_tris` confirmed **executed** (not skipped) + PASSED on Block_O + structuredMesh1; PAT-gated 5 skip.

## Branch / PR
- `development` @ `38029a7`, pushed. Rolling draft PR **#95** (`development → main`), body refreshed.
- PR #96 (Monte-Carlo study) retargeted to `development`. PR #94 (experimental conditioning) untouched — kept draft per its own decision.

## What comes next
- **Operator gates (unchanged):** #93 cross-repo Valence read PAT secret (now only
  blocks the remaining 5-mesh CI coverage of the gate, not the whole gate); #90
  ENPAC ≥2-boundary-edge skew tail (deviation call); #46 onion hero domain
  (gated on ADMESH-Domains#93 `.14`).
- Research/brainstorm queue needs operator green-light: #17/#18/#21/#26/#38/#76/#77/#97/#98.
- **#98 (boundary-layer-only conditioning)** is the natural next code frontier once
  green-lit — the geometric-tri detector landed here makes the boundary-vs-interior
  distinction it relies on now part of the gate. The boundary 180°-corner quad
  population (the thing #98 wants to reduce) is exactly what `test_no_degenerate_quads`
  would bound once those fixes ship.

## Open chilmesh issues
- None newly hit. The five filed (#132/#133/#134/#138/#139) remain closed + consumed.

## Pains (→ matrix, no new request:skill per #203)
```yaml
pain_points:
  - pain: "No Valence PAT in routine env — large/most fixtures unprovisionable offline; only the 2 chilmesh.data meshes (Block_O, structuredMesh1) run the gate. CI faithfulness coverage stays PAT-gated (#93)."
    repo: QuADMESH
    severity: med
    frequency: recurring
    domi_issue: ""
    saved_min: 0
    wasted_tok: 0
    missing_skill: ""
  - pain: "Valuable test/code authored on an unmerged research branch (geometric interior-tri detector on PR #94's branch) is invisible to development's gate until someone cherry-picks the invariant-safe subset. Cost: a diff + per-mesh verification pass to separate the faithful part (interior check, passes) from the research part (degenerate bound, would fail). Manual; no tooling flags 'invariant test exists on a branch but not on default'."
    repo: QuADMESH
    severity: low
    frequency: occasional
    domi_issue: ""
    saved_min: 0
    wasted_tok: 0
    missing_skill: ""
```
