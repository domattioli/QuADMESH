"""Conditions a triangular CHILmesh by walking layers 0→N, detecting tris that quadmesh+ would leave unpaired (via identify_edges + match_layer_heuristic), and rewiring each with point-preserving edge flips (walk_isolated_tri). No points added/moved; element + vertex counts preserved. No max-cardinality/blossom matching. Experimental, opt-in."""

from __future__ import annotations

from typing import Optional

import numpy as np
from chilmesh import CHILmesh

from ._recombine import walk_isolated_tri
from ._tri_removal import WorkingMesh


def _layer_elem_ids(domain, li) -> np.ndarray:
    """Return all tri IDs (OE + IE) in layer li."""
    layers = domain.layers
    oe = np.asarray(layers["OE"][li], dtype=int)
    ie = np.asarray(layers["IE"][li], dtype=int)
    return np.concatenate([oe, ie]) if oe.size or ie.size else np.empty(0, dtype=int)


def _layer_paired_globals(domain, li) -> set:
    """Return set of global elem IDs that would be paired in this layer via quadmesh+ heuristic.

    Mirrors the pairing logic in tri2quad._quadmesh_plus_per_layer (lines ~813-909):
    - identify_edges_in_layer to get the removed edges (structural pairs)
    - match_layer_heuristic T1+T2 to get the greedy heuristic pairs
    - Returns union of both sets of paired global IDs
    """
    from .identify_edges import identify_edges_in_layer
    from ._match_quadmesh_plus import match_layer_heuristic

    try:
        sel = identify_edges_in_layer(domain, li)
    except Exception:
        return set()

    if sel.sub_mesh is None:
        return set()

    glob = np.asarray(sel.elem_ids_global, dtype=int)
    paired = set()

    # Phase 1: pairs from removed edges (structural, first priority)
    e2e = sel.sub_mesh.adjacencies["Edge2Elem"]
    for eid in sel.removed_edge_ids:
        row = np.asarray(e2e[int(eid)]).ravel()
        if row.size < 2 or int(row[0]) < 0 or int(row[1]) < 0:
            continue
        la, lb = int(row[0]), int(row[1])
        if la >= glob.size or lb >= glob.size:
            continue
        paired.add(int(glob[la]))
        paired.add(int(glob[lb]))

    # Phase 2: greedy heuristic pairs (T017/T018 interior-saturating)
    ie_ids = np.asarray(domain.layers["IE"][li], dtype=int)
    oe_ids = np.asarray(domain.layers["OE"][li], dtype=int)
    layer_conn = domain.connectivity_list[glob]

    # Flagged pairs (fold-seam forbiddance, T018)
    flagged_global_pairs = set()
    if sel.flagged_vert_pairs:
        fv = {(int(min(p)), int(max(p))) for p in sel.flagged_vert_pairs}
        n_sub_edges = sel.sub_mesh.n_edges
        e2v_all = sel.sub_mesh.edge2vert(np.arange(n_sub_edges))
        e2e_sub = sel.sub_mesh.adjacencies["Edge2Elem"]
        for eidx in range(n_sub_edges):
            u, v = int(e2v_all[eidx, 0]), int(e2v_all[eidx, 1])
            if (min(u, v), max(u, v)) in fv:
                row = np.asarray(e2e_sub[eidx]).ravel()
                if row.size >= 2 and int(row[0]) >= 0 and int(row[1]) >= 0:
                    la2, lb2 = int(row[0]), int(row[1])
                    if la2 < glob.size and lb2 < glob.size:
                        flagged_global_pairs.add(
                            frozenset([int(glob[la2]), int(glob[lb2])])
                        )

    already = {int(glob[i]) for i in range(glob.size) if int(glob[i]) in paired}
    nl = int(getattr(domain, "n_layers", 0) or 0)
    is_boundary_layer = (li == nl - 1)

    try:
        greedy_pairs, _ = match_layer_heuristic(
            layer_conn=layer_conn,
            layer_global_ids=glob,
            ie_global_ids=ie_ids,
            oe_global_ids=oe_ids,
            pts=domain.points,
            flagged_pairs=flagged_global_pairs,
            already_consumed=already,
            is_boundary_layer=is_boundary_layer,
        )
    except Exception:
        greedy_pairs = []

    for la, lb in greedy_pairs:
        if la < glob.size and lb < glob.size:
            paired.add(int(glob[la]))
            paired.add(int(glob[lb]))

    return paired


def condition_triangulation(domain, *, max_hops=4, collect_stats=False):
    """Return NEW CHILmesh with point-preserving rewired connectivity for cleaner per-layer matching.

    Walks layers 0→N (outer to inner). For each layer, detects which tris would be
    leftover (unpaired) after quadmesh+'s own pairing heuristic, then applies edge-flip
    walks (walk_isolated_tri) to rewire them so they can pair. Does NOT mutate input.
    Same points, same element count (walks only flip edges — no point add/move).

    Args:
        domain: Input triangular CHILmesh (from create_quad_domain).
        max_hops: Max edge-flip walk depth per leftover tri (passed to walk_isolated_tri).
        collect_stats: If True, return (mesh, stats_list).

    Returns:
        Conditioned CHILmesh, or (CHILmesh, stats) if collect_stats=True.
        stats is list of dicts: {'layer': int, 'n_elems': int, 'unmatched_before': int,
                                 'unmatched_after': int, 'swaps': int}
    """
    # Copy to avoid mutating input
    conn = np.asarray(domain.connectivity_list).copy()
    pts = np.asarray(domain.points)
    nl = int(getattr(domain, "n_layers", 0) or 0)
    stats = []

    for li in range(nl):  # Outer (0) to inner (N)
        elem_ids = _layer_elem_ids(domain, li)
        if elem_ids.size == 0:
            continue

        # Detect which tris quadmesh+ would pair in this layer
        paired = _layer_paired_globals(domain, li)

        # Build local mapping and identify leftovers
        local_to_global = [int(g) for g in elem_ids]
        leftovers_local = [loc for loc, g in enumerate(local_to_global) if g not in paired]

        # Build WorkingMesh for this layer
        work = WorkingMesh(points=pts, quads=[])
        work.tris = [conn[g, :3].astype(int).copy() for g in local_to_global]

        rewired = 0
        for loc in leftovers_local:
            if work.tris[loc] is None:
                continue
            try:
                if walk_isolated_tri(work, loc, pts, max_hops=max_hops):
                    rewired += 1
            except Exception:
                pass

        # Write rewired tris back to conn
        for loc, g in enumerate(local_to_global):
            if work.tris[loc] is None:
                continue
            conn[g, 0:3] = [int(work.tris[loc][0]), int(work.tris[loc][1]), int(work.tris[loc][2])]

        stats.append({
            'layer': li,
            'n_elems': int(elem_ids.size),
            'unmatched_before': int(len(leftovers_local)),
            'unmatched_after': int(len(leftovers_local) - rewired),
            'swaps': int(rewired),
        })

    out = CHILmesh(conn, pts.copy(), grid_name=getattr(domain, "grid_name", None))
    if collect_stats:
        return out, stats
    return out
