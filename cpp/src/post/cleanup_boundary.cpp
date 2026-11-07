// T041: cleanup_boundary_quads.py (CleanupBoundaryQuads_v2.m).
//
// Angles use all three point components, as Python does (mesh.points rows
// carry depth in column 2). The shift mode moves the full 3-vector too.
#include <algorithm>
#include <cmath>
#include <numeric>

#include "common.hpp"
#include "quadmesh/post_process.hpp"

namespace quadmesh {

using post_detail::adj_only;
using post_detail::has_quad;
using post_detail::rebuild;

namespace {

constexpr double kAngleThresholdDeg = 134.0;
constexpr double kPi = 3.14159265358979323846;

using P2 = std::array<double, 2>;

double cr(const P2& o, const P2& p, const P2& q) {
    return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0]);
}
bool seg_cross(const P2& a, const P2& b, const P2& c, const P2& d) {
    return ((cr(c, d, a) > 0) != (cr(c, d, b) > 0)) && ((cr(a, b, c) > 0) != (cr(a, b, d) > 0));
}
bool is_bowtie(const std::array<P2, 4>& p) {
    return seg_cross(p[0], p[1], p[2], p[3]) || seg_cross(p[1], p[2], p[3], p[0]);
}

double angle_deg(const Point& c, const Point& a, const Point& b) {
    const double va[3] = {a[0] - c[0], a[1] - c[1], a[2] - c[2]};
    const double vb[3] = {b[0] - c[0], b[1] - c[1], b[2] - c[2]};
    const double na = std::sqrt(va[0] * va[0] + va[1] * va[1] + va[2] * va[2]);
    const double nb = std::sqrt(vb[0] * vb[0] + vb[1] * vb[1] + vb[2] * vb[2]);
    if (na == 0 || nb == 0) return 0.0;
    double cosv = (va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2]) / (na * nb);
    cosv = std::max(-1.0, std::min(1.0, cosv));
    return std::acos(cosv) * (180.0 / kPi);
}

Point lerp(const Point& c, const Point& o, double t) {
    return {c[0] + t * (o[0] - c[0]), c[1] + t * (o[1] - c[1]), c[2] + t * (o[2] - c[2])};
}

Point shift_to_target_angle(const Point& c, const Point& a, const Point& b, const Point& opp,
                            double target = 90.0) {
    double lo = 0.0, hi = 1.0;
    for (int i = 0; i < 24; ++i) {
        const double t = 0.5 * (lo + hi);
        if (angle_deg(lerp(c, opp, t), a, b) > target) lo = t;
        else hi = t;
    }
    return lerp(c, opp, 0.5 * (lo + hi));
}

struct Bad {
    int elem, corner, opposing, ci;
    Elem verts;
};

// _scan_bad_quads, ascending element ids.
std::vector<Bad> scan_bad_quads(const Mesh& mesh) {
    std::vector<char> bdy_edge(mesh.n_edges(), 0);
    for (int e : mesh.boundary_edges()) bdy_edge[e] = 1;
    std::vector<char> consumed(mesh.n_elems(), 0);
    std::vector<Bad> out;
    for (int e = 0; e < mesh.n_elems(); ++e) {
        const Elem& v = mesh.elems[e];
        if (is_tri(v)) continue;
        const Elem& edges = mesh.elem2edge[e];
        std::vector<int> on;
        for (int i = 0; i < 4; ++i)
            if (edges[i] >= 0 && bdy_edge[edges[i]]) on.push_back(i);
        if (on.size() < 2) continue;
        int a0 = -1, a1 = -1;
        for (std::size_t i = 0; i + 1 < on.size(); ++i) {
            if ((on[i] + 1) % 4 == on[i + 1]) {
                a0 = on[i];
                a1 = on[i + 1];
                break;
            }
        }
        if (a0 < 0 && on.front() == 0 && on.back() == 3) {
            a0 = 3;
            a1 = 0;
        }
        if (a0 < 0) continue;
        const int ci = a1;
        const int corner = v[ci];
        const Point& pp = mesh.points[v[(ci + 3) % 4]];
        const Point& pn = mesh.points[v[(ci + 1) % 4]];
        if (angle_deg(mesh.points[corner], pp, pn) <= kAngleThresholdDeg) continue;
        if (consumed[e]) continue;
        std::vector<int> nbrs;
        for (int k = 0; k < 4; ++k)
            for (int x : mesh.get_vertex_elements(v[k])) nbrs.push_back(x);
        bool hit = false;
        for (int x : nbrs) hit = hit || consumed[x];
        if (hit) continue;
        for (int x : nbrs) consumed[x] = 1;
        out.push_back({e, corner, v[(ci + 2) % 4], ci, v});
    }
    return out;
}

