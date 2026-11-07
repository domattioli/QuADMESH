// T045: post-process against the Python oracle.
// Input: expected/<mesh>.core.14 (Python core stage). Reference:
// post_ref/<mesh>.json written by .scratch/cpp-port/ground_truth/post_ref.py
// (Python post_process_routine on the same core mesh), plus
// expected/<mesh>.full.json (in-memory Python full pipeline).
#include <catch_amalgamated.hpp>

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <map>
#include <set>
#include <type_traits>

#include "ground_truth.hpp"
#include "quadmesh/post_process.hpp"
#include "quadmesh/quality.hpp"

using namespace quadmesh;

namespace {

const std::vector<std::string> kMeshes = {"Block_O", "WNAT_Test", "Lake_Michigan_mesh"};

std::filesystem::path core_path(const std::string& m) { return gt::dir() / "expected" / (m + ".core.14"); }
// ".sorted" = Python with ascending get_vertex_elements (the ADR 0001 tie rule).
std::filesystem::path ref_path(const std::string& m, const std::string& tag = "") {
    return gt::dir() / "post_ref" / (m + tag + ".json");
}
std::filesystem::path full_path(const std::string& m) { return gt::dir() / "expected" / (m + ".full.json"); }

const json::Value& ref(const std::string& m, const std::string& tag = "") {
    static std::map<std::string, json::Value> cache;
    auto it = cache.find(m + tag);
    if (it == cache.end()) it = cache.emplace(m + tag, json::parse_file(ref_path(m, tag))).first;
    return it->second;
}

// C++ post_process of each core mesh, with every step's boundary checked.
struct Run {
    Mesh out;
    Mesh smoothed;  // fem_smoother output, before fix_bowties
    std::size_t steps = 0;
    std::size_t moved_boundary = 0;  // boundary vertices whose xy is not an input xy
    std::string first_bad;
    std::size_t fem_moved = 0;       // boundary verts moved by a fem pass (by index)
};

const Run& run(const std::string& m) {
    static std::map<std::string, Run> cache;
    auto it = cache.find(m);
    if (it != cache.end()) return it->second;
    Run r;
    const Mesh in = read_fort14(core_path(m), MeshOptions{true, false});
    std::set<std::pair<double, double>> input_xy;
    for (const Point& p : in.points) input_xy.insert({p[0], p[1]});
    Mesh pre_fem, last;
    PostProcessOptions o;
    o.on_step = [&](const std::string& name, const Mesh& s) {
        ++r.steps;
        REQUIRE_FALSE(s.has_layers());
        if (name == "fix_bowties") {
            // Reorders rows only (a reordered row can expose an interior
            // vertex as boundary); no coordinate may change.
            for (int v = 0; v < s.n_verts(); ++v)
                if (s.points[v] != last.points[v]) ++r.moved_boundary;
            return;
        }
        last = s;
        if (name == "fem_smoother") r.smoothed = s;
        for (int v : s.boundary_node_indices()) {
            if (!input_xy.count({s.points[v][0], s.points[v][1]})) {
                if (r.moved_boundary++ == 0) r.first_bad = name + " v" + std::to_string(v);
            }
        }
        if (name == "cleanup_boundary_quads" || name == "quad_vertex_merge") pre_fem = s;
        if (name == "fem_pass") {
            // pre_fem may still hold unused vertices; compare via remove_unused.
            const Mesh before = remove_unused(pre_fem, MeshOptions{true, false});
            for (int v : before.boundary_node_indices())
                if (before.points[v][0] != s.points[v][0] || before.points[v][1] != s.points[v][1])
                    ++r.fem_moved;
        }
    };
    r.out = post_process(in, o);
    return cache.emplace(m, std::move(r)).first->second;
}

bool within(double a, double b, double rel) { return std::fabs(a - b) <= rel * std::max(std::fabs(b), 1.0); }

// Elements equal up to cyclic rotation (fix_bowties hull start may rotate).
bool same_cycle(const Elem& a, const Elem& b) {
    if (is_tri(a) != is_tri(b)) return false;
    const int n = n_corners(a);
    for (int s = 0; s < n; ++s) {
        bool ok = true;
        for (int k = 0; k < n && ok; ++k) ok = a[(k + s) % n] == b[k];
        if (ok) return true;
    }
    return false;
}

}  // namespace

