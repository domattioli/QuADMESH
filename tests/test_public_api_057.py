"""Public API stays importable with unchanged signatures (spec 057 FR-003).

Snapshot taken before the sibling-dedupe changes (T003).
"""
from __future__ import annotations

import inspect

import pytest

import quadmesh

SNAPSHOT = {
    'tri2quad': "(domain: 'CHILmesh', can_remove_edges: 'bool' = True, parent: 'Optional[CHILmesh]' = None, aggressive: 'bool' = False, remove_boundary_tris: 'bool' = True, method: 'str' = 'quadmesh+', minimize_boundary_change: 'Optional[bool]' = None, point_insert: 'bool' = True, refuse_boundary_merge: 'bool' = False) -> 'CHILmesh'",
    'post_process': "(mesh: 'CHILmesh', can_remove_edges: 'bool' = True, n_smooth_iter: 'int' = 3, max_outer_iter: 'int' = 5, max_inner_iter: 'int' = 5, repair: 'bool' = False, truss_smooth: 'bool' = False, truss_fh=None, preserve_boundary: 'bool' = False, protected_points=None) -> 'CHILmesh'",
    'fem_smoother': "(mesh: 'CHILmesh', n_iter: 'int' = 3, method: 'str' = 'fem') -> 'CHILmesh'",
    'compute_quality_stats': "(mesh: 'CHILmesh') -> 'dict'",
    'format_quality_report': "(stats: 'dict') -> 'str'",
    'repair_mesh': "(conn: 'np.ndarray', pts: 'np.ndarray', mid_threshold: 'int' = 0) -> 'tuple[np.ndarray, np.ndarray]'",
    'repair_chilmesh': '(mesh: "\'CHILmesh\'") -> "\'CHILmesh\'"',
    '__version__': None,
    'create_quad_domain': "(mesh: 'CHILmesh', polygon: 'Optional[PolygonInput]' = None) -> 'CHILmesh'",
    'run_pipeline': "(mesh: 'CHILmesh', polygon: 'Optional[np.ndarray]' = None, can_remove_edges: 'bool' = True, n_smooth_iter: 'int' = 3, do_post_process: 'bool' = True, max_outer_iter: 'int' = 5, max_inner_iter: 'int' = 5, method: 'str' = 'quadmesh+', truss_smooth: 'bool' = False, truss_fh=None, refuse_boundary_merge: 'bool' = False, preserve_boundary: 'bool' = False) -> 'CHILmesh'",
}


def test_snapshot_covers_all_public_names():
    assert set(SNAPSHOT) == set(quadmesh.__all__) | {"create_quad_domain", "run_pipeline"}


@pytest.mark.parametrize("name", sorted(SNAPSHOT))
def test_public_name_signature(name):
    obj = getattr(quadmesh, name)
    if inspect.ismodule(obj):
        # Once the submodule is imported, its name shadows the lazy function.
        obj = getattr(obj, name)
    want = SNAPSHOT[name]
    if want is None:
        return  # __version__: importable, no signature
    assert str(inspect.signature(obj)) == want
