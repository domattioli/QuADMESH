// T023: layer peel, outer-vertex paths and priority against the oracle.
#include <catch_amalgamated.hpp>

#include "ground_truth.hpp"
#include "quadmesh/mesh.hpp"

using namespace quadmesh;

namespace {
std::size_t list_diffs(const std::vector<std::vector<int>>& got, const quadmesh::json::Value& want,
                       std::string& first, const char* what) {
    std::size_t n = 0;
    const std::size_t nl = std::max(got.size(), want.size());
    for (std::size_t li = 0; li < nl; ++li) {
        const bool ok = li < got.size() && li < want.size() && got[li] == want[li].as_int_vector();
        if (!ok && n++ == 0) first = std::string(what) + " layer " + std::to_string(li);
    }
    return n;
}
}  // namespace

TEST_CASE("layers match the CHILmesh oracle", "[layers][oracle]") {
    for (const std::string& name : gt::mesh_names()) {
        DYNAMIC_SECTION(name) {
            if (!gt::available(name)) SKIP("ground truth missing for " << name);
            const Mesh& m = gt::mesh(name);
            const auto& L = gt::ref(name)["layers"];
            REQUIRE(m.n_layers() == L["n_layers"].as_int());
            std::string first;
            CHECK(list_diffs(m.layers.OE, L["OE"], first, "OE") == 0);
            CHECK(list_diffs(m.layers.IE, L["IE"], first, "IE") == 0);
            CHECK(list_diffs(m.layers.OV, L["OV"], first, "OV") == 0);
            CHECK(list_diffs(m.layers.IV, L["IV"], first, "IV") == 0);
            CHECK(list_diffs(m.layers.bEdgeIDs, L["bEdgeIDs"], first, "bEdgeIDs") == 0);
            INFO("first layer diff: " << first);
            CHECK(first.empty());

            CHECK(layer_priority(m, m.n_elems()) == gt::ref(name)["priority"].as_int_vector());

            std::size_t bad_paths = 0;
            for (int li = 0; li < m.n_layers(); ++li) {
                const auto got = paths_on_outer_vertices(m, li);
                const auto& want = L["paths"][li];
                bool ok = got.size() == want.size();
                for (std::size_t k = 0; ok && k < got.size(); ++k) ok = got[k] == want[k].as_int_vector();
                if (!ok) {
                    ++bad_paths;
                    UNSCOPED_INFO("paths differ on layer " << li);
                }
            }
            CHECK(bad_paths == 0);
        }
    }
}
