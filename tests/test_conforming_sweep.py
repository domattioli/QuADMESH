"""The per-layer QuADMESH+ sweep must leave a conforming mesh.

A leftover triangle in layer ``L`` gains its fourth corner on its outer ring,
and the element across that ring edge is split at the new vertex
(``SweepContext``). Before this, the sweep compared sub-mesh edge ids with
parent edge ids, so most leftovers fell through to an edge insertion whose
opposite-triangle split never ran: every one left a hanging node (T-junction)
and an unshared interior edge in the output.

Uses chilmesh's bundled meshes, so the tests run without the Valence fixtures.
"""
from __future__ import annotations

import tempfile
from collections import Counter
from importlib import resources
from pathlib import Path

import numpy as np
import pytest
from chilmesh import CHILmesh

from quadmesh import run_pipeline, tri2quad
from quadmesh._tri_removal import SweepContext, WorkingMesh, _corner_sines
from quadmesh.tri2quad import _boundary_edge_set


def _load(name):
    data = resources.files("chilmesh").joinpath("data", name).read_bytes()
    with tempfile.NamedTemporaryFile(suffix=".14", delete=False) as fh:
        fh.write(data)
    return CHILmesh.read_from_fort14(Path(fh.name))


def _norm(row):
    vs = [int(x) for x in row]
    u = list(dict.fromkeys(vs))
    return u if len(u) == 3 else vs


def _area(P, e):
    x, y = P[list(e), 0], P[list(e), 1]
    return 0.5 * float(x @ np.roll(y, -1) - np.roll(x, -1) @ y)


def _edges(e):
    k = len(e)
    return [tuple(sorted((e[j], e[(j + 1) % k]))) for j in range(k)]


def _max_angle_deg(P):
    k = len(P)
    out = 0.0
    for i in range(k):
        u = P[i - 1] - P[i]
        v = P[(i + 1) % k] - P[i]
        c = float(u @ v / (np.linalg.norm(u) * np.linalg.norm(v)))
        out = max(out, float(np.degrees(np.arccos(np.clip(c, -1.0, 1.0)))))
    return out


def _conformity(m_in, q):
    """(off-boundary unshared edges, edges in > 2 elements, area ratio, tris)."""
    Pi = np.asarray(m_in.points)[:, :2]
    ein = [_norm(r) for r in np.asarray(m_in.connectivity_list)]
    a_in = sum(abs(_area(Pi, e)) for e in ein)
    seg = np.array([[Pi[a], Pi[b]]
                    for (a, b), n in Counter(x for e in ein for x in _edges(e)).items()
                    if n == 1])
    tol = 1e-7 * float(np.linalg.norm(Pi.max(0) - Pi.min(0)))

    def on_boundary(p):
        a, b = seg[:, 0], seg[:, 1]
        d = b - a
        t = np.clip(((p - a) * d).sum(1) / (d * d).sum(1), 0.0, 1.0)
        return bool((np.hypot(*(a + t[:, None] * d - p).T) <= tol).any())

    P = np.asarray(q.points)[:, :2]
    els = [e for e in (_norm(r) for r in np.asarray(q.connectivity_list)) if len(set(e)) >= 3]
    ec = Counter(x for e in els for x in _edges(e))
    off = sum(
        1 for (a, b), n in ec.items()
        if n == 1 and not (on_boundary(P[a]) and on_boundary(P[b])
                           and on_boundary(0.5 * (P[a] + P[b])))
    )
    over = sum(1 for n in ec.values() if n > 2)
    ratio = sum(abs(_area(P, e)) for e in els) / a_in
    tris = sum(1 for e in els if len(e) == 3)
    return off, over, ratio, tris


@pytest.mark.parametrize("name", ["Block_O.14", "annulus_200pts.fort.14"])
@pytest.mark.parametrize("mode", ["tri2quad", "preserve"])
def test_output_has_no_hanging_nodes(name, mode):
    m = _load(name)
    if mode == "tri2quad":
        q = tri2quad(_load(name), method="quadmesh+")
    else:
        q = run_pipeline(_load(name), preserve_boundary=True)
    off, over, ratio, tris = _conformity(m, q)
    assert off == 0, f"{name}/{mode}: {off} unshared edges off the domain boundary (T-junctions)"
    assert over == 0, f"{name}/{mode}: {over} edges shared by more than two elements"
    assert tris == 0
    assert abs(ratio - 1.0) < 1e-9, f"{name}/{mode}: area ratio {ratio}"


def test_tri2quad_leaves_bundled_input_untouched():
    m = _load("Block_O.14")
    pts = np.asarray(m.points).copy()
    cl = np.asarray(m.connectivity_list).copy()
    oe = [np.asarray(a).copy() for a in m.layers["OE"]]
    n_verts, n_elems = m.n_verts, m.n_elems
    tri2quad(m, method="quadmesh+")
    assert np.array_equal(np.asarray(m.points), pts)
    assert np.array_equal(np.asarray(m.connectivity_list), cl)
    assert len(m.layers["OE"]) == len(oe)
    assert all(np.array_equal(np.asarray(a), b) for a, b in zip(m.layers["OE"], oe))
    assert (m.n_verts, m.n_elems) == (n_verts, n_elems)


