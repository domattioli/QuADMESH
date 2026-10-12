"""Test that validator triggers CHILmesh layer computation (peel_layers) correctly.

Regression test for QuADMesh #55 / CHILmesh 1.4.0 lexicon rename.
The validator should prefer peel_layers (CHILmesh 1.4.0+) but fall back to
_skeletonize for older versions.
"""
from __future__ import annotations

import numpy as np
import pytest

from quadmesh.validation.validator import (
    _resolve_layer_trigger,
    validate_mesh_elements,
)


class _FakeMesh:
    """Duck-typed stand-in exposing only the given layer-trigger method names."""

    def __init__(self, *names: str):
        for name in names:
            setattr(self, name, lambda: None)


def test_resolve_prefers_peel_layers():
    """peel_layers wins when all three names are present (CHILmesh >=1.4.0)."""
    mesh = _FakeMesh("peel_layers", "_peel", "_skeletonize")
    assert _resolve_layer_trigger(mesh) is mesh.peel_layers


def test_resolve_falls_back_to_private_peel():
    """_peel is used when peel_layers is absent but the private name exists."""
    mesh = _FakeMesh("_peel", "_skeletonize")
    assert _resolve_layer_trigger(mesh) is mesh._peel


def test_resolve_falls_back_to_skeletonize():
    """_skeletonize is the last resort for chilmesh <=1.3.x."""
    mesh = _FakeMesh("_skeletonize")
    assert _resolve_layer_trigger(mesh) is mesh._skeletonize


def test_resolve_returns_none_when_no_trigger():
    """None when the mesh exposes no recognized layer-trigger method."""
    assert _resolve_layer_trigger(_FakeMesh()) is None


@pytest.fixture
def small_synthetic_mesh():
    """Build a tiny synthetic mesh without precomputed layers.

    Creates a 2x2 grid of quads (4 elements, 9 vertices).
    CHILmesh is constructed with compute_layers=False so layers are initially empty.
    """
    try:
        from chilmesh import CHILmesh
    except ImportError:
        pytest.skip("CHILmesh not available")

    # Simple 2x2 grid: 3x3 points, 4 quad elements
    points = np.array([
        [0.0, 0.0],
        [1.0, 0.0],
        [2.0, 0.0],
        [0.0, 1.0],
        [1.0, 1.0],
        [2.0, 1.0],
        [0.0, 2.0],
        [1.0, 2.0],
        [2.0, 2.0],
    ], dtype=float)

    connectivity = np.array([
        [0, 1, 4, 3],  # Lower-left quad
        [1, 2, 5, 4],  # Lower-right quad
        [3, 4, 7, 6],  # Upper-left quad
        [4, 5, 8, 7],  # Upper-right quad
    ], dtype=int)

    # Create mesh with adjacencies but no layers
    mesh = CHILmesh(connectivity, points, compute_adjacencies=True, compute_layers=False)

    # Verify initial state: layers exist but are empty
    assert hasattr(mesh, "layers"), "CHILmesh should have layers attribute"
    assert mesh.layers.get("OE") == [] or not mesh.layers.get("OE"), "OE should be empty initially"

    return mesh


def test_validator_triggers_peel_layers(small_synthetic_mesh):
    """Test that validate_mesh_elements triggers peel_layers when layers are empty."""
    mesh = small_synthetic_mesh

    # Verify mesh has peel_layers method (CHILmesh 1.4.0+)
    assert hasattr(mesh, "peel_layers"), "Test fixture should use CHILmesh 1.4.0+"

    # Layers should be empty initially
    initial_oe = mesh.layers.get("OE")
    assert not initial_oe, "Layers should be empty before validator call"

    # Run validator; it should trigger peel_layers auto-computation
    report = validate_mesh_elements(mesh)

    # Check that layers were computed
    assert mesh.layers.get("OE"), "Layers should be populated after validator call"

    # Check that the informational note was recorded
    note_categories = {note.category for note in report.notes}
    assert "LAYERS_AUTO_TRIGGERED" in note_categories, \
        f"Expected LAYERS_AUTO_TRIGGERED note; got {note_categories}"

    # Verify the note mentions peel_layers
    auto_triggered_notes = [n for n in report.notes if n.category == "LAYERS_AUTO_TRIGGERED"]
    assert len(auto_triggered_notes) == 1
    assert "peel_layers" in auto_triggered_notes[0].detail.lower(), \
        f"Note should mention peel_layers; got: {auto_triggered_notes[0].detail}"


def test_validator_report_ok_when_layers_computed(small_synthetic_mesh):
    """Test that validator produces valid report after auto-computing layers."""
    mesh = small_synthetic_mesh

    # Run validator
    report = validate_mesh_elements(mesh)

    # Report should complete without crashing
    assert report is not None
    assert hasattr(report, "ok")
    assert hasattr(report, "violations")
    assert hasattr(report, "notes")

    # For a simple well-formed quad grid, no violations expected
    # (mesh is planar, no self-intersections, all quads)
    assert report.ok, f"Expected valid mesh; got violations: {report.violations}"
