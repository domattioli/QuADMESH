"""059: boundary-layer routing gives quad-pure output and matches the quality reference.

The reference values are the "after" columns of
``specs/059-boundary-layer-routing/baseline-quality.md``: the output of
boundary-correct routing (layer 0 is the boundary layer). Operator ruling,
2026-10-10: the structuredMesh1 mean-skew drop (0.6963 -> 0.6466) is expected.
"""
from __future__ import annotations

import os

import pytest

import chilmesh.data as chdata
from chilmesh import CHILmesh

from quadmesh import tri2quad
from quadmesh.quality_report import compute_quality_stats

from test_no_interior_tris import _interior_tri_count, _tri_count

_DATA = os.path.dirname(chdata.__file__)
NAMED = [
    "Block_O.14",
    "annulus_200pts.fort.14",
    "donut_domain.fort.14",
    "structuredMesh1.14",
]
BUNDLED = sorted(f for f in os.listdir(_DATA) if f.endswith(".14"))

# (mean skew, worst skew) reference from baseline-quality.md.
REFERENCE = {
    "Block_O.14": (0.5440, 0.0),
    "annulus_200pts.fort.14": (0.2730, 0.0),
    "donut_domain.fort.14": (0.3339, 0.0),
    "structuredMesh1.14": (0.6466, 0.0),
    "quad_2x2.fort.14": (0.0, 0.0),
}


def _load(name: str) -> CHILmesh:
    path = os.path.join(_DATA, name)
    if not os.path.exists(path):
        pytest.skip(f"{name} not bundled")
    return CHILmesh.read_from_fort14(path)


@pytest.mark.parametrize("name", NAMED)
def test_named_meshes_are_quad_pure(name):
    assert _tri_count(tri2quad(_load(name))) == 0


@pytest.mark.parametrize("name", BUNDLED)
def test_bundled_meshes_have_no_interior_residual_tris(name):
    assert _interior_tri_count(tri2quad(_load(name))) == 0


def test_single_layer_mesh_unchanged():
    mesh = _load("quad_2x2.fort.14")
    assert mesh.n_layers == 1
    out = tri2quad(mesh)
    assert out.n_elems == 4
    assert _tri_count(out) == 0


@pytest.mark.parametrize("name", sorted(REFERENCE))
def test_quality_matches_059_reference(name):
    stats = compute_quality_stats(tri2quad(_load(name)))
    mean_ref, worst_ref = REFERENCE[name]
    assert stats["mean"] >= 0.99 * mean_ref - 1e-4, (name, stats["mean"], mean_ref)
    assert stats["min"] >= worst_ref, (name, stats["min"], worst_ref)
