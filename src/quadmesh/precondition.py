"""Conditions a triangular CHILmesh so each layer admits a cleaner intra-layer perfect matching, by detecting tris antagonistic to perfect matching and applying edge swaps (thesis Fig 3.2 recombination) to rewire them. Points are never moved or added — only connectivity is rewired. Experimental, opt-in."""

from __future__ import annotations

from typing import Optional, List, Tuple, Set

import numpy as np
from chilmesh import CHILmesh

from ._recombine import edge_swap
from ._tri_removal import WorkingMesh


def _layer_elem_ids(domain, li) -> np.ndarray:
    """Return all tri IDs (OE + IE) in layer li."""
    layers = domain.layers
    oe = np.asarray(layers["OE"][li], dtype=int)
    ie = np.asarray(layers["IE"][li], dtype=int)
    return np.concatenate([oe, ie]) if oe.size or ie.size else np.empty(0, dtype=int)


def _tri_edges(row) -> list[tuple[int, int]]:
    """Return 3 undirected edges of triangle (first 3 verts of row) as sorted tuples."""
    v = [int(row[0]), int(row[1]), int(row[2])]
    return [tuple(sorted((v[0], v[1]))), tuple(sorted((v[1], v[2]))), tuple(sorted((v[2], v[0])))]


def _build_dual_graph(tris, iv_set):
    """Build dual graph: nodes are local tri indices, edges connect tris sharing non-fold-seam edges.

    Returns (G, edge_to_local) where:
    - G is networkx.Graph with nodes = live tri indices
    - edge_to_local maps vertex-edge tuple -> list of local tri indices sharing it
    """
    try:
        import networkx as nx
    except ImportError:
        raise ImportError("conditioning requires networkx: pip install quadmesh[experimental]")

    edge_to_local = {}
    for i, t in enumerate(tris):
        if t is None:
            continue
        for e in _tri_edges(t):
            edge_to_local.setdefault(e, []).append(i)

    G = nx.Graph()
    G.add_nodes_from([i for i, t in enumerate(tris) if t is not None])

    for e, locs in edge_to_local.items():
        if len(locs) != 2:
            continue
        # Skip fold-seam edges (both endpoints in inner-vertex set)
        if (e[0] in iv_set) and (e[1] in iv_set):
            continue
        G.add_edge(locs[0], locs[1])

    return G, edge_to_local


def _unmatched_locals(tris, iv_set) -> set[int]:
    """Return set of local tri indices not matched in max cardinality matching."""
    try:
        import networkx as nx
    except ImportError:
        raise ImportError("conditioning requires networkx: pip install quadmesh[experimental]")

    G, _ = _build_dual_graph(tris, iv_set)
    matching = nx.max_weight_matching(G, maxcardinality=True)
    matched = set()
    for a, b in matching:
        matched.add(a)
        matched.add(b)
    return {n for n in G.nodes if n not in matched}


def _tri_quality(pts, tri, metric: str = "aspect_ratio") -> float:
    """Quality of a single triangle (higher = better; ~1 ideal, ~0 sliver).

    Returns 0.0 on degenerate/failed evaluation so a bad result never reads as
    'good'. Lazy-imports element_quality so the module still imports on a
    chilmesh build that lacks it (quality_aware is opt-in).
    """
    try:
        from chilmesh import element_quality
        q = element_quality(pts, [[int(tri[0]), int(tri[1]), int(tri[2])]], metric=metric)
        v = float(np.asarray(q).ravel()[0])
        return 0.0 if v != v else v  # nan -> 0.0
    except Exception:
        return 0.0


