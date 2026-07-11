"""Tests for identify_edges_in_layer."""

from __future__ import annotations

import numpy as np
import pytest

from quadmesh.identify_edges import identify_edges_in_layer


def test_layer0_selection_nonempty(test_case_1):
    """Outermost layer of Test_Case_1: at least some edges should be selected."""
    sel = identify_edges_in_layer(test_case_1, 0)
    assert sel.sub_mesh is not None
    assert sel.elem_ids_global.size > 0
    assert sel.boundary_edge_ids.size > 0
    # Removed edges should be non-zero count for a typical layer.
    assert sel.removed_edge_ids.size > 0


def test_selected_edges_yield_disjoint_pairs(test_case_1):
    """Each selected edge maps to an elem pair; pairs are mutually exclusive."""
    sel = identify_edges_in_layer(test_case_1, 0)
    edge2elem = sel.sub_mesh.adjacencies["Edge2Elem"]
    used_elems = set()
    for eid in sel.removed_edge_ids:
        a, b = edge2elem[int(eid)]
        assert int(a) not in used_elems
        assert int(b) not in used_elems
        used_elems.add(int(a))
        used_elems.add(int(b))


def test_sweep_all_layers_no_crash(test_case_1):
    """Every layer's selection runs without raising."""
    for k in range(test_case_1.n_layers):
        sel = identify_edges_in_layer(test_case_1, k)
        assert sel.sub_mesh is not None or sel.elem_ids_global.size == 0


def test_all_layers_disjoint_pairs(test_case_1):
    """Removed-edge elem pairs are mutually exclusive within EVERY layer, not just layer 0."""
    for k in range(test_case_1.n_layers):
        sel = identify_edges_in_layer(test_case_1, k)
        if sel.removed_edge_ids.size == 0:
            continue
        edge2elem = sel.sub_mesh.adjacencies["Edge2Elem"]
        used_elems = set()
        for eid in sel.removed_edge_ids:
            a, b = edge2elem[int(eid)]
            assert int(a) not in used_elems
            assert int(b) not in used_elems
            used_elems.add(int(a))
            used_elems.add(int(b))


@pytest.mark.parametrize("fixture_name", ["test_case_1", "test_case_2"])
def test_boundary_edges_wellformed_every_layer(fixture_name, request):
    """Every non-empty layer selection exposes a well-formed boundary-edge set."""
    mesh = request.getfixturevalue(fixture_name)
    for k in range(mesh.n_layers):
        sel = identify_edges_in_layer(mesh, k)
        if sel.elem_ids_global.size == 0:
            continue
        assert sel.sub_mesh is not None
        bids = sel.boundary_edge_ids
        assert bids.size == 0 or int(bids.min()) >= 0
        assert len(set(bids.tolist())) == bids.size  # no duplicate boundary edges
