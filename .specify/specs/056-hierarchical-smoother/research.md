# Research: Hierarchical Smoothing Routine (spec-056)

All Phase-0 unknowns resolved against the live codebase (chilmesh 1.2.2 editable sibling at
`/home/user/CHILmesh`, QuADMESH `056-hierarchical-smoother` branch). No NEEDS CLARIFICATION remain.

## R1 — Patch-submesh solve mechanics

**Decision**: Build one small `CHILmesh` per patch from compacted connectivity + points, with
`compute_layers=False, compute_adjacencies=True, build_spatial_indices=False, validate=False`,
then run the existing `quadmesh.post_process._balendran_smooth` on it unmodified.

**Rationale**: `CHILmesh.__init__` (CHILmesh.py:244) exposes exactly these fast-init flags —
adjacency dicts (needed by `boundary_edges()` and the stiffness assemblies) build without
layerization or KD-trees, so per-patch init is O(patch size). `_balendran_smooth`
(src/quadmesh/post_process.py:44) needs only `points`, `n_verts`, `_detect_element_types()`,
the three `_*_stiffness_assembly` methods (CHILmesh.py:1935/1955/1981), `edge2vert`, and
`boundary_edges()` — all available on a fast-init mesh.

**Alternatives considered**: (a) masking rows of the parent's global K — rejected: still pays
global assembly each pass, which is the cost being removed; (b) asking chilmesh for a new
submesh-assembly API — unnecessary given (fast-init ctor + compaction) works today; would
re-open a #237-style upstream wait.

## R2 — Rim pinning correctness

**Decision**: Rely on the patch submesh's own boundary detection for pinning; no solver change.

**Rationale**: In the compacted submesh, an edge is a boundary edge iff it has exactly one
incident element *within the patch*. That set is precisely (rim edges between patch and
far-field) ∪ (true domain-boundary edges owned by patch elements). `_balendran_smooth` pins
every node on `boundary_edges()` with the kinf trick — so rim nodes hold the interface fixed
(far field untouched, FR-003) and true boundary nodes never move (FR-008). Equivalence to a
whole-mesh solve with far-field frozen: for zero-RHS equilibrium, freezing all far-field dofs
is identical to solving the patch with Dirichlet rim values — standard static condensation
with prescribed boundary.

**Alternatives considered**: explicit pin-list parameter added to `_balendran_smooth` —
rejected: touches the shared global path (constitution: default byte-identical), and the
implicit boundary route needs no signature change.

## R3 — Layer indices for the "layer" policy

**Decision**: Read the parent mesh's existing layer decomposition (`mesh.layers`, populated by
skeletonization during normal pipeline init); policy `"layer"` maps requested domain-layer
indices → element ids. If layers absent (fast-init parent), raise ValueError telling the
caller to use policy `"skew"` — do NOT trigger a skeletonization pass inside the smoother.

**Rationale**: Spec assumption says no extra skeletonization; pipeline meshes already carry
layers; #90 built its layer-0 evidence from this same decomposition.

**Alternatives considered**: on-demand skeletonize — rejected: 66×-optimized but still
non-trivial at ENPAC scale, and would silently blow the end-to-end wall-clock accounting.

## R4 — Quality metric

**Decision**: `mesh.element_quality(metric="skew", elem_ids=...)` (CHILmesh.py:1272) for both
selection and patch-halt measurement; patch-halt measures only patch element ids.

**Rationale**: subset `elem_ids` supported natively; same metric as #90/#104 evidence and the
spec's SC-002, so gates and selection speak one language.

## R5 — Fixtures / bench ladder

**Decision**: Bench resolves meshes via the existing fixture path (`tests/fixtures/meshes/`,
provisioned by `scripts/fetch_fixtures.py` from Valence with `GITHUB_TOKEN`); Test_Case_1 +
Block_O for iteration, WNAT_Onur for the SC-001 gate. Without a token, bench + fixture tests
skip cleanly (repo's established mesh-dependent-skip pattern); unit tests run on synthetic
structured meshes built inline (small quad grid with an injected distorted band).

**Rationale**: matches `tests/fixtures/README.md` contract already used by
`test_no_interior_tris.py`; keeps CI green in tokenless containers.

## R6 — Baseline measurement protocol

**Decision**: The bench measures baseline `fem_smoother(n_iter=3)` fresh, same process, same
mesh object state (deep-copied pre-smoothing snapshot), immediately before variant runs.
README's ENPAC table numbers are context, never the comparison target.

**Rationale**: spec assumption (no cross-machine comparison); deep-copy isolation prevents
variant contamination (smoothers mutate `mesh.points` in place).

## R7 — Cheap global pass (OFF by default; kept available)

**Decision**: Reuse `truss_smoother` (post_process.py:90) restricted-scope via its existing
frozen-edge mechanics where possible; simplest compliant guard = run it, compare per-element
skew on the complement, revert if mean drops (whole-stage revert, deterministic). Ship behind
`stage_plan=("local_fem","cheap_global")` opt-in only (clarification Q1); measured as bench
variants, not in the default plan.

**Rationale**: FR-005 demands availability + guard, default plan excludes it; whole-stage
revert is the cheapest guard that cannot degrade quality.
