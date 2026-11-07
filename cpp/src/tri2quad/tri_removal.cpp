// T032: _tri_removal.py — WorkingMesh, SweepContext (the conforming
// per-layer sweep), the removeTrianglesFun ops for the non-sweep path, and
// handle_isolated_tris. Python sets of row or quad ids are std::set here
// (ascending); the order-sensitive sites write tie records (ADR 0001):
// _tri_removal.py:301 (edge_insertion), :426 (outer_tris_on_edge) and
// :453 (elems_on_edge).
#include <algorithm>
#include <cmath>
#include <limits>

#include "quadmesh/error.hpp"
#include "quadmesh/tri2quad_detail.hpp"

namespace quadmesh::detail {

namespace {

const std::set<int> kEmpty;

template <class M>
const std::set<int>& get_set(const M& m, int k) {
    auto it = m.find(k);
    return it == m.end() ? kEmpty : it->second;
}

std::vector<int> intersect(const std::set<int>& a, const std::set<int>& b) {
    std::vector<int> out;
    std::set_intersection(a.begin(), a.end(), b.begin(), b.end(), std::back_inserter(out));
    return out;
}

// _corner_sines: signed sine of each corner of a polygon.
std::vector<double> corner_sines(const std::vector<XY>& poly) {
    const int k = static_cast<int>(poly.size());
    std::vector<double> out(k);
    for (int i = 0; i < k; ++i) {
        const XY& o = poly[i];
        const XY& a = poly[(i + 1) % k];
        const XY& b = poly[(i + k - 1) % k];
        const double e1x = a[0] - o[0], e1y = a[1] - o[1];
        const double e2x = b[0] - o[0], e2y = b[1] - o[1];
        const double n = std::hypot(e1x, e1y) * std::hypot(e2x, e2y);
        out[i] = n > 0.0 ? (e1x * e2y - e1y * e2x) / n : -1.0;
    }
    return out;
}

// _signed_area: 0.5 * (x @ roll(y,-1) - roll(x,-1) @ y).
double signed_area_poly(const std::vector<XY>& p) {
    const int k = static_cast<int>(p.size());
    double d1 = 0.0, d2 = 0.0;
    for (int i = 0; i < k; ++i) d1 += p[i][0] * p[(i + 1) % k][1];
    for (int i = 0; i < k; ++i) d2 += p[(i + 1) % k][0] * p[i][1];
    return 0.5 * (d1 - d2);
}

double min_of(const std::vector<double>& v) {
    double m = std::numeric_limits<double>::infinity();
    for (double x : v) m = std::min(m, x);
    return m;
}

}  // namespace

// ---- WorkingMesh -------------------------------------------------------------

int WorkingMesh::add_quad(const Elem& q) {
    const int idx = static_cast<int>(quads.size());
    quads.push_back(q);
    for (int k = 0; k < 4; ++k) v2q[q[k]].insert(idx);
    return idx;
}

int WorkingMesh::add_point(Point xyz) {
    const int idx = n_pts;
    extra.push_back(xyz);
    ++n_pts;
    return idx;
}

const std::set<int>& WorkingMesh::quads_with(int v) const { return get_set(v2q, v); }

void WorkingMesh::replace_vertex_in_quad(int qi, int old_v, int new_v) {
    Elem& q = quads[qi];
    for (int k = 0; k < 4; ++k)
        if (q[k] == old_v) q[k] = new_v;
    auto it = v2q.find(old_v);
    if (it != v2q.end()) it->second.erase(qi);
    v2q[new_v].insert(qi);
}

void WorkingMesh::flush_points_to(std::vector<Point>& dst) {
    if (extra.empty()) return;
    dst.insert(dst.end(), extra.begin(), extra.end());
    extra.clear();
    base = n_pts;
}

// ---- SweepContext ------------------------------------------------------------

SweepContext::SweepContext(Mesh& dom, WorkingMesh& work, std::unordered_set<int>& consumed,
                           std::unordered_set<int>& refused, const PairSet& boundary_edges, TieLog* log)
    : dom_bdy(boundary_edges), d_(dom), w_(work), consumed_(consumed), refused_(refused), log_(log) {
    const int nl = d_.layers.n_layers();
    for (int li = 0; li < nl; ++li) {
        for (int e : d_.layers.OE[li]) elem_layer_.emplace(e, std::make_pair(li, 'O'));
        for (int e : d_.layers.IE[li]) elem_layer_.emplace(e, std::make_pair(li, 'I'));
    }
    for (int r = 0; r < d_.n_elems(); ++r) {
        const Elem& row = d_.elems[r];
        for (int k = 0; k < 3; ++k) v2t_[row[k]].insert(r);
    }
    for (auto k : dom_bdy) {
        dom_bdy_verts.insert(static_cast<int>(k >> 32));
        dom_bdy_verts.insert(static_cast<int>(k & 0xffffffffu));
    }
    layer_idx = nl - 1;
}

XY SweepContext::xy(int v) const {
    if (v < d_.n_verts()) return xy_of(d_.points[v]);
    return xy_of(w_.get_extra_point(v));
}

Tri3 SweepContext::tri_row(int r) const {
    const Elem& e = d_.elems[r];
    return {e[0], e[1], e[2]};
}

bool SweepContext::live(int r) const {
    if (consumed_.count(r) && !refused_.count(r)) return false;
    const Tri3 t = tri_row(r);
    return t[0] != t[1] && t[1] != t[2] && t[0] != t[2];
}

bool SweepContext::outer(int r) const {
    auto it = elem_layer_.find(r);
    return it != elem_layer_.end() && it->second.first < layer_idx && live(r);
}

std::vector<int> SweepContext::outer_tris_on_edge(int u, int v) const {
    std::vector<int> out;
    for (int r : intersect(get_set(v2t_, u), get_set(v2t_, v)))
        if (outer(r)) out.push_back(r);
    if (log_ && out.size() > 1) log_->record("SPEC-07", "_tri_removal.py:426", out, -1);
    return out;
}

bool SweepContext::is_ring_edge(int u, int v) const {
    if (layer_idx == 0) return dom_bdy.count(pair_key(u, v)) > 0;
    return !outer_tris_on_edge(u, v).empty();
}

bool SweepContext::is_ring_vert(int v) const {
    if (layer_idx == 0) return dom_bdy_verts.count(v) > 0;
    for (int r : get_set(v2t_, v))
        if (outer(r)) return true;
    return false;
}

std::vector<int> SweepContext::elem_verts(const El& el) const {
    if (el.first == 'q') {
        const Elem& q = w_.quads[el.second];
        return {q[0], q[1], q[2], q[3]};
    }
    const Tri3 t = tri_row(el.second);
    return {t[0], t[1], t[2]};
}

std::vector<SweepContext::El> SweepContext::elems_on_edge(int u, int v) const {
    std::vector<El> out;
    for (int qi : intersect(w_.quads_with(u), w_.quads_with(v))) {
        const Elem& q = w_.quads[qi];
        for (int j = 0; j < 4; ++j) {
            const int a = q[j], b = q[(j + 1) % 4];
            if ((a == u && b == v) || (a == v && b == u)) {
                out.push_back({'q', qi});
                break;
            }
        }
    }
    std::vector<int> tl;
    for (int r : intersect(get_set(v2t_, u), get_set(v2t_, v)))
        if (live(r)) {
            out.push_back({'t', r});
            tl.push_back(r);
        }
    if (log_ && tl.size() > 1) log_->record("SPEC-07", "_tri_removal.py:453", tl, -1);
    return out;
}

void SweepContext::set_row(int r, const Tri3& v) { d_.elems[r] = make_tri(v[0], v[1], v[2]); }

void SweepContext::retire_tri(int r) {
    const Tri3 t = tri_row(r);
    for (int v : t) {
        auto it = v2t_.find(v);
        if (it != v2t_.end()) it->second.erase(r);
    }
    d_.elems[r] = make_tri(0, 0, 0);
}

void SweepContext::replace_vertex(const El& el, int old_v, int new_v) {
    if (el.first == 'q') {
        w_.replace_vertex_in_quad(el.second, old_v, new_v);
        return;
    }
    Tri3 t = tri_row(el.second);
    for (int& x : t)
        if (x == old_v) x = new_v;
    set_row(el.second, t);
    auto it = v2t_.find(old_v);
    if (it != v2t_.end()) it->second.erase(el.second);
    v2t_[new_v].insert(el.second);
}

int SweepContext::split_outer(int r, int x, int y, int m) {
    const Tri3 row = tri_row(r);
    Tri3 keep = row, nw = row;
    for (int& v : keep)
        if (v == y) v = m;
    for (int& v : nw)
        if (v == x) v = m;
    set_row(r, keep);
    const int nid = d_.n_elems();
    d_.elems.push_back(make_tri(nw[0], nw[1], nw[2]));
    {
        auto it = v2t_.find(y);
        if (it != v2t_.end()) it->second.erase(r);
    }
    v2t_[m].insert(r);
    for (int v : nw) v2t_[v].insert(nid);
    auto it = elem_layer_.find(r);
    if (it != elem_layer_.end()) {
        const auto lay = it->second;
        elem_layer_[nid] = lay;
        const int li = lay.first;
        (lay.second == 'O' ? d_.layers.OE : d_.layers.IE)[li].push_back(nid);
        for (auto* key : {&d_.layers.IV, &d_.layers.OV}) {
            auto& arr = (*key)[li];
            const bool hx = std::find(arr.begin(), arr.end(), x) != arr.end();
            const bool hy = std::find(arr.begin(), arr.end(), y) != arr.end();
            if (hx && hy) arr.push_back(m);
        }
    }
    dirty = true;
    return nid;
}

void SweepContext::split_ring_edge(int x, int y, int m, std::optional<int> outer_row) {
    if (outer_row) {
        split_outer(*outer_row, x, y, m);
    } else {
        dom_bdy.erase(pair_key(x, y));
        dom_bdy.insert(pair_key(x, m));
        dom_bdy.insert(pair_key(m, y));
        dom_bdy_verts.insert(m);
    }
    dirty = true;
}

void SweepContext::sync() {
    if (!dirty) return;
    w_.flush_points_to(d_.points);
    const int n = d_.n_elems();
    for (int r : consumed_) {
        if (refused_.count(r) || r >= n) continue;
        const Elem& e = d_.elems[r];
        if (e[0] != 0 || e[1] != 0 || e[2] != 0) retire_tri(r);
    }
    d_.build_adjacencies();
    dirty = false;
}

std::pair<bool, std::optional<int>> SweepContext::ring_target(int x, int y) const {
    if (layer_idx == 0) return {dom_bdy.count(pair_key(x, y)) > 0, std::nullopt};
    const auto o = outer_tris_on_edge(x, y);
    if (o.size() != 1) return {false, std::nullopt};
    return {true, o[0]};
}

std::optional<XY> SweepContext::bisect_point(int a, int b, int c, std::optional<int> outer_row) const {
    const XY pa = xy(a), pb = xy(b), pc = xy(c);
    const XY mid{0.5 * (pa[0] + pb[0]), 0.5 * (pa[1] + pb[1])};
    if (!outer_row) return mid;
    std::vector<int> apex;
    for (int v : tri_row(*outer_row))
        if (v != a && v != b) apex.push_back(v);
    if (apex.size() != 1) return std::nullopt;
    const XY pz = xy(apex[0]);
    std::optional<std::pair<double, XY>> best;
    for (double t : {0.15, 0.25, 1.0 / 3.0, 0.5}) {
        const XY pm{mid[0] + t * (pz[0] - mid[0]), mid[1] + t * (pz[1] - mid[1])};
        const double worst = std::min(std::min(min_of(corner_sines({pa, pm, pb, pc})),
                                               min_of(corner_sines({pa, pz, pm}))),
                                      min_of(corner_sines({pm, pz, pb})));
        if (worst > MIN_SINE && (!best || worst > best->first)) best = std::make_pair(worst, pm);
    }
    if (!best) return std::nullopt;
    return best->second;
}

bool SweepContext::bisect(int r, int a, int b, int c, bool flat_ok) {
    auto [ok, outer_row] = ring_target(a, b);
    if (!ok) return false;
    std::optional<XY> pm = bisect_point(a, b, c, outer_row);
    if (!pm) {
        if (!flat_ok) return false;
        const XY pa = xy(a), pb = xy(b);
        pm = XY{0.5 * (pa[0] + pb[0]), 0.5 * (pa[1] + pb[1])};
    }
    const int m = w_.add_point({(*pm)[0], (*pm)[1], 0.0});
    w_.add_quad({a, m, b, c});
    retire_tri(r);
    split_ring_edge(a, b, m, outer_row);
    return true;
}

std::optional<std::pair<int, std::vector<SweepContext::El>>> SweepContext::fan(int r, int b, int start) const {
    El prev{'t', r};
    int cur = start;
    std::vector<El> elems;
    for (int it = 0; it < MAX_FAN; ++it) {
        if (is_ring_edge(b, cur)) {
            if (elems.empty()) return std::nullopt;
            return std::make_pair(cur, elems);
        }
        std::vector<El> nxt;
        for (const El& e : elems_on_edge(b, cur))
            if (e != prev) nxt.push_back(e);
        if (nxt.size() != 1) return std::nullopt;
        const El el = nxt[0];
        if (el == El{'t', r} || std::find(elems.begin(), elems.end(), el) != elems.end()) return std::nullopt;
        const std::vector<int> vs = elem_verts(el);
        if (std::count(vs.begin(), vs.end(), b) != 1) return std::nullopt;
        const int k = static_cast<int>(vs.size());
        const int i = static_cast<int>(std::find(vs.begin(), vs.end(), b) - vs.begin());
        const int n0 = vs[(i + k - 1) % k], n1 = vs[(i + 1) % k];
        if (cur != n0 && cur != n1) return std::nullopt;
        const int nx = n0 == cur ? n1 : n0;
        elems.push_back(el);
        prev = el;
        cur = nx;
    }
    return std::nullopt;
}

bool SweepContext::vertex_split(int r, int b, int p, int q) {
    struct Best {
        double worst;
        char side;
        int s;
        std::vector<El> elems;
        std::optional<int> outer_row;
        XY pn;
    };
    std::optional<Best> best;
    for (auto [side, start] : {std::make_pair('A', p), std::make_pair('B', q)}) {
        auto f = fan(r, b, start);
        if (!f) continue;
        const int s = f->first;
        const std::vector<El>& elems = f->second;
        auto [ok, outer_row] = ring_target(b, s);
        if (!ok) continue;
        const XY pb = xy(b), ps = xy(s);
        struct Old {
            std::vector<int> vs;
            double sign;
            std::vector<double> o_sin;
        };
        std::vector<Old> olds;
        for (const El& el : elems) {
            std::vector<int> vs = elem_verts(el);
            std::vector<XY> poly;
            for (int v : vs) poly.push_back(xy(v));
            const double sign = signed_area_poly(poly) >= 0.0 ? 1.0 : -1.0;
            std::vector<double> cs = corner_sines(poly);
            for (double& x : cs) x *= sign;
            olds.push_back({vs, sign, cs});
        }
        for (double t : {0.5, 1.0 / 3.0, 0.25, 1.0 / 6.0}) {
            const XY pn{pb[0] + t * (ps[0] - pb[0]), pb[1] + t * (ps[1] - pb[1])};
            double worst = std::numeric_limits<double>::infinity();
            bool valid = true;
            for (const Old& o : olds) {
                std::vector<XY> poly;
                for (int v : o.vs) poly.push_back(v == b ? pn : xy(v));
                if (o.sign * signed_area_poly(poly) <= 0.0) {
                    valid = false;
                    break;
                }
                std::vector<double> n_sin = corner_sines(poly);
                for (double& x : n_sin) x *= o.sign;
                bool any_convex = false;
                for (std::size_t k = 0; k < n_sin.size(); ++k) {
                    if (!(o.o_sin[k] > 0.0)) continue;
                    any_convex = true;
                    if (n_sin[k] <= std::min(MIN_SINE, o.o_sin[k])) valid = false;
                }
                if (!valid) break;
                if (any_convex) {
                    double mn = std::numeric_limits<double>::infinity();
                    for (std::size_t k = 0; k < n_sin.size(); ++k)
                        if (o.o_sin[k] > 0.0) mn = std::min(mn, n_sin[k]);
                    worst = std::min(worst, mn);
                }
            }
            if (!valid) continue;
            std::vector<XY> quad_pts = side == 'A' ? std::vector<XY>{pb, pn, xy(p), xy(q)}
                                                   : std::vector<XY>{pb, xy(p), xy(q), pn};
            if (signed_area_poly(quad_pts) <= 0.0) continue;
            const double qmin = min_of(corner_sines(quad_pts));
            if (qmin <= MIN_SINE) continue;
            worst = std::min(worst, qmin);
            if (!best || worst > best->worst) best = Best{worst, side, s, elems, outer_row, pn};
        }
    }
    if (!best) return false;
    const int n = w_.add_point({best->pn[0], best->pn[1], 0.0});
    for (const El& el : best->elems) replace_vertex(el, b, n);
    if (best->side == 'A') w_.add_quad({b, n, p, q});
    else w_.add_quad({b, p, q, n});
    retire_tri(r);
    split_ring_edge(b, best->s, n, best->outer_row);
    return true;
}

std::optional<bool> SweepContext::route(int r, bool refuse_boundary_merge) {
    if (!live(r)) return std::nullopt;
    Tri3 tri = tri_row(r);
    if (signed_area_poly({xy(tri[0]), xy(tri[1]), xy(tri[2])}) < 0.0) std::swap(tri[0], tri[2]);
    const int a = tri[0], b = tri[1], c = tri[2];
    const std::array<Tri3, 3> sides{Tri3{a, b, c}, Tri3{b, c, a}, Tri3{c, a, b}};
    std::vector<Tri3> ring;
    for (const Tri3& s : sides)
        if (is_ring_edge(s[0], s[1])) ring.push_back(s);
    if (layer_idx == 0 && ring.size() >= 2 && refuse_boundary_merge) return false;
    std::stable_sort(ring.begin(), ring.end(), [&](const Tri3& s1, const Tri3& s2) {
        const XY p0 = xy(s1[0]), p1 = xy(s1[1]), q0 = xy(s2[0]), q1 = xy(s2[1]);
        return -std::hypot(p0[0] - p1[0], p0[1] - p1[1]) < -std::hypot(q0[0] - q1[0], q0[1] - q1[1]);
    });
    for (const Tri3& s : ring)
        if (bisect(r, s[0], s[1], s[2])) return true;
    for (const Tri3& s : sides)
        if (is_ring_vert(s[0]) && vertex_split(r, s[0], s[1], s[2])) return true;
    for (const Tri3& s : ring)
        if (bisect(r, s[0], s[1], s[2], true)) return true;
    return std::nullopt;
}

// ---- non-sweep removeTrianglesFun ops -----------------------------------------

void edge_removal(Mesh& domain, WorkingMesh& work, int tri, int bdy_edge_idx) {
    const int eid = domain.elem2edge[tri][bdy_edge_idx];
    const int va = domain.edge2vert[eid][0], vb = domain.edge2vert[eid][1];
    Point mid;
    for (int k = 0; k < 3; ++k) mid[k] = 0.5 * (domain.points[va][k] + domain.points[vb][k]);
    domain.points[va] = mid;
    for (Elem& row : domain.elems)
        for (int k = 0; k < 4; ++k)
            if (row[k] == vb) row[k] = va;
    const std::set<int> qs = work.quads_with(vb);
    for (int qi : qs) work.replace_vertex_in_quad(qi, vb, va);
}

std::optional<int> edge_bisection(Mesh& domain, WorkingMesh& work, int tri, int bdy_edge_idx) {
    const int eid = domain.elem2edge[tri][bdy_edge_idx];
    int va = domain.edge2vert[eid][0], vb = domain.edge2vert[eid][1];
    Point mid;
    for (int k = 0; k < 3; ++k) mid[k] = 0.5 * (domain.points[va][k] + domain.points[vb][k]);
    const int np_id = work.add_point(mid);
    std::array<int, 3> conn{domain.elems[tri][0], domain.elems[tri][1], domain.elems[tri][2]};
    auto pos = [&](int v) {
        for (int k = 0; k < 3; ++k)
            if (conn[k] == v) return k;
        return -1;
    };
    bool found = false;
    for (int it = 0; it < 3; ++it) {
        const int ia = pos(va), ib = pos(vb);
        if (ia < 0 || ib < 0) return std::nullopt;
        if ((ia + 1) % 3 == ib) {
            found = true;
            break;
        }
        if ((ib + 1) % 3 == ia) {
            std::swap(va, vb);
            found = true;
            break;
        }
        std::rotate(conn.begin(), conn.begin() + 1, conn.end());
    }
    if (!found) return std::nullopt;
    int ia = pos(va);
    if (conn[(ia + 1) % 3] != vb) {
        std::swap(va, vb);
        ia = pos(va);
    }
    work.add_quad({conn[ia], np_id, conn[(ia + 1) % 3], conn[(ia + 2) % 3]});
    domain.elems[tri] = make_tri(0, 0, 0);
    return np_id;
}

std::optional<int> split_opposing_tri(Mesh& domain, int edge_id, int np_id, int consumed_tri) {
    const Edge pr = domain.edge2elem[edge_id];
    int opp = -1;
    for (int e : pr)
        if (e != consumed_tri && e >= 0) {
            opp = e;
            break;
        }
    if (opp < 0) return std::nullopt;
    const Elem oc = domain.elems[opp];
    const int va = domain.edge2vert[edge_id][0], vb = domain.edge2vert[edge_id][1];
    std::vector<int> apex;
    for (int k = 0; k < 3; ++k)
        if (oc[k] != va && oc[k] != vb) apex.push_back(oc[k]);
    if (apex.size() != 1) return std::nullopt;
    const int n = domain.n_verts();
    for (int v : {apex[0], va, vb, np_id})
        if (v >= n) return std::nullopt;
    auto ccw_tri = [&](Tri3 t) {
        const Point &p0 = domain.points[t[0]], &p1 = domain.points[t[1]], &p2 = domain.points[t[2]];
        const double area = 0.5 * ((p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1]));
        if (area < 0) std::swap(t[0], t[2]);
        return t;
    };
    const Tri3 t1 = ccw_tri({apex[0], va, np_id});
    const Tri3 t2 = ccw_tri({apex[0], np_id, vb});
    domain.elems[opp] = make_tri(t1[0], t1[1], t1[2]);
    const int nid = domain.n_elems();
    domain.elems.push_back(make_tri(t2[0], t2[1], t2[2]));
    return nid;
}

