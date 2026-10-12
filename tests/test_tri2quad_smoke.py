"""Smoke tests for tri2quad: doesn't crash, produces valid CHILmesh."""

from __future__ import annotations

import numpy as np
import pytest

from quadmesh import tri2quad


def _count_quads(mesh) -> int:
    """A row is a quad iff it has 4 distinct verts; tri otherwise (with padding)."""
    cl = mesh.connectivity_list
    if cl.shape[1] != 4:
        return 0
    return int((cl[:, 2] != cl[:, 3]).sum())


def test_tri2quad_runs(test_case_1):
    out = tri2quad(test_case_1, can_remove_edges=True)
    assert out is not None
    assert out.n_elems > 0
    assert out.n_verts > 0
    assert out.connectivity_list.shape[0] == out.n_elems


def test_tri2quad_outputs_mostly_quads(test_case_1):
    out = tri2quad(test_case_1, can_remove_edges=True)
    n_quads = _count_quads(out)
    ratio = n_quads / max(out.n_elems, 1)
    # Loosely: most elems should be quads (≥50% is a sane lower bound for v0.1).
    assert ratio >= 0.5, f"only {ratio:.1%} quads — too low"


def test_tri2quad_no_zero_area(test_case_1):
    """All output elems should have non-zero signed area."""
    out = tri2quad(test_case_1, can_remove_edges=True)
    areas = out.signed_area()
    assert np.all(np.abs(areas) > 1e-12), f"{(np.abs(areas) <= 1e-12).sum()} zero-area elems"


_REAL_FIXTURES = ["test_case_1", "test_case_2"]


@pytest.mark.parametrize("fixture_name", _REAL_FIXTURES)
def test_tri2quad_multi_fixture_valid(fixture_name, request):
    """tri2quad on each real layered mesh: quad-dominant, in-range, non-degenerate."""
    mesh = request.getfixturevalue(fixture_name)
    out = tri2quad(mesh, can_remove_edges=True)
    assert out is not None and out.n_elems > 0 and out.n_verts > 0
    assert out.connectivity_list.shape[0] == out.n_elems
    ratio = _count_quads(out) / max(out.n_elems, 1)
    assert ratio >= 0.5, f"{fixture_name}: only {ratio:.1%} quads"
    areas = out.signed_area()
    assert np.all(np.abs(areas) > 1e-12), f"{fixture_name}: zero-area elems"
    cl = out.connectivity_list
    assert cl.min() >= 0 and cl.max() < out.n_verts, (
        f"{fixture_name}: connectivity index out of [0, n_verts) range"
    )


@pytest.mark.slow
def test_tri2quad_block_o_valid(_block_o):
    """Larger Block_O mesh: same validity invariants (slow — large fixture)."""
    out = tri2quad(_block_o, can_remove_edges=True)
    assert out.n_elems > 0
    ratio = _count_quads(out) / max(out.n_elems, 1)
    assert ratio >= 0.5, f"block_o: only {ratio:.1%} quads"
    assert np.all(np.abs(out.signed_area()) > 1e-12)
    cl = out.connectivity_list
    assert cl.min() >= 0 and cl.max() < out.n_verts


# --- Token-free offline coverage (issue #109) -------------------------------
# The tests above use `.14` fixtures that need a Valence token, so they SKIP in
# CI. These provision a small mesh from chilmesh.data instead, so tri2quad is
# actually exercised offline. Mirrors tests/test_no_interior_tris.py's pattern.
_OFFLINE_FIXTURES = ["structuredMesh1.14", "Block_O.14"]


def _offline_mesh():
    """Load a small tri mesh provisionable offline from chilmesh.data, or skip."""
    import sys as _sys
    from pathlib import Path as _Path

    _here = _Path(__file__).resolve().parent
    if str(_here) not in _sys.path:
        _sys.path.insert(0, str(_here))
    from _mesh_provision import provision, FIXTURE_DIR

    provision(_OFFLINE_FIXTURES)
    for name in _OFFLINE_FIXTURES:
        p = FIXTURE_DIR / name
        if p.exists():
            from chilmesh import CHILmesh

            return CHILmesh.read_from_fort14(p)
    pytest.skip("no offline fixture provisioned (chilmesh.data unavailable)")


def test_tri2quad_offline_valid():
    """Token-free (#109): tri2quad on a chilmesh.data mesh runs in CI, not skipped."""
    mesh = _offline_mesh()
    out = tri2quad(mesh, can_remove_edges=True)
    assert out is not None and out.n_elems > 0 and out.n_verts > 0
    assert out.connectivity_list.shape[0] == out.n_elems
    ratio = _count_quads(out) / max(out.n_elems, 1)
    assert ratio >= 0.5, f"offline: only {ratio:.1%} quads"
    assert np.all(np.abs(out.signed_area()) > 1e-12), "offline: zero-area elems"
    cl = out.connectivity_list
    assert cl.min() >= 0 and cl.max() < out.n_verts


def test_tri2quad_offline_preserves_original_vertices():
    """quadmesh+ only adds/rewires verts — it never drops originals (offline)."""
    mesh = _offline_mesh()
    n_in = mesh.n_verts
    out = tri2quad(mesh, can_remove_edges=True)
    assert out.n_verts >= n_in, "offline: tri2quad dropped original vertices"
