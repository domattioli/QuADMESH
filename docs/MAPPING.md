# MATLAB -> Python Map

Port status. v0.5 (faithful-port milestone M2).

| MATLAB (`02_QuADMESH_Library/`) | Python (`quadmesh/`) | Status |
|---|---|---|
| `00_Main/Main.m` | `cli.py` + `pipeline.run_pipeline` | done |
| `01_Create_Quad_Domain/createQuadDomain.m` | `create_quad_domain` | done (polygon mode) |
| `01_Create_Quad_Domain/drawSubdomain.m` | - | skip (GUI) |
| `02_Tri2Quad_Routine/Tri2QuadRoutine.m` | `tri2quad.tri2quad_routine` | done: layer-ordered per-layer sweep (`method="quadmesh+"`); MATLAB parity is the port intent; no test verifies it (see [`algorithm.md`](algorithm.md) section 7); the removed `"matching"` and `"faithful"` values raise ValueError (#46) |
| `02_Tri2Quad_Routine/identifyEdgesFun.m` | - | skip (superseded by v2) |
| `02_Tri2Quad_Routine/identifyEdgesFun_v2.m` | `identify_edges.identify_edges_in_layer` | done |
| `02_Tri2Quad_Routine/mergeTrianglesFun.m` | `chilmesh.quads_from_tri_pairs` | done |
| `02_Tri2Quad_Routine/CCWEdgesAroundVertsFun.m` | `CHILmesh.ccw_edges_around_vert` | done |
| `02_Tri2Quad_Routine/plotQuadProgress.m` | - | skip (plot) |
| `03_Layer_Paths/PathsOnOV.m` | `chilmesh.layer_paths.paths_on_outer_vertices` | done via chilmesh |
| `03_Layer_Paths/pathRewind.m` | - | not ported: no rewind exists in `identify_edges` or `chilmesh.layer_paths`; at a dead end the walk stops and a new path is seeded (port_check items 29-30) |
| `04_Remove_Triangles/removeTrianglesFun.m` | `_tri_removal.route_leftover_tri` | done: all cases; recombination ops wired (`_recombine.py`). The `onMeshBoundary` test (`removeTrianglesFun.m:12`, `iLayer == 1`) maps to `li == 0` (`tri2quad._is_boundary_layer`). The `CM.nLayers == Domain.nLayers` guard is not ported. `create_quad_domain` builds a fresh CHILmesh for the selected elements, so its layers are recomputed and no stale full-mesh `nLayers` exists; in polygon mode layer 0 is the subdomain boundary, not the full-mesh boundary (port_check item 7). Live path: `SweepContext` (MATLAB bookkeeping for leftover triangles restored, see [Port vs MATLAB differences](#port-vs-matlab-differences)). Python additions: a triangle that no case changes is passed to the post-sweep closing pass (`_remove_boundary_tris`, edge swap, point insertion), and in layer 0 a one-boundary-edge triangle is bisected in place of `edgeRemoval`, so every original boundary vertex is kept (spec 059). |
| `04_Remove_Triangles/edgeInsertion.m` | `_tri_removal.SweepContext.vertex_split` (live); `_tri_removal.edge_insertion` (stand-alone helper, not on the live path) | done on the live path: CASE 2 re-triangulates iLayer-1 as two fans plus one bridge, tElemID is split on diagonal 2-4, OE/IE/OV/IV follow L150-L234; differences in the table below |
| `04_Remove_Triangles/edgeBisection.m` | `_tri_removal.SweepContext.bisect` (live); `_tri_removal.edge_bisection` (stand-alone helper) | done on the live path: opposite triangle split (L78-L80), tElemID split in Domain (L83-L88), OV/IV update (L89-L90) |
| `04_Remove_Triangles/edgeRemoval.m` | `_tri_removal.edge_removal` (stand-alone helper) | not on the live path: the sweep bisects instead of collapsing (port_check items 46, 62) |
| `05_Post-Process_Routine/PostProcessRoutine.m` | `post_process.post_process_routine` | done |
| `05_Post-Process_Routine/plotQualityProgress.m` | `quality_report.compute_quality_stats` + `format_quality_report` | done (stats; plot skipped) |
| `06_Cleanup_Boundary_Quads/CleanupBoundaryQuads_v2.m` | `cleanup_boundary_quads` | done (collapse MATLAB-aligned: side verts -> corner; shift: Python-only) |
| `06_Cleanup_Boundary_Quads/TruncateBoundaryQuads.m` | - | skip (legacy) |
| `07_Doublet_Collapse/DoubletCollapse.m` | `doublet_collapse.doublet_collapse` | done (removes interior valence-2 doublets only; the `DoubletCollapse.m` header says it "collapses all concave quads", which overstates it, because its code targets interior valence-2 vertices only) |
| `08_Quad_Vertex_Merge/QuadVertexMerge.m` | - | skip (legacy) |
| `08_Quad_Vertex_Merge/QuadVertexMerge_v2.m` | `quad_vertex_merge.quad_vertex_merge` | done |
| `10_Remove_Unused_Vertices/RemoveUnusedVertices.m` | `remove_unused.remove_unused_vertices` | done |
| `11_FEM_Smoothing/FEMSmooth.m` | `post_process.fem_smoother` | done |
| `11_FEM_Smoothing/MCSmooth.m` | - | not ported (boundary-layer MCSmooth half never implemented) |
| `11_FEM_Smoothing/twoPartSmoother.m` | `post_process.fem_smoother` | done (FEM half only; `two_part_smoother` stays as a deprecated alias; MCSmooth half absent) |
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
- side1 = `verts[(ci-1)%4]`, side2 = `verts[(ci+1)%4]`; both are remapped to corner everywhere.
- Bad quad deleted. Two vertices removed per pass.

Python (v0.2+) is MATLAB-aligned.

## Version history

### v0.1 collapse

Python v0.1 moved the corner to the opposing vertex and remapped opposing->corner. The topology differed from MATLAB and removed one vertex.

### v0.3 bug fixes

- `two_part_smoother`: `method="angle"` -> `method="angle-based"`. The smoother was silently broken (ValueError caught by bare `except Exception`). Angle-based costs ~42s/pass, so the default is FEM-only.

### v0.4 bug fixes

- `edge_insertion`: `domain.edge2vert(e).astype(int).tolist()` missed `.ravel()`,
  shape `(1,2)` failed to unpack into 2 ints. Latent: aggressive path is dead
  code, so no production crash. Caught by new T4.6 tests.

## deferred v0.5

1. ~~Case-2 iLayer-1 retriangulation~~: done on the live path
   (`SweepContext._apply_vertex_split`; two fans plus one bridge). See
   [Port vs MATLAB differences](#port-vs-matlab-differences) for what still differs.
2. Aggressive leftover-tri routing wired into `tri2quad_routine`: a reserved
   v0.3 feature (`tri2quad(aggressive=)`). chilmesh#132 (`merge_elements`) is
   closed upstream and consumed, so the deferral is a choice; no upstream API is missing.
3. ~~`two_part_smoother` sub-domain split~~: dropped (#44). The MCSmooth
   boundary-layer half of the MATLAB two-part smoother was never ported; the
   smoother is FEM-only (`fem_smoother`), so no `CHILmesh.submesh()` split is planned.
4. ADMESH library (`01_ADMESH_Library/`).
5. MATLAB ground-truth element counts for the parity tests. `tests/test_parity.py`
   pins a Python regression baseline, because the Block_O `.mat` file cannot be
   read without MATLAB. Parity status: [`algorithm.md`](algorithm.md) section 7.

## chilmesh gaps (all closed upstream + consumed, 2026-05-22..24)

All five filed chilmesh API issues are closed upstream and consumed here; none is an open blocker (see `AGENTS.md`).

- chilmesh#132: `MutableMesh.merge_elements`: closed upstream. Wiring `tri2quad(aggressive=)` to it is a reserved v0.3 feature and blocks nothing.
- chilmesh#133: public `ccw_edges_around_vert`: consumed; callers use the public helper directly.
- chilmesh#134: `CHILmesh(compute_adjacencies=True)` independent of `compute_layers`: consumed.
- chilmesh#138: `CHILmesh.submesh(elem_ids)`: closed upstream; the `two_part_smoother` -> `fem_smoother` switch (#44) makes adoption moot. It does not block the quadmesh smoother.
- chilmesh#139: `angle_based_smoother` performance: consumed; port uses `fem_smoother` only (`two_part_smoother` deprecated).

## Recombination operators (new in M2)

| Thesis ref | Python | Status |
|---|---|---|
| Fig 3.2 (p39): edge-swap | `_recombine.edge_swap` | done |
| Fig 3.3 (p39): vertex-duplication | `_recombine.vertex_duplication` | done |
| Fig 3.6 (p40) / Fig 4.4 (p69): edge-flip + walk | `_recombine.edge_flip`, `walk_isolated_tri` | done |
| Ch 4.1: IE-before-OE, T1/T2 heuristics | `_match_quadmesh_plus.match_layer_heuristic` | done |
| Ch 4.2: OE-before-IE, walkability pre-pass | `_match_quadmesh_plus.walkability_prepass` | done |
| T007: LayerState | `_tri_removal.LayerState` | done |

## chilmesh gaps (all closed upstream + consumed)

None open. Retained as a resolution ledger; live detail is in the section above.

| API | Issue | Status |
|---|---|---|
| `merge_elements` | chilmesh#132 | closed upstream; `tri2quad(aggressive=)` wiring reserved for v0.3 (nothing blocks it) |
| `ccw_edges_around_vert` public | chilmesh#133 | consumed; callers use the public helper directly |
| `submesh()` API | chilmesh#138 | closed; adoption mooted by `fem_smoother` switch (#44) |
| `angle_based_smoother` perf | chilmesh#139 | consumed; port uses `fem_smoother` only |

## Sibling delegation (057)

QuADMESH calls CHILmesh where CHILmesh offers an equivalent public API. The table lists every item that was checked. "Partial" means a sibling covers only part of the behavior. Each partial row carries the label `downstream-api`. The local code stays until the sibling API exists.

| # | QuADMESH item | Sibling | Disposition |
|---|---|---|---|
| 1 | `.14` read and write in `cli.py` | `CHILmesh.read_from_fort14`, `write_to_fort14` | Already delegated. |
| 2 | `remove_unused_vertices` (`remove_unused.py`) | `CHILmesh.submesh` | Delegated. The module is a short shim that keeps the early return and the `grid_name`. |
| 3 | FEM solve in `fem_smoother` (`post_process.py`) | `CHILmesh.direct_smoother` | Delegated. On Block_O and structuredMesh1, for triangle and quad meshes, the largest point difference from the former local solver was 0.0. The local `_balendran_smooth` is removed. |
| 4 | `fem_smoother` wrapper | same as row 3 | Kept. It compacts first, stops after one pass (#107), and restores the points on an exception. |
| 5 | `two_part_smoother` | none | Kept as a deprecated alias. The warning names removal in 0.4.0. |
| 6 | `truss_smoother` | `chilmesh.optimize_with_admesh_truss` | Partial, `downstream-api`. The upstream path handles triangles only. Needed: a quad or mixed-element entry point. |
| 7 | `_topology.py` shims | `CHILmesh.ccw_edges_around_vert`, `chilmesh.quad_from_tri_pair` | Done. `_topology.py` removed; call sites use the CHILmesh APIs directly. |
| 8 | `_build_tri_adjacency` | `adjacencies["Edge2Elem"]` | Partial, `downstream-api`. It works on a raw `(N, 3)` array, and CHILmesh needs a mesh object. Needed: an adjacency builder for raw connectivity. |
| 9 | `create_quad_domain` polygon mask | `CHILmesh.submesh`, `admesh in_polygon` | Partial, `downstream-api`. `submesh` renumbers vertices, and `tri2quad(parent=...)` needs the original numbering. Kept. `matplotlib` is a declared dependency. |
| 10 | `compute_quality_stats` | `chilmesh.element_quality` | Already delegated. The wrapper keeps the report format and the 0.3 threshold. |
| 11 | `identify_edges_in_layer` | `layers`, `paths_on_outer_vertices` | Unique. Layer peeling comes from CHILmesh. |
| 12 | `tri2quad` core | `MutableMesh.merge_elements` | Unique. Wiring `merge_elements` is reserved for `tri2quad(aggressive=)`. |
| 13 | Post-process topology operations | `MutableMesh.collapse_edge`, `remove_vertex` | Unique. Upstream has no quad-aware equivalent. |
| 14 | `_merge_tri_pairs_to_quads` (`repair.py`) | `chilmesh.quads_from_tri_pairs` | Partial, `downstream-api`. The local function chooses the pairs greedily and rejects bowtie quads. The upstream function merges pairs that the caller already chose. Needed: a pairing and validity entry point. |
| 15 | `quadmesh.validation` | none (tracked as issue #142) | Partial, `downstream-api`. Needed: `chilmesh.validate`. |
| 16 | `scripts/render_quadmesh.py` | `chilmesh.chilplotting` | Partial, `downstream-api`. Mesh drawing can delegate. The diagnostic overlays stay. It is a script outside the package API. |
| 17 | `tests/_mesh_provision.py`, `scripts/fetch_fixtures.py` | none | Partial, `downstream-api`. The token-based fetch and the SHA-1 check stay. A shared fetch API would remove the local copy. |
| 18 | ADMESH | `admesh.quad_prep` | No duplicate. QuADMESH does not depend on ADMESH. |

## Benchmark subpackage (058)

`quadmesh.benchmark` compares tri-to-quad meshers through adapters. It has no MATLAB counterpart. It reads and writes Gmsh `.msh` 2.2 and Wavefront `.obj` files with local helpers in `benchmark/_io.py`.

| Item | Sibling | Status |
|---|---|---|
| `.msh` and `.obj` read and write (`benchmark/_io.py`) | none (CHILmesh has `.14` I/O only) | Partial, `downstream-api`. Needed: OBJ and MSH I/O in CHILmesh. The local helpers stay until it exists. |

## Port vs MATLAB differences

Every item that `pseudo/port_check.md` (verification checklist of
`pseudo/final.md`) marks DEVIATES-DOCUMENTED, DEVIATES-UNDOCUMENTED or MISSING.
Status: **deliberate** = the port differs on purpose and keeps the
difference; **documented, not fixed** = recorded here by operator ruling, no
behaviour change.

Restored to MATLAB in the leftover-triangle bookkeeping change (no longer
deviations): item 49 (appended outer half goes to IE{iLayer-1},
edgeBisection.m:L78-L80), 51 (tElemID split in Domain, half to OE{iLayer},
L83-L88), 52 (new vertex to OV{iLayer} and IV{iLayer-1}, L89-L90), 59 (OE iff
exactly one vertex in newBoundaryVerts, edgeInsertion.m:L206-L210), 60
(tElemID split on quad diagonal 2-4, edgeInsertion.m:L224, splitQuad.m:L21-L22),
61 (appended half to IE{iLayer} iff <= 1 vertex in newBoundaryVerts,
edgeInsertion.m:L225-L234).

| item | MATLAB cite | port behaviour | status |
|---|---|---|---|
| 1 | Main.m:L56-L58 | `n_smooth_iter` defaults to 3, not 100 (100 is the MCSmooth sweep count, not ported); FEM stops after 1 pass (#107); no plotProgress. | deliberate |
| 7 | createQuadDomain.m:L83 | A fresh CHILmesh is built for the selection; no stale `CM.nLayers`. | deliberate |
| 11 | identifyEdgesFun_v2.m:L29-L31 | Keeps only boundary edges with BOTH endpoints in OV; MATLAB keeps mixed OV/IV edges. | documented, not fixed |
| 12 | identifyEdgesFun_v2.m:L46, L58 | The initial Path(end) visit is skipped. | documented, not fixed |
| 13 | identifyEdgesFun_v2.m:L50-L55 | Fallback takes the first boundary edge touching `u` only, and is applied at every vertex. | documented, not fixed |
| 16 | identifyEdgesFun_v2.m:L88 | 0-based off-by-one: Python skips when `idown == 1` (MATLAB's flip case) and flips at `idown == 2` (MATLAB position 3). | documented, not fixed |
| 17 | identifyEdgesFun_v2.m:L49, L65-L67 | No first iteration with up = down = closing edge. | documented, not fixed |
| 18 | identifyEdgesFun_v2.m:L91 | Candidates are `ordered[1:idown]`, not positions 2..totalNumEdges-1 (differs at pinch vertices and in the flip case). | documented, not fixed |
| 23 | PathsOnOV.m:L105-L118 | Path 1 seeds at the junction of maximum remaining degree, else the first OV vertex. | deliberate |
| 24 | PathsOnOV.m:L157, L178 | No preference for non-junction neighbours. | documented, not fixed |
| 29 | PathsOnOV.m:L323-L353 | No rewind: at a dead end the walk stops and a new path is seeded. | documented, not fixed |
| 30 | pathRewind.m:L85-L144 | pathRewind not ported. | documented, not fixed |
| 31 | PathsOnOV.m:L412, L432 | No "last junction lone-node candidate" rule in later paths. | documented, not fixed |
| 32 | PathsOnOV.m:L677 | No lone-node restriction on non-junction neighbours in later paths. | documented, not fixed |
| 36 | Tri2QuadRoutine.m:L28 | Merges in selection order, but skips a merge with a corner >= 177 deg (#108). | deliberate |
| 37 | mergeTrianglesFun.m:L36 | Quad order is [apex_a, s0, apex_b, s1] (CCW), so only the start corner differs. | deliberate |
| 39 | Tri2QuadRoutine.m:L36-L37 | Leftovers are re-paired by `match_layer_heuristic` (thesis T1/T2) before routing. | deliberate |
| 40 | removeTrianglesFun.m:L12-L16 | `onMeshBoundary` is `li == 0`; the stale-nLayers guard is not ported. | deliberate |
| 41 | removeTrianglesFun.m:L45-L47 | Classifies on the live outer ring, not the stale `subDomain.edge2Vert`. | deliberate |
| 42 | removeTrianglesFun.m:L57-L60 | Ring-edge bisection competes with the vertex splits of the same triangle; the lowest valence cost wins (tie: longest first); inside the mesh the new vertex moves off the midpoint toward the outer apex. | deliberate |
| 43 | removeTrianglesFun.m:L68-L71 | edgeInsertion(2) is `vertex_split`. | deliberate |
| 44 | removeTrianglesFun.m:L63-L66 | edgeInsertion(1) is `vertex_split`. | deliberate |
| 45 | removeTrianglesFun.m:L73-L76; edgeInsertion.m:L267-L273 | The triangle is not dropped: its boundary edge is bisected at the midpoint (near-180-degree boundary quad), or it is refused with `refuse_boundary_merge`. | deliberate |
| 46 | removeTrianglesFun.m:L79-L83 | edgeRemoval is replaced by a boundary bisection; edges are never collapsed. | deliberate |
| 47 | edgeBisection.m:L24-L31 | Edge choice by valence cost (tie: longest), not the first edge. Midpoint only in layer 0; inside the mesh the point moves toward the apex (`APEX_FRACTIONS`, `MIN_SINE`), flat midpoint as last resort. | deliberate |
| 54 | edgeInsertion.m:L28-L35 | Every ring vertex of the triangle is tried; the best side, fraction and bridge win. | deliberate |
| 55 | edgeInsertion.m:L63-L67, L132-L133 | `n` goes on ring edge (b, s) at the best of `SPLIT_FRACTIONS`; `b` is not moved (MATLAB moves tbVertID), so no corner reaches 180 deg and no element inverts. | deliberate |
| 56 | edgeInsertion.m:L127, L136 | b -> n in all fan elements between the triangle and the ring edge, on the side chosen. | deliberate |
| 57 | edgeInsertion.m:L139-L145 | Side B gives [b, p, q, n] (MATLAB form); side A gives [b, n, p, q]. | deliberate |
| 58 | edgeInsertion.m:L150-L218 | Two fans plus one bridge as in MATLAB, but only for the iLayer-1 triangles in the sector next to (b, s), not every iLayer-1 triangle at tbVertID. The bridge vertex is the one with the lowest valence cost (tie: best worst corner, then MATLAB's switchVertID). Port guard: a bridge is rejected if a new triangle would have no vertex on the outer ring of its layer (it could not be closed later). | deliberate |
| 62 | edgeRemoval.m:L9-L26 | Not reached from the pipeline; the squeeze in `_remove_boundary_tris` is off by default. | deliberate |
| 63 | edgeRemoval.m:L29 | Not reached; `edge_removal` does not touch OE{1}. | deliberate |
| 64 | Tri2QuadRoutine.m:L52-L53 | Padding is [v1 v2 v3 v3]; in polygon mode the unselected triangles are not appended. | documented, not fixed |
| 67 | PostProcessRoutine.m:L32-L47 | Inner loop capped at `max_inner_iter=5`. | deliberate |
| 69 | PostProcessRoutine.m:L56-L63 | Outer loop continues if the inner loop or CBQ reduced the count (MATLAB: CBQ only); capped at 5. | documented, not fixed |
| 70 | PostProcessRoutine.m:L67-L76 | On an exception the points are reverted and the loop stops; MCSmooth not run. | deliberate |
| 77 | QuadVertexMerge_v2.m:L14-L32 | One pass per call; repetition comes from the capped inner loop. | deliberate |
| 79 | CleanupBoundaryQuads_v2.m:L85-L96 | `len(on_bdy) < 2` lets 3-boundary-edge quads through when two are adjacent. | documented, not fixed |
| 80 | CleanupBoundaryQuads_v2.m:L106-L108 | Threshold > 134.0 deg, not > 135.00. | documented, not fixed |
| 81 | CleanupBoundaryQuads_v2.m:L119-L129 | Used-check covers elements around all 4 quad vertices (stricter). | documented, not fixed |
| 82 | CleanupBoundaryQuads_v2.m:L238-L245 | Collapse skipped when it would bowtie a neighbour or move a protected vertex. | deliberate |
| 85 | FEMSmooth.m:L20-L29 | Quads use a Q4 bilinear Laplacian, not MATLAB's ke{2} = {D, Q, O, Q'} with mu = 1. | documented, not fixed |
| 86 | MCSmooth.m:L31, L69-L73 | MCSmooth not ported. | documented, not fixed |
| 87 | MCSmooth.m:L155-L167 | MCSmooth not ported. | documented, not fixed |
| 88 | MCSmooth.m:L68, L84-L101, L107 | MCSmooth not ported; FEM only, one effective pass. | documented, not fixed |

Other port departures in the leftover-triangle path (not checklist items):

- `SweepContext.sync` retires consumed Domain rows (merged pairs and the
  Domain halves of closed triangles) at each layer start. MATLAB keeps them in
  Domain. The port's processed layers live in `work.quads`, and a vertex split
  rewrites only live elements, so keeping the halves would leave stale rows.
- Valence choice (operator ruling 2026-10-26): where MATLAB leaves a choice
  (which edge to bisect, which bridge diagonal, which vertex-split side and
  fraction), the candidate whose vertex valences are closest to ideal wins.
  When the triangle has a ring edge, every valid bisection and every valid
  vertex split of it compete in one pool (MATLAB always bisects first; the
  port bisects first only on a cost tie, via list order). The cost scores
  every vertex the full candidate touches (quad, moved fan, outer fans and
  bridge) on its expected final quad valence `nq + nt/2` (triangles pair into
  quads later), target 4 inside and `4 * angle / 2 pi` on the domain
  boundary. The earlier interim score `|nq/4 + nt/6 - target|` and the
  bisection-first dispatch made the annulus valence deviation worse than the
  pre-restore port on 3 of 6 cells; the pooled final-valence score is no
  worse on all 6 (numbers in the PR).
- `tri2quad._point_insert_tri_pairs`: a pentagon (lone tri + neighbour quad)
  has no all-quad cover, so the tri's domain-boundary edge is split at its
  midpoint and the hexagon plus one interior point becomes three quads. The
  old two-quad split left a triangular hole.
- The bisected Domain triangle halves are written CCW (`isPolyCCW`); MATLAB
  does not check the appended rows (edgeBisection.m:L87, item 53).