std::optional<int> edge_insertion(Mesh& domain, WorkingMesh& work, int tri, int bdy_vert, TieLog* log) {
    const std::array<int, 3> conn{domain.elems[tri][0], domain.elems[tri][1], domain.elems[tri][2]};
    auto in_conn = [&](int v) { return conn[0] == v || conn[1] == v || conn[2] == v; };
    if (!in_conn(bdy_vert)) bdy_vert = conn[0];
    const std::vector<int>& edges = domain.get_vertex_edges(bdy_vert);  // Python set: ascending
    if (edges.empty()) return std::nullopt;
    std::vector<int> others;
    for (int e : edges) {
        const int u = domain.edge2vert[e][0], v = domain.edge2vert[e][1];
        const int other = u == bdy_vert ? v : u;
        if (in_conn(other) && other != bdy_vert) others.push_back(other);
    }
    if (others.empty()) return std::nullopt;
    if (log && others.size() > 1) log->record("SPEC-07", "_tri_removal.py:301", others, others[0]);
    const int other = others[0];
    Point nx;
    for (int k = 0; k < 3; ++k)
        nx[k] = (2.0 / 3.0) * domain.points[bdy_vert][k] + (1.0 / 3.0) * domain.points[other][k];
    const int np_id = work.add_point(nx);
    int third = -1;
    for (int v : conn)
        if (v != bdy_vert && v != other) {
            third = v;
            break;
        }
    work.add_quad({bdy_vert, np_id, other, third});
    domain.elems[tri] = make_tri(0, 0, 0);
    return np_id;
}

