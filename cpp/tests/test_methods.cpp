// T039: method handling. "quadmesh+" is the default, "layered" is its
// alias; "matching", "faithful" and unknown names throw InvalidMethod.
#include <catch_amalgamated.hpp>

#include "quadmesh/error.hpp"
#include "t2q_oracle.hpp"

using namespace quadmesh;

namespace {
Mesh square() {
    return Mesh({{0, 0, 0}, {1, 0, 0}, {1, 1, 0}, {0, 1, 0}, {0.5, 0.5, 0}},
                {make_tri(0, 1, 4), make_tri(1, 2, 4), make_tri(2, 3, 4), make_tri(3, 0, 4)});
}
}  // namespace

TEST_CASE("default method is quadmesh+", "[tri2quad][methods]") {
    CHECK(Tri2QuadOptions{}.method == "quadmesh+");
}

TEST_CASE("layered equals quadmesh+", "[tri2quad][methods]") {
    const Mesh m = std::filesystem::exists(gt::mesh_path("Block_O")) ? t2q::input("Block_O") : square();
    Tri2QuadOptions a, b;
    b.method = "layered";
    const Mesh qa = tri2quad(m, a), qb = tri2quad(m, b);
    CHECK(qa.points == qb.points);
    CHECK(qa.elems == qb.elems);
}

TEST_CASE("removed and unknown methods throw InvalidMethod", "[tri2quad][methods]") {
    const Mesh m = square();
    for (const char* bad : {"matching", "faithful", "nope", ""}) {
        Tri2QuadOptions o;
        o.method = bad;
        CHECK_THROWS_AS(tri2quad(m, o), InvalidMethod);
    }
}

TEST_CASE("quad input is rejected", "[tri2quad][methods]") {
    const Mesh q({{0, 0, 0}, {1, 0, 0}, {1, 1, 0}, {0, 1, 0}}, {{0, 1, 2, 3}});
    CHECK_THROWS_AS(tri2quad(q), InputError);
}
