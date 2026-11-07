#pragma once
// Internal helpers shared by cpp/src/post/*.cpp.
#include <vector>

#include "quadmesh/mesh.hpp"

namespace quadmesh::post_detail {

// Post-process meshes carry adjacencies and never layers (FR-007).
inline MeshOptions adj_only() { return MeshOptions{true, false}; }

// CHILmesh(rows, points, grid_name=mesh.grid_name), keeping the source
// boundary block like remove_unused does (R-06).
inline Mesh rebuild(const Mesh& src, std::vector<Point> pts, std::vector<Elem> rows) {
    Mesh out(std::move(pts), std::move(rows), src.grid_name, adj_only());
    out.boundary_raw = src.boundary_raw;
    out.boundaries_present = src.boundaries_present;
    out.boundary_segments = src.boundary_segments;
    return out;
}

inline bool has_quad(const Mesh& m) {
    for (const Elem& r : m.elems)
        if (!is_tri(r)) return true;
    return false;
}

// Python boundary set as a mask over vertices.
inline std::vector<char> boundary_mask(const Mesh& m) {
    std::vector<char> b(m.points.size(), 0);
    for (int v : m.boundary_node_indices()) b[v] = 1;
    return b;
}

}  // namespace quadmesh::post_detail
