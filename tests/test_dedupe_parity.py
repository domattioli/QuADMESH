"""Parity gate for feature 057 (sibling dedupe).

Baseline: ``compute_quality_stats`` mean/min and ``n_elems`` after ``run_pipeline``
on the code before delegation to CHILmesh. Stored in
``fixtures/baselines/dedupe_057.json``. Each fixture is skipped when absent.

Regenerate (only when behavior is meant to change)::

    python tests/test_dedupe_parity.py --write
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "meshes"
BASELINE = Path(__file__).resolve().parent / "fixtures" / "baselines" / "dedupe_057.json"
TOL = 1e-6

# T006 spike (2026-10-10): max abs point difference between the former local
# ``_balendran_smooth`` and ``CHILmesh.direct_smoother`` (chilmesh 1.5.0) was
# 0.0 on structuredMesh1.14 and Block_O.14, for both the triangle input and the
# tri2quad output. Mixed_Test, Test_Case_1 to 3 were not available (no Valence
# token). Result: delegate (R3, threshold 1e-6).
#
# Re-pinned for the restored MATLAB leftover-triangle bookkeeping (tElemID
# split, CASE 2 fans + bridge, valence choice). Block_O.14 only; measured
# with the old code (git HEAD af3c2ac) and the new code:
#   old: n_elems 2833, mean 0.8013828665577247, min 0.26800986345455824
#   new: n_elems 2825, mean 0.7933965765807829, min 0.26269546813378153
# structuredMesh1.14 unchanged.
# Re-pinned again for the valence ruling (bisection and vertex splits in one
# pool, final-valence cost nq + nt/2). Measured with the code before and
# after that change:
#   Block_O.14:         2825 / 0.79340 / 0.26270 -> 3095 / 0.79453 / 0.21352
#   structuredMesh1.14:  336 / 0.67654 / 0.25494 ->  337 / 0.82167 / 0.31226


def _snapshot(path: Path) -> dict:
    from chilmesh import CHILmesh

    from quadmesh import compute_quality_stats, run_pipeline

    mesh = CHILmesh.read_from_fort14(path)
    stats = compute_quality_stats(run_pipeline(mesh))
    return {"mean": stats["mean"], "min": stats["min"], "n_elems": stats["n_elems"]}


def _load() -> dict:
    return json.loads(BASELINE.read_text()) if BASELINE.exists() else {}


_BASE = _load()


@pytest.mark.parametrize("name", sorted(_BASE))
def test_pipeline_matches_baseline(name):
    path = FIXTURE_DIR / name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    got = _snapshot(path)
    want = _BASE[name]
    assert got["n_elems"] == want["n_elems"]
    assert abs(got["mean"] - want["mean"]) <= TOL
    assert abs(got["min"] - want["min"]) <= TOL


if __name__ == "__main__":
    if "--write" not in sys.argv:
        sys.exit("pass --write to regenerate the baseline")
    out = {p.name: _snapshot(p) for p in sorted(FIXTURE_DIR.glob("*.14"))}
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))
