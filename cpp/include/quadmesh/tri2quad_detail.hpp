#pragma once
// Internal pieces of the tri2quad port, exposed for the oracle tests.
// Not part of the stable library contract (contracts/library.md).
//
// Python sources: tri2quad.py, identify_edges.py, _match_quadmesh_plus.py,
// _tri_removal.py, _recombine.py. Where Python iterates a set whose order
// can change the result, the port iterates ascending id and writes a
// TieLog record (ADR 0001, FR-011/FR-012).
#include <array>
#include <cstdint>
#include <map>
#include <optional>
#include <set>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

#include "quadmesh/mesh.hpp"
#include "quadmesh/tielog.hpp"
#include "quadmesh/tri2quad.hpp"

namespace quadmesh::detail {

using XY = std::array<double, 2>;
using Tri3 = std::array<int, 3>;
using IPair = std::array<int, 2>;

inline std::uint64_t pair_key(int a, int b) {
    if (a > b) std::swap(a, b);
    return (static_cast<std::uint64_t>(static_cast<std::uint32_t>(a)) << 32) |
           static_cast<std::uint32_t>(b);
}
using PairSet = std::unordered_set<std::uint64_t>;  // unordered pairs

inline XY xy_of(const Point& p) { return {p[0], p[1]}; }

// ---- geometry (tri2quad.py:47-93, 791-813) ---------------------------------
bool segments_cross(const XY& a, const XY& b, const XY& c, const XY& d);
// np.sum(x * roll(y,-1) - roll(x,-1) * y) over a closed polygon.
double area2_roll(const XY* p, int n);
double quad_quality(const std::array<XY, 4>& p);
bool quad_ok(const std::array<XY, 4>& p);
bool quad_is_degenerate(const std::vector<Point>& pts, const Elem& quad, double max_angle_deg = 177.0);
// _match_quadmesh_plus._quad_quality_pair over local rows.
double quad_quality_pair(const std::vector<Tri3>& conn, const std::vector<Point>& pts, int ia, int ib);

// ---- identify_edges.py ------------------------------------------------------
struct LayerEdgeSelection {
    bool has_sub_mesh = false;
    Mesh sub_mesh;
    std::vector<int> elem_ids_global;
    std::vector<int> boundary_edge_ids;
    std::vector<int> boundary_vert_ids_global;
    std::vector<int> removed_edge_ids;
    std::vector<std::vector<int>> paths;
    std::vector<int> flagged_edge_ids;
    std::vector<IPair> flagged_vert_pairs;
};
// Throws quadmesh::Error where Python raises (the sweep then skips the layer).
LayerEdgeSelection identify_edges_in_layer(const Mesh& domain, int layer_idx);
// tri2quad._sweep_pairs: (merge pairs, flagged vertex pairs).
std::pair<std::vector<IPair>, std::vector<IPair>> sweep_pairs(const Mesh& domain);

// ---- _match_quadmesh_plus.py ------------------------------------------------
// Returns local (a, b) pairs into layer_conn.
std::vector<IPair> match_layer_heuristic(const std::vector<Tri3>& layer_conn,
                                         const std::vector<int>& layer_global_ids,
                                         const std::vector<int>& ie_global_ids,
                                         const std::vector<int>& oe_global_ids,
                                         const std::vector<Point>& pts,
                                         const PairSet& flagged_pairs,
                                         const std::unordered_set<int>& already_consumed,
                                         bool use_t2_ladder = true, bool is_boundary_layer = false,
                                         const std::vector<IPair>* removed_edge_local_pairs = nullptr);
// _build_tri_adjacency: neighbour lists in Python dict insertion order.
std::vector<std::vector<int>> build_tri_adjacency(const std::vector<Tri3>& conn);

// ---- tri2quad._match_tris_to_quads -----------------------------------------
struct MatchResult {
    std::vector<Elem> quads;
    std::vector<int> leftover;
};
MatchResult match_tris_to_quads(const std::vector<Tri3>& tris, const std::vector<Point>& points,
                                const std::vector<int>* prio = nullptr, bool quality_aware = false,
                                const std::vector<IPair>* seed_pairs = nullptr,
                                const PairSet* forbidden_edges = nullptr, TieLog* log = nullptr);

// ---- tri2quad.py boundary-tri passes ----------------------------------------
PairSet boundary_edge_set(const std::vector<Tri3>& tris);
// Returns kept (interior or preserved) leftover indices; edits quads, points.
std::vector<int> remove_boundary_tris(std::vector<Elem>& quads, const std::vector<int>& leftover_idx,
                                      const std::vector<Tri3>& tris, std::vector<Point>& points,
                                      const PairSet& bset, bool can_remove_edges,
                                      bool minimize_boundary_change);
void edge_swap_tri_pairs(std::vector<Elem>& quads, std::vector<Tri3>& tris,
                         const std::vector<Point>& points, TieLog* log = nullptr);
std::optional<std::vector<int>> ordered_loop(const std::vector<IPair>& perimeter);
void point_insert_tri_pairs(std::vector<Elem>& quads, std::vector<Tri3>& tris,
                            std::vector<Point>& points);

// ---- _tri_removal.py ---------------------------------------------------------
struct WorkingMesh {
    std::vector<Point> points;  // recombine helpers only; the sweep leaves it empty
    std::vector<Elem> quads;
    std::optional<std::vector<std::optional<Tri3>>> tris;
    int n_pts = 0;
    int base = 0;
    std::vector<Point> extra;
    std::unordered_map<int, std::set<int>> v2q;

