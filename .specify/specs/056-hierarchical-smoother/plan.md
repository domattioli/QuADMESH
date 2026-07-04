# Implementation Plan: Hierarchical Smoothing Routine

**Branch**: `056-hierarchical-smoother` | **Date**: 2026-07-03 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `.specify/specs/056-hierarchical-smoother/spec.md` (#104)

## Summary

Replace global smoothing effort with targeted effort. New `hierarchical_smoother()` in
`src/quadmesh/hierarchical_smooth.py`: (1) select worst-skew elements + 1-ring (default;
layer-0 and valence policies also available), (2) group into connected patches, (3) per
patch build a small compacted CHILmesh submesh and run the EXISTING Balendran solve on it —
the patch submesh's own `boundary_edges()` is exactly rim ∪ true-boundary, so
`_balendran_smooth`'s pinning mechanism works unmodified — iterating each patch to a
quality-delta halt, (4) write converged patch coordinates back into the parent mesh.
`post_process_routine` gains an opt-in kwarg composing it as a pre-pass followed by 1
(configurable) global FEM pass. Bench script sweeps policy × ordering on Test_Case_1 /
Block_O / WNAT_Onur against the `fem_smoother(n_iter=3)` baseline.

## Technical Context

**Language/Version**: Python ≥3.10 (repo standard)
**Primary Dependencies**: `chilmesh` (editable sibling, 1.2.2 — CHILmesh ctor fast-init flags, `_balendran_smooth`-style assembly internals, `element_quality`, adjacencies), `numpy`, `scipy.sparse(.linalg)`
**Storage**: N/A (in-memory meshes; bench writes md+json results under `output/`)
**Testing**: pytest; fixtures via Valence registry (token-gated; mesh-dependent tests skip without)
**Target Platform**: Linux/macOS, single-thread
**Project Type**: library (additive module in existing `src/quadmesh` package)
**Performance Goals**: SC-001 — smoothing phase ≤50% of baseline `fem_smoother(n_iter=3)` wall-clock on WNAT_Onur, end-to-end (selection+patch build+solves all counted)
**Constraints**: deterministic (bitwise-reproducible), boundary nodes exactly pinned, zero-interior-tri invariant, default paths byte-identical, additive-only
**Scale/Scope**: meshes 10³–5×10⁵ elements; patches expected ≪ mesh (5–10% selection + 1-ring)

## Constitution Check

*GATE: evaluated pre-Phase-0 and re-checked post-design — PASS (both).*

| Principle | Compliance |
|---|---|
| I. Faithful Port | New routine is NOT a MATLAB port — it is additive Python-side tooling. Default pipeline behavior unchanged (spec FR-001, SC-005); faithfulness invariant test gates all outputs (FR-009). No locked behavior modified. |
| II. Depend on chilmesh, no reinvention | Patch solves REUSE chilmesh stiffness assemblies + CHILmesh submesh construction; no new smoother physics, no copied chilmesh code. The one QuADMESH-side FEM piece reused is `post_process._balendran_smooth` (already exists here per chilmesh#173). New spokes documented in this spec. |
| III. Test-first per module | `tests/test_hierarchical_smooth.py` paired with the module; synthetic + fixture-gated cases; acceptance = quality stats sane, no orphan verts, no zero-area elems, invariant test passes. |
| IV. Layered implementation | Leaf helpers (selection, patch build) → patch solver → orchestrator → post_process kwarg wiring → bench. |
| V. 0-based indexing | All numpy indices 0-based; -1 sentinel via chilmesh conventions. |
| VI. Caveman docs | Terse docstrings, invariants explicit. |

## Project Structure

### Documentation (this feature)

```text
.specify/specs/056-hierarchical-smoother/
├── spec.md              # done (clarified ×5)
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── api.md           # Phase 1 — public callable contracts
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/quadmesh/
├── hierarchical_smooth.py   # NEW — selection policies, Patch build, patch solver, orchestrator
└── post_process.py          # EDIT — opt-in kwarg on post_process_routine (supplement composition)

scripts/
└── bench_hierarchical_smooth.py  # NEW — policy × ordering sweep vs baseline, md+json out

tests/
└── test_hierarchical_smooth.py   # NEW — unit (synthetic) + fixture-gated integration
```

## Design

### Selection stage (FR-002)

`select_region(mesh, policy, **params) -> np.ndarray[int]` (element ids, sorted, deduped):

- `"skew"` (default): `q = mesh.element_quality(metric="skew")`; seed = worst `frac`
  (default 0.075, i.e. 7.5% ∈ [5,10]%) by ascending q with deterministic tie-break on
  element id; dilate by 1-ring via `Vert2Elem` over the seed elements' vertices.
- `"layer"`: elements of `mesh.layers` domain-layer indices in `layers` param (default `(0,)`).
- `"valence"`: elements incident to interior vertices whose valence (len `Vert2Elem[v]`,
  quads → target 4) deviates ≥ `dev` (default ≥2); dilate 1-ring.

All pure numpy/adjacency reads — no mutation. Empty selection → return empty array (FR-013).
Selected fraction > `fallback_frac` (default 0.5) → orchestrator falls back to global path (FR-012).

### Patch construction (FR-003/004, edge cases)

- Connected components of selected elements over shared-edge adjacency (`Edge2Elem`),
  computed with a deterministic BFS seeded in ascending element-id order → components are
  order-independent (same set in, same partition out). Overlap impossible post-components.
- Patches smaller than `min_interior` (default 4 free nodes) merged into the neighboring
  component if edge-adjacent, else skipped (edge case: tiny/singular patches).
- Per patch: compact vertex map old→new; submesh conn (preserving 3-col tri / 4-col padded
  rows exactly as parent — mixed assembly path stays correct); build
  `CHILmesh(conn_sub, pts_sub, compute_layers=False, compute_adjacencies=True,
  build_spatial_indices=False, validate=False)` — cheap init (no layerization, no KD-trees).
- **Pinning insight (load-bearing)**: the submesh's `boundary_edges()` = patch rim edges ∪
  any true domain-boundary edges inside the patch. `_balendran_smooth(submesh)` pins exactly
  those nodes with the existing kinf mechanism — rim stays glued to the untouched far field,
  true boundary never moves (FR-008). Zero modification of the solver.

### Patch solve loop (FR-007)

Per patch, iterate: `new_pts = _balendran_smooth(patch_mesh)`; apply; measure
`mean(element_quality("skew"))` over patch elements; halt when improvement < `eps`
(default 1e-3) or `max_patch_iter` (default 10) reached; keep best-so-far coordinates
(monotone guard — a worsening pass reverts and halts). Write back via the vertex map:
only patch-interior node coords change in the parent (rim/boundary were pinned → unchanged
by construction; assert with atol=0 equality on pinned rows in tests).

### Orchestrator + composition (FR-001/005/006)

```
hierarchical_smoother(mesh, policy="skew", stage_plan=("local_fem",), ...) -> CHILmesh
```
Stage plan tuple orders stages; `"cheap_global"` (guarded truss/Laplacian on complement)
available but OFF by default (clarification Q1). After stages, run existing `_fix_bowties`
(FR-010). `post_process_routine(..., hierarchical=False, hierarchical_opts=None)`: when
truthy, run pre-pass then global `fem_smoother(n_iter=hierarchical_opts.get("n_global",1))`
(clarifications Q3/Q5) instead of the plain `fem_smoother(n_iter=3)` call; `hierarchical`
absent/False → byte-identical current path (SC-005).

### Benchmark (FR-011)

`scripts/bench_hierarchical_smooth.py --mesh <id|path> [--policies ...] [--orderings ...]`:
loads mesh → runs tri2quad pipeline up to pre-smoothing state once → deep-copies for each
variant → times baseline `fem_smoother(n_iter=3)` vs variants end-to-end → md + json rows:
wall-clock, mean/median skew, sub-0.30 count, invariant pass/fail. Ladder: Test_Case_1,
Block_O (fast), WNAT_Onur (SC-001 decision mesh; token-gated).

### Determinism (FR-004, SC-006)

No RNG anywhere; selection tie-breaks on element id; BFS order fixed; spsolve deterministic
for fixed sparsity/permutation. Two identical runs → bitwise-identical coordinates.

## Phase 0 → research.md (unknowns resolved there)

R1 patch-submesh assembly viability + cost; R2 rim-pinning equivalence proof sketch;
R3 layer-index recovery; R4 skew metric subset calls; R5 fixture availability; R6 baseline
measurement protocol. All resolved — see research.md.

## Phase 1 outputs

- data-model.md — SelectionPolicy, Patch, StagePlan, BenchRecord entities.
- contracts/api.md — public signatures + guarantees.
- quickstart.md — 10-line usage + bench invocation.

## Risks

- **Patch CHILmesh init overhead** could eat the win on many tiny patches → mitigated by
  `min_interior` merge/skip + measured in bench (end-to-end accounting makes this honest).
- **Supplement default (1 global pass)** still pays one giant spsolve — the 2× headroom is
  (3 global) vs (cheap pre-pass + 1 global); if pre-pass isn't ≪ 1 global solve at WNAT
  scale, SC-001 fails in supplement mode → bench reports standalone (replacement) rows too,
  giving the operator the fallback decision data (US3).
- **chilmesh private-API reach** (`_tri/_quad/_mixed_stiffness_assembly` via
  `_balendran_smooth`) — already the status quo in `post_process.py`; no NEW private
  surface is touched beyond what ships today.
