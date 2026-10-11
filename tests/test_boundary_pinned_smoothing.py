"""Boundary vertices must not move under smoothing (all bundled chilmesh.data tri meshes)."""
from importlib import resources
import tempfile
from pathlib import Path

import numpy as np
import pytest
from chilmesh import CHILmesh
from scipy.spatial import cKDTree

from quadmesh import run_pipeline
from quadmesh.create_quad_domain import create_quad_domain
from quadmesh.post_process import fem_smoother, truss_smoother
from quadmesh.tri2quad import tri2quad_routine


def _tri_meshes():
    out = []
    for res in sorted(resources.files("chilmesh").joinpath("data").iterdir(),
                      key=lambda r: r.name):
        if not res.name.endswith(".14"):
            continue
        m = _load(res.name)
        c = m.connectivity_list
        if c.shape[1] == 3 or np.all(c[:, 3] == c[:, 0]):
            out.append(res.name)
    return out


def _load(name):
    data = resources.files("chilmesh").joinpath("data", name).read_bytes()
    with tempfile.NamedTemporaryFile(suffix=".14", delete=False) as fh:
        fh.write(data)
    return CHILmesh.read_from_fort14(Path(fh.name))


def _bidx(m):
    return np.unique(m.edge2vert(m.boundary_edges()).ravel()).astype(int)


NAMES = _tri_meshes()


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("smoother", ["fem", "angle-based", "truss"])
def test_boundary_coords_identical_across_smoothing(name, smoother):
    m = _load(name)
    quad = tri2quad_routine(create_quad_domain(m), parent=m)
    quad = CHILmesh(quad.connectivity_list.copy(), quad.points.copy())
    # fem_smoother compacts unused vertices first; do the same so indices match.
    from quadmesh.remove_unused import remove_unused_vertices
    quad = remove_unused_vertices(quad)
    idx = _bidx(quad)
    before = quad.points[idx, :2].copy()
    if smoother == "truss":
        out = truss_smoother(quad, n_iter=20)
    else:
        out = fem_smoother(quad, n_iter=2, method="fem" if smoother == "fem" else "angle-based")
    assert np.array_equal(out.points[idx, :2], before)


@pytest.mark.xfail(
    strict=True,
    reason="cleanup_boundary_quads (collapse mode) deletes boundary quads and "
    "remaps boundary vertices; not a smoother. Open item, see CHANGELOG.",
)
@pytest.mark.parametrize("name", NAMES)
def test_run_pipeline_keeps_original_boundary_vertices(name):
    m = _load(name)
    p = m.points[:, :2].copy()
    b = p[_bidx(m)]
    tol = 1e-9 * np.linalg.norm(p.max(0) - p.min(0))
    q = run_pipeline(m)
    d, _ = cKDTree(q.points[:, :2]).query(b)
    assert int((d > tol).sum()) == 0
