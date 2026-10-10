# QuADMESH+ converts a triangulation into quadrilaterals layer by layer

This document describes the QuADMESH+ algorithm (Quadrangular ADvanced MESH generator for hydrodynamic models) and its Python port. Sections 2 and 3 describe the default path. Section 5 describes an experimental fallback path. Each section states which of the two it covers.

The source is Mattioli (2017), chapters 3 and 4, at [`docs/Mattioli_Thesis.pdf`](Mattioli_Thesis.pdf). Code pointers give `file:line` in `src/quadmesh/`.

The words "vertex", "node", and "point" are interchangeable for mesh points. In section 5, "vertex" also names a node of the triangle adjacency graph; the text says which one applies.

## 1. Summary: triangles in, quadrilaterals out, no interior triangle left

The input is an existing triangular mesh of a 2D shallow-water domain (for example an ADCIRC `fort.14` file). The output is a quadrilateral mesh on the input vertices, plus the few points that section 3.3 adds. Each output quadrilateral is two adjacent input triangles merged across their shared edge.

The default method is `method="quadmesh+"`. The alias `method="layered"` selects the same path. The values `"faithful"` and `"matching"` raise `ValueError`.

One invariant holds on every output: zero interior residual triangles. An interior residual triangle is a triangle with no domain-boundary edge.

Some boundary triangles can remain in intermediate or explicitly configured output. The test `tests/test_no_interior_tris.py` enforces this invariant (the faithfulness invariant).

The conversion keeps the input vertices. Points are added or moved only by the local operations that clear unpaired triangles (section 3.3). The pairing step itself adds no points.

## 2. The thesis algorithm matches triangles innermost layer first (Mattioli 2017)

The port implements the thesis algorithm as the default path (section 3).

### 2.1 Mesh layers order the domain by topological distance to the boundary

The mesh is split into layers (thesis section 3.2.1). Layer 0 is the band of elements on the domain boundary.

Each further layer is the band next to the previous one, so the innermost layer is the farthest from the boundary in topological distance. The layers come from the `chilmesh` skeletonization (`domain.layers`, `domain.n_layers`).

Each layer L has four sets (thesis section 3.2.1, Figure 3.18):

| Set | Meaning |
|---|---|
| OE(L), outer elements | triangles of layer L that share an edge with the next layer toward the boundary |
| IE(L), inner elements | triangles of layer L that share no edge with that layer |
| OV(L), outer vertices | vertices on the outer ring of layer L |
| IV(L), inner vertices | vertices on the inner ring of layer L |

A layer can border itself (a self-intersecting layer). A flagged edge is an edge whose two endpoints are both inner vertices (thesis section 3.2.1, Figure 3.19).

The two triangles on either side of a flagged edge are treated as non-neighbours. This keeps a matching from joining the two strips of a folded layer.

### 2.2 Interior layers are matched from the inside out, IE before OE

The sweep starts at the innermost layer and moves outward (thesis section 3.2.2 and chapter 4). In layer L, all intra-layer matchings come before any inter-layer matching with the next layer outward.

Inside a layer, the algorithm selects a first triangle T1 and then its partner T2 (thesis sections 4.1.1 and 4.1.2):

- T1 is a triangle with the fewest eligible neighbours. An eligible neighbour is an unmatched neighbour in the same layer, not across a flagged edge.
- When all candidates have two or more eligible neighbours, IE triangles go first. Only OE triangles can still match into the next layer, so only IE triangles can become isolated.
- Tie-breakers then select T1 and T2 by neighbour counts and by the number of IE neighbours.

An isolated triangle is a triangle with no eligible neighbour. When one appears, the thesis isolates a second unmatched triangle that shares a vertex with it. An edge swap later turns the pair into quadrilaterals (thesis section 4.1.2, Figure 4.3).

### 2.3 The boundary layer is matched last, OE before IE

The boundary layer has no layer outside it, so an unmatched boundary-layer triangle stays unmatched (thesis section 4.2). Edge flips first improve the walkability of the layer (thesis section 4.2.1).

The matching then gives OE triangles priority over IE triangles (thesis section 4.2.2). The aim is that the last triangle left, if any, is an IE triangle. An IE triangle has no edge on the domain boundary, and the thesis clears it by adding one point to the boundary.

The thesis reports that this step leaves at most one triangle on the boundary in typical cases; an odd number of boundary vertices is a common cause. Larger meshes with complex boundaries can leave more.

