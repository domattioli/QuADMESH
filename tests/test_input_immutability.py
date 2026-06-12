"""tri2quad must not mutate the caller's mesh (#46 default-flip hazard).

The quadmesh+ sweep's route ops mutate domain.points / connectivity_list
in place; tri2quad_routine snapshots + restores them. Pin that contract —
session-scoped fixtures and downstream callers (MADMESHing) share inputs.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from chilmesh import CHILmesh
from quadmesh import tri2quad

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "meshes"


@pytest.mark.parametrize("fixture_name", ["Test_Case_1.14", "Test_Case_2.14"])
def test_tri2quad_leaves_input_untouched(fixture_name):
    path = FIXTURE_DIR / fixture_name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    mesh = CHILmesh.read_from_fort14(path)
    pts_before = np.asarray(mesh.points).copy()
    cl_before = np.asarray(mesh.connectivity_list).copy()

    tri2quad(mesh)  # default method = quadmesh+

    assert np.array_equal(np.asarray(mesh.points), pts_before), (
        "tri2quad mutated input mesh points"
    )
    assert np.array_equal(np.asarray(mesh.connectivity_list), cl_before), (
        "tri2quad mutated input mesh connectivity"
    )
