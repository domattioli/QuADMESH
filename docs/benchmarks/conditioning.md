# Triangulation conditioning preprocessor — benchmark

Experimental variant: walk mesh layers 0→N, detect triangles **antagonistic to a
clean intra-layer perfect matching**, and rewire them with edge swaps (thesis
Fig 3.2) before handing the triangulation to the normal `quadmesh+` pipeline.
The hypothesis: pre-conditioning the triangulation yields better quad topology
and higher overall quality.

Opt-in only: `run_pipeline(mesh, precondition=True)` or `quadmesh ... --precondition`.
Default behaviour is unchanged.

## How to reproduce

```bash
bash scripts/dev_setup.sh        # or: pip install -e . chilmesh networkx
. .venv/bin/activate
python scripts/bench_conditioning.py
```

Meshes are `chilmesh.examples` (annulus, donut, block_o, structured) — used here
as stand-in synthetic domains until the thesis `.14` fixtures are supplied.
Quality metric: `element_quality(..., metric="aspect_ratio")`, mean/min over the
final quad mesh.

## Results (2026-06-15, chilmesh dev 1.2.0)

| Mesh       | Baseline mean | Cond. mean | Mean Δ   | Residual tris (base→cond) | Per-layer unmatched (before→after) |
|------------|---------------|------------|----------|---------------------------|------------------------------------|
| annulus    | 0.2624        | 0.2599     | −0.0025  | 0 → 0                     | 16 → 10                            |
| donut      | 0.2409        | 0.2409     |  0.0000  | 0 → 0                     | 4 → 4                              |
| block_o    | 0.5466        | 0.5464     | −0.0002  | 0 → 0                     | 20 → 14                            |
| structured | 0.4751        | 0.4755     | +0.0004  | 0 → 0                     | 0 → 0                              |

Min quality is 0.0000 in every case for both baseline and conditioned — a
pre-existing degenerate-element artifact on these example meshes, unrelated to
conditioning.

## Finding (honest)

**The hypothesis is not supported on these synthetic meshes.** Conditioning does
what it claims at the *topological* level — it measurably reduces the count of
triangles antagonistic to a per-layer perfect matching (annulus 16→10, block_o
20→14) — but this does **not** translate into better final quad quality. Mean
quality moves by ≤0.0025 and is slightly *negative* on annulus. The zero
interior-residual-tri invariant is preserved in all cases.

Likely reasons the topological win doesn't reach final quality:

1. **Objective mismatch.** `quadmesh+` pairs tris via the `identify_edges`
   path-walk, not via maximum-cardinality matching. Fewer "antagonistic" tris by
   the matching-graph definition is not the same target the production pairing
   optimises, so the gain doesn't carry through.
2. **Topology vs. geometry tension.** An edge swap that makes two tris pairable
   can hand `tri2quad` a worse-shaped diagonal, trading matchability for skew.
3. **Post-process washout.** `fem_smoother` + doublet/QVM cleanup largely
   re-equalise quality regardless of the incoming triangulation.

## Next steps if pursued

- Re-run on the real thesis meshes (`Test_Case_1.14`, `Block_O.14`) — synthetic
  ring meshes may not be representative.
- Make swap acceptance **quality-aware**: only accept a swap when it both reduces
  unmatched count and does not lower the worst incident element quality.
- Align the conditioning objective with the production `identify_edges` pairing
  rather than a generic max-cardinality matching.
