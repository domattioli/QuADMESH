"""Shared adapter contract tests, parametrized over the registry (spec 058)."""
from __future__ import annotations

import os

import numpy as np
import pytest

import chilmesh
from chilmesh import CHILmesh

from quadmesh.benchmark import AdapterOptions, AdapterResult, get_adapters, register
from quadmesh.benchmark._protocol import Availability, LICENSE_TAGS, unregister
from quadmesh.benchmark._metrics import element_rows


def smallest_mesh() -> CHILmesh:
    path = os.path.join(os.path.dirname(chilmesh.__file__), "data", "donut_domain.fort.14")
    return CHILmesh.read_from_fort14(path)


class PassThrough:
    """Test-only adapter: returns a copy of the input (SC-002)."""

    name = "test-pass-through"
    display_name = "Pass through"
    family = "direct"
    license_tag = "project"
    citation = "none"
    install_route = "base"
    install_hint = ""
    accepts_mixed = True

    def probe(self):
        return Availability(True, "test", None, "")

    def run(self, mesh, options):
        out = CHILmesh(np.array(mesh.connectivity_list), np.array(mesh.points))
        return AdapterResult(mesh=out, adapter=self.name, version="test",
                             license_tag=self.license_tag)


@pytest.fixture
def with_pass_through():
    register(PassThrough)
    yield
    unregister(PassThrough.name)


def _all():
    register(PassThrough)
    names = sorted(get_adapters())
    unregister(PassThrough.name)
    return names


@pytest.fixture(params=_all())
def adapter(request, with_pass_through):
    ad = get_adapters()[request.param]
    av = ad.probe()
    assert isinstance(av, Availability)
    if not av.installed:
        pytest.skip(f"{ad.name} not installed: {av.message}")
    return ad


def test_metadata_typed(adapter):
    for f in ("name", "display_name", "family", "license_tag", "citation",
              "install_route", "install_hint"):
        assert isinstance(getattr(adapter, f), str)
    assert adapter.license_tag in LICENSE_TAGS
    assert isinstance(adapter.accepts_mixed, bool)


def test_run_contract(adapter):
    mesh = smallest_mesh()
    pts, cl = np.array(mesh.points), np.array(mesh.connectivity_list)
    res = adapter.run(mesh, AdapterOptions(timeout_s=60))
    assert isinstance(res, AdapterResult) and res.success, res.message
    assert res.adapter == adapter.name and isinstance(res.runtime_s, float)
    assert isinstance(res.vertex_order_preserved, bool)
    out = res.mesh
    assert out.n_verts > 0
    P = np.asarray(out.points)[:, :2]
    for r in element_rows(out.connectivity_list):
        q = P[r]
        x, y = q[:, 0], q[:, 1]
        area2 = float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))
        assert area2 > 0, f"element {r} not CCW or zero area"
    # input immutability
    assert np.array_equal(np.asarray(mesh.points), pts)
    assert np.array_equal(np.asarray(mesh.connectivity_list), cl)


def test_residuals_reported_not_asserted(adapter):
    from quadmesh.benchmark._metrics import residual_split, row_from_result
    mesh = smallest_mesh()
    res = adapter.run(mesh, AdapterOptions(timeout_s=60))
    row = row_from_result("donut", mesh, res)
    assert row.residual_tris_interior is not None
    if adapter.name == "quadmesh-plus":
        assert residual_split(res.mesh.connectivity_list)[0] == 0  # FR-017


def test_pass_through_included_without_edits(with_pass_through):
    """SC-002: a new adapter appears in the registry and runner with one decorator."""
    from quadmesh.benchmark import run_benchmark
    rec = run_benchmark([smallest_mesh()], adapters=["test-pass-through"])
    assert [r.status for r in rec.rows] == ["ok"]
