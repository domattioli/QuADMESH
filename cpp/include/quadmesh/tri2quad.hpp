#pragma once
// SPEC-06 public tri2quad entry (contracts/library.md). Port of
// quadmesh.tri2quad.tri2quad_routine with the quadmesh+ per-layer sweep.
#include <array>
#include <string>
#include <vector>

#include "quadmesh/mesh.hpp"
#include "quadmesh/tielog.hpp"

namespace quadmesh {

// Defaults copied from tri2quad.py:1034-1044 (tri2quad_routine) and
// pipeline.py:16-28 (run_pipeline) for the post-process hook.
struct Tri2QuadOptions {
    std::string method = "quadmesh+";  // "layered" is an alias
    bool can_remove_edges = true;
    bool remove_boundary_tris = true;
    bool minimize_boundary_change = true;  // Python None -> True
    bool point_insert = true;
    bool refuse_boundary_merge = false;
    // Post-process hook (run_pipeline). Off by default: tri2quad alone is
    // tri2quad_routine. When on, calls quadmesh::post_process if the library
    // was built with cpp/include/quadmesh/post_process.hpp, else throws.
    bool do_post_process = false;
    int n_smooth_iter = 3;
    int max_outer_iter = 5;
    int max_inner_iter = 5;
    bool preserve_boundary = false;
    // Optional tie log (FR-011/FR-012). Not owned.
    TieLog* tie_log = nullptr;
};

// Per-layer record, same keys as the oracle dump's per_layer entries
// (DUMP_NOTES.md).
struct LayerTrace {
    int layer = -1;
    std::string status = "ok";  // "ok" | "identify_failed" | "no_sub_mesh"
    std::vector<std::array<int, 2>> removed_edges;  // parent vertex ids, u < v
    std::vector<int> removed_edge_ids;              // sub-mesh edge ids
    std::vector<std::array<int, 2>> flagged_pairs;
    std::vector<std::array<int, 2>> pairs;  // accepted merges, global elem ids
    std::vector<std::string> pair_source;   // "sweep" | "greedy"
    std::vector<int> leftover;
    std::vector<std::string> leftover_outcome;  // handled | refused | unchanged | error
};

struct Tri2QuadTrace {
    std::vector<LayerTrace> per_layer;  // sweep order
    std::vector<Elem> global_fallback_quads;
    std::vector<Point> inserted_points;  // sweep only
};

// Converts a triangle mesh. The input is not changed (FR-015). Throws
// InvalidMethod for "matching", "faithful" or any unknown method.
Mesh tri2quad(const Mesh& input, const Tri2QuadOptions& opts = {}, Tri2QuadTrace* trace = nullptr);

// tri2quad.fold_bridge_quads: indices of quads whose diagonal is a flagged
// (min, max) vertex pair.
std::vector<int> fold_bridge_quads(const std::vector<Elem>& quads,
                                   const std::vector<std::array<int, 2>>& flagged_edges);

// Flagged vertex pairs of every layer (tri2quad._sweep_pairs second value).
std::vector<std::array<int, 2>> flagged_edges_of(const Mesh& mesh);

}  // namespace quadmesh
