// T036: tri2quad._quadmesh_plus_per_layer (tri2quad.py:816-1031) and
// tri2quad_routine (tri2quad.py:1034-1205), with the run_pipeline
// post-process hook.
#include <algorithm>

#include "quadmesh/error.hpp"
#include "quadmesh/tri2quad.hpp"
#include "quadmesh/tri2quad_detail.hpp"

#if __has_include("quadmesh/post_process.hpp")
#include "quadmesh/post_process.hpp"
#define QUADMESH_HAS_POST_PROCESS 1
#endif

namespace quadmesh::detail {

PerLayerResult quadmesh_plus_per_layer(const Mesh& input, const std::vector<Tri3>& tris,
                                       bool can_remove_edges, bool refuse_boundary_merge,
                                       TieLog* log, Tri2QuadTrace* trace) {
    Mesh dom = input;  // private copy: the sweep mutates it
    const int n_in_pts = dom.n_verts();
    WorkingMesh work(n_in_pts);
    std::unordered_set<int> consumed, refused;
    const int nl = dom.n_layers();
    SweepContext ctx(dom, work, consumed, refused, boundary_edge_set(tris), log);

    std::unordered_set<int> all_layer_elems;
    for (int li = 0; li < nl; ++li) {
        all_layer_elems.insert(dom.layers.OE[li].begin(), dom.layers.OE[li].end());
        all_layer_elems.insert(dom.layers.IE[li].begin(), dom.layers.IE[li].end());
    }

    for (int li = nl - 1; li >= 0; --li) {
        if (log) log->layer = li;
        ctx.layer_idx = li;
        ctx.sync();
        LayerTrace lt;
        lt.layer = li;
        LayerEdgeSelection sel;
        try {
            sel = identify_edges_in_layer(dom, li);
        } catch (const std::exception&) {
            lt.status = "identify_failed";
            if (trace) trace->per_layer.push_back(lt);
            continue;
        }
        if (!sel.has_sub_mesh) {
            lt.status = "no_sub_mesh";
            if (trace) trace->per_layer.push_back(lt);
            continue;
        }
        const Mesh& sm = sel.sub_mesh;
        const std::vector<int>& glob = sel.elem_ids_global;
        const int gn = static_cast<int>(glob.size());
        if (trace) {
            for (int eid : sel.removed_edge_ids) {
                lt.removed_edge_ids.push_back(eid);
                lt.removed_edges.push_back({sm.edge2vert[eid][0], sm.edge2vert[eid][1]});
            }
            lt.flagged_pairs = sel.flagged_vert_pairs;
        }
        std::unordered_set<int> local_consumed;

        auto try_merge = [&](int la, int lb, const char* src) {
            const int ga = glob[la], gb = glob[lb];
            if (consumed.count(ga) || consumed.count(gb)) return;
            if (local_consumed.count(la) || local_consumed.count(lb)) return;
            Elem quad;
            try {
                quad = quad_from_tri_pair(sm.points, sm.elems[la], sm.elems[lb]);
            } catch (const std::exception&) {
                return;
            }
            if (quad_is_degenerate(sm.points, quad)) return;
            work.add_quad(quad);
            consumed.insert(ga);
            consumed.insert(gb);
            local_consumed.insert(la);
            local_consumed.insert(lb);
            if (trace) {
                lt.pairs.push_back({ga, gb});
                lt.pair_source.push_back(src);
            }
        };

        for (int eid : sel.removed_edge_ids) {
            const Edge& row = sm.edge2elem[eid];
            if (row[0] < 0 || row[1] < 0 || row[0] >= gn || row[1] >= gn) continue;
            try_merge(row[0], row[1], "sweep");
        }

        // Fold-seam pairs -> forbidden global element pairs.
        PairSet flagged_global;
        if (!sel.flagged_vert_pairs.empty()) {
            PairSet fv;
            for (const IPair& p : sel.flagged_vert_pairs) fv.insert(pair_key(p[0], p[1]));
            for (int e = 0; e < sm.n_edges(); ++e) {
                if (!fv.count(pair_key(sm.edge2vert[e][0], sm.edge2vert[e][1]))) continue;
                const Edge& row = sm.edge2elem[e];
                if (row[0] >= 0 && row[1] >= 0 && row[0] < gn && row[1] < gn)
                    flagged_global.insert(pair_key(glob[row[0]], glob[row[1]]));
            }
        }
        std::unordered_set<int> already;
        for (int i : local_consumed) already.insert(glob[i]);
        std::vector<Tri3> layer_conn;
        for (int g : glob) layer_conn.push_back(ctx.tri_row(g));
        std::vector<IPair> greedy;
        try {
            greedy = match_layer_heuristic(layer_conn, glob, dom.layers.IE[li], dom.layers.OE[li], dom.points,
                                           flagged_global, already, true, li == 0);
        } catch (const std::exception&) {
            greedy.clear();
        }
        for (const IPair& p : greedy) try_merge(p[0], p[1], "greedy");

        const std::unordered_set<int> no_edges;
        const std::unordered_set<int> b_verts(sel.boundary_vert_ids_global.begin(),
                                              sel.boundary_vert_ids_global.end());
        for (int gid : glob) {
            if (consumed.count(gid)) continue;
            std::optional<bool> handled;
            bool err = false;
            try {
                handled = route_leftover_tri(dom, work, gid, li == 0, can_remove_edges, no_edges, b_verts,
                                             refuse_boundary_merge, true, &ctx, log);
            } catch (const std::exception&) {
                handled.reset();
                err = true;
            }
            if (trace) {
                lt.leftover.push_back(gid);
                lt.leftover_outcome.push_back(err ? "error" : !handled ? "unchanged"
                                                         : *handled  ? "handled"
                                                                     : "refused");
            }
            if (!handled) continue;
            if (!*handled) refused.insert(gid);
            consumed.insert(gid);
        }
        if (trace) trace->per_layer.push_back(lt);
    }
    if (log) log->layer = -1;

    work.flush_points_to(dom.points);
    PerLayerResult res;
    for (const Elem& e : dom.elems) res.tris_out.push_back({e[0], e[1], e[2]});
    for (int i : consumed)
        if (!refused.count(i)) res.tris_out[i] = {0, 0, 0};
    auto distinct3 = [](const Tri3& t) { return t[0] != t[1] && t[1] != t[2] && t[0] != t[2]; };

    std::vector<int> unclaimed;
    for (int i = 0; i < static_cast<int>(tris.size()); ++i)
        if (!consumed.count(i) && !all_layer_elems.count(i) && distinct3(res.tris_out[i])) unclaimed.push_back(i);
    if (!unclaimed.empty()) {
        std::vector<Tri3> ut;
        for (int i : unclaimed) ut.push_back(res.tris_out[i]);
        MatchResult m = match_tris_to_quads(ut, dom.points, nullptr, false, nullptr, nullptr, log);
        for (const Elem& q : m.quads) {
            work.add_quad(q);
            if (trace) trace->global_fallback_quads.push_back(q);
        }
        std::unordered_set<int> left(m.leftover.begin(), m.leftover.end());
        for (int j = 0; j < static_cast<int>(unclaimed.size()); ++j)
            if (!left.count(j)) consumed.insert(unclaimed[j]);
    }
    for (int i = 0; i < static_cast<int>(res.tris_out.size()); ++i)
        if (!consumed.count(i) && distinct3(res.tris_out[i])) res.leftover_idx.push_back(i);
    res.points = dom.points;
    if (trace)
        trace->inserted_points.assign(dom.points.begin() + n_in_pts, dom.points.end());
    res.refused.insert(refused.begin(), refused.end());
    res.bset_out = ctx.dom_bdy;
    res.quads = work.quads;
    return res;
}

}  // namespace quadmesh::detail

