# API Contracts: Hierarchical Smoothing Routine (spec-056)

## `quadmesh.hierarchical_smooth.select_region`

```python
select_region(mesh, policy="skew", *, frac=0.075, layers=(0,), dev=2, dilate=True) -> np.ndarray
```
Returns sorted unique element ids. Pure (no mesh mutation). Deterministic (id tie-breaks).
Empty result allowed. `"layer"` on a mesh without layers → ValueError.

## `quadmesh.hierarchical_smooth.hierarchical_smoother`

```python
hierarchical_smoother(
    mesh,
    policy="skew",
    stage_plan=("local_fem",),
    *,
    frac=0.075, layers=(0,), dev=2, dilate=True,
    eps=1e-3, max_patch_iter=10, min_interior=4,
    fallback_frac=0.5,
    return_info=False,
) -> CHILmesh | tuple[CHILmesh, HierarchicalResult]
```
Guarantees:
- Domain-boundary node coordinates bitwise-unchanged (FR-008).
- Non-selected-region node coordinates bitwise-unchanged when `stage_plan=("local_fem",)` (FR-003).
- Deterministic: identical inputs+options → bitwise-identical output (SC-006/FR-004).
- Empty selection → FEM stage skipped, valid mesh returned (FR-013).
- Selection fraction > `fallback_frac` → delegates to `fem_smoother(n_iter=3)` (FR-012), `fell_back=True`.
- Patch loop halts on skew-improvement < `eps` or `max_patch_iter`; best-so-far kept (FR-007).
- Bowtie repair applied before return (FR-010).

## `quadmesh.post_process.post_process_routine` (extended — additive)

```python
post_process_routine(..., hierarchical=False, hierarchical_opts=None)
```
- `hierarchical=False` (default): behavior byte-identical to current release (SC-005).
- truthy: hierarchical pre-pass (opts forwarded), then `fem_smoother(n_iter=hierarchical_opts.get("n_global", 1))`
  replaces the plain `fem_smoother(n_iter=n_smooth_iter)` call (supplement composition, clarifications Q3/Q5).

## `scripts/bench_hierarchical_smooth.py` (CLI)

```
python scripts/bench_hierarchical_smooth.py --mesh <fixture-name-or-path>
    [--policies skew,layer,valence] [--orderings local,local+cheap,cheap+local]
    [--out output/hier_smooth_bench] [--json]
```
Always includes the baseline row; writes `<out>.md` + `<out>.json` (BenchRecord rows);
exits nonzero if any variant fails the invariant test (faithfulness is a bench gate too).
