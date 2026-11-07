#pragma once
// Shared helpers for the tri2quad oracle tests (T029, T031, T034, T037, T038).
// Expected files: <gt dir>/expected/<mesh>.{match,core,full}.json (dump.py).
#include <cmath>
#include <map>
#include <sstream>
#include <string>

#include "ground_truth.hpp"
#include "quadmesh/tri2quad.hpp"
#include "quadmesh/tri2quad_detail.hpp"

namespace t2q {

inline std::filesystem::path expected_path(const std::string& name, const std::string& stage) {
    return gt::dir() / "expected" / (name + "." + stage + ".json");
}
inline bool has_expected(const std::string& name, const std::string& stage) {
    return std::filesystem::exists(gt::mesh_path(name)) && std::filesystem::exists(expected_path(name, stage));
}
inline const quadmesh::json::Value& expected(const std::string& name, const std::string& stage) {
    static std::map<std::string, quadmesh::json::Value> cache;
    const std::string k = name + "." + stage;
    auto it = cache.find(k);
    if (it == cache.end()) it = cache.emplace(k, quadmesh::json::parse_file(expected_path(name, stage))).first;
    return it->second;
}
inline const quadmesh::Mesh& input(const std::string& name) {
    static std::map<std::string, quadmesh::Mesh> cache;
    auto it = cache.find(name);
    if (it == cache.end()) it = cache.emplace(name, quadmesh::read_fort14(gt::mesh_path(name))).first;
    return it->second;
}

struct Run {
    quadmesh::Mesh out;
    quadmesh::Tri2QuadTrace trace;
};
// Cached tri2quad runs: stage "match" (remove_boundary_tris=false) or "core".
inline const Run& run(const std::string& name, const std::string& stage, bool rbm = false) {
    static std::map<std::string, Run> cache;
    const std::string k = name + "." + stage + (rbm ? ".rbm" : "");
    auto it = cache.find(k);
    if (it == cache.end()) {
        quadmesh::Tri2QuadOptions o;
        o.remove_boundary_tris = stage != "match";
        o.refuse_boundary_merge = rbm;
        Run r;
        r.out = quadmesh::tri2quad(input(name), o, &r.trace);
        it = cache.emplace(k, std::move(r)).first;
    }
    return it->second;
}

inline std::vector<std::array<int, 2>> pairs_of(const quadmesh::json::Value& v) {
    std::vector<std::array<int, 2>> out;
    for (std::size_t i = 0; i < v.size(); ++i)
        out.push_back({static_cast<int>(v[i][0].as_int()), static_cast<int>(v[i][1].as_int())});
    return out;
}
inline std::vector<std::string> strings_of(const quadmesh::json::Value& v) {
    std::vector<std::string> out;
    for (std::size_t i = 0; i < v.size(); ++i) out.push_back(v[i].as_string());
    return out;
}

// First per-layer field that differs from the oracle, "" when identical.
inline std::string first_layer_diff(const quadmesh::Tri2QuadTrace& tr, const quadmesh::json::Value& want,
                                    const std::vector<std::string>& fields) {
    const std::size_t n = std::max(tr.per_layer.size(), want.size());
    for (std::size_t k = 0; k < n; ++k) {
        if (k >= tr.per_layer.size() || k >= want.size()) return "layer count differs at entry " + std::to_string(k);
        const auto& g = tr.per_layer[k];
        const auto& w = want[k];
        const std::string at = "layer " + std::to_string(w["layer"].as_int()) + ": ";
        for (const std::string& f : fields) {
            bool same = true;
            if (f == "status") same = g.status == w["status"].as_string();
            else if (f == "removed_edges") same = g.removed_edges == pairs_of(w["removed_edges"]);
            else if (f == "removed_edge_ids") same = g.removed_edge_ids == w["removed_edge_ids"].as_int_vector();
            else if (f == "flagged_pairs") same = g.flagged_pairs == pairs_of(w["flagged_pairs"]);
            else if (f == "pairs") same = g.pairs == pairs_of(w["pairs"]);
            else if (f == "pair_source") same = g.pair_source == strings_of(w["pair_source"]);
            else if (f == "leftover") same = g.leftover == w["leftover"].as_int_vector();
            else if (f == "leftover_outcome") same = g.leftover_outcome == strings_of(w["leftover_outcome"]);
            if (!same) return at + f;
        }
    }
    return "";
}

// Triangles of a mesh with no domain-boundary edge (tri2quad.py invariant).
inline int interior_residual_tris(const quadmesh::Mesh& m) {
    int n = 0;
    for (int e = 0; e < m.n_elems(); ++e) {
        if (!quadmesh::is_tri(m.elems[e])) continue;
        bool bdy = false;
        for (int k = 0; k < 3; ++k) bdy = bdy || m.edge2elem[m.elem2edge[e][k]][1] < 0;
        if (!bdy) ++n;
    }
    return n;
}
inline int n_tris(const quadmesh::Mesh& m) {
    int n = 0;
    for (const auto& e : m.elems) n += quadmesh::is_tri(e) ? 1 : 0;
    return n;
}
// tests/test_no_interior_tris._geo_tri_counts: 4-distinct quads with a corner
// >= 178 deg or a zero-length edge.
inline int geometric_tris(const quadmesh::Mesh& m, bool interior_only) {
    int n = 0;
    for (int e = 0; e < m.n_elems(); ++e) {
        const auto& r = m.elems[e];
        if (quadmesh::is_tri(r)) continue;
        if (!quadmesh::detail::quad_is_degenerate(m.points, r, 178.0)) continue;
        if (interior_only) {
            bool bdy = false;
            for (int k = 0; k < quadmesh::n_corners(r); ++k)
                if (m.elem2edge[e][k] >= 0) bdy = bdy || m.edge2elem[m.elem2edge[e][k]][1] < 0;
            if (bdy) continue;
        }
        ++n;
    }
    return n;
}

}  // namespace t2q
