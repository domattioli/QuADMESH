# Test mesh fixtures

`tests/fixtures/meshes/` is gitignored. Valence registry bytes are source; no
fixture mesh is vendored here.

`tests/conftest.py` runs the shared provisioner. It uses `chilmesh.registry`
and `VALENCE_TOKEN`, then checks both API hash and downloaded bytes against the
pinned SHA-256. A 401, 404, malformed reply, or mismatch fails. A 429,
transport outage, or 503 skips.

Without `VALENCE_TOKEN`, or when `chilmesh.registry` is unavailable, the
provisioner uses bundled `chilmesh.data` only when its bytes equal the pin.
Otherwise mesh-dependent tests skip with the stated reason. Fork pull requests
receive no `VALENCE_TOKEN`, so skips are expected.

```bash
VALENCE_TOKEN=<token> python scripts/fetch_fixtures.py
```

`Mixed_Test.14` was removed from Valence registry (#347) and is never pinned.

Set `QUADMESH_NO_FETCH=1` to skip the network even when a token is set; the bundled fallback rule still applies.
