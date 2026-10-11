"""Mesh quality stats. Port of MATLAB plotQualityProgress minus the plot."""

from __future__ import annotations

import numpy as np

from chilmesh import CHILmesh, element_quality


def count_concave_quads(points, conn) -> int:
    """Count quads (4 distinct vertices) with at least one reflex corner.

    Each quad is oriented counter-clockwise by signed area; a corner is reflex
    when the cross product of its two edges is negative. Padded triangles
    ([a,b,c,c] or any row with fewer than 4 distinct vertices) are skipped.
    """
    pts = np.asarray(points, dtype=float)[:, :2]
    n = 0
    for row in np.asarray(conn):
        v = [int(x) for x in row if int(x) >= 0]
        if len(v) != 4 or len(set(v)) != 4:
            continue
        p = pts[v]
        x, y = p[:, 0], p[:, 1]
        area2 = float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
        if area2 < 0:
            p = p[::-1]
        e_in = p - np.roll(p, 1, axis=0)
        e_out = np.roll(p, -1, axis=0) - p
        cross = e_in[:, 0] * e_out[:, 1] - e_in[:, 1] * e_out[:, 0]
        if np.any(cross < 0):
            n += 1
    return n


def compute_quality_stats(mesh: CHILmesh) -> dict:
    """Compute element quality statistics.

    Delegates to standalone chilmesh.element_quality(metric='skew') for canonical
    quality scoring (MADMESHing#48 unification; CHILmesh#206 skew parity).
    """
    quality_arr = element_quality(mesh.points, mesh.connectivity_list, metric="skew")
    n_bad = int(np.sum(quality_arr < 0.3))
    n_elems = mesh.n_elems
    pct_bad = 100.0 * n_bad / n_elems if n_elems > 0 else 0.0

    return {
        "mean": float(np.mean(quality_arr)),
        "min": float(np.min(quality_arr)),
        "max": float(np.max(quality_arr)),
        "std": float(np.std(quality_arr)),
        "n_bad": int(n_bad),
        "pct_bad": float(pct_bad),
        "n_elems": int(n_elems),
        "n_concave": count_concave_quads(mesh.points, mesh.connectivity_list),
    }


def format_quality_report(stats: dict) -> str:
    """Format quality stats as single-line string."""
    return (
        f"quality: mean={stats['mean']:.3f}  "
        f"min={stats['min']:.3f}  "
        f"std={stats['std']:.3f}  "
        f"bad(<0.3)={stats['n_bad']}/{stats['n_elems']} ({stats['pct_bad']:.1f}%)  "
        f"concave={stats.get('n_concave', 0)}"
    )
