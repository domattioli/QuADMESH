"""Verify offline chilmesh.data fallback in tests/_mesh_provision.py (QuADMESH #93)."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

_MOD_PATH = Path(__file__).resolve().parent / "_mesh_provision.py"
_spec = importlib.util.spec_from_file_location("_mesh_provision_fb", _MOD_PATH)
_mp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mp)


def _has_chilmesh_data(name: str) -> bool:
    return _mp._chilmesh_data_bytes(name) is not None


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


@pytest.mark.parametrize("name", ["structuredMesh1.14", "Block_O.14"])
def test_chilmesh_data_fallback_no_token(tmp_path, monkeypatch, name):
    """With no token and NO_FETCH set, mesh provisions from chilmesh.data, sha-verified."""
    if not _has_chilmesh_data(name):
        pytest.skip(f"chilmesh.data missing {name}")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setenv("QUADMESH_NO_FETCH", "1")
    res = _mp.provision([name], dest=tmp_path)
    assert res[name] in ("fetched-chilmesh", "present"), res
    out = tmp_path / name
    assert out.exists()
    assert _git_blob_sha1(out.read_bytes()) == _mp.MANIFEST[name]


def test_fallback_helper_returns_none_for_unknown():
    assert _mp._chilmesh_data_bytes("definitely_not_a_mesh_zzz.14") is None
