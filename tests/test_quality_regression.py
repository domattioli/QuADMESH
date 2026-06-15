"""Quality regression tests — pin mean-quality baselines per fixture and method.

All tests are marked ``slow`` and skipped unless ``--runslow`` is passed.
Run with:  pytest tests/test_quality_regression.py --runslow -v

Baselines: tests/fixtures/quality_baselines.json
Extends (does not replace) test_parity.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from quadmesh import compute_quality_stats, post_process, tri2quad

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "meshes"
BASELINES_FILE = Path(__file__).resolve().parent / "fixtures" / "quality_baselines.json"


def _load_baselines() -> dict:
    if not BASELINES_FILE.exists():
        return {}
    with open(BASELINES_FILE) as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith("_")}


BASELINES = _load_baselines()

# Parametrize: one test per (fixture, method, n_smooth_iter) in baselines JSON.
# WNAT_Hagen is also marked slow (large mesh — would time out in normal CI).
_PARAMS = []
for key, spec in BASELINES.items():
    fixture_name, method, n_smooth = key.split("|")
    _PARAMS.append(pytest.param(
        fixture_name, method, int(n_smooth), spec,
        id=key,
    ))


@pytest.mark.slow
@pytest.mark.parametrize("fixture_name,method,n_smooth_iter,spec", _PARAMS)
def test_mean_quality_baseline(fixture_name, method, n_smooth_iter, spec):
    """Mean quality after tri2quad + post_process must stay above baseline floor."""
    path = FIXTURE_DIR / fixture_name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")

    from chilmesh import CHILmesh
    mesh = CHILmesh.read_from_fort14(path)
    result = tri2quad(mesh, method=method)
    pp = post_process(result, n_smooth_iter=n_smooth_iter)
    stats = compute_quality_stats(pp)

    floor = spec["mean_quality_floor"]
    tol = spec["tolerance"]
    mean_q = stats["mean"]
    assert abs(mean_q - floor) <= tol, (
        f"{fixture_name}/{method}/n_smooth={n_smooth_iter}: "
        f"mean_quality {mean_q:.3f} outside ±{tol} of baseline {floor:.3f}"
    )
