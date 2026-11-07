#include <catch_amalgamated.hpp>

#include "diff_lib.hpp"
#include "quadmesh/json.hpp"

using namespace quadmesh::difftool;

TEST_CASE("canonical row rotates to the smallest vertex and drops padding", "[diff]") {
    REQUIRE(canonical_row({5, 3, 9, 4}) == Row{3, 9, 4, 5});
    REQUIRE(canonical_row({7, 2, 8, 6}) == Row{2, 8, 6, 7});
    REQUIRE(canonical_row({4, 5, 6, 6}) == Row{4, 5, 6});   // [a,b,c,c]
    REQUIRE(canonical_row({4, 5, 6, 4}) == Row{4, 5, 6});   // [a,b,c,a]
    REQUIRE(canonical_row({4, 5, 6, -1}) == Row{4, 5, 6});  // C++ triangle
    REQUIRE(canonical_row({6, 4, 5}) == Row{4, 5, 6});      // direction kept
}

TEST_CASE("canonical rows sort and make rotated duplicates equal", "[diff]") {
    auto a = canonical_rows({{9, 1, 2, 3}, {1, 2, 3, 9}, {0, 4, 5, 6}});
    REQUIRE(a.size() == 3);
    REQUIRE(a[0] == Row{0, 4, 5, 6});
    REQUIRE(a[1] == a[2]);
    // Same quads in another order and rotation: empty connectivity diff.
    StageResult r;
    diff_connectivity({{1, 2, 3, 4}, {5, 6, 7, 8}}, {{7, 8, 5, 6}, {3, 4, 1, 2}}, {}, r);
    REQUIRE(r.diffs.empty());
    REQUIRE(r.conn_oracle_only == 0);
}

TEST_CASE("connectivity diff counts rows on each side", "[diff]") {
    StageResult r;
    diff_connectivity({{1, 2, 3, 4}, {5, 6, 7, 8}}, {{1, 2, 3, 4}, {5, 6, 7, 9}}, {}, r);
    REQUIRE(r.conn_oracle_only == 1);
    REQUIRE(r.conn_cpp_only == 1);
    REQUIRE(r.diffs.size() == 2);
    REQUIRE(r.unexplained() == 2);
}

static std::vector<TieRecord> sample_ties() {
    TieRecord a;
    a.seq = 5; a.spec = "SPEC-07"; a.py_site = "tri2quad.py:100"; a.layer = 3; a.ids = {10, 11}; a.chosen = 10;
    TieRecord b = a;
    b.seq = 9; b.spec = "SPEC-05"; b.py_site = "tri2quad.py:200"; b.layer = 2; b.ids = {20, 21}; b.chosen = 21;
    return {a, b};
}

TEST_CASE("tie attribution names the lowest matching record", "[diff]") {
    auto ties = sample_ties();
    Difference d;
    d.ids = {11, 99};
    attribute(d, ties);
    REQUIRE(d.explained);
    REQUIRE(d.attribution == "SPEC-07 tri2quad.py:100 seq 5");

    Difference e;
    e.ids = {500, 501};
    attribute(e, ties);
    REQUIRE_FALSE(e.explained);
    REQUIRE(e.attribution == "unexplained");
}

TEST_CASE("tie attribution honours layer and the at-or-before bound", "[diff]") {
    auto ties = sample_ties();
    Difference d;
    d.ids = {21};
    d.layer = 2;
    attribute(d, ties);
    REQUIRE(d.explained);
    d.layer = 3;  // tie is in layer 2
    attribute(d, ties);
    REQUIRE_FALSE(d.explained);
    d.layer = -1;
    attribute(d, ties, 9);  // seq 9 is at the bound: counts
    REQUIRE(d.explained);
    attribute(d, ties, 8);  // after the bound: does not count
    REQUIRE_FALSE(d.explained);
}

TEST_CASE("0.5 percent count bound edges", "[diff]") {
    REQUIRE(within_count_bound(1000, 1000));
    REQUIRE(within_count_bound(1005, 1000));    // exactly 0.5%
    REQUIRE(within_count_bound(995, 1000));
    REQUIRE_FALSE(within_count_bound(1006, 1000));
    REQUIRE_FALSE(within_count_bound(994, 1000));
    REQUIRE(within_count_bound(2989 + 14, 2989));      // 14 <= 14.945
    REQUIRE_FALSE(within_count_bound(2989 + 15, 2989));  // 15 > 14.945
    REQUIRE(within_count_bound(0, 0));
    REQUIRE_FALSE(within_count_bound(1, 0));
}

TEST_CASE("relative tolerance edge", "[diff]") {
    REQUIRE(within_rel(1.000001, 1.0, 1e-6));
    REQUIRE_FALSE(within_rel(1.00001, 1.0, 1e-6));
    REQUIRE(within_rel(0.0, 0.0, 1e-6));
}

