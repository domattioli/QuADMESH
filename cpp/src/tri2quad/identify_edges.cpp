// T028: identify_edges.py (identify_edges_in_layer, _find_boundary_edge),
// tri2quad._sweep_pairs and fold_bridge_quads.
#include <algorithm>

#include "quadmesh/error.hpp"
#include "quadmesh/tri2quad.hpp"
#include "quadmesh/tri2quad_detail.hpp"

namespace quadmesh::detail {

namespace {

int find_boundary_edge(const std::vector<int>& b_edges, const std::vector<Edge>& b_e2v, int u, int v) {
    if (b_edges.empty()) return -1;
    for (std::size_t i = 0; i < b_edges.size(); ++i) {
        const Edge& e = b_e2v[i];
        if ((e[0] == u && e[1] == v) || (e[0] == v && e[1] == u)) return b_edges[i];
    }
    for (std::size_t i = 0; i < b_edges.size(); ++i) {
        const Edge& e = b_e2v[i];
        if (e[0] == u || e[1] == u) return b_edges[i];
    }
    return -1;
}

}  // namespace

LayerEdgeSelection identify_edges_in_layer(const Mesh& domain, int li) {
    LayerEdgeSelection sel;
    const Layers& L = domain.layers;
    if (li < 0 || li >= L.n_layers()) throw Error("identify_edges_in_layer: layer out of range");
    std::vector<int> elem_ids = L.OE[li];
    elem_ids.insert(elem_ids.end(), L.IE[li].begin(), L.IE[li].end());
    sel.elem_ids_global = elem_ids;
    if (elem_ids.empty()) return sel;

    const int nvt = domain.n_verts();
    std::vector<Elem> sub_conn;
    sub_conn.reserve(elem_ids.size());
    for (int e : elem_ids) {
        if (e < 0 || e >= domain.n_elems()) throw Error("identify_edges_in_layer: elem id out of range");
        sub_conn.push_back(domain.elems[e]);
    }
    sel.sub_mesh = Mesh(domain.points, sub_conn, "", MeshOptions{true, false});
    sel.has_sub_mesh = true;
    const Mesh& sm = sel.sub_mesh;
    const int nse = sm.n_edges();

    // Flagged (fold-seam) edges: both endpoints inner vertices, two elements.
    int max_vid = 0;
    for (const Edge& e : sm.edge2vert) max_vid = std::max(max_vid, std::max(e[0], e[1]) + 1);
    std::vector<char> iv_mask(max_vid, 0);
    for (int v : L.IV[li]) {
        if (v < 0 || v >= max_vid) throw Error("identify_edges_in_layer: IV vertex outside sub-mesh edges");
        iv_mask[v] = 1;
    }
    std::vector<char> flagged_mask(nse, 0);
    for (int id = 0; id < nse; ++id) {
        const Edge& ev = sm.edge2vert[id];
        const Edge& ee = sm.edge2elem[id];
        if (iv_mask[ev[0]] && iv_mask[ev[1]] && ee[0] >= 0 && ee[1] >= 0) {
            flagged_mask[id] = 1;
            sel.flagged_edge_ids.push_back(id);
            sel.flagged_vert_pairs.push_back({std::min(ev[0], ev[1]), std::max(ev[0], ev[1])});
        }
    }

    const std::vector<std::vector<int>> paths = paths_on_outer_vertices(domain, li);

    std::vector<int> vert_layer_count(nvt, 0);
    for (const Elem& r : sub_conn)
        for (int k = 0; k < n_corners(r); ++k)
            if (r[k] >= 0) ++vert_layer_count.at(r[k]);

    for (const auto& path : paths) {
        std::vector<int> verts = path;
        if (verts.size() <= 1) {
            sel.paths.push_back(verts);
            continue;
        }
        if (verts.front() == verts.back()) verts.pop_back();
        int corner = -1;
        for (std::size_t i = 0; i < verts.size(); ++i) {
            if (vert_layer_count.at(verts[i]) == 1) {
                corner = static_cast<int>(i);
                break;
            }
        }
        if (corner >= 0) {
            std::vector<int> rot(verts.begin() + corner + 1, verts.end());
            rot.insert(rot.end(), verts.begin(), verts.begin() + corner + 1);
            verts.swap(rot);
        }
        sel.paths.push_back(verts);
    }

    std::vector<char> ov_mask(nvt, 0);
    for (int v : L.OV[li]) ov_mask.at(v) = 1;
    std::vector<int> b_edges;
    std::vector<Edge> b_e2v;
    for (int id : sm.boundary_edges()) {
        const Edge& ev = sm.edge2vert[id];
        if (ov_mask[ev[0]] && ov_mask[ev[1]]) {
            b_edges.push_back(id);
            b_e2v.push_back(ev);
        }
    }

    std::vector<char> edge_used(nse, 0), elem_used(sm.n_elems(), 0), b_edge_bool(nse, 0);
    for (int id : b_edges) b_edge_bool[id] = 1;

    for (const auto& path : sel.paths) {
        if (path.size() < 2) continue;
        std::vector<int> wrap;
        wrap.push_back(path.back());
        wrap.insert(wrap.end(), path.begin(), path.end());
        wrap.push_back(path.front());
        int up_edge = find_boundary_edge(b_edges, b_e2v, wrap[0], wrap[1]);
        for (std::size_t k = 1; k + 1 < wrap.size(); ++k) {
            const int cur_v = wrap[k];
            const int nxt_v = wrap[k + 1];
            const std::vector<int> ccw = sm.ccw_edges_around_vert(cur_v);
            if (ccw.empty()) continue;
            const int down_edge = find_boundary_edge(b_edges, b_e2v, cur_v, nxt_v);
            if (up_edge < 0 || down_edge < 0) {
                up_edge = down_edge;
                continue;
            }
            auto iu_it = std::find(ccw.begin(), ccw.end(), up_edge);
            if (iu_it == ccw.end() || std::find(ccw.begin(), ccw.end(), down_edge) == ccw.end()) {
                up_edge = down_edge;
                continue;
            }
            std::vector<int> ordered(iu_it, ccw.end());
            ordered.insert(ordered.end(), ccw.begin(), iu_it);
            auto idx_of = [&](int e) {
                return static_cast<int>(std::find(ordered.begin(), ordered.end(), e) - ordered.begin());
            };
            int idown = idx_of(down_edge);
            if (idown <= 1) {
                up_edge = down_edge;
                continue;
            }
            if (idown == 2) {
                std::reverse(ordered.begin() + 1, ordered.end());
                idown = idx_of(down_edge);
            }
            for (int i = 1; i < idown; ++i) {
                const int eid = ordered[i];
                if (edge_used[eid] || b_edge_bool[eid]) continue;
                if (flagged_mask[eid]) continue;
                const Edge& pair = sm.edge2elem[eid];
                if (pair[0] < 0 || pair[1] < 0) continue;
                if (elem_used[pair[0]] || elem_used[pair[1]]) continue;
                edge_used[eid] = 1;
                elem_used[pair[0]] = 1;
                elem_used[pair[1]] = 1;
                sel.removed_edge_ids.push_back(eid);
            }
            up_edge = down_edge;
        }
    }

    sel.boundary_edge_ids = b_edges;
    for (const Edge& e : b_e2v) {
        sel.boundary_vert_ids_global.push_back(e[0]);
        sel.boundary_vert_ids_global.push_back(e[1]);
    }
    std::sort(sel.boundary_vert_ids_global.begin(), sel.boundary_vert_ids_global.end());
    sel.boundary_vert_ids_global.erase(
        std::unique(sel.boundary_vert_ids_global.begin(), sel.boundary_vert_ids_global.end()),
        sel.boundary_vert_ids_global.end());
    return sel;
}

std::pair<std::vector<IPair>, std::vector<IPair>> sweep_pairs(const Mesh& domain) {
    std::vector<IPair> pairs, flagged;
    PairSet fseen;
    for (int li = domain.n_layers() - 1; li >= 0; --li) {
        LayerEdgeSelection sel = identify_edges_in_layer(domain, li);
        if (!sel.has_sub_mesh) continue;
        for (const IPair& p : sel.flagged_vert_pairs)
            if (fseen.insert(pair_key(p[0], p[1])).second) flagged.push_back(p);
        const auto& glob = sel.elem_ids_global;
        for (int eid : sel.removed_edge_ids) {
            const Edge& row = sel.sub_mesh.edge2elem[eid];
            if (row[0] < 0 || row[1] < 0) continue;
            pairs.push_back({glob[row[0]], glob[row[1]]});
        }
    }
    return {pairs, flagged};
}

}  // namespace quadmesh::detail

namespace quadmesh {

std::vector<int> fold_bridge_quads(const std::vector<Elem>& quads,
                                   const std::vector<std::array<int, 2>>& flagged_edges) {
    detail::PairSet f;
    for (const auto& p : flagged_edges) f.insert(detail::pair_key(p[0], p[1]));
    std::vector<int> out;
    for (int i = 0; i < static_cast<int>(quads.size()); ++i) {
        const Elem& q = quads[i];
        if (is_tri(q)) continue;
        if (f.count(detail::pair_key(q[0], q[2])) || f.count(detail::pair_key(q[1], q[3]))) out.push_back(i);
    }
    return out;
}

std::vector<std::array<int, 2>> flagged_edges_of(const Mesh& mesh) {
    auto fl = detail::sweep_pairs(mesh).second;
    std::sort(fl.begin(), fl.end());
    return fl;
}

}  // namespace quadmesh
