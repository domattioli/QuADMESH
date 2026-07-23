# Size-function drift on real meshes (#21)

Durable record of the `scripts/size_drift_report.py` measurement on **real,
non-uniform-`h` ADCIRC meshes**, run under the current `method="quadmesh+"`
pipeline. This closes the gap left by the earlier synthetic-only and
old-`method="matching"` runs (see issue #21 thread) — the real-mesh
confirmation previously blocked on Valence mesh availability.

## What is measured

For each mesh, `h_local(v)` is recovered from the **input** triangulation as the
mean length of the unique edges incident to each vertex. The ratio
`|edge| / h_local` (evaluated at the nearest input vertex to each edge midpoint,
so it is robust to vertices being added, removed, or moved) is reported at three
pipeline stages:

- `input-tris` — the input triangular mesh (baseline; ratio ≈ 1 by construction)
- `post-tri2quad` — after `tri2quad_routine` (`method="quadmesh+"`)
- `post-smooth` — after `post_process_routine` (doublet / QVM / cleanup +
  `fem_smoother`)

A ratio inside `[0.5, 2.0]` means the mesh honours the input size function to
within a factor of two locally. `frac in [0.5,2.0]` is the fraction of edges
inside that band — the issue's acceptance criterion.

## Results (2026-07-23, `method="quadmesh+"`, real meshes)

### Test_Case_1 (baseline, near-uniform)

| stage | n_edges | p5 | p50 | p95 | mean | frac in [0.5,2.0] | min | max |
|---|---|---|---|---|---|---|---|---|
| input-tris | 3736 | 0.892 | 0.998 | 1.120 | 1.002 | 1.000 | 0.776 | 1.566 |
| post-tri2quad | 2535 | 0.886 | 0.996 | 1.120 | 1.000 | 0.999 | 0.361 | 1.562 |
| post-smooth | 2409 | 0.635 | 0.949 | 1.286 | 0.962 | 0.994 | 0.190 | 2.020 |

### LakeErie_5k_500 (graded `h`, 5000 → 500)

| stage | n_edges | p5 | p50 | p95 | mean | frac in [0.5,2.0] | min | max |
|---|---|---|---|---|---|---|---|---|
| input-tris | 38179 | 0.788 | 0.999 | 1.230 | 1.003 | 1.000 | 0.603 | 1.732 |
| post-tri2quad | 25729 | 0.789 | 1.005 | 1.234 | 1.007 | 1.000 | 0.291 | 1.732 |
| post-smooth | 24444 | 0.620 | 0.951 | 1.345 | 0.963 | 0.990 | 0.161 | 2.314 |

### Deleware_Bay_hmin_100_hmax_20000 (real-world graded `h`, 200× contrast)

| stage | n_edges | p5 | p50 | p95 | mean | frac in [0.5,2.0] | min | max |
|---|---|---|---|---|---|---|---|---|
| input-tris | 41157 | 0.820 | 0.996 | 1.193 | 1.002 | 1.000 | 0.493 | 2.074 |
| post-tri2quad | 27816 | 0.820 | 0.996 | 1.193 | 1.002 | 1.000 | 0.288 | 2.074 |
| post-smooth | 26482 | 0.634 | 0.952 | 1.330 | 0.963 | 0.992 | 0.170 | 3.671 |

## Conclusion — acceptance branch (a), benign, bound documented

1. **The `[0.5, 2.0]` p95 bound holds with margin on every mesh.** Post-smooth
   p95 is 1.29 / 1.35 / 1.33; frac-in-band is 0.990–0.994. The pipeline does not
   systematically violate the input size contract, including on the 200×-contrast
   Delaware mesh.
2. **`tri2quad` is benign.** p50, mean, and frac-in-band are essentially
   unchanged from the input across all three meshes. The merge lowers only the
   `min` (a thin tail of short merge-diagonal / boundary-pad edges), not the bulk
   distribution.
3. **Smoothing is the drift source, and it is bounded.** The `fem_smoother`
   optimises angle quality with no `h`-awareness, so it contracts the median
   ~5% and widens the p5/p95 spread ~20–40%; ≤1% of edges leave the band. The
   worst tail (`max = 3.67`) is on the highest size-contrast mesh (Delaware),
   exactly as the issue hypothesised.
4. **Tighter than the removed `matching` method.** Under the old
   `method="matching"` (removed by #46) the same real meshes gave post-smooth
   p95 ≈ 1.5 and max 3.8–7.0. The current `quadmesh+` sweep is measurably better:
   p95 ≈ 1.3, max 2.0–3.7.

**Lever if outlier tails ever matter downstream** (not needed for (a)): feed the
recovered `h`-field into the existing size-aware smoothing path
(`post_process_routine(truss_smooth=True, truss_fh=<h-field>)`) rather than
writing a per-move `α·h_local` displacement cap into `fem_smoother`.

## Reproduce

```bash
bash scripts/dev_setup.sh
# Real meshes (require a Valence checkout / registry access):
.venv/bin/python scripts/size_drift_report.py \
  <valence>/Test_Case_1.14 \
  <valence>/LakeErie_5k_500.14 \
  <valence>/Deleware_Bay_hmin_100_hmax_20000.14
# Token-free synthetic uniform-h fallback (no Valence needed):
.venv/bin/python scripts/size_drift_report.py --offline
```
