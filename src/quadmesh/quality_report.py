"""Mesh quality stats. Port of MATLAB plotQualityProgress minus the plot."""

from __future__ import annotations

import numpy as np

from chilmesh import CHILmesh, element_quality


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
    }


def format_quality_report(stats: dict) -> str:
    """Format quality stats as single-line string."""
    return (
        f"quality: mean={stats['mean']:.3f}  "
        f"min={stats['min']:.3f}  "
        f"std={stats['std']:.3f}  "
        f"bad(<0.3)={stats['n_bad']}/{stats['n_elems']} ({stats['pct_bad']:.1f}%)"
    )
