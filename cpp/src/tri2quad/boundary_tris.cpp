// T020: tri2quad.py _remove_boundary_tris (280-399), _edge_swap_tri_pairs
// (402-501), _ordered_loop (504-526), _point_insert_tri_pairs (529-665).
#include <algorithm>
#include <cmath>
#include <functional>
#include <map>

#include "quadmesh/tri2quad_detail.hpp"

namespace quadmesh::detail {

namespace {

std::set<int> uniq(const std::vector<int>& e) { return {e.begin(), e.end()}; }

// ccw() of the two passes: keep qd when np.sum area2 > 0, else reversed.
std::vector<int> ccw_list(const std::vector<int>& qd, const std::function<XY(int)>& P) {
    std::vector<XY> p;
    for (int v : qd) p.push_back(P(v));
    if (area2_roll(p.data(), static_cast<int>(p.size())) > 0) return qd;
    return {qd.rbegin(), qd.rend()};
}

bool quad_ok_ids(const std::vector<int>& q, const std::function<XY(int)>& P) {
    return quad_ok({P(q[0]), P(q[1]), P(q[2]), P(q[3])});
}

}  // namespace

std::vector<int> remove_boundary_tris(std::vector<Elem>& quads, const std::vector<int>& leftover_idx,
                                      const std::vector<Tri3>& tris, std::vector<Point>& points,
                                      const PairSet& bset, bool can_remove_edges,
                                      bool minimize_boundary_change) {
    std::vector<int> kept;
    if (leftover_idx.empty()) return kept;
    std::vector<Elem>& quad_arr = quads;
    std::vector<Point>& pts = points;
    std::unordered_map<int, std::vector<std::pair<int, int>>> inc;
    for (int r = 0; r < static_cast<int>(quad_arr.size()); ++r)
        for (int c = 0; c < 4; ++c) inc[quad_arr[r][c]].push_back({r, c});
    std::unordered_map<int, int> parent;
    auto find = [&](int v) {
        for (auto it = parent.find(v); it != parent.end(); it = parent.find(v)) v = it->second;
        return v;
    };

    for (int ti : leftover_idx) {
        const Tri3& t = tris[ti];
        std::vector<IPair> bdy;
        const IPair es[3] = {{t[0], t[1]}, {t[1], t[2]}, {t[2], t[0]}};
        for (const IPair& e : es)
            if (bset.count(pair_key(e[0], e[1]))) bdy.push_back({std::min(e[0], e[1]), std::max(e[0], e[1])});
        if (bdy.empty()) {
            kept.push_back(ti);
            continue;
        }
        if (minimize_boundary_change) {
            kept.push_back(ti);
            continue;
        }
        if (bdy.size() >= 2) continue;
        if (!can_remove_edges) continue;
        const int va = find(bdy[0][0]), vb = find(bdy[0][1]);
        if (va == vb) continue;
        Point new_va;
        for (int k = 0; k < 3; ++k) new_va[k] = 0.5 * (pts[va][k] + pts[vb][k]);
        std::set<int> affected;
        for (auto& rc : inc[va]) affected.insert(rc.first);
        for (auto& rc : inc[vb]) affected.insert(rc.first);
        bool ok = true;
        for (int r : affected) {
            std::array<int, 4> row;
            for (int c = 0; c < 4; ++c) row[c] = quad_arr[r][c] == vb ? va : quad_arr[r][c];
            if (std::set<int>(row.begin(), row.end()).size() != 4) {
                ok = false;
                break;
            }
            std::array<XY, 4> poly;
            for (int c = 0; c < 4; ++c) poly[c] = row[c] == va ? xy_of(new_va) : xy_of(pts[row[c]]);
            if (!quad_ok(poly)) {
                ok = false;
                break;
            }
        }
        if (!ok) continue;
        pts[va] = new_va;
        parent[vb] = va;
        for (auto& rc : inc[vb]) {
            quad_arr[rc.first][rc.second] = va;
            inc[va].push_back(rc);
        }
        inc[vb].clear();
    }
    return kept;
}

void edge_swap_tri_pairs(std::vector<Elem>& quads, std::vector<Tri3>& tris,
                         const std::vector<Point>& points, TieLog* log) {
    auto P = [&](int v) { return xy_of(points[v]); };
    std::vector<std::vector<int>> elems;
    for (const Elem& q : quads) elems.push_back({q[0], q[1], q[2], q[3]});
    for (const Tri3& t : tris) elems.push_back({t[0], t[1], t[2]});

    struct Cand {
        int i, j, q;
        std::vector<int> q1, q2;
    };
    auto candidates = [&]() {
        std::unordered_map<int, std::set<int>> v2e;
        std::vector<std::set<int>> es(elems.size());
        for (std::size_t ei = 0; ei < elems.size(); ++ei) {
            es[ei] = uniq(elems[ei]);
            for (int v : es[ei]) v2e[v].insert(static_cast<int>(ei));
        }
        std::vector<Cand> out;
        std::set<std::array<int, 3>> seen;
        for (int ei = 0; ei < static_cast<int>(elems.size()); ++ei) {
            if (es[ei].size() != 3) continue;
            std::vector<int> found_s;
            for (int s : es[ei]) {  // Python set(e): ascending here (ADR 0001)
                const std::set<int>& fan = v2e[s];
                std::vector<int> tri_f, quad_f;
                for (int k : fan) {
                    if (es[k].size() == 3) tri_f.push_back(k);
                    if (es[k].size() == 4) quad_f.push_back(k);
                }
                if (tri_f.size() != 2 || quad_f.size() != 1 ||
                    std::find(tri_f.begin(), tri_f.end(), ei) == tri_f.end())
                    continue;
                const int t2 = tri_f[0] == ei ? tri_f[1] : tri_f[0];
                const int q = quad_f[0];
                std::array<int, 3> key{std::min(ei, t2), std::max(ei, t2), q};
                if (!seen.insert(key).second) continue;
                const std::set<int>&T1 = es[ei], &T2 = es[t2], &Q = es[q];
                auto minus = [](const std::set<int>& A, std::initializer_list<const std::set<int>*> Bs,
                                int s0) {
                    std::set<int> r;
                    for (int x : A) {
                        if (x == s0) continue;
                        bool skip = false;
                        for (auto* B : Bs) skip = skip || B->count(x);
                        if (!skip) r.insert(x);
                    }
                    return r;
                };
                std::set<int> T1Q, T2Q;
                for (int x : T1)
                    if (Q.count(x) && x != s) T1Q.insert(x);
                for (int x : T2)
                    if (Q.count(x) && x != s) T2Q.insert(x);
                const std::set<int>&b = T1Q, &d = T2Q;
                const std::set<int> c = minus(Q, {&b, &d}, s);
                const std::set<int> a = minus(T1, {&b}, s);
                const std::set<int> e2 = minus(T2, {&d}, s);
                if (!(a.size() == 1 && b.size() == 1 && c.size() == 1 && d.size() == 1 && e2.size() == 1))
                    continue;
                const int av = *a.begin(), bv = *b.begin(), cv = *c.begin(), dv = *d.begin(),
                          ev = *e2.begin();
                std::vector<int> q1 = ccw_list({s, av, bv, cv}, P);
                std::vector<int> q2 = ccw_list({s, cv, dv, ev}, P);
                if (quad_ok_ids(q1, P) && quad_ok_ids(q2, P)) {
                    out.push_back({ei, t2, q, q1, q2});
                    found_s.push_back(s);
                }
            }
            if (log && found_s.size() > 1)
                log->record("SPEC-07", "tri2quad.py:444", found_s, found_s.front());
        }
        return out;
    };

    bool changed = true;
    while (changed) {
        changed = false;
        std::vector<Cand> cands = candidates();
        if (cands.empty()) break;
        std::unordered_map<int, int> tri_use, quad_use;
        for (const Cand& c : cands) {
            ++tri_use[c.i];
            ++tri_use[c.j];
            ++quad_use[c.q];
        }
        std::stable_sort(cands.begin(), cands.end(), [&](const Cand& x, const Cand& y) {
            return tri_use[x.i] + tri_use[x.j] + quad_use[x.q] < tri_use[y.i] + tri_use[y.j] + quad_use[y.q];
        });
        std::set<int> usedset;
        std::vector<std::vector<int>> new_elems;
        for (const Cand& c : cands) {
            if (usedset.count(c.i) || usedset.count(c.j) || usedset.count(c.q)) continue;
            usedset.insert({c.i, c.j, c.q});
            new_elems.push_back(c.q1);
            new_elems.push_back(c.q2);
            changed = true;
        }
        if (changed) {
            std::vector<std::vector<int>> next;
            for (std::size_t k = 0; k < elems.size(); ++k)
                if (!usedset.count(static_cast<int>(k))) next.push_back(elems[k]);
            for (auto& e : new_elems) next.push_back(e);
            elems.swap(next);
        }
    }
    quads.clear();
    tris.clear();
    for (const auto& e : elems) {
        const std::size_t u = uniq(e).size();
        if (u == 4) quads.push_back({e[0], e[1], e[2], e[3]});
        else if (u == 3) tris.push_back({e[0], e[1], e[2]});
    }
}

std::optional<std::vector<int>> ordered_loop(const std::vector<IPair>& perimeter) {
    std::vector<int> keys;
    std::unordered_map<int, std::vector<int>> adj;
    for (const IPair& e : perimeter) {
        for (int k = 0; k < 2; ++k) {
            const int u = e[k], v = e[1 - k];
            if (!adj.count(u)) keys.push_back(u);
            adj[u].push_back(v);
        }
    }
    for (int k : keys)
        if (adj[k].size() != 2) return std::nullopt;
    if (perimeter.empty()) return std::nullopt;
    const int start = perimeter[0][0];
    std::vector<int> loop{start};
    int prev = -1;
    bool has_prev = false;
    int cur = start;
    while (true) {
        int nxt = -1;
        bool found = false;
        for (int w : adj[cur]) {
            if (has_prev && w == prev) continue;
            nxt = w;
            found = true;
            break;
        }
        if (!found) return std::nullopt;
        if (nxt == start) break;
        loop.push_back(nxt);
        prev = cur;
        has_prev = true;
        cur = nxt;
        if (loop.size() > perimeter.size() + 1) return std::nullopt;
    }
    return loop;
}

void point_insert_tri_pairs(std::vector<Elem>& quads, std::vector<Tri3>& tris, std::vector<Point>& points) {
    std::vector<Point>& pts = points;
    std::vector<std::vector<int>> elems;
    for (const Elem& q : quads) elems.push_back({q[0], q[1], q[2], q[3]});
    for (const Tri3& t : tris) elems.push_back({t[0], t[1], t[2]});
    auto nuniq = [](const std::vector<int>& e) { return uniq(e).size(); };

    bool changed = true;
    while (changed) {
        changed = false;
        std::unordered_map<std::uint64_t, std::vector<int>> edge2elem;
        for (int ei = 0; ei < static_cast<int>(elems.size()); ++ei) {
            const auto& e = elems[ei];
            const int n = static_cast<int>(e.size());
            for (int i = 0; i < n; ++i) edge2elem[pair_key(e[i], e[(i + 1) % n])].push_back(ei);
        }
        std::set<int> consumed;
        std::vector<std::vector<int>> new_elems;
        std::vector<Point> new_pts;
        for (int ti = 0; ti < static_cast<int>(elems.size()); ++ti) {
            const std::vector<int> e = elems[ti];
            if (consumed.count(ti) || nuniq(e) != 3) continue;
            for (int i = 0; i < 3; ++i) {
                const auto key = pair_key(e[i], e[(i + 1) % 3]);
                std::vector<int> nbrs;
                for (int x : edge2elem[key])
                    if (x != ti && !consumed.count(x) && nuniq(elems[x]) == 4) nbrs.push_back(x);
                if (nbrs.empty()) continue;
                const int q = nbrs[0];
                // Perimeter edges in dict insertion order.
                std::vector<std::uint64_t> order;
                std::unordered_map<std::uint64_t, std::pair<IPair, int>> cnt;
                for (const auto* el : {&elems[ti], &elems[q]}) {
                    const int n = static_cast<int>(el->size());
                    for (int k = 0; k < n; ++k) {
                        const int a = (*el)[k], b = (*el)[(k + 1) % n];
                        const auto kk = pair_key(a, b);
                        auto it = cnt.find(kk);
                        if (it == cnt.end()) {
                            order.push_back(kk);
                            cnt[kk] = {{std::min(a, b), std::max(a, b)}, 1};
                        } else {
                            ++it->second.second;
                        }
                    }
                }
                std::vector<IPair> perim;
                for (auto kk : order)
                    if (cnt[kk].second == 1) perim.push_back(cnt[kk].first);
                const auto loop_opt = ordered_loop(perim);
                if (!loop_opt || loop_opt->size() != 5) continue;
                const std::vector<int>& loop = *loop_opt;
                XY LP[5];
                double zs = 0.0;
                for (int k = 0; k < 5; ++k) {
                    LP[k] = xy_of(pts[loop[k]]);
                    zs += pts[loop[k]][2];
                }
                const double zc = zs / 5.0;
                XY centroid{0.0, 0.0};
                XY mn = LP[0], mx = LP[0];
                for (int k = 0; k < 5; ++k) {
                    centroid[0] += LP[k][0];
                    centroid[1] += LP[k][1];
                    for (int c = 0; c < 2; ++c) {
                        mn[c] = std::min(mn[c], LP[k][c]);
                        mx[c] = std::max(mx[c], LP[k][c]);
                    }
                }
                centroid[0] /= 5.0;
                centroid[1] /= 5.0;
                std::vector<XY> std_cand{centroid};
                auto lin = [](double a, double b) {
                    std::array<double, 4> r;
                    const double step = (b - a) / 5.0;
                    for (int k = 1; k <= 4; ++k) r[k - 1] = k * step + a;
                    return r;
                };
                const auto xs = lin(mn[0], mx[0]);
                const auto ys = lin(mn[1], mx[1]);
                for (double x : xs)
                    for (double y : ys) std_cand.push_back({x, y});
                const double dx = mx[0] - mn[0], dy = mx[1] - mn[1];
                const double diag = std::sqrt(dx * dx + dy * dy);
                std::vector<XY> fb_cand;
                for (int k = 0; k < 5; ++k)
                    fb_cand.push_back({0.5 * (LP[k][0] + LP[(k + 2) % 5][0]), 0.5 * (LP[k][1] + LP[(k + 2) % 5][1])});
                for (int k = 0; k < 5; ++k) {
                    const XY em{0.5 * (LP[k][0] + LP[(k + 1) % 5][0]), 0.5 * (LP[k][1] + LP[(k + 1) % 5][1])};
                    XY inw{centroid[0] - em[0], centroid[1] - em[1]};
                    const double nrm = std::sqrt(inw[0] * inw[0] + inw[1] * inw[1]);
                    if (nrm < 1e-12) continue;
                    inw[0] /= nrm;
                    inw[1] /= nrm;
                    for (double t : {0.1, 0.2, 0.3, 0.4}) {
                        const double s = t * diag;
                        fb_cand.push_back({em[0] + s * inw[0], em[1] + s * inw[1]});
                    }
                }
                const int pt = static_cast<int>(pts.size());
                struct Sel {
                    XY p;
                    std::vector<int> q1, q2;
                };
                auto scan = [&](const std::vector<XY>& cands) {
                    double bq = -1.0;
                    std::optional<Sel> bsel;
                    for (const XY& pxy : cands) {
                        auto P = [&](int v) { return v == pt ? pxy : xy_of(pts[v]); };
                        for (int r = 0; r < 5; ++r) {
                            int L[5];
                            for (int k = 0; k < 5; ++k) L[k] = loop[(r + k) % 5];
                            std::vector<int> q1 = ccw_list({L[0], L[1], L[2], pt}, P);
                            std::vector<int> q2 = ccw_list({L[2], L[3], L[4], pt}, P);
                            if (quad_ok_ids(q1, P) && quad_ok_ids(q2, P)) {
                                const double mq =
                                    std::min(quad_quality({P(q1[0]), P(q1[1]), P(q1[2]), P(q1[3])}),
                                             quad_quality({P(q2[0]), P(q2[1]), P(q2[2]), P(q2[3])}));
                                if (mq > bq) {
                                    bq = mq;
                                    bsel = Sel{pxy, q1, q2};
                                }
                            }
                        }
                    }
                    return std::make_pair(bq, bsel);
                };
                auto [best_q, best] = scan(std_cand);
                if (!best || best_q < 0.1) {
                    auto [fb_q, fb] = scan(fb_cand);
                    if (fb && fb_q >= 0.3) {
                        best_q = fb_q;
                        best = fb;
                    }
                }
                if (!best || best_q < 0.1) continue;
                const int pid = static_cast<int>(pts.size() + new_pts.size());
                new_pts.push_back({best->p[0], best->p[1], zc});
                for (const auto* ql : {&best->q1, &best->q2}) {
                    std::vector<int> ne;
                    for (int v : *ql) ne.push_back(v == pt ? pid : v);
                    new_elems.push_back(ne);
                }
                consumed.insert(ti);
                consumed.insert(q);
                changed = true;
                break;
            }
        }
        if (changed) {
            for (const Point& p : new_pts) pts.push_back(p);
            std::vector<std::vector<int>> next;
            for (std::size_t k = 0; k < elems.size(); ++k)
                if (!consumed.count(static_cast<int>(k))) next.push_back(elems[k]);
            for (auto& e : new_elems) next.push_back(e);
            elems.swap(next);
        }
    }
    quads.clear();
    tris.clear();
    for (const auto& e : elems) {
        const std::size_t u = uniq(e).size();
        if (u == 4) quads.push_back({e[0], e[1], e[2], e[3]});
        else if (u == 3) tris.push_back({e[0], e[1], e[2]});
    }
}

}  // namespace quadmesh::detail
