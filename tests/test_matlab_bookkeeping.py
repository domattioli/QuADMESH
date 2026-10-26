"""MATLAB bookkeeping for leftover triangles (port_check items 49, 51, 52,
59, 60, 61).

Cites the MATLAB lines each assertion restores:

- edgeBisection.m:L78-L80: the outer triangle is split at ``m``; row kept,
  the appended half goes to IE of the outer triangle's layer.
- edgeBisection.m:L83-L88: tElemID is split in Domain into two triangles;
  the appended half goes to OE of this layer.
- edgeBisection.m:L89-L90 / edgeInsertion.m:L213-L214: the new vertex joins
  OV of this layer and IV of the layer outside.
- edgeInsertion.m:L150-L218: CASE 2 re-triangulates the outer sector at
  ``b`` as two fans plus one bridge; a new triangle is OE iff exactly one of
  its vertices is in newBoundaryVerts.
- edgeInsertion.m:L224-L234, splitQuad.m:L21-L22: tElemID is split on quad
  diagonal 2-4.

Uses chilmesh's bundled meshes.
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from quadmesh import run_pipeline, tri2quad
from quadmesh._tri_removal import SweepContext

from test_conforming_sweep import (
    _area,
    _check_conforming,
    _conformity,
    _ctx,
    _edges,
    _layer_tris,
    _live,
    _load,
    _norm,
)


def _snapshot(ctx):
    P0 = ctx.poly(range(ctx.work.n_pts))
    area0 = sum(abs(_area(P0, e)) for e in _live(ctx))
    bdy0 = {tuple(sorted(e)) for e in ctx.dom_bdy}
    return area0, bdy0


def test_bisection_bookkeeping_follows_edgeBisection_L78_L90():
    ctx = _ctx("Block_O.14", 1)
    area0, bdy0 = _snapshot(ctx)
    n_rows = ctx.domain.connectivity_list.shape[0]
    hit = None
    for r, (a, b, c) in _layer_tris(ctx, 1):
        for x, y, z in ((a, b, c), (b, c, a), (c, a, b)):
            outer = ctx.outer_tris_on_edge(x, y)
            if len(outer) == 1:
                o_layer = ctx.elem_layer[outer[0]][0]
                if ctx.bisect(r, x, y, z):
                    hit = (r, x, y, z, outer[0], o_layer)
                    break
        if hit:
            break
    assert hit, "no layer-1 triangle could be bisected"
    r, x, y, z, o, o_layer = hit
    m = [int(v) for v in ctx.work.quads[-1]][1]
    # Row order: the tElemID half is appended first, then the outer half.
    # L78-L80: outer split, appended half in IE of the outer layer.
    o_half = n_rows + 1
    assert o_half in ctx.layers["IE"][o_layer].tolist()
    assert set(ctx.tri_row(o)) | set(ctx.tri_row(o_half)) >= {x, y, m}
    assert m in ctx.tri_row(o) and m in ctx.tri_row(o_half)
    # L83-L88: tElemID split in Domain (row r kept, half appended to OE{L}).
    half = n_rows
    assert half in ctx.layers["OE"][1].tolist()
    assert {int(v) for v in ctx.tri_row(r)} | {int(v) for v in ctx.tri_row(half)} == {x, y, z, m}
    for row in (r, half):
        assert _area(ctx.poly(ctx.tri_row(row)), [0, 1, 2]) > 0.0  # isPolyCCW
        assert not ctx.live(row)  # covered by the emitted quad
    # L89-L90: m into OV{L} and IV{L-1}.
    assert m in ctx.layers["OV"][1].tolist()
    assert m in ctx.layers["IV"][0].tolist()
    _check_conforming(ctx, area0, bdy0)


def _first_vertex_split(ctx, li):
    plans = {}
    orig = SweepContext._apply_vertex_split

    def spy(self, plan):
        plans["plan"] = plan
        return orig(self, plan)

    ctx._apply_vertex_split = spy.__get__(ctx)
    for r, (a, b, c) in _layer_tris(ctx, li):
        sides = ((a, b, c), (b, c, a), (c, a, b))
        if any(ctx.is_ring_edge(x, y) for x, y, _ in sides):
            continue
        for x, y, z in sides:
            if not ctx.is_ring_vert(x):
                continue
            n_rows = ctx.domain.connectivity_list.shape[0]
            if ctx.vertex_split(r, x, y, z):
                return r, n_rows, plans["plan"]
    return None


def test_insertion_case2_fans_and_bridge_follow_edgeInsertion_L150_L234():
    ctx = _ctx("Block_O.14", 1)
    area0, bdy0 = _snapshot(ctx)
    got = _first_vertex_split(ctx, 1)
    assert got, "no layer-1 triangle could be closed by a vertex split"
    r, n_rows, plan = got
    assert plan["sector"] is not None  # CASE 2 (layer > 0)
    rows, w = plan["sector"]
    b, p, q = plan["bpq"]
    quad = [int(v) for v in ctx.work.quads[-1]]
    n = quad[1] if plan["side"] == "A" else quad[3]
    # L224-L228: tElemID split on diagonal 2-4 -> one appended row; L150-L218:
    # k sector rows are re-used and the bridge is appended -> one more row.
    assert ctx.domain.connectivity_list.shape[0] == n_rows + 2
    # Two fans (from n, from b) plus one bridge: k + 1 triangles.
    li = ctx.elem_layer[rows[0]][0]
    new_rows = sorted(rows) + [n_rows + 1]
    tris = [ctx.tri_row(t) for t in new_rows]
    assert len(tris) == len(rows) + 1
    assert sum(1 for t in tris if n in t and b in t) == 1  # the bridge
    from_n = [t for t in tris if n in t and b not in t]
    from_b = [t for t in tris if b in t and n not in t]
    assert len(from_n) == plan["sw"] and len(from_b) == len(rows) - plan["sw"]
    # L197-L218: OE iff exactly one vertex in newBoundaryVerts.
    nbv = {plan["s"], n, b, w[-1]}
    for t, tri in zip(new_rows, tris):
        kind = "OE" if sum(v in nbv for v in tri) == 1 else "IE"
        assert t in ctx.layers[kind][li].tolist()
        assert t not in ctx.layers["IE" if kind == "OE" else "OE"][li].tolist()
    # L213-L214: n into OV{L} and IV{L-1}.
    assert n in ctx.layers["OV"][1].tolist() and n in ctx.layers["IV"][0].tolist()
    # tElemID halves are consumed (the quad covers them).
    assert not ctx.live(r) and not ctx.live(n_rows)
    _check_conforming(ctx, area0, bdy0)


def test_valence_choice_picks_the_lowest_cost_candidate():
    """Operator ruling: where MATLAB leaves a choice (bisected edge, bridge
    diagonal), the candidate with valences closest to ideal wins (4 for quad
    vertices, 6 in the triangle domain); ties go to the best worst corner,
    then to MATLAB's own bridge (switchVertID, edgeInsertion.m:L180)."""
    pick = SweepContext._pick
    a = {"cost": 0.5, "worst": 0.9, "pref": 0}
    b = {"cost": 0.1, "worst": 0.2, "pref": 1}
    assert pick([a, b]) is b
    c = {"cost": 0.1, "worst": 0.3, "pref": 1}
    assert pick([b, c]) is c
    d = {"cost": 0.1, "worst": 0.3, "pref": 0}
    assert pick([c, d]) is d
    # On a real mesh: every closed vertex split took a minimum-cost bridge.
    ctx = _ctx("Block_O.14", 1)
    seen = 0
    for r, (x0, y0, z0) in _layer_tris(ctx, 1):
        sides = ((x0, y0, z0), (y0, z0, x0), (z0, x0, y0))
        if any(ctx.is_ring_edge(x, y) for x, y, _ in sides):
            continue
        for x, y, z in sides:
            if not ctx.is_ring_vert(x):
                continue
            plans = ctx._vertex_split_plans(r, x, y, z)
            if len({round(p["cost"], 9) for p in plans}) < 2:
                continue
            best = pick(plans)
            assert round(best["cost"], 9) == min(round(p["cost"], 9) for p in plans)
            seen += 1
    assert seen > 0, "fixture has no vertex split with a real valence choice"


