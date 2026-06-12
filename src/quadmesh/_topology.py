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

def merge_tri_pair(mesh, elem_id_a: int, elem_id_b: int) -> np.ndarray:
    """Merge two tris sharing an edge into one quad. Return 4-vert connectivity."""
    conn = mesh.connectivity_list
    tri_a = conn[elem_id_a, :3].astype(int)
    tri_b = conn[elem_id_b, :3].astype(int)
    return chilmesh.quad_from_tri_pair(mesh.points, tri_a, tri_b)

def merge_tri_pairs(mesh, pair_elem_ids: np.ndarray) -> np.ndarray:
    """Vector form. ``pair_elem_ids`` is shape ``(n, 2)``. Returns ``(n, 4)`` quads."""
    pair_elem_ids = np.atleast_2d(np.asarray(pair_elem_ids, dtype=int))
    return chilmesh.quads_from_tri_pairs(mesh.points, mesh.connectivity_list, pair_elem_ids)
