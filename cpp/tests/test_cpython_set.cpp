// cpython_set_order against real CPython output
// (.scratch/cpp-port/ground_truth/set_order.json from set_order_ref.py).
#include <catch_amalgamated.hpp>

#include "ground_truth.hpp"
#include "quadmesh/cpython_set.hpp"

using namespace quadmesh;

TEST_CASE("cpython_set_order: hand cases", "[post][cpython_set]") {
    CHECK(cpython_set_order({3, 5}) == std::vector<int>{3, 5});
    CHECK(cpython_set_order({5, 9}) == std::vector<int>{9, 5});   // 9 & 7 = 1
    CHECK(cpython_set_order({1, 9}) == std::vector<int>{1, 9});   // collision, probe to 6
}

TEST_CASE("cpython_set_order matches CPython", "[post][cpython_set]") {
    const auto path = gt::dir() / "set_order.json";
    if (!std::filesystem::exists(path)) {
        WARN("skip: run set_order_ref.py");
        return;
    }
    const auto doc = json::parse_file(path);
    const auto& cases = doc["cases"];
    std::size_t bad = 0;
    for (std::size_t i = 0; i < cases.size(); ++i) {
        const auto got = cpython_set_order(cases[i][0].as_int_vector());
        if (got != cases[i][1].as_int_vector()) ++bad;
    }
    CHECK(cases.size() > 1000);
    CHECK(bad == 0);
}
