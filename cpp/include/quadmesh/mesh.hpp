#pragma once
// SPEC-01 Mesh: the CHILmesh subset QuADMESH needs (data-model.md).
//
// Semantics follow CHILmesh's pure-Python backend (CHILMESH_BACKEND=python):
// edge ids by first appearance, edge2elem lower element in column 0, layer
// peel identical to CHILmesh._peel. Triangles are stored as [v0,v1,v2,-1]
// (ADR 0001); is_tri() is the only triangle test.

#include <array>
#include <optional>
#include <string>
#include <vector>

namespace quadmesh {

using Point = std::array<double, 3>;  // x, y, depth
using Elem = std::array<int, 4>;      // triangle: [v0, v1, v2, -1]
using Edge = std::array<int, 2>;

// The single triangle test of the port. [a,b,c,a] is a (degenerate) quad.
inline bool is_tri(const Elem& row) { return row[3] == -1; }
inline int n_corners(const Elem& row) { return is_tri(row) ? 3 : 4; }
inline Elem make_tri(int a, int b, int c) { return {a, b, c, -1}; }

// One NOPE (open) or NBOU (flow) segment, parsed for information. The raw
// bytes in Mesh::boundary_raw are what the writer emits.
struct BoundarySegment {
    std::string kind;            // "open" or "flow"
    std::optional<int> ibtype;   // flow segments only, when given
    std::vector<int> nodes;      // 0-based
};

// CHILmesh.layers: one entry per layer, each list ascending.
struct Layers {
    std::vector<std::vector<int>> OE, IE, OV, IV, bEdgeIDs;
    int n_layers() const { return static_cast<int>(OE.size()); }
};

struct MeshOptions {
    bool compute_adjacencies = true;
    bool compute_layers = true;  // forces compute_adjacencies
};

class Mesh {
public:
    std::string grid_name;
    std::vector<Point> points;
    std::vector<Elem> elems;  // CHILmesh connectivity_list

    // Boundary block of the source .14: everything after the element rows,
    // byte for byte (FR-004). Empty for a mesh built in memory.
    std::string boundary_raw;
    bool boundaries_present = false;
    std::vector<BoundarySegment> boundary_segments;

    // Adjacency (valid when has_adjacencies()).
    std::vector<Edge> edge2vert;            // (min, max) per edge
    std::vector<Edge> edge2elem;            // [lower elem, other or -1]
    std::vector<Elem> elem2edge;            // triangle rows: slot 3 = -1
    std::vector<std::vector<int>> vert2edge;  // ascending
    std::vector<std::vector<int>> vert2elem;  // ascending

    Layers layers;

    Mesh() = default;
    // Same steps as CHILmesh(connectivity, points, ...): orient CCW, then
    // build adjacencies and peel as requested.
    Mesh(std::vector<Point> pts, std::vector<Elem> conn, std::string name = {},
         const MeshOptions& opts = {});

    int n_verts() const { return static_cast<int>(points.size()); }
    int n_elems() const { return static_cast<int>(elems.size()); }
    int n_edges() const { return static_cast<int>(edge2vert.size()); }
    int n_layers() const { return layers.n_layers(); }
    bool has_adjacencies() const { return adj_built_; }
    bool has_layers() const { return layers_built_; }

    // CHILmesh._ensure_ccw_orientation.
    void ensure_ccw();
    // CHILmesh._build_adjacencies / rebuild_adjacencies.
    void build_adjacencies();
    // CHILmesh._peel / peel_layers (all boundary edges seed layer 0).
    void peel_layers();
    void invalidate_adjacencies();

    // CHILmesh.signed_area (with the 1/2 factor).
    double signed_area(int elem) const;
    std::vector<double> signed_area() const;

    // CHILmesh.boundary_edges: edge ids with edge2elem[e][1] == -1, ascending.
    std::vector<int> boundary_edges() const;
    // CHILmesh.boundary_node_indices: sorted unique boundary vertices.
    std::vector<int> boundary_node_indices() const;
    // CHILmesh.get_vertex_edges / get_vertex_elements (sorted, not a set).
    const std::vector<int>& get_vertex_edges(int v) const;
    const std::vector<int>& get_vertex_elements(int v) const;
    // CHILmesh.ccw_edges_around_vert: by atan2 angle, ties by edge id.
    std::vector<int> ccw_edges_around_vert(int v) const;
    // EdgeMap.find_edge: edge id of (a, b) or -1.
    int find_edge(int a, int b) const;
    // CHILmesh.elements_in_layer: sorted OE ∪ IE.
    std::vector<int> elements_in_layer(int layer) const;
    // CHILmesh.get_layer pieces are layers.OE[li] etc.

    // CHILmesh.submesh: sorted unique elems, vertices renumbered compactly.
    Mesh submesh(const std::vector<int>& elem_ids, const MeshOptions& opts = {}) const;

private:
    bool adj_built_ = false;
    bool layers_built_ = false;
};

// chilmesh.quad_from_tri_pair: [apex_a, s0, apex_b, s1], CCW. Throws
// quadmesh::Error when the rows are not two triangles sharing one edge.
Elem quad_from_tri_pair(const std::vector<Point>& points, const Elem& tri_a, const Elem& tri_b);

// quadmesh.remove_unused.remove_unused_vertices: drops vertices no element
// uses (CHILmesh.submesh of every element). Returns the input unchanged
// (copied) when every vertex is used or there are no elements.
Mesh remove_unused(const Mesh& mesh, const MeshOptions& opts = {});

// CHILmesh.paths_on_outer_vertices (layer_paths.py).
std::vector<std::vector<int>> paths_on_outer_vertices(const Mesh& mesh, int layer_idx);

// quadmesh.tri2quad._layer_priority over n elements.
std::vector<int> layer_priority(const Mesh& mesh, int n);

}  // namespace quadmesh
