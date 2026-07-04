"""Tests for quadmesh.hierarchical_smooth (spec-056, #104). Synthetic-only — no fixtures."""
from __future__ import annotations

import numpy as np
import pytest

from chilmesh import CHILmesh, element_quality

from quadmesh.hierarchical_smooth import (
    _build_patches,
    _cheap_global_guarded,
    _signed_areas,
    hierarchical_smoother,
    select_region,
)
from quadmesh.post_process import fem_smoother, post_process_routine


def test_no_inverted_elements_after_smoothing():
    """#104 review HIGH: orientation-blind skew must never let a tangling pass
    win. Output signed-area signs must match the input (no flips)."""
    conn, pts = _make_grid()
    base = np.sign(_signed_areas(pts, conn))
    out = hierarchical_smoother(_mesh(conn, pts))
    after = np.sign(_signed_areas(np.asarray(out.points), np.asarray(out.connectivity_list)))
    assert np.array_equal(after, base)


def test_supplement_ignores_return_info_opt():
    """#104 review MEDIUM: return_info must not leak the (mesh,info) tuple into
    fem_smoother through the supplement wiring."""
    conn, pts = _make_grid()
    out = post_process_routine(_mesh(conn, pts), hierarchical=True,
                               hierarchical_opts={"return_info": True, "n_global": 1})
    assert hasattr(out, "connectivity_list")


def _make_grid(nx=13, ny=13, band=(1, 4)):
    """Structured quad grid on [0,1]^2 with a deterministically distorted band."""
    xs, ys = np.meshgrid(np.linspace(0, 1, nx), np.linspace(0, 1, ny))
    pts = np.column_stack([xs.ravel(), ys.ravel(), np.zeros(nx * ny)])

    def vid(i, j):
        return j * nx + i

    conn = np.array(
        [[vid(i, j), vid(i + 1, j), vid(i + 1, j + 1), vid(i, j + 1)]
         for j in range(ny - 1) for i in range(nx - 1)],
        dtype=int,
    )
    for j in range(band[0], band[1]):
        for i in range(1, nx - 1):
            v = vid(i, j)
            pts[v, 0] += 0.28 / (nx - 1) * np.sin(3.1 * i + j)
            pts[v, 1] += 0.31 / (ny - 1) * np.cos(2.3 * i - j)
    return conn, pts


def _mesh(conn, pts):
    return CHILmesh(connectivity=conn.copy(), points=pts.copy(), compute_layers=False,
                    compute_adjacencies=True, build_spatial_indices=False, validate=False)


@pytest.fixture()
def grid():
    return _make_grid()


def test_select_determinism(grid):
    conn, pts = grid
    a = select_region(_mesh(conn, pts), "skew")
    b = select_region(_mesh(conn, pts), "skew")
    assert np.array_equal(a, b)


def test_select_skew_seed_targets_band(grid):
    conn, pts = grid
    seed = select_region(_mesh(conn, pts), "skew", dilate=False)
    nx = 13
    rows = seed // (nx - 1)
    assert seed.size > 0
    assert rows.max() <= 4  # distorted vert rows 1-3 touch elem rows 0-4 only


def test_select_empty_when_frac_zero(grid):
    conn, pts = grid
    sel = select_region(_mesh(conn, pts), "skew", frac=0.0)
    assert sel.size == 0


def test_select_layer_raises_without_layers(grid):
    conn, pts = grid
    with pytest.raises(ValueError):
        select_region(_mesh(conn, pts), "layer")


def test_select_valence_empty_on_regular_grid(grid):
    conn, pts = grid
    sel = select_region(_mesh(conn, pts), "valence")
    assert sel.size == 0  # every interior vertex of a structured quad grid has valence 4


def test_unknown_policy_raises(grid):
    conn, pts = grid
    with pytest.raises(ValueError):
        select_region(_mesh(conn, pts), "nope")


def test_patches_disjoint_free_interior(grid):
    conn, pts = grid
    m = _mesh(conn, pts)
    sel = select_region(m, "skew")
    patches = _build_patches(m, sel)
    assert patches, "expected at least one patch on the distorted band"
    seen = set()
    for p in patches:
        ids = set(p.elem_ids.tolist())
        assert not (ids & seen)
        seen |= ids
        sub = p.submesh
        bsub = np.unique(sub.edge2vert(sub.boundary_edges()).ravel())
        assert not (set(np.nonzero(p.free_mask)[0].tolist()) & set(bsub.tolist()))


def test_min_interior_skips_tiny(grid):
    conn, pts = grid
    m = _mesh(conn, pts)
    patches = _build_patches(m, np.array([0]), min_interior=4)
    assert patches == []  # single quad has 0 interior verts -> skipped