std::optional<bool> route_leftover_tri(Mesh& domain, WorkingMesh& work, int tri, bool on_mesh_boundary,
                                       bool can_remove_edges, const std::unordered_set<int>& sub_b_edges,
                                       const std::unordered_set<int>& sub_b_verts,
                                       bool refuse_boundary_merge, bool preserve_boundary_verts,
                                       SweepContext* ctx, TieLog* log) {
    if (ctx) return ctx->route(tri, refuse_boundary_merge);
    const Elem edge_ids = domain.elem2edge[tri];
    std::vector<int> bdy_local;
    for (int i = 0; i < 3; ++i)
        if (sub_b_edges.count(edge_ids[i])) bdy_local.push_back(i);
    const int n_bdy = static_cast<int>(bdy_local.size());
    std::vector<int> bverts;
    for (int k = 0; k < 3; ++k)
        if (sub_b_verts.count(domain.elems[tri][k])) bverts.push_back(domain.elems[tri][k]);
    const bool on_domain_boundary = preserve_boundary_verts && on_mesh_boundary;
    auto collapse_safe = [&](int li) {
        const int e = edge_ids[li];
        const int va = domain.edge2vert[e][0], vb = domain.edge2vert[e][1];
        for (const Elem& q : work.quads) {
            const bool ha = std::find(q.begin(), q.end(), va) != q.end();
            const bool hb = std::find(q.begin(), q.end(), vb) != q.end();
            if (ha && hb) return false;
        }
        return true;
    };
    if (!on_mesh_boundary && n_bdy >= 1) {
        const int eid = edge_ids[bdy_local[0]];
        auto np_id = edge_bisection(domain, work, tri, bdy_local[0]);
        if (np_id) split_opposing_tri(domain, eid, *np_id, tri);
    } else if (n_bdy == 0) {
        if (bverts.empty()) return std::nullopt;
        edge_insertion(domain, work, tri, bverts[0], log);
    } else if (on_mesh_boundary && (n_bdy == 2 || n_bdy == 3)) {
        if (refuse_boundary_merge) return false;
        if (bverts.empty()) return std::nullopt;
        edge_insertion(domain, work, tri, bverts[0], log);
    } else if (on_mesh_boundary && n_bdy == 1 && can_remove_edges && !on_domain_boundary &&
               collapse_safe(bdy_local[0])) {
        edge_removal(domain, work, tri, bdy_local[0]);
    } else if (on_mesh_boundary && n_bdy == 1) {
        if (!edge_bisection(domain, work, tri, bdy_local[0])) return std::nullopt;
    } else {
        return std::nullopt;
    }
    return true;
}

