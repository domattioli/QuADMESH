"""Tests for truss_smoother quad row detection (issue #88).

Padded boundary triangles are stored as [v0, v1, v2, v2] (last vertex
repeated). A simple len(elem)==4 check on a rectangular N×4 array fails
because every row has 4 elements. The canonical arity test row[2]!=row[3]
correctly identifies genuine quads vs. padded triangles.
"""

from __future__ import annotations

import numpy as np

from quadmesh.post_process import _quad_rows


def test_quad_rows_excludes_padded_tris():
    """[v0,v1,v2,v2] padded tri excluded; [v0,v1,v2,v3] quad kept."""
    conn = np.array([[0, 1, 2, 3], [4, 5, 6, 6], [7, 8, 9, 10]], dtype=int)
    out = _quad_rows(conn)
    assert out.shape == (2, 4)
    assert {tuple(r) for r in out} == {(0, 1, 2, 3), (7, 8, 9, 10)}


def test_quad_rows_all_padded_tris_returns_empty():
    """All rows are padded tris; result is empty."""
    conn = np.array([[0, 1, 2, 2], [3, 4, 5, 5]], dtype=int)
    out = _quad_rows(conn)
    assert out.shape == (0, 4)


def test_quad_rows_empty_input():
    """Empty input; result is empty."""
    out = _quad_rows(np.empty((0, 4), dtype=int))
    assert out.shape == (0, 4)


def test_quad_rows_all_quads():
    """All rows are genuine quads; all returned."""
    conn = np.array(
        [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9, 10, 11]], dtype=int
    )
    out = _quad_rows(conn)
    assert out.shape == (3, 4)
    assert np.array_equal(out, conn)


def test_quad_rows_preserves_dtype():
    """Output is always int dtype."""
    conn = np.array([[0, 1, 2, 3], [4, 5, 6, 6]], dtype=float)
    out = _quad_rows(conn)
    assert out.dtype == int
