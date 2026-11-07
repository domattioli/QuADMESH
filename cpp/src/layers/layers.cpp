// SPEC-03 layer peel (CHILmesh._peel), outer-vertex path walk
// (chilmesh/layer_paths.py) and layer priority (tri2quad._layer_priority).
#include <algorithm>
#include <cmath>
#include <unordered_map>

#include "quadmesh/error.hpp"
#include "quadmesh/mesh.hpp"

namespace quadmesh {

namespace {
void sort_unique(std::vector<int>& v) {
    std::sort(v.begin(), v.end());
    v.erase(std::unique(v.begin(), v.end()), v.end());
}
}  // namespace

void Mesh::peel_layers() {
    if (!has_adjacencies()) build_adjacencies();
    layers = Layers{};
    const int ne = n_elems();
    const int nv = n_verts();
    const int nE = n_edges();

    // Working copies as masks: an edge2elem entry is active while its element
    // is not consumed; an edge2vert entry while its vertex is not consumed.
    std::vector<char> elem_dead(ne, 0), vert_dead(nv, 0), in_ov(nv, 0);
    auto active = [&](int e) { return e >= 0 && !elem_dead[e]; };

    const int max_layers = ne + 1;
    int iL = 0;
    while (true) {
        bool any_active = false;
        for (int id = 0; id < nE && !any_active; ++id) {
            any_active = active(edge2elem[id][0]) || active(edge2elem[id][1]);
        }
        if (!any_active) break;
        if (iL > max_layers) {
            throw Error("peel did not converge: exceeded max layer count");
        }
        // Step 1: this layer's boundary edges.
        std::vector<int> bedges;
        for (int id = 0; id < nE; ++id) {
            if (iL == 0) {
                if (edge2elem[id][1] == -1) bedges.push_back(id);
            } else {
                const int c = (active(edge2elem[id][0]) ? 1 : 0) + (active(edge2elem[id][1]) ? 1 : 0);
                if (c == 1) bedges.push_back(id);
            }
        }
        if (bedges.empty()) break;

        // Step 2: OV.
        std::vector<int> ov;
        for (int id : bedges) {
            for (int v : edge2vert[id]) {
                if (!vert_dead[v]) ov.push_back(v);
            }
        }
        sort_unique(ov);
        // Step 3: OE.
        std::vector<int> oe;
        for (int id : bedges) {
            for (int e : edge2elem[id]) {
                if (active(e)) oe.push_back(e);
            }
        }
        sort_unique(oe);
        // Step 4: consume OE.
        for (int e : oe) elem_dead[e] = 1;
        // Steps 5-6: IE = active elements on any edge touching an OV vertex.
        std::vector<int> ie;
        for (int v : ov) {
            for (int id : vert2edge[v]) {
                for (int e : edge2elem[id]) {
                    if (active(e)) ie.push_back(e);
                }
            }
        }
        sort_unique(ie);
        // Step 7: consume OV and IE.
        for (int v : ov) {
            vert_dead[v] = 1;
            in_ov[v] = 1;
        }
        for (int e : ie) elem_dead[e] = 1;
        // Step 8: IV = vertices of OE ∪ IE not in OV.
        std::vector<int> iv;
        for (const std::vector<int>* lst : {&oe, &ie}) {
            for (int e : *lst) {
                const Elem& r = elems[e];
                for (int k = 0; k < 4; ++k) {
                    if (r[k] >= 0 && !in_ov[r[k]]) iv.push_back(r[k]);
                }
            }
        }
        sort_unique(iv);
        for (int v : ov) in_ov[v] = 0;

        layers.OV.push_back(std::move(ov));
        layers.bEdgeIDs.push_back(std::move(bedges));
        layers.OE.push_back(std::move(oe));
        layers.IE.push_back(std::move(ie));
        layers.IV.push_back(std::move(iv));
        ++iL;
    }
    layers_built_ = true;
}

std::vector<int> layer_priority(const Mesh& mesh, int n) {
    const int nl = mesh.n_layers();
    std::vector<int> prio(n, 2 * nl + 1);
    for (int li = 0; li < nl; ++li) {
        const int rank = nl - 1 - li;
        const bool boundary = li == 0;  // _is_boundary_layer
        const int ie_off = boundary ? 1 : 0;
        const int oe_off = boundary ? 0 : 1;
        for (int e : mesh.layers.IE[li]) {
            if (e >= 0 && e < n) prio[e] = 2 * rank + ie_off;
        }
        for (int e : mesh.layers.OE[li]) {
            if (e >= 0 && e < n) prio[e] = 2 * rank + oe_off;
        }
    }
    return prio;
}

// ---- layer_paths.py -------------------------------------------------------

namespace {

struct Nbr {
    int v;
    int e;
};

struct Subgraph {
    std::vector<int> verts;                 // OV order (dict insertion order)
    std::unordered_map<int, int> slot;      // vertex -> index in verts
    std::vector<std::vector<Nbr>> adj;      // per slot
    std::unordered_map<int, int> edge_elem; // edge -> its single layer element
};

Subgraph build_subgraph(const Mesh& m, int li) {
    Subgraph g;
    const std::vector<int>& ov = m.layers.OV[li];
    if (ov.empty()) return g;
    std::vector<char> ov_mask(m.n_verts(), 0), lmask(m.n_elems(), 0);
    for (int v : ov) ov_mask[v] = 1;
    std::vector<int> lelems = m.layers.OE[li];
    lelems.insert(lelems.end(), m.layers.IE[li].begin(), m.layers.IE[li].end());
    for (int e : lelems) lmask[e] = 1;

    g.verts = ov;
    g.adj.assign(ov.size(), {});
    for (std::size_t i = 0; i < ov.size(); ++i) g.slot[ov[i]] = static_cast<int>(i);

    // Python pads mixed triangle rows of Elem2Edge with edge 0; the port has
    // -1 there and skips it (see PORTING_NOTES.md).
    std::vector<int> eids;
    for (int e : lelems) {
        for (int id : m.elem2edge[e]) {
            if (id >= 0) eids.push_back(id);
        }
    }
    sort_unique(eids);
    for (int id : eids) {
        const Edge& ev = m.edge2vert[id];
        if (!(ov_mask[ev[0]] && ov_mask[ev[1]])) continue;
        const Edge& ee = m.edge2elem[id];
        const bool in0 = ee[0] >= 0 && lmask[ee[0]];
        const bool in1 = ee[1] >= 0 && lmask[ee[1]];
        if ((in0 ? 1 : 0) + (in1 ? 1 : 0) != 1) continue;
        const int nb = in0 ? ee[0] : ee[1];
        g.adj[g.slot[ev[0]]].push_back({ev[1], id});
        g.adj[g.slot[ev[1]]].push_back({ev[0], id});
        g.edge_elem[id] = nb;
    }
    return g;
}

}  // namespace

std::vector<std::vector<int>> paths_on_outer_vertices(const Mesh& m, int li) {
    if (li < 0 || li >= m.n_layers()) throw Error("layer_idx out of range");
    Subgraph g = build_subgraph(m, li);
    std::vector<std::vector<int>> paths;
    if (g.edge_elem.empty()) return paths;
    std::vector<char> visited(m.n_edges(), 0);
    std::size_t n_visited = 0;
    const std::size_t n_edges = g.edge_elem.size();

    auto deg_rem = [&](int s) {
        int d = 0;
        for (const Nbr& nb : g.adj[s]) d += visited[nb.e] ? 0 : 1;
        return d;
    };
    const auto& P = m.points;

    while (n_visited < n_edges) {
        // _pick_seed
        int best_any = -1, best_j = -1, best_j_deg = -1;
        for (std::size_t s = 0; s < g.verts.size(); ++s) {
            const int d = deg_rem(static_cast<int>(s));
            if (d == 0) continue;
            if (best_any < 0) best_any = static_cast<int>(s);
            if (d > 2 && d > best_j_deg) {
                best_j = static_cast<int>(s);
                best_j_deg = d;
            }
        }
        const int seed_slot = best_j >= 0 ? best_j : best_any;
        if (seed_slot < 0) break;
        const int start = g.verts[seed_slot];

        // _walk
        std::vector<int> path{start};
        int prev_edge = -1, prev_v = -1, cur = start;
        while (true) {
            std::vector<Nbr> out;
            for (const Nbr& nb : g.adj[g.slot.at(cur)]) {
                if (!visited[nb.e]) out.push_back(nb);
            }
            if (out.empty()) break;
            Nbr pick = out[0];
            if (out.size() > 1 && prev_edge >= 0) {
                const int pe = g.edge_elem.at(prev_edge);
                std::vector<Nbr> same;
                for (const Nbr& nb : out) {
                    if (g.edge_elem.at(nb.e) == pe) same.push_back(nb);
                }
                const std::vector<Nbr>& cand = same.empty() ? out : same;
                pick = cand[0];
                if (cand.size() > 1) {
                    // Turning angle uses all three point columns, as numpy does.
                    double a[3], an2 = 0.0;
                    for (int k = 0; k < 3; ++k) {
                        a[k] = P[cur][k] - P[prev_v][k];
                        an2 += a[k] * a[k];
                    }
                    const double an = std::sqrt(an2);
                    if (an != 0.0) {
                        double best = 0.0;
                        for (std::size_t c = 0; c < cand.size(); ++c) {
                            double b[3], bn2 = 0.0, dot = 0.0;
                            for (int k = 0; k < 3; ++k) {
                                b[k] = P[cand[c].v][k] - P[cur][k];
                                bn2 += b[k] * b[k];
                                dot += a[k] * b[k];
                            }
                            const double bn = std::sqrt(bn2);
                            double t;
                            if (bn == 0.0) {
                                t = M_PI;
                            } else {
                                double ca = dot / (an * bn);
                                ca = std::min(1.0, std::max(-1.0, ca));
                                t = std::acos(ca);
                            }
                            if (c == 0 || t < best) {
                                best = t;
                                pick = cand[c];
                            }
                        }
                    }
                }
            }
            visited[pick.e] = 1;
            ++n_visited;
            path.push_back(pick.v);
            prev_v = cur;
            prev_edge = pick.e;
            cur = pick.v;
            if (cur == start) break;
        }
        if (path.size() <= 1) break;
        paths.push_back(std::move(path));
    }
    return paths;
}

}  // namespace quadmesh