static const char* kOracle =
    R"({"n_elems":1000,"n_verts":1100,"n_interior_residual_tris":0,"n_interior_geometric_tris":0,
        "quality":{"mean":0.5,"min":0.0,"max":0.99,"std":0.15,"n_bad":10,"n_concave":2}})";

static StageResult run_rule(const std::string& cpp_json, const std::string& stage) {
    StageResult r;
    apply_pass_rule(quadmesh::json::parse(kOracle), quadmesh::json::parse(cpp_json), stage, Options{}, r);
    return r;
}

TEST_CASE("pass rule items 1 to 4", "[diff]") {
    const std::string good =
        R"({"n_elems":1005,"n_verts":1100,"n_interior_residual_tris":0,"n_interior_geometric_tris":0,
            "quality":{"mean":0.5,"min":0.0,"max":0.99,"std":0.15,"n_bad":10,"n_concave":2}})";
    REQUIRE(run_rule(good, "core").state == StageResult::State::Pass);
    REQUIRE(run_rule(good, "match").state == StageResult::State::Pass);

    SECTION("item 1: residual triangle fails match") {
        std::string bad = good;
        bad.replace(bad.find("\"n_interior_residual_tris\":0"), 28, "\"n_interior_residual_tris\":1");
        REQUIRE(run_rule(bad, "match").state == StageResult::State::Fail);
    }
    SECTION("item 2: geometric triangle fails core but not match") {
        std::string bad = good;
        bad.replace(bad.find("\"n_interior_geometric_tris\":0"), 29, "\"n_interior_geometric_tris\":1");
        REQUIRE(run_rule(bad, "core").state == StageResult::State::Fail);
        REQUIRE(run_rule(bad, "match").state == StageResult::State::Pass);
    }
    SECTION("item 3: count one past the bound fails") {
        std::string bad = good;
        bad.replace(bad.find("1005"), 4, "1006");
        REQUIRE(run_rule(bad, "core").state == StageResult::State::Fail);
    }
    SECTION("item 4: exact counts and relative stats") {
        std::string bad = good;
        bad.replace(bad.find("\"n_bad\":10"), 10, "\"n_bad\":11");
        REQUIRE(run_rule(bad, "full").state == StageResult::State::Fail);
        std::string bad2 = good;
        bad2.replace(bad2.find("\"mean\":0.5"), 10, "\"mean\":0.51");
        REQUIRE(run_rule(bad2, "full").state == StageResult::State::Fail);
        std::string ok = good;
        ok.replace(ok.find("\"mean\":0.5"), 10, "\"mean\":0.5000004");
        REQUIRE(run_rule(ok, "full").state == StageResult::State::Pass);
    }
}

TEST_CASE("table diff ignores elem2edge slot 3 and attributes by tie", "[diff]") {
    using quadmesh::json::parse;
    auto o = parse(R"({"adjacency":{"edge2vert":[[0,1]],"edge2elem":[[0,-1]],"elem2edge":[[0,1,2]],"vert2elem":[[0]]},
                       "per_layer":[{"layer":3,"pairs":[[10,11],[12,13]]}],"layer_priority":[1,2]})");
    auto c = parse(R"({"adjacency":{"edge2vert":[[0,1]],"edge2elem":[[0,-1]],"elem2edge":[[0,1,2,-1]],"vert2elem":[[0]]},
                       "per_layer":[{"layer":3,"pairs":[[10,11],[12,14]]}]})");
    StageResult r;
    diff_tables(o, c, Options{}, sample_ties(), r);
    REQUIRE(r.skipped_tables == std::vector<std::string>{"layer_priority"});
    REQUIRE(r.diffs.size() == 1);
    REQUIRE(r.diffs[0].layer == 3);
    REQUIRE_FALSE(r.diffs[0].explained);  // ids 12,13,14 not in any tie
    TieRecord t; t.seq = 1; t.spec = "SPEC-05"; t.py_site = "x:1"; t.layer = 3; t.ids = {13, 14}; t.chosen = 14;
    StageResult r2;
    diff_tables(o, c, Options{}, {t}, r2);
    REQUIRE(r2.diffs[0].explained);
    REQUIRE(r2.unexplained() == 0);
}

TEST_CASE("timing gate: cpp must not be slower", "[diff]") {
    REQUIRE(timing_passes(2.0, 1.0));
    REQUIRE(timing_passes(2.0, 2.0));
    REQUIRE_FALSE(timing_passes(2.0, 2.001));
}

TEST_CASE("fort14 text parser reads padded triangle rows", "[diff]") {
    auto d = parse_fort14_text("g\n2 4\n1 0 0 0\n2 1 0 0\n3 1 1 0\n4 0 1 0\n1 4 1 2 3 3\n2 3 1 3 4\n");
    REQUIRE(d.nodes.size() == 4);
    REQUIRE(d.elems.size() == 2);
    REQUIRE(canonical_row(d.elems[0]) == Row{0, 1, 2});
    REQUIRE(canonical_row(d.elems[1]) == Row{0, 2, 3});
}
