# Session 021 — 2026-06-16 (hour-03 rotation, maintenance track)

## What changed
- **#93 partial fix** — `tests/_mesh_provision.py` gains a **chilmesh.data fallback**.
  Provisioning previously returned `skip-no-token` with no Valence PAT → the
  faithfulness gate (`test_no_interior_tris.py`, parametrized incl.
  `structuredMesh1`) skipped entirely = false-green on the non-negotiable
  zero-interior-tri invariant. Now `provision()` falls back to the installed
  `chilmesh/data/` package dir for the meshes chilmesh ships byte-exact
  (`Block_O.14`, `structuredMesh1.14`), sha-verified against the pinned manifest,
  including under `QUADMESH_NO_FETCH` and with no token.
- New regression test `tests/test_mesh_provision_fallback.py` (3 tests).
- Commit `eeac3a8` on `development`, pushed. Rolling PR **#95** body updated.

## Key decisions
- **chilmesh.data is a legitimate offline fixture source.** `chilmesh/data/Block_O.14`
  and `structuredMesh1.14` are git-blob-sha1 IDENTICAL to the Valence pins
  (verified: `9a98cf04…`, `8bfaa8ad…`). Reusing them offline ≠ re-vendoring
  (cache stays gitignored; chilmesh is already a hard dep). Removes the *complete*
  false-green without needing the operator PAT.
- **#93 stays OPEN.** Only 2 of 8 pinned meshes ship with chilmesh; the other 6
  (`Test_Case_1/2/3`, `simple_test_case`, `square_mesh_test`, `Mixed_Test`) still
  need the cross-repo read PAT secret for full-coverage CI. Documented on #93.
- Overhaul slice (#82) already complete → maintenance track, top of issue queue.

## Verification
- Env: `dev_setup.sh` OK; chilmesh **1.2.2** editable from `/home/user/CHILmesh` + `quadmesh[dev]`.
- `QUADMESH_NO_FETCH=1 pytest tests/` → **93 passed / 67 skipped** (was 76/75 — fallback
  un-skips Block_O + structuredMesh1 fixture tests).
- Faithfulness gate offline: `4 passed, 17 skipped` (structuredMesh1 PASSES; was all-skip).
- `tests/test_mesh_provision_fallback.py` → 3 passed.

## Branch / PR
- `development` @ `eeac3a8`, pushed. Rolling draft PR **#95** (`development → main`), body refreshed.
- PR #94 (experimental opt-in preconditioner, `claude/*` branch) — prior session's draft, untouched.

## What comes next
- **Operator gates (unchanged):** Q#93 cross-repo Valence read PAT secret (now only blocks
  the remaining 6-mesh coverage, not the whole gate); Q#90 ENPAC ≥2-boundary-edge skew tail
  (thesis/faithful-merge deviation call); Q#46 onion hero domain (gated on ADMESH-Domains#93 `.14`).
- Research/brainstorm queue needs operator green-light: #17/#18/#21/#26/#38/#77 (#77 also blocked on CHILmesh#129).
- #76 (layer-sweep profiling on WNAT_Hagen) still needs a PAT-provisioned large fixture —
  chilmesh.data only ships up to Block_O (~5k elems), not WNAT_Hagen (98k). Could deliver a
  *preliminary* hotspot profile on Block_O offline in a future slot if WNAT remains blocked.

## Open chilmesh issues
- None newly hit. The five filed (#132/#133/#134/#138/#139) remain closed + consumed.

## Pains (→ matrix, no new request:skill per #203)
- **No Valence PAT in routine env** → large-mesh tasks (#76 WNAT, #90 ENPAC, #21 size-drift
  on real meshes) blocked offline. chilmesh.data fallback recovers small/medium fixtures only.
  Recurring; operator-PAT-gated (Q#93).
- **Haiku subagent placement nit** — inserted the new helper between two module constants
  (`VALENCE_OWNER` / `VALENCE_REPO`), splitting them. Syntactically fine, caught + fixed in
  orchestrator review. Reinforces the dispatch contract (main session verifies before commit).
- **Git proxy is single-repo** — `git ls-remote` against sibling `domattioli/Valence`/`CHILmesh`
  through the local proxy fails (`could not read Username`); only the active repo is served.
  Sibling code reachable only via on-disk clones (`/home/user/CHILmesh`), not git.
