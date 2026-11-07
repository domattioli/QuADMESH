// T043: repair._fix_bowties. Reorders self-intersecting quads; no point is
// added, moved or deleted.
//
// Python adds scipy's ConvexHull ordering as a fourth candidate when all
// four points are hull vertices. The port builds that CCW hull order itself
// and starts it at the quad's first vertex; qhull's start vertex may differ,
// which can rotate the output row (same polygon, same vertices).
#include <algorithm>
#include <set>

#include "quadmesh/post_process.hpp"

namespace quadmesh {

namespace {
using P2 = std::array<double, 2>;

int ori(const P2& a, const P2& b, const P2& c) {
    const double v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
    return v > 1e-12 ? 1 : (v < -1e-12 ? -1 : 0);
}
bool seg_cross(const P2& p1, const P2& p2, const P2& p3, const P2& p4) {
    const int o1 = ori(p1, p2, p3), o2 = ori(p1, p2, p4), o3 = ori(p3, p4, p1), o4 = ori(p3, p4, p2);
    if (o1 == 0 || o2 == 0 || o3 == 0 || o4 == 0) return false;
    return o1 != o2 && o3 != o4;
}
std::array<P2, 4> xy(const std::vector<Point>& pts, const Elem& c) {
    std::array<P2, 4> p;
    for (int k = 0; k < 4; ++k) p[k] = {pts[c[k]][0], pts[c[k]][1]};
    return p;
}
double shoelace(const std::array<P2, 4>& p) {
    double s = 0.0;  // np.sum over 4 terms, sequential
    for (int k = 0; k < 4; ++k) s += p[k][0] * p[(k + 1) % 4][1] - p[(k + 1) % 4][0] * p[k][1];
    return 0.5 * s;
}
double cross(const P2& o, const P2& a, const P2& b) {
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
}
// CCW hull of 4 points as local indices when all 4 are strict hull vertices.
bool hull4(const std::array<P2, 4>& p, std::array<int, 4>& out) {
    std::array<int, 4> idx = {0, 1, 2, 3};
    std::sort(idx.begin(), idx.end(), [&](int a, int b) {
        return p[a][0] < p[b][0] || (p[a][0] == p[b][0] && p[a][1] < p[b][1]);
    });
    std::vector<int> h;  // Andrew's monotone chain
    for (int pass = 0; pass < 2; ++pass) {
        const std::size_t base = h.size();
        for (int k = 0; k < 4; ++k) {
            const int i = pass == 0 ? idx[k] : idx[3 - k];
            while (h.size() >= base + 2 && cross(p[h[h.size() - 2]], p[h.back()], p[i]) <= 0) h.pop_back();
            h.push_back(i);
        }
        h.pop_back();
    }
    if (h.size() != 4) return false;
    const auto it = std::find(h.begin(), h.end(), 0);
    std::rotate(h.begin(), it, h.end());
    std::copy(h.begin(), h.end(), out.begin());
    return true;
}
}  // namespace

int fix_bowties(std::vector<Elem>& conn, const std::vector<Point>& pts) {
    int n_fixed = 0;
    for (Elem& r : conn) {
        if (is_tri(r) || r[0] == r[3]) continue;
        if (std::set<int>(r.begin(), r.end()).size() < 4) continue;
        const auto p = xy(pts, r);
        if (!(seg_cross(p[0], p[1], p[2], p[3]) || seg_cross(p[1], p[2], p[3], p[0]))) continue;
        std::vector<Elem> cands = {{r[0], r[1], r[3], r[2]}, {r[0], r[2], r[1], r[3]}, {r[0], r[3], r[2], r[1]}};
        std::array<int, 4> h;
        if (hull4(p, h)) cands.push_back({r[h[0]], r[h[1]], r[h[2]], r[h[3]]});
        int best = -1;
        double best_sa = 0.0;
        for (int i = 0; i < static_cast<int>(cands.size()); ++i) {
            const auto q = xy(pts, cands[i]);
            const double sa = shoelace(q);
            if (sa <= 0) continue;
            if (seg_cross(q[0], q[1], q[2], q[3]) || seg_cross(q[1], q[2], q[3], q[0])) continue;
            if (best < 0 || sa > best_sa) {
                best = i;
                best_sa = sa;
            }
        }
        if (best >= 0) {
            r = cands[best];
            ++n_fixed;
        }
    }
    return n_fixed;
}

}  // namespace quadmesh
