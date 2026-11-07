// T029: removed edges and flagged pairs per layer against the oracle
// (match-stage per_layer records, sweep order).
#include <catch_amalgamated.hpp>

#include "t2q_oracle.hpp"

using namespace quadmesh;

TEST_CASE("identify_edges per layer matches the oracle", "[tri2quad][identify][oracle]") {
    for (const std::string& name : gt::mesh_names()) {
        DYNAMIC_SECTION(name) {
            if (!t2q::has_expected(name, "match")) SKIP("expected dump missing: " << name);
            const auto& r = t2q::run(name, "match");
            const std::string d = t2q::first_layer_diff(
                r.trace, t2q::expected(name, "match")["per_layer"],
                {"status", "removed_edges", "removed_edge_ids", "flagged_pairs"});
            INFO("first divergence: " << d);
            CHECK(d.empty());
        }
    }
}

TEST_CASE("identify_edges on the input mesh: innermost layer", "[tri2quad][identify]") {
    if (!t2q::has_expected("Block_O", "match")) SKIP("Block_O missing");
    const Mesh& m = t2q::input("Block_O");
    const int li = m.n_layers() - 1;
    const auto sel = detail::identify_edges_in_layer(m, li);
    REQUIRE(sel.has_sub_mesh);
    const auto& w = t2q::expected("Block_O", "match")["per_layer"][0];
    CHECK(sel.removed_edge_ids == w["removed_edge_ids"].as_int_vector());
    CHECK(sel.flagged_vert_pairs == t2q::pairs_of(w["flagged_pairs"]));
}

TEST_CASE("fold_bridge_quads flags a quad on a flagged diagonal", "[tri2quad][identify]") {
    const std::vector<Elem> quads = {{0, 1, 2, 3}, {4, 5, 6, 7}, {0, 1, 2, -1}};
    CHECK(fold_bridge_quads(quads, {{{2, 0}}}) == std::vector<int>{0});
    CHECK(fold_bridge_quads(quads, {{{5, 7}}}) == std::vector<int>{1});
    CHECK(fold_bridge_quads(quads, {{{0, 1}}}).empty());
}
