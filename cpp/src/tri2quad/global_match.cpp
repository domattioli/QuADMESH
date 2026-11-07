// T035: tri2quad._match_tris_to_quads (tri2quad.py:96-277) and
// _boundary_edge_set. Python neighbour sets become ascending std::set;
// each site where set order picks a result writes a tie record.
#include <algorithm>
#include <deque>
#include <functional>
#include <queue>
#include <tuple>

#include "quadmesh/tri2quad_detail.hpp"

namespace quadmesh::detail {

namespace {
inline std::array<std::uint64_t, 3> tri_edge_keys(const Tri3& t) {
    return {pair_key(t[0], t[1]), pair_key(t[1], t[2]), pair_key(t[2], t[0])};
}
}  // namespace

PairSet boundary_edge_set(const std::vector<Tri3>& tris) {
    std::unordered_map<std::uint64_t, int> count;
    count.reserve(tris.size() * 2);
    for (const Tri3& t : tris)
        for (auto k : tri_edge_keys(t)) ++count[k];
    PairSet out;
    for (const auto& kv : count)
        if (kv.second == 1) out.insert(kv.first);
    return out;
}

MatchResult match_tris_to_quads(const std::vector<Tri3>& tris, const std::vector<Point>& points,
                                const std::vector<int>* prio_in, bool quality_aware,
                                const std::vector<IPair>* seed_pairs, const PairSet* forbidden,
                                TieLog* log) {
    const int n = static_cast<int>(tris.size());
    const PairSet bset = boundary_edge_set(tris);

    std::vector<std::uint64_t> order;
    std::unordered_map<std::uint64_t, std::vector<int>> e2t;
    for (int i = 0; i < n; ++i) {
        for (auto k : tri_edge_keys(tris[i])) {
            auto it = e2t.find(k);
            if (it == e2t.end()) {
                order.push_back(k);
                e2t[k].push_back(i);
            } else {
                it->second.push_back(i);
            }
        }
    }
    std::vector<std::set<int>> adj(n);
    for (auto k : order) {
        const auto& lst = e2t[k];
        if (lst.size() != 2) continue;
        if (forbidden && !forbidden->empty() && forbidden->count(k)) continue;
        adj[lst[0]].insert(lst[1]);
        adj[lst[1]].insert(lst[0]);
    }

    std::vector<int> interior;
    std::vector<char> is_interior(n, 0);
    for (int i = 0; i < n; ++i) {
        bool any = false;
        for (auto k : tri_edge_keys(tris[i])) any = any || bset.count(k);
        if (!any) {
            interior.push_back(i);
            is_interior[i] = 1;
        }
    }

    // matched: Python dict, iterated later in key insertion order.
    std::vector<int> matched(n, -1);
    std::vector<int> key_order;
    std::vector<char> has_key(n, 0);
    auto set_match = [&](int a, int b) {
        for (int x : {a, b}) {
            if (!has_key[x]) {
                has_key[x] = 1;
                key_order.push_back(x);
            }
        }
        matched[a] = b;
        matched[b] = a;
    };
    std::vector<char> used(n, 0);

    std::vector<int> prio(n);
    for (int i = 0; i < n; ++i) prio[i] = prio_in ? (*prio_in)[i] : (is_interior[i] ? 0 : 1);

    if (seed_pairs) {
        for (const IPair& p : *seed_pairs) {
            const int a = p[0], b = p[1];
            if (used[a] || used[b] || !adj[a].count(b)) continue;
            set_match(a, b);
            used[a] = used[b] = 1;
        }
    }

    auto augment = [&](int start) -> bool {
        std::unordered_map<int, int> prev{{start, -1}};
        std::deque<int> queue{start};
        while (!queue.empty()) {
            const int u = queue.front();
            queue.pop_front();
            if (log && adj[u].size() > 1)
                log->record("SPEC-06", "tri2quad.py:191", {adj[u].begin(), adj[u].end()}, -1);
            for (int w : adj[u]) {
                if (prev.count(w)) continue;
                if (!used[w]) {
                    std::vector<int> path{w, u};
                    int x = u;
                    while (prev[x] != -1) {
                        x = prev[x];
                        path.push_back(x);
                    }
                    for (std::size_t k = 0; k + 1 < path.size(); k += 2) {
                        set_match(path[k], path[k + 1]);
                        used[path[k]] = used[path[k + 1]] = 1;
                    }
                    return true;
                }
                const int partner = has_key[w] ? matched[w] : -1;
                if (partner >= 0 && !prev.count(partner)) {
                    prev[w] = u;
                    prev[partner] = w;
                    queue.push_back(partner);
                }
            }
        }
        return false;
    };

    std::vector<int> free_deg(n, 0);
    for (int i = 0; i < n; ++i)
        for (int j : adj[i]) free_deg[i] += used[j] ? 0 : 1;
    using T = std::tuple<int, int, int>;
    std::priority_queue<T, std::vector<T>, std::greater<T>> heap;
    for (int i = 0; i < n; ++i)
        if (!used[i]) heap.emplace(prio[i], free_deg[i], i);

    const auto P = [&](int v) { return xy_of(points[v]); };
    std::vector<Tri3> tri_conn = tris;
    while (!heap.empty()) {
        auto [pr, d, i] = heap.top();
        heap.pop();
        (void)pr;
        if (used[i]) continue;
        if (d != free_deg[i]) {
            heap.emplace(prio[i], free_deg[i], i);
            continue;
        }
        std::vector<int> cand;
        for (int j : adj[i])
            if (!used[j]) cand.push_back(j);
        if (cand.empty()) continue;
        int j = -1;
        std::vector<int> tied;
        if (quality_aware) {
            std::tuple<int, double, int> best{};
            for (int y : cand) {
                std::tuple<int, double, int> key{prio[y], -quad_quality_pair(tri_conn, points, i, y),
                                                 free_deg[y]};
                if (j < 0 || key < best) {
                    best = key;
                    j = y;
                    tied = {y};
                } else if (key == best) {
                    tied.push_back(y);
                }
            }
        } else {
            std::pair<int, int> best{};
            for (int y : cand) {
                std::pair<int, int> key{prio[y], free_deg[y]};
                if (j < 0 || key < best) {
                    best = key;
                    j = y;
                    tied = {y};
                } else if (key == best) {
                    tied.push_back(y);
                }
            }
        }
        if (log && tied.size() > 1) log->record("SPEC-06", "tri2quad.py:238", tied, j);
        set_match(i, j);
        used[i] = used[j] = 1;
        for (int x : {i, j}) {
            for (int nb : adj[x]) {
                if (!used[nb]) {
                    --free_deg[nb];
                    heap.emplace(prio[nb], free_deg[nb], nb);
                }
            }
        }
    }

    {
        std::vector<int> unmatched;
        for (int i : interior)
            if (!used[i]) unmatched.push_back(i);
        if (log && unmatched.size() > 1) log->record("SPEC-06", "tri2quad.py:251", unmatched, -1);
        for (int i : interior)
            if (!used[i]) augment(i);
    }

    MatchResult res;
    PairSet seen;
    for (int i : key_order) {
        const int j = matched[i];
        if (j < 0) continue;
        if (!seen.insert(pair_key(i, j)).second) continue;
        const Tri3& ti = tris[i];
        const Tri3& tj = tris[j];
        auto in = [](const Tri3& t, int v) { return t[0] == v || t[1] == v || t[2] == v; };
        std::set<int> shared;
        for (int v : ti)
            if (in(tj, v)) shared.insert(v);
        if (shared.size() != 2) continue;
        const int a = *shared.begin(), b = *std::next(shared.begin());
        if (log) log->record("SPEC-06", "tri2quad.py:266", {a, b}, a);
        int o1 = -1, o2 = -1;
        for (int v : ti)
            if (!shared.count(v)) { o1 = v; break; }
        for (int v : tj)
            if (!shared.count(v)) { o2 = v; break; }
        Elem quad{o1, a, o2, b};
        XY p[4] = {P(quad[0]), P(quad[1]), P(quad[2]), P(quad[3])};
        if (area2_roll(p, 4) < 0) quad = {o1, b, o2, a};
        res.quads.push_back(quad);
    }
    for (int i = 0; i < n; ++i)
        if (!used[i]) res.leftover.push_back(i);
    return res;
}

}  // namespace quadmesh::detail
