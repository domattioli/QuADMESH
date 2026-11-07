// SPEC-10b dump driver: runs the C++ conversion for stages match/core/full
// and writes <mesh>.<stage>.json and <mesh>.<stage>.14 (contracts/dump-format.md).
//   dump_driver --out DIR [--in DIR] [--mesh NAME]... [--stage S]...
// Mirrors the oracle stage calls (ground_truth/DUMP_NOTES.md):
//   match = tri2quad(can_remove_edges, remove_boundary_tris=false), no post
//   core  = tri2quad defaults, no post-process
//   full  = tri2quad defaults, then post_process defaults
// The tri2quad / tie log headers are written by other work items; without
// them this tool compiles and reports "not built".
#include <chrono>
#include <cmath>
#include <array>
#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include "quadmesh/error.hpp"
#include "quadmesh/fort14.hpp"
#include "quadmesh/mesh.hpp"
#include "quadmesh/quality.hpp"

#if __has_include("quadmesh/tri2quad.hpp") && __has_include("quadmesh/post_process.hpp")
#include "quadmesh/post_process.hpp"
#include "quadmesh/tri2quad.hpp"
#define QUADMESH_DUMP_BUILT 1
#endif

namespace fs = std::filesystem;
using namespace quadmesh;

#ifndef QUADMESH_DUMP_BUILT
int main() {
    std::cerr << "dump_driver: not built (quadmesh/tri2quad.hpp or post_process.hpp missing at compile time)\n";
    return 3;
}
#else

