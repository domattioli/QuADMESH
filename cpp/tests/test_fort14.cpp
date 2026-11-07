// T017: fort.14 read against the oracle, write, re-read, boundary bytes.
// The C++ outputs land in QUADMESH_ROUNDTRIP_DIR; the ctest entry
// fort14_python_roundtrip then loads them with the Python reader
// (tests/fort14_roundtrip_check.py).
#include <catch_amalgamated.hpp>

#include <fstream>
#include <iterator>

#include "ground_truth.hpp"
#include "quadmesh/error.hpp"
#include "quadmesh/fort14.hpp"

using namespace quadmesh;

namespace {
std::filesystem::path out_dir() {
    if (const char* e = std::getenv("QUADMESH_ROUNDTRIP_DIR")) return e;
#ifdef QUADMESH_ROUNDTRIP_DIR_DEFAULT
    return QUADMESH_ROUNDTRIP_DIR_DEFAULT;
#else
    return std::filesystem::temp_directory_path() / "quadmesh_roundtrip";
#endif
}

std::string slurp(const std::filesystem::path& p) {
    std::ifstream in(p, std::ios::binary);
    return std::string((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
}
}  // namespace

TEST_CASE("fort14: missing input and failed write", "[fort14]") {
    REQUIRE_THROWS_AS(read_fort14("/nonexistent/dir/x.14"), InputError);
    Mesh m({{0, 0, 0}, {1, 0, 0}, {0, 1, 0}}, {make_tri(0, 1, 2)}, "t", {false, false});
    const auto bad = std::filesystem::path("/nonexistent/dir/out.14");
    REQUIRE_THROWS_AS(write_fort14(m, bad), WriteError);
    REQUIRE_FALSE(std::filesystem::exists(bad));
}

TEST_CASE("fort14: malformed input throws ParseError", "[fort14]") {
    const auto dir = out_dir();
    std::filesystem::create_directories(dir);
    const auto p = dir / "malformed.14";
    {
        std::ofstream f(p, std::ios::binary);
        f << "bad\n1 3\n1 0 0 0\n2 1 0 0\n3 0 1 0\n1 3 1 2 9\n";
    }
    REQUIRE_THROWS_AS(read_fort14(p), ParseError);
}

TEST_CASE("fort14: in-memory mesh gets the canonical empty boundary block", "[fort14]") {
    const auto dir = out_dir();
    std::filesystem::create_directories(dir);
    Mesh m({{0, 0, 0}, {1, 0, 0}, {0, 1, 0}, {1, 1, -0.0}},
           {make_tri(0, 1, 2), Elem{0, 1, 3, 2}}, "", {false, false});
    const auto p = dir / "inmem.14";
    write_fort14(m, p);
    REQUIRE(slurp(p) ==
            "CHILmesh\n2 4\n"
            "1 0.0000000000 0.0000000000 0.0000000000\n"
            "2 1.0000000000 0.0000000000 0.0000000000\n"
            "3 0.0000000000 1.0000000000 0.0000000000\n"
            "4 1.0000000000 1.0000000000 -0.0000000000\n"
            "1 3 1 2 3\n2 4 1 2 4 3\n0\n0\n0\n0\n");
    REQUIRE_FALSE(std::filesystem::exists(dir / "inmem.14.tmp"));
}

TEST_CASE("fort14 round trip per fixture", "[fort14][oracle]") {
    const auto dir = out_dir();
    std::filesystem::create_directories(dir);
    for (const std::string& name : gt::mesh_names()) {
        DYNAMIC_SECTION(name) {
            if (!gt::available(name)) SKIP("ground truth missing for " << name);
            const Mesh& m = gt::mesh(name);
            const auto& F = gt::ref(name)["fort14"];
            CHECK(m.grid_name == F["grid_name"].as_string());
            CHECK(m.boundaries_present == F["boundaries_present"].b);

            // Parsed arrays equal the Python reader's, exactly.
            std::size_t bad_pts = 0, bad_conn = 0;
            for (int v = 0; v < m.n_verts(); ++v) {
                const auto row = F["points"][v].as_double_vector();
                for (int k = 0; k < 3; ++k) bad_pts += m.points[v][k] == row[k] ? 0 : 1;
            }
            for (int e = 0; e < m.n_elems(); ++e) {
                const auto row = F["conn"][e].as_int_vector();
                for (int k = 0; k < n_corners(m.elems[e]); ++k) bad_conn += m.elems[e][k] == row[k] ? 0 : 1;
            }
            CHECK(bad_pts == 0);
            CHECK(bad_conn == 0);
            const auto& segs = F["boundary_segments"];
            REQUIRE(m.boundary_segments.size() == segs.size());
            for (std::size_t s = 0; s < segs.size(); ++s) {
                CHECK(m.boundary_segments[s].kind == segs[s]["kind"].as_string());
                CHECK(m.boundary_segments[s].nodes == segs[s]["nodes"].as_int_vector());
                if (segs[s]["ibtype"].is_null()) {
                    CHECK_FALSE(m.boundary_segments[s].ibtype.has_value());
                } else {
                    CHECK(m.boundary_segments[s].ibtype == segs[s]["ibtype"].as_int());
                }
            }

            // Write, then the boundary block is byte-identical to the input's.
            const auto out = dir / (name + ".cpp.14");
            write_fort14(m, out);
            const std::string in_bytes = slurp(gt::mesh_path(name));
            const std::string out_bytes = slurp(out);
            REQUIRE(m.boundary_raw.size() <= in_bytes.size());
            CHECK(in_bytes.compare(in_bytes.size() - m.boundary_raw.size(), std::string::npos,
                                   m.boundary_raw) == 0);
            REQUIRE(out_bytes.size() >= m.boundary_raw.size());
            CHECK(out_bytes.compare(out_bytes.size() - m.boundary_raw.size(), std::string::npos,
                                    m.boundary_raw) == 0);

            // C++ re-read: same connectivity and boundary, points to .10f.
            const Mesh back = read_fort14(out, {false, false});
            CHECK(back.elems == m.elems);
            CHECK(back.boundary_raw == m.boundary_raw);
            CHECK(back.grid_name == m.grid_name);
            std::size_t far = 0;
            for (int v = 0; v < m.n_verts(); ++v) {
                for (int k = 0; k < 3; ++k) {
                    const double x = m.points[v][k];
                    far += std::fabs(back.points[v][k] - x) <= 5.1e-11 + 4e-16 * std::fabs(x) ? 0 : 1;
                }
            }
            CHECK(far == 0);
        }
    }
}
