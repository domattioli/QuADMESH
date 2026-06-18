"""Vertex-valence and gridded-flow / direction-disruption per-triangle features.

Complements features.py (follow-up to the valence + flow-disruption questions on
PR #96). All arrays have length N == number of triangles, indexed by original
triangle id, so they align with the MC pass counts.
"""
from __future__ import annotations

import numpy as np


def compute_extra_features(domain) -> dict:
    conn = np.asarray(domain.connectivity_list)[:, :3].astype(int)
    N = conn.shape[0]
    P = np.asarray(domain.points)[:, :2].astype(float)
    nP = P.shape[0]

    # Edge map + per-vertex neighbour sets (edge valence).
    edge2tris: dict = {}
    vert_nbrs = [set() for _ in range(nP)]
    for i in range(N):
        t = conn[i]
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            key = (int(min(a, b)), int(max(a, b)))
            edge2tris.setdefault(key, []).append(i)
            vert_nbrs[int(a)].add(int(b))
            vert_nbrs[int(b)].add(int(a))

    valence = np.array([len(s) for s in vert_nbrs], dtype=int)
    bvert = np.zeros(nP, dtype=bool)
    for key, inc in edge2tris.items():
        if len(inc) == 1:
            bvert[key[0]] = True
            bvert[key[1]] = True
    ideal = np.where(bvert, 4, 6)  # ideal valence: 6 interior, 4 boundary
    valence_irreg = np.abs(valence - ideal)

    val_tri = valence[conn]
    irr_tri = valence_irreg[conn]
    mean_valence = val_tri.mean(axis=1).astype(float)
    max_valence = val_tri.max(axis=1).astype(float)
    min_valence = val_tri.min(axis=1).astype(float)
    valence_irreg_mean = irr_tri.mean(axis=1).astype(float)
    valence_irreg_max = irr_tri.max(axis=1).astype(float)
    n_irregular_verts = (irr_tri > 0).sum(axis=1).astype(int)

    # Triangle orientation = direction of longest edge (undirected, period pi).
    p0, p1, p2 = P[conn[:, 0]], P[conn[:, 1]], P[conn[:, 2]]
    edges = np.stack([p1 - p0, p2 - p1, p0 - p2], axis=1)  # (N,3,2)
    elen = np.linalg.norm(edges, axis=2)
    li = np.argmax(elen, axis=1)
    longvec = edges[np.arange(N), li]
    theta = np.arctan2(longvec[:, 1], longvec[:, 0])
    two = 2.0 * theta
    ux, uy = np.cos(two), np.sin(two)

    area = 0.5 * np.abs(
        (p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1])
        - (p1[:, 1] - p0[:, 1]) * (p2[:, 0] - p0[:, 0])
    )

    adj = [[] for _ in range(N)]
    for inc in edge2tris.values():
        if len(inc) == 2:
            adj[inc[0]].append(inc[1])
            adj[inc[1]].append(inc[0])

    flow_disorder = np.full(N, np.nan)
    flow_misalign = np.full(N, np.nan)
    log_size_gradient = np.full(N, np.nan)
    for i in range(N):
        nb = adj[i]
        if not nb:
            continue
        mx, my = ux[nb].mean(), uy[nb].mean()
        R = float(np.hypot(mx, my))  # neighbour orientation coherence in [0,1]
        flow_disorder[i] = 1.0 - R
        if R > 1e-9:
            ang_nb = np.arctan2(my, mx)
            d = 0.5 * (two[i] - ang_nb)
            flow_misalign[i] = abs(np.sin(d))  # 0 aligned .. 1 perpendicular
        if area[i] > 0:
            na = area[nb]
            na = na[na > 0]
            if na.size:
                log_size_gradient[i] = abs(np.log(area[i]) - np.log(na).mean())

    # Layer-flow misalignment: tri long-axis vs its skeleton-layer path tangent.
    layer_flow_misalign = np.full(N, np.nan)
    try:
        from chilmesh.layer_paths import paths_on_outer_vertices
        nl = int(getattr(domain, "n_layers", 0) or 0)
        vtan = np.full((nP, 2), np.nan)
        for lyr in range(nl):
            for path in paths_on_outer_vertices(domain, lyr):
                pv = np.asarray(path, dtype=int)
                if pv.size < 2:
                    continue
                if pv[0] == pv[-1]:
                    pv = pv[:-1]
                for k in range(pv.size):
                    a = pv[k]
                    b = pv[(k + 1) % pv.size]
                    tvec = P[b] - P[a]
                    n = float(np.hypot(*tvec))
                    if n > 0:
                        vtan[a] = tvec / n
        for i in range(N):
            ts = vtan[conn[i]]
            ts = ts[~np.isnan(ts[:, 0])]
            if ts.size == 0:
                continue
            tm = ts.mean(axis=0)
            n = float(np.hypot(*tm))
            if n < 1e-9:
                continue
            tm /= n
            lv = longvec[i]
            ln = float(np.hypot(*lv))
            if ln < 1e-9:
                continue
            lvn = lv / ln
            layer_flow_misalign[i] = abs(lvn[0] * tm[1] - lvn[1] * tm[0])
    except Exception:
        pass

    return {
        "mean_valence": mean_valence, "max_valence": max_valence,
        "min_valence": min_valence, "valence_irreg_mean": valence_irreg_mean,
        "valence_irreg_max": valence_irreg_max, "n_irregular_verts": n_irregular_verts,
        "flow_disorder": flow_disorder, "flow_misalign": flow_misalign,
        "log_size_gradient": log_size_gradient,
        "layer_flow_misalign": layer_flow_misalign,
    }
