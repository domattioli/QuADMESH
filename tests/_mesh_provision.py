"""Provision test .14 meshes from domattioli/Valence registry via authenticated GitHub API.

Meshes are integrity-checked by git-blob-sha1 and cached into tests/fixtures/meshes/
(gitignored). Gracefully no-ops when no auth token is present.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "meshes"

VALENCE_OWNER = "domattioli"
VALENCE_REPO = "Valence"
VALENCE_PATH = "registry_data/meshes"

MANIFEST: dict[str, str] = {
    "Block_O.14": "9a98cf04ca54cd1d2a7a96efab317e854888fb90",
    "Mixed_Test.14": "e49ed31fe40c6651e39ce063b52eedb0e4a6c3f2",
    "Test_Case_1.14": "6b1c65e181f21d4f52f63a3f22f13008bc1328e5",
    "Test_Case_2.14": "2ff0e29d03553460f4df4e18e742ddd59b53246c",
    "Test_Case_3.14": "5576fc647fd1199ebdc76fac798975cd0a7a2edf",
    "simple_test_case.14": "8816d2c6a8cac839a8cddd719de549bb92368291",
    "square_mesh_test.14": "b130328508df96e45e4373b38d41307235950aa7",
    "structuredMesh1.14": "8bfaa8adbac1d623fc1650c1370ba63f7a1b9884",
}


def _token() -> str | None:
    """Return GitHub token from env, or None."""
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None


def _git_blob_sha1(data: bytes) -> str:
    """Compute git blob sha1 of data."""
    blob_header = b"blob " + str(len(data)).encode() + b"\0"
    return hashlib.sha1(blob_header + data).hexdigest()


def _download(name: str, token: str) -> bytes:
    """Download mesh file from Valence registry via authenticated GitHub API.

    Returns raw bytes. Raises urllib.error.HTTPError, json.JSONDecodeError, ValueError on error.
    """
    url = (
        f"https://api.github.com/repos/{VALENCE_OWNER}/{VALENCE_REPO}/"
        f"contents/{VALENCE_PATH}/{name}"
    )
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "quadmesh-fixture-provision",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        j = json.load(resp)
    if j.get("encoding") != "base64":
        raise ValueError(f"expected base64 encoding, got {j.get('encoding')}")
    return base64.b64decode(j["content"])


def provision(
    names: list[str] | None = None, dest: Path | None = None, *, verify: bool = True
) -> dict[str, str]:
    """Provision test meshes from Valence registry.

    Parameters
    ----------
    names : list[str] | None
        Mesh filenames to provision. Defaults to all in MANIFEST.
    dest : Path | None
        Destination directory. Defaults to FIXTURE_DIR.
    verify : bool
        Verify git-blob-sha1 integrity. Defaults to True.

    Returns
    -------
    dict[str, str]
        Mapping name -> status in {"present", "fetched", "skip-no-token", "error: <msg>"}.
    """
    if names is None:
        names = list(MANIFEST)
    if dest is None:
        dest = FIXTURE_DIR

    # Honor offline mode.
    if os.environ.get("QUADMESH_NO_FETCH"):
        results = {}
        for name in names:
            local = dest / name
            results[name] = "present" if local.exists() else "skip-no-token"
        return results

    token = _token()
    results = {}

    try:
        dest.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    for name in names:
        local = dest / name
        if local.exists():
            results[name] = "present"
            continue

        if token is None:
            results[name] = "skip-no-token"
            continue

        try:
            data = _download(name, token)
            if verify and name in MANIFEST:
                got = _git_blob_sha1(data)
                if got != MANIFEST[name]:
                    raise RuntimeError(f"sha mismatch {got} != {MANIFEST[name]}")
            local.write_bytes(data)
            results[name] = "fetched"
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            OSError,
            ValueError,
            RuntimeError,
            json.JSONDecodeError,
        ) as e:
            results[name] = f"error: {type(e).__name__}: {e}"

    return results


def needed_names() -> list[str]:
    """Return list of mesh filenames in the manifest."""
    return list(MANIFEST)
