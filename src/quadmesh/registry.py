"""Valence registry client, re-exported from ``chilmesh.registry``.

Importing this module always succeeds. If the installed chilmesh does not ship
``chilmesh.registry``, every function raises ``ImportError`` with an upgrade hint.
"""

from __future__ import annotations

__all__ = [
    "RegistryError", "RegistryAuthError", "RegistryNotFoundError",
    "RegistryUnavailableError", "RegistryIntegrityError",
    "list_meshes", "fetch_hash", "fetch_mesh_bytes", "fetch_mesh", "download_mesh",
]

try:
    from chilmesh.registry import (  # noqa: F401
        RegistryAuthError,
        RegistryError,
        RegistryIntegrityError,
        RegistryNotFoundError,
        RegistryUnavailableError,
        download_mesh,
        fetch_hash,
        fetch_mesh,
        fetch_mesh_bytes,
        list_meshes,
    )

    AVAILABLE = True
except ImportError:
    AVAILABLE = False
    try:
        from importlib.metadata import version as _v

        _installed = _v("chilmesh")
    except Exception:  # pragma: no cover
        _installed = "unknown"
    _MSG = (
        "Valence registry client needs chilmesh with chilmesh.registry "
        f"(newer than installed {_installed}); upgrade chilmesh"
    )

    class RegistryError(RuntimeError):
        """Base registry error (stub)."""

    class RegistryAuthError(RegistryError):
        pass

    class RegistryNotFoundError(RegistryError, ValueError):
        pass

    class RegistryUnavailableError(RegistryError):
        pass

    class RegistryIntegrityError(RegistryError):
        pass

    def _missing(*_a, **_k):
        raise ImportError(_MSG)

    list_meshes = fetch_hash = fetch_mesh_bytes = fetch_mesh = download_mesh = _missing
