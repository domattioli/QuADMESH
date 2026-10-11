"""CLI --from-registry and quadmesh.registry stub behaviour (no network)."""

from __future__ import annotations

import importlib
import sys
import types
from importlib import resources

import pytest
from chilmesh import CHILmesh

from quadmesh import cli
from quadmesh import registry as qreg


def _mesh_path():
    return str(resources.files("chilmesh.data") / "annulus_200pts.fort.14")


def test_from_registry_happy_path(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(qreg, "fetch_mesh",
                        lambda name: CHILmesh.read_from_fort14(_mesh_path()))
    out = tmp_path / "o.14"
    rc = cli.main(["--from-registry", "ANN.14", "-o", str(out)])
    assert rc == 0 and out.exists()
    assert "loaded: ANN.14" in capsys.readouterr().out


def test_from_registry_error_exit2(tmp_path, monkeypatch, capsys):
    def boom(name):
        raise qreg.RegistryAuthError("VALENCE_TOKEN is not set")

    monkeypatch.setattr(qreg, "fetch_mesh", boom)
    rc = cli.main(["--from-registry", "X", "-o", str(tmp_path / "o.14")])
    err = capsys.readouterr().err
    assert rc == 2
    assert "VALENCE_TOKEN is not set" in err and "Traceback" not in err


def test_import_error_exit2(tmp_path, monkeypatch, capsys):
    def boom(name):
        raise ImportError("upgrade chilmesh")

    monkeypatch.setattr(qreg, "fetch_mesh", boom)
    assert cli.main(["--from-registry", "X", "-o", str(tmp_path / "o.14")]) == 2


def test_both_inputs_rejected(tmp_path):
    with pytest.raises(SystemExit) as e:
        cli.main([_mesh_path(), "--from-registry", "X", "-o", str(tmp_path / "o")])
    assert e.value.code == 2


def test_neither_input_rejected(tmp_path):
    with pytest.raises(SystemExit) as e:
        cli.main(["-o", str(tmp_path / "o")])
    assert e.value.code == 2


def test_stub_when_chilmesh_registry_absent(monkeypatch):
    monkeypatch.setitem(sys.modules, "chilmesh.registry", None)  # import fails
    saved = sys.modules.pop("quadmesh.registry", None)
    try:
        stub = importlib.import_module("quadmesh.registry")
        assert stub.AVAILABLE is False
        with pytest.raises(ImportError, match="upgrade chilmesh"):
            stub.fetch_mesh("X")
        assert issubclass(stub.RegistryNotFoundError, ValueError)
    finally:
        sys.modules.pop("quadmesh.registry", None)
        if saved is not None:
            sys.modules["quadmesh.registry"] = saved


def test_reexport_when_chilmesh_registry_present(monkeypatch):
    fake = types.ModuleType("chilmesh.registry")
    class RegistryError(RuntimeError): ...
    for n in ("RegistryAuthError", "RegistryNotFoundError",
              "RegistryUnavailableError", "RegistryIntegrityError"):
        setattr(fake, n, type(n, (RegistryError,), {}))
    fake.RegistryError = RegistryError
    for n in ("list_meshes", "fetch_hash", "fetch_mesh_bytes", "fetch_mesh",
              "download_mesh"):
        setattr(fake, n, lambda *a, **k: "ok")
    monkeypatch.setitem(sys.modules, "chilmesh.registry", fake)
    saved = sys.modules.pop("quadmesh.registry", None)
    try:
        mod = importlib.import_module("quadmesh.registry")
        assert mod.AVAILABLE and mod.fetch_mesh("x") == "ok"
    finally:
        sys.modules.pop("quadmesh.registry", None)
        if saved is not None:
            sys.modules["quadmesh.registry"] = saved
