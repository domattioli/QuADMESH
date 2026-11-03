"""#133 valence-4 fan (``fan_valence4``, default off).

Fixtures in ``fixtures/fan_cells/`` are ADMESH triangle inputs from
domattioli/quadmesh-rl-experiments (sha256 in ``sha256.txt``):
``h5.08_admesh`` from ``quadmesh_port/inputs_admesh_size/`` (0767cdb) and the
two constant cells from ``keepers/004/quadmeshplus_inputs/``. The 5.08 cells
left one hole each in an earlier fan port; they pin the closing step.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from chilmesh import CHILmesh
from quadmesh import _tri_removal as tr
from quadmesh.pipeline import run_pipeline

CELLS = Path(__file__).resolve().parent / "fixtures" / "fan_cells"
# Quad count of the default path (fan off), measured at af3c2ac.
DEFAULT_QUADS = {"5.08_admesh": 526, "5.08_constant": 872, "7.62_constant": 380}


def _load(name):
    d = np.load(CELLS / f"admesh_tri_h{name}.npz")
    P0 = np.asarray(d["points"])[:, :2]
    T0 = np.asarray(d["elements"])[:, :3].astype(int)
    return P0, T0


def _run(P0, T0, **kw):
    mesh = CHILmesh(connectivity=T0, points=np.c_[P0, np.zeros(len(P0))])
    q = run_pipeline(mesh, preserve_boundary=True, **kw)
    P = np.asarray(q.points)[:, :2]
    els = [list(dict.fromkeys(int(v) for v in row)) for row in np.asarray(q.connectivity_list)]
    return P, els


def _area(P, e):
    x, y = P[e, 0], P[e, 1]
    return 0.5 * float(x @ np.roll(y, -1) - np.roll(x, -1) @ y)


def _whole(P0, T0, P, els):
    """Return (triangles, doubled directed edges, boundary loops, area ratio)."""
    tris = sum(1 for e in els if len(e) == 3)
    d, und = {}, {}
    for e in els:
        e = e if _area(P, e) > 0 else e[::-1]
        for i in range(len(e)):
            k = (e[i], e[(i + 1) % len(e)])
            d[k] = d.get(k, 0) + 1
            u = (min(k), max(k))
            und[u] = und.get(u, 0) + 1
    doubled = sum(1 for v in d.values() if v > 1)
    bnd = [k for k, v in und.items() if v == 1]
    nb = {}
    for a, b in bnd:
        nb.setdefault(a, []).append(b)
        nb.setdefault(b, []).append(a)
    seen, loops = set(), 0
    for s in nb:
        if s in seen:
            continue
        loops += 1
        stack = [s]
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            stack.extend(nb[v])
    a_in = sum(abs(_area(P0, list(t))) for t in T0)
    a_out = sum(abs(_area(P, e)) for e in els)
    return tris, doubled, loops, a_out / a_in


@pytest.mark.parametrize("name", sorted(DEFAULT_QUADS))
def test_default_off_unchanged(name):
    P0, T0 = _load(name)
    P, els = _run(P0, T0)
    P2, els2 = _run(P0, T0, fan_valence4=False)
    assert len(els) == DEFAULT_QUADS[name]
    assert els == els2 and np.array_equal(P, P2)


@pytest.mark.parametrize("post", [False, True])
@pytest.mark.parametrize("name", sorted(DEFAULT_QUADS))
def test_fan_mesh_whole(name, post, monkeypatch):
    ctxs = []
    orig = tr.SweepContext.__init__

    def init(self, *a, **k):
        orig(self, *a, **k)
        ctxs.append(self)

    monkeypatch.setattr(tr.SweepContext, "__init__", init)
    P0, T0 = _load(name)
    P, els = _run(P0, T0, fan_valence4=True, do_post_process=post)
    tris, doubled, loops, ratio = _whole(P0, T0, P, els)
    assert tris == 0
    assert doubled == 0
    assert loops == 1
    assert ratio == pytest.approx(1.0, abs=1e-9)
    assert ctxs and len(ctxs[0].fan_records) > len(ctxs[0].fan_undone)


def _raw_rows(P0, T0, post):
    mesh = CHILmesh(connectivity=T0, points=np.c_[P0, np.zeros(len(P0))])
    q = run_pipeline(mesh, preserve_boundary=True, fan_valence4=True, do_post_process=post)
    return np.asarray(q.points)[:, :2], np.asarray(q.connectivity_list)


@pytest.mark.parametrize("post", [False, True])
@pytest.mark.parametrize("name", sorted(DEFAULT_QUADS))
def test_fan_rows_have_four_distinct_vertices(name, post):
    """_fan4_undo zeroes a connectivity row; no such row may reach the output."""
    P0, T0 = _load(name)
    P, rows = _raw_rows(P0, T0, post)
    assert rows.shape[1] == 4
    for r in rows:
        assert len(set(int(v) for v in r)) == 4, r


@pytest.mark.parametrize("name", sorted(DEFAULT_QUADS))
def test_fan_no_straight_corner_at_lone_node(name):
    """No quad keeps a straight corner at a node that only it uses (boundary bisect)."""
    P0, T0 = _load(name)
    P, rows = _raw_rows(P0, T0, False)
    count = np.bincount(rows.ravel(), minlength=len(P))
    for r in rows:
        r = [int(v) for v in r]
        poly = P[r] if tr._signed_area(P[r]) > 0 else P[r[::-1]]
        rr = r if tr._signed_area(P[r]) > 0 else r[::-1]
        s = tr._corner_sines(poly)
        for k, v in enumerate(rr):
            if count[v] == 1:
                assert s[k] > tr.SweepContext.MIN_SINE, (r, v, s)


@pytest.mark.parametrize("mirror", [1.0, -1.0])
def test_resplit_two_straight_nodes(mirror):
    """a, p, b, x on one straight boundary: cut 1 fails, cut 2 adds two nodes."""
    P = np.array([[0, 0], [1, 0], [2, 0], [3, 0], [3, 1], [1.5, 1.2]], float) * [mirror, 1.0]
    q, pts, n = tr.resplit_straight_boundary_quads(np.array([[0, 1, 2, 5], [2, 3, 4, 5]]), P, 0.06)
    assert n == 1 and len(q) == 4 and len(pts) == len(P) + 2
    area = sum(abs(tr._signed_area(pts[e])) for e in q)
    assert area == pytest.approx(abs(tr._signed_area(P[[0, 1, 2, 5]])) + abs(tr._signed_area(P[[2, 3, 4, 5]])))
    for e in q:
        assert tr._signed_area(pts[e]) > 0
        assert tr._corner_sines(pts[e]).min() > 0.06


def test_resplit_one_cut_no_new_node():
    """Only p is straight: cut on the diagonal p-s3, no node added."""
    P = np.array([[0, 0], [1, 0], [2, 0], [3, 0.4], [3, 1.4], [1.5, 1.2]], float)
    q, pts, n = tr.resplit_straight_boundary_quads(np.array([[0, 1, 2, 5], [2, 3, 4, 5]]), P, 0.06)
    assert n == 1 and len(q) == 2 and len(pts) == len(P)
    for e in q:
        assert tr._corner_sines(pts[e] if tr._signed_area(pts[e]) > 0 else pts[e[::-1]]).min() > 0.06
