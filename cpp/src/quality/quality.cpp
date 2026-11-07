// SPEC-12 skew stats. Ports chilmesh/quality.py _triangle_quality and
// _quad_quality ("skew" branch) and quadmesh/quality_report.py.
#include "quadmesh/quality.hpp"

#include <algorithm>
#include <cmath>

namespace quadmesh {

namespace {

constexpr double kDeg = 180.0 / M_PI;  // np.degrees

inline double clip1(double x) { return std::min(1.0, std::max(-1.0, x)); }

double tri_skew(const Point& v0, const Point& v1, const Point& v2) {
    const double a[2] = {v1[0] - v0[0], v1[1] - v0[1]};
    const double b[2] = {v2[0] - v1[0], v2[1] - v1[1]};
    const double c[2] = {v0[0] - v2[0], v0[1] - v2[1]};
    const double la = std::sqrt(a[0] * a[0] + a[1] * a[1]);
    const double lb = std::sqrt(b[0] * b[0] + b[1] * b[1]);
    const double lc = std::sqrt(c[0] * c[0] + c[1] * c[1]);
    const double ang[3] = {
        std::acos(clip1((-c[0] * a[0] + -c[1] * a[1]) / (lc * la + 1e-300))) * kDeg,
        std::acos(clip1((-a[0] * b[0] + -a[1] * b[1]) / (la * lb + 1e-300))) * kDeg,
        std::acos(clip1((-b[0] * c[0] + -b[1] * c[1]) / (lb * lc + 1e-300))) * kDeg,
    };
    if (ang[0] + ang[1] + ang[2] <= 179.99) return 0.0;
    const double mx = std::max({ang[0], ang[1], ang[2]});
    const double mn = std::min({ang[0], ang[1], ang[2]});
    return 1.0 - std::max((mx - 60.0) / 120.0, (60.0 - mn) / 60.0);
}

double quad_skew(const Point* v[4]) {
    double ang[4];
    for (int j = 0; j < 4; ++j) {
        const Point& cur = *v[j];
        const Point& nxt = *v[(j + 1) % 4];
        const Point& prv = *v[(j + 3) % 4];
        const double e1[2] = {nxt[0] - cur[0], nxt[1] - cur[1]};
        const double e2[2] = {prv[0] - cur[0], prv[1] - cur[1]};
        const double n1 = std::sqrt(e1[0] * e1[0] + e1[1] * e1[1]) + 1e-12;
        const double n2 = std::sqrt(e2[0] * e2[0] + e2[1] * e2[1]) + 1e-12;
        const double dot = (e1[0] / n1) * (e2[0] / n2) + (e1[1] / n1) * (e2[1] / n2);
        ang[j] = std::acos(clip1(dot)) * kDeg;
    }
    if (ang[0] + ang[1] + ang[2] + ang[3] <= 359.99) return 0.0;
    const double mx = std::max({ang[0], ang[1], ang[2], ang[3]});
    const double mn = std::min({ang[0], ang[1], ang[2], ang[3]});
    return 1.0 - std::max((mx - 90.0) / 90.0, (90.0 - mn) / 90.0);
}

}  // namespace

std::vector<double> element_skew(const std::vector<Point>& points, const std::vector<Elem>& elems) {
    std::vector<double> q(elems.size(), 0.0);
    for (std::size_t i = 0; i < elems.size(); ++i) {
        const Elem& r = elems[i];
        if (is_tri(r)) {
            q[i] = tri_skew(points[r[0]], points[r[1]], points[r[2]]);
        } else {
            const Point* v[4] = {&points[r[0]], &points[r[1]], &points[r[2]], &points[r[3]]};
            q[i] = quad_skew(v);
        }
    }
    return q;
}

int count_concave_quads(const std::vector<Point>& points, const std::vector<Elem>& elems) {
    int n = 0;
    for (const Elem& r : elems) {
        if (is_tri(r)) continue;
        if (r[0] == r[1] || r[0] == r[2] || r[0] == r[3] || r[1] == r[2] || r[1] == r[3] ||
            r[2] == r[3]) {
            continue;  // fewer than 4 distinct vertices
        }
        double p[4][2];
        for (int k = 0; k < 4; ++k) {
            p[k][0] = points[r[k]][0];
            p[k][1] = points[r[k]][1];
        }
        double area2 = 0.0;
        for (int k = 0; k < 4; ++k) area2 += p[k][0] * p[(k + 1) % 4][1] - p[(k + 1) % 4][0] * p[k][1];
        if (area2 < 0) {
            std::swap(p[0], p[3]);
            std::swap(p[1], p[2]);
        }
        bool reflex = false;
        for (int k = 0; k < 4; ++k) {
            const double* prv = p[(k + 3) % 4];
            const double* cur = p[k];
            const double* nxt = p[(k + 1) % 4];
            const double ei[2] = {cur[0] - prv[0], cur[1] - prv[1]};
            const double eo[2] = {nxt[0] - cur[0], nxt[1] - cur[1]};
            const double cross = ei[0] * eo[1] - ei[1] * eo[0];
            const double norm = std::hypot(ei[0], ei[1]) * std::hypot(eo[0], eo[1]);
            if (cross < -1e-9 * norm) reflex = true;
        }
        if (reflex) ++n;
    }
    return n;
}

QualityStats compute_quality_stats(const Mesh& mesh) {
    QualityStats s;
    const std::vector<double> q = element_skew(mesh.points, mesh.elems);
    s.n_elems = mesh.n_elems();
    if (!q.empty()) {
        long double sum = 0.0L;
        s.min = q[0];
        s.max = q[0];
        for (double x : q) {
            sum += x;
            s.min = std::min(s.min, x);
            s.max = std::max(s.max, x);
            if (x < 0.3) ++s.n_bad;
        }
        s.mean = static_cast<double>(sum / q.size());
        long double ss = 0.0L;
        for (double x : q) ss += (x - s.mean) * (x - s.mean);
        s.std = std::sqrt(static_cast<double>(ss / q.size()));
        s.pct_bad = 100.0 * s.n_bad / s.n_elems;
    }
    s.n_concave = count_concave_quads(mesh.points, mesh.elems);
    return s;
}

}  // namespace quadmesh