namespace {

// ---------------------------------------------------------------- SHA-256
struct Sha256 {
    uint32_t h[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
    static uint32_t rotr(uint32_t x, int n) { return (x >> n) | (x << (32 - n)); }
    void block(const uint8_t* p) {
        static const uint32_t K[64] = {
            0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
            0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
            0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
            0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
            0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
            0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
            0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
            0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2};
        uint32_t w[64];
        for (int i = 0; i < 16; ++i)
            w[i] = (uint32_t(p[4 * i]) << 24) | (uint32_t(p[4 * i + 1]) << 16) | (uint32_t(p[4 * i + 2]) << 8) | p[4 * i + 3];
        for (int i = 16; i < 64; ++i) {
            uint32_t s0 = rotr(w[i - 15], 7) ^ rotr(w[i - 15], 18) ^ (w[i - 15] >> 3);
            uint32_t s1 = rotr(w[i - 2], 17) ^ rotr(w[i - 2], 19) ^ (w[i - 2] >> 10);
            w[i] = w[i - 16] + s0 + w[i - 7] + s1;
        }
        uint32_t a = h[0], b = h[1], c = h[2], d = h[3], e = h[4], f = h[5], g = h[6], hh = h[7];
        for (int i = 0; i < 64; ++i) {
            uint32_t t1 = hh + (rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i];
            uint32_t t2 = (rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)) + ((a & b) ^ (a & c) ^ (b & c));
            hh = g; g = f; f = e; e = d + t1; d = c; c = b; b = a; a = t1 + t2;
        }
        h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
    }
    static std::string hex(const std::string& data) {
        Sha256 s;
        std::string m = data;
        uint64_t bits = uint64_t(data.size()) * 8;
        m.push_back(char(0x80));
        while (m.size() % 64 != 56) m.push_back(0);
        for (int i = 7; i >= 0; --i) m.push_back(char((bits >> (8 * i)) & 0xff));
        for (std::size_t i = 0; i < m.size(); i += 64) s.block(reinterpret_cast<const uint8_t*>(m.data()) + i);
        char buf[65];
        for (int i = 0; i < 8; ++i) std::snprintf(buf + 8 * i, 9, "%08x", s.h[i]);
        return std::string(buf, 64);
    }
};

std::string fnum(double v) {
    char b[40];
    std::snprintf(b, sizeof b, "%.17g", v);
    return b;
}

template <class T>
void int_list(std::ostream& o, const T& v) {
    o << "[";
    bool first = true;
    for (auto x : v) { o << (first ? "" : ", ") << x; first = false; }
    o << "]";
}
template <class T>
void int_matrix(std::ostream& o, const T& m) {
    o << "[";
    bool first = true;
    for (const auto& r : m) { o << (first ? "" : ", "); int_list(o, r); first = false; }
    o << "]";
}

// FR-020 item 1/2 counters on an output mesh (adjacencies rebuilt here).
struct TriCounts { int residual = 0, geometric = 0; };

TriCounts count_interior_tris(const Mesh& out) {
    Mesh m = out;
    m.build_adjacencies();
    TriCounts c;
    for (int e = 0; e < m.n_elems(); ++e) {
        const Elem& row = m.elems[static_cast<std::size_t>(e)];
        const int n = n_corners(row);
        bool boundary = false;
        for (int k = 0; k < n; ++k) {
            int ed = m.elem2edge[static_cast<std::size_t>(e)][static_cast<std::size_t>(k)];
            if (ed >= 0 && m.edge2elem[static_cast<std::size_t>(ed)][1] == -1) boundary = true;
        }
        if (boundary) continue;
        if (n == 3) {
            if (row[0] != row[1] && row[1] != row[2] && row[0] != row[2]) ++c.residual;
            continue;
        }
        bool distinct = true;
        for (int i = 0; i < 4; ++i)
            for (int j = i + 1; j < 4; ++j) distinct = distinct && row[i] != row[j];
        if (!distinct) continue;
        bool geo = false;
        for (int k = 0; k < 4; ++k) {
            const Point& p = m.points[static_cast<std::size_t>(row[k])];
            const Point& a = m.points[static_cast<std::size_t>(row[(k + 3) % 4])];
            const Point& b = m.points[static_cast<std::size_t>(row[(k + 1) % 4])];
            double ux = a[0] - p[0], uy = a[1] - p[1], vx = b[0] - p[0], vy = b[1] - p[1];
            double lu = std::hypot(ux, uy), lv = std::hypot(vx, vy);
            if (lu < 1e-12 || lv < 1e-12) { geo = true; break; }
            double ang = std::atan2(std::fabs(ux * vy - uy * vx), ux * vx + uy * vy) * 180.0 / M_PI;
            if (ang >= 178.0) { geo = true; break; }
        }
        if (geo) ++c.geometric;
    }
    return c;
}

Mesh run_stage(const Mesh& in, const std::string& stage, TieLog& ties, Tri2QuadTrace& trace) {
    ties.clear();
    trace = Tri2QuadTrace{};
    Tri2QuadOptions o;
    if (stage == "match") o.remove_boundary_tris = false;
    o.tie_log = &ties;
    Mesh q = tri2quad(in, o, &trace);
    if (stage == "full") q = post_process(q, PostProcessOptions{});
    return q;
}

void int_pairs(std::ostream& o, const std::vector<std::array<int, 2>>& v) {
    o << "[";
    for (std::size_t i = 0; i < v.size(); ++i) o << (i ? ", " : "") << "[" << v[i][0] << ", " << v[i][1] << "]";
    o << "]";
}

void write_dump(const Mesh& in, const Mesh& out, const TieLog& ties, const Tri2QuadTrace& trace, const std::string& mesh, const std::string& stage,
                const std::array<double, 3>& times, const fs::path& dir) {
    fs::path f14 = dir / (mesh + "." + stage + ".14");
    write_fort14(out, f14);
    std::string bytes;
    {
        std::ifstream f(f14, std::ios::binary);
        std::ostringstream s;
        s << f.rdbuf();
        bytes = s.str();
    }
    QualityStats q = compute_quality_stats(out);
    TriCounts tc = count_interior_tris(out);
    const char* commit = std::getenv("QUADMESH_COMMIT");
    std::ostringstream o;
    o << "{\n  \"mesh\": \"" << mesh << "\", \"stage\": \"" << stage << "\",\n"
      << "  \"quadmesh_commit\": \"" << (commit ? commit : "unknown") << "\", \"chilmesh_version\": \"cpp\", \"chilmesh_backend\": \"cpp\",\n"
      << "  \"n_elems\": " << out.n_elems() << ", \"n_verts\": " << out.n_verts() << ",\n"
      << "  \"n_interior_residual_tris\": " << tc.residual << ", \"n_interior_geometric_tris\": " << tc.geometric << ",\n"
      << "  \"quality\": {\"mean\": " << fnum(q.mean) << ", \"min\": " << fnum(q.min) << ", \"max\": " << fnum(q.max)
      << ", \"std\": " << fnum(q.std) << ", \"n_bad\": " << q.n_bad << ", \"n_concave\": " << q.n_concave << "},\n"
      << "  \"sha256_14\": \"" << Sha256::hex(bytes) << "\",\n"
      << "  \"time_s\": [" << fnum(times[0]) << ", " << fnum(times[1]) << ", " << fnum(times[2]) << "]";
    if (stage != "full") {
        // Adjacency, layers and layer_priority describe the input mesh (DUMP_NOTES.md).
        o << ",\n  \"adjacency\": {\"edge2vert\": ";
        int_matrix(o, in.edge2vert);
        o << ", \"edge2elem\": ";
        int_matrix(o, in.edge2elem);
        o << ", \"elem2edge\": ";
        int_matrix(o, in.elem2edge);
        o << ", \"vert2elem\": ";
        int_matrix(o, in.vert2elem);
        o << "},\n  \"layers\": [";
        for (int li = 0; li < in.n_layers(); ++li) {
            const auto l = static_cast<std::size_t>(li);
            o << (li ? ", " : "") << "{\"IE\": "; int_list(o, in.layers.IE[l]);
            o << ", \"OE\": "; int_list(o, in.layers.OE[l]);
            o << ", \"OV\": "; int_list(o, in.layers.OV[l]);
            o << ", \"IV\": "; int_list(o, in.layers.IV[l]);
            o << "}";
        }
        o << "],\n  \"layer_priority\": ";
        int_list(o, layer_priority(in, in.n_elems()));
        o << ",\n  \"per_layer\": [";
        for (std::size_t k = 0; k < trace.per_layer.size(); ++k) {
            const LayerTrace& t = trace.per_layer[k];
            o << (k ? ", " : "") << "{\"layer\": " << t.layer << ", \"status\": \"" << t.status << "\", \"removed_edges\": ";
            int_pairs(o, t.removed_edges);
            o << ", \"flagged_pairs\": ";
            int_pairs(o, t.flagged_pairs);
            o << ", \"pairs\": ";
            int_pairs(o, t.pairs);
            o << ", \"leftover\": ";
            int_list(o, t.leftover);
            o << "}";
        }
        o << "],\n  \"inserted_points\": [";
        for (std::size_t k = 0; k < trace.inserted_points.size(); ++k) {
            const Point& p = trace.inserted_points[k];
            o << (k ? ", " : "") << "[" << fnum(p[0]) << ", " << fnum(p[1]) << ", " << fnum(p[2]) << "]";
        }
        o << "]";
    }
    o << ",\n  \"tie_log\": " << ties.to_json();
    o << "\n}\n";
    std::ofstream(dir / (mesh + "." + stage + ".json")) << o.str();
}

}  // namespace

