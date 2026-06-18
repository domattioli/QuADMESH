# DRAFT — file this issue in `domattioli/CHILmesh`

> Prepared in the QuADMESH `monte-carlo-quality-analysis` session. CHILmesh is
> outside that session's GitHub MCP scope, so file it from a CHILmesh-scoped
> session. Voice: dom-write.

---

**Title:** Add size-controlled mesh cartograms (non-contiguous, layer-unrolled, focus+context) for per-element scalar fields

**Labels (suggest):** `type: feat`, `scope: plotting` (or nearest), `request: research`

**Body:**

## Summary

CHILmesh should provide reusable cartogram plotting so a per-element (or per-vertex) scalar field can be read without large elements visually dominating small ones. A geographic, area-weighted `tripcolor` of a 98,365-element WNAT mesh devotes most of the canvas to coarse open-ocean elements and shrinks the refined coastline — where the signal of interest concentrated — to sub-pixel threads. Three prototype views (built in QuADMESH; see QuADMESH#96 / QuADMESH#97) solved this, and they are mesh-generic, so they belong in CHILmesh.

## Motivation

The QuADMESH+ Monte-Carlo layer-pass study measured a per-triangle pass-frequency (fraction of randomized-start runs in which a triangle is left over by the per-layer sweep). On WNAT_Hagen the ever-routed elements are 9.9% of the mesh and the always-routed 4.9%, concentrated in the fine coastal band; the plain map renders them invisible. Equalizing visual weight per element exposed real structure — e.g. start-dependent "swing" triangles cluster at specific layer-and-angle locations in the deep small layers (L21–L25), invisible on the geographic map. The large-element-dominance problem is general: any scalar (element quality, residual, error indicator, layer index, valence) on any non-uniform mesh hits it.

## Prototype to generalize (QuADMESH `experiments/mc_layer_pass/`)

- `cartogram_noncontig` — each element redrawn at equal area about its centroid, geographic position preserved (the literal electoral-cartogram analog).
- `cartogram_unrolled` — skeleton `layers` unrolled into equal-height bands; each element an equal-width cell ordered by angular position. Built from CHILmesh `layers` + `paths_on_outer_vertices`, so it is already a CHILmesh-native construction.
- `cartogram_hybrid` — focus+context: element extent ∝ |value − reference| + ε, with reference ∈ {mean, median, mode, max, min}; the near-reference bulk compresses to slivers and deviating elements dominate.

## Proposed API

A `chilmesh.plotting` entry, e.g.

```
fig, ax = mesh.cartogram(values, kind="unrolled" | "noncontig" | "hybrid",
                         reference="mean", cmap="inferno", ax=None)
```

accepting a per-element or per-vertex array, returning Matplotlib handles for composition. (Note: "vertex", "node", and "point" are interchangeable here.)

## Iteration backlog (presentation + utility)

- Non-contiguous overlap/gaps: add a Dorling equal-circle option and/or a contiguous Gastner–Newman diffusion cartogram.
- Unrolled band height: selectable equal-per-layer (current) vs element-count-weighted vs log-count.
- Within-band ordering: true outer-vertex-path arc-length instead of centroid angle; correct handling of multi-loop layers and islands.
- Mixed-element support: CHILmesh meshes are mixed tri/quad — generalize beyond triangles.
- Colormaps: diverging option, percentile-clip normalization, colorblind-safe defaults.
- Scale: PolyCollection batching / decimation for 10^6-element meshes.
- Optional interactivity (hover element id); publication-default styling; tests + a gallery doc.

## Acceptance criteria

API plus docstrings (MATLAB-help register), a gallery page, unit/smoke tests, and reproduction of the QuADMESH pass-frequency cartograms directly from CHILmesh.

## References

- QuADMESH PR #96 (branch `monte-carlo-quality-analysis`), issue #97; prototype files `experiments/mc_layer_pass/cartogram.py` and `cartogram_hybrid.py`.
- Gastner & Newman (2004), diffusion-based cartograms; Dorling (1996), circular cartograms.
