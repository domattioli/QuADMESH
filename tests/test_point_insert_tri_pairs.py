"""Direct unit test of ``tri2quad._point_insert_tri_pairs``.

The old version split pentagon (tri + neighbour quad) + one interior point
into two quads, which always left the triangle (L4, L0, p) uncovered: a hole.
A pentagon has no all-quad cover (odd side count), so the fix splits the
tri's domain-boundary edge and builds three quads around the interior point.
"""

from collections import Counter

import numpy as np

from quadmesh.tri2quad import _point_insert_tri_pairs


def _area(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(x @ np.roll(y, -1) - np.roll(x, -1) @ y)


def _edges(e):
    return [tuple(sorted((e[i], e[(i + 1) % len(e)]))) for i in range(len(e))]


def test_point_insert_covers_pentagon_without_hole():
    pts = np.array([
        [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
        [2.0, 0.5, 0.0],
    ])
    quads = [(0, 1, 2, 3)]
    tris = np.array([[1, 4, 2]])
    area_in = abs(_area(pts[[0, 1, 2, 3], :2])) + abs(_area(pts[[1, 4, 2], :2]))

    q_out, t_out, p_out = _point_insert_tri_pairs(quads, tris, pts)

    assert t_out.shape[0] == 0
    assert len(q_out) == 3
    np.testing.assert_array_equal(p_out[:5], pts)  # originals untouched
    P = p_out[:, :2]
    areas = [_area(P[list(q)]) for q in q_out]
    assert all(a > 0 for a in areas)  # CCW, non-degenerate
    assert abs(sum(areas) - area_in) < 1e-12  # area conserved -> no hole

    # Conforming: every edge is shared by 2 quads or lies on the outer
    # boundary, and the boundary edges trace the original outline.
    ec = Counter(x for q in q_out for x in _edges(q))
    assert set(ec.values()) <= {1, 2}
    bdy = [e for e, n in ec.items() if n == 1]
    outline = [(0, 1), (1, 4), (4, 2), (2, 3), (3, 0)]
    blen = sum(float(np.linalg.norm(P[a] - P[b])) for a, b in bdy)
    olen = sum(float(np.linalg.norm(P[a] - P[b])) for a, b in outline)
    assert abs(blen - olen) < 1e-12
    # No T-junction: no vertex strictly inside any edge.
    used = sorted({v for q in q_out for v in q})
    for a, b in ec:
        d = P[b] - P[a]
        for v in used:
            if v in (a, b):
                continue
            w = P[v] - P[a]
            t = float(w @ d) / float(d @ d)
            dist = abs(w[0] * d[1] - w[1] * d[0]) / float(np.linalg.norm(d))
            assert not (1e-9 < t < 1 - 1e-9 and dist < 1e-9), (a, b, v)
