"""Tests for fem_smoother."""

from __future__ import annotations

import numpy as np
from chilmesh import CHILmesh

from quadmesh.post_process import fem_smoother


def test_fem_smoother_actually_runs(test_case_1):
    """Smoother runs n_iter=1 without crash; vertex count unchanged."""
    result = fem_smoother(test_case_1, n_iter=1)
    assert result is not None
    assert result.n_verts == test_case_1.n_verts


def test_fem_smoother_zero_iter(test_case_1):
    """Smoother with n_iter=0 is a no-op."""
    result = fem_smoother(test_case_1, n_iter=0)
    assert result.n_verts == test_case_1.n_verts


def test_fem_smoother_drops_unattached_vertices(test_case_1):
    """An element-less vertex would make the stiffness matrix singular (#35).

    fem_smoother must compact it out before solving so the result stays finite.
    """
    pts = np.asarray(test_case_1.points)
    conn = np.asarray(test_case_1.connectivity_list)
    orphan = pts.mean(axis=0, keepdims=True)
    mesh = CHILmesh(conn, np.vstack([pts, orphan]))
    assert mesh.n_verts == test_case_1.n_verts + 1

    result = fem_smoother(mesh, n_iter=1)

    assert result.n_verts == test_case_1.n_verts
    assert np.isfinite(np.asarray(result.points)).all()


def _grid_mesh():
    """Synthetic 5x5 structured quad grid (offline; no Valence fixture)."""
    xs, ys = np.meshgrid(np.arange(6.0), np.arange(6.0))
    pts = np.c_[xs.ravel(), ys.ravel()]
    def vid(i, j):
        return j * 6 + i
    quads = np.array([[vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)]
                      for j in range(5) for i in range(5)])
    return CHILmesh(quads, pts)


def test_fem_smoother_fem_path_short_circuits(monkeypatch):
    """FEM path short-circuits after one pass per #107 (n_iter 2+ are no-ops)."""
    import copy
    import importlib

    pp = importlib.import_module("quadmesh.post_process")

    calls = {"n": 0}
    real = pp._balendran_smooth
    def counting(mesh):
        calls["n"] += 1
        return real(mesh)
    monkeypatch.setattr(pp, "_balendran_smooth", counting)

    mesh = _grid_mesh()
    fem_smoother(copy.deepcopy(mesh), n_iter=3, method="fem")
    assert calls["n"] == 1  # #107: passes 2+ are no-ops, short-circuited

    # byte-identical output regardless of n_iter for the fem path
    a = fem_smoother(copy.deepcopy(mesh), n_iter=1).points[:, :2].copy()
    b = fem_smoother(copy.deepcopy(mesh), n_iter=3).points[:, :2].copy()
    assert np.array_equal(a, b)


def test_fem_smoother_non_fem_runs_all_passes(monkeypatch):
    """Non-FEM methods still run all n_iter passes; no short-circuit."""
    mesh = _grid_mesh()
    calls = {"n": 0}
    def fake_smooth(*args, **kwargs):
        calls["n"] += 1
    monkeypatch.setattr(mesh, "smooth_mesh", fake_smooth)
    fem_smoother(mesh, n_iter=3, method="angle-based")
    assert calls["n"] == 3
