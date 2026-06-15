# Test mesh fixtures

The `.14` ADCIRC test meshes are **not vendored in this repo**. They were
removed in commit `4dc5eea` ("Delete tests/fixtures directory — meshes can be
found on domattioli/Valence") to keep the repo small; the authoritative copies
live in the [`domattioli/Valence`](https://github.com/domattioli/Valence)
registry under `registry_data/meshes/`.

`tests/fixtures/meshes/` is **gitignored** and provisioned on demand.

## How provisioning works

`tests/conftest.py` calls `tests/_mesh_provision.py` at collection time. For
each mesh in `MANIFEST` it:

1. uses the existing local copy if present, else
2. downloads it from the Valence registry via the authenticated GitHub
   contents API, then
3. integrity-checks the bytes against the pinned git-blob-sha1 before caching
   it into `tests/fixtures/meshes/`.

No token, offline, or `QUADMESH_NO_FETCH=1` → provisioning is a no-op and the
mesh-dependent tests **skip** (exactly the pre-provisioning behaviour).

## Requirements

A token with **cross-repo read access on `domattioli/Valence`** (which is
private) exported as `GITHUB_TOKEN` or `GH_TOKEN`.

- **Local dev:** a personal access token with `repo` (read) scope.
- **CI:** the default `GITHUB_TOKEN` is scoped to the running repo only and
  **cannot** read `domattioli/Valence`. A dedicated cross-repo read PAT must be
  added as a repository secret and exported as `GITHUB_TOKEN` for the test job.
  Until that secret exists, the faithfulness gate (`test_no_interior_tris.py`)
  and other mesh-dependent tests **skip silently** in CI — see the tracking
  issue.

## Manual provisioning

```bash
GITHUB_TOKEN=<pat> python scripts/fetch_fixtures.py
```

Prints one `name: status` line per mesh (`present` / `fetched` /
`skip-no-token` / `error: …`).