def condition_triangulation(domain, *, max_passes_per_layer=6, quality_aware=False,
                            quality_metric="aspect_ratio", quality_eps=1e-9,
                            collect_stats=False):
    """Return NEW CHILmesh with rewired connectivity for cleaner per-layer matching.

    Does NOT mutate input. Same points, same element count (swaps preserve both).

    Args:
        domain: Input triangular CHILmesh (from create_quad_domain).
        max_passes_per_layer: Max edge-swap iterations per layer.
        quality_aware: If True, accept a swap only when it BOTH reduces the
            unmatched count AND does not lower the worst incident triangle
            quality (worst_after >= worst_before - quality_eps).
        quality_metric: Metric for incident-quality check ("aspect_ratio" or "skew";
            higher = better for both).
        quality_eps: Tolerance for the worst-incident-quality comparison.
        collect_stats: If True, return (mesh, stats_list).

    Returns:
        Conditioned CHILmesh, or (CHILmesh, stats) if collect_stats=True.
        stats is list of dicts: {'layer': int, 'n_elems': int, 'unmatched_before': int,
                                 'unmatched_after': int, 'swaps': int}
    """
    # Copy to avoid mutating input
    work_domain = domain.copy()
    conn = np.asarray(work_domain.connectivity_list).copy()
    pts = np.asarray(work_domain.points)
    nl = int(getattr(work_domain, "n_layers", 0) or 0)
    stats = []

    for li in range(nl):  # Outer (0) to inner (N)
        elem_ids = _layer_elem_ids(work_domain, li)
        if elem_ids.size == 0:
            continue

        iv_set = set(int(v) for v in np.asarray(work_domain.layers["IV"][li], dtype=int))

        # Build WorkingMesh local tris with mapping to global elem ids
        local_to_global = [int(g) for g in elem_ids]
        tris = [conn[g, :3].astype(int).copy() for g in local_to_global]
        work = WorkingMesh(points=pts, quads=[])
        work.tris = tris

        before = len(_unmatched_locals(work.tris, iv_set))
        swaps = 0

        # Iterative edge-swap: greedily reduce unmatched count per layer
        for _ in range(max_passes_per_layer):
            unmatched = _unmatched_locals(work.tris, iv_set)
            if not unmatched:
                break

            improved = False
            cur = len(unmatched)

            for u in list(unmatched):
                if work.tris[u] is None:
                    continue

                made = False
                for (va, vb) in _tri_edges(work.tris[u]):
                    # Skip fold-seam edges
                    if (va in iv_set) and (vb in iv_set):
                        continue

                    # Find tris sharing this edge
                    sharers = [k for k, t in enumerate(work.tris)
                               if t is not None and va in set(int(x) for x in t[:3])
                               and vb in set(int(x) for x in t[:3])]
                    if len(sharers) != 2:
                        continue

                    i, j = sharers
                    snap_i = work.tris[i].copy()
                    snap_j = work.tris[j].copy()

                    # Try swap
                    if edge_swap(work, va, vb, pts):
                        new_unmatched = len(_unmatched_locals(work.tris, iv_set))
                        accept = new_unmatched < cur
                        if accept and quality_aware:
                            worst_before = min(_tri_quality(pts, snap_i, quality_metric),
                                               _tri_quality(pts, snap_j, quality_metric))
                            worst_after = min(_tri_quality(pts, work.tris[i], quality_metric),
                                              _tri_quality(pts, work.tris[j], quality_metric))
                            if worst_after < worst_before - quality_eps:
                                accept = False
                        if accept:
                            swaps += 1
                            made = True
                            break
                        else:
                            # Revert
                            work.tris[i] = snap_i
                            work.tris[j] = snap_j

                if made:
                    improved = True
                    break

            if not improved:
                break

        after = len(_unmatched_locals(work.tris, iv_set))

        # Write rewired tris back to conn
        for loc, g in enumerate(local_to_global):
            if work.tris[loc] is None:
                continue
            conn[g, 0] = int(work.tris[loc][0])
            conn[g, 1] = int(work.tris[loc][1])
            conn[g, 2] = int(work.tris[loc][2])

        stats.append({
            'layer': li,
            'n_elems': int(elem_ids.size),
            'unmatched_before': int(before),
            'unmatched_after': int(after),
            'swaps': int(swaps)
        })

    out = CHILmesh(conn, pts.copy(), grid_name=getattr(domain, "grid_name", None))
    if collect_stats:
        return out, stats
    return out