// _protected_mask: vertices within 1e-9*span of a protected point (nearest).
std::vector<char> protected_mask(const Mesh& mesh, const std::vector<P2>* prot) {
    std::vector<char> mask(mesh.points.size(), 0);
    if (!prot || prot->empty() || mesh.points.empty()) return mask;
    double lo[2] = {mesh.points[0][0], mesh.points[0][1]}, hi[2] = {lo[0], lo[1]};
    for (const Point& p : mesh.points)
        for (int d = 0; d < 2; ++d) {
            lo[d] = std::min(lo[d], p[d]);
            hi[d] = std::max(hi[d], p[d]);
        }
    const double span = std::hypot(hi[0] - lo[0], hi[1] - lo[1]);
    const double tol = 1e-9 * span + 1e-300;
    std::vector<int> order(mesh.points.size());
    std::iota(order.begin(), order.end(), 0);
    std::sort(order.begin(), order.end(),
              [&](int a, int b) { return mesh.points[a][0] < mesh.points[b][0]; });
    for (const P2& q : *prot) {
        auto it = std::lower_bound(order.begin(), order.end(), q[0] - tol,
                                   [&](int i, double x) { return mesh.points[i][0] < x; });
        int best = -1;
        double bd = tol;
        for (; it != order.end() && mesh.points[*it][0] <= q[0] + tol; ++it) {
            const double d = std::hypot(mesh.points[*it][0] - q[0], mesh.points[*it][1] - q[1]);
            if (d <= bd) {
                if (best < 0 || d < bd || *it < best) best = *it;
                bd = d;
            }
        }
        if (best >= 0) mask[best] = 1;
    }
    return mask;
}

}  // namespace

std::vector<P2> boundary_points(const Mesh& mesh) {
    std::vector<P2> out;
    for (int v : mesh.boundary_node_indices()) out.push_back({mesh.points[v][0], mesh.points[v][1]});
    return out;
}

Mesh cleanup_boundary_quads(const Mesh& mesh, bool can_remove_edges,
                            const std::vector<P2>* protected_points) {
    if (!has_quad(mesh)) return mesh;
    const std::vector<Bad> bad = scan_bad_quads(mesh);
    if (bad.empty()) return mesh;
    std::vector<Point> pts = mesh.points;
    std::vector<Elem> rows = mesh.elems;
    const std::vector<char> pinned = protected_mask(mesh, protected_points);

    if (can_remove_edges) {
        std::vector<char> deleted(rows.size(), 0);
        for (const Bad& b : bad) {
            const int s1 = b.verts[(b.ci + 3) % 4];
            const int s2 = b.verts[(b.ci + 1) % 4];
            if (pinned[s1] || pinned[s2]) continue;
            bool ok = true;
            for (std::size_t r = 0; r < rows.size() && ok; ++r) {
                if (deleted[r] || static_cast<int>(r) == b.elem) continue;
                const Elem& row = rows[r];
                bool touches = false;
                for (int k = 0; k < n_corners(row); ++k) touches = touches || row[k] == s1 || row[k] == s2;
                if (!touches) continue;
                std::vector<int> vs;  // dict.fromkeys order
                for (int k = 0; k < n_corners(row); ++k) {
                    int x = (row[k] == s1 || row[k] == s2) ? b.corner : row[k];
                    if (std::find(vs.begin(), vs.end(), x) == vs.end()) vs.push_back(x);
                }
                if (vs.size() < 4) { ok = false; break; }
                std::array<P2, 4> p4;
                for (int k = 0; k < 4; ++k) p4[k] = {pts[vs[k]][0], pts[vs[k]][1]};
                if (is_bowtie(p4)) ok = false;
            }
            if (!ok) continue;
            for (Elem& row : rows)
                for (int k = 0; k < n_corners(row); ++k)
                    if (row[k] == s1 || row[k] == s2) row[k] = b.corner;
            deleted[b.elem] = 1;
        }
        std::vector<Elem> keep;
        for (std::size_t r = 0; r < rows.size(); ++r)
            if (!deleted[r]) keep.push_back(rows[r]);
        return remove_unused(rebuild(mesh, std::move(pts), std::move(keep)), adj_only());
    }
    for (const Bad& b : bad) {
        if (pinned[b.corner]) continue;
        pts[b.corner] = shift_to_target_angle(mesh.points[b.corner], mesh.points[b.verts[(b.ci + 3) % 4]],
                                              mesh.points[b.verts[(b.ci + 1) % 4]],
                                              mesh.points[b.opposing]);
    }
    return rebuild(mesh, std::move(pts), std::move(rows));
}

}  // namespace quadmesh
