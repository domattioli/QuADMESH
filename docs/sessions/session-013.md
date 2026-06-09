# Session 013 — branch-rule doc fix + file layered-path IndexError (#81)

**Date:** 2026-06-06
**Branch:** `development`
**PR:** [#80](https://github.com/domattioli/QuADMESH/pull/80) (rolling, draft) — updated, head `c1bd0b9`
**Model:** claude-opus-4-8
**Duration:** ~15 min
**Outcome:** complete (doc + triage; no code shipped)

## Pre-flight

- branch_policy_conflict: caught_and_resolved (harness injected `claude/lucid-brown-DY07t`; switched to `development` per DomI `branching.md` + PR#80 rolling head; `daily-maintenance`/`development` reconciled — see below)
- mcp_scope_gap: no
- label_scheme_mismatch: no (`type: bug`, `priority: normal` exist)
- env: `bash scripts/dev_setup.sh` exit 0 (venv + editable chilmesh + quadmesh[dev])

## What changed

| File | Change | Commit |
|---|---|---|
| `CLAUDE.md` | Branch rule `daily-maintenance` → `development`; `daily-maintenance` added to historical/deprecated list; cite DomI `branching.md` (PR → main only) | `c1bd0b9` |

## Work loop

Picked from 9 open issues. `status: ready` = #46, #21. #46 (onion hero domain) **filtered out — blocked on ADMESH-Domains#93** (the `.14` generator). #76 profiling and #21 size-function investigation both need a full layered/`matching` run; layered path has the IndexError + >70s hang (below), so high-risk at low effort.

Shipped the two safe, in-budget handoff items instead:

1. **#6 (handoff) — branch-rule doc.** `CLAUDE.md` said `daily-maintenance`, which does not exist on the remote; `development` does (PR#80 head). Corrected to match enforced DomI branching policy.
2. **#1 (handoff) — filed [#81](https://github.com/domattioli/QuADMESH/issues/81).** Root-caused the WIP layered-path `IndexError` at `_tri_removal.py:194` (`_ccw_tri`): `_insert_boundary_tri_midpoint` (`_tri_removal.py:155-158`) appends the boundary midpoint to the **working** mesh only (`work.add_point`), deliberately *not* growing `domain.points`. But `_ccw_tri(tri, points=domain.points)` later indexes that `work`-only `np_id` into `domain.points` → OOB (`index 5 / size 5`). Fix = pick one point-store ownership model and apply consistently (grow `domain.points`, or read coords from the working array everywhere).

## Validation

Doc-only commit — no test run required. `dev_setup.sh` green confirms the gate is runnable for the next session that touches code.

## Open / next steps

1. [ ] **#81** — fix the layered-path IndexError (`_tri_removal.py:194`). Blocked-by: the hang below makes validation hard; add the timeout guard first.
2. [ ] **`test_faithful_invariants.py` + `test_faithful_pairing.py` hang >70s** — still unfiled as its own issue; needs a `@pytest.mark.timeout` guard or the underlying fix. Consider filing next session.
3. [ ] **#76** (profiling) — needs a non-crashing layered or matching run; do on `matching` path or after #81.
4. [ ] **#21** (size-function divergence) — status: ready; needs pipeline run on a fixture with recoverable `h`.
5. [ ] **#46** (onion domain) — stays blocked until ADMESH-Domains#93 ships the `.14`.

## Context to remember

- `development` is canonical (PR#80, DomI `branching.md`). `daily-maintenance` deprecated; never existed on this remote. Ignore harness-injected `claude/*` branch names.
- Layered path (`method="layered"`, alias `"faithful"`) WIP: T017/T018 unimplemented + IndexError (#81) + hang. Do NOT make default. `method="matching"` is the safe default.
- `dev_setup.sh` → `. .venv/bin/activate` → `pytest tests/`.

## Files to review on resume

- `src/quadmesh/_tri_removal.py:155-199` — the point-store ownership bug (#81).
- `docs/sessions/session-012.md` — prior session context.
