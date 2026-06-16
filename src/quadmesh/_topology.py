"""Topology delegation: CCW edges (CHILmesh#133), tri merges (CHILmesh#207).

MATLAB: CCWEdgesAroundVertsFun.m, mergeTrianglesFun.m.
"""
from __future__ import annotations
import numpy as np
import chilmesh

def ccw_edges_around_vert(mesh, vert_ids):
    """Sort edges incident to each vert by polar angle, CCW."""
    vert_ids = np.asarray(list(vert_ids), dtype=int).ravel()
    return [np.asarray(mesh.ccw_edges_around_vert(int(v)), dtype=int) for v in vert_ids]

def _ccw_order(points: np.ndarray, quad) -> np.ndarray:
    """Return the quad's 4 vertex ids in CCW convex-perimeter order.

    quad_from_tri_pair can return vertices in a non-cyclic order, which makes a
    perfectly good quad read as degenerate. Sorting the 4 corners by polar angle
    about their centroid recovers the simple convex quad (a no-op when the input
    is already cyclic). Only applied to genuine 4-distinct-vertex quads.
    """
    q = np.asarray(quad, dtype=int).ravel()
    if q.size != 4 or len(set(int(v) for v in q)) != 4:
        return q
    pts = np.asarray(points)[q, :2]
    c = pts.mean(axis=0)
    ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
    return q[np.argsort(ang)]

def merge_tri_pair(mesh, elem_id_a: int, elem_id_b: int) -> np.ndarray:
    """Merge two tris sharing an edge into one quad. Return 4-vert connectivity."""
    conn = mesh.connectivity_list
    tri_a = conn[elem_id_a, :3].astype(int)
    tri_b = conn[elem_id_b, :3].astype(int)
    quad = chilmesh.quad_from_tri_pair(mesh.points, tri_a, tri_b)
    return _ccw_order(mesh.points, quad)

def merge_tri_pairs(mesh, pair_elem_ids: np.ndarray) -> np.ndarray:
    """Vector form. ``pair_elem_ids`` is shape ``(n, 2)``. Returns ``(n, 4)`` quads."""
    pair_elem_ids = np.atleast_2d(np.asarray(pair_elem_ids, dtype=int))
    return chilmesh.quads_from_tri_pairs(mesh.points, mesh.connectivity_list, pair_elem_ids)
