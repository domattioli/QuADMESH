# MATLAB -> Python Map

Port status. v0.5 (faithful-port milestone M2).

| MATLAB (`02_QuADMESH_Library/`) | Python (`quadmesh/`) | Status |
|---|---|---|
| `00_Main/Main.m` | `cli.py` + `pipeline.run_pipeline` | done |
| `01_Create_Quad_Domain/createQuadDomain.m` | `create_quad_domain` | done (polygon mode) |
| `01_Create_Quad_Domain/drawSubdomain.m` | - | skip (GUI) |
| `02_Tri2Quad_Routine/Tri2QuadRoutine.m` | `tri2quad.tri2quad_routine` | done — layer-ordered per-layer sweep (`method="quadmesh+"`, MATLAB-faithful; `"matching"` and `"faithful"` aliases removed per #46, raise ValueError) |
| `02_Tri2Quad_Routine/identifyEdgesFun.m` | - | skip (superseded by v2) |
| `02_Tri2Quad_Routine/identifyEdgesFun_v2.m` | `identify_edges.identify_edges_in_layer` | done |
| `02_Tri2Quad_Routine/mergeTrianglesFun.m` | `_topology.merge_tri_pairs` | done |
| `02_Tri2Quad_Routine/CCWEdgesAroundVertsFun.m` | `_topology.ccw_edges_around_vert` | done |
| `02_Tri2Quad_Routine/plotQuadProgress.m` | - | skip (plot) |
| `03_Layer_Paths/PathsOnOV.m` | `chilmesh.layer_paths.paths_on_outer_vertices` | done via chilmesh |
| `03_Layer_Paths/pathRewind.m` | inline in `identify_edges` | done |
| `04_Remove_Triangles/removeTrianglesFun.m` | `_tri_removal.route_leftover_tri` | done — all cases; recombination ops wired (`_recombine.py`) |
| `04_Remove_Triangles/edgeInsertion.m` | `_tri_removal.edge_insertion` | partial (cases 1/2 without iLayer-1 retri; v0.4 unit-tested, ravel bug fixed) |
| `04_Remove_Triangles/edgeBisection.m` | `_tri_removal.edge_bisection` | done (infinite-loop fix for reversed CCW orientation) |
| `04_Remove_Triangles/edgeRemoval.m` | `_tri_removal.edge_removal` | done |
| `05_Post-Process_Routine/PostProcessRoutine.m` | `post_process.post_process_routine` | done |
| `05_Post-Process_Routine/plotQualityProgress.m` | `quality_report.compute_quality_stats` + `format_quality_report` | done (stats; plot skipped) |
| `06_Cleanup_Boundary_Quads/CleanupBoundaryQuads_v2.m` | `cleanup_boundary_quads` | done (collapse MATLAB-aligned: side verts -> corner; shift: Python-only) |
| `06_Cleanup_Boundary_Quads/TruncateBoundaryQuads.m` | - | skip (legacy) |
| `07_Doublet_Collapse/DoubletCollapse.m` | `doublet_collapse.doublet_collapse` | done |
| `08_Quad_Vertex_Merge/QuadVertexMerge.m` | - | skip (legacy) |
| `08_Quad_Vertex_Merge/QuadVertexMerge_v2.m` | `quad_vertex_merge.quad_vertex_merge` | done |
| `10_Remove_Unused_Vertices/RemoveUnusedVertices.m` | `remove_unused.remove_unused_vertices` | done |
| `11_FEM_Smoothing/FEMSmooth.m` | `post_process.fem_smoother` | done |
| `11_FEM_Smoothing/MCSmooth.m` | - | not ported (boundary-layer MCSmooth half never implemented) |
| `11_FEM_Smoothing/twoPartSmoother.m` | `post_process.fem_smoother` | done (FEM half only; renamed from `two_part_smoother`, MCSmooth half absent) |
| `11_FEM_Smoothing/extdom_edges2.m` | `chilmesh.boundary_edges()` | done via chilmesh |
| `99_In_Progress/*` | - | skip (drafts) |

## chilmesh reuse

| quadmesh uses | from |
|---|---|
| `CHILmesh` | `chilmesh.CHILmesh` |
| `read_from_fort14` / `write_to_fort14` | classmethod / method |
| `boundary_edges` / `boundary_node_indices` | mesh method |
| `edge2vert` / `edge2elem` / `elem2edge` | mesh method |
| `get_vertex_edges` / `get_vertex_elements` | mesh method |
| `adjacencies` (Edge2Vert, Edge2Elem, Vert2Edge) | property |
| `layers` (OE/IE/OV/IV/bEdgeIDs) | property |
| `n_elems` / `n_verts` / `n_edges` / `n_layers` | property |
| `connectivity_list` / `points` | property |
| `paths_on_outer_vertices` | `chilmesh.layer_paths` |
| `smooth_mesh(method)` | method |
| `signed_area` / `elem_quality` | method |

## collapse alignment note

MATLAB `subroutineCleanupBoundaryQuads`:
- corner = middleVertID, stays at its position.
- side1 = `verts[(ci-1)%4]`, side2 = `verts[(ci+1)%4]` -- both remapped to corner everywhere.
- Bad quad deleted. Two vertices removed per pass.

Prev Python (v0.1): moved corner to opposing, remapped opposing->corner. Different topology, one vertex removed.
Current Python (v0.2+): MATLAB-aligned.

## v0.3 bug fixes

- `two_part_smoother`: `method="angle"` -> `method="angle-based"` -- smoother was silently broken (ValueError caught by bare `except Exception`). Discovered angle-based is ~42s/pass; defaulted to FEM-only.

## v0.4 bug fixes

- `edge_insertion`: `domain.edge2vert(e).astype(int).tolist()` missed `.ravel()`,
  shape `(1,2)` failed to unpack into 2 ints. Latent: aggressive path is dead
  code, so no production crash. Caught by new T4.6 tests.

## deferred v0.5

1. Case-2 iLayer-1 retriangulation -- design doc landed in v0.4
   (`specs/001-matlab-to-python-port/case-2-design.md`). Impl needs LayerState
   + adjacency invalidation; pairs with the `merge_elements` wiring (chilmesh#132
   closed upstream + consumed -- a reserved v0.3 feature, not an open blocker).
2. Aggressive leftover-tri routing wired into `tri2quad_routine` -- a reserved
   v0.3 feature (`tri2quad(aggressive=)`). chilmesh#132 (`merge_elements`) is
   closed upstream and consumed, so this is deferred by choice, not blocked by a
   missing upstream API.
3. ~~`two_part_smoother` sub-domain split~~ -- dropped (#44). The MCSmooth
   boundary-layer half of the MATLAB two-part smoother was never ported; the
   smoother is FEM-only (`fem_smoother`), so no `CHILmesh.submesh()` split is planned.
4. ADMESH library (`01_ADMESH_Library/`).
5. MATLAB ground-truth elem counts for parity tests -- current scaffold uses
   Python regression baseline (Block_O `.mat` is MATLAB-opaque, can't extract
   without running MATLAB).

## chilmesh gaps (all closed upstream + consumed, 2026-05-22..24)

All five filed chilmesh API issues are closed upstream and consumed here; none is an open blocker (see CLAUDE.md `## chilmesh`).

- chilmesh#132: `MutableMesh.merge_elements` -- closed upstream. Wiring `tri2quad(aggressive=)` to it is a reserved v0.3 feature, not a blocker.
- chilmesh#133: public `ccw_edges_around_vert` -- consumed; `_topology.py` uses the public helper, no private call remains.
- chilmesh#134: `CHILmesh(compute_adjacencies=True)` independent of `compute_layers` -- consumed.
- chilmesh#138: `CHILmesh.submesh(elem_ids)` -- closed upstream; adoption mooted by the `two_part_smoother` -> `fem_smoother` switch (#44). No longer a quadmesh smoother blocker.
- chilmesh#139: `angle_based_smoother` performance -- consumed; port uses `fem_smoother` only (`two_part_smoother` deprecated).

## Recombination operators (new in M2)

| Thesis ref | Python | Status |
|---|---|---|
| Fig 3.2 (p39) — edge-swap | `_recombine.edge_swap` | done |
| Fig 3.3 (p39) — vertex-duplication | `_recombine.vertex_duplication` | done |
| Fig 3.6 (p40) / Fig 4.4 (p69) — edge-flip + walk | `_recombine.edge_flip`, `walk_isolated_tri` | done |
| Ch 4.1 — IE-before-OE, T1/T2 heuristics | `_match_quadmesh_plus.match_layer_heuristic` | done |
| Ch 4.2 — OE-before-IE, walkability pre-pass | `_match_quadmesh_plus.walkability_prepass` | done |
| T007 — LayerState | `_tri_removal.LayerState` | done |

## chilmesh gaps (all closed upstream + consumed)

None open. Retained as a resolution ledger; live detail is in the section above.

| API | Issue | Status |
|---|---|---|
| `merge_elements` | chilmesh#132 | closed upstream; `tri2quad(aggressive=)` wiring reserved for v0.3 (not blocked) |
| `ccw_edges_around_vert` public | chilmesh#133 | consumed; `_topology` uses the public helper |
| `submesh()` API | chilmesh#138 | closed; adoption mooted by `fem_smoother` switch (#44) |
| `angle_based_smoother` perf | chilmesh#139 | consumed; port uses `fem_smoother` only |
