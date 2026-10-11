"""Provision pinned test meshes through ``chilmesh.registry`` only."""
from __future__ import annotations

import hashlib
import os
from importlib import resources
from pathlib import Path

try:
    import chilmesh.registry as registry
except ImportError:
    registry = None

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "meshes"
MANIFEST: dict[str, str] = {
    "Block_O.14": "d67869e16282d36e6b8bd5cd512cd7a960ddedc53af87196c0f4e8a7e55440dc",
    "Test_Case_1.14": "39bfe3bd5ca35b37d3379267a92297e10ab265bf6a5b132253ec1d50c9285ce9",
    "Test_Case_2.14": "28b8119fae43ec3ed6ec046ff7e4767a94eb72abf2762216688ff3326016e505",
    "Test_Case_3.14": "179427a6f48c2cf92d8139e91b2a4de39825f8bc26e38b4b9cd2e2f71775bb8d",
    "simple_test_case.14": "0e0f8e65e1b3c3208ef75acfe3323f8d43d58e2286c02e86206ea2b4b8293a99",
    "square_mesh_test.14": "77ee24d326270681198245907b1f185faf6ff4f6ed2dd1d48a29593976be2455",
    "structuredMesh1.14": "baf81485021e39edaebf7d1a0f7c320b4e1d47b8f2db7096549ff38b1ee13f60",
}


def _chilmesh_data_bytes(name: str) -> bytes | None:
    try:
        path = resources.files("chilmesh").joinpath("data", name)
        return path.read_bytes() if path.is_file() else None
    except (ModuleNotFoundError, FileNotFoundError, OSError, AttributeError):
        return None


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fallback(name: str, dest: Path, reason: str) -> str:
    data = _chilmesh_data_bytes(name)
    if data is None or _sha256(data) != MANIFEST[name]:
        return f"skip: {reason}; bundled bytes differ from pin"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / name).write_bytes(data)
    return "fetched-chilmesh"


def _is_outage(error: Exception) -> bool:
    return error.__class__.__name__ == "RegistryUnavailableError"


def provision(names: list[str] | None = None, dest: Path | None = None) -> dict[str, str]:
    """Provision pinned meshes. Integrity and authenticated-not-found errors fail."""
    names = list(MANIFEST) if names is None else names
    dest = FIXTURE_DIR if dest is None else dest
    token = os.environ.get("VALENCE_TOKEN", "").strip()
    results: dict[str, str] = {}
    for name in names:
        if name not in MANIFEST:
            raise ValueError(f"un-pinned fixture: {name}")
        local = dest / name
        if local.is_file():
            if _sha256(local.read_bytes()) == MANIFEST[name]:
                results[name] = "present"
                continue
            # Stale cache from an older pin: discard and re-provision.
            local.unlink()
        if os.environ.get("QUADMESH_NO_FETCH"):
            results[name] = _fallback(name, dest, "QUADMESH_NO_FETCH set")
            continue
        if not token:
            results[name] = _fallback(name, dest, "no VALENCE_TOKEN")
            continue
        if registry is None:
            results[name] = _fallback(name, dest, "chilmesh.registry unavailable")
            continue
        try:
            remote_hash = registry.fetch_hash(name)
            data = registry.fetch_mesh_bytes(name)
        except Exception as error:
            if _is_outage(error):
                results[name] = "skip: registry unavailable"
                continue
            raise RuntimeError(f"fixture {name}: registry request failed") from error
        if not isinstance(remote_hash, str) or remote_hash != MANIFEST[name]:
            raise RuntimeError(f"fixture {name}: registry hash differs from pin")
        if _sha256(data) != MANIFEST[name]:
            raise RuntimeError(f"fixture {name}: downloaded bytes differ from pin")
        dest.mkdir(parents=True, exist_ok=True)
        local.write_bytes(data)
        results[name] = "fetched"
    return results


def needed_names() -> list[str]:
    return list(MANIFEST)
