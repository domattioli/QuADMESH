"""End-to-end pipeline driver. Equivalent of Main.m without the GUI."""

from __future__ import annotations

from typing import Optional

import numpy as np

from chilmesh import CHILmesh

from .create_quad_domain import create_quad_domain
from .post_process import post_process_routine
from .tri2quad import tri2quad_routine


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
    precondition: bool = False,
    precondition_kwargs: Optional[dict] = None,
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
        precondition: If True, apply triangulation conditioning before tri2quad.
        precondition_kwargs: Optional dict of kwargs for condition_triangulation.

    Returns:
        Final quad CHILmesh.
    """
    domain = create_quad_domain(mesh, polygon=polygon)
    if precondition:
        from .precondition import condition_triangulation
        domain = condition_triangulation(domain, **(precondition_kwargs or {}))
    quad = tri2quad_routine(
        domain, can_remove_edges=can_remove_edges, parent=mesh, method=method
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
        )
    return quad