def test_boundary_pinned_bitwise(grid):
    conn, pts = grid
    m = _mesh(conn, pts)
    bverts = np.unique(m.edge2vert(m.boundary_edges()).ravel())
    out = hierarchical_smoother(m)
    assert np.array_equal(np.asarray(out.points)[bverts], pts[bverts])


def test_nonselected_untouched_default_plan(grid):
    conn, pts = grid
    probe = _mesh(conn, pts)
    allowed = set()
    for p in _build_patches(probe, select_region(probe, "skew")):
        allowed.update(p.vert_map[p.free_mask].tolist())
    out = hierarchical_smoother(_mesh(conn, pts))
    moved = np.nonzero(np.any(np.asarray(out.points) != pts, axis=1))[0]
    assert set(moved.tolist()) <= allowed


def test_full_determinism_bitwise(grid):
    conn, pts = grid
    o1 = hierarchical_smoother(_mesh(conn, pts))
    o2 = hierarchical_smoother(_mesh(conn, pts))
    assert np.array_equal(np.asarray(o1.points), np.asarray(o2.points))
    assert np.array_equal(np.asarray(o1.connectivity_list), np.asarray(o2.connectivity_list))


def test_empty_selection_returns_unchanged(grid):
    conn, pts = grid
    out = hierarchical_smoother(_mesh(conn, pts), frac=0.0)
    assert np.array_equal(np.asarray(out.points), pts)


def test_fallback_delegates_to_global(grid):
    conn, pts = grid
    out, info = hierarchical_smoother(_mesh(conn, pts), fallback_frac=0.01, return_info=True)
    assert info.fell_back
    bverts = np.unique(_mesh(conn, pts).edge2vert(_mesh(conn, pts).boundary_edges()).ravel())
    assert np.array_equal(np.asarray(out.points)[bverts], pts[bverts])


def test_quality_improves_on_band(grid):
    conn, pts = grid
    q0 = element_quality(pts, conn, metric="skew").mean()
    out = hierarchical_smoother(_mesh(conn, pts))
    q1 = element_quality(out.points, out.connectivity_list, metric="skew").mean()
    assert q1 > q0 + 0.02


def test_eps_controls_patch_iterations(grid):
    conn, pts = grid
    _, tight = hierarchical_smoother(_mesh(conn, pts), eps=1e-9, return_info=True)
    _, loose = hierarchical_smoother(_mesh(conn, pts), eps=0.5, return_info=True)
    assert sum(tight.patch_iters) >= sum(loose.patch_iters)
    assert all(i <= 10 for i in tight.patch_iters)  # hard cap


def test_unknown_stage_raises(grid):
    conn, pts = grid
    with pytest.raises(ValueError):
        hierarchical_smoother(_mesh(conn, pts), stage_plan=("warp",))


def test_cheap_global_guard_never_degrades_complement(grid):
    conn, pts = grid
    m = _mesh(conn, pts)
    sel = select_region(m, "skew")
    comp = np.setdiff1d(np.arange(m.n_elems), sel)
    q_before = element_quality(np.asarray(m.points), np.asarray(m.connectivity_list)[comp],
                               metric="skew").mean()
    _cheap_global_guarded(m, sel)
    q_after = element_quality(np.asarray(m.points), np.asarray(m.connectivity_list)[comp],
                              metric="skew").mean()
    assert q_after >= q_before - 1e-12


def test_stage_orderings_run_and_are_deterministic(grid):
    conn, pts = grid
    for plan in (("local_fem", "cheap_global"), ("cheap_global", "local_fem")):
        a = hierarchical_smoother(_mesh(conn, pts), stage_plan=plan)
        b = hierarchical_smoother(_mesh(conn, pts), stage_plan=plan)
        assert np.array_equal(np.asarray(a.points), np.asarray(b.points))


def test_post_process_default_path_matches_explicit_false(grid):
    conn, pts = grid
    o1 = post_process_routine(_mesh(conn, pts))
    o2 = post_process_routine(_mesh(conn, pts), hierarchical=False)
    assert np.array_equal(np.asarray(o1.points), np.asarray(o2.points))


def test_post_process_hierarchical_supplement_valid_and_parity(grid):
    conn, pts = grid
    out = post_process_routine(_mesh(conn, pts), hierarchical=True)
    q = element_quality(out.points, out.connectivity_list, metric="skew")
    assert np.isfinite(np.asarray(out.points)).all()
    assert np.isfinite(q).all()
    base = post_process_routine(_mesh(conn, pts))
    qb = element_quality(base.points, base.connectivity_list, metric="skew")
    assert q.mean() >= qb.mean() - 0.005
    assert np.median(q) >= np.median(qb) - 0.005
