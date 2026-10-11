"""Concave-quad count in quality_report."""
from __future__ import annotations

import numpy as np

from quadmesh.quality_report import compute_quality_stats, count_concave_quads, format_quality_report

PTS = np.array([[0, 0], [2, 0], [2, 2], [0, 2], [1, 0.5]], dtype=float)


def test_convex_quad_is_not_concave():
    assert count_concave_quads(PTS, np.array([[0, 1, 2, 3]])) == 0


def test_dart_quad_is_concave_either_orientation():
    ccw = np.array([[0, 1, 2, 4]])  # (0,0),(2,0),(2,2),(1,0.5): reflex at vertex 4
    assert count_concave_quads(PTS, ccw) == 1
    assert count_concave_quads(PTS, ccw[:, ::-1]) == 1


def test_padded_triangle_is_excluded():
    assert count_concave_quads(PTS, np.array([[0, 1, 4, 4], [0, 1, 2, -1]])) == 0


def test_bundled_mesh_smoke_and_format():
    from pathlib import Path

    import chilmesh
    from chilmesh import CHILmesh
    from quadmesh import run_pipeline

    f = sorted((Path(chilmesh.__file__).parent / "data").glob("*.14"))
    m = next(x for x in (CHILmesh.read_from_fort14(p) for p in f) if x.type == "Triangular")
    out = run_pipeline(m)
    stats = compute_quality_stats(out)
    assert isinstance(stats["n_concave"], int) and 0 <= stats["n_concave"] <= out.n_elems
    assert f"concave={stats['n_concave']}" in format_quality_report(stats)