    WorkingMesh() = default;
    explicit WorkingMesh(int n_points) : n_pts(n_points), base(n_points) {}
    explicit WorkingMesh(std::vector<Point> pts)
        : points(std::move(pts)), n_pts(static_cast<int>(points.size())), base(n_pts) {}
    int add_quad(const Elem& q);
    int add_point(Point xyz);
    const Point& get_extra_point(int idx) const { return extra.at(idx - base); }
    const std::set<int>& quads_with(int v) const;
    void replace_vertex_in_quad(int qi, int old_v, int new_v);
    void flush_points_to(std::vector<Point>& dst);
};

enum class Route { Handled, Refused, Unchanged };

// SweepContext: live topology of the per-layer sweep. `dom` plays the role
// of the mutated Python domain: points, rows (retired rows are [0,0,0,-1]),
// layers (private copy) and adjacency (rebuilt by sync()).
class SweepContext {
public:
    static constexpr int MAX_FAN = 64;
    static constexpr double MIN_SINE = 0.06;

    SweepContext(Mesh& dom, WorkingMesh& work, std::unordered_set<int>& consumed,
                 std::unordered_set<int>& refused, const PairSet& boundary_edges, TieLog* log);

    int layer_idx = 0;
    bool dirty = false;
    PairSet dom_bdy;
    std::unordered_set<int> dom_bdy_verts;

    XY xy(int v) const;
    Tri3 tri_row(int r) const;
    bool live(int r) const;
    bool is_ring_edge(int u, int v) const;
    bool is_ring_vert(int v) const;
    void sync();
    std::optional<bool> route(int r, bool refuse_boundary_merge);  // nullopt = unchanged

private:
    using El = std::pair<char, int>;  // 'q' quad index, 't' tri row
    Mesh& d_;
    WorkingMesh& w_;
    std::unordered_set<int>& consumed_;
    std::unordered_set<int>& refused_;
    TieLog* log_;
    std::unordered_map<int, std::pair<int, char>> elem_layer_;  // 'O' or 'I'
    std::unordered_map<int, std::set<int>> v2t_;

    bool outer(int r) const;
    std::vector<int> outer_tris_on_edge(int u, int v) const;
    std::vector<int> elem_verts(const El& el) const;
    std::vector<El> elems_on_edge(int u, int v) const;
    void set_row(int r, const Tri3& v);
    void retire_tri(int r);
    void replace_vertex(const El& el, int old_v, int new_v);
    int split_outer(int r, int x, int y, int m);
    void split_ring_edge(int x, int y, int m, std::optional<int> outer_row);
    std::pair<bool, std::optional<int>> ring_target(int x, int y) const;
    std::optional<XY> bisect_point(int a, int b, int c, std::optional<int> outer_row) const;
    bool bisect(int r, int a, int b, int c, bool flat_ok = false);
    std::optional<std::pair<int, std::vector<El>>> fan(int r, int b, int start) const;
    bool vertex_split(int r, int b, int p, int q);
};

// Non-sweep removeTrianglesFun ops on a domain mesh with adjacency (Python
// route_leftover_tri without ctx). Retired rows are zeroed. Kept for parity;
// tri2quad always routes through SweepContext.
void edge_removal(Mesh& domain, WorkingMesh& work, int tri, int bdy_edge_idx);
std::optional<int> edge_bisection(Mesh& domain, WorkingMesh& work, int tri, int bdy_edge_idx);
std::optional<int> split_opposing_tri(Mesh& domain, int edge_id, int np_id, int consumed_tri);
std::optional<int> edge_insertion(Mesh& domain, WorkingMesh& work, int tri, int bdy_vert,
                                  TieLog* log = nullptr);
std::optional<bool> route_leftover_tri(Mesh& domain, WorkingMesh& work, int tri, bool on_mesh_boundary,
                                       bool can_remove_edges, const std::unordered_set<int>& sub_b_edges,
                                       const std::unordered_set<int>& sub_b_verts,
                                       bool refuse_boundary_merge, bool preserve_boundary_verts,
                                       SweepContext* ctx = nullptr, TieLog* log = nullptr);
std::unordered_set<int> handle_isolated_tris(const std::vector<Tri3>& layer_conn,
                                             const std::vector<int>& layer_global_ids,
                                             const std::unordered_set<int>& consumed,
                                             const std::vector<Point>& pts, WorkingMesh& work);

// ---- _recombine.py (work.tris must be set) ----------------------------------
bool edge_swap(WorkingMesh& work, int va, int vb, const std::vector<Point>& pts);
std::pair<bool, int> vertex_duplication(WorkingMesh& work, int v, const std::vector<Point>& pts);
bool edge_flip(WorkingMesh& work, int elem_idx, const std::vector<Point>& pts);
bool walk_isolated_tri(WorkingMesh& work, int isolated_idx, const std::vector<Point>& pts,
                       int max_hops = 4);

// ---- per-layer driver (tri2quad._quadmesh_plus_per_layer) -------------------
struct PerLayerResult {
    std::vector<Elem> quads;
    std::vector<int> leftover_idx;
    std::vector<Point> points;
    std::set<int> refused;
    std::vector<Tri3> tris_out;  // consumed rows zeroed
    PairSet bset_out;
};
PerLayerResult quadmesh_plus_per_layer(const Mesh& input, const std::vector<Tri3>& tris,
                                       bool can_remove_edges, bool refuse_boundary_merge,
                                       TieLog* log, Tri2QuadTrace* trace);

}  // namespace quadmesh::detail
