# 059 quality reference

Code before: `development` at ec97ba5 (057), `tri2quad` defaults. Code after: 059 working tree (boundary flag `li == 0`, unchanged tris passed to the closing pass, boundary-edge bisection in place of collapse). Metric: `quadmesh.quality_report.compute_quality_stats` (skew, `chilmesh.element_quality`). Tri and interior-residual counts use the helpers in `tests/test_no_interior_tris.py`. Bundled meshes come from `chilmesh.data`.

| Mesh | Layers | Elements before / after | Tris before / after | Interior residual tris before / after | Mean skew before | Mean skew after | Worst skew before / after |
|---|---|---|---|---|---|---|---|
| Block_O.14 | 9 | 2744 / 2739 | 0 / 0 | 0 / 0 | 0.5418 | 0.5440 | 0.0000 / 0.0000 |
| annulus_200pts.fort.14 | 4 | 341 / 340 | 0 / 0 | 0 / 0 | 0.2713 | 0.2730 | 0.0000 / 0.0000 |
| donut_domain.fort.14 | 3 | 168 / 168 | 0 / 0 | 0 / 0 | 0.3339 | 0.3339 | 0.0000 / 0.0000 |
| structuredMesh1.14 | 5 | 340 / 341 | 0 / 0 | 0 / 0 | 0.6963 | 0.6466 | 0.0000 / 0.0000 |
| quad_2x2.fort.14 | 1 | 4 / 4 | 0 / 0 | 0 / 0 | 0.0000 | 0.0000 | 0.0000 / 0.0000 |

The "after" columns are the 059 reference for FR-006 and SC-004. Operator ruling, 2026-10-10 (option c): boundary-correct routing is the reference. The structuredMesh1 drop from 0.6963 to 0.6466 is expected.

## T015 operator sign-off (Valence fixtures)

Pending.
