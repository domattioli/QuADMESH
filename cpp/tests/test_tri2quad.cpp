// T038: core stage (run_pipeline(do_post_process=False, n_smooth_iter=0) is
// tri2quad_routine with defaults): zero interior geometric triangles, counts
// within 0.5% of the oracle (SC-005), input unchanged (FR-015) and zero
// fold-bridge quads (FR-009).
#include <catch_amalgamated.hpp>

#include "t2q_oracle.hpp"

using namespace quadmesh;

namespace {
bool within(long long got, long long want) {
    return std::abs(static_cast<double>(got - want)) <= 0.005 * static_cast<double>(want);
}
}  // namespace

TEST_CASE("core stage against the oracle", "[tri2quad][core][oracle]") {
    for (const std::string& name : gt::mesh_names()) {
        DYNAMIC_SECTION(name) {
            if (!std::filesystem::exists(gt::mesh_path(name))) SKIP("mesh missing");
            const auto& r = t2q::run(name, "core");
            INFO(name << ": core elems " << r.out.n_elems() << " verts " << r.out.n_verts() << " tris "
                      << t2q::n_tris(r.out));
            CHECK(t2q::geometric_tris(r.out, true) == 0);
            CHECK(t2q::interior_residual_tris(r.out) == 0);
            if (t2q::has_expected(name, "core")) {
                const auto& w = t2q::expected(name, "core");
                CHECK(within(r.out.n_elems(), w["n_elems"].as_int()));
                CHECK(within(r.out.n_verts(), w["n_verts"].as_int()));
                CHECK(t2q::n_tris(r.out) == w["counts"]["out_tris"].as_int());
                CHECK(t2q::geometric_tris(r.out, true) == w["n_interior_geometric_tris"].as_int());
            }
        }
    }
}

TEST_CASE("tri2quad leaves its input unchanged", "[tri2quad][core]") {
    const std::string name = "Block_O";
    if (!std::filesystem::exists(gt::mesh_path(name))) SKIP("mesh missing");
    const Mesh before = read_fort14(gt::mesh_path(name));
    Mesh m = before;
    (void)tri2quad(m);
    CHECK(m.points == before.points);
    CHECK(m.elems == before.elems);
    CHECK(m.edge2vert == before.edge2vert);
    CHECK(m.edge2elem == before.edge2elem);
    CHECK(m.layers.OE == before.layers.OE);
    CHECK(m.layers.IE == before.layers.IE);
    CHECK(m.layers.OV == before.layers.OV);
    CHECK(m.layers.IV == before.layers.IV);
}

TEST_CASE("core output has no fold-bridge quads", "[tri2quad][core]") {
    for (const std::string& name : gt::mesh_names()) {
        DYNAMIC_SECTION(name) {
            if (!std::filesystem::exists(gt::mesh_path(name))) SKIP("mesh missing");
            const Mesh& in = t2q::input(name);
            const auto flagged = flagged_edges_of(in);
            const auto& out = t2q::run(name, "core").out;
            // Output vertices are compacted; map flagged pairs by coordinates.
            std::map<std::pair<double, double>, int> at;
            for (int v = 0; v < out.n_verts(); ++v) at[{out.points[v][0], out.points[v][1]}] = v;
            std::vector<std::array<int, 2>> mapped;
            for (const auto& p : flagged) {
                auto a = at.find({in.points[p[0]][0], in.points[p[0]][1]});
                auto b = at.find({in.points[p[1]][0], in.points[p[1]][1]});
                if (a != at.end() && b != at.end()) mapped.push_back({a->second, b->second});
            }
            CHECK(fold_bridge_quads(out.elems, mapped).empty());
        }
    }
}
