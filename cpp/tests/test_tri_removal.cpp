// T034: geometric-triangle baselines (tests/test_no_interior_tris.py
// _GEO_TRI_BASELINE and _GEO_TRI_FLAG_ON) and sweep-inserted points within
// 1e-12 of the oracle.
#include <catch_amalgamated.hpp>

#include "t2q_oracle.hpp"

using namespace quadmesh;

TEST_CASE("geometric-triangle baselines", "[tri2quad][removal]") {
    struct Pin {
        const char* mesh;
        bool rbm;
        int total;
    };
    for (const Pin& p : {Pin{"Block_O", false, 17}, Pin{"Block_O", true, 17}, Pin{"structuredMesh1", false, 5},
                         Pin{"structuredMesh1", true, 4}}) {
        DYNAMIC_SECTION(p.mesh << (p.rbm ? " refuse_boundary_merge" : " default")) {
            if (!std::filesystem::exists(gt::mesh_path(p.mesh))) SKIP("mesh missing");
            const auto& r = t2q::run(p.mesh, "core", p.rbm);
            CHECK(t2q::geometric_tris(r.out, true) == 0);
            CHECK(t2q::geometric_tris(r.out, false) == p.total);
        }
    }
}

TEST_CASE("sweep-inserted points match the oracle within 1e-12", "[tri2quad][removal][oracle]") {
    for (const std::string& name : gt::mesh_names()) {
        DYNAMIC_SECTION(name) {
            if (!t2q::has_expected(name, "match")) SKIP("expected dump missing");
            const auto& got = t2q::run(name, "match").trace.inserted_points;
            const auto& want = t2q::expected(name, "match")["inserted_points"];
            REQUIRE(got.size() == want.size());
            double worst = 0.0;
            for (std::size_t i = 0; i < got.size(); ++i)
                for (int k = 0; k < 3; ++k)
                    worst = std::max(worst, std::abs(got[i][k] - want[i][k].as_double()));
            INFO("max abs diff " << worst);
            CHECK(worst <= 1e-12);
        }
    }
}

TEST_CASE("edge_bisection splits a tri into a quad with a midpoint", "[tri2quad][removal]") {
    Mesh m({{0, 0, 0}, {2, 0, 0}, {0, 2, 0}}, {make_tri(0, 1, 2)}, "", MeshOptions{true, false});
    detail::WorkingMesh w(m.n_verts());
    int bdy = -1;
    for (int k = 0; k < 3; ++k) {
        const Edge& e = m.edge2vert[m.elem2edge[0][k]];
        if (e[0] == 0 && e[1] == 1) bdy = k;
    }
    REQUIRE(bdy >= 0);
    const auto np = detail::edge_bisection(m, w, 0, bdy);
    REQUIRE(np);
    CHECK(*np == 3);
    CHECK(w.extra[0][0] == 1.0);
    REQUIRE(w.quads.size() == 1);
    CHECK(w.quads[0] == Elem{0, 3, 1, 2});
    CHECK(m.elems[0] == make_tri(0, 0, 0));
}
