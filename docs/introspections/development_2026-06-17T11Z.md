---
date: 2026-06-17
session: 2026-06-17T11Z-rotation
repo: domattioli/QuADMESH
severity: low
freq: occasional
issues: [48, 93, 46]
wasted_min: 1
wasted_tok: 1000
missing_skill: null
---

# Rotation 2026-06-17T11Z — faithfulness-test false-green fix (maintenance)

## Summary

Hour-11 Q rotation slot (UTC 11 → QuADMESH per roster). Q #48 slice complete
(#82 redundancy convergence closed prior slots). No open overhaul slice →
maintenance + false-green hygiene track.

Bootstrap: health HEALTHY; caveman `Unknown skill` at start (marketplace
late-connect, DomI#268) → emulated from CLAUDE.md. `.domi-pin` already in sync
on `development` (`a9b240f` == DomI `main` HEAD via sibling clone
`/home/user/DomI`; manifest `8e928b8`) — no resync. Harness injected
`claude/sharp-cori-u5kuq7`; CLAUDE.md precedence → `development`.

## Shipped

- `bb5a404` (`development`, rolling PR #95) — **fixed a #93-class false-green**.
  Three tests in `tests/test_no_interior_tris.py` hardcoded `Test_Case_1.14`,
  a Valence-only mesh not provisionable offline or in CI, so they **skipped
  silently everywhere CI can reach**: `test_tri2quad_conforming_and_valid`,
  `test_removed_methods_raise[faithful/matching]` (verifies the non-negotiable
  `"faithful"`/`"matching"` method removal, #46), `test_quadmesh_plus_alias_no_warn`.
  Repointed at the offline-provisionable fixtures (`structuredMesh1.14` /
  `Block_O.14` via chilmesh.data fallback) through a `_first_available` helper;
  still skips gracefully when nothing provisioned. Offline suite 97→101 passed,
  72→68 skipped (net +4 real CI assertions), zero regressions. README +
  CLAUDE.md offline run/skip split updated.
- Coding dispatched to Haiku subagent; orchestrator reviewed diff + verified the
  4 tests flip SKIPPED→PASSED before commit (coding-dispatch policy).

## Verify-don't-dup

- Whole offline suite run first (`QUADMESH_NO_FETCH=1 pytest tests/` → 97/72
  baseline) before touching anything. The fixed tests were the *only* offline
  silent-skips that assert a hard invariant; the remaining 68 skips are
  genuinely Valence-mesh-dependent (parity / multi-mesh parametrizations), not
  stale gates.
- Confirmed `.domi-pin` current rather than re-syncing blindly (the start-of-
  session `.domi-pin` read showed the *stale harness branch* value 69b073d;
  `development` carries the prior slot's pin-sync to a9b240f).

## What comes next

- Operator gates (unchanged): #93 cross-repo Valence read PAT (un-skips the
  other 6 fixtures' CI coverage — would let the *parametrized* tri2quad gates
  run on Test_Case_*/simple/square in CI too, not just the 2 chilmesh.data
  meshes); #90 ENPAC ≥2-boundary-edge skew tail (deviation call); #46 onion hero
  (gated on ADMESH-Domains#93). Research/brainstorm queue
  (#17/#18/#21/#26/#38/#76/#77/#97/#98) needs operator green-light. #98
  boundary-layer-only conditioning = natural next code frontier once green-lit.

## Pains (→ matrix, no new request:skill per #203)

```yaml
pain_points:
  - pain: "Faithfulness/invariant tests hardcoded a single Valence-only fixture (Test_Case_1.14), so the assertions that the removed methods raise + the canonical alias does not warn skipped silently in every CI/offline run — green while testing nothing. Same false-green class as #93 but on a *different* axis (hardcoded fixture vs blanket skip-on-missing). A lint that flags `pytest.skip` paths gating a hard invariant, or a 'at least one offline fixture must exercise each invariant test' rule, would catch this category instead of a human spotting it in a verbose -v run."
    repo: QuADMESH
    severity: low
    frequency: occasional
    domi_issue: ""
    saved_min: 0
    wasted_tok: 0
    missing_skill: ""
  - pain: "caveman plugin still not loaded at bootstrap in routine env (DomI#268) — `Unknown skill` every slot; emulation-from-CLAUDE.md is steady state. Container-baked plugin is the operator fix; nothing autonomous to do."
    repo: QuADMESH
    severity: low
    frequency: recurring
    domi_issue: "DomI#268"
    saved_min: 0
    wasted_tok: 0
    missing_skill: ""
```
