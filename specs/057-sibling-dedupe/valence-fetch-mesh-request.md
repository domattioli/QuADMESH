<!-- provenance: author=domattioli model=claude-sonnet-5-5 effort=medium date=2026-10-10 skill=speckit-implement repo=quadmesh session=unknown -->
# Request: fetch_mesh(name) -> Path with integrity verification

Label: `downstream-api`. This draft is not filed.

QuADMESH tests provision `.14` fixtures from `registry_data/meshes` with an authenticated GitHub contents download. They verify a pinned git-blob SHA-1 and cache the result in a gitignored folder (`quadmesh/tests/_mesh_provision.py:23-60`).

`valence_domains` resolves a mesh only from a local `base_dir` (`schema.py:382`). It computes a canonical SHA-256 `content_uid` (`schema.py:402`). It has no remote fetch.

Please add `valence_domains.fetch_mesh(name, *, cache_dir=None, token=None) -> Path`. The function should do three things:

1. Download the file from the registry when it is not available locally.
2. Verify the result against the manifest `content_uid`.
3. Raise a typed error on a mismatch or on missing access.

With this API, QuADMESH, ADMESH, and CHILmesh can drop their own copies of the fetch and hash code.
