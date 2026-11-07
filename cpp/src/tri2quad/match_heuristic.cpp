// T030: _match_quadmesh_plus.py (T1 fewest-eligible, T2 ladder, IE/OE
// ordering, walkability pre-pass). Neighbour lists keep Python's first-seen
// order (dict insertion order), so no tie is decided by set order here; the
// flagged and consumed sets are only tested for membership.
#include <algorithm>
#include <functional>

#include "quadmesh/tri2quad_detail.hpp"

namespace quadmesh::detail {

std::vector<std::vector<int>> build_tri_adjacency(const std::vector<Tri3>& conn) {
    std::vector<std::uint64_t> order;
    std::unordered_map<std::uint64_t, std::vector<int>> e2t;
    e2t.reserve(conn.size() * 2);
    for (int i = 0; i < static_cast<int>(conn.size()); ++i) {
        const int a = conn[i][0], b = conn[i][1], c = conn[i][2];
        for (auto k : {pair_key(a, b), pair_key(b, c), pair_key(a, c)}) {
            auto it = e2t.find(k);
            if (it == e2t.end()) {
                order.push_back(k);
                e2t[k].push_back(i);
            } else {
                it->second.push_back(i);
            }
        }
    }
    std::vector<std::vector<int>> adj(conn.size());
    for (auto k : order) {
        const auto& t = e2t[k];
        if (t.size() == 2) {
            adj[t[0]].push_back(t[1]);
            adj[t[1]].push_back(t[0]);
        }
    }
    return adj;
}

namespace {

using IsConsumed = std::function<bool(int)>;

std::vector<int> eligible(int ti, const std::vector<std::vector<int>>& adj, const IsConsumed& consumed,
                          const PairSet& flagged) {
    std::vector<int> out;
    for (int nb : adj[ti])
        if (!consumed(nb) && !flagged.count(pair_key(ti, nb))) out.push_back(nb);
    return out;
}

std::optional<IPair> t1_select(int ti, const std::vector<std::vector<int>>& adj, const IsConsumed& consumed,
                               const PairSet& flagged, const std::vector<Tri3>& conn,
                               const std::vector<Point>& pts) {
    if (consumed(ti)) return std::nullopt;
    const std::vector<int> nbs = eligible(ti, adj, consumed, flagged);
    if (nbs.empty()) return std::nullopt;
    int best_nb = -1;
    double best_q = -1.0;
    for (int nb : nbs) {
        const double q = quad_quality_pair(conn, pts, ti, nb);
        if (q > best_q) {
            best_q = q;
            best_nb = nb;
        }
    }
    if (best_nb < 0) return std::nullopt;
    return IPair{ti, best_nb};
}

std::vector<IPair> t2_ladder(int start, const std::vector<std::vector<int>>& adj, const IsConsumed& consumed,
                             const PairSet& flagged, int max_len = 20) {
    std::vector<IPair> pairs;
    std::unordered_set<int> visited;
    int current = start;
    for (int it = 0; it < max_len; ++it) {
        if (consumed(current) || visited.count(current)) break;
        visited.insert(current);
        std::vector<int> nbs;
        for (int nb : eligible(current, adj, consumed, flagged))
            if (!visited.count(nb)) nbs.push_back(nb);
        if (nbs.empty()) break;
        const int partner = nbs[0];
        pairs.push_back({current, partner});
        visited.insert(partner);
        std::vector<int> next_nbs;
        for (int nb : eligible(partner, adj, consumed, flagged))
            if (!visited.count(nb)) next_nbs.push_back(nb);
        if (next_nbs.empty()) break;
        current = next_nbs[0];
    }
    return pairs;
}

std::vector<int> order_groups(int n, const std::vector<int>& first, const std::vector<int>& second) {
    std::unordered_set<int> fs(first.begin(), first.end()), ss(second.begin(), second.end());
    std::vector<int> out;
    for (int e = 0; e < n; ++e)
        if (fs.count(e)) out.push_back(e);
    for (int e = 0; e < n; ++e)
        if (ss.count(e)) out.push_back(e);
    for (int e = 0; e < n; ++e)
        if (!fs.count(e) && !ss.count(e)) out.push_back(e);
    return out;
}

void walkability_prepass(std::vector<Tri3>& layer_conn, const std::vector<IPair>& removed_pairs,
                         const std::vector<Point>& pts, const std::vector<char>& consumed) {
    const auto adj = build_tri_adjacency(layer_conn);
    const PairSet flagged;
    WorkingMesh work(pts);
    work.tris.emplace();
    for (const Tri3& t : layer_conn) work.tris->push_back(t);
    const IsConsumed is_c = [&](int x) { return consumed[x] != 0; };
    for (const IPair& p : removed_pairs) {
        for (int target : {p[0], p[1]}) {
            if (consumed[target]) continue;
            if (!eligible(target, adj, is_c, flagged).empty()) continue;
            walk_isolated_tri(work, target, pts, 3);
        }
    }
    for (std::size_t i = 0; i < work.tris->size() && i < layer_conn.size(); ++i)
        if ((*work.tris)[i]) layer_conn[i] = *(*work.tris)[i];
}

}  // namespace

std::vector<IPair> match_layer_heuristic(const std::vector<Tri3>& layer_conn_in,
                                         const std::vector<int>& layer_global_ids,
                                         const std::vector<int>& ie_global_ids,
                                         const std::vector<int>& oe_global_ids,
                                         const std::vector<Point>& pts, const PairSet& flagged_pairs,
                                         const std::unordered_set<int>& already_consumed,
                                         bool use_t2_ladder, bool is_boundary_layer,
                                         const std::vector<IPair>* removed_edge_local_pairs) {
    std::vector<Tri3> layer_conn = layer_conn_in;
    const int n = static_cast<int>(layer_conn.size());
    std::unordered_map<int, int> g2l;
    for (int i = 0; i < n; ++i) g2l[layer_global_ids[i]] = i;

    std::vector<char> consumed(n, 0);
    for (int g : already_consumed) {
        auto it = g2l.find(g);
        if (it != g2l.end()) consumed[it->second] = 1;
    }
    auto adj = build_tri_adjacency(layer_conn);

    // flagged_pairs hold global elem id pairs; map both ends to local ids.
    // PairSet keys cannot be decoded without the ids, so the caller's keys
    // are matched by testing each local adjacency pair instead.
    PairSet local_flagged;
    for (int i = 0; i < n; ++i)
        for (int j : adj[i])
            if (flagged_pairs.count(pair_key(layer_global_ids[i], layer_global_ids[j]))) {
                // Python maps with global_to_local (last occurrence wins).
                local_flagged.insert(pair_key(g2l[layer_global_ids[i]], g2l[layer_global_ids[j]]));
            }

    std::vector<int> ie_local, oe_local;
    for (int g : ie_global_ids) {
        auto it = g2l.find(g);
        if (it != g2l.end()) ie_local.push_back(it->second);
    }
    for (int g : oe_global_ids) {
        auto it = g2l.find(g);
        if (it != g2l.end()) oe_local.push_back(it->second);
    }

    std::vector<int> all_local;
    if (is_boundary_layer) {
        all_local = order_groups(n, oe_local, ie_local);
        if (removed_edge_local_pairs && !removed_edge_local_pairs->empty()) {
            walkability_prepass(layer_conn, *removed_edge_local_pairs, pts, consumed);
            adj = build_tri_adjacency(layer_conn);
        }
    } else {
        all_local = order_groups(n, ie_local, oe_local);
    }

    std::vector<IPair> pairs;
    const IsConsumed is_c = [&](int x) { return consumed[x] != 0; };
    for (int ti : all_local) {
        if (consumed[ti]) continue;
        if (eligible(ti, adj, is_c, local_flagged).empty()) continue;
        auto result = t1_select(ti, adj, is_c, local_flagged, layer_conn, pts);
        if (!result) continue;
        const int a = (*result)[0], b = (*result)[1];
        if (use_t2_ladder) {
            const IsConsumed is_c_a = [&](int x) { return consumed[x] != 0 || x == a; };
            const auto ladder = t2_ladder(b, adj, is_c_a, local_flagged);
            pairs.push_back({a, b});
            consumed[a] = consumed[b] = 1;
            for (const IPair& p : ladder) {
                if (!consumed[p[0]] && !consumed[p[1]]) {
                    pairs.push_back(p);
                    consumed[p[0]] = consumed[p[1]] = 1;
                }
            }
        } else {
            pairs.push_back({a, b});
            consumed[a] = consumed[b] = 1;
        }
    }
    return pairs;
}

}  // namespace quadmesh::detail
