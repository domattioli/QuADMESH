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

## Follow-up — real meshes + quality-aware (2026-06-15, session 019)

Two of the three "next steps" below were executed this session: (1) re-run on real
ADCIRC `.14` meshes, and (2) implement quality-aware swap acceptance. Meshes were
read directly from the local Valence registry checkout
(`/workspace/Valence/registry_data/meshes/`, overridable via `QUADMESH_REGISTRY_DIR`);
no HuggingFace fetch needed. `bench_conditioning.py` gained `--mesh <full_id|name|path>`
(resolves full_ids like `WNAT/onur@v1` through the registry `manifest.toml`) and
`--quality-aware`.

### Real meshes — default conditioning (`--mesh ...`)

| Mesh        | Base aspect | Cond aspect | Asp Δ   | Base skew | Cond skew | Skew Δ  | Unmatched B→A | Swaps | Interior tris |
|-------------|-------------|-------------|---------|-----------|-----------|---------|---------------|-------|---------------|
| Test_Case_1 | 0.5558      | 0.5572      | +0.0014 | 0.6959    | 0.6946    | −0.0012 | 33 → 17       | 8     | 0 → 0         |
| Test_Case_2 | 0.5198      | 0.5198      |  0.0000 | 0.6542    | 0.6542    |  0.0000 | 19 → 19       | 0     | 0 → 0         |
| Test_Case_3 | 0.5258      | 0.5245      | −0.0014 | 0.6600    | 0.6593    | −0.0007 | 15 → 9        | 3     | 0 → 0         |
| Test_Case_4 | 0.5220      | 0.5223      | +0.0003 | 0.6551    | 0.6553    | +0.0002 | 46 → 32       | 7     | 0 → 0 (1 bdry)|
| Block_O     | 0.5466      | 0.5464      | −0.0002 | 0.6806    | 0.6801    | −0.0005 | 20 → 14       | 3     | 0 → 0         |

Same pattern as the synthetic meshes: conditioning reduces the topological
antagonist count wherever swaps fire, but final quad quality moves by ≤0.0014,
mixed sign, indistinguishable from noise. **Zero interior residual tris in every
case (invariant holds with `precondition=True`).** Test_Case_4 keeps one *boundary*
tri (allowed).

### Real meshes — quality-aware acceptance (`--mesh ... --quality-aware`)

Swap accepted only if it BOTH reduces unmatched count AND does not lower the worst
incident triangle quality (`worst_after >= worst_before - 1e-9`, metric `aspect_ratio`).

| Mesh        | Cond aspect | Asp Δ   | Unmatched B→A | Swaps |
|-------------|-------------|---------|---------------|-------|
| Test_Case_1 | 0.5559      |  ~0     | 33 → 33       | 0     |
| Test_Case_2 | 0.5198      |  0.0000 | 19 → 19       | 0     |
| Test_Case_3 | 0.5258      |  0.0000 | 15 → 15       | 0     |
| Test_Case_4 | 0.5220      | −0.0000 | 46 → 46       | 0     |
| Block_O     | 0.5463      | −0.0003 | 20 → 20       | 0     |

**Decisive result: quality-aware mode accepts ZERO swaps on every mesh.** Every
edge swap that reduces the unmatched count also lowers the worst incident triangle
quality, so the quality gate rejects all of them — conditioning collapses to a
no-op. This says the matching objective and the geometric-quality objective are in
direct tension here: you cannot buy matchability without paying skew.

The small non-zero deltas that survive at **0 swaps** (e.g. Block_O −0.0003) are
pure pipeline noise: with `precondition=True` the domain is rebuilt
(`CHILmesh(conn, pts.copy())`) before `tri2quad`, and the rebuild perturbs element
ordering / layer derivation enough to shift final quality by ~0.0003. **That noise
floor is the same order as the entire signal we were chasing** — further
confirmation the effect is not real.

### WNAT_Onur (`WNAT/onur@v1`) — conditioning computationally infeasible

| | n_pts | n_elems (tri) | layers | largest layer | baseline pipeline | conditioned |
|--|-------|---------------|--------|---------------|-------------------|-------------|
| WNAT_Onur | 127,572 | 246,186 | 39 | 18,482 tris | aspect 0.5011 / skew 0.6365, 129,916 quads, 275 s | **not run** |

A single `nx.max_weight_matching(maxcardinality=True)` on the largest layer's dual
graph (18,482 nodes) takes **46.75 s**. The conditioning inner loop recomputes that
matching once per candidate swap (≈ passes × unmatched × 3 per layer × 39 layers),
so a full run is many hours-to-days. The generic blossom matching is the bottleneck
(O(V³)-ish, sparsity does not help networkx's implementation). Conditioning as
written does not scale to production-size ADCIRC meshes.

## Decision (2026-06-15)

**Do not promote. PR #94 stays a draft; `precondition` stays opt-in, default OFF.**

- Hypothesis unsupported on real meshes (default mode: flat/mixed, ≤0.0014, at/below
  pipeline rebuild-noise floor ~0.0003).
- Quality-aware acceptance — the documented next step — makes the pass a no-op
  (every matchability-improving swap is quality-negative), so it cannot rescue the
  result.
- Infeasible at scale (WNAT_Onur: one matching call 46.75 s × thousands).

The machinery, the real-mesh `--mesh` harness, the quality-aware mode, and this
clean negative result are kept for the record and for the one remaining idea below.

## Still not pursued

- Align the conditioning objective with the production `identify_edges` path-walk
  pairing rather than a generic max-cardinality matching. This is the only avenue
  not yet falsified — but it is a larger redesign (and would not fix the WNAT-scale
  matching cost), so it is parked unless a concrete reason to revisit appears.
