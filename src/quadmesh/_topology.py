"""Topology helpers. CCW edge sorting around verts. Merge tri pairs to quads.

``ccw_edges_around_vert`` delegates to CHILmesh #133 (canonical owner per
MADMESHing#48 unification). ``merge_tri_pair``/``merge_tri_pairs`` stay local
pending a pure (non-mutating) upstream helper — CHILmesh#207 (`merge_elements`
#132 mutates + rebuilds adjacencies per call, wrong shape for the per-layer sweep).

MATLAB src: CCWEdgesAroundVertsFun.m, mergeTrianglesFun.m.
"""

from __future__ import annotations

from typing import List, Sequence

import numpy as np


def ccw_edges_around_vert(mesh, vert_ids: Sequence[int]) -> List[np.ndarray]:
    """Sort edges incident to each vert by polar angle, CCW.

    Thin shim over ``CHILmesh.ccw_edges_around_vert`` (CHILmesh#133), the
    canonical owner of this op per the MADMESHing#48 unification map.

    Args:
        mesh: CHILmesh instance (adjacencies built).
        vert_ids: Iterable of global vertex IDs.

    Returns:
        List of 1-D arrays (one per input vert) of edge IDs in CCW order.
    """
    vert_ids = np.asarray(list(vert_ids), dtype=int).ravel()
    return [
        np.asarray(mesh.ccw_edges_around_vert(int(v)), dtype=int)
        for v in vert_ids
    ]


# Local pure impl kept: CHILmesh merge_elements (#132) mutates the mesh — see CHILmesh#207.
def merge_tri_pair(mesh, elem_id_a: int, elem_id_b: int) -> np.ndarray:
    """Merge two tris sharing an edge into one quad. Return 4-vert connectivity.

    Quads are CCW. Shared edge is removed; opposing vertices form the new diagonal.
    """
    conn = mesh.connectivity_list
    t1 = conn[elem_id_a, :3].astype(int)
    t2 = conn[elem_id_b, :3].astype(int)

    shared = np.intersect1d(t1, t2, assume_unique=False)
    if shared.size != 2:
        raise ValueError(
            f"Elems {elem_id_a},{elem_id_b} do not share exactly 2 verts (got {shared.size})"
        )

    unique_b = int(np.setdiff1d(t2, shared, assume_unique=False)[0])
    # Rotate t1 so shared edge sits at positions (0,1); unique-of-t1 ends up at index 2.
    # Then quad = [t1[0], unique_b, t1[1], t1[2]] preserves CCW.
    # Find unique-of-t1.
    unique_a = int(np.setdiff1d(t1, shared, assume_unique=False)[0])
    iu = int(np.where(t1 == unique_a)[0][0])
    rotated = np.roll(t1, -iu)  # rotated[0] = unique_a
    # rotated = [unique_a, s1, s2]. Insert unique_b between s1 and s2 to form quad
    # [unique_a, s1, unique_b, s2] which is CCW if both tris were CCW.
    quad = np.array([rotated[0], rotated[1], unique_b, rotated[2]], dtype=int)
    return quad


def merge_tri_pairs(mesh, pair_elem_ids: np.ndarray) -> np.ndarray:
    """Vector form. ``pair_elem_ids`` is shape ``(n, 2)``.

    Returns ``(n, 4)`` quad connectivity (CCW assuming CCW input).
    """
    pair_elem_ids = np.atleast_2d(np.asarray(pair_elem_ids, dtype=int))
    if pair_elem_ids.shape[1] != 2:
        raise ValueError(f"pair_elem_ids must be (n,2); got {pair_elem_ids.shape}")
    quads = np.empty((pair_elem_ids.shape[0], 4), dtype=int)
    for i, (a, b) in enumerate(pair_elem_ids):
        quads[i] = merge_tri_pair(mesh, int(a), int(b))
    return quads
