# Data Model: Hierarchical Smoothing Routine (spec-056)

## SelectionPolicy (conceptual — implemented as policy functions keyed by name)

| Field | Type | Notes |
|---|---|---|
| name | `"skew" \| "layer" \| "valence"` | default `"skew"` |
| frac | float ∈ (0,1] | skew policy seed fraction, default 0.075 |
| layers | tuple[int,...] | layer policy domain-layer indices, default `(0,)` |
| dev | int ≥1 | valence policy deviation threshold, default 2 |
| dilate | bool | 1-ring dilation (skew/valence), default True |

Validation: unknown name → ValueError. Output invariant: sorted unique element ids,
deterministic for fixed (mesh, params).

## Patch

| Field | Type | Notes |
|---|---|---|
| elem_ids | np.ndarray[int] | parent element ids, one connected component |
| vert_map | np.ndarray[int] | parent vertex id per submesh row (new→old) |
| submesh | CHILmesh | fast-init compacted mesh (`compute_layers=False`) |
| free_mask | np.ndarray[bool] | submesh nodes NOT on submesh boundary (= movable) |

Invariants: components pairwise edge-disjoint (post component split); `free_mask` count ≥
`min_interior` (else merged/skipped); pinned submesh nodes' coordinates identical to parent
before AND after solve; only `vert_map[free_mask]` parent rows may change on write-back.

Lifecycle: built → iterated (solve loop, best-so-far tracking) → written back → discarded.

## StagePlan

Ordered tuple of stage names, subset of `{"local_fem", "cheap_global"}`; default
`("local_fem",)` (clarification Q1). Orderings for the bench: `("local_fem","cheap_global")`
and `("cheap_global","local_fem")` (FR-006).

## HierarchicalResult (return metadata, attached for bench/tests)

| Field | Type | Notes |
|---|---|---|
| mesh | CHILmesh | smoothed mesh (same object semantics as fem_smoother return) |
| n_selected / n_patches | int | selection + partition sizes |
| fell_back | bool | True when selection frac > fallback_frac → global path used (FR-012) |
| patch_iters | list[int] | per-patch iterations until halt |
| timings | dict[str,float] | end-to-end phase seconds (selection, patch_build, solves, total) |

## BenchRecord (one row per mesh × variant)

| Field | Type |
|---|---|
| mesh_id, variant | str |
| wall_s | float (end-to-end per clarification Q2) |
| mean_skew, median_skew | float |
| sub030_count | int |
| invariant_pass | bool |
| speedup_vs_baseline | float |

Emitted as markdown table + JSON list; baseline row always present per mesh (R6).
