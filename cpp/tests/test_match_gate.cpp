// T037: match-stage gate (hard rule). tri2quad with remove_boundary_tris=false
// leaves zero interior residual triangles on every fixture.
#include <catch_amalgamated.hpp>

#include "t2q_oracle.hpp"

using namespace quadmesh;

TEST_CASE("match stage leaves zero interior residual triangles", "[tri2quad][gate]") {
    for (const std::string& name : gt::mesh_names()) {
        DYNAMIC_SECTION(name) {
            if (!std::filesystem::exists(gt::mesh_path(name))) SKIP("mesh missing: " << name);
            const auto& r = t2q::run(name, "match");
            INFO(name << ": elems " << r.out.n_elems() << " verts " << r.out.n_verts() << " tris "
                      << t2q::n_tris(r.out));
            CHECK(t2q::interior_residual_tris(r.out) == 0);
            if (t2q::has_expected(name, "match")) {
                const auto& w = t2q::expected(name, "match");
                CHECK(t2q::n_tris(r.out) == w["counts"]["out_tris"].as_int());
                CHECK(r.out.n_elems() == w["n_elems"].as_int());
                CHECK(r.out.n_verts() == w["n_verts"].as_int());
                CHECK(r.trace.inserted_points.size() == w["inserted_points"].size());
            }
        }
    }
}
