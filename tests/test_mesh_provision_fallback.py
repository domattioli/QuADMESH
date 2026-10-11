"""Exercise registry-provision branches without network access."""
import hashlib
import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location("_mesh_provision_fb", Path(__file__).parent / "_mesh_provision.py")
_mp = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_mp)
NAME, DATA = "Block_O.14", b"pinned fixture"
PIN = hashlib.sha256(DATA).hexdigest()


class _Client:
    class RegistryUnavailableError(Exception): pass
    def __init__(self, digest=PIN, data=DATA, error=None): self.digest, self.data, self.error = digest, data, error
    def fetch_hash(self, name):
        if self.error: raise self.error
        return self.digest
    def fetch_mesh_bytes(self, name): return self.data


@pytest.fixture(autouse=True)
def pin(monkeypatch):
    monkeypatch.setattr(_mp, "MANIFEST", {NAME: PIN})


def test_no_token_uses_matching_bundled_bytes(tmp_path, monkeypatch):
    monkeypatch.delenv("VALENCE_TOKEN", raising=False); monkeypatch.setattr(_mp, "_chilmesh_data_bytes", lambda _: DATA)
    assert _mp.provision(dest=tmp_path)[NAME] == "fetched-chilmesh"


def test_no_token_skips_mismatched_bundled_bytes(tmp_path, monkeypatch):
    monkeypatch.delenv("VALENCE_TOKEN", raising=False); monkeypatch.setattr(_mp, "_chilmesh_data_bytes", lambda _: b"old")
    assert "no VALENCE_TOKEN; bundled bytes differ from pin" in _mp.provision(dest=tmp_path)[NAME]


def test_missing_client_skips_with_distinct_reason(tmp_path, monkeypatch):
    monkeypatch.setenv("VALENCE_TOKEN", "token"); monkeypatch.setattr(_mp, "registry", None); monkeypatch.setattr(_mp, "_chilmesh_data_bytes", lambda _: b"old")
    assert "chilmesh.registry unavailable; bundled bytes differ from pin" in _mp.provision(dest=tmp_path)[NAME]


def test_client_fetches_matching_bytes(tmp_path, monkeypatch):
    monkeypatch.setenv("VALENCE_TOKEN", "token"); monkeypatch.setattr(_mp, "registry", _Client())
    assert _mp.provision(dest=tmp_path)[NAME] == "fetched"


@pytest.mark.parametrize("client", [_Client(digest="0" * 64), _Client(data=b"bad")])
def test_client_integrity_mismatch_fails(tmp_path, monkeypatch, client):
    monkeypatch.setenv("VALENCE_TOKEN", "token"); monkeypatch.setattr(_mp, "registry", client)
    with pytest.raises(RuntimeError, match="differ.*pin"): _mp.provision(dest=tmp_path)


@pytest.mark.parametrize("error", [Exception("401"), Exception("404"), ValueError("malformed")])
def test_client_auth_not_found_and_malformed_fail(tmp_path, monkeypatch, error):
    monkeypatch.setenv("VALENCE_TOKEN", "token"); monkeypatch.setattr(_mp, "registry", _Client(error=error))
    with pytest.raises(RuntimeError, match="registry request failed"): _mp.provision(dest=tmp_path)


def test_client_outage_skips(tmp_path, monkeypatch):
    monkeypatch.setenv("VALENCE_TOKEN", "token"); monkeypatch.setattr(_mp, "registry", _Client(error=_Client.RegistryUnavailableError()))
    assert _mp.provision(dest=tmp_path)[NAME] == "skip: registry unavailable"


def test_stale_local_cache_is_discarded(tmp_path, monkeypatch):
    monkeypatch.delenv("VALENCE_TOKEN", raising=False)
    monkeypatch.setattr(_mp, "_chilmesh_data_bytes", lambda name: None)
    (tmp_path / NAME).write_bytes(b"old")
    assert _mp.provision(names=[NAME], dest=tmp_path)[NAME].startswith("skip: no VALENCE_TOKEN")
    assert not (tmp_path / NAME).exists()


def test_no_fetch_env_uses_bundled_even_with_token(tmp_path, monkeypatch):
    monkeypatch.setenv("VALENCE_TOKEN", "token"); monkeypatch.setenv("QUADMESH_NO_FETCH", "1")
    monkeypatch.setattr(_mp, "registry", _Client(error=AssertionError("network used")))
    monkeypatch.setattr(_mp, "_chilmesh_data_bytes", lambda _: DATA)
    assert _mp.provision(names=[NAME], dest=tmp_path)[NAME] == "fetched-chilmesh"


def test_wrong_pin_then_outage_fails_not_skips(tmp_path, monkeypatch):
    class _Outage(_Client):
        def fetch_mesh_bytes(self, name): raise _Client.RegistryUnavailableError()
    monkeypatch.setenv("VALENCE_TOKEN", "token"); monkeypatch.setattr(_mp, "registry", _Outage(digest="0" * 64))
    with pytest.raises(RuntimeError, match="registry hash differs from pin"): _mp.provision(dest=tmp_path)
