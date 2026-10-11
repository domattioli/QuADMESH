"""Metrics: boundary preservation and residual split (spec 058 R5, R6)."""
from __future__ import annotations

import numpy as np

from quadmesh.benchmark._metrics import boundary_preservation, residual_split

# Square fan: centre vertex 4, four triangles; every triangle touches the boundary.
P = np.array([[0, 0], [2, 0], [2, 2], [0, 2], [1, 1]], float)
FAN = np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]])


def test_boundary_identity():
    assert boundary_preservation(P, FAN, P, FAN) == (0, 0)


def test_boundary_shifted_vertex():
    q = P.copy()
    q[1] += [0.1, 0.0]
    lost, added = boundary_preservation(P, FAN, q, FAN)
    assert (lost, added) == (1, 1)  # one input vertex lost, one new appears


def test_residual_split_all_boundary():
    assert residual_split(FAN) == (0, 4)


def test_residual_split_interior_triangle():
    # Triangle 0,1,2 ringed by three triangles: its three edges are all shared.
    p = np.array([[0, 0], [4, 0], [2, 3], [2, -2], [6, 2], [-2, 2]], float)
    c = np.array([[0, 1, 2], [0, 3, 1], [1, 4, 2], [2, 5, 0]])
    assert residual_split(c) == (1, 3)


def test_padded_triangle_counts_as_triangle():
    c = np.array([[0, 1, 2, 2]])
    assert residual_split(c) == (0, 1)