Remaining triangles are removed by edge swap or vertex duplication (two triangles that share a vertex), by edge collapse (an OE triangle), or by edge insertion (an IE triangle) (thesis section 4.2.2).

## 3. The port runs the per-layer sweep by default

This section describes the Python code. `tri2quad` is `tri2quad_routine` (`src/quadmesh/__init__.py:6`, `src/quadmesh/tri2quad.py:995`).

### 3.1 Dispatch in `tri2quad_routine` selects the path from the layer count

| Input | Code path | Location |
|---|---|---|
| `method="quadmesh+"` (default) | renamed to `"layered"` | `tri2quad.py:1054-1057` |
| `method="faithful"` or `"matching"` | `ValueError` | `tri2quad.py:1059-1063` |
| any other unknown method | `ValueError` | `tri2quad.py:1095` |
| `"layered"` and `domain.n_layers > 0` | per-layer sweep `_quadmesh_plus_per_layer` (default path) | `tri2quad.py:1065-1081` |
| `"layered"` and `domain.n_layers == 0` (layerless mesh) | global matcher, experimental fallback (section 5) | `tri2quad.py:1083-1093` |

A layerless mesh is, for example, a mesh too coarse for skeletonization.

### 3.2 The per-layer sweep follows `Tri2QuadRoutine.m`

`_quadmesh_plus_per_layer` (`tri2quad.py:805`) loops from the innermost layer to the boundary layer (`tri2quad.py:839`). For each layer it runs three steps:

1. Identify edges. `identify_edges_in_layer` (`src/quadmesh/identify_edges.py:51`) ports `identifyEdgesFun_v2.m`. It returns the edges to remove (each removal merges two triangles) and the flagged vertex pairs of the layer.
2. Merge pairs. `merge_tri_pair` (`src/quadmesh/_topology.py:14`) merges each selected pair into a quadrilateral. A merge with a corner of 177 degrees or more is skipped (`_quad_is_degenerate`, `tri2quad.py:780`). Then `match_layer_heuristic` (`src/quadmesh/_match_quadmesh_plus.py:220`) pairs the remaining layer triangles with the thesis T1 and T2 rules (`_t1_select`, `_match_quadmesh_plus.py:55`; `_t2_ladder`, `:104`). The flagged pairs go to it as forbidden pairs (`tri2quad.py:888-917`).
3. Route leftovers. `route_leftover_tri` (`src/quadmesh/_tri_removal.py:308`) ports `removeTrianglesFun.m`. It clears each unpaired triangle by edge bisection (`:143`), edge insertion (`:260`), or edge removal (`:121`), selected by boundary-edge count and by `can_remove_edges`.

Steps 2 and 3 treat layer 0 as the boundary layer. `chilmesh` numbers layers from the domain boundary inward, so layer 0 holds the triangles on the domain boundary. One predicate, `_is_boundary_layer` (`tri2quad.py:668`), sets the matcher flag (`:926`) and the routing flag (`:949`). It matches `removeTrianglesFun.m:12` (`iLayer == 1`, 1-based).

In layer 0, a leftover triangle with one boundary edge is bisected on that edge (`_tri_removal.py:378-385`). An edge collapse (`edgeRemoval`) would move two original boundary vertices, so the sweep passes `preserve_boundary_verts=True` to `route_leftover_tri`. If no routing case applies, `route_leftover_tri` returns `None`. The sweep then leaves the triangle unconsumed (`tri2quad.py:969`), and it goes to the closing pass in section 3.3.

After the loop, triangles that belong to no layer go to the global matcher `_match_tris_to_quads` without layer priority (`tri2quad.py:960-971`). This is the second trigger of the experimental fallback.

### 3.3 Post-sweep stages clear the remaining boundary triangles

`tri2quad_routine` then runs these stages on the remaining triangles, in order:

| Stage | Function | Default | Effect on points |
|---|---|---|---|
| Boundary-triangle removal | `_remove_boundary_tris` (`tri2quad.py:280`) | on (`remove_boundary_tris=True`) | prefers dropping a triangle over collapsing a boundary edge (`minimize_boundary_change=None` resolves to `True`) |
| Edge swap of tri-quad-tri fans | `_edge_swap_tri_pairs` (`tri2quad.py:402`) | on | adds none |
| Point insertion | `_point_insert_tri_pairs` (`tri2quad.py:529`) | on (`point_insert=True`, `tri2quad.py:1003`) | adds one interior point per cleared triangle |
| Refused boundary triangles | appended as triangles (`tri2quad.py:1124-1131`) | off (`refuse_boundary_merge=False`) | adds none |

