"""Regression tests for the #109 silent-skip loudness hook in conftest.py.

The hook `pytest_terminal_summary` warns loudly when mesh-dependent tests
(incl. the faithfulness gate) skip because `.14` fixtures are absent, so a
green CI run that never exercised the gate cannot masquerade as a pass.

The original hook filtered with `"fixture missing:" in report.longrepr`, but a
skip report's `longrepr` is a `(path, lineno, "Skipped: <reason>")` tuple —
so that membership test matched nothing and the hook was dead on arrival.
These tests pin the string-normalizing detection so the regression can't recur.
"""

from __future__ import annotations

from types import SimpleNamespace

from conftest import _gate_exercised, _is_fixture_missing_skip, _skip_reason


def _skip_report(reason: str, nodeid: str = "tests/test_x.py::test_a"):
    """Fake a pytest skip report: longrepr is a (path, lineno, reason) tuple."""
    return SimpleNamespace(
        longrepr=("tests/test_x.py", 3, f"Skipped: {reason}"),
        nodeid=nodeid,
    )


def test_skip_reason_extracts_from_tuple():
    r = _skip_report("fixture missing: /meshes/Block_O.14")
    assert _skip_reason(r) == "Skipped: fixture missing: /meshes/Block_O.14"


def test_skip_reason_handles_string_longrepr():
    r = SimpleNamespace(longrepr="Skipped: fixture missing: /x.14", nodeid="n")
    assert "fixture missing:" in _skip_reason(r)


def test_skip_reason_handles_none():
    assert _skip_reason(SimpleNamespace(longrepr=None)) == ""


def test_fixture_missing_skip_detected_through_tuple():
    # The exact shape that defeated the original `in report.longrepr` filter.
    r = _skip_report("fixture missing: /meshes/Test_Case_1.14")
    assert _is_fixture_missing_skip(r) is True


def test_non_fixture_skip_not_flagged():
    r = _skip_report("Pass --runslow to run slow tests")
    assert _is_fixture_missing_skip(r) is False


class _Reporter:
    """Minimal stand-in for pytest's terminalreporter (only .stats used)."""

    def __init__(self, **stats):
        self.stats = stats


def _run_report(nodeid: str):
    return SimpleNamespace(nodeid=nodeid)


def test_gate_exercised_true_when_gate_test_ran():
    rep = _Reporter(passed=[_run_report("tests/test_no_interior_tris.py::test_x")])
    assert _gate_exercised(rep) is True


def test_gate_exercised_counts_failures_too():
    rep = _Reporter(failed=[_run_report("tests/test_no_interior_tris.py::test_x")])
    assert _gate_exercised(rep) is True


def test_gate_not_exercised_when_only_skipped():
    # Gate present only among skips (any reason) → not exercised. This is the
    # case the old fixture-missing-only check reported as "not affected".
    rep = _Reporter(
        passed=[_run_report("tests/test_other.py::test_y")],
        skipped=[_skip_report("chilmesh.data mesh unavailable: annulus",
                              nodeid="tests/test_no_interior_tris.py::test_z")],
    )
    assert _gate_exercised(rep) is False
