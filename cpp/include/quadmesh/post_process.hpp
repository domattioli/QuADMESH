#pragma once
// SPEC-09 post-process (quadmesh.post_process.post_process_routine).
//
// Takes a quad (or mixed) mesh and NO layer input; layers are never computed
// or read here (FR-007, ADR 0001). Every mesh this module builds has
// adjacencies only (MeshOptions{true, false}).
//
// Pipeline, as in Python:
//   repeat (max_outer_iter):
//     repeat (max_inner_iter): doublet_collapse -> quad_vertex_merge
//     cleanup_boundary_quads           (skipped on mixed meshes)
//   fem_smoother (remove unused vertices, FEM direct solve)
//   fix_bowties
// Boundary vertices never move in a smoother pass: their exact input
// coordinates are restored after every pass (operator hard rule).

#include <functional>
#include <string>
#include <vector>

#include "quadmesh/mesh.hpp"
#include "quadmesh/tielog.hpp"

namespace quadmesh {

// Mirrors the post_process_routine kwargs run_pipeline passes in the default
// full pipeline. truss_smooth and repair are not ported (both default off).
struct PostProcessOptions {
    bool can_remove_edges = true;
    int n_smooth_iter = 3;
    int max_outer_iter = 5;
    int max_inner_iter = 5;
    // preserve_boundary=True: cleanup never deletes or moves a vertex that
    // matches a protected point. Empty protected_points = boundary of input.
    bool preserve_boundary = false;
    std::vector<std::array<double, 2>> protected_points;
    // Test hook: called after every step with its name ("doublet_collapse",
    // "quad_vertex_merge", "cleanup_boundary_quads", "fem_pass",
    // "fem_smoother", "fix_bowties") and the mesh it produced.
    std::function<void(const std::string&, const Mesh&)> on_step;
    // Optional tie log (FR-012): doublet_collapse.py:43 records go here.
    TieLog* tielog = nullptr;
};

Mesh post_process(const Mesh& mesh, const PostProcessOptions& opts = {});

// Components (each mirrors one Python function; see cpp/src/post/).
Mesh doublet_collapse(const Mesh& mesh, TieLog* tielog = nullptr);
Mesh quad_vertex_merge(const Mesh& mesh);
Mesh cleanup_boundary_quads(const Mesh& mesh, bool can_remove_edges = true,
                            const std::vector<std::array<double, 2>>* protected_points = nullptr);
std::vector<std::array<double, 2>> boundary_points(const Mesh& mesh);
// CHILmesh.direct_smoother(kinf=1e12), solver="direct": returns new points.
std::vector<Point> direct_smoother(const Mesh& mesh, double kinf = 1e12);
// post_process.fem_smoother(method="fem"); on_pass sees the mesh after each pass.
Mesh fem_smoother(const Mesh& mesh, int n_iter = 3,
                  const std::function<void(const Mesh&)>& on_pass = {});
// repair._fix_bowties: returns the number of quads reordered.
int fix_bowties(std::vector<Elem>& conn, const std::vector<Point>& pts);

// True when the mesh holds both triangles and quads (CHILmesh "Mixed-Element").
bool is_mixed(const Mesh& mesh);

}  // namespace quadmesh
