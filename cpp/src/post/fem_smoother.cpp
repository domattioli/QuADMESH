// T042: post_process.fem_smoother (method="fem") and CHILmesh.direct_smoother
// (kinf=1e12, solver="direct", no size_fn, freeze_quad_nodes=False).
//
// Stiffness: Balendran rotation blocks for triangles, Q4 bilinear Laplacian
// for quads; interior RHS 0; boundary pinned by the penalty kinf (the
// diagonal is replaced, not added to, as in _solve_pinned_penalty). Python
// solves with scipy spsolve (SuperLU); the port uses Eigen SparseLU.
// Boundary coordinates are restored bit for bit after every pass.
#include <Eigen/SparseCore>
#include <Eigen/SparseLU>

#include <cmath>
#include <stdexcept>

#include "common.hpp"
#include "quadmesh/post_process.hpp"

namespace quadmesh {

std::vector<Point> direct_smoother(const Mesh& mesh, double kinf) {
    const int n = mesh.n_verts();
    using Trip = Eigen::Triplet<double>;
    std::vector<Trip> trips;
    const double s3 = std::sqrt(3.0);
    const double T[2][2] = {{-1.0, -s3}, {s3, -1.0}};
    const double KL[4][4] = {{4.0, -1.0, -2.0, -1.0},
                             {-1.0, 4.0, -1.0, -2.0},
                             {-2.0, -1.0, 4.0, -1.0},
                             {-1.0, -2.0, -1.0, 4.0}};
    // Python assembles all triangles first, then all quads (mixed path).
    for (const Elem& r : mesh.elems) {
        if (!is_tri(r)) continue;
        for (int i = 0; i < 3; ++i)
            for (int j = 0; j < 3; ++j)
                for (int di = 0; di < 2; ++di)
                    for (int dj = 0; dj < 2; ++dj) {
                        double b;
                        if (i == j) b = di == dj ? 2.0 : 0.0;
                        else if (j == (i + 1) % 3) b = T[di][dj];
                        else b = T[dj][di];
                        trips.emplace_back(2 * r[i] + di, 2 * r[j] + dj, b);
                    }
    }
    for (const Elem& r : mesh.elems) {
        if (is_tri(r)) continue;
        for (int i = 0; i < 4; ++i)
            for (int j = 0; j < 4; ++j) {
                const double k = (1.0 / 6.0) * KL[i][j];
                for (int d = 0; d < 2; ++d) trips.emplace_back(2 * r[i] + d, 2 * r[j] + d, k);
            }
    }
    Eigen::SparseMatrix<double> K(2 * n, 2 * n);
    K.setFromTriplets(trips.begin(), trips.end());
    Eigen::VectorXd F = Eigen::VectorXd::Zero(2 * n);
    for (int v : mesh.boundary_node_indices()) {
        for (int d = 0; d < 2; ++d) {
            F[2 * v + d] = kinf * mesh.points[v][d];
            K.coeffRef(2 * v + d, 2 * v + d) = kinf;
        }
    }
    K.makeCompressed();
    Eigen::SparseLU<Eigen::SparseMatrix<double>, Eigen::COLAMDOrdering<int>> lu;
    lu.compute(K);
    if (lu.info() != Eigen::Success) throw std::runtime_error("direct_smoother: factorization failed");
    Eigen::VectorXd c = lu.solve(F);
    if (lu.info() != Eigen::Success) throw std::runtime_error("direct_smoother: solve failed");

    double lo[2] = {0, 0}, hi[2] = {0, 0};
    for (int v = 0; v < n; ++v)
        for (int d = 0; d < 2; ++d) {
            const double x = mesh.points[v][d];
            if (v == 0 || x < lo[d]) lo[d] = x;
            if (v == 0 || x > hi[d]) hi[d] = x;
        }
    const double diag = std::hypot(hi[0] - lo[0], hi[1] - lo[1]);
    double max_disp = 0.0;
    bool finite = true;
    for (int v = 0; v < n; ++v) {
        finite = finite && std::isfinite(c[2 * v]) && std::isfinite(c[2 * v + 1]);
        max_disp = std::max(max_disp, std::hypot(c[2 * v] - mesh.points[v][0],
                                                 c[2 * v + 1] - mesh.points[v][1]));
    }
    if (!finite || max_disp > diag) return mesh.points;
    std::vector<Point> out = mesh.points;
    for (int v = 0; v < n; ++v) {
        out[v][0] = c[2 * v];
        out[v][1] = c[2 * v + 1];
    }
    return out;
}

Mesh fem_smoother(const Mesh& in, int n_iter, const std::function<void(const Mesh&)>& on_pass) {
    Mesh mesh = remove_unused(in, post_detail::adj_only());
    const std::vector<int> bidx = mesh.boundary_node_indices();
    std::vector<std::array<double, 2>> bxy;
    for (int v : bidx) bxy.push_back({mesh.points[v][0], mesh.points[v][1]});

    for (int pass = 0; pass < n_iter; ++pass) {
        const std::vector<Point> before = mesh.points;
        try {
            const std::vector<Point> np_ = direct_smoother(mesh);
            for (int v = 0; v < mesh.n_verts(); ++v) {
                mesh.points[v][0] = np_[v][0];
                mesh.points[v][1] = np_[v][1];
            }
        } catch (const std::exception&) {
            mesh.points = before;
            break;
        }
        // Operator hard rule: boundary vertices never move.
        for (std::size_t i = 0; i < bidx.size(); ++i) {
            mesh.points[bidx[i]][0] = bxy[i][0];
            mesh.points[bidx[i]][1] = bxy[i][1];
        }
        if (on_pass) on_pass(mesh);
        // #107: the FEM solve is a fixed point; passes 2+ are no-ops.
        break;
    }
    return mesh;
}

}  // namespace quadmesh
