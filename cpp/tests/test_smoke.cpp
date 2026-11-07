#include <catch_amalgamated.hpp>

#include <Eigen/Dense>

#include "quadmesh/error.hpp"

TEST_CASE("smoke: test binary runs", "[smoke]") {
    SUCCEED();
}

TEST_CASE("smoke: InvalidMethod is a quadmesh::Error", "[smoke]") {
    REQUIRE_THROWS_AS(throw quadmesh::InvalidMethod("matching"), quadmesh::Error);
}

TEST_CASE("smoke: vendored Eigen compiles", "[smoke]") {
    Eigen::Vector2d v(3.0, 4.0);
    REQUIRE(v.norm() == 5.0);
}
