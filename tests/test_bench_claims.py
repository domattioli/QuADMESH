"""Public claims match registered adapters (spec 058, R8, FR-015, FR-021)."""
from __future__ import annotations

import re
from pathlib import Path

from quadmesh.benchmark import get_adapters

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text()
DESC = re.search(r'^description = "(.*)"', (ROOT / "pyproject.toml").read_text(), re.M).group(1)
KNOWN = ("QuadriFlow", "Gmsh", "Blossom-Quad")


def _benchmark_section() -> str:
    m = re.search(r"^## Benchmark\n(.*?)(?=^## )", README, re.M | re.S)
    return m.group(1) if m else ""


def test_named_tools_are_registered():
    names = " ".join(a.display_name for a in get_adapters().values()).lower()
    for text in (README, DESC):
        for hit in ("QuadriFlow", "Gmsh"):
            if hit in text:
                assert hit.lower() in names, f"{hit} named but not registered"


def test_external_adapters_marked():
    sec = _benchmark_section()
    for ad in get_adapters().values():
        if ad.install_route == "external" and ad.display_name in sec:
            para = next(p for p in sec.split("\n\n") if ad.display_name in p)
            assert "requires user-installed tool" in para


def test_benchmark_section_needs_results():
    if _benchmark_section():
        assert (ROOT / "docs" / "benchmarks" / "0.3.0" / "results.md").exists()


def test_description_names_only_ok_rows():
    results = (ROOT / "docs" / "benchmarks" / "0.3.0" / "results.md").read_text()
    for name in ("QuadriFlow", "Gmsh"):
        assert name not in DESC or f"| {name.lower()}" in results and "| ok |" in results
