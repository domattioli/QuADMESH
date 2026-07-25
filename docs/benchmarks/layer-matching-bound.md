# Bounding the achievable within-layer pairing gain (issue #97)

**Question (#97, "Proposed next steps" item 2):** *bound the achievable gain — compute
a per-layer optimal / maximum-matching pairing per strip and measure leftover
reduction against the every-other heuristic.*

**Answer:** across 8 meshes, a maximum-cardinality matching on each skeleton
layer's legal tri-adjacency graph strands **64.5 %–100 % fewer** triangles than
the QuADMESH+ every-other-walk + greedy pairing. On WNAT_Hagen the heuristic
strands **5,509** triangles (identical to the #97 Monte-Carlo study's
corner-start count) where optimal matching strands **755** — an **86.3 %**
reduction. The leftovers are structural *with respect to the every-other parity
rule*, not with respect to the pairing problem itself.

## What was measured

For each skeleton layer, two within-layer pairings are compared, both purely
topological (no geometric-degeneracy skip, so the comparison isolates pairing
*strategy* from element *quality*):

- **Heuristic** — a faithful replay of the production per-layer pairing:
  `identify_edges_in_layer` (the every-other-edge walk, thesis Ch 4.1) followed
  by the T017/T018 greedy interior-saturating `match_layer_heuristic`, with the
  exact `consumed` / `local_consumed` accounting of
  `tri2quad._quadmesh_plus_per_layer` (lines 851–933). Fold-seam pairs are
  forbidden (thesis Ch 4.2).
- **Optimal** — `networkx.max_weight_matching(..., maxcardinality=True)` on the
  layer's tri-adjacency graph: nodes = layer triangles, edges = shared interior
  sub-mesh edges, **minus fold-seam (flagged) edges** — i.e. the same legal
  merge set the heuristic operates over.

Both track their own global `consumed` set, innermost layer first, matching the
production sweep order. A *stranded* triangle is one left unpaired by within-layer
pairing; in the real pipeline these are precisely the triangles routed to
`route_leftover_tri` (removeTrianglesFun) — point-insertion / edge-swap onto the
boundary — the operations that produce the boundary-quality tail characterised in
issue #90.

Script: [`experiments/layer_matching_bound/bound.py`](../../experiments/layer_matching_bound/bound.py).
Raw per-layer JSON: [`experiments/layer_matching_bound/results/`](../../experiments/layer_matching_bound/results/).

## Results

| Mesh | n_elems | layers | heuristic stranded | optimal stranded | reduction | pairs missed |
|---|---:|---:|---:|---:|---:|---:|
| structuredMesh1 | 660 | 5 | 20 | 0 | 100.0 % | 10 |
| donut_domain | 276 | 3 | 60 | 4 | 93.3 % | 28 |
| Block_O | 5,214 | 9 | 272 | 20 | 92.6 % | 126 |
| Deleware_Bay | 26,698 | 17 | 1,696 | 186 | 89.0 % | 755 |
| LakeErie_5k_500 | 24,910 | 17 | 1,676 | 204 | 87.8 % | 736 |
| WNAT_Hagen | 98,365 | 30 | **5,509** | 755 | 86.3 % | 2,377 |
| annulus_200pts | 580 | 4 | 78 | 16 | 79.5 % | 31 |
| Test_Case_1 | 2,417 | 7 | 93 | 33 | 64.5 % | 60 |

*"pairs missed" = optimal pairs − heuristic pairs; each missed pair is one
stranded triangle recovered.*

- **Layers are disjoint** (Σ per-layer triangles = n_elems on every mesh), so the
  per-layer comparison has no cross-layer availability confound.
- **Cross-validated against the production pipeline.** On Block_O, running the real
  `_quadmesh_plus_per_layer` reaches 2,744 quads and 0 final leftovers — the
  extra quads beyond the heuristic's 2,471 within-layer pairs are formed by the
  routing stage (point-insertion), confirming the 272 heuristic-stranded
  triangles are real and are exactly what the pipeline rescues at a quality cost.
- **The WNAT_Hagen heuristic stranded count (5,509) reproduces the #97
  Monte-Carlo study's corner-start count (5,509) exactly**, confirming this
  metric is the same "passed downstream" count the study instrumented.

## Interpretation

The #97 MC study varied the walk **start vertex** across 200 runs and found it is
not a lever (5,532 ± 11 triangles; corner start 5,509). This experiment varies
the **pairing rule** instead and finds it is a large lever: max-cardinality
matching recovers 86 % of WNAT_Hagen's stranded triangles. The two results are
consistent — the start vertex only reshuffles which triangles a *fixed parity
rule* strands, whereas the parity rule itself is what leaves pairs on the table.
So the MC study's "≈50 % structural" leftovers are structural relative to the
every-other heuristic, not relative to the within-layer pairing problem.

**This is a bound, not a prescription.** Maximum-cardinality matching is
Blossom-Quad (Remacle et al. 2012) — the `method="matching"` path the operator
**removed** from this repo (#46, 2026-06-12) precisely because QuADMESH+ is a
*faithful* port of the thesis every-other-edge algorithm, not a matching mesher.
The result therefore quantifies the **price of faithfulness**: ~86 % of the
leftover-routing burden on WNAT_Hagen (and, downstream, a large share of the #90
boundary-quality tail) is attributable to the every-other pairing rule's
topological suboptimality, and is *not* an unavoidable property of the meshes.

**Consequences for the open pairing-quality research family (#17 / #18 / #26 /
#77 / #97):**

- The premise that better within-layer pairing can reduce leftovers is
  **confirmed with a measured ceiling** — up to 86 % fewer stranded triangles on
  the largest tested mesh, i.e. up to 86 % less point-insertion / edge-swap work,
  the mechanism behind the #90 quality tail.
- Any faithful improvement lives **between** the every-other rule and the matching
  ceiling: a smarter greedy extension (thesis-legal reorderings of the T017/T018
  pass), or an explicitly opt-in non-faithful matching mode, are the two levers
  that can move the number. A within-faithfulness change cannot exceed this
  ceiling; only a method change (Blossom) reaches it.
- Conversely, the **755-triangle optimal floor on WNAT_Hagen is irreducible by
  connectivity alone** — those are odd-component parity residuals that no pairing
  strategy removes; they require point insertion or boundary geometry, matching
  the #98 negative result that boundary *connectivity* levers are no-ops.

## Reproduce

```bash
bash scripts/dev_setup.sh && . .venv/bin/activate
pip install networkx    # experiment-only; not a package dependency
# token-free (chilmesh.data bundled meshes):
python experiments/layer_matching_bound/bound.py \
    "$(python -c 'import os,chilmesh;print(os.path.dirname(chilmesh.__file__))')/data/Block_O.14"
# real meshes (from a Valence checkout):
python experiments/layer_matching_bound/bound.py \
    /path/to/Valence/registry_data/meshes/WNAT_Hagen.14 --json out.json
```

WNAT_Hagen (98k elems, 30 layers) runs in a few minutes; the largest layer's
`max_weight_matching` dominates. Meshes above ~250k elems (ENPAC2003, WNAT_Onur)
are not recommended for the optimal track — blossom matching on their largest
layers is O(V³) and impractical (cf. PR #94: 46 s for one 18k-node layer).
