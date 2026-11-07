# Porting notes: CHILmesh API used by QuADMESH and its C++ equivalent

The C++ `quadmesh::Mesh` (`include/quadmesh/mesh.hpp`) replaces the CHILmesh
object for `tri2quad.py`, `_tri_removal.py`, `identify_edges.py`,
`_match_quadmesh_plus.py`, `post_process.py` and `remove_unused.py`.
Semantics follow the CHILmesh pure-Python backend (`CHILMESH_BACKEND=python`),
checked element for element by `tests/test_mesh.cpp`, `test_layers.cpp`,
`test_quality.cpp` and `test_fort14.cpp` against
`.scratch/cpp-port/ground_truth/ref/*.json` (written by `ref_tables.py`).

## Name map

| Python (CHILmesh / quadmesh) | C++ |
|---|---|
| `CHILmesh(conn, pts, grid_name=, compute_layers=, compute_adjacencies=)` | `Mesh(pts, elems, name, MeshOptions{compute_adjacencies, compute_layers})` |
| `CHILmesh.read_from_fort14(path)` | `read_fort14(path, opts)` (`fort14.hpp`) |
| `mesh.write_to_fort14(path)` | `write_fort14(mesh, path)` |
| `mesh.points` (n x 3) | `mesh.points` (`std::vector<Point>`, `Point = std::array<double,3>`) |
| `mesh.connectivity_list` | `mesh.elems` (`std::vector<Elem>`, triangle `[a,b,c,-1]`) |
| row is a padded triangle (`row[3]==row[0]`, `row[2]==row[3]`, any repeat) | `is_tri(row)` (trailing `-1` only) |
| `mesh.grid_name` | `mesh.grid_name` (empty string = `None`) |
| `mesh.boundary_segments`, `mesh.boundaries_present` | same names; writer uses `mesh.boundary_raw` |
| `mesh.n_verts`, `n_elems`, `n_edges`, `n_layers` | `n_verts()`, `n_elems()`, `n_edges()`, `n_layers()` |
| `mesh.adjacencies["Edge2Vert"]`, `mesh.edge2vert(ids)` | `mesh.edge2vert[id]` |
| `mesh.adjacencies["Edge2Elem"]`, `mesh.edge2elem(ids)` | `mesh.edge2elem[id]` |
| `mesh.adjacencies["Elem2Edge"]`, `mesh.elem2edge(ids)` | `mesh.elem2edge[e]` (triangle slot 3 = `-1`) |
| `mesh.adjacencies["Vert2Edge"]`, `get_vertex_edges(v)` | `mesh.vert2edge[v]`, `get_vertex_edges(v)` (sorted vector) |
| `mesh.adjacencies["Vert2Elem"]`, `get_vertex_elements(v)` | `mesh.vert2elem[v]`, `get_vertex_elements(v)` (sorted vector) |
| `adjacencies["EdgeMap"].find_edge(a, b)` | `mesh.find_edge(a, b)` (`-1` if absent) |
| `mesh._build_adjacencies(validate=False)`, `rebuild_adjacencies()` | `mesh.build_adjacencies()` |
| `invalidate_adjacencies()` | `invalidate_adjacencies()` |
| `mesh._ensure_ccw_orientation()` | `mesh.ensure_ccw()` (run by the constructor) |
| `mesh.signed_area(ids)` | `signed_area(e)`, `signed_area()` |
| `mesh.boundary_edges()` | `boundary_edges()` |
| `mesh.boundary_node_indices()`, `unique(edge2vert(boundary_edges()))` | `boundary_node_indices()` |
| `mesh.ccw_edges_around_vert(v)` | `ccw_edges_around_vert(v)` |
| `mesh._peel()`, `peel_layers()` | `peel_layers()` (seed filters not ported) |
| `mesh.layers["OE"/"IE"/"OV"/"IV"/"bEdgeIDs"][li]` | `mesh.layers.OE[li]` etc. |
| `mesh.get_layer(li)` | `mesh.layers.*[li]` |
| `mesh.elements_in_layer(li)` | `elements_in_layer(li)` |
| `mesh.submesh(ids, compute_layers=, compute_adjacencies=)` | `submesh(ids, opts)` |
| `chilmesh.layer_paths.paths_on_outer_vertices(mesh, li)`, `mesh.paths_on_outer_vertices(li)` | `paths_on_outer_vertices(mesh, li)` |
| `chilmesh.quad_from_tri_pair(points, a, b)` | `quad_from_tri_pair(points, a, b)` |
| `quadmesh.tri2quad._layer_priority(domain, n)` | `layer_priority(mesh, n)` |
| `quadmesh.remove_unused.remove_unused_vertices(mesh)` | `remove_unused(mesh, opts)` |
| `chilmesh.element_quality(pts, conn, metric="skew")` | `element_skew(points, elems)` (`quality.hpp`) |
| `quality_report.count_concave_quads` | `count_concave_quads` |
| `quality_report.compute_quality_stats` | `compute_quality_stats` (`QualityStats`) |
| `mesh.copy()` | copy construction (`Mesh m2 = m;`) |
| `mesh.direct_smoother()` (kinf penalty, direct solve), `post_process.fem_smoother` | `direct_smoother(mesh)`, `fem_smoother(mesh, n)` (`post_process.hpp`, Eigen SparseLU) |

