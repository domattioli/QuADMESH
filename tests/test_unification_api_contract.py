"""Pin the QuADMesh public-API surface for MADMESHing unification (issue #82).

MADMESHing (https://github.com/domattioli/MADMESHing) depends on stable
imports and signatures from QuADMesh:
  - `from quadmesh.pipeline import run_pipeline`
  - `from quadmesh.post_process import post_process_routine, fem_smoother, two_part_smoother`
  - `from quadmesh.quality_report import compute_quality_stats, format_quality_report`

This contract test fails CI if those symbols move, change signature, are
removed from `__all__`, or (in the case of `two_part_smoother`) the
deprecation alias is lost. Ensures MADMESHing's compare.py stays unbroken
across QuADMesh versions.

Reference: domattioli/QuADMesh#82, MADMESHing#48
"""

from __future__ import annotations

import inspect


def test_unification_surface_importable():
    """Pipeline, post-process, and quality functions are importable."""
    from quadmesh.pipeline import run_pipeline
    from quadmesh.post_process import (
        post_process_routine,
        fem_smoother,
        two_part_smoother,
    )
    from quadmesh.quality_report import compute_quality_stats, format_quality_report

    assert run_pipeline is not None
    assert post_process_routine is not None
    assert fem_smoother is not None
    assert two_part_smoother is not None
    assert compute_quality_stats is not None
    assert format_quality_report is not None


def test_lazy_top_level_run_pipeline():
    """import quadmesh; quadmesh.run_pipeline is available via __getattr__."""
    import quadmesh
    from quadmesh.pipeline import run_pipeline

    assert quadmesh.run_pipeline is run_pipeline, (
        "quadmesh.run_pipeline must be accessible via __getattr__ lazy import"
    )


def test_unification_surface_in_all():
    """Key symbols are in quadmesh.__all__."""
    import quadmesh

    expected = {
        "tri2quad",
        "post_process",
        "fem_smoother",
        "compute_quality_stats",
        "format_quality_report",
    }
    missing = expected - set(quadmesh.__all__)
    assert not missing, f"quadmesh.__all__ missing: {missing}"


def test_run_pipeline_signature():
    """run_pipeline() has required signature for MADMESHing.

    MADMESHing calls: run_pipeline(mesh, polygon=None, can_remove_edges=True,
    n_smooth_iter=3, do_post_process=True, max_outer_iter=5, max_inner_iter=5,
    method='quadmesh+', truss_smooth=False, truss_fh=None).
    """
    from quadmesh.pipeline import run_pipeline

    sig = inspect.signature(run_pipeline)
    params = sig.parameters

    # Parameter list and order
    param_list = list(params.keys())
    expected_params = [
        "mesh",
        "polygon",
        "can_remove_edges",
        "n_smooth_iter",
        "do_post_process",
        "max_outer_iter",
        "max_inner_iter",
        "method",
        "truss_smooth",
        "truss_fh",
        "refuse_boundary_merge",
        # spec-056 #104 — appended AFTER the pinned contract params so every
        # existing positional index is unchanged (MADMESHing calls by keyword).
        "hierarchical",
        "hierarchical_opts",
    ]
    assert param_list == expected_params, (
        f"run_pipeline params in wrong order. Expected {expected_params}, got {param_list}"
    )

    # Check defaults
    assert params["do_post_process"].default is True, (
        "do_post_process must default to True"
    )
    assert params["method"].default == "quadmesh+", (
        "method must default to 'quadmesh+'"
    )
    assert params["can_remove_edges"].default is True, (
        "can_remove_edges must default to True"
    )
    assert params["n_smooth_iter"].default == 3, (
        "n_smooth_iter must default to 3"
    )


def test_fem_smoother_signature():
    """fem_smoother() has required signature."""
    from quadmesh.post_process import fem_smoother

    sig = inspect.signature(fem_smoother)
    params = sig.parameters

    # Expected params: mesh, n_iter, method
    param_list = list(params.keys())
    assert param_list == ["mesh", "n_iter", "method"], (
        f"fem_smoother params should be [mesh, n_iter, method], got {param_list}"
    )

    # Check defaults
    assert params["n_iter"].default == 3, "n_iter must default to 3"
    assert params["method"].default == "fem", "method must default to 'fem'"


def test_two_part_smoother_deprecated_alias():
    """two_part_smoother() is a deprecated alias matching fem_smoother signature."""
    from quadmesh.post_process import two_part_smoother, fem_smoother

    sig_two_part = inspect.signature(two_part_smoother)
    sig_fem = inspect.signature(fem_smoother)

    # Signatures must match
    params_two_part = list(sig_two_part.parameters.keys())
    params_fem = list(sig_fem.parameters.keys())
    assert params_two_part == params_fem, (
        f"two_part_smoother params {params_two_part} != fem_smoother params {params_fem}"
    )

    # Check defaults match
    for param_name in params_fem:
        default_two_part = sig_two_part.parameters[param_name].default
        default_fem = sig_fem.parameters[param_name].default
        assert default_two_part == default_fem, (
            f"Default for {param_name} differs: "
            f"two_part_smoother={default_two_part} vs fem_smoother={default_fem}"
        )

    # Check that two_part_smoother references fem_smoother and mentions deprecation
    source = inspect.getsource(two_part_smoother)
    assert "fem_smoother" in source, "two_part_smoother must call fem_smoother"
    assert "DeprecationWarning" in source, (
        "two_part_smoother must emit DeprecationWarning"
    )


def test_canonical_modules():
    """Symbols live in pinned canonical modules."""
    from quadmesh.pipeline import run_pipeline
    from quadmesh.post_process import fem_smoother, post_process_routine
    from quadmesh.quality_report import compute_quality_stats

    assert run_pipeline.__module__ == "quadmesh.pipeline", (
        f"run_pipeline must live in quadmesh.pipeline, found in {run_pipeline.__module__}"
    )
    assert fem_smoother.__module__ == "quadmesh.post_process", (
        f"fem_smoother must live in quadmesh.post_process, found in {fem_smoother.__module__}"
    )
    assert post_process_routine.__module__ == "quadmesh.post_process", (
        f"post_process_routine must live in quadmesh.post_process, "
        f"found in {post_process_routine.__module__}"
    )
    assert compute_quality_stats.__module__ == "quadmesh.quality_report", (
        f"compute_quality_stats must live in quadmesh.quality_report, "
        f"found in {compute_quality_stats.__module__}"
    )


def test_compute_quality_stats_signature():
    """compute_quality_stats() has single parameter: mesh."""
    from quadmesh.quality_report import compute_quality_stats

    sig = inspect.signature(compute_quality_stats)
    params = sig.parameters

    param_list = list(params.keys())
    assert param_list == ["mesh"], (
        f"compute_quality_stats must have single param 'mesh', got {param_list}"
    )