Point insertion runs only on the `"layered"` path and only on triangles that are still unpaired (`tri2quad.py:1118`). Set `point_insert=False` to keep those triangles as boundary triangles. Set `can_remove_edges=False` to stop boundary-edge collapse during routing.

## 4. The port differs from the thesis in eight places

| Topic | Thesis | Port | Code | Status |
|---|---|---|---|---|
| Layer order | innermost first, boundary last | innermost first, boundary last | `tri2quad.py:839` | same |
| Edge selection per layer | `identifyEdgesFun_v2` | `identify_edges_in_layer` | `identify_edges.py:51` | same intent |
| T1 and T2 selection | full tie-breaker hierarchy (sections 4.1.1, 4.1.2) | eligible-neighbour count with IE/OE order; T2 by ladder walk | `_match_quadmesh_plus.py:55`, `:104`, `:220` | differs (reduced tie-breakers) |
| Flagged edges | neighbours across a flagged edge are not eligible | flagged pairs forbidden in the per-layer matcher | `tri2quad.py:888-917` | same |
| Isolated triangles | isolate a partner, then edge swap | leftover routing per `removeTrianglesFun`; post-sweep edge swap | `_tri_removal.py:308`, `tri2quad.py:402` | differs |
| Near-flat merges | not described | merge skipped when a corner is 177 degrees or more | `tri2quad.py:780` | port-only |
| Elements outside every layer | not described | global matcher fallback | `tri2quad.py:960-971` | port-only |
| Layerless mesh | not described | global matcher fallback | `tri2quad.py:1083-1093` | port-only |
| Boundary-layer index | the boundary layer is matched last, OE before IE; `removeTrianglesFun.m:12` tests `iLayer == 1` | layer 0 is the boundary layer for the matcher, leftover routing and `_layer_priority` | `tri2quad.py:668`, `:926`, `:949` | same |
| Boundary-edge collapse in the boundary layer | `edgeRemoval` when `canRemoveEdges` is true | edge bisection, so that every original boundary vertex is kept | `_tri_removal.py:378-385` | differs |
| Lone boundary triangles | add a boundary point (IE) or collapse an edge (OE) | interior point insertion, on by default | `tri2quad.py:529`, `:1118` | differs |

## 5. Experimental fallback: layer-priority global matching

The global matcher is a port-side experiment. The operator stated on 2026-10-10: "the hybrid blossom-layers was just an experiment". The code keeps it as the fallback. It runs in two cases only:

- Layerless mesh: `domain.n_layers == 0` (`tri2quad.py:1083-1093`). Here it runs with layer priority, sweep seeds, and fold-seam exclusion.
- Elements that no layer covers, after the per-layer sweep (`tri2quad.py:960-971`). Here it runs with the default interior-first priority, without seeds or forbidden edges.

The main function is `_match_tris_to_quads` (`tri2quad.py:96`). Its helpers are `_layer_priority` (`tri2quad.py:668`) and `_sweep_pairs` (`tri2quad.py:691`).

### 5.1 The matching runs on the triangle adjacency graph

Let T = {t1, ..., tn} be the triangles. The triangle adjacency graph is G = (V, E), with V = T and an edge (ti, tj) when ti and tj share one interior edge. Each merge of two triangles into a quadrilateral is one edge of G. The output is set by the matching M, a subset of E.

In this section a graph vertex is a triangle. An interior graph vertex is a triangle with no edge on the domain boundary. The fallback requires interior saturation: every interior graph vertex is in M. If n is odd, at least one triangle stays unmatched; interior saturation puts every unmatched triangle on the boundary.

### 5.2 Fold-seam edges are removed from the graph

On a self-intersecting layer, a flagged edge is an edge of G whose two endpoints are inner vertices of that layer (section 2.1). `_sweep_pairs` returns the flagged edges, and `_match_tris_to_quads` drops them from the adjacency (`tri2quad.py:149`). The graph becomes G' = (V, E \ F), where F is the set of flagged edges. Two triangles across a flagged edge are then not adjacent.

### 5.3 Layer priority orders the greedy pass

`_layer_priority` (`tri2quad.py:668`) gives each triangle one integer priority. A lower value is matched first.

| Triangle | Priority |
|---|---|
| IE triangle of interior layer Li | 2(nL - 1 - i) |
| OE triangle of interior layer Li | 2(nL - 1 - i) + 1 |
| IE triangle of the boundary layer (i = 0) | 2(nL - 1) + 1 |
| OE triangle of the boundary layer (i = 0) | 2(nL - 1) |
| triangle in no layer | 2nL + 1 |

