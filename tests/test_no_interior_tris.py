"""Regression: tri2quad must leave ZERO interior residual triangles.

A properly converted mesh may keep triangles only on the domain boundary;
any triangle whose three edges are all interior is a conversion failure.
This pins the interior-saturating matching guarantee across fixtures.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from chilmesh import CHILmesh
from quadmesh import tri2quad

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "meshes"

FIXTURES = [
    "Test_Case_1.14",
    "Test_Case_2.14",
    "Test_Case_3.14",
    "simple_test_case.14",
    "square_mesh_test.14",
    "structuredMesh1.14",
]


def _edges(el):
    n = len(el)
    return [tuple(sorted((int(el[i]), int(el[(i + 1) % n])))) for i in range(n)]


def _normalize(row):
    """Padded quad [a,b,c,c] (any duplicated vertex) -> the underlying triangle."""
    vs = [int(x) for x in row]
    uniq = list(dict.fromkeys(vs))
    return tuple(uniq) if len(uniq) == 3 else tuple(vs)


def _interior_tri_count(mesh: CHILmesh) -> int:
    elems = [_normalize(r) for r in np.asarray(mesh.connectivity_list)]
    count = {}
    for el in elems:
        for e in _edges(el):
            count[e] = count.get(e, 0) + 1
    bset = {e for e, c in count.items() if c == 1}
    return sum(
        1 for el in elems if len(el) == 3 and not any(e in bset for e in _edges(el))
    )


def _tri_count(mesh: CHILmesh) -> int:
    return sum(
        1 for r in np.asarray(mesh.connectivity_list) if len(_normalize(r)) == 3
    )


def _segments_cross(a, b, c, d) -> bool:
    def cr(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    return (cr(c, d, a) > 0) != (cr(c, d, b) > 0) and (cr(a, b, c) > 0) != (
        cr(a, b, d) > 0
    )


def _bowtie_count(mesh: CHILmesh) -> int:
    cl = np.asarray(mesh.connectivity_list)
    P = mesh.points[:, :2]
    n = 0
    for row in cl:
        el = _normalize(row)
        if len(el) != 4:
            continue
        p = P[list(el)]
        if _segments_cross(p[0], p[1], p[2], p[3]) or _segments_cross(
            p[1], p[2], p[3], p[0]
        ):
            n += 1
    return n


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_tri2quad_zero_interior_tris(fixture_name):
    path = FIXTURE_DIR / fixture_name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    mesh = CHILmesh.read_from_fort14(path)
    # Matching-only path (no boundary removal): interior must already be zero.
    quad_mesh = tri2quad(mesh, can_remove_edges=True, remove_boundary_tris=False)
    n_interior = _interior_tri_count(quad_mesh)
    assert n_interior == 0, (
        f"{fixture_name}: {n_interior} interior residual triangles after matching "
        f"(expected 0)"
    )


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_tri2quad_quad_pure(fixture_name):
    """Default tri2quad eliminates ALL triangles (interior and boundary)."""
    path = FIXTURE_DIR / fixture_name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    mesh = CHILmesh.read_from_fort14(path)
    quad_mesh = tri2quad(mesh, can_remove_edges=True)
    n_tri = _tri_count(quad_mesh)
    assert n_tri == 0, (
        f"{fixture_name}: {n_tri} residual triangles after quad-pure tri2quad "
        f"(expected 0)"
    )
    n_bt = _bowtie_count(quad_mesh)
    assert n_bt == 0, (
        f"{fixture_name}: {n_bt} self-intersecting (bowtie) quads after boundary-tri "
        f"removal (expected 0)"
    )


@pytest.mark.parametrize(
    "fixture_name", ["Test_Case_1.14", "square_mesh_test.14", "structuredMesh1.14"]
)
def test_tri2quad_quadmesh_plus_path(fixture_name):
    """QuadMesh+ layer-ordered path: ZERO interior residual tris (the invariant),
    conforming, bowtie-free, and quad-pure (default point_insert clears residual
    boundary tris by pairing each with a neighbour quad + an interior point,
    preserving every original vertex)."""
    path = FIXTURE_DIR / fixture_name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    mesh = CHILmesh.read_from_fort14(path)
    q = tri2quad(mesh, method="layered")
    assert _interior_tri_count(q) == 0, (
        f"{fixture_name}: quadmesh+ path left interior residual tris — NOT faithful"
    )
    assert _bowtie_count(q) == 0, f"{fixture_name}: quadmesh+ path produced bowties"
    assert _tri_count(q) == 0, f"{fixture_name}: quadmesh+ path not quad-pure"


@pytest.mark.parametrize("fixture_name", ["Test_Case_1.14", "structuredMesh1.14"])
def test_quadmesh_plus_preserves_original_boundary_vertices(fixture_name):
    """QuadMesh+ path must not move/delete ORIGINAL boundary vertices.

    Residual boundary tris are dropped (apex exposed), not squeezed (which moves
    + deletes the two original boundary verts). Every original boundary-vertex
    coordinate must still be present in the output.
    """
    path = FIXTURE_DIR / fixture_name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    mesh = CHILmesh.read_from_fort14(path)
    cl_in = np.asarray(mesh.connectivity_list)[:, :3].astype(int)
    P_in = mesh.points[:, :2]
    ecount: dict = {}
    for t in cl_in:
        for e in _edges(list(t)):
            ecount[e] = ecount.get(e, 0) + 1
    bverts = {v for e, c in ecount.items() if c == 1 for v in e}

    q = tri2quad(mesh, method="layered")
    out = {tuple(np.round(p, 6)) for p in q.points[:, :2]}
    missing = [v for v in bverts if tuple(np.round(P_in[v], 6)) not in out]
    assert not missing, (
        f"{fixture_name}: {len(missing)} original boundary verts altered/removed "
        f"by quadmesh+ path (expected 0)"
    )


def test_tri2quad_conforming_and_valid():
    """Quads must be non-degenerate and the mesh conforming (no edge in >2 elems)."""
    path = FIXTURE_DIR / "Test_Case_1.14"
    if not path.exists():
        pytest.skip("fixture missing")
    mesh = CHILmesh.read_from_fort14(path)
    q = tri2quad(mesh, can_remove_edges=True)
    cl = np.asarray(q.connectivity_list)
    count = {}
    for row in cl:
        for e in _edges(_normalize(row)):
            count[e] = count.get(e, 0) + 1
    assert max(count.values()) <= 2, "non-conforming edge shared by >2 elements"


@pytest.mark.parametrize("removed", ["faithful", "matching"])
def test_removed_methods_raise(removed):
    """'faithful' and 'matching' were removed entirely (#46) — ValueError."""
    path = FIXTURE_DIR / "Test_Case_1.14"
    if not path.exists():
        pytest.skip("fixture missing")
    mesh = CHILmesh.read_from_fort14(path)
    with pytest.raises(ValueError, match="was removed"):
        tri2quad(mesh, method=removed)


def test_quadmesh_plus_alias_no_warn():
    """method='quadmesh+' is the canonical (sole) method — no warning, quad-pure."""
    import warnings as _w
    path = FIXTURE_DIR / "Test_Case_1.14"
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    mesh = CHILmesh.read_from_fort14(path)
    with _w.catch_warnings(record=True) as rec:
        _w.simplefilter("always")
        q = tri2quad(mesh, method="quadmesh+")
    assert not any(issubclass(r.category, DeprecationWarning) for r in rec), (
        "method='quadmesh+' must NOT emit DeprecationWarning"
    )
    assert _tri_count(q) == 0, "quadmesh+ must produce quad-pure output"


@pytest.mark.parametrize("fixture_name", FIXTURES)
def test_no_interior_geometric_tris(fixture_name):
    """A quad with a ~180 deg corner is geometrically a triangle; the index-based
    check misses it. The quadmesh+ path must leave ZERO *interior* geometric
    triangles (boundary ones are allowed, like residual boundary tris)."""
    path = FIXTURE_DIR / fixture_name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    mesh = CHILmesh.read_from_fort14(path)
    q = tri2quad(mesh, method="quadmesh+")
    P = np.asarray(q.points)[:, :2]
    cl = np.asarray(q.connectivity_list)
    # boundary edges over normalized elems
    ecount = {}
    for row in cl:
        el = _normalize(row)
        for e in _edges(el):
            ecount[e] = ecount.get(e, 0) + 1
    bset = {e for e, c in ecount.items() if c == 1}
    interior_geo = 0
    for row in cl:
        idx = [int(x) for x in row]
        if len(set(idx)) != 4:
            continue
        pts = P[idx]
        flat = -1
        for i in range(4):
            v1 = pts[(i - 1) % 4] - pts[i]; v2 = pts[(i + 1) % 4] - pts[i]
            n1 = np.linalg.norm(v1); n2 = np.linalg.norm(v2)
            if n1 < 1e-12 or n2 < 1e-12:
                flat = i; break
            ang = np.degrees(np.arccos(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)))
            if ang >= 178.0:
                flat = i; break
        if flat < 0:
            continue
        # "interior" iff none of the element's actual edges is a boundary edge
        elem_edges = _edges(_normalize(row))
        if not any(e in bset for e in elem_edges):
            interior_geo += 1
    assert interior_geo == 0, (
        f"{fixture_name}: {interior_geo} interior geometric triangles "
        f"(quad with ~180 deg corner, no boundary edge)"
    )
