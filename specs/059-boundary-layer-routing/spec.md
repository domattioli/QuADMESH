# Feature Specification: Boundary-layer routing fix

**Feature Branch**: `development` (no new branch)
**Feature directory**: `specs/059-boundary-layer-routing/`
**Created**: 2026-10-10
**Status**: Clarified 2026-10-10
**Blocks**: release 0.3.0

## Problem

`chilmesh` numbers mesh layers from the domain boundary inward: layer 0 holds every triangle with a domain-boundary edge. Measured on bundled meshes, layer 0 of `annulus_200pts` holds 180 of 288 triangles with boundary edges and every other layer holds 0; `donut_domain`, `Block_O`, and `structuredMesh1` show the same pattern.

The per-layer sweep in `_quadmesh_plus_per_layer` flags the innermost layer as the boundary layer in two places:

- `src/quadmesh/tri2quad.py:915`: `is_boundary_layer=(li == nl - 1)` is passed to `match_layer_heuristic`, which controls the OE-before-IE pre-pass.
- `src/quadmesh/tri2quad.py:937`: `on_mesh_boundary = (li == nl - 1)` controls leftover-triangle routing (`removeTrianglesFun`). The comment at `:936` cites MATLAB `iLayer == nLayers`.

The MATLAB reference disagrees with that comment. `archive/matlab/quadmesh/04_Remove_Triangles/removeTrianglesFun.m:12` sets `onMeshBoundary` when `iLayer == 1 && CM.nLayers == Domain.nLayers`. MATLAB layer 1 is the outer layer, and `Tri2QuadRoutine.m:21` loops `Domain.nLayers:-1:1` ("Work outward"). MATLAB `iLayer == 1` maps to Python `li == 0`. `_layer_priority` (`tri2quad.py:683`) already uses `li == 0`. `docs/algorithm.md:90` and `:119` record the defect as open.

## Why the one-line fix is not enough (measured by CoS before this spec)

| Change | Interior residual tris | Boundary tris left (Block_O / annulus / donut) | structuredMesh1 mean skew | Tests |
|---|---|---|---|---|
| Current (bug) | 0 | 0 / 0 / 0 | 0.696 | pass; `test_boundary_layer_index.py` xfail strict |
| Flip `:915` and `:937` | 1 on Block_O (invariant broken) | n/a | 0.646 (worse) | 11 fail |
| Flip `:915` only | 0 | not reported | worse | n/a |
| Flip `:937` only | 0 | 3 / 3 / 9 (quad purity lost) | slightly better | n/a |

The current quad-pure output depends partly on the bug. When boundary routing runs on the innermost layer, leftover boundary-layer triangles go through the interior routing path (edge insertion, bisection, and removal), and that path removes them. When routing runs on the correct layer, some leftovers stay as legal boundary triangles. So the fix needs a correct boundary-layer flag and a routing policy that still produces quad-pure output by default.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Correct boundary-layer semantics (Priority: P1)

A maintainer who reads `tri2quad.py` beside the thesis and MATLAB finds that every boundary-layer decision applies to `chilmesh` layer 0.

**Why this priority**: This is the defect. Release 0.3.0 waits on it.

**Independent Test**: Remove the xfail from `tests/test_boundary_layer_index.py`. The test passes on `annulus_200pts`, `donut_domain`, and `structuredMesh1`.

**Acceptance Scenarios**:

1. **Given** any bundled mesh, **When** the per-layer sweep processes layer `li`, **Then** the matcher receives `is_boundary_layer=True` only when `li == 0`.
2. **Given** any bundled mesh, **When** leftover triangles are routed, **Then** `on_mesh_boundary` is True only when `li == 0`, which matches `removeTrianglesFun.m:12`.

### User Story 2 - The invariant holds and output stays quad-pure (Priority: P1)

A user who runs `tri2quad` with default arguments still gets zero interior residual triangles and, on the bundled meshes, zero triangles of any kind.

**Why this priority**: The faithfulness invariant is a hard rule in `quadmesh/AGENTS.md`. Quad purity is current user-visible behaviour.

