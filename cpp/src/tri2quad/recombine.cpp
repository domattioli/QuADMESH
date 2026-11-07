// T033: _recombine.py (edge_swap, vertex_duplication, edge_flip,
// walk_isolated_tri). Topology-only patches on WorkingMesh::tris.
#include <cmath>

#include "quadmesh/tri2quad_detail.hpp"

namespace quadmesh::detail {

namespace {

std::pair<int, int> tris_sharing_edge(const WorkingMesh& work, int va, int vb) {
    if (!work.tris) return {-1, -1};
    std::vector<int> hits;
    for (int i = 0; i < static_cast<int>(work.tris->size()); ++i) {
        const auto& t = (*work.tris)[i];
        if (!t) continue;
        const bool ha = (*t)[0] == va || (*t)[1] == va || (*t)[2] == va;
        const bool hb = (*t)[0] == vb || (*t)[1] == vb || (*t)[2] == vb;
        if (ha && hb) hits.push_back(i);
        if (hits.size() == 2) return {hits[0], hits[1]};
    }
    return {-1, -1};
}

int opposite_vert(const Tri3& t, int va, int vb) {
    for (int v : t)
        if (v != va && v != vb) return v;
    return -1;
}

double ccw_area(const std::vector<Point>& pts, int a, int b, int c) {
    const Point &p = pts[a], &q = pts[b], &r = pts[c];
    return 0.5 * ((q[0] - p[0]) * (r[1] - p[1]) - (r[0] - p[0]) * (q[1] - p[1]));
}

}  // namespace

bool edge_swap(WorkingMesh& work, int va, int vb, const std::vector<Point>& pts) {
    auto [i, j] = tris_sharing_edge(work, va, vb);
    if (i == -1) return false;
    const int vc = opposite_vert(*(*work.tris)[i], va, vb);
    const int vd = opposite_vert(*(*work.tris)[j], va, vb);
    if (vc == -1 || vd == -1) return false;
    if (ccw_area(pts, va, vc, vd) > 1e-14 && ccw_area(pts, vb, vd, vc) > 1e-14) {
        (*work.tris)[i] = Tri3{va, vc, vd};
        (*work.tris)[j] = Tri3{vb, vd, vc};
        return true;
    }
    if (ccw_area(pts, va, vd, vc) > 1e-14 && ccw_area(pts, vb, vc, vd) > 1e-14) {
        (*work.tris)[i] = Tri3{va, vd, vc};
        (*work.tris)[j] = Tri3{vb, vc, vd};
        return true;
    }
    return false;
}

std::pair<bool, int> vertex_duplication(WorkingMesh& work, int v, const std::vector<Point>& pts) {
    std::vector<int> incident;
    for (int i = 0; i < static_cast<int>(work.tris->size()); ++i) {
        const auto& t = (*work.tris)[i];
        if (t && ((*t)[0] == v || (*t)[1] == v || (*t)[2] == v)) incident.push_back(i);
    }
    if (incident.size() < 2) return {false, -1};
    const int new_idx = static_cast<int>(pts.size());
    std::vector<Point> np = pts;
    np.push_back(pts[v]);
    Tri3 t = *(*work.tris)[incident[1]];
    for (int& x : t)
        if (x == v) x = new_idx;
    (*work.tris)[incident[1]] = t;
    work.points = std::move(np);
    return {true, new_idx};
}

bool edge_flip(WorkingMesh& work, int elem_idx, const std::vector<Point>& pts) {
    if (!(*work.tris)[elem_idx]) return false;
    const Tri3 t = *(*work.tris)[elem_idx];
    const IPair edges[3] = {{t[0], t[1]}, {t[1], t[2]}, {t[2], t[0]}};
    double best_len = -1.0;
    std::optional<IPair> best;
    for (const IPair& e : edges) {
        auto [i, j] = tris_sharing_edge(work, e[0], e[1]);
        if (i == -1 || j == -1) continue;
        double s = 0.0;
        for (int k = 0; k < 3; ++k) {
            const double d = pts[e[0]][k] - pts[e[1]][k];
            s += d * d;
        }
        const double len = std::sqrt(s);
        if (len > best_len) {
            best_len = len;
            best = e;
        }
    }
    if (!best) return false;
    return edge_swap(work, (*best)[0], (*best)[1], pts);
}

bool walk_isolated_tri(WorkingMesh& work, int isolated_idx, const std::vector<Point>& pts, int max_hops) {
    const int current = isolated_idx;
    for (int h = 0; h < max_hops; ++h) {
        if (!(*work.tris)[current]) return false;
        const Tri3 t = *(*work.tris)[current];
        const IPair edges[3] = {{t[0], t[1]}, {t[1], t[2]}, {t[2], t[0]}};
        for (const IPair& e : edges) {
            auto [i, j] = tris_sharing_edge(work, e[0], e[1]);
            if (i != -1 && j != -1) return true;
        }
        if (!edge_flip(work, current, pts)) return false;
    }
    return false;
}

}  // namespace quadmesh::detail
