"""Pytest fixtures. Load test .14 meshes from `tests/fixtures/meshes`."""

from __future__ import annotations

from pathlib import Path

import pytest

from chilmesh import CHILmesh


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "meshes"


def _load(name: str) -> CHILmesh:
    path = FIXTURE_DIR / name
    if not path.exists():
        pytest.skip(f"fixture missing: {path}")
    return CHILmesh.read_from_fort14(path)


@pytest.fixture(scope="session")
def test_case_1() -> CHILmesh:
    return _load("Test_Case_1.14")


@pytest.fixture(scope="session")
def test_case_2() -> CHILmesh:
    return _load("Test_Case_2.14")


@pytest.fixture(scope="session")
def mixed_test() -> CHILmesh:
    return _load("Mixed_Test.14")


@pytest.fixture(scope="session")
def _block_o() -> CHILmesh:
    """Block_O fixture for parity scaffold (test_parity.py)."""
    return _load("Block_O.14")


def pytest_addoption(parser):
    parser.addoption(
        "--runslow",
        action="store_true",
        default=False,
        help="Run tests marked @pytest.mark.slow (large meshes, slow algorithms).",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip_slow = pytest.mark.skip(reason="Pass --runslow to run slow tests")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


def pytest_configure(config):
    """Best-effort provision of test meshes from the Valence registry.

    Meshes are not vendored in this repo (see Valence registry); when a
    GITHUB_TOKEN / GH_TOKEN with cross-repo read on domattioli/Valence is
    available, fetch + integrity-check them into tests/fixtures/meshes/.
    No token or offline -> no-op; mesh-dependent tests skip as before.
    """
    import importlib.util
    from pathlib import Path

    mod_path = Path(__file__).resolve().parent / "_mesh_provision.py"
    spec = importlib.util.spec_from_file_location("_mesh_provision", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    results = mod.provision()
    fetched = [n for n, s in results.items() if s == "fetched"]
    errors = {n: s for n, s in results.items() if s.startswith("error")}
    if fetched:
        reporter = config.pluginmanager.get_plugin("terminalreporter")
        if reporter:
            print(
                f"[fixtures] provisioned {len(fetched)} mesh(es) from Valence: "
                f"{', '.join(sorted(fetched))}"
            )
    if errors:
        print(f"[fixtures] provision errors (tests will skip): {errors}")


def _skip_reason(report) -> str:
    """Normalize a skip report's ``longrepr`` to its reason string.

    A skipped test's ``longrepr`` is a ``(path, lineno, "Skipped: <reason>")``
    tuple, NOT a bare string — so a naive ``"fixture missing:" in report.longrepr``
    tests tuple *membership* (element equality) and silently never matches, which
    left the #109 loudness hook dead on arrival. Return the reason string so the
    substring test works regardless of longrepr shape.
    """
    lr = getattr(report, "longrepr", None)
    if isinstance(lr, tuple):
        return str(lr[-1])
    return "" if lr is None else str(lr)


def _is_fixture_missing_skip(report) -> bool:
    """True when ``report`` is a skip caused by a missing ``.14`` fixture."""
    return "fixture missing:" in _skip_reason(report)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Report on mesh-dependent tests skipped due to missing fixtures.

    Makes silent fixture-missing skips visible to alert when the faithfulness
    gate (test_no_interior_tris) is not exercised.
    """
    # Collect all skipped reports
    skipped_reports = terminalreporter.stats.get("skipped", [])

    # Filter for fixture-missing skips
    fixture_missing_skips = [
        r for r in skipped_reports
        if _is_fixture_missing_skip(r)
    ]

    if not fixture_missing_skips:
        return

    # Check if the faithfulness gate is among the skipped
    gate_not_exercised = any(
        "test_no_interior_tris" in r.nodeid
        for r in fixture_missing_skips
    )

    gate_status = "NOT EXERCISED" if gate_not_exercised else "not affected"
    msg = (
        f"{len(fixture_missing_skips)} mesh-dependent test(s) skipped "
        f"(no Valence token / offline) — FAITHFULNESS GATE {gate_status}"
    )

    terminalreporter.write_sep("=", msg, red=True, bold=True)
    terminalreporter.write_line(msg, red=True, bold=True)
