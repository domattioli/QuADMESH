// SPEC-02 fort.14 reader and writer. Parsing mirrors CHILmesh.py
// read_from_fort14 (_read_fort14_points, _read_fort14_connectivity,
// _read_fort14_boundary_segments); the writer mirrors write_fort14 except
// that the boundary block is written back byte for byte (FR-004, R-06).
#include "quadmesh/fort14.hpp"

#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <string>
#include <system_error>
#include <vector>

#include "quadmesh/error.hpp"

namespace quadmesh {

namespace {

struct Line {
    std::size_t begin;  // byte offset of the line in the file
    std::string text;   // without the terminator and a trailing '\r'
};

std::vector<Line> split_lines(const std::string& data) {
    std::vector<Line> out;
    std::size_t pos = 0;
    while (pos < data.size()) {
        std::size_t nl = data.find('\n', pos);
        std::size_t end = nl == std::string::npos ? data.size() : nl;
        std::size_t tend = end;
        if (tend > pos && data[tend - 1] == '\r') --tend;
        out.push_back({pos, data.substr(pos, tend - pos)});
        pos = nl == std::string::npos ? data.size() : nl + 1;
    }
    return out;
}

std::vector<std::string> tokens(const std::string& s) {
    std::vector<std::string> t;
    std::istringstream is(s);
    std::string w;
    while (is >> w) t.push_back(w);
    return t;
}

// Python int(): optional sign and digits only.
bool parse_int(const std::string& s, long long& out) {
    if (s.empty()) return false;
    char* end = nullptr;
    errno = 0;
    out = std::strtoll(s.c_str(), &end, 10);
    return errno == 0 && end && *end == '\0';
}

bool parse_double(const std::string& s, double& out) {
    if (s.empty()) return false;
    char* end = nullptr;
    out = std::strtod(s.c_str(), &end);
    return end && *end == '\0';
}

struct Cursor {
    const std::vector<Line>& lines;
    const std::filesystem::path& path;
    std::size_t i = 0;
    const std::vector<std::string> next(const char* what) {
        if (i >= lines.size()) {
            throw ParseError(path.string() + ": unexpected end of file reading " + what);
        }
        return tokens(lines[i++].text);
    }
};

[[noreturn]] void bad(const std::filesystem::path& p, std::size_t line, const std::string& msg) {
    throw ParseError(p.string() + ":" + std::to_string(line) + ": " + msg);
}

int need_int(const std::vector<std::string>& t, std::size_t k, const std::filesystem::path& p,
             std::size_t line) {
    long long v;
    if (k >= t.size() || !parse_int(t[k], v)) bad(p, line, "expected an integer");
    return static_cast<int>(v);
}

// Lenient boundary parse: like Python, a short or malformed block keeps the
// segments read so far.
void parse_boundaries(const std::vector<Line>& lines, std::size_t i, Mesh& m) {
    auto first_int = [&](std::size_t k, long long& v) {
        if (k >= lines.size()) return false;
        auto t = tokens(lines[k].text);
        return !t.empty() && parse_int(t[0], v);
    };
    long long v = 0;
    if (!first_int(i, v)) return;
    const long long nope = v;
    ++i;
    if (!first_int(i, v)) return;
    ++i;
    m.boundaries_present = true;
    auto read_nodes = [&](long long n, BoundarySegment& seg) {
        for (long long k = 0; k < n; ++k) {
            long long node;
            if (!first_int(i, node)) return false;
            seg.nodes.push_back(static_cast<int>(node - 1));
            ++i;
        }
        return true;
    };
    for (long long s = 0; s < nope; ++s) {
        long long n;
        if (!first_int(i, n)) return;
        ++i;
        BoundarySegment seg{"open", std::nullopt, {}};
        if (!read_nodes(n, seg)) return;
        m.boundary_segments.push_back(std::move(seg));
    }
    long long nbou;
    if (!first_int(i, nbou)) return;
    ++i;
    if (!first_int(i, v)) return;
    ++i;
    for (long long s = 0; s < nbou; ++s) {
        if (i >= lines.size()) return;
        auto hdr = tokens(lines[i].text);
        long long n, ib;
        if (hdr.empty() || !parse_int(hdr[0], n)) return;
        BoundarySegment seg{"flow", std::nullopt, {}};
        if (hdr.size() > 1) {
            if (!parse_int(hdr[1], ib)) return;
            seg.ibtype = static_cast<int>(ib);
        }
        ++i;
        if (!read_nodes(n, seg)) return;
        m.boundary_segments.push_back(std::move(seg));
    }
}

}  // namespace

Mesh read_fort14(const std::filesystem::path& path, const MeshOptions& opts) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw InputError(path.string() + ": cannot open input file");
    std::string data((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
    if (in.bad()) throw InputError(path.string() + ": read error");

    const std::vector<Line> lines = split_lines(data);
    Cursor cur{lines, path};
    if (lines.empty()) bad(path, 1, "empty file");
    // Python str.strip(): leading and trailing whitespace.
    std::string name = lines[0].text;
    const char* ws = " \t\r\n\v\f";
    name.erase(0, name.find_first_not_of(ws));
    name.erase(name.find_last_not_of(ws) + 1);
    cur.i = 1;

    auto hdr = cur.next("the size header");
    const int n_elems = need_int(hdr, 0, path, cur.i);
    const int n_verts = need_int(hdr, 1, path, cur.i);
    if (n_elems < 0 || n_verts < 0) bad(path, cur.i, "negative element or node count");

    std::vector<Point> pts(n_verts);
    for (int j = 0; j < n_verts; ++j) {
        auto t = cur.next("node rows");
        if (t.size() < 3) bad(path, cur.i, "node row needs id, x, y");
        double x, y, z = 0.0;
        if (!parse_double(t[1], x) || !parse_double(t[2], y) ||
            (t.size() > 3 && !parse_double(t[3], z))) {
            bad(path, cur.i, "bad node coordinate");
        }
        pts[j] = {x, y, z};
    }

    std::vector<Elem> conn(n_elems);
    for (int j = 0; j < n_elems; ++j) {
        auto t = cur.next("element rows");
        need_int(t, 0, path, cur.i);
        const int nve = need_int(t, 1, path, cur.i);
        if (nve != 3 && nve != 4) bad(path, cur.i, "element must have 3 or 4 nodes");
        if (t.size() < static_cast<std::size_t>(2 + nve)) bad(path, cur.i, "short element row");
        Elem r{-1, -1, -1, -1};
        for (int k = 0; k < nve; ++k) {
            double d;  // Python int(float(x))
            if (!parse_double(t[2 + k], d)) bad(path, cur.i, "bad node id");
            const long long nid = static_cast<long long>(d);
            if (nid < 1 || nid > n_verts) {
                bad(path, cur.i, "node id " + std::to_string(nid) + " outside 1.." +
                                     std::to_string(n_verts));
            }
            r[k] = static_cast<int>(nid - 1);
        }
        conn[j] = r;
    }

    Mesh m(std::move(pts), std::move(conn), name, MeshOptions{false, false});
    const std::size_t bstart = cur.i < lines.size() ? lines[cur.i].begin : data.size();
    m.boundary_raw = data.substr(bstart);
    parse_boundaries(lines, cur.i, m);
    if (opts.compute_adjacencies || opts.compute_layers) m.build_adjacencies();
    if (opts.compute_layers) m.peel_layers();
    return m;
}

void write_fort14(const Mesh& mesh, const std::filesystem::path& path) {
    std::filesystem::path tmp = path;
    tmp += ".tmp";
    std::FILE* f = std::fopen(tmp.string().c_str(), "wb");
    if (!f) throw WriteError(path.string() + ": cannot open " + tmp.string() + " for writing");
    bool ok = true;
#define put(...)                                                \
    do {                                                        \
        if (ok && std::fprintf(f, __VA_ARGS__) < 0) ok = false; \
    } while (0)
    const std::string& name = mesh.grid_name.empty() ? std::string("CHILmesh") : mesh.grid_name;
    put("%s\n", name.c_str());
    put("%d %d\n", mesh.n_elems(), mesh.n_verts());
    for (int i = 0; i < mesh.n_verts(); ++i) {
        const Point& p = mesh.points[i];
        put("%d %.10f %.10f %.10f\n", i + 1, p[0], p[1], p[2]);
    }
    for (int i = 0; i < mesh.n_elems(); ++i) {
        const Elem& r = mesh.elems[i];
        if (is_tri(r)) {
            put("%d 3 %d %d %d\n", i + 1, r[0] + 1, r[1] + 1, r[2] + 1);
        } else {
            put("%d 4 %d %d %d %d\n", i + 1, r[0] + 1, r[1] + 1, r[2] + 1, r[3] + 1);
        }
    }
    if (!mesh.boundary_raw.empty()) {
        if (ok && std::fwrite(mesh.boundary_raw.data(), 1, mesh.boundary_raw.size(), f) !=
                      mesh.boundary_raw.size()) {
            ok = false;
        }
    } else {
        // Python _write_fort14_boundaries from parsed segments.
        std::size_t n_open = 0, n_flow = 0, tot_open = 0, tot_flow = 0;
        for (const auto& s : mesh.boundary_segments) {
            if (s.kind == "open") {
                ++n_open;
                tot_open += s.nodes.size();
            } else {
                ++n_flow;
                tot_flow += s.nodes.size();
            }
        }
        put("%zu\n%zu\n", n_open, tot_open);
        for (const auto& s : mesh.boundary_segments) {
            if (s.kind != "open") continue;
            put("%zu\n", s.nodes.size());
            for (int v : s.nodes) put("%d\n", v + 1);
        }
        put("%zu\n%zu\n", n_flow, tot_flow);
        for (const auto& s : mesh.boundary_segments) {
            if (s.kind == "open") continue;
            put("%zu", s.nodes.size());
            if (s.ibtype) put(" %d", *s.ibtype);
            put("\n");
            for (int v : s.nodes) put("%d\n", v + 1);
        }
    }
#undef put
    if (std::fclose(f) != 0) ok = false;
    std::error_code ec;
    if (ok) {
        std::filesystem::rename(tmp, path, ec);
        if (ec) ok = false;
    }
    if (!ok) {
        std::filesystem::remove(tmp, ec);
        throw WriteError(path.string() + ": write failed");
    }
}

}  // namespace quadmesh