std::unordered_set<int> handle_isolated_tris(const std::vector<Tri3>& layer_conn,
                                             const std::vector<int>& layer_global_ids,
                                             const std::unordered_set<int>& consumed,
                                             const std::vector<Point>& pts, WorkingMesh& work) {
    std::vector<std::uint64_t> order;
    std::unordered_map<std::uint64_t, std::vector<int>> e2t;
    for (int i = 0; i < static_cast<int>(layer_conn.size()); ++i) {
        const int a = layer_conn[i][0], b = layer_conn[i][1], c = layer_conn[i][2];
        for (auto k : {pair_key(a, b), pair_key(b, c), pair_key(a, c)}) {
            if (!e2t.count(k)) order.push_back(k);
            e2t[k].push_back(i);
        }
    }
    std::unordered_map<int, std::vector<int>> adj;
    for (auto k : order) {
        const auto& t = e2t[k];
        if (t.size() == 2) {
            adj[t[0]].push_back(t[1]);
            adj[t[1]].push_back(t[0]);
        }
    }
    std::unordered_map<int, int> g2l;
    for (int i = 0; i < static_cast<int>(layer_global_ids.size()); ++i) g2l[layer_global_ids[i]] = i;
    std::unordered_set<int> local_consumed;
    for (int g : consumed) {
        auto it = g2l.find(g);
        if (it != g2l.end()) local_consumed.insert(it->second);
    }
    work.tris.emplace();
    for (const Tri3& t : layer_conn) work.tris->push_back(t);
    std::unordered_set<int> newly;
    const int n = static_cast<int>(layer_conn.size());
    for (int li = 0; li < n; ++li) {
        if (local_consumed.count(li)) continue;
        bool has_nb = false;
        for (int nb : adj[li]) has_nb = has_nb || !local_consumed.count(nb);
        if (has_nb) continue;
        walk_isolated_tri(work, li, pts, 4);
        const auto& tn = (*work.tris)[li];
        if (!tn) continue;
        const int a = (*tn)[0], b = (*tn)[1], c = (*tn)[2];
        std::vector<int> new_nbs;
        for (auto k : {pair_key(a, b), pair_key(b, c), pair_key(a, c)}) {
            auto it = e2t.find(k);
            if (it == e2t.end()) continue;
            for (int nb : it->second)
                if (nb != li && !local_consumed.count(nb)) new_nbs.push_back(nb);
        }
        if (new_nbs.empty()) continue;
        const int nb = new_nbs[0];
        if (!(*work.tris)[nb]) continue;
        const std::set<int> va((*work.tris)[li]->begin(), (*work.tris)[li]->end());
        const std::set<int> vb((*work.tris)[nb]->begin(), (*work.tris)[nb]->end());
        std::vector<int> shared, ua, ub;
        for (int x : va) (vb.count(x) ? shared : ua).push_back(x);
        for (int x : vb)
            if (!va.count(x)) ub.push_back(x);
        if (shared.size() != 2 || ua.empty() || ub.empty()) continue;
        work.add_quad({ua[0], shared[0], ub[0], shared[1]});
        local_consumed.insert(li);
        local_consumed.insert(nb);
        newly.insert(layer_global_ids[li]);
        newly.insert(layer_global_ids[nb]);
    }
    return newly;
}

}  // namespace quadmesh::detail