namespace quadmesh {

Mesh tri2quad(const Mesh& input, const Tri2QuadOptions& opts, Tri2QuadTrace* trace) {
    using namespace detail;
    std::string method = opts.method;
    if (method == "quadmesh+") method = "layered";
    if (method == "faithful" || method == "matching")
        throw InvalidMethod("method='" + method + "' was removed (QuADMesh#46); use 'quadmesh+'");
    if (method != "layered") throw InvalidMethod("unknown method '" + method + "' (use 'quadmesh+')");

    std::vector<Tri3> tris;
    for (const Elem& e : input.elems) {
        if (!is_tri(e)) throw InputError("tri2quad: input must be a triangle mesh");
        tris.push_back({e[0], e[1], e[2]});
    }
    std::vector<Point> points = input.points;
    std::vector<Elem> quads;
    std::vector<int> leftover;
    std::set<int> refused;
    std::optional<PairSet> bset_sweep;

    if (input.n_layers() > 0) {
        PerLayerResult r = quadmesh_plus_per_layer(input, tris, opts.can_remove_edges,
                                                   opts.refuse_boundary_merge, opts.tie_log, trace);
        quads = std::move(r.quads);
        leftover = std::move(r.leftover_idx);
        points = std::move(r.points);
        refused = std::move(r.refused);
        tris = std::move(r.tris_out);
        bset_sweep = std::move(r.bset_out);
    } else {
        const std::vector<int> prio = layer_priority(input, static_cast<int>(tris.size()));
        std::optional<std::vector<IPair>> seed;
        PairSet forbidden;
        bool have = false;
        try {
            auto sp = sweep_pairs(input);
            seed = sp.first;
            for (const IPair& p : sp.second) forbidden.insert(pair_key(p[0], p[1]));
            have = true;
        } catch (const std::exception&) {
        }
        MatchResult m = match_tris_to_quads(tris, points, &prio, false, have ? &*seed : nullptr,
                                            have ? &forbidden : nullptr, opts.tie_log);
        quads = std::move(m.quads);
        leftover = std::move(m.leftover);
    }

    if (opts.remove_boundary_tris && !leftover.empty()) {
        const PairSet bset = bset_sweep ? *bset_sweep : boundary_edge_set(tris);
        leftover = remove_boundary_tris(quads, leftover, tris, points, bset, opts.can_remove_edges,
                                        opts.minimize_boundary_change);
    }
    std::vector<Tri3> surviving;
    for (int i : leftover) surviving.push_back(tris[i]);
    if (!surviving.empty() && !quads.empty()) edge_swap_tri_pairs(quads, surviving, points, opts.tie_log);
    if (opts.point_insert && !surviving.empty() && !quads.empty())
        point_insert_tri_pairs(quads, surviving, points);
    for (int i : refused) surviving.push_back(tris[i]);

    if (quads.empty() && surviving.empty()) throw Error("tri2quad produced empty mesh");
    std::vector<Elem> conn = quads;
    for (const Tri3& t : surviving) conn.push_back(make_tri(t[0], t[1], t[2]));

    std::vector<int> remap(points.size(), -1);
    for (const Elem& e : conn)
        for (int k = 0; k < n_corners(e); ++k) remap.at(e[k]) = 0;
    std::vector<Point> pts_out;
    for (std::size_t v = 0; v < points.size(); ++v)
        if (remap[v] == 0) {
            remap[v] = static_cast<int>(pts_out.size());
            pts_out.push_back(points[v]);
        }
    for (Elem& e : conn)
        for (int k = 0; k < n_corners(e); ++k) e[k] = remap[e[k]];

    Mesh out(std::move(pts_out), std::move(conn), input.grid_name, MeshOptions{true, false});
    if (!opts.do_post_process) return out;
#ifdef QUADMESH_HAS_POST_PROCESS
    PostProcessOptions po;
    po.can_remove_edges = opts.can_remove_edges;
    po.n_smooth_iter = opts.n_smooth_iter;
    po.max_outer_iter = opts.max_outer_iter;
    po.max_inner_iter = opts.max_inner_iter;
    po.preserve_boundary = opts.preserve_boundary;
    if (opts.preserve_boundary) po.protected_points = boundary_points(input);
    return post_process(out, po);
#else
    throw Error("post-process not built");
#endif
}

}  // namespace quadmesh
