"""quadmesh-bench CLI exit codes and listing (spec 058)."""
from __future__ import annotations

import os

import pytest

import chilmesh
from quadmesh.benchmark import register
from quadmesh.benchmark._protocol import unregister
from quadmesh.benchmark.cli import main
from test_bench_runner import Missing

DONUT = os.path.join(os.path.dirname(chilmesh.__file__), "data", "donut_domain.fort.14")


@pytest.fixture
def missing():
    register(Missing)
    yield
    unregister(Missing.name)


def test_list(capsys):
    assert main(["--list"]) == 0
    out = capsys.readouterr().out
    assert "quadmesh-plus" in out and "greedy-tri-merge" in out and "available" in out


def test_list_shows_disabled_and_hint(capsys, missing):
    assert main(["--list", "--disable", "greedy-tri-merge"]) == 0
    out = capsys.readouterr().out
    assert "greedy-tri-merge\tclean-room\tbase\tdisabled" in out
    assert "not installed: install fake-tool" in out


def test_unknown_adapter_exit_2(capsys):
    assert main([DONUT, "--adapters", "nope"]) == 2
    assert "known" in capsys.readouterr().err


def test_strict_exit_codes(missing):
    args = [DONUT, "--adapters", "greedy-tri-merge,fake-missing"]
    assert main(args) == 0
    assert main(args + ["--strict"]) == 1
    assert main([DONUT, "--adapters", "greedy-tri-merge", "--strict"]) == 0


def test_disable_and_show_disabled(capsys):
    args = [DONUT, "--adapters", "quadmesh-plus,greedy-tri-merge", "--disable", "greedy-tri-merge"]
    assert main(args) == 0
    assert "| greedy recombination (baseline) |" not in capsys.readouterr().out
    assert main(args + ["--show-disabled"]) == 0
    assert "| greedy recombination (baseline) | disabled" in capsys.readouterr().out


def test_out_writes_files(tmp_path):
    assert main([DONUT, "--adapters", "greedy-tri-merge", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "results.md").exists() and (tmp_path / "results.json").exists()
