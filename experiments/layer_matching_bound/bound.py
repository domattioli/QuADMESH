"""Layer-level matching bounds: QuADMESH+ heuristic vs max-cardinality optimal.

Compares within-layer tri pairing via every-other-walk + greedy (heuristic)
against maximum-cardinality matching (optimal) on legal intra-layer tri-adjacency.
Bounds achievable leftover reduction from smarter within-layer pairing.
Topological only (no geometric degeneracy skips in either track).

Reference: GitHub issue #97.
"""

import argparse
import json
import os
import sys
import numpy as np
import networkx as nx
from chilmesh import CHILmesh
from quadmesh.identify_edges import identify_edges_in_layer
from quadmesh._match_quadmesh_plus import match_layer_heuristic


def greedy_maximal_matching(g):
    """Minimum-degree-first greedy maximal matching on graph g.

    Within-faithful-adjacent pairing: no augmenting paths (unlike Blossom
    max-cardinality), just one greedy pass matching the most-constrained
    (lowest-degree) triangle first. Deterministic (degree then node-id
    tie-break). Measures the pairing ceiling reachable by a simple greedy
    reordering of the T017/T018 pass -- the within-faithful lever named in
    the #97 bound doc.
    """
    deg = dict(g.degree())
    matched = set()
    pairs = []
    for n in sorted(g.nodes(), key=lambda x: (deg[x], x)):
        if n in matched:
            continue
        free_nbrs = [w for w in g.neighbors(n) if w not in matched]
        if not free_nbrs:
            continue
        w = min(free_nbrs, key=lambda x: (deg[x], x))
        matched.add(n)
        matched.add(w)
        pairs.append((n, w))
    return pairs


