"""Greedy triangle-merge baseline.

Scans triangles in index order and merges each unmerged triangle with the unmerged
neighbour across a non-boundary edge that gives the best skew for the resulting
convex quad (skew >= 0.1). Leftovers stay triangles. Deterministic.

Standard greedy triangle recombination; a reference baseline, not a contribution of this package.
"""
from __future__ import annotations

import time

import numpy as np
from chilmesh import CHILmesh, element_quality

from .. import _protocol as P

MIN_SKEW = 0.1


def _ccw(points, tri):
    a, b, c = (points[i] for i in tri)
    area2 = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return list(tri) if area2 >= 0 else [tri[0], tri[2], tri[1]]


def _convex(points, q) -> bool:
    for i in range(4):
        a, b, c = points[q[i]], points[q[(i + 1) % 4]], points[q[(i + 2) % 4]]
        if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) <= 0:
            return False
    return True


def greedy_merge(points: np.ndarray, tris: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, float)[:, :2]
    T = [_ccw(pts, t) for t in np.asarray(tris)]
    edge_tris: dict = {}
    for ti, t in enumerate(T):
        for k in range(3):
            edge_tris.setdefault(frozenset((t[k], t[(k + 1) % 3])), []).append(ti)
    used = [False] * len(T)
    out: list = []
    for ti, t in enumerate(T):
        if used[ti]:
            continue
        best, best_q = MIN_SKEW, None
        for k in range(3):
            u, v, p = t[k], t[(k + 1) % 3], t[(k + 2) % 3]
            nb = [x for x in edge_tris[frozenset((u, v))] if x != ti]
            if len(nb) != 1 or used[nb[0]]:
                continue  # domain-boundary edge or neighbour taken
            tb = T[nb[0]]
            q = [x for x in tb if x not in (u, v)][0]
            quad = [u, q, v, p]
            if not _convex(pts, quad):
                continue
            s = float(element_quality(np.asarray(points, float), np.array([quad]),
                                      metric="skew")[0])
            if s >= best:
                best, best_q = s, (nb[0], quad)
        if best_q is None:
            out.append(t)
        else:
            used[ti] = used[best_q[0]] = True
            out.append(best_q[1])
        used[ti] = True
    if all(len(r) == 3 for r in out):
        return np.array(out, dtype=int)
    return np.array([r if len(r) == 4 else r + [r[2]] for r in out], dtype=int)


@P.register
class GreedyTriMerge:
    name = "greedy-tri-merge"
    display_name = "greedy recombination (baseline)"
    family = "indirect-recombine"
    license_tag = "clean-room"
    citation = "Standard greedy triangle recombination (reference baseline)."
    install_route = "base"
    install_hint = P.install_route_hint("base")
    accepts_mixed = False

    def probe(self) -> P.Availability:
        return P.Availability(True, "built-in", None, "")

    def run(self, mesh, options: P.AdapterOptions) -> P.AdapterResult:
        t0 = time.perf_counter()
        pts = np.array(mesh.points)
        conn = greedy_merge(pts, np.asarray(mesh.connectivity_list))
        out = CHILmesh(conn, pts)
        return P.AdapterResult(
            mesh=out, adapter=self.name, version="built-in",
            license_tag=self.license_tag, runtime_s=time.perf_counter() - t0,
            vertex_order_preserved=True,
        )
