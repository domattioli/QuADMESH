"""Smoke guard for scripts/size_drift_report.py offline path (#21).

The report's default fixtures are Valence-only .14 files, so a plain run skips
silently without a PAT — and it once used the removed ``matching`` method (#46).
This pins that the offline chilmesh.data path still produces finite ratio stats
through input-tris -> tri2quad -> post_process, so the #21 probe stays runnable
in CI without a token.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "size_drift_report.py"


def _load():
    spec = importlib.util.spec_from_file_location("size_drift_report", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_offline_fixtures_provision():
    mod = _load()
    paths = mod.offline_fixtures()
    if not paths:
        pytest.skip("chilmesh.data bundled meshes unavailable")
    for p in paths:
        assert Path(p).exists()


def test_offline_report_stats_finite():
    import math

    mod = _load()
    paths = mod.offline_fixtures()
    if not paths:
        pytest.skip("chilmesh.data bundled meshes unavailable")
    result = mod.run_fixture(paths[0])
    for stage in ("input-tris", "post-tri2quad", "post-smooth"):
        assert stage in result, f"missing stage {stage}"
        st = result[stage]
        assert "error" not in st, f"{stage} errored: {st.get('error')}"
        assert st["n"] > 0
        for key in ("p5", "p50", "p95", "mean", "min", "max"):
            assert math.isfinite(st[key]), f"{stage}.{key} not finite"
    # tri2quad is near-benign for edge/h agreement (band ~flat); assert it does
    # not collapse the in-band fraction relative to the input triangulation.
    assert result["post-tri2quad"]["frac_in_band"] >= result["input-tris"]["frac_in_band"] - 0.05
