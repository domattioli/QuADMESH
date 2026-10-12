"""Runner behaviour: isolation, timeout, opt-out, unsupported input (spec 058)."""
from __future__ import annotations

import time

import numpy as np
import pytest
from chilmesh import CHILmesh

from quadmesh.benchmark import AdapterResult, Availability, register, run_benchmark
from quadmesh.benchmark._protocol import unregister
from quadmesh.benchmark._report import load_json
from test_bench_contract import smallest_mesh


class _Base:
    display_name = "Fake"
    family = "direct"
    license_tag = "project"
    citation = ""
    install_route = "external"
    install_hint = "install fake-tool"
    accepts_mixed = False

    def probe(self):
        return Availability(True, "1", None, "")

    def run(self, mesh, options):
        out = CHILmesh(np.array(mesh.connectivity_list), np.array(mesh.points))
        return AdapterResult(out, self.name)


class Boom(_Base):
    name = "fake-boom"

    def run(self, mesh, options):
        raise RuntimeError("kaboom")


class Missing(_Base):
    name = "fake-missing"

    def probe(self):
        return Availability(False, None, None, "fake-tool not found")


class Slow(_Base):
    name = "fake-slow"

    def run(self, mesh, options):
        time.sleep(1.0)
        return super().run(mesh, options)


class Ok(_Base):
    name = "fake-ok"


@pytest.fixture
def fakes():
    classes = (Boom, Missing, Slow, Ok)
    for c in classes:
        register(c)
    yield
    for c in classes:
        unregister(c.name)


def _status(rec):
    return {r.adapter: r.status for r in rec.rows}


def test_two_builtins_ok():
    rec = run_benchmark([smallest_mesh()], adapters=["quadmesh-plus", "greedy-tri-merge"])
    assert _status(rec) == {"quadmesh-plus": "ok", "greedy-tri-merge": "ok"}
    assert all(r.residual_tris_interior is not None for r in rec.rows)


def test_failure_isolated_and_missing_has_hint(fakes):
    rec = run_benchmark([smallest_mesh()], adapters=["fake-boom", "fake-missing", "fake-ok"])
    s = _status(rec)
    assert s == {"fake-boom": "failed", "fake-missing": "not installed", "fake-ok": "ok"}
    miss = [r for r in rec.rows if r.adapter == "fake-missing"][0]
    assert "install fake-tool" in miss.message
    assert "kaboom" in [r for r in rec.rows if r.adapter == "fake-boom"][0].message


def test_timeout(fakes):
    rec = run_benchmark([smallest_mesh()], adapters=["fake-slow"], timeout_s=0.1)
    assert _status(rec) == {"fake-slow": "timeout"}


def test_disable_argument_and_env(fakes):
    rec = run_benchmark([smallest_mesh()], adapters=["fake-ok", "fake-boom"], disabled=["fake-boom"])
    assert _status(rec) == {"fake-ok": "ok"}
    rec = run_benchmark([smallest_mesh()], adapters=["fake-ok", "fake-boom"],
                        env={"QUADMESH_BENCH_DISABLE": "fake-ok"}, show_disabled=True)
    assert _status(rec) == {"fake-ok": "disabled", "fake-boom": "failed"}


def test_mixed_input_unsupported(fakes):
    mixed = CHILmesh(np.array([[0, 1, 2, 3], [1, 4, 2, 2]]),
                     np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [2, .5, 0]], float))
    rec = run_benchmark([mixed], adapters=["fake-ok"])
    assert _status(rec) == {"fake-ok": "unsupported input"}


def test_unknown_adapter_raises():
    with pytest.raises(KeyError):
        run_benchmark([smallest_mesh()], adapters=["nope"])


def test_report_roundtrip(tmp_path):
    rec = run_benchmark([smallest_mesh()], adapters=["greedy-tri-merge"])
    rec.to_json(tmp_path / "r.json")
    back = load_json(tmp_path / "r.json")
    assert back.rows == rec.rows and back.meshes == rec.meshes
    md = rec.to_markdown()
    assert "greedy-tri-merge" in md and "Reproduce" in md
