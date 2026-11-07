// SPEC-01 mesh queries and pure operations (CHILmesh.py boundary_edges,
// ccw_edges_around_vert, submesh; mesh_topology.quad_from_tri_pair;
// quadmesh remove_unused.py).
#include <algorithm>
#include <cmath>
#include <numeric>

#include "quadmesh/error.hpp"
#include "quadmesh/mesh.hpp"

namespace quadmesh {

namespace {
void require_adj(const Mesh& m, const char* what) {
    if (!m.has_adjacencies()) {
        throw Error(std::string(what) + ": adjacencies not built");
    }
}
}  // namespace

std::vector<int> Mesh::boundary_edges() const {
    require_adj(*this, "boundary_edges");
    std::vector<int> out;
    for (int id = 0; id < n_edges(); ++id) {
        if (edge2elem[id][1] == -1) out.push_back(id);
    }
    return out;
}

std::vector<int> Mesh::boundary_node_indices() const {
    std::vector<int> out;
    for (int id : boundary_edges()) {
        out.push_back(edge2vert[id][0]);
        out.push_back(edge2vert[id][1]);
    }
    std::sort(out.begin(), out.end());
    out.erase(std::unique(out.begin(), out.end()), out.end());
    return out;
}

const std::vector<int>& Mesh::get_vertex_edges(int v) const {
    require_adj(*this, "get_vertex_edges");
    if (v < 0 || v >= n_verts()) throw Error("vertex out of range");
    return vert2edge[v];
}

const std::vector<int>& Mesh::get_vertex_elements(int v) const {
    require_adj(*this, "get_vertex_elements");
    if (v < 0 || v >= n_verts()) throw Error("vertex out of range");
    return vert2elem[v];
}

std::vector<int> Mesh::ccw_edges_around_vert(int v) const {
    const std::vector<int>& ids = get_vertex_edges(v);
    std::vector<std::pair<double, int>> keyed;
    keyed.reserve(ids.size());
    const Point& o = points[v];
    for (int id : ids) {
        const Edge& ev = edge2vert[id];
        const int other = ev[0] == v ? ev[1] : ev[0];
        const double dx = points[other][0] - o[0];
        const double dy = points[other][1] - o[1];
        keyed.emplace_back(std::atan2(dy, dx), id);
    }
    std::sort(keyed.begin(), keyed.end());  // angle, then edge id
    std::vector<int> out;
    out.reserve(keyed.size());
    for (const auto& kv : keyed) out.push_back(kv.second);
    return out;
}

std::vector<int> Mesh::elements_in_layer(int li) const {
    if (li < 0 || li >= n_layers()) throw Error("layer index out of range");
    std::vector<int> out = layers.OE[li];
    out.insert(out.end(), layers.IE[li].begin(), layers.IE[li].end());
    std::sort(out.begin(), out.end());
    return out;
}

Mesh Mesh::submesh(const std::vector<int>& elem_ids, const MeshOptions& opts) const {
    if (elem_ids.empty()) throw Error("submesh requires at least one element id");
    std::vector<int> ue = elem_ids;
    std::sort(ue.begin(), ue.end());
    ue.erase(std::unique(ue.begin(), ue.end()), ue.end());
    if (ue.front() < 0 || ue.back() >= n_elems()) throw Error("submesh: elem_ids out of range");

    std::vector<int> remap(points.size(), -1);
    for (int e : ue) {
        const Elem& r = elems[e];
        for (int k = 0; k < n_corners(r); ++k) remap[r[k]] = 0;
    }
    std::vector<Point> sub_pts;
    for (int v = 0; v < n_verts(); ++v) {
        if (remap[v] == 0) {
            remap[v] = static_cast<int>(sub_pts.size());
            sub_pts.push_back(points[v]);
        }
    }
    std::vector<Elem> sub_conn;
    sub_conn.reserve(ue.size());
    for (int e : ue) {
        Elem r = elems[e];
        for (int k = 0; k < 4; ++k) {
            if (r[k] >= 0) r[k] = remap[r[k]];
        }
        sub_conn.push_back(r);
    }
    std::string name = grid_name.empty() ? std::string() : grid_name + "_submesh";
    return Mesh(std::move(sub_pts), std::move(sub_conn), std::move(name), opts);
}

Elem quad_from_tri_pair(const std::vector<Point>& points, const Elem& tri_a, const Elem& tri_b) {
    auto uniq = [](const Elem& t) {
        std::vector<int> v;
        for (int x : t) {
            if (x >= 0) v.push_back(x);
        }
        std::sort(v.begin(), v.end());
        v.erase(std::unique(v.begin(), v.end()), v.end());
        return v;
    };
    const std::vector<int> a = uniq(tri_a);
    const std::vector<int> b = uniq(tri_b);
    if (a.size() != 3) throw Error("tri_a must have exactly 3 unique valid vertices");
    if (b.size() != 3) throw Error("tri_b must have exactly 3 unique valid vertices");
    std::vector<int> shared;
    std::set_intersection(a.begin(), a.end(), b.begin(), b.end(), std::back_inserter(shared));
    if (shared.size() != 2) throw Error("triangles must share exactly 2 vertices");
    int apex_a = -1, apex_b = -1;
    for (int x : a) {
        if (x != shared[0] && x != shared[1]) apex_a = x;
    }
    for (int x : b) {
        if (x != shared[0] && x != shared[1]) apex_b = x;
    }
    const int s0 = shared[0], s1 = shared[1];
    // _polygon_signed_area: 0.5 * (dot(x, roll(y,-1)) - dot(roll(x,-1), y)).
    const int q[4] = {apex_a, s0, apex_b, s1};
    double d1 = 0.0, d2 = 0.0;
    for (int i = 0; i < 4; ++i) {
        const Point& p = points[q[i]];
        const Point& n = points[q[(i + 1) % 4]];
        d1 += p[0] * n[1];
        d2 += n[0] * p[1];
    }
    const double area = 0.5 * (d1 - d2);
    if (area < 0) return {apex_a, s1, apex_b, s0};
    return {apex_a, s0, apex_b, s1};
}

Mesh remove_unused(const Mesh& mesh, const MeshOptions& opts) {
    std::vector<char> used(mesh.points.size(), 0);
    std::size_t n_used = 0;
    for (const Elem& r : mesh.elems) {
        for (int k = 0; k < n_corners(r); ++k) {
            if (!used[r[k]]) {
                used[r[k]] = 1;
                ++n_used;
            }
        }
    }
    if (n_used == mesh.points.size() || mesh.elems.empty()) return mesh;
    std::vector<int> all(mesh.elems.size());
    std::iota(all.begin(), all.end(), 0);
    Mesh out = mesh.submesh(all, opts);
    out.grid_name = mesh.grid_name;
    // Port choice: keep the boundary block (R-06, no node remap). Python's
    // submesh drops boundary_segments here.
    out.boundary_raw = mesh.boundary_raw;
    out.boundaries_present = mesh.boundaries_present;
    out.boundary_segments = mesh.boundary_segments;
    return out;
}

}  // namespace quadmesh
