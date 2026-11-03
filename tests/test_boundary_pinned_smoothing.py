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


def _lost(m, q):
    p = m.points[:, :2]
    b = p[_bidx(m)]
    tol = 1e-9 * np.linalg.norm(p.max(0) - p.min(0))
    d, _ = cKDTree(q.points[:, :2]).query(b)
    return int((d > tol).sum())


def _interior_tris(q):
    """Triangles (padded rows) with no boundary edge."""
    bdy = set(int(e) for e in q.boundary_edges())
    n = 0
    for e, row in enumerate(q.connectivity_list):
        if int(row[2]) == int(row[3]):
            if not any(int(x) in bdy for x in q.elem2edge(e).ravel()):
                n += 1
    return n


@pytest.mark.parametrize("name", NAMES)
def test_preserve_boundary_keeps_original_vertices(name):
    m = _load(name)
    q = run_pipeline(m, preserve_boundary=True)
    assert _lost(m, q) == 0
    assert _interior_tris(q) == 0


# Default is MATLAB-faithful: cleanup_boundary_quads may drop boundary vertices.
# Measured counts on the bundled meshes; update if cleanup behavior changes.
# Conforming sweep (SweepContext): a layer-0 leftover tri is closed by
# bisecting its boundary edge at the midpoint, which leaves a flat
# boundary quad that the collapse removes with its two original boundary
# vertices. Before, those tris took a hanging-node insertion instead.
# Block_O 12 -> 40, annulus 18 -> 100, donut 4 -> 0, structuredMesh1 2 -> 10.
# MATLAB bookkeeping restored (tElemID split, CASE 2 fans + bridge, valence
# choice): annulus 100 -> 96 (re-measured: old code 100, new code 96); the
# other three unchanged.
# Valence ruling (bisection and vertex splits in one pool, final-valence
# cost): Block_O 40 -> 39, annulus 96 -> 115, structuredMesh1 10 -> 9
# (re-measured before/after that change).
DEFAULT_LOST = {
    "Block_O.14": 39,
    "annulus_200pts.fort.14": 115,
    "donut_domain.fort.14": 0,
    "structuredMesh1.14": 9,
}


@pytest.mark.parametrize("name", NAMES)
def test_default_pipeline_loss_is_documented(name):
    m = _load(name)
    q = run_pipeline(m)
    assert _lost(m, q) == DEFAULT_LOST[name]
    assert _interior_tris(q) == 0
