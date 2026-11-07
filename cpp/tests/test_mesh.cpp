// T013 / T015: Mesh, is_tri and adjacency tables against the CHILmesh oracle.
#include <catch_amalgamated.hpp>

#include "ground_truth.hpp"
#include "quadmesh/error.hpp"
#include "quadmesh/mesh.hpp"

using namespace quadmesh;

TEST_CASE("is_tri: trailing -1 marks a triangle, a repeated vertex does not", "[mesh]") {
    REQUIRE(is_tri(Elem{0, 1, 2, -1}));
    REQUIRE_FALSE(is_tri(Elem{0, 1, 2, 0}));  // a quad in the port (ADR 0001)
    REQUIRE_FALSE(is_tri(Elem{0, 1, 2, 3}));
    REQUIRE(n_corners(make_tri(4, 5, 6)) == 3);
}

TEST_CASE("Mesh: two triangles, orientation and adjacency", "[mesh]") {
    // Unit square split on the diagonal 0-2; second triangle given clockwise.
    std::vector<Point> p = {{0, 0, 0}, {1, 0, 0}, {1, 1, 0}, {0, 1, 0}};
    Mesh m(p, {make_tri(0, 1, 2), make_tri(0, 2, 3)}, "sq", {true, false});
    REQUIRE(m.n_edges() == 5);
    REQUIRE(m.edge2vert[0] == Edge{0, 1});
    REQUIRE(m.edge2vert[2] == Edge{0, 2});
    REQUIRE(m.edge2elem[2] == Edge{0, 1});
    REQUIRE(m.elem2edge[0][3] == -1);
    REQUIRE(m.boundary_edges() == std::vector<int>{0, 1, 3, 4});
    REQUIRE(m.boundary_node_indices() == std::vector<int>{0, 1, 2, 3});
    REQUIRE(m.find_edge(2, 0) == 2);
    REQUIRE(m.find_edge(1, 3) == -1);

    Mesh cw(p, {make_tri(0, 2, 1)}, "", {true, false});
    REQUIRE(cw.elems[0] == Elem{0, 1, 2, -1});
    REQUIRE(cw.signed_area(0) == Catch::Approx(0.5));

    // ccw order around vertex 0: edge to 1 (0 rad), to 2 (pi/4), to 3 (pi/2).
    REQUIRE(m.ccw_edges_around_vert(0) == std::vector<int>{0, 2, 4});

    Elem q = quad_from_tri_pair(m.points, m.elems[0], m.elems[1]);
    // [apex_a=1, s0=0, apex_b=3, s1=2] is clockwise, so s0 and s1 swap.
    REQUIRE(q == Elem{1, 2, 3, 0});
    REQUIRE_THROWS_AS(quad_from_tri_pair(m.points, m.elems[0], m.elems[0]), Error);
}

TEST_CASE("submesh and remove_unused", "[mesh]") {
    std::vector<Point> p = {{0, 0, 0}, {1, 0, 0}, {1, 1, 0}, {0, 1, 0}, {9, 9, 0}};
    Mesh m(p, {make_tri(0, 1, 2), make_tri(0, 2, 3)}, "g", {true, false});
    Mesh s = m.submesh({1}, {true, false});
    REQUIRE(s.n_verts() == 3);
    REQUIRE(s.grid_name == "g_submesh");
    REQUIRE(s.elems[0] == Elem{0, 1, 2, -1});
    Mesh r = remove_unused(m, {true, false});
    REQUIRE(r.n_verts() == 4);
    REQUIRE(r.grid_name == "g");
}

TEST_CASE("adjacency matches the CHILmesh oracle", "[mesh][oracle]") {
    for (const std::string& name : gt::mesh_names()) {
        DYNAMIC_SECTION(name) {
            if (!gt::available(name)) SKIP("ground truth missing for " << name);
            const Mesh& m = gt::mesh(name);
            const auto& r = gt::ref(name);
            const auto& a = r["adjacency"];
            REQUIRE(m.n_verts() == r["n_verts"].as_int());
            REQUIRE(m.n_elems() == r["n_elems"].as_int());
            REQUIRE(m.n_edges() == r["n_edges"].as_int());
            const int ncols = static_cast<int>(r["n_cols"].as_int());

            gt::Diff d_e2v, d_e2e, d_el2e, d_v2e, d_conn;
            const auto& conn = r["fort14"]["conn"];
            for (int e = 0; e < m.n_elems(); ++e) {
                const auto row = conn[e].as_int_vector();
                for (int k = 0; k < n_corners(m.elems[e]); ++k) {
                    if (m.elems[e][k] != row[k]) d_conn.add("elem " + std::to_string(e));
                }
            }
            for (int id = 0; id < m.n_edges(); ++id) {
                const auto ev = a["edge2vert"][id].as_int_vector();
                const auto ee = a["edge2elem"][id].as_int_vector();
                if (m.edge2vert[id][0] != ev[0] || m.edge2vert[id][1] != ev[1]) {
                    d_e2v.add("edge " + std::to_string(id));
                }
                if (m.edge2elem[id][0] != ee[0] || m.edge2elem[id][1] != ee[1]) {
                    d_e2e.add("edge " + std::to_string(id));
                }
            }
            for (int e = 0; e < m.n_elems(); ++e) {
                const auto row = a["elem2edge"][e].as_int_vector();
                // Slot 3 of a triangle row is ignored (Python: padded or absent).
                const int nk = is_tri(m.elems[e]) ? 3 : std::min(4, ncols);
                for (int k = 0; k < nk; ++k) {
                    if (m.elem2edge[e][k] != row[k]) d_el2e.add("elem " + std::to_string(e));
                }
            }
            for (int v = 0; v < m.n_verts(); ++v) {
                if (m.vert2elem[v] != a["vert2elem"][v].as_int_vector()) {
                    d_v2e.add("vert " + std::to_string(v));
                }
            }
            INFO("conn first diff: " << d_conn.first);
            INFO("edge2vert first diff: " << d_e2v.first);
            INFO("edge2elem first diff: " << d_e2e.first);
            INFO("elem2edge first diff: " << d_el2e.first);
            INFO("vert2elem first diff: " << d_v2e.first);
            CHECK(d_conn.n == 0);
            CHECK(d_e2v.n == 0);
            CHECK(d_e2e.n == 0);
            CHECK(d_el2e.n == 0);
            CHECK(d_v2e.n == 0);
            CHECK(m.boundary_edges() == a["boundary_edges"].as_int_vector());
        }
    }
}
