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
    "Block_O.14": "d06983e1578523438bb9d87145ab356bfc0fe4f48cde1938f553629a5fad4328",
    "Test_Case_1.14": "a9150c12db5cb7a60866492b332abda49040f912afdcd1d9cc4db925cf6d9277",
    "Test_Case_2.14": "ab2dd98349c9e0fa247f285bbfb36de248b5434057c19daa05187b979a72d2b8",
    "Test_Case_3.14": "791f4529537c1bc3a8bf4a9087beb45834a112ee139272ae1c74a565c45b1157",
    "simple_test_case.14": "9c2ba61dbb45b25b43bf3404341534b8bfa5ee7c2caa9b39a8c07f55b9b7772d",
    "square_mesh_test.14": "762f7b9700b253088646110853404f07aef321b69921c0bb1dc7e1400faaaa1a",
    "structuredMesh1.14": "d6f7fac1898af01340ac7119e39a4ce5f32c19c7d4f43f16c0a4d7cddb2fa26a",
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