int main(int argc, char** argv) {
    fs::path in_dir = ".scratch/cpp-port/ground_truth/meshes", out_dir;
    std::vector<std::string> meshes, stages;
    for (int i = 1; i < argc; ++i) {
        std::string a = argv[i];
        if (i + 1 >= argc) { std::cerr << "dump_driver: bad argument " << a << "\n"; return 2; }
        std::string v = argv[++i];
        if (a == "--out") out_dir = v;
        else if (a == "--in") in_dir = v;
        else if (a == "--mesh") meshes.push_back(v);
        else if (a == "--stage") stages.push_back(v);
        else { std::cerr << "dump_driver: unknown argument " << a << "\n"; return 2; }
    }
    if (out_dir.empty()) { std::cerr << "usage: dump_driver --out DIR [--in DIR] [--mesh NAME]... [--stage S]...\n"; return 2; }
    if (stages.empty()) stages = {"match", "core", "full"};
    if (meshes.empty()) meshes = {"Block_O", "WNAT_Test", "Lake_Michigan_mesh", "structuredMesh1"};
    fs::create_directories(out_dir);
    int rc = 0;
    for (const auto& m : meshes) {
        try {
            Mesh in = read_fort14(in_dir / (m + ".14"));
            for (const auto& s : stages) {
                std::array<double, 3> t{};
                Mesh out;
                TieLog ties;
                Tri2QuadTrace trace;
                for (int run = 0; run < 3; ++run) {
                    auto t0 = std::chrono::steady_clock::now();
                    out = run_stage(in, s, ties, trace);
                    t[static_cast<std::size_t>(run)] = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
                }
                write_dump(in, out, ties, trace, m, s, t, out_dir);
                std::cout << "wrote " << m << "." << s << "\n";
            }
        } catch (const std::exception& e) {
            std::cerr << "dump_driver: " << m << ": " << e.what() << "\n";
            rc = 1;
        }
    }
    return rc;
}
#endif