**Independent Test**: `tests/test_no_interior_tris.py` passes. A per-mesh check counts 0 triangles on every bundled mesh with default arguments.

**Acceptance Scenarios**:

1. **Given** `Block_O`, **When** `tri2quad` runs with defaults, **Then** no triangle without a domain-boundary edge remains.
2. **Given** `Block_O`, `annulus_200pts`, `donut_domain`, or `structuredMesh1`, **When** `tri2quad` runs with defaults, **Then** the output has 0 triangles.

### User Story 3 - Quality does not regress (Priority: P2)

A user sees element quality equal to or better than 0.2.x/current output on every bundled mesh.

**Independent Test**: A baseline table of mean and worst skew (and the other metrics the existing benchmark reports) for each bundled mesh, captured before the change, compared after it.

**Acceptance Scenarios**:

1. **Given** `structuredMesh1`, **When** `tri2quad` runs with defaults, **Then** mean skew matches the 059 reference value 0.6466 in `baseline-quality.md`. Operator ruling (2026-10-10, option c): boundary-correct routing is the reference, and the drop from 0.6963 is expected.
2. **Given** any other bundled mesh, **Then** mean skew matches the 059 reference value in `baseline-quality.md` within 1% relative, and worst skew is no worse.

### Edge Cases

- A mesh with a single layer (`nl == 1`): layer 0 is both the innermost and the boundary layer. Behaviour must not change from today.
- A sub-domain where `CM.nLayers != Domain.nLayers` (the MATLAB second condition at `removeTrianglesFun.m:12`): define whether the Python port needs that guard.
- A triangle in layer 0 with only a boundary vertex and no boundary edge. Under the invariant it counts as interior, so it must be removed.
- Mixed or multiply-connected domains (annulus, donut), where layer 0 spans more than one boundary loop.
- Meshes in the private Valence fixtures skip in CI without a token. They gate the release through a manual operator run (FR-012).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `_quadmesh_plus_per_layer` MUST treat `chilmesh` layer 0 as the boundary layer in the matcher call (`tri2quad.py:915`) and in leftover routing (`tri2quad.py:937`). One shared helper or constant SHOULD define the predicate, matching `_layer_priority` (`:683`).
- **FR-002**: The `tri2quad.py:936` comment MUST cite MATLAB `iLayer == 1` (`removeTrianglesFun.m:12`).
- **FR-003**: `tri2quad` with defaults MUST leave zero interior residual triangles on every bundled mesh (`tests/test_no_interior_tris.py`).
- **FR-004**: `tri2quad` with defaults MUST produce 0 triangles on `Block_O`, `annulus_200pts`, `donut_domain`, and `structuredMesh1`.
- **FR-005**: Leftover layer-0 triangles MUST first be routed by `route_leftover_tri` with `on_mesh_boundary=True` (MATLAB `removeTrianglesFun`). Every triangle that is still a triangle after that MUST reach the closing pass (existing operations, including `_remove_boundary_tris`, `tri2quad.py:280`). The closing pass MUST be documented in `docs/MAPPING.md` as a Python addition.
- **FR-006**: For each bundled mesh, element-quality metrics MUST match the 059 reference values ("after" columns in `baseline-quality.md`), within tolerance: mean skew within 1% relative, worst skew no worse. The reference is the output of boundary-correct routing (operator ruling, 2026-10-10, option c). The change from the pre-059 values is expected and recorded.
- **FR-007**: `tests/test_boundary_layer_index.py` MUST pass with its `xfail(strict=True)` marker removed.
- **FR-008**: The 11 tests that fail under the naive flip MUST pass. Expectations in a test that encoded the buggy behaviour may be changed only with a written reason in the PR.
- **FR-009**: `docs/algorithm.md` MUST drop the open-defect notes (`:90`, `:119` row) and describe the corrected behaviour. `docs/MAPPING.md` MUST be updated if routing differs from MATLAB.
- **FR-010**: `CHANGELOG.md` `[0.3.0]` MUST gain a `Fixed` entry for this defect.
- **FR-012**: Before 0.3.0 is tagged, the operator MUST run `pytest tests/` and the quality table on the Valence fixtures with `GITHUB_TOKEN`. Results: zero interior residual triangles and no quality regression beyond tolerance.
- **FR-013**: `docs/MAPPING.md` MUST state that the `CM.nLayers == Domain.nLayers` guard is not ported, and why.
- **FR-011**: Public API (`method="quadmesh+"`, `"layered"` alias, `ValueError` for `"matching"` and `"faithful"`) MUST NOT change.

