// T021 (FR-014): the boundary-triangle passes give quad-pure core output on
// Block_O and structuredMesh1 and keep every original boundary vertex.
#include <catch_amalgamated.hpp>

#include <set>

#include "t2q_oracle.hpp"

using namespace quadmesh;

TEST_CASE("core output is quad-pure and keeps boundary vertices", "[tri2quad][boundary]") {
    for (const char* name : {"Block_O", "structuredMesh1"}) {
        DYNAMIC_SECTION(name) {
            if (!std::filesystem::exists(gt::mesh_path(name))) SKIP("mesh missing");
            const Mesh& in = t2q::input(name);
            const Mesh& out = t2q::run(name, "core").out;
            CHECK(t2q::n_tris(out) == 0);
            std::set<std::pair<double, double>> have;
            for (const Point& p : out.points) have.insert({p[0], p[1]});
            int missing = 0;
            for (int v : in.boundary_node_indices())
                missing += have.count({in.points[v][0], in.points[v][1]}) ? 0 : 1;
            CHECK(missing == 0);
        }
    }
}

TEST_CASE("ordered_loop walks a perimeter and rejects a broken one", "[tri2quad][boundary]") {
    const auto loop = detail::ordered_loop({{0, 1}, {2, 3}, {1, 2}, {3, 0}});
    REQUIRE(loop);
    CHECK(loop->size() == 4);
    CHECK(!detail::ordered_loop({{0, 1}, {2, 3}}));
}

TEST_CASE("remove_boundary_tris keeps leftovers when minimizing boundary change", "[tri2quad][boundary]") {
    std::vector<Point> pts = {{0, 0, 0}, {1, 0, 0}, {0, 1, 0}};
    std::vector<detail::Tri3> tris = {{0, 1, 2}};
    std::vector<Elem> quads;
    const auto bset = detail::boundary_edge_set(tris);
    const auto kept = detail::remove_boundary_tris(quads, {0}, tris, pts, bset, true, true);
    CHECK(kept == std::vector<int>{0});
    CHECK(pts.size() == 3);
}