## Differences from Python, on purpose

- Triangles end in `-1` (ADR 0001). `elem2edge` slot 3 of a triangle row is `-1`;
  Python leaves `0` there for mixed meshes and has no slot 3 for pure triangle meshes.
  The oracle tests ignore that slot.
- `paths_on_outer_vertices`: Python collects layer edges from `elem2edge`
  including the padded edge `0` of mixed triangle rows; the port skips `-1`.
  The four ground-truth inputs are pure triangle meshes, so this is untested.
- Sets become sorted vectors (`get_vertex_edges`, `vert2elem`). Callers that
  iterate a Python set and break ties by iteration order must sort (ADR 0001).
- `remove_unused` keeps the boundary block; CHILmesh `submesh` drops
  `boundary_segments` (R-06: written back unchanged, no node remap).
- `write_fort14` writes the boundary block of the source file byte for byte
  (FR-004), including CRLF endings in Lake_Michigan_mesh.14. Python rewrites it
  as bare counts. A mesh with no source block gets Python's canonical form.
- Retired rows in `_tri_removal.py` are all-zero rows; the port has no such
  row form. Porters must delete rows (and renumber) or use another marker.
- `Mesh` throws `quadmesh::Error` on an out-of-range vertex id; reader errors
  are `InputError` (missing file) and `ParseError` (malformed).
- `Layers` carries no seed-boundary filters (`seed_boundary_kinds`,
  `seed_ibtypes`); QuADMESH never passes them.

## Test data

- Oracle: `CHILMESH_BACKEND=python .venv/bin/python .scratch/cpp-port/ground_truth/ref_tables.py`.
- Paths: compile definition `QUADMESH_GT_DIR_DEFAULT` (CMake cache `QUADMESH_GT_DIR`),
  overridden by the `QUADMESH_GT_DIR` environment variable. Missing data skips.
- `ctest` runs `quadmesh_tests` and then `fort14_python_roundtrip`
  (`tests/fort14_roundtrip_check.py`, needs `QUADMESH_PYTHON`, default repo `.venv`).
- `json.hpp` / `src/util/json.cpp` is the shared minimal JSON reader for the diff tool.

## Post-process tie site (SPEC-09)

`doublet_collapse.py:43` reproduces CPython set order exactly instead of
sorting (FR-020 needs quality within 1e-6, and ascending order missed it on
WNAT_Test and Lake_Michigan_mesh). `include/quadmesh/cpython_set.hpp`
models CPython 3.14 `set(ascending ids).copy()`; `tests/test_cpython_set.cpp`
checks it against `ground_truth/set_order.json` (`set_order_ref.py`).
No other post-process site depends on set order.