def analyze_mesh(path):
    """Analyze a mesh: compare heuristic vs optimal pairing per layer.

    Args:
        path: fort.14 mesh file path

    Returns:
        dict with mesh metadata, per-layer results, and totals
    """
    m = CHILmesh.read_from_fort14(path)
    nl = int(getattr(m, 'n_layers', 0) or 0)
    layers = m.layers

    # Global consumed sets (one per track)
    consumed_h = set()  # heuristic track
    consumed_o = set()  # optimal track
    consumed_g = set()  # greedy-maximal track

    per_layer = []

    # Iterate innermost-first
    for li in range(nl - 1, -1, -1):
        try:
            sel = identify_edges_in_layer(m, li)
        except Exception:
            continue

        if sel.sub_mesh is None:
            continue

        glob = np.asarray(sel.elem_ids_global, dtype=int)
        n_tris = int(glob.size)
        e2e = sel.sub_mesh.adjacencies['Edge2Elem']

        # === HEURISTIC TRACK ===
        local_consumed = set()
        h_pairs = 0

        # Step 1: removed_edge_ids merges
        for eid in sel.removed_edge_ids:
            row = np.asarray(e2e[int(eid)]).ravel()
            if row.size < 2 or int(row[0]) < 0 or int(row[1]) < 0:
                continue
            la, lb = int(row[0]), int(row[1])
            if la >= glob.size or lb >= glob.size:
                continue
            ga, gb = int(glob[la]), int(glob[lb])
            if ga in consumed_h or gb in consumed_h:
                continue
            if la in local_consumed or lb in local_consumed:
                continue
            h_pairs += 1
            consumed_h.add(ga)
            consumed_h.add(gb)
            local_consumed.add(la)
            local_consumed.add(lb)

        # Step 2: greedy match_layer_heuristic
        ie_ids = np.asarray(layers['IE'][li], dtype=int)
        oe_ids = np.asarray(layers['OE'][li], dtype=int)
        layer_conn = m.connectivity_list[glob]
        flagged_global_pairs = set()

        if sel.flagged_vert_pairs:
            fv = {(int(min(p)), int(max(p))) for p in sel.flagged_vert_pairs}
            n_sub_edges = sel.sub_mesh.n_edges
            e2v_all = sel.sub_mesh.edge2vert(np.arange(n_sub_edges))
            e2e_sub = sel.sub_mesh.adjacencies['Edge2Elem']
            for eidx in range(n_sub_edges):
                u, v = int(e2v_all[eidx, 0]), int(e2v_all[eidx, 1])
                if (min(u, v), max(u, v)) in fv:
                    r = np.asarray(e2e_sub[eidx]).ravel()
                    if r.size >= 2 and int(r[0]) >= 0 and int(r[1]) >= 0:
                        la2, lb2 = int(r[0]), int(r[1])
                        if la2 < glob.size and lb2 < glob.size:
                            flagged_global_pairs.add(
                                frozenset([int(glob[la2]), int(glob[lb2])])
                            )

        already = {int(glob[i]) for i in local_consumed}
        try:
            greedy_pairs, _ = match_layer_heuristic(
                layer_conn=layer_conn,
                layer_global_ids=glob,
                ie_global_ids=ie_ids,
                oe_global_ids=oe_ids,
                pts=m.points,
                flagged_pairs=flagged_global_pairs,
                already_consumed=already,
                is_boundary_layer=(li == nl - 1)
            )
        except Exception:
            greedy_pairs = []

        for la, lb in greedy_pairs:
            ga, gb = int(glob[la]), int(glob[lb])
            if ga in consumed_h or gb in consumed_h:
                continue
            if la in local_consumed or lb in local_consumed:
                continue
            h_pairs += 1
            consumed_h.add(ga)
            consumed_h.add(gb)
            local_consumed.add(la)
            local_consumed.add(lb)

        h_leftover = n_tris - 2 * h_pairs

        # === OPTIMAL TRACK ===
        flagged_edge_set = set(int(x) for x in sel.flagged_edge_ids)
        avail = [i for i in range(sel.sub_mesh.n_elems)
                 if int(glob[i]) not in consumed_o]
        avail_set = set(avail)

        G = nx.Graph()
        G.add_nodes_from(avail)
        e2e_sub2 = sel.sub_mesh.adjacencies['Edge2Elem']

        for eidx in range(sel.sub_mesh.n_edges):
            if eidx in flagged_edge_set:
                continue
            r = np.asarray(e2e_sub2[eidx]).ravel()
            if r.size < 2 or int(r[0]) < 0 or int(r[1]) < 0:
                continue
            la, lb = int(r[0]), int(r[1])
            if la in avail_set and lb in avail_set and la != lb:
                G.add_edge(la, lb)

        matching = nx.max_weight_matching(G, maxcardinality=True)
        o_pairs = len(matching)
        for a, b in matching:
            consumed_o.add(int(glob[a]))
            consumed_o.add(int(glob[b]))
        o_leftover = n_tris - 2 * o_pairs

        # === GREEDY-MAXIMAL TRACK (within-faithful lever ceiling) ===
        avail_g = [i for i in range(sel.sub_mesh.n_elems)
                   if int(glob[i]) not in consumed_g]
        avail_g_set = set(avail_g)
        Gg = nx.Graph()
        Gg.add_nodes_from(avail_g)
        for eidx in range(sel.sub_mesh.n_edges):
            if eidx in flagged_edge_set:
                continue
            r = np.asarray(e2e_sub2[eidx]).ravel()
            if r.size < 2 or int(r[0]) < 0 or int(r[1]) < 0:
                continue
            la, lb = int(r[0]), int(r[1])
            if la in avail_g_set and lb in avail_g_set and la != lb:
                Gg.add_edge(la, lb)
        greedy_matching = greedy_maximal_matching(Gg)
        g_pairs = len(greedy_matching)
        for a, b in greedy_matching:
            consumed_g.add(int(glob[a]))
            consumed_g.add(int(glob[b]))
        g_leftover = n_tris - 2 * g_pairs

        per_layer.append({
            'layer': li,
            'n_tris': n_tris,
            'h_pairs': h_pairs,
            'g_pairs': g_pairs,
            'o_pairs': o_pairs,
            'h_leftover': h_leftover,
            'g_leftover': g_leftover,
            'o_leftover': o_leftover,
            'headroom_pairs': o_pairs - h_pairs,
            'greedy_leftover': g_leftover
        })

    # Totals
    sum_n_tris = sum(d['n_tris'] for d in per_layer)
    sum_h_pairs = sum(d['h_pairs'] for d in per_layer)
    sum_g_pairs = sum(d['g_pairs'] for d in per_layer)
    sum_o_pairs = sum(d['o_pairs'] for d in per_layer)
    sum_h_leftover = sum(d['h_leftover'] for d in per_layer)
    sum_g_leftover = sum(d['g_leftover'] for d in per_layer)
    sum_o_leftover = sum(d['o_leftover'] for d in per_layer)
    total_headroom = sum_o_pairs - sum_h_pairs
    headroom_reduction = sum_h_leftover - sum_o_leftover

    return {
        'mesh': os.path.basename(path),
        'n_elems': int(m.n_elems),
        'n_layers': nl,
        'per_layer': per_layer,
        'totals': {
            'n_tris': sum_n_tris,
            'h_pairs': sum_h_pairs,
            'g_pairs': sum_g_pairs,
            'o_pairs': sum_o_pairs,
            'h_leftover': sum_h_leftover,
            'g_leftover': sum_g_leftover,
            'o_leftover': sum_o_leftover,
            'headroom_pairs': total_headroom,
            'leftover_reduction': headroom_reduction
        }
    }


def main():
    parser = argparse.ArgumentParser(
        description='Layer-level matching bounds analysis'
    )
    parser.add_argument('meshes', nargs='+', help='fort.14 mesh file paths')
    parser.add_argument('--json', dest='json_out', help='output JSON file')
    args = parser.parse_args()

    results = []
    for mesh_path in args.meshes:
        try:
            result = analyze_mesh(mesh_path)
            results.append(result)
            t = result['totals']
            print(
                f"{result['mesh']} n_elems={result['n_elems']} "
                f"n_layers={result['n_layers']} | "
                f"heuristic_pairs={t['h_pairs']} optimal_pairs={t['o_pairs']} | "
                f"heuristic_leftover={t['h_leftover']} "
                f"optimal_leftover={t['o_leftover']} | "
                f"headroom_pairs={t['headroom_pairs']} "
                f"(leftover_reduction={t['leftover_reduction']})"
            )
        except Exception as e:
            print(f"{mesh_path} ERROR: {e}", file=sys.stderr)

    if args.json_out:
        with open(args.json_out, 'w') as f:
            json.dump(results, f, indent=2)


if __name__ == '__main__':
    main()