Here nL is the number of layers. The order copies the thesis: innermost layer first, IE before OE in interior layers, OE before IE in the boundary layer.

### 5.4 Sweep seeds, greedy extension, and augmenting paths build the matching

1. Seed. `_sweep_pairs` (`tri2quad.py:691`) runs `identify_edges_in_layer` on each layer, innermost first. Each selected edge gives one seed pair. Each element is used at most once per layer, and layers do not share elements, so the seeds form a valid partial matching M0. Seed quadrilaterals follow the layer strips.
2. Greedy extension. The remaining triangles are matched in priority order. Within one priority class, the triangle with the fewest free neighbours goes first, and it takes the free neighbour with the lowest (priority, free degree).
3. Augmenting-path fixup. Each interior triangle that is still unmatched starts a breadth-first search on alternating paths (`augment`, `tri2quad.py:184`). A path that ends at a free triangle is augmenting. Swapping the matched and unmatched edges along it matches the interior triangle and moves the unmatched triangle toward the boundary (Berge's theorem: a matching is maximum if and only if no augmenting path exists).

An interior triangle stays unmatched only when the graph G' has no matching that saturates the interior set.

### 5.5 Unmatched boundary triangles go to the same post-sweep stages

The triangles that the fallback leaves unmatched go to the stages in section 3.3: boundary-triangle removal, edge swap, and point insertion.

## 6. Blossom-Quad relates only to the experimental fallback

The thesis algorithm (section 2) has no functional relation to Blossom-Quad (Remacle et al. 2012). The operator stated on 2026-10-10: "the original thesis did not involve anything related functionally to blossom". The thesis cites Blossom-Quad as prior work in its survey of matching approaches (thesis section 3.1.2) and then uses layer-ordered heuristics in place of a global matching algorithm (thesis section 3.2.2).

The fallback in section 5 shares one framing with Blossom-Quad: both build quadrilaterals from a matching on the triangle adjacency graph (the dual graph of the triangulation). They differ in these ways:

| Topic | Blossom-Quad (Remacle et al. 2012) | QuADMESH fallback |
|---|---|---|
| Matching method | minimum-cost perfect matching (Edmonds' blossom algorithm) | greedy pass with priorities, then augmenting-path fixup; no global cost minimum |
| Order | no layer order | layer order: innermost first, IE/OE rules (`tri2quad.py:668-689`) |
| Fold seams | none | flagged edges removed from the graph (`tri2quad.py:149`) |
| Unmatched triangles | perfect matching targets zero unmatched triangles | interior saturation steers unmatched triangles to the boundary (`tri2quad.py:184`) |
| Point insertion | part of the method that produces the all-quadrilateral mesh | the matching inserts no points; the post-sweep `point_insert` stage (on by default, `tri2quad.py:1118`) adds one interior point per remaining lone triangle |

## 7. Parity with MATLAB is intent, not a verified result

`tests/test_parity.py` pins the current Python output on Test_Case_1 and Block_O as a regression baseline. MATLAB element counts for these meshes were never captured: the Block_O `.mat` artifact cannot be read from Python. The test therefore compares Python with Python, with loose tolerances.

The `Tri2QuadRoutine.m` row of [`MAPPING.md`](MAPPING.md) records MATLAB parity as the intent of the port. The function map in `MAPPING.md` shows which MATLAB routines have a Python counterpart. Capturing the MATLAB counts remains open (`MAPPING.md`, open item 5).

## 8. References

- Mattioli, D. D. (2017). QuADMESH+: A Quadrangular ADvanced Mesh Generator for Hydrodynamic Models. Master's thesis, The Ohio State University. OhioLINK ETD, http://rave.ohiolink.edu/etdc/view?acc_num=osu1500627779532088. In-repo copy: [`docs/Mattioli_Thesis.pdf`](Mattioli_Thesis.pdf).
- Remacle, J.-F., Lambrechts, J., Seny, B., Marchandise, E., Johnen, A., Geuzaine, C. (2012). Blossom-Quad: a non-uniform quadrilateral mesh generator using a minimum cost perfect matching algorithm. International Journal for Numerical Methods in Engineering, 89(9), 1102-1119.
- Berge, C. (1957). Two theorems in graph theory. Proceedings of the National Academy of Sciences, 43(9), 842-844.
- [`docs/MAPPING.md`](MAPPING.md): MATLAB-to-Python function map.
