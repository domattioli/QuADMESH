// T044: post_process_routine. No layer input; layers are never computed
// (FR-007, ADR 0001). Python rebuilds a CHILmesh (and re-peels) after every
// step; no step reads layers, so the port builds adjacencies only.
#include "quadmesh/post_process.hpp"

#include "common.hpp"

namespace quadmesh {

bool is_mixed(const Mesh& mesh) {
    bool t = false, q = false;
    for (const Elem& r : mesh.elems) (is_tri(r) ? t : q) = true;
    return t && q;
}

Mesh post_process(const Mesh& input, const PostProcessOptions& opts) {
    auto step = [&](const char* name, const Mesh& m) {
        if (opts.on_step) opts.on_step(name, m);
    };
    Mesh mesh = input;
    if (!mesh.has_adjacencies()) mesh.build_adjacencies();

    std::vector<std::array<double, 2>> protected_pts;
    const std::vector<std::array<double, 2>>* prot = nullptr;
    if (opts.preserve_boundary) {
        protected_pts = opts.protected_points.empty() ? boundary_points(mesh) : opts.protected_points;
        prot = &protected_pts;
    }

    int n_prev = mesh.n_elems();
    for (int outer = 0; outer < opts.max_outer_iter; ++outer) {
        for (int inner = 0; inner < opts.max_inner_iter; ++inner) {
            const int n_before = mesh.n_elems();
            mesh = doublet_collapse(mesh, opts.tielog);
            step("doublet_collapse", mesh);
            mesh = quad_vertex_merge(mesh);
            step("quad_vertex_merge", mesh);
            if (mesh.n_elems() >= n_before) break;
        }
        if (!is_mixed(mesh)) {
            mesh = cleanup_boundary_quads(mesh, opts.can_remove_edges, prot);
            step("cleanup_boundary_quads", mesh);
        }
        if (mesh.n_elems() >= n_prev) break;
        n_prev = mesh.n_elems();
    }

    mesh = fem_smoother(mesh, opts.n_smooth_iter, [&](const Mesh& m) { step("fem_pass", m); });
    step("fem_smoother", mesh);

    std::vector<Elem> conn = mesh.elems;
    if (fix_bowties(conn, mesh.points) > 0) {
        mesh = post_detail::rebuild(mesh, mesh.points, std::move(conn));
    }
    step("fix_bowties", mesh);
    return mesh;
}

}  // namespace quadmesh
