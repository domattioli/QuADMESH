"""Regression: the per-layer sweep must flag CHILmesh layer 0 as the boundary layer.

CHILmesh numbers layers from the domain boundary inward: layer 0 holds the
triangles that touch the domain boundary. ``_quadmesh_plus_per_layer`` once
flagged ``li == n_layers - 1`` (the innermost layer) as the boundary layer, so
the OE-before-IE pre-pass and boundary routing ran on the wrong layer.
"""
from __future__ import annotations

import os
from collections import Counter

import numpy as np
import pytest

import chilmesh.data as chdata
from chilmesh import CHILmesh

from quadmesh import _match_quadmesh_plus, _tri_removal
from quadmesh import tri2quad

_DATA = os.path.dirname(chdata.__file__)
MESHES = ["annulus_200pts.fort.14", "donut_domain.fort.14", "structuredMesh1.14"]


def _boundary_layers(mesh: CHILmesh) -> set:
    cl = np.asarray(mesh.connectivity_list)
    cnt: Counter = Counter()
    rows = []
    for r in cl:
        t = list(dict.fromkeys(int(x) for x in r if x >= 0))
        es = [tuple(sorted((t[i], t[(i + 1) % len(t)]))) for i in range(len(t))]
        rows.append(es)
        cnt.update(es)
    bset = {e for e, n in cnt.items() if n == 1}
    out = set()
    for li in range(mesh.n_layers):
        ids = list(mesh.layers["OE"][li]) + list(mesh.layers["IE"][li])
        if any(any(e in bset for e in rows[int(k)]) for k in ids):
            out.add(li)
    return out


@pytest.mark.xfail(
    strict=True,
    reason="known defect: per-layer sweep flags li == n_layers - 1 as boundary "
    "(tri2quad.py:915, :937). Naive fix to li == 0 breaks the interior-residual "
    "invariant on Block_O.14; needs routing rework before it can land.",
)
@pytest.mark.parametrize("name", MESHES)
def test_boundary_flag_matches_boundary_layer(name, monkeypatch):
    path = os.path.join(_DATA, name)
    if not os.path.exists(path):
        pytest.skip(f"{name} not bundled")
    mesh = CHILmesh.read_from_fort14(path)
    expected = _boundary_layers(mesh)
    assert expected == {0}, f"CHILmesh convention changed: {expected}"

    match_flags: list = []
    flagged_route: set = set()

    orig_match = _match_quadmesh_plus.match_layer_heuristic
    orig_route = _tri_removal.route_leftover_tri

    def spy_match(*a, **kw):
        match_flags.append(bool(kw.get("is_boundary_layer")))
        return orig_match(*a, **kw)

    def spy_route(domain, work, gid, li, *a, **kw):
        if kw.get("on_mesh_boundary"):
            flagged_route.add(int(li))
        return orig_route(domain, work, gid, li, *a, **kw)

    monkeypatch.setattr(_match_quadmesh_plus, "match_layer_heuristic", spy_match)
    monkeypatch.setattr(_tri_removal, "route_leftover_tri", spy_route)

    tri2quad(CHILmesh.read_from_fort14(path))

    assert flagged_route, "no leftover routed with on_mesh_boundary=True"
    assert flagged_route <= {0}, f"boundary routing applied to layers {flagged_route}"
    # Sweep runs innermost first, so the boundary layer (0) is the last call.
    assert match_flags, "match_layer_heuristic never called"
    assert match_flags[-1] is True, f"boundary flag order wrong: {match_flags}"
    assert sum(match_flags) == 1, f"boundary flag set on {sum(match_flags)} layers"
