# Feature Specification: Skeletonization Rename — Unify layers / skeleton / medial axis

> **SUPERSEDED / REMOVED (2026-06-18, issue #82 cross-repo dedup).** The implementing
> modules (`mesh_structure.py`, `_layer_state.py`, `_medial_axis.py`, `domains.py`) were
> removed: they were disconnected from the production `tri2quad` pipeline and duplicated
> functionality owned upstream — layers/skeleton by CHILmesh (`mesh.layers`, `skeleton()`),
> medial axis by ADMESH stage-05 (`src/admesh/medial_axis.py`), demo domains by ADMESH
> `domains.py` + the Valence registry. `_layer_state.LayerState` also duplicated the live
> `_tri_removal.py::LayerState` used by the sweep. Retained here for historical context only.

**Feature Branch**: `daily-maintenance`
**Created**: 2026-05-31
**Status**: Superseded — implementation removed per #82 (2026-06-18); was Complete (rename pass done, skeleton implemented per operator 2026-05-30 definition)
**Input**: Issue #55: "medial axis, layers, and skeleton are all similar but different. i think skeleton for a mesh should be defined/derived in the same way it is for an image. we need to create a unifying function that computes all three of these and the user can designate which with an input."
**Cross-ref**: `specs/004-unified-mesh-structure/spec.md` (API already implemented; this spec covers the rename sweep and remaining research tasks)

---

## Motivation

The codebase uses "skeleton" and "skeletonization" as a loose alias for "layers" — the CHILmesh concentric ring decomposition. This conflation is inaccurate: a mesh skeleton in the image-processing sense (ridge of the distance transform / thinning) is a distinct concept from layering. The medial axis (locus of inscribed-circle centres) is a third concept. All three are similar but not the same, and mixing the terms makes it harder to reason about which structure the algorithm uses and why.

**Spec 004** already delivered:
- `compute_mesh_structure(domain, kind=)` — the unifying entrypoint.
- `kind="layers"` — returns a deep-copied `LayerState` (CHILmesh layers, innermost→outermost).
- `kind="medial_axis"` — returns a `MeshStructure` with interior Voronoi nodes/edges.
- `kind="skeleton"` — raises `NotImplementedError` (concept still being scoped).

This spec covers the remaining work: **purging the stale "skeletonization" terminology** from docstrings and internal helpers, and **scoping the skeleton research** so a future session can implement it correctly.

---

## Acceptance Criteria

1. **No false synonyms**: every reference to "skeletonization" or "skeleton" in QuADMesh source that *actually means layers* is renamed to "layers" or "layer decomposition".
2. **`_skeletonize` method handle in validator** — the `hasattr(mesh, "_skeletonize")` branch is either updated to `_compute_layers` (matching CHILmesh's real API) or removed if it is dead code.
3. **Docstring precision**: `_layer_state.py` module docstring uses "layer decomposition", not "skeletonization". `tri2quad.py` function docstring at line 670 uses "layer-priority" not "skeleton layers".
4. **`kind="skeleton"` error message** in `mesh_structure.py` references this spec (#55) so the operator knows where the open question lives.
5. **All existing tests pass** after the rename: `pytest tests/` green (no functional change — rename is documentation-level only for now).
6. **Skeleton scoping note** committed in this spec (see Research section below).

---

## Migration Path — Rename Touchpoints

All files requiring terminology fixes (as of 2026-05-31):

| File | Line(s) | Current text | Replacement |
|---|---|---|---|
| `src/quadmesh/_layer_state.py` | 1 | `"CHILmesh skeletonization layers"` | `"CHILmesh layer decomposition"` |
| `src/quadmesh/mesh_structure.py` | 7 | `"skeletonization layer"` | `"layer decomposition"` |
| `src/quadmesh/tri2quad.py` | 670, 698, 790, 879, 945, 978 | `"skeleton layers"` | `"layers"` or `"layer decomposition"` (context-dependent) |
| `src/quadmesh/validation/validator.py` | 118–133 | `_skeletonize` | audit: if CHILmesh uses `_compute_layers`, update; if dead code, remove |
| `tests/test_layer_state.py` | 5 | `"CHILmesh skeletonization"` | `"CHILmesh layer decomposition"` |
| `tests/test_mesh_structure.py` | 5 | `"skeleton (not yet implemented"` | keep — still accurate; update to reference #55 |

### Validator `_skeletonize` — required audit

The `validator.py` snippet at lines 118–133 checks `hasattr(mesh, "_skeletonize")` and calls `mesh._skeletonize()`. This is CHILmesh's internal method name. Before renaming, confirm the CHILmesh API:

```
python -c "import chilmesh; import inspect; print([m for m in dir(chilmesh.CHILmesh) if 'layer' in m.lower() or 'skelet' in m.lower()])"
```

If CHILmesh exposes `_skeletonize`, keep the name (it is their API, not ours to rename). If CHILmesh renamed it, update the call site. Either way, add a comment clarifying this calls into CHILmesh's layer-computation method.

---

## Research Section — Skeleton Definition

**Operator clarification (2026-05-30 comment on #55):**
> "Repeat the layers process (peeling, storing the elements that are peeled with each iteration), until you end up with a skeleton that can't be peeled anymore. Then we can explore whether starting with the skeleton or medial axis elements has any benefit over starting w the Nth layer."

This is the **morphological skeleton** definition — identical to the CHILmesh `_skeletonize()` layer-peeling algorithm, not image-style distance-transform thinning.

Key distinctions (updated):

| Concept | Definition | Input | Output |
|---|---|---|---|
| **Layers** | CHILmesh concentric ring decomposition; layer 0 = outermost, N-1 = innermost | CHILmesh domain | `LayerState` (OE/IE/OV/IV lists per ring) |
| **Skeleton** | Same layer decomposition + `skeleton_core` exposing the innermost irreducible layer | CHILmesh domain | `MeshStructure(kind="skeleton")` with `skeleton_core`, `skeleton_core_verts` properties — **shipped** |
| **Medial axis** | Locus of centres of maximal inscribed circles; Voronoi interior ridges approximation | Domain polygon | Node/edge graph — **shipped** |

### Skeleton implementation (shipped 2026-06-01, spec 055)

`compute_mesh_structure(domain, kind="skeleton")` returns:
- Full layer decomposition in `layers` attribute (layer 0 = outermost-peeled, N-1 = core)
- `skeleton_core` → `(OE[-1], IE[-1])` — elements of the irreducible innermost layer
- `skeleton_core_verts` → `(OV[-1], IV[-1])` — vertices of the irreducible innermost layer

### Skeleton-vs-layers comparison harness (future session)

The operator wants to quantify whether starting tri→quad from the skeleton core (innermost layer)
vs the outermost layer changes quad quality. Plan:
1. Run `identify_edges` / tri2quad starting from layer N-1 (skeleton core) vs layer 0 (outermost).
2. Compare: which tris are matched, in which order, what is the resulting quad quality?
3. Compare against medial_axis as a starting-point guide (project tri centroids onto nearest medial branch).

Prior art may exist in `domattioli/madmeshing` — check before implementing.

---

## Test Plan

| Test | File | Trigger |
|---|---|---|
| Docstring-only tests (none) | — | Rename is doc-only; no new functional tests needed |
| Existing: `test_layer_state.py` (all) | `tests/test_layer_state.py` | Must pass — no functional change |
| Skeleton tests (6) | `tests/test_mesh_structure.py` | Added 2026-06-01; all pass |
| Future: `test_skeleton_vs_layers_comparison` | `tests/test_mesh_structure.py` | Add when comparison harness is built |

Run: `pytest tests/test_mesh_structure.py tests/test_layer_state.py -v`

---

## Success Criteria

- **SC-001**: `grep -rn "skeletonization" src/` returns no results that refer to "layers" (only legitimate references to CHILmesh's internal method name are allowed). ✓ DONE
- **SC-002**: `pytest tests/` green. ✓ DONE (65 tests, 2026-06-01)
- **SC-003**: `kind="skeleton"` now implemented (not NotImplementedError). ✓ DONE
- **SC-004**: The `_skeletonize` validator branch is documented with a comment explaining it calls CHILmesh's layer-computation API. ✓ DONE

## Assumptions

- CHILmesh's method `_skeletonize` is their canonical name for layer computation and should not be renamed here.
- Skeleton = morphological skeleton via CHILmesh layer peeling (operator 2026-05-30). Image-style impl deferred indefinitely.
- Skeleton-vs-layers comparison harness is future work.
