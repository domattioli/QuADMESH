// SPEC-01 Mesh construction, orientation and adjacency (CHILmesh.py
// _ensure_ccw_orientation, signed_area, _build_adjacencies).
#include "quadmesh/mesh.hpp"

#include <algorithm>
#include <cstdint>
#include <unordered_map>
#include <utility>

#include "quadmesh/error.hpp"

namespace quadmesh {

namespace {

inline std::uint64_t edge_key(int a, int b) {
    if (a > b) std::swap(a, b);
    return (static_cast<std::uint64_t>(static_cast<std::uint32_t>(a)) << 32) |
           static_cast<std::uint32_t>(b);
}

}  // namespace

Mesh::Mesh(std::vector<Point> pts, std::vector<Elem> conn, std::string name,
           const MeshOptions& opts)
    : grid_name(std::move(name)), points(std::move(pts)), elems(std::move(conn)) {
    const int nv = n_verts();
    for (const Elem& row : elems) {
        for (int k = 0; k < n_corners(row); ++k) {
            if (row[k] < 0 || row[k] >= nv) {
                throw Error("element references vertex " + std::to_string(row[k]) +
                            " outside [0, " + std::to_string(nv) + ")");
            }
        }
    }
    ensure_ccw();
    if (opts.compute_adjacencies || opts.compute_layers) build_adjacencies();
    if (opts.compute_layers) peel_layers();
}

double Mesh::signed_area(int e) const {
    const Elem& r = elems[e];
    if (is_tri(r)) {
        const Point& p0 = points[r[0]];
        const Point& p1 = points[r[1]];
        const Point& p2 = points[r[2]];
        return 0.5 * (p0[0] * (p1[1] - p2[1]) + p1[0] * (p2[1] - p0[1]) +
                      p2[0] * (p0[1] - p1[1]));
    }
    const Point& p0 = points[r[0]];
    const Point& p1 = points[r[1]];
    const Point& p2 = points[r[2]];
    const Point& p3 = points[r[3]];
    return 0.5 * (p0[0] * (p1[1] - p3[1]) + p1[0] * (p2[1] - p0[1]) +
                  p2[0] * (p3[1] - p1[1]) + p3[0] * (p0[1] - p2[1]));
}

std::vector<double> Mesh::signed_area() const {
    std::vector<double> out(elems.size());
    for (int e = 0; e < n_elems(); ++e) out[e] = signed_area(e);
    return out;
}

void Mesh::ensure_ccw() {
    for (int e = 0; e < n_elems(); ++e) {
        if (!(signed_area(e) < 0)) continue;
        Elem& r = elems[e];
        if (is_tri(r)) {
            std::swap(r[1], r[2]);  // [0, 2, 1]
        } else {
            std::swap(r[1], r[3]);  // [0, 3, 2, 1]
        }
    }
}

void Mesh::invalidate_adjacencies() {
    edge2vert.clear();
    edge2elem.clear();
    elem2edge.clear();
    vert2edge.clear();
    vert2elem.clear();
    adj_built_ = false;
}

void Mesh::build_adjacencies() {
    invalidate_adjacencies();
    const int ne = n_elems();
    const int nv = n_verts();
    std::unordered_map<std::uint64_t, int> emap;
    emap.reserve(static_cast<std::size_t>(ne) * 2);
    elem2edge.assign(ne, Elem{-1, -1, -1, -1});
    std::vector<int> last_elem;  // per edge, last element written

    for (int e = 0; e < ne; ++e) {
        const Elem& r = elems[e];
        const int nc = n_corners(r);
        for (int k = 0; k < nc; ++k) {
            const int a = r[k];
            const int b = r[(k + 1) % nc];
            if (a < 0 || b < 0 || a == b) continue;
            auto [it, inserted] = emap.emplace(edge_key(a, b), n_edges());
            const int id = it->second;
            if (inserted) {
                edge2vert.push_back({std::min(a, b), std::max(a, b)});
                edge2elem.push_back({e, -1});
                last_elem.push_back(e);
            } else if (last_elem[id] != e) {
                // Non-manifold edges keep the last write, as numpy does.
                edge2elem[id][1] = e;
                last_elem[id] = e;
            }
            elem2edge[e][k] = id;
        }
    }

    vert2edge.assign(nv, {});
    for (int id = 0; id < n_edges(); ++id) {
        vert2edge[edge2vert[id][0]].push_back(id);
        vert2edge[edge2vert[id][1]].push_back(id);
    }
    vert2elem.assign(nv, {});
    for (int e = 0; e < ne; ++e) {
        const Elem& r = elems[e];
        for (int k = 0; k < n_corners(r); ++k) {
            auto& lst = vert2elem[r[k]];
            if (lst.empty() || lst.back() != e) lst.push_back(e);
        }
    }
    // Repeated vertices in one row ([a,b,c,a]) can leave e twice, non-adjacent.
    for (auto& lst : vert2elem) lst.erase(std::unique(lst.begin(), lst.end()), lst.end());
    adj_built_ = true;
}

int Mesh::find_edge(int a, int b) const {
    if (a < 0 || b < 0 || a >= n_verts() || b >= n_verts()) return -1;
    for (int id : vert2edge[a]) {
        const Edge& ev = edge2vert[id];
        if ((ev[0] == a && ev[1] == b) || (ev[0] == b && ev[1] == a)) return id;
    }
    return -1;
}

}  // namespace quadmesh
