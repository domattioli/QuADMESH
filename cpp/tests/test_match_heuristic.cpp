// T031: per-layer pair lists (sweep then greedy merges) and leftover routing
// against the oracle, in order. FR-010: a divergence must sit at a logged tie
// site; the test reports the first divergent layer and field.
#include <catch_amalgamated.hpp>

#include "t2q_oracle.hpp"

using namespace quadmesh;

TEST_CASE("per-layer pairs match the oracle", "[tri2quad][heuristic][oracle]") {
    for (const std::string& name : gt::mesh_names()) {
        DYNAMIC_SECTION(name) {
            if (!t2q::has_expected(name, "match")) SKIP("expected dump missing: " << name);
            const auto& r = t2q::run(name, "match");
            const std::string d = t2q::first_layer_diff(r.trace, t2q::expected(name, "match")["per_layer"],
                                                        {"pairs", "pair_source", "leftover", "leftover_outcome"});
            INFO("first divergence: " << d);
            CHECK(d.empty());
        }
    }
}

TEST_CASE("build_tri_adjacency keeps first-seen order", "[tri2quad][heuristic]") {
    // Fan of three tris around vertex 0.
    const std::vector<detail::Tri3> conn = {{0, 1, 2}, {0, 2, 3}, {0, 3, 1}};
    const auto adj = detail::build_tri_adjacency(conn);
    CHECK(adj[0] == std::vector<int>{2, 1});  // edge (0,1) is seen first, shared with tri 2
    CHECK(adj[1] == std::vector<int>{0, 2});
}

TEST_CASE("match_layer_heuristic pairs a two-tri strip", "[tri2quad][heuristic]") {
    const std::vector<Point> pts = {{0, 0, 0}, {1, 0, 0}, {1, 1, 0}, {0, 1, 0}};
    const std::vector<detail::Tri3> conn = {{0, 1, 2}, {0, 2, 3}};
    const auto p = detail::match_layer_heuristic(conn, {10, 11}, {10, 11}, {}, pts, {}, {});
    REQUIRE(p.size() == 1);
    CHECK(p[0] == detail::IPair{0, 1});
    detail::PairSet forbid{detail::pair_key(10, 11)};
    CHECK(detail::match_layer_heuristic(conn, {10, 11}, {10, 11}, {}, pts, forbid, {}).empty());
}
