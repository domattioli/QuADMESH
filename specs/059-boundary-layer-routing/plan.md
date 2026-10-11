# Implementation Plan: Boundary-layer routing fix (059)

**Spec**: `spec.md` | **Date**: 2026-10-10 | **Branch**: `development`

## Summary

Treat `chilmesh` layer 0 as the boundary layer in the matcher flag (`src/quadmesh/tri2quad.py:915`) and in leftover routing (`:937`), using one shared predicate. Add a closing pass so that layer-0 triangles left by `route_leftover_tri` still reach the quad-purity cleanup. Hard constraints: zero interior residual triangles, quad-pure output by default, and no quality regression.

## Technical context

- Python 3, numpy, `chilmesh` (sibling editable install), pytest.
- Files changed: `src/quadmesh/tri2quad.py`, possibly `src/quadmesh/_tri_removal.py`, `tests/test_boundary_layer_index.py`, new `tests/test_boundary_routing_quality.py`, `docs/algorithm.md`, `docs/MAPPING.md`, `CHANGELOG.md`.
- Files not changed (057 owns them): `post_process.py`, `remove_unused.py`, `identify_edges.py`, `pyproject.toml`.

## Root-cause hypothesis for the 3/3/9 boundary triangles (verify in T003)

`tri2quad.py:943-958` adds every routed triangle to `consumed`, including:
- triangles that `route_leftover_tri` leaves unchanged (the silent fall-through at `_tri_removal.py:359`), and
- triangles refused under `refuse_boundary_merge`.

Consumed triangles never enter `leftover_idx` (`:983`). So `_remove_boundary_tris` (`:280`, called at `:1097`) never sees them, and they survive as triangles. Under the bug, layer 0 went through the `not on_mesh_boundary` branches (`_tri_removal.py:336`, `:347`), which always act. With the correct flag, layer 0 reaches the `on_mesh_boundary` branches, and some of those can leave a triangle in place.

**Fix design (Q1 = A).** `route_leftover_tri` reports whether the triangle was actually converted. A triangle that is still present is left out of `consumed`, so it flows into `leftover_idx`. The existing `_remove_boundary_tris`, edge swap, and point insertion pipeline (`:1097` onward) acts as the closing pass. Refused triangles keep today's behaviour. If T003 disproves the hypothesis, the fallback is an explicit post-sweep pass that re-routes surviving layer-0 triangles through `edge_insertion`/`edge_bisection` (`_tri_removal.py`) with `on_mesh_boundary=False`. That is the code path the bug used, applied only as the last step.

## Root-cause (T003 result)

**Hypothesis rejected.** With the flag flipped to `li == 0` (in memory, at `:915` and `:937`), the per-layer sweep returns `leftover_idx == []` and `refused == {}` on all four meshes. Every routed triangle is cleared (none stays in `connectivity_list`). The surviving triangles are emitted quads that lost a vertex: 4 on Block_O, 6 on annulus, 15 on donut and 1 on structuredMesh1. They have 3 unique vertices, and two of them have 2.

Cause: the layer-0 branch `on_mesh_boundary and n_bdy == 1 and can_remove_edges` calls `edge_removal` (`_tri_removal.py:121`). That function rewrites `v_b -> v_a` in `work.quads`. A quad that already holds both vertices collapses to a triangle. Route-branch counts (on-boundary, n_bdy == 1, 0 new quads): Block_O 6, annulus 11, donut 22, structuredMesh1 2.

Fix as attempted: `route_leftover_tri` returns `None` for an unchanged triangle, and the caller does not consume it. A collapse that would merge two vertices of an emitted quad is replaced by `edge_bisection`. First result: 0 tris on all meshes, but structuredMesh1 mean skew fell to 0.648 (gate 0.696), and `edge_removal` moved original boundary vertex 33. Escalated to the CoS. Operator ruling (2026-10-10, option c): accept the boundary-correct output as the new reference. To keep every original boundary vertex, the sweep now passes `preserve_boundary_verts=True`, and a layer-0 triangle with one boundary edge is bisected on that edge instead of collapsed. Final structuredMesh1 mean skew: 0.6466.

## Constitution check

- The QuADMESH+ invariant (zero interior residual triangles) is gated by `tests/test_no_interior_tris.py` at every commit. PASS by design (Q2 = A).
- `method` API unchanged. PASS.
- MATLAB parity: the boundary predicate now matches `removeTrianglesFun.m:12`. The closing pass and the omitted guard are recorded in `MAPPING.md`. PASS.

## 057 leftovers: T012 (inline `merge_tri_pair` as `chilmesh.quad_from_tri_pair`) and T013 (delete `_topology.py`)

**Decision: 059 absorbs them as a separate final phase (Phase 6), after the fix is green.** Reasons:
- 059 already owns `tri2quad.py`, so no other worker would touch it.
- The change preserves behaviour and is checked by the same quality baseline.

Conditions:
- They land as their own commit, so the fix can be bisected independently.
- If `chilmesh.quad_from_tri_pair` output differs from `merge_tri_pair` on any bundled mesh, drop them back to 057 or a follow-up and do not block 0.3.0.

## Project structure (feature docs)

```
specs/059-boundary-layer-routing/
  spec.md  plan.md  tasks.md  checklists/requirements.md
  baseline-quality.md   (T002 output)
```

## Phases

1. Baseline: quality table and triangle counts on the current code.
2. Diagnose: confirm the root cause of the 3/3/9 triangles.
3. Fix (US1 + US2 together): shared predicate, both flags, closing pass, xfail removal.
4. Quality gate (US3).
5. Docs: `algorithm.md`, `MAPPING.md`, `CHANGELOG`.
6. Absorb 057 T012/T013.
7. Release gate: operator Valence run.

## Risks

- Changing the `consumed` set may alter the global-fallback branch (`:960`). Mitigation: the T002 baseline compares every mesh.
- 057 baselines (`tests/fixtures/baselines/`, `test_dedupe_parity.py`) may change with the output. Mitigation: T014 rebaselines after 057 commits, with CoS approval.
- `structuredMesh1` skew could fall below .696 even with the closing pass. Outcome: it did (0.6466). The operator ruled on 2026-10-10 (option c) that boundary-correct routing is the reference and the drop is expected.

## Complexity tracking

None.
