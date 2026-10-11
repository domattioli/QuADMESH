"""Wheel carries no GPL tool code and no Valence code (spec 058 R9, R11)."""
from __future__ import annotations

import re
import subprocess
import sys
import tomllib
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("gmsh", "comiso", "qex", "valence")


def test_pyproject_extras_name_no_gpl():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())
    extras = data["project"]["optional-dependencies"]
    for name, deps in extras.items():
        if name.startswith("bench"):
            for d in deps:
                assert not re.search(r"gmsh|comiso|libqex", d, re.I), (name, d)
    qf = extras["bench-quadriflow"]
    assert len(qf) == 1 and qf[0].startswith("pyquadriflow")
    assert "linux" in qf[0] and "win32" in qf[0] and "darwin" not in qf[0]
    assert data["project"]["scripts"]["quadmesh-bench"] == "quadmesh.benchmark.cli:main"


def test_import_does_not_pull_gmsh():
    code = ("import sys, quadmesh.benchmark as b; b.get_adapters(); "
            "assert 'gmsh' not in sys.modules")
    subprocess.run([sys.executable, "-c", code], check=True)


@pytest.mark.slow
def test_wheel_has_no_gpl_or_valence_paths(tmp_path):
    r = subprocess.run(
        [sys.executable, "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
         "-w", str(tmp_path), str(ROOT)], capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"wheel build unavailable: {r.stderr[-300:]}")
    wheel = next(tmp_path.glob("*.whl"))
    names = zipfile.ZipFile(wheel).namelist()
    assert any("benchmark" in n for n in names)
    # The subprocess wrapper (our own code, no Gmsh content) is the one allowed path.
    allowed = {"quadmesh/benchmark/adapters/gmsh_blossom.py"}
    bad = [n for n in names if n not in allowed and any(f in n.lower() for f in FORBIDDEN)]
    assert not bad, bad
