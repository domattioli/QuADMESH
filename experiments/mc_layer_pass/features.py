"""Per-triangle topology / quality / size features for the MC layer-pass study.

Every feature is an array of length N == number of triangles in ``domain``,
indexed by the original triangle id (row of ``domain.connectivity_list``), so it
aligns 1:1 with the Monte-Carlo per-triangle "routed" counts.
"""
from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree


def compute_tri_features(domain) -> dict:
    """Return a dict of per-triangle feature arrays (each shape (N,)).

    Keys:
      tri_idx, cx, cy, area, perimeter, edge_min, edge_max, edge_mean,
      aspect_ratio (edge_max/edge_min), min_angle_deg, max_angle_deg,
      radius_ratio (2*r_in/r_circ, equilateral->1, in [0,1]),
      n_boundary_edges (0..3), deg_mean, deg_max, deg_min (vertex tri-incidence
      degrees), layer (skeleton-layer index or -1), is_IE (0/1), is_OE (0/1),
      n_tri_neighbours (0..3), size_ratio (area / mean adjacent-tri area; 1.0 if
      isolated), bdy_dist (centroid distance to nearest boundary vertex).
    """
    conn = np.asarray(domain.connectivity_list)[:, :3].astype(int)
    N = conn.shape[0]
    P = np.asarray(domain.points)[:, :2].astype(float)

    v0, v1, v2 = conn[:, 0], conn[:, 1], conn[:, 2]
    p0, p1, p2 = P[v0], P[v1], P[v2]

    # Centroid.
    cx = (p0[:, 0] + p1[:, 0] + p2[:, 0]) / 3.0
    cy = (p0[:, 1] + p1[:, 1] + p2[:, 1]) / 3.0

    # Edge lengths: a=|p1-p2| (opp v0), b=|p2-p0| (opp v1), c=|p0-p1| (opp v2).
    a = np.linalg.norm(p1 - p2, axis=1)
    b = np.linalg.norm(p2 - p0, axis=1)
    c = np.linalg.norm(p0 - p1, axis=1)
    E = np.vstack([a, b, c]).T  # (N,3)
    edge_min = E.min(axis=1)
    edge_max = E.max(axis=1)
    edge_mean = E.mean(axis=1)
    perimeter = a + b + c
    with np.errstate(divide="ignore", invalid="ignore"):
        aspect_ratio = np.where(edge_min > 0, edge_max / edge_min, np.inf)

    # Signed area -> |area|.
    cross = (p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1]) - (p1[:, 1] - p0[:, 1]) * (p2[:, 0] - p0[:, 0])
    area = 0.5 * np.abs(cross)

    # Interior angles (law of cosines), degrees. Clip for numerical safety.
    def ang(opp, s1, s2):
        with np.errstate(divide="ignore", invalid="ignore"):
            cosv = (s1 ** 2 + s2 ** 2 - opp ** 2) / (2.0 * s1 * s2)
        cosv = np.clip(cosv, -1.0, 1.0)
        return np.degrees(np.arccos(cosv))

    ang0 = ang(a, b, c)  # angle at v0 (opposite edge a)
    ang1 = ang(b, c, a)  # angle at v1
    ang2 = ang(c, a, b)  # angle at v2
    A = np.vstack([ang0, ang1, ang2]).T
    min_angle_deg = np.nanmin(A, axis=1)
    max_angle_deg = np.nanmax(A, axis=1)

    # Radius ratio quality: r_in = 2*area/perimeter; r_circ = (a*b*c)/(4*area);
    # quality = 2*r_in/r_circ in [0,1] (1 == equilateral).
    with np.errstate(divide="ignore", invalid="ignore"):
        r_in = np.where(perimeter > 0, 2.0 * area / perimeter, 0.0)
        r_circ = np.where(area > 0, (a * b * c) / (4.0 * area), np.inf)
        radius_ratio = np.where(r_circ > 0, 2.0 * r_in / r_circ, 0.0)
    radius_ratio = np.clip(radius_ratio, 0.0, 1.0)

    # Edge -> incident triangles (sorted vertex pair as key).
    edge2tris: dict = {}
    for i in range(N):
        t = conn[i]
        for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            key = (int(min(e)), int(max(e)))
            edge2tris.setdefault(key, []).append(i)

    n_boundary_edges = np.zeros(N, dtype=int)
    n_tri_neighbours = np.zeros(N, dtype=int)
    nbr_area_sum = np.zeros(N, dtype=float)
    nbr_count = np.zeros(N, dtype=int)
    for i in range(N):
        t = conn[i]
        for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            key = (int(min(e)), int(max(e)))
            inc = edge2tris[key]
            if len(inc) == 1:
                n_boundary_edges[i] += 1
            elif len(inc) == 2:
                n_tri_neighbours[i] += 1
                j = inc[0] if inc[1] == i else inc[1]
                nbr_area_sum[i] += area[j]
                nbr_count[i] += 1
    with np.errstate(divide="ignore", invalid="ignore"):
        mean_nbr_area = np.where(nbr_count > 0, nbr_area_sum / np.maximum(nbr_count, 1), area)
        size_ratio = np.where(mean_nbr_area > 0, area / mean_nbr_area, 1.0)
    size_ratio = np.where(nbr_count > 0, size_ratio, 1.0)

    # Vertex tri-incidence degree.
    vdeg = np.bincount(conn.ravel(), minlength=P.shape[0])
    deg_tri = vdeg[conn]  # (N,3)
    deg_mean = deg_tri.mean(axis=1)
    deg_max = deg_tri.max(axis=1)
    deg_min = deg_tri.min(axis=1)

    # Skeleton-layer membership.
    layer = np.full(N, -1, dtype=int)
    is_IE = np.zeros(N, dtype=int)
    is_OE = np.zeros(N, dtype=int)
    layers = domain.layers
    nl = int(getattr(domain, "n_layers", 0) or 0)
    for li in range(nl):
        for e in np.asarray(layers["IE"][li], dtype=int):
            if 0 <= int(e) < N:
                layer[int(e)] = li
                is_IE[int(e)] = 1
        for e in np.asarray(layers["OE"][li], dtype=int):
            if 0 <= int(e) < N:
                layer[int(e)] = li
                is_OE[int(e)] = 1

    # Boundary distance: centroid -> nearest boundary vertex (KDTree).
    bverts = sorted({v for key, inc in edge2tris.items() if len(inc) == 1 for v in key})
    if bverts:
        tree = cKDTree(P[np.asarray(bverts, dtype=int)])
        bdy_dist, _ = tree.query(np.vstack([cx, cy]).T)
    else:
        bdy_dist = np.zeros(N, dtype=float)

    return {
        "tri_idx": np.arange(N),
        "cx": cx, "cy": cy, "area": area, "perimeter": perimeter,
        "edge_min": edge_min, "edge_max": edge_max, "edge_mean": edge_mean,
        "aspect_ratio": aspect_ratio, "min_angle_deg": min_angle_deg,
        "max_angle_deg": max_angle_deg, "radius_ratio": radius_ratio,
        "n_boundary_edges": n_boundary_edges, "deg_mean": deg_mean,
        "deg_max": deg_max, "deg_min": deg_min, "layer": layer,
        "is_IE": is_IE, "is_OE": is_OE, "n_tri_neighbours": n_tri_neighbours,
        "size_ratio": size_ratio, "bdy_dist": bdy_dist,
    }


if __name__ == "__main__":
    import sys
    from chilmesh import CHILmesh
    m = CHILmesh.read_from_fort14(sys.argv[1] if len(sys.argv) > 1 else "/tmp/WNAT_Test.14")
    f = compute_tri_features(m)
    print("N =", len(f["tri_idx"]))
    for k, v in f.items():
        arr = np.asarray(v, dtype=float)
        finite = arr[np.isfinite(arr)]
        print(f"{k:18s} min={finite.min():.4g} max={finite.max():.4g} mean={finite.mean():.4g}")
