"""End-to-end pipeline driver. Equivalent of Main.m without the GUI."""

from __future__ import annotations

from typing import Optional

import numpy as np

from chilmesh import CHILmesh

from .create_quad_domain import create_quad_domain
from .post_process import post_process_routine
from .tri2quad import tri2quad_routine


class InteriorTriangleError(RuntimeError):
    """QuADMESH+ output holds an interior triangle (operator ruling
    2026-11-04: zero interior triangles is a hard rule).

    Attributes:
        mesh: The offending output mesh, for inspection.
        rows: Row indices into ``mesh.connectivity_list`` of the interior
            triangles.
    """

    def __init__(self, mesh: CHILmesh, rows) -> None:
        self.mesh = mesh
        self.rows = [int(r) for r in rows]
        cl = np.asarray(mesh.connectivity_list)
        shown = ", ".join(
            f"{r}: {list(dict.fromkeys(int(v) for v in cl[r]))}" for r in self.rows[:5]
        )
        more = "" if len(self.rows) <= 5 else f" (+{len(self.rows) - 5} more)"
        super().__init__(
            f"QuADMESH+ output has {len(self.rows)} interior triangle(s) "
            f"(no edge on the domain boundary); rows {shown}{more}"
        )


def interior_triangle_rows(mesh: CHILmesh) -> list:
    """Rows of ``mesh`` that are interior triangles.

    Same definition as ``tests/test_no_interior_tris.py``: a row with three
    distinct vertices (a padded ``[a, b, c, c]`` row counts) none of whose
    edges is a boundary edge, i.e. an edge used by exactly one element after
    padding is removed.
    """
    elems = []
    for row in np.asarray(mesh.connectivity_list):
        vs = [int(x) for x in row]
        uniq = list(dict.fromkeys(vs))
        elems.append(tuple(uniq) if len(uniq) == 3 else tuple(vs))

    def edges(el):
        n = len(el)
        return [tuple(sorted((el[i], el[(i + 1) % n]))) for i in range(n)]

    count: dict = {}
    for el in elems:
        for e in edges(el):
            count[e] = count.get(e, 0) + 1
    return [
        i for i, el in enumerate(elems)
        if len(el) == 3 and not any(count[e] == 1 for e in edges(el))
    ]


def run_pipeline(
    mesh: CHILmesh,
    polygon: Optional[np.ndarray] = None,
    can_remove_edges: bool = True,
    n_smooth_iter: int = 3,
    do_post_process: bool = True,
    max_outer_iter: int = 5,
    max_inner_iter: int = 5,
    method: str = "quadmesh+",
    truss_smooth: bool = False,
    truss_fh=None,
    refuse_boundary_merge: bool = False,
    preserve_boundary: bool = False,
    fan_valence4: bool = False,
) -> CHILmesh:
    """Full create_quad_domain → tri2quad → post_process sweep.

    Args:
        mesh: Input triangular CHILmesh.
        polygon: Optional polygon mask for partial conversion.
        can_remove_edges: Allow edge_removal + boundary-quad collapse.
        n_smooth_iter: Iterations for the alternating angle/FEM smoother.
        do_post_process: If False, skip post-process (raw tri2quad output).
        max_outer_iter: Outer loop cap in post_process_routine.
        max_inner_iter: Inner loop cap (doublet + QVM) in post_process_routine.
        method: tri2quad pairing method — ``"quadmesh+"`` (default and only
            method; ``"layered"`` mechanism alias). ``"matching"`` and
            ``"faithful"`` removed per #46.
        truss_smooth: If True, apply truss_smoother before fem_smoother.
        truss_fh: Callable or None. Target edge length function for truss_smoother.
        refuse_boundary_merge: pass-through to tri2quad_routine (#98 option A,
            default OFF). Emit 2-3-boundary-edge leftover tris as boundary
            triangles instead of degenerate quads.
        preserve_boundary: If True, keep every boundary vertex of the input
            mesh. Boundary-quad cleanup skips collapses and shifts that would
            delete or move one. Default False (MATLAB-faithful).
        fan_valence4: If True, close a leftover triangle on an interior ring
            edge with a valence-4 fan instead of a plain bisect (#133).
            Default False: output unchanged.

    Returns:
        Final quad CHILmesh.

    Raises:
        InteriorTriangleError: the output has a triangle with no edge on
            the domain boundary (``interior_triangle_rows``). Zero interior
            triangles is a hard rule of QuADMESH+; there is no opt-out.
    """
    protected = None
    if preserve_boundary:
        from .cleanup_boundary_quads import boundary_points
        protected = boundary_points(mesh)
    domain = create_quad_domain(mesh, polygon=polygon)
    quad = tri2quad_routine(
        domain, can_remove_edges=can_remove_edges, parent=mesh, method=method,
        refuse_boundary_merge=refuse_boundary_merge,
        fan_valence4=fan_valence4,
    )
    if do_post_process:
        quad = post_process_routine(
            quad,
            can_remove_edges=can_remove_edges,
            n_smooth_iter=n_smooth_iter,
            max_outer_iter=max_outer_iter,
            max_inner_iter=max_inner_iter,
            truss_smooth=truss_smooth,
            truss_fh=truss_fh,
            preserve_boundary=preserve_boundary,
            protected_points=protected,
        )
    bad = interior_triangle_rows(quad)
    if bad:
        raise InteriorTriangleError(quad, bad)
    return quad
