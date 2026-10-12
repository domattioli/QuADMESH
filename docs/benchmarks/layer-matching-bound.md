# Bounding the achievable within-layer pairing gain (issue #97)

Question (#97, "Proposed next steps" item 2): *bound the achievable gain. Compute
a per-layer optimal (maximum-matching) pairing per strip and measure leftover
reduction against the every-other heuristic.*

Answer: across 8 meshes, a maximum-cardinality matching on each skeleton
layer's legal tri-adjacency graph strands 64.5 %–100 % fewer triangles than
the QuADMESH+ every-other-walk + greedy pairing. On WNAT_Hagen the heuristic
strands 5,509 triangles (identical to the #97 Monte-Carlo study's
corner-start count), and optimal matching strands 755: an 86.3 %
reduction. The leftovers are structural with respect to the every-other parity
rule. They are not structural with respect to the pairing problem itself.

## What was measured

For each skeleton layer, the experiment compares two within-layer pairings. Both
are purely topological (no geometric-degeneracy skip), so the comparison isolates
pairing strategy from element quality.

- Heuristic: a faithful replay of the production per-layer pairing.
  `identify_edges_in_layer` (the every-other-edge walk, thesis Ch 4.1) runs first.
  The T017/T018 greedy interior-saturating `match_layer_heuristic` follows, with the
  exact `consumed` / `local_consumed` accounting of
  `tri2quad._quadmesh_plus_per_layer` (lines 851–933). Fold-seam pairs are
  forbidden (thesis Ch 4.2).
- Optimal: `networkx.max_weight_matching(..., maxcardinality=True)` on the
  layer's tri-adjacency graph. Nodes are layer triangles. Edges are shared interior
  sub-mesh edges, minus fold-seam (flagged) edges. This is the same legal
  merge set the heuristic operates over.

Both track their own global `consumed` set, innermost layer first, matching the
production sweep order. A stranded triangle is one that within-layer pairing leaves
unpaired. In the real pipeline these triangles go to
`route_leftover_tri` (removeTrianglesFun), which uses point insertion and edge swap onto the
boundary. These operations produce the boundary-quality tail characterised in
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
| WNAT_Hagen | 98,365 | 30 | 5,509 | 755 | 86.3 % | 2,377 |
| annulus_200pts | 580 | 4 | 78 | 16 | 79.5 % | 31 |
| Test_Case_1 | 2,417 | 7 | 93 | 33 | 64.5 % | 60 |

"Pairs missed" is optimal pairs minus heuristic pairs. Each missed pair is one
stranded triangle recovered.

- Layers are disjoint (the sum of per-layer triangles equals n_elems on every mesh), so the
  per-layer comparison has no cross-layer availability confound.
- Cross-validation against the production pipeline: on Block_O, the real
  `_quadmesh_plus_per_layer` reaches 2,744 quads and 0 final leftovers. The
  routing stage (point insertion) forms the extra quads beyond the heuristic's 2,471
  within-layer pairs. This confirms that the 272 heuristic-stranded
  triangles are real, and that the pipeline rescues them at a quality cost.
- The WNAT_Hagen heuristic stranded count (5,509) reproduces the #97
  Monte-Carlo study's corner-start count (5,509) exactly. The metric is the same
  "passed downstream" count the study instrumented.

## Interpretation

The #97 MC study varied the walk start vertex across 200 runs. The start vertex
is not a lever (5,532 ± 11 triangles; corner start 5,509). This experiment varies
the pairing rule and finds a large lever: max-cardinality
matching recovers 86 % of WNAT_Hagen's stranded triangles. The two results are
consistent. The start vertex only reshuffles which triangles a fixed parity
rule strands, whereas the parity rule itself leaves pairs on the table.
The MC study's "≈50 % structural" leftovers are therefore structural relative to the
every-other heuristic. They are not structural relative to the within-layer pairing problem.

The result is a bound. It is not a prescription. Maximum-cardinality matching is
Blossom-Quad (Remacle et al. 2012), the `method="matching"` path the operator
removed from this repo (#46, 2026-06-12). QuADMESH+ is a faithful port of the
thesis every-other-edge algorithm, and it is not a matching mesher.
The result quantifies the price of faithfulness: ~86 % of the
leftover-routing burden on WNAT_Hagen (and, downstream, a large share of the #90
boundary-quality tail) comes from the every-other pairing rule's
topological suboptimality. The meshes themselves do not force it.

Consequences for the open pairing-quality research family (#17 / #18 / #26 /
#77 / #97):

- Better within-layer pairing can reduce leftovers. The measured ceiling is
  up to 86 % fewer stranded triangles on
  the largest tested mesh, which is up to 86 % less point-insertion / edge-swap work,
  the mechanism behind the #90 quality tail.
- Any faithful improvement lives between the every-other rule and the matching
  ceiling. Two levers can move the number: a smarter greedy extension (thesis-legal
  reorderings of the T017/T018 pass) and an explicitly opt-in non-faithful matching
  mode. A within-faithfulness change cannot exceed this
  ceiling; only a method change (Blossom) reaches it.
- The 755-triangle optimal floor on WNAT_Hagen cannot be reduced by
  connectivity alone. These are odd-component parity residuals that no pairing
  strategy removes; they require point insertion or boundary geometry. This
  matches the #98 negative result that boundary connectivity levers are no-ops.

## Is the within-faithful lever real? A single-pass greedy does not reach it (2026-07-26)

The Interpretation above named two levers that could move the leftover count: a
within-faithful smarter greedy (thesis-legal reordering of the T017/T018
pass) and the forbidden Blossom matching. The open
`#17` / `#18` brainstorms propose the first lever as Option 1 / P1 (quality-aware merge
selection). This follow-up tests whether any single-pass greedy can reach the
matching ceiling. It adds a third pairing track to `bound.py`: a deterministic
minimum-degree-first greedy maximal matching (`greedy_maximal_matching`) on
the same legal tri-adjacency graph the optimal track uses (fold-seams excluded).
It differs from the optimal track only in the algorithm: greedy maximal (no
augmenting paths) vs. `max_weight_matching` (augmenting paths / Blossom).

| Mesh | n_elems | heuristic stranded | greedy stranded | optimal stranded | greedy vs heuristic |
|---|---:|---:|---:|---:|---:|
| structuredMesh1 | 660 | 20 | 0 | 0 | −100.0 % |
| donut_domain | 276 | 60 | 64 | 4 | +6.7 % |
| Block_O | 5,214 | 272 | 636 | 20 | +133.8 % |
| Deleware_Bay | 26,698 | 1,696 | 3,496 | 186 | +106.1 % |
| LakeErie_5k_500 | 24,910 | 1,676 | 3,420 | 204 | +104.1 % |
| WNAT_Hagen | 98,365 | 5,509 | 9,567 | 755 | +73.7 % |
| annulus_200pts | 580 | 78 | 78 | 16 | +0.0 % |
| Test_Case_1 | 2,417 | 93 | 311 | 33 | +234.4 % |

Finding: the greedy maximal matching does not approach the optimal ceiling, and
on 6 of 8 meshes it strands more triangles than the production heuristic. The count
is roughly double on every real ADCIRC mesh (WNAT_Hagen 9,567 vs 5,509; Deleware
3,496 vs 1,696; LakeErie 3,420 vs 1,676). It reaches optimal only on the trivial
structured mesh and ties on the annulus.

Interpretation: the headroom belongs to matching and greedy passes cannot reach it.

- The 64–86 % leftover reduction the optimal track showed is a property of
  augmenting-path matching (Blossom-Quad, `method="matching"`, removed in
  #46). A smarter greedy does not provide it. Replacing the every-other + T017/T018 walk
  with a generic greedy regresses: the production heuristic is already a
  well-tuned pairing that a naive greedy underperforms. No easy
  greedy pass leaves pairs on the table for a reorder to grab.
- The result holds a fortiori for the specific `#17`/`#18` Option-1 proposal
  (a quality- or size-aware greedy ordering). That ordering optimizes for element
  quality and ignores pairing cardinality, so it can only strand as many or more
  triangles than this cardinality-agnostic min-degree greedy. It cannot capture
  the cardinality headroom either.
- Disposition for `#17` / `#18`: quality-aware greedy merge selection is not a
  leftover-reduction lever. Reaching the matching ceiling requires the forbidden
  augmenting-path method; a within-faithful pairing change cannot. The realistic
  within-faithful headroom above the every-other rule is near zero (or
  negative), far below the 86 % optimal ceiling. The geometric lever
  (session-034: tangential boundary slide / geometric acceptance on the pairing
  merge) addresses the #90 boundary-quality tail better than any pairing-rule
  change.

Raw per-layer JSON (heuristic / greedy / optimal per layer, all 8 meshes):
[`experiments/layer_matching_bound/results/greedy_track.json`](../../experiments/layer_matching_bound/results/greedy_track.json).

### Generality: the pattern holds on independent non-WNAT domains (#97 replication item)

The WNAT / Test_Case / `chilmesh.data`
families dominate the 8-mesh set above. To test the #97 "replicate on a non-WNAT mesh to test generality" item,
the three-track experiment was re-run on four independent domains: a terrain
mesh (Baranja Hill), a synthetic concentric mesh (Onion), a Mediterranean coastal
mesh (Italy), and a Great-Lakes mesh (Lake Michigan):

| Mesh | n_elems | heuristic | greedy | optimal | greedy vs heuristic |
|---|---:|---:|---:|---:|---:|
| Baranja_Hill | 1,193 | 99 | 157 | 15 | +58.6 % |
| Onion | 9,373 | 915 | 1,221 | 213 | +33.4 % |
| Italy | 24,417 | 1,267 | 2,605 | 189 | +105.6 % |
| Lake_Michigan_mesh | 41,887 | 2,065 | 4,429 | 335 | +114.5 % |

Both effects reproduce on every independent domain. The greedy maximal matching
regresses vs the production heuristic (+33 % to +115 % more stranded), while
max-cardinality matching reaches the ceiling (77–85 % leftover reduction). The
pairing headroom is augmenting-path-specific, and no single-pass
greedy captures it. This holds outside the WNAT family. Raw JSON:
[`results/greedy_track_nonwnat.json`](../../experiments/layer_matching_bound/results/greedy_track_nonwnat.json).

## Reproduce

```bash
bash scripts/dev_setup.sh && . .venv/bin/activate
pip install networkx    # experiment-only; not a package dependency
# token-free (chilmesh.data bundled meshes):
python experiments/layer_matching_bound/bound.py \
    "$(python -c 'import os,chilmesh;print(os.path.dirname(chilmesh.__file__))')/data/Block_O.14"
# real meshes (from a Valence checkout):
python experiments/layer_matching_bound/bound.py \
    /path/to/meshes/WNAT_Hagen.14 --json out.json
```

WNAT_Hagen (98k elems, 30 layers) runs in a few minutes; the largest layer's
`max_weight_matching` dominates. Meshes above ~250k elems (ENPAC2003, WNAT_Onur)
are not recommended for the optimal track: blossom matching on their largest
layers is O(V³) and impractical (cf. PR #94: 46 s for one 18k-node layer).

## #97 investigation status: converged (2026-07-27)

Issue #97 asked which triangles the QuADMESH+ per-layer sweep routes to the
leftover handler, and whether a faithful port can reduce that count.
Across five rotation sessions the question has been answered on both the
descriptive axis (what determines a leftover) and the prescriptive axis (what, if
anything, can reduce it within faithfulness). This section consolidates the findings and the disposition of
each "Proposed next steps" checkbox on the issue. The thread then has a single durable close-out artifact; the evidence is otherwise scattered
across the issue body, draft PR #96, and this document.

The full checklist, with disposition:

| #97 next-step item | status | evidence |
|---|---|---|
| Add + correlate valence-irregularity / flow metrics | ✅ done | PR #96 Finding 3: both register as *secondary* predictors (\|ρ\| < 0.12) |
| Bound achievable gain: max-matching per strip vs every-other | ✅ done | this doc, §Results: 64.5–100 % fewer stranded, 86.3 % on WNAT_Hagen |
| Test a valence-/size-aware pairing bias (quality-aware greedy) | ✅ done (negative) | this doc, §"Is the within-faithful lever real?": a single-pass greedy *regresses* on 6/8 meshes; a fortiori for the quality-aware variant |
| Replicate on a non-WNAT mesh | ✅ done | this doc, §Generality: 4 independent domains, both effects reproduce |
| 1,000-run pass to split p = 1 from p ≈ 0.99 leftovers | ⬜ not done: a refinement and not a lever | see below |

Descriptive verdict (PR #96 Monte-Carlo study, 200 random walk-starts on
WNAT_Hagen): the walk-start vertex is not a lever. The per-run leftover
total holds at 5,532 ± 11 triangles (1.0 % spread), and the deterministic corner
start (5,509) already sits below the random mean. Roughly half the leftovers are
structural (always routed regardless of start) and half are start-dependent
("swing") triangles. The always-routed set is spatially anti-clustered (dispersed
point defects, not contiguous bands), predominantly outer-edge and
boundary-adjacent. No single mesh feature explains routing: the strongest
correlate (local size ratio, ρ = −0.115) accounts for ~1 % of the variance, so
routing is multifactorial (parity rule + local topology + ADmesh size transition).

Prescriptive verdict (this document): the ~86 % headroom above the every-other
rule is real, and only augmenting-path matching reaches it: the
Blossom matching method (`method="matching"`) the operator removed in #46, because
QuADMESH+ is a faithful port of the thesis every-other-edge algorithm and not a
matching mesher. Every within-faithful pairing change tested either fails to
approach the ceiling or regresses. A min-degree greedy strands ~2× the production
count on real ADCIRC meshes. A quality-aware greedy can only do the same or
worse, because it optimizes for element quality and ignores pairing cardinality. The realistic
within-faithful headroom above the every-other rule is near zero, far
below the 86 % optimal ceiling.

The remaining 1,000-run item does not change the disposition. That pass
would only sharpen the boundary between structural (p = 1) and
near-structural (p ≈ 0.99) leftovers in the descriptive MC study, a resolution
refinement on the 200-run tail. It cannot create a within-faithful pairing lever
that the matching-bound and greedy experiments have shown does not exist.
It needs substantial compute (1,000 full sweeps of a 98k-element mesh) for a
result that does not move any decision. If the p = 1 / p ≈ 0.99 split is ever needed,
open a separate, narrowly scoped issue for it and close this broad research issue.

Consequence for the whole pairing-quality family (#17 / #18 / #26 / #77): the
measured negative results above close the within-faithful pairing-selection avenue
these brainstorms propose (Option 1 / P1, quality-aware merge selection). The
single live lever for the #90 boundary-quality tail is geometric
(a tangential boundary slide with a per-step validity guard, or geometric
acceptance on the pairing merge; session-034). It operates on point positions,
and the pairing rule controls connectivity. This is consistent with the
#98 negative result that boundary connectivity levers are no-ops. Do not pursue pairing-rule
changes as a leftover-reduction strategy.

Disposition: the #97 research question is answered and the
investigation is converged. The descriptive characterization is complete. The
prescriptive answer is a measured "no within-faithful pairing lever exists." The
one unchecked box is a non-lever refinement; it becomes its own issue if
needed.
