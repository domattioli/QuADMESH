"""Zero interior triangles is a hard rule (operator ruling 2026-11-04).

Part A: a leftover triangle whose only ring contact is one vertex ``b`` and
whose vertex splits all fail the ``MIN_SINE`` gates is closed by a port of
MATLAB edgeInsertion CASE 1 / 2 with no angle gate
(``SweepContext.close_by_insertion``): ``npID`` goes 1/3 along one ring edge
and ``b`` moves 1/3 along the other (edgeInsertion.m:L63-L67, L132-L133).
An original domain-boundary vertex ``b`` stays put. A candidate that would
invert an element is never taken; with none left the triangle stays.

Part B: ``run_pipeline`` raises ``InteriorTriangleError`` when its output
holds an interior triangle (definition of tests/test_no_interior_tris.py).

WNAT_Test.14 row 142 (triangle [836, 815, 853]) was such a stranded
triangle: one ring vertex on the domain boundary, no ring edge, the quad
corner at ``b`` 174-179 deg. The synthetic meshes below rebuild that shape.
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import pytest
from chilmesh import CHILmesh

import quadmesh
from quadmesh import pipeline
from quadmesh._tri_removal import SweepContext, WorkingMesh
from quadmesh.tri2quad import _boundary_edge_set

from test_conforming_sweep import (
    _area,
    _check_conforming,
    _ctx,
    _edges,
    _layer_tris,
    _live,
)
from test_no_interior_tris import _interior_tri_count


def _mesh(pts, tris):
    P = np.zeros((len(pts), 3))
    P[:, :2] = np.asarray(pts, dtype=float)
    return CHILmesh(np.asarray(tris, dtype=int), P)


def _sweep_ctx(mesh, layer_idx=0):
    tris = np.asarray(mesh.connectivity_list)[:, :3].astype(int)
    work = WorkingMesh(points=mesh.points.copy(), quads=[])
    ctx = SweepContext(mesh, work, set(), set(), _boundary_edge_set(tris))
    ctx.layer_idx = layer_idx
    return ctx


def _row_of(mesh, tri):
    cl = np.asarray(mesh.connectivity_list)[:, :3]
    for r, row in enumerate(cl.tolist()):
        if set(row) == set(tri):
            return r
    raise AssertionError(f"triangle {tri} not in mesh")


def _star_mesh(eps_deg=1.5):
    """b = 0 on a straight domain boundary. Triangle (b, q, p) holds
    180 - 2 eps deg at b; the thin fans (b, sB, q) and (b, p, sA) hold eps
    each. p and q are interior, so b is the only ring contact."""
    t = np.radians(eps_deg)
    pts = [(0, 0), (-1, 0), (1, 0), (np.cos(t), np.sin(t)), (-np.cos(t), np.sin(t)),
           (-2, 0), (2, 0), (-2, 1.5), (2, 1.5), (0, 1.5)]
    tris = [(0, 2, 3), (0, 3, 4), (0, 4, 1), (5, 1, 4), (5, 4, 7), (4, 9, 7),
            (4, 3, 9), (3, 8, 9), (3, 6, 8), (2, 6, 3)]
    return _mesh(pts, tris), (0, 3, 4)


def _inverting_mesh():
    """Like ``_star_mesh``, but each side fan of b holds a vertex (u, u')
    0.1 from b and 0.002 above the boundary. Moving b's fan to a point 1/3
    along the ring edge folds the fan triangle at u / u' on either side."""
    pts = [(0, 0), (-1, 0), (1, 0), (0.5, 0.5), (-0.5, 0.5), (0.1, 0.002),
           (-0.1, 0.002), (-2, 0), (2, 0), (-2, 1.5), (2, 1.5), (0, 1.5)]
    tris = [(0, 2, 5), (0, 5, 3), (0, 3, 4), (0, 4, 6), (0, 6, 1), (5, 2, 3),
            (6, 4, 1), (2, 8, 3), (3, 8, 10), (3, 10, 11), (4, 3, 11),
            (4, 11, 9), (7, 4, 9), (7, 1, 4)]
    return _mesh(pts, tris), (0, 3, 4)


def _snapshot(ctx):
    P = ctx.poly(range(ctx.work.n_pts))
    return sum(abs(_area(P, e)) for e in _live(ctx)), {tuple(sorted(e)) for e in ctx.dom_bdy}


def test_gated_boundary_vertex_triangle_is_closed():
    """1 ring vertex, 0 ring edges, both vertex splits gated: the closer
    closes it, keeps the original boundary vertex b in place, puts npID at
    1/3 of a ring edge, and keeps the mesh conforming."""
    mesh, tri = _star_mesh()
    ctx = _sweep_ctx(mesh)
    r = _row_of(mesh, tri)
    area0, bdy0 = _snapshot(ctx)
    b_xy = ctx.xy(0).copy()
    # The gated port finds nothing (this was the stranded case).
    assert ctx._vertex_split_plans(r, 0, 3, 4) == []
    assert ctx.route(r, False) is True
    assert ctx.insert_stats.get("closed") == 1
    assert ctx.insert_stats.get("fixed_b") == 1
    assert not ctx.live(r)
    assert np.allclose(ctx.xy(0), b_xy), "an original boundary vertex moved"
    quad = [int(v) for v in ctx.work.quads[-1]]
    assert len(set(quad)) == 4 and 0 in quad
    assert _area(ctx.poly(quad), range(4)) > 0.0
    n = ctx.work.n_pts - 1
    assert n in quad
    third = [(2 * b_xy + ctx.xy(s)) / 3.0 for s in (1, 2)]
    assert any(np.allclose(ctx.xy(n), t) for t in third), "npID not at 1/3 (L63-L67)"
    # The new vertex splits the domain-boundary edge (CASE 1).
    assert any(n in e for e in ctx.dom_bdy)
    _bdy_after = {tuple(sorted(e)) for e in ctx.dom_bdy}
    assert len(_bdy_after) == len(bdy0) + 1
    _check_conforming(ctx, area0, _bdy_after)


def test_closer_moves_interior_b_as_matlab():
    """CASE 2 (layer 1 of Block_O): b is interior, so it moves 1/3 along the
    second ring edge (edgeInsertion.m:L133) and npID sits 1/3 along the first
    (L132). The mesh stays conforming and no element inverts."""
    ctx = _ctx("Block_O.14", 1)
    area0, bdy0 = _snapshot(ctx)
    done = None
    for r, (a, b, c) in _layer_tris(ctx, 1):
        sides = ((a, b, c), (b, c, a), (c, a, b))
        if any(ctx.is_ring_edge(x, y) for x, y, _ in sides):
            continue
        ring = [x for x, _, _ in sides
                if ctx.is_ring_vert(x) and x not in ctx.dom_bdy_verts]
        if not ring:
            continue
        before = {v: ctx.xy(v).copy() for v in (a, b, c)}
        moved0 = ctx.insert_stats.get("moved_b", 0)
        if ctx.close_by_insertion(r):
            assert ctx.insert_stats.get("moved_b", 0) == moved0 + 1
            done = (r, before)
            break
    assert done is not None, "no layer-1 triangle closed by the MATLAB insertion"
    r, before = done
    moved = [v for v, p in before.items() if not np.allclose(ctx.xy(v), p)]
    assert len(moved) == 1
    b = moved[0]
    nbrs = {w for e in _live(ctx) if b in e for w in e if w != b}
    assert any(np.allclose(ctx.xy(b), (2 * before[b] + ctx.xy(w)) / 3.0) for w in nbrs), (
        "b did not move 1/3 along a ring edge (L133)")
    n = ctx.work.n_pts - 1
    assert any(np.allclose(ctx.xy(n), (2 * before[b] + ctx.xy(w)) / 3.0)
               for w in {w for e in _live(ctx) if n in e for w in e}), "npID not at 1/3"
    for e in _live(ctx):
        if b in e or n in e:
            pts = ctx.poly(e)
            assert abs(_area(pts, range(len(e)))) > 0.0
    _check_conforming(ctx, area0, bdy0)
    # Every element around b and n keeps one orientation (no fold).
    sides = Counter(np.sign(_area(ctx.poly(e), range(len(e))))
                    for e in _live(ctx) if b in e or n in e)
    assert len(sides) == 1


def test_closer_leaves_triangle_when_every_candidate_inverts():
    """All MATLAB candidates fold an element: the triangle stays (so
    run_pipeline fails loudly) and nothing is written."""
    mesh, tri = _inverting_mesh()
    ctx = _sweep_ctx(mesh)
    r = _row_of(mesh, tri)
    n_pts = ctx.work.n_pts
    pts0 = np.asarray(mesh.points).copy()
    assert ctx.route(r, False) is None
    assert ctx.live(r)
    assert ctx.work.quads == []
    assert ctx.work.n_pts == n_pts
    assert np.array_equal(np.asarray(mesh.points), pts0)
    assert ctx.insert_stats.get("no_valid_candidate") == 1
    assert ctx.insert_stats.get("inverted_variant", 0) >= 2
    assert ctx.insert_failed == [r]


def test_interior_triangle_rows_matches_the_invariant_test():
    mesh, _ = _star_mesh()
    rows = pipeline.interior_triangle_rows(mesh)
    assert len(rows) == _interior_tri_count(mesh)
    # Padded rows count as triangles; a quad never does.
    pts = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [2, 0, 0], [2, 1, 0]], float)
    quads = CHILmesh(np.array([[0, 1, 2, 3], [1, 4, 5, 2]]), pts)
    assert pipeline.interior_triangle_rows(quads) == []


def test_run_pipeline_raises_on_interior_triangle(monkeypatch):
    """A QuADMESH+ output with an interior triangle is an error, not a
    result."""
    mesh, _ = _star_mesh()
    cl = np.asarray(mesh.connectivity_list)[:, :3]
    padded = CHILmesh(np.hstack([cl, cl[:, [2]]]), np.asarray(mesh.points))
    monkeypatch.setattr(pipeline, "tri2quad_routine", lambda *a, **k: padded)
    with pytest.raises(quadmesh.InteriorTriangleError) as ei:
        quadmesh.run_pipeline(mesh, do_post_process=False)
    assert ei.value.rows == pipeline.interior_triangle_rows(padded)
    assert ei.value.rows
    assert ei.value.mesh is padded
    assert "interior triangle" in str(ei.value)


def test_run_pipeline_passes_quad_output():
    mesh, _ = _star_mesh()
    q = quadmesh.run_pipeline(mesh, do_post_process=False)
    assert _interior_tri_count(q) == 0