def test_working_mesh_ids_resolve_after_flush():
    class _Dom:
        points = np.zeros((3, 3))

    dom = _Dom()
    work = WorkingMesh(points=dom.points.copy(), quads=[])
    a = work.add_point([1.0, 1.0, 0.0])
    work.flush_points_to_domain(dom)
    b = work.add_point([2.0, 3.0, 0.0])
    assert (a, b) == (3, 4)
    assert np.array_equal(work.get_extra_point(b), [2.0, 3.0, 0.0])
    work.flush_points_to_domain(dom)
    assert dom.points.shape == (5, 3)
    assert np.array_equal(dom.points[b], [2.0, 3.0, 0.0])


def _ctx(name, layer_idx):
    dom = _load(name)
    tris = np.asarray(dom.connectivity_list)[:, :3].astype(int)
    work = WorkingMesh(points=dom.points.copy(), quads=[])
    ctx = SweepContext(dom, work, set(), set(), _boundary_edge_set(tris))
    ctx.layer_idx = layer_idx
    return ctx


def _live(ctx):
    """Vertex lists of every live element (triangles and emitted quads)."""
    els = [ctx.tri_row(r) for r in range(ctx.domain.connectivity_list.shape[0])
           if ctx.live(r)]
    return els + [[int(v) for v in q] for q in ctx.work.quads]


def _check_conforming(ctx, area0, bdy0):
    els = _live(ctx)
    P = ctx.poly(range(ctx.work.n_pts))
    ec = Counter(x for e in els for x in _edges(e))
    assert max(ec.values()) == 2
    unshared = {e for e, n in ec.items() if n == 1}
    assert len(unshared) == len(bdy0), "an interior edge lost its neighbour (hanging node)"
    assert abs(sum(abs(_area(P, e)) for e in els) - area0) < 1e-9 * area0


def _layer_tris(ctx, li):
    rows = np.concatenate([ctx.layers["OE"][li], ctx.layers["IE"][li]]).astype(int)
    out = []
    for r in rows.tolist():
        tri = ctx.tri_row(r)
        if _area(ctx.poly(tri), [0, 1, 2]) < 0.0:
            tri = tri[::-1]
        out.append((r, tri))
    return out


def test_ring_classification_follows_live_rows():
    ctx = _ctx("structuredMesh1.14", 0)
    a, b = sorted(next(iter(ctx.dom_bdy)))
    assert ctx.is_ring_edge(a, b) and ctx.is_ring_vert(a)
    ctx.layer_idx = 1
    r = next(r for r in ctx.layers["OE"][0].tolist() if ctx.live(r))
    u, v = ctx.tri_row(r)[:2]
    assert r in ctx.outer_tris_on_edge(u, v)
    ctx.retire_tri(r)
    assert r not in ctx.outer_tris_on_edge(u, v)
    assert not ctx.live(r)


def test_bisection_splits_the_outer_triangle_off_the_midpoint():
    ctx = _ctx("Block_O.14", 1)
    P0 = ctx.poly(range(ctx.work.n_pts))
    area0 = sum(abs(_area(P0, e)) for e in _live(ctx))
    bdy0 = {tuple(sorted(e)) for e in ctx.dom_bdy}
    n_rows = ctx.domain.connectivity_list.shape[0]
    for r, (a, b, c) in _layer_tris(ctx, 1):
        for x, y, z in ((a, b, c), (b, c, a), (c, a, b)):
            outer = ctx.outer_tris_on_edge(x, y)
            if len(outer) == 1 and ctx.bisect(r, x, y, z):
                break
        else:
            continue
        break
    else:
        pytest.fail("no layer-1 triangle could be bisected")
    # Old pin n_rows + 1 (outer tri split only). New pin n_rows + 2: the outer
    # tri is split (edgeBisection.m:L78-L80) and tElemID is split in Domain
    # too (edgeBisection.m:L83-L86) instead of retiring its row.
    assert ctx.domain.connectivity_list.shape[0] == n_rows + 2
    quad = [int(v) for v in ctx.work.quads[-1]]
    m = quad[1]
    pq = ctx.poly(quad)
    assert _max_angle_deg(pq) < 178.0, "bisection left a straight corner"
    assert _corner_sines(pq).min() > ctx.MIN_SINE
    mid = 0.5 * (ctx.xy(x) + ctx.xy(y))
    assert np.linalg.norm(ctx.xy(m) - mid) > 0.0  # displaced toward the outer apex
    _check_conforming(ctx, area0, bdy0)


def test_vertex_split_keeps_the_mesh_conforming():
    ctx = _ctx("Block_O.14", 1)
    P0 = ctx.poly(range(ctx.work.n_pts))
    area0 = sum(abs(_area(P0, e)) for e in _live(ctx))
    bdy0 = {tuple(sorted(e)) for e in ctx.dom_bdy}
    done = False
    for r, (a, b, c) in _layer_tris(ctx, 1):
        sides = ((a, b, c), (b, c, a), (c, a, b))
        if any(ctx.is_ring_edge(x, y) for x, y, _ in sides):
            continue
        for x, y, z in sides:
            if ctx.is_ring_vert(x) and ctx.vertex_split(r, x, y, z):
                done = True
                break
        if done:
            break
    assert done, "no layer-1 triangle could be closed by a vertex split"
    quad = [int(v) for v in ctx.work.quads[-1]]
    assert len(set(quad)) == 4
    assert _corner_sines(ctx.poly(quad)).min() > ctx.MIN_SINE
    assert not ctx.live(r)
    _check_conforming(ctx, area0, bdy0)
