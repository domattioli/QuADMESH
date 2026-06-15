"""Tests for triangulation conditioning module."""
from __future__ import annotations

import numpy as np
import pytest
import chilmesh.examples as ex

from quadmesh.precondition import condition_triangulation
from quadmesh.pipeline import run_pipeline
from quadmesh.create_quad_domain import create_quad_domain

def test_returns_chilmesh_same_counts():
    """Output has same vertex and element count as input."""
    m = ex.annulus()
    out = condition_triangulation(m)
    assert out.points.shape[0] == m.points.shape[0], "vertex count changed"
    assert np.asarray(out.connectivity_list).shape[0] == np.asarray(m.connectivity_list).shape[0], "element count changed"

def test_input_not_mutated():
    """Input domain is not modified by condition_triangulation."""
    m = ex.annulus()
    orig_conn = np.asarray(m.connectivity_list).copy()
    condition_triangulation(m)
    assert np.array_equal(np.asarray(m.connectivity_list), orig_conn), "input was mutated"

def test_unmatched_monotone():
    """Unmatched count never increases per layer."""
    out, stats = condition_triangulation(ex.annulus(), collect_stats=True)
    for s in stats:
        assert s['unmatched_after'] <= s['unmatched_before'], \
            f"layer {s['layer']}: unmatched grew {s['unmatched_before']} → {s['unmatched_after']}"

def test_pipeline_precondition_runs():
    """run_pipeline(precondition=True) executes without error."""
    q = run_pipeline(ex.annulus(), precondition=True)
    assert q is not None
    assert np.asarray(q.connectivity_list).shape[0] > 0

def test_no_interior_tris_preserved():
    """preconditioned pipeline output maintains zero interior residual tris."""
    # Reuse interior-tri check logic from test_no_interior_tris.py
    def _edges(el):
        n = len(el)
        return [tuple(sorted((int(el[i]), int(el[(i+1)%n])))) for i in range(n)]

    def _normalize(row):
        vs = [int(x) for x in row]
        uniq = list(dict.fromkeys(vs))
        return tuple(uniq) if len(uniq) == 3 else tuple(vs)

    def _interior_tri_count(mesh):
        elems = [_normalize(r) for r in np.asarray(mesh.connectivity_list)]
        count = {}
        for el in elems:
            for e in _edges(el):
                count[e] = count.get(e, 0) + 1
        bset = {e for e, c in count.items() if c == 1}
        return sum(1 for el in elems if len(el) == 3 and not any(e in bset for e in _edges(el)))

    q = run_pipeline(ex.annulus(), precondition=True)
    assert _interior_tri_count(q) == 0, "preconditioned pipeline left interior residual tris"
