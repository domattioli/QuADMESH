// T019: skew stats to 6 significant digits against the oracle.
#include <catch_amalgamated.hpp>

#include <cmath>

#include "ground_truth.hpp"
#include "quadmesh/quality.hpp"

using namespace quadmesh;

namespace {
bool sig6(double a, double b) {
    if (a == b) return true;
    const double scale = std::max(std::fabs(a), std::fabs(b));
    return std::fabs(a - b) <= 5e-7 * scale;
}
}  // namespace

TEST_CASE("skew: ideal, concave and degenerate elements", "[quality]") {
    const double h = std::sqrt(3.0) / 2.0;
    std::vector<Point> p = {{0, 0, 0}, {1, 0, 0}, {0.5, h, 0}, {2, 0, 0}};
    auto q = element_skew(p, {make_tri(0, 1, 2), make_tri(0, 1, 3)});
    REQUIRE(q[0] == Catch::Approx(1.0).margin(1e-9));
    REQUIRE(q[1] == 0.0);  // collinear

    std::vector<Point> s = {{0, 0, 0}, {1, 0, 0}, {1, 1, 0}, {0, 1, 0}};
    REQUIRE(element_skew(s, {Elem{0, 1, 2, 3}})[0] == Catch::Approx(1.0).margin(1e-9));
    // Concave quad (CHILmesh docstring example): skew 0, counted concave.
    std::vector<Point> c = {{0, 0, 0}, {2, 0, 0}, {0.8, 0.5, 0}, {0, 2, 0}};
    REQUIRE(element_skew(c, {Elem{0, 1, 2, 3}})[0] == 0.0);
    REQUIRE(count_concave_quads(c, {Elem{0, 1, 2, 3}}) == 1);
    REQUIRE(count_concave_quads(s, {Elem{0, 1, 2, 3}, make_tri(0, 1, 2)}) == 0);
}

TEST_CASE("quality stats match the oracle", "[quality][oracle]") {
    for (const std::string& name : gt::mesh_names()) {
        DYNAMIC_SECTION(name) {
            if (!gt::available(name)) SKIP("ground truth missing for " << name);
            const Mesh& m = gt::mesh(name);
            const auto& Q = gt::ref(name)["quality"];
            const QualityStats s = compute_quality_stats(m);
            INFO("mean " << s.mean << " vs " << Q["mean"].as_double());
            CHECK(sig6(s.mean, Q["mean"].as_double()));
            CHECK(sig6(s.min, Q["min"].as_double()));
            CHECK(sig6(s.max, Q["max"].as_double()));
            CHECK(sig6(s.std, Q["std"].as_double()));
            CHECK(s.n_bad == Q["n_bad"].as_int());
            CHECK(s.n_concave == Q["n_concave"].as_int());

            const auto per = Q["per_elem"].as_double_vector();
            const auto q = element_skew(m.points, m.elems);
            REQUIRE(q.size() == per.size());
            std::size_t bad = 0;
            for (std::size_t i = 0; i < q.size(); ++i) bad += sig6(q[i], per[i]) ? 0 : 1;
            CHECK(bad == 0);
        }
    }
}