def test_valence_cost_counts_quad_and_triangle_shares():
    """Deviation per vertex is |nq + nt/2 - 4| inside the domain (expected
    final quad valence: triangles pair into quads later). A 6-triangle
    vertex v starts at |0 + 3 - 4| = 1. Trading two triangles for one quad
    keeps it at 1 (a tri pair is a quad); trading them for two quads ends at
    |2 + 2 - 4| = 0. Placeholder ids (not in the mesh) start at deviation 4;
    the sum below is worked out by hand."""
    ctx = _ctx("structuredMesh1.14", 1)
    v = next(v for v, rs in ctx.v2t.items()
             if v not in ctx.dom_bdy_verts and len(rs) == 6)
    removed = [("t", [v, -2, -3]), ("t", [v, -4, -5])]
    added = [("q", [v, -2, -3, -4])]
    # v: 1 -> 1 (0); -2, -3, -4: |1 - 1/2 - 4| - 4 = -1/2 each;
    # -5: |-1/2 - 4| - 4 = 1/2.  Total: 0 - 3/2 + 1/2 = -1.
    assert ctx._valence_cost(removed, added, new_on_bdy=False) == pytest.approx(-1.0, abs=1e-12)
    only_v = ctx._valence_cost([("t", [v])] * 2, [("q", [v])], new_on_bdy=False)
    assert only_v == pytest.approx(0.0, abs=1e-12)
    two_q = ctx._valence_cost([("t", [v])] * 2, [("q", [v])] * 2, new_on_bdy=False)
    assert two_q == pytest.approx(-1.0, abs=1e-12)
    # The vertex a candidate adds starts from nothing: one quad inside the
    # domain deviates by |1 - 4| = 3, on the boundary by |1 - 2| = 1.
    N = ctx._NEW
    assert ctx._valence_cost([], [("q", [N])], new_on_bdy=False) == pytest.approx(3.0)
    assert ctx._valence_cost([], [("q", [N])], new_on_bdy=True) == pytest.approx(1.0)


