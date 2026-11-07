// Shared geometry of the tri2quad port: tri2quad.py:47-93 (_segments_cross,
// _quad_quality, _quad_ok), 791-813 (_quad_is_degenerate) and
// _match_quadmesh_plus.py:330-360 (_quad_quality_pair). Sums run in index
// order, as numpy does for arrays under 8 entries.
#include <algorithm>
#include <cmath>

#include "quadmesh/tri2quad_detail.hpp"

namespace quadmesh::detail {

namespace {
constexpr double kRad2Deg = 180.0 / M_PI;  // np.degrees

inline double corner_angle_deg(const XY& a, const XY& b, double na, double nb) {
    double c = (a[0] * b[0] + a[1] * b[1]) / (na * nb);
    c = std::min(1.0, std::max(-1.0, c));
    return std::acos(c) * kRad2Deg;
}
}  // namespace

bool segments_cross(const XY& a, const XY& b, const XY& c, const XY& d) {
    auto cross = [](const XY& o, const XY& p, const XY& q) {
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0]);
    };
    const double d1 = cross(c, d, a), d2 = cross(c, d, b);
    const double d3 = cross(a, b, c), d4 = cross(a, b, d);
    return ((d1 > 0) != (d2 > 0)) && ((d3 > 0) != (d4 > 0));
}

double area2_roll(const XY* p, int n) {
    double s = 0.0;
    for (int i = 0; i < n; ++i) {
        const XY& a = p[i];
        const XY& b = p[(i + 1) % n];
        s += a[0] * b[1] - b[0] * a[1];
    }
    return s;
}

double quad_quality(const std::array<XY, 4>& p) {
    double worst = 0.0;
    for (int i = 0; i < 4; ++i) {
        const XY& o = p[i];
        const XY& pm = p[(i + 3) % 4];
        const XY& pp = p[(i + 1) % 4];
        const XY a{pm[0] - o[0], pm[1] - o[1]};
        const XY b{pp[0] - o[0], pp[1] - o[1]};
        const double na = std::hypot(a[0], a[1]), nb = std::hypot(b[0], b[1]);
        if (na < 1e-12 || nb < 1e-12) return 0.0;
        worst = std::max(worst, std::abs(corner_angle_deg(a, b, na, nb) - 90.0));
    }
    return std::max(0.0, 1.0 - worst / 90.0);
}

bool quad_ok(const std::array<XY, 4>& p) {
    if (segments_cross(p[0], p[1], p[2], p[3])) return false;
    if (segments_cross(p[1], p[2], p[3], p[0])) return false;
    return area2_roll(p.data(), 4) > 1e-12;
}

bool quad_is_degenerate(const std::vector<Point>& pts, const Elem& quad, double max_angle_deg) {
    std::array<int, 4> v{quad[0], quad[1], quad[2], quad[3]};
    for (int i = 0; i < 4; ++i)
        for (int j = i + 1; j < 4; ++j)
            if (v[i] == v[j]) return false;
    std::array<XY, 4> p;
    for (int i = 0; i < 4; ++i) p[i] = xy_of(pts[v[i]]);
    for (int i = 0; i < 4; ++i) {
        const XY& o = p[i];
        const XY e1{p[(i + 3) % 4][0] - o[0], p[(i + 3) % 4][1] - o[1]};
        const XY e2{p[(i + 1) % 4][0] - o[0], p[(i + 1) % 4][1] - o[1]};
        const double n1 = std::hypot(e1[0], e1[1]), n2 = std::hypot(e2[0], e2[1]);
        if (n1 < 1e-12 || n2 < 1e-12) return true;
        if (corner_angle_deg(e1, e2, n1, n2) >= max_angle_deg) return true;
    }
    return false;
}

double quad_quality_pair(const std::vector<Tri3>& conn, const std::vector<Point>& pts, int ia, int ib) {
    // The shared pair's order (a Python set) only mirrors the quad, which
    // leaves the min-angle quality unchanged; no tie is possible here.
    const Tri3& ta = conn[ia];
    const Tri3& tb = conn[ib];
    auto in = [](const Tri3& t, int v) { return t[0] == v || t[1] == v || t[2] == v; };
    std::vector<int> sh;
    for (int v : ta)
        if (in(tb, v) && std::find(sh.begin(), sh.end(), v) == sh.end()) sh.push_back(v);
    std::vector<int> ua;
    for (int v : ta)
        if (std::find(ua.begin(), ua.end(), v) == ua.end()) ua.push_back(v);
    if (sh.size() != 2) return 0.0;
    int o1 = -1, o2 = -1;
    for (int v : ta)
        if (!in(tb, v)) { o1 = v; break; }
    for (int v : tb)
        if (!in(ta, v)) { o2 = v; break; }
    std::sort(sh.begin(), sh.end());
    const int verts[4] = {o1, sh[0], o2, sh[1]};
    for (int v : verts)
        if (v < 0 || v >= static_cast<int>(pts.size())) return 0.0;
    std::array<XY, 4> p;
    for (int i = 0; i < 4; ++i) p[i] = xy_of(pts[verts[i]]);
    return quad_quality(p);
}

}  // namespace quadmesh::detail