TEST_CASE("post_process API takes no layer input (FR-007)", "[post]") {
    STATIC_REQUIRE(std::is_same_v<decltype(&quadmesh::post_process),
                                  Mesh (*)(const Mesh&, const PostProcessOptions&)>);
    // A unit square split into two quads plus a valence-2 doublet: works
    // without layers and returns a mesh without layers.
    std::vector<Point> p = {{0, 0, 0}, {2, 0, 0}, {2, 2, 0}, {0, 2, 0}, {1, 1, 0}};
    Mesh m(p, {Elem{0, 1, 2, 4}, Elem{0, 4, 2, 3}}, "doublet", MeshOptions{true, false});
    REQUIRE_FALSE(m.has_layers());
    Mesh out = post_process(m);
    CHECK_FALSE(out.has_layers());
    CHECK(out.has_adjacencies());
    // Vertex 4 is interior with valence 2: the doublet collapses to one quad.
    CHECK(out.n_elems() == 1);
    CHECK(out.n_verts() == 4);
    for (int v : out.boundary_node_indices()) {
        bool found = false;
        for (const Point& q : p) found = found || (q[0] == out.points[v][0] && q[1] == out.points[v][1]);
        CHECK(found);
    }
}

TEST_CASE("doublet_collapse merges an interior valence-2 pair", "[post]") {
    // 3x3 grid of quads with the centre quad split by a valence-2 vertex.
    std::vector<Point> p;
    for (int j = 0; j < 4; ++j)
        for (int i = 0; i < 4; ++i) p.push_back({double(i), double(j), 0});
    p.push_back({1.5, 1.5, 0});  // 16: doublet vertex inside quad 5-6-10-9
    auto q = [](int a, int b, int c, int d) { return Elem{a, b, c, d}; };
    std::vector<Elem> e = {q(0, 1, 5, 4), q(1, 2, 6, 5), q(2, 3, 7, 6), q(4, 5, 9, 8),
                           q(5, 6, 10, 16), q(5, 16, 10, 9), q(6, 7, 11, 10), q(8, 9, 13, 12),
                           q(9, 10, 14, 13), q(10, 11, 15, 14)};
    Mesh m(p, e, "grid", MeshOptions{true, false});
    TieLog log;
    Mesh out = doublet_collapse(m, &log);
    CHECK(out.n_elems() == 9);
    CHECK(out.n_verts() == 16);
    REQUIRE(log.size() == 1);
    CHECK(log.records()[0].py_site == "doublet_collapse.py:43");
}

TEST_CASE("fem_smoother never moves boundary vertices", "[post]") {
    for (const auto& name : kMeshes) {
        if (!std::filesystem::exists(ref_path(name))) {
            WARN("skip " << name << ": run post_ref.py");
            continue;
        }
        const auto& pre = ref(name)["pre_smooth"];
        std::vector<Point> pts;
        for (std::size_t i = 0; i < pre["points"].size(); ++i)
            pts.push_back({pre["points"][i][0].as_double(), pre["points"][i][1].as_double(), 0.0});
        std::vector<Elem> el;
        for (const auto& r : pre["elems"].as_int_matrix()) el.push_back({r[0], r[1], r[2], r[3]});
        Mesh m(pts, el, name, MeshOptions{true, false});
        int passes = 0;
        std::size_t moved = 0;
        const std::vector<int> b = m.boundary_node_indices();
        Mesh out = fem_smoother(m, 3, [&](const Mesh& s) {
            ++passes;
            for (int v : b) moved += (s.points[v][0] != pts[v][0] || s.points[v][1] != pts[v][1]);
        });
        CHECK(passes == 1);  // #107 short circuit
        CHECK(moved == 0);
        for (int v : b) {
            CHECK(out.points[v][0] == pts[v][0]);
            CHECK(out.points[v][1] == pts[v][1]);
        }
        // Same topology as Python: interior coordinates within 1e-9.
        const auto& fin = ref(name)["final"];
        REQUIRE(static_cast<int>(fin["points"].size()) == out.n_verts());
        double worst = 0.0;
        for (int v = 0; v < out.n_verts(); ++v)
            for (int d = 0; d < 2; ++d)
                worst = std::max(worst, std::fabs(out.points[v][d] - fin["points"][v][d].as_double()));
        std::printf("[post] %s fem on Python pre-smooth mesh: max |dxy| = %.3e\n", name.c_str(), worst);
        CHECK(worst <= 1e-9);
    }
}