_MESHES = ["Block_O.14", "annulus_200pts.fort.14", "donut_domain.fort.14",
           "structuredMesh1.14"]


def _t_junctions(q):
    """Vertices lying strictly inside an element edge."""
    P = np.asarray(q.points)[:, :2]
    els = [e for e in (_norm(r) for r in np.asarray(q.connectivity_list)) if len(set(e)) >= 3]
    ec = Counter(x for e in els for x in _edges(e))
    used = sorted({v for e in els for v in e})
    U = P[used]
    tol = 1e-9 * float(np.linalg.norm(P.max(0) - P.min(0)))
    n = 0
    for a, b in ec:
        d = P[b] - P[a]
        L2 = float(d @ d)
        t = ((U - P[a]) @ d) / L2
        dist = np.abs((U[:, 0] - P[a][0]) * d[1] - (U[:, 1] - P[a][1]) * d[0]) / np.sqrt(L2)
        n += int(((t > 1e-9) & (t < 1 - 1e-9) & (dist <= tol)).sum())
    return n


@pytest.mark.parametrize("name", _MESHES)
@pytest.mark.parametrize("mode", ["tri2quad", "preserve"])
def test_no_t_junctions_on_bundled_meshes(name, mode):
    m = _load(name)
    if mode == "tri2quad":
        q = tri2quad(_load(name), method="quadmesh+")
    else:
        q = run_pipeline(_load(name), preserve_boundary=True)
    off, over, ratio, _ = _conformity(m, q)
    assert _t_junctions(q) == 0, f"{name}/{mode}: vertex inside an element edge"
    assert off == 0 and over == 0
    assert abs(ratio - 1.0) < 1e-9
