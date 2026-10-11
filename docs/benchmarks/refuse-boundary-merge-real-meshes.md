# #98: boundary-layer treatment on real ADCIRC meshes (measured)

At-scale validation of the two connectivity-only boundary levers proposed for
issue [#98](https://github.com/domattioli/QuADMESH/issues/98) / the #90 boundary
degeneracy. Both were characterized offline only (chilmesh.data
fixtures); sessions 031/032 deferred real-ADCIRC validation on a "needs Valence
read PAT" gate. That gate no longer applies: the real `.14` meshes are in the
local mesh directory. The deferred at-scale measurement ran under the current `quadmesh+` pipeline.

Harness: `scripts/exp_refuse_boundary_merge.py` (baseline vs
`refuse_boundary_merge=True`) + inline boundary-only-conditioning probe. Backend:
chilmesh C++ (`chilmesh_cpp` 0.6.0.dev0, `backend_info().selected == "cpp"`;
bit-equivalent to pure-Python per CHILmesh v1.0.0). Faithfulness invariant
(interior geometric-tri count) is checked on every row and holds at 0 throughout.

Geometric triangle = a 4-distinct-index quad with a corner angle ≥178° (or a
zero-length edge). `interior` = no element edge is a domain-boundary edge;
`boundary` = ≥1 boundary edge (`_geo_tri_counts` in `tests/test_no_interior_tris.py`).

## Lever A: `refuse_boundary_merge=True` (#98 option A)

Refuses the `route_leftover_tri` merge for leftover boundary tris with
`n_bdy ∈ (2,3)`, emitting them as boundary triangles instead of degenerate quads.

| Mesh | n_tris_in | base geo_total | optA geo_total | Δ geo_total | interior (base/optA) | base skew_mean | optA skew_mean |
|---|---|---|---|---|---|---|---|
| Test_Case_1 | 2,417 | 97 | 97 | 0 | 0 / 0 | 0.5593 | 0.5593 |
| Block_O | 5,214 | 274 | 274 | 0 | 0 / 0 | 0.5418 | 0.5418 |
| LakeErie_5k_500 | 24,910 | 1,684 | 1,684 | 0 | 0 / 0 | 0.5071 | 0.5071 |
| Deleware_Bay | 26,698 | 1,724 | 1,724 | 0 | 0 / 0 | 0.5275 | 0.5275 |
| WNAT_Hagen | 98,365 | 5,723 | 5,723 | 0 | 0 / 0 | 0.4993 | 0.4993 |
| WNAT_Onur | 246,186 | 15,730 | 15,730 | 0 | 0 / 0 | 0.5047 | 0.5047 |

Result: option A is a complete no-op on every real mesh. The geo_total, quad count, and skew
are bit-identical between baseline and option A, up to and including WNAT_Onur
(246k tris / 130,958 quads). This extends the session-032 offline finding
(Block_O unchanged) to real ADCIRC meshes at full scale. It falsifies the
session-031 at-scale hypothesis that option A would clear the #90 ≥2-boundary-edge
degenerate tail (93% of ENPAC bad quads). Those quads are untouched at every size.

Mechanism: the main per-layer pairing merge (two boundary tris → one
~180° quad) manufactures the #90 degenerate boundary quads. Leftover-tri routing
does not. `refuse_boundary_merge` only
intercepts the leftover handler, so it never touches the quads that
carry the degeneracy. An earlier offline run confirmed that the count is invariant under
`point_insert=False` and `remove_boundary_tris=False`.

## Lever B: boundary-only triangulation conditioning (#98 literal hypothesis)

The issue's stated idea: restrict the PR #94 conditioning pass to the boundary
layer only (`condition_triangulation(domain, layers=[0])`). It rewires that layer's
unmatched tris with point-preserving edge flips, then runs `quadmesh+`. The
measurement used the PR #94 machinery transiently (not merged; PR #94 is "do NOT promote").

| Mesh | L0 swaps | unmatched (before→after) | base geo_total → cond | interior | base skew_mean → cond |
|---|---|---|---|---|---|
| Test_Case_1 | 7 | 7 → 0 | 97 → 97 | 0 → 0 | 0.5593 → 0.5597 |
| Block_O | 34 | 34 → 0 | 274 → 290 | 0 → 0 | 0.5418 → 0.5379 |
| LakeErie_5k_500 | 200 | 201 → 1 | 1,684 → 1,812 | 0 → 0 | 0.5071 → 0.5019 |

Result: flat-to-harmful. Boundary-layer conditioning clears the unmatched-tri
count (its own objective). It increases the degenerate boundary-quad
population (Block_O +16, LakeErie +128) and slightly lowers mean skew.
The interior invariant holds. This matches PR #94's whole-mesh conditioning verdict
(flat-to-harmful; quality-aware acceptance = 0 swaps accepted). Restricting the
scope to the boundary layer does not rescue it.

Why: conditioning rewires connectivity and moves no points. The domain boundary polygon
fixes the shape of a boundary-following quad, so
rewiring the boundary layer redistributes pairings without removing the geometric
degeneracy. It can manufacture more ~180° quads than it clears.

## Conclusion for #98

Both connectivity-only boundary levers fail on real ADCIRC meshes:

- Option A (refuse leftover merges): no-op, because the degeneracy is outside the leftover path.
- Boundary-only conditioning: flat-to-harmful, because points are fixed and rewiring cannot fix geometry.

The live lever for the #90 boundary-quality tail is geometric: a point-moving op
(tangential boundary slide, or a geometric
acceptance criterion on the pairing merge itself). That is #90's domain. #98's
connectivity-conditioning hypothesis is answered negative.