TEST_CASE("post_process matches the Python oracle exactly (CPython set-order ties)", "[post]") {
    for (const auto& name : kMeshes) {
        if (!std::filesystem::exists(core_path(name)) || !std::filesystem::exists(ref_path(name))) {
            WARN("skip " << name << ": ground truth or post_ref missing");
            continue;
        }
        const Run& r = run(name);
        INFO(name);
        // Boundary vertices bit-identical through every step (SC-003).
        CHECK(r.steps > 0);
        INFO("first moved boundary vertex: " << r.first_bad);
        CHECK(r.moved_boundary == 0);
        CHECK(r.fem_moved == 0);

        const auto& fin = ref(name)["final"];
        const int py_e = static_cast<int>(fin["n_elems"].as_int());
        const int py_v = static_cast<int>(fin["n_verts"].as_int());
        REQUIRE(py_e == r.out.n_elems());
        REQUIRE(py_v == r.out.n_verts());
        const auto pe = fin["elems"].as_int_matrix();
        std::size_t elem_diff = 0, rot_only = 0;
        for (int e = 0; e < py_e; ++e) {
            Elem b{pe[e][0], pe[e][1], pe[e][2], pe[e][3]};
            if (r.out.elems[e] != b) ++(same_cycle(r.out.elems[e], b) ? rot_only : elem_diff);
        }
        std::vector<char> isb(py_v, 0);
        // Boundary as the smoother saw it (fix_bowties can expose a smoothed
        // interior vertex on a reordered row; same vertex ids).
        for (int v : r.smoothed.boundary_node_indices()) isb[v] = 1;
        std::size_t bnd_diff = 0;
        double worst = 0.0;
        for (int v = 0; v < py_v; ++v) {
            const double x = fin["points"][v][0].as_double(), y = fin["points"][v][1].as_double();
            if (isb[v]) bnd_diff += (r.out.points[v][0] != x || r.out.points[v][1] != y);
            else worst = std::max({worst, std::fabs(r.out.points[v][0] - x), std::fabs(r.out.points[v][1] - y)});
        }
        std::printf("[post] %s vs Python: %d elems %d verts; rows differing %zu "
                    "(+%zu rotated only); boundary xy differing %zu; interior max |dxy| %.3e\n",
                    name.c_str(), py_e, py_v, elem_diff, rot_only, bnd_diff, worst);
        CHECK(elem_diff == 0);
        CHECK(bnd_diff == 0);
        CHECK(worst <= 1e-9);
    }
}

TEST_CASE("post_process counts within 0.5% of Python (set-order ties)", "[post]") {
    for (const auto& name : kMeshes) {
        if (!std::filesystem::exists(core_path(name)) || !std::filesystem::exists(ref_path(name))) {
            WARN("skip " << name << ": ground truth or post_ref missing");
            continue;
        }
        const Run& r = run(name);
        INFO(name);
        const auto& fin = ref(name)["final"];
        const double py_e = fin["n_elems"].as_double(), py_v = fin["n_verts"].as_double();
        CHECK(within(r.out.n_elems(), py_e, 0.005));
        CHECK(within(r.out.n_verts(), py_v, 0.005));
        const auto full = json::parse_file(full_path(name));
        CHECK(within(r.out.n_elems(), full["n_elems"].as_double(), 0.005));
        CHECK(within(r.out.n_verts(), full["n_verts"].as_double(), 0.005));
        const QualityStats q = compute_quality_stats(r.out);
        const auto& fq = full["quality"];
        std::printf("[post] %s: C++ %d/%d, Python(core.14) %.0f/%.0f, full.json %lld/%lld elems/verts; "
                    "skew mean %.6f (full.json %.6f) min %.4f (%.4f) n_bad %d (%lld) n_concave %d (%lld)\n",
                    name.c_str(), r.out.n_elems(), r.out.n_verts(), py_e, py_v, full["n_elems"].as_int(),
                    full["n_verts"].as_int(), q.mean, fq["mean"].as_double(), q.min, fq["min"].as_double(),
                    q.n_bad, fq["n_bad"].as_int(), q.n_concave, fq["n_concave"].as_int());
    }
}