### Key Entities

- **Boundary layer**: `chilmesh` layer 0; every triangle with a domain-boundary edge is in it.
- **Interior residual triangle**: an output triangle with no domain-boundary edge. Forbidden.
- **Boundary residual triangle**: an output triangle with at least one domain-boundary edge. Legal by the invariant; forbidden by default under FR-004.

## Success Criteria *(mandatory)*

- **SC-001**: `pytest tests/` passes with no xfail on `test_boundary_layer_index.py`.
- **SC-002**: Interior residual triangle count = 0 on every bundled mesh, and on every Valence fixture when available.
- **SC-003**: Total triangle count = 0 on the four named meshes with defaults.
- **SC-004**: Every bundled mesh matches its 059 reference mean skew within 1% relative (structuredMesh1: 0.6466, before 0.6963; expected drop, operator ruling 2026-10-10). Table in `baseline-quality.md`.
- **SC-006**: Operator sign-off on the Valence run is recorded before the release tag.
- **SC-005**: No `li == nl - 1` boundary predicate remains in `src/quadmesh/`.

## Coordination and file overlap

- **057 (sibling dedupe, in progress)** edits `post_process.py`, `remove_unused.py`, `identify_edges.py`, and `pyproject.toml`. This feature's main target is `tri2quad.py`. Routing changes may touch `_tri_removal` and `_match_quadmesh_plus`; neither is in 057's list. If routing work reaches `identify_edges.py` or `post_process.py`, it waits until 057 merges. 057's uncommitted baselines (`tests/fixtures/baselines/`) and `tests/test_dedupe_parity.py` may shift if output changes; rebaseline after both land.
- **058 (benchmark adapters, speccing)**: quality numbers for SC-004 should use the same metric code 058 adopts, or the existing benchmark if 058 has not landed.
- **CHANGELOG.md and docs/algorithm.md** are shared with the 0.3.0 release prep (056). Edit only the `[0.3.0] Fixed` section and the defect lines.

## Assumptions

- The `chilmesh` layer numbering (0 = boundary) is stable and public.
- The bundled meshes are those in `chilmesh.data` plus `Block_O`.
- Skew is "higher is better" under the current metric (0.696 -> 0.646 was described as worse).
- Writes to `.specify/feature.json` were skipped: that path is outside the feature directory under this turn's constraints.

## Out of scope

- The `aggressive=` option and `merge_elements` integration.
- Smoother changes (`fem_smoother`).
- New public routing options.

## Clarifications

### Session 2026-10-10

- Q: How are leftover layer-0 triangles routed once routing is correct? → A: Use the thesis/MATLAB `removeTrianglesFun` routing on layer 0, then run a closing pass that sends any boundary triangle still left through the existing operations (edge insertion, bisection, removal, and `_remove_boundary_tris`). Output stays quad-pure.
- Q: Which flags change, and in what order? → A: Both (`:915`, `:937`) change in this feature together with the closing pass. The invariant holds at every commit.
- Q: What quality tolerance applies? → A: Mean skew within 1% relative of baseline, and worst skew no worse, on every bundled mesh. Superseded 2026-10-10 by operator ruling (option c): the reference is the boundary-correct output in `baseline-quality.md`.
- Q: Should the MATLAB `CM.nLayers == Domain.nLayers` guard be ported? → A: No. Record the omission in `docs/MAPPING.md` (the Python sweep always runs on the full domain).
- Q: Do Valence fixtures gate 0.3.0? → A: Yes. Before release, the operator runs the test suite and the quality table on the Valence fixtures (ENPAC and others) with `GITHUB_TOKEN`. The CoS coordinates this. CI still skips without a token.
