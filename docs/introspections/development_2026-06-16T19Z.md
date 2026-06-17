---
date: 2026-06-16
session: 2026-06-16T19Z-rotation
repo: domattioli/QuADMESH
severity: low
freq: occasional
issues: [48, 93]
wasted_min: 2
wasted_tok: 1500
missing_skill: null
---

# Rotation 2026-06-16T19Z — doc-accuracy test-count drift fix (maintenance)

## Summary

Hour-19 Q rotation slot (UTC 19 → QuADMESH per roster). Q spec-048 slice
complete (#82 redundancy convergence closed; T3/T5/T7 + #46 method removal +
T017/T018 prior slots). No open overhaul slice → maintenance track.

Bootstrap: health HEALTHY; caveman `Unknown skill` at start (marketplace
late-connect, DomI#268) → emulated from CLAUDE.md (no re-attempt success this
slot — MCP servers connected but caveman plugin not among them). `.domi-pin`
already in sync (`a9b240f` == DomI `main` HEAD via sibling clone
`/home/user/DomI`; manifest `8e928b8`) — no resync. Harness injected
`claude/sharp-cori-rzn9a5`; CLAUDE.md precedence → `development` (tracked from
`origin/development`, == remote at start).

## Shipped

- `f6651eb` (`development`, rolling PR #95) — corrected stale test-count drift.
  README claimed `# 133 tests`, CLAUDE.md `# 151 collected`; ground truth =
  **97 passed / 72 skipped = 169 collected** offline. Both → 169, plus the
  offline run/skip split and a pointer to the Valence-PAT provisioning note so a
  fresh-clone contributor isn't surprised by mesh-dependent skips (#93 theme).
  Docs-only.

## Verify-don't-dup

- Scanned tests for stale skip/xfail/false-green markers (the recurring sibling
  pain: ADMESH hour-17 docstring-skip, QuADMESH #93). None found — the two
  skips present (`test_parity` awaiting MATLAB counts; `simple_test_case.14
  missing`) are legitimate, not stale-version gates.
- Confirmed README "Status & Roadmap" Now/Next/Future + Performance/quality
  numbers (Test_Case_1 0.696, Block_O 0.680; ENPAC perf table) consistent with
  CLAUDE.md and #90. No drift there.

## What comes next

- Operator gates (unchanged): #93 cross-repo Valence read PAT (other 6
  fixtures' CI coverage); #90 ENPAC ≥2-boundary-edge skew tail (deviation call);
  #46 onion hero (gated on ADMESH-Domains#93). Research/brainstorm queue
  (#17/#18/#21/#26/#38/#76/#77/#97/#98) needs operator green-light. #98
  boundary-layer-only conditioning is the natural next code frontier once
  green-lit.

## Pains (→ matrix, no new request:skill per #203)

```yaml
pain_points:
  - pain: "Doc test-counts (README, CLAUDE.md) drift silently — no test asserts the documented count matches collected. Caught only by a manual `pytest --collect-only` during a maintenance sweep. Low cost individually but recurs as the suite grows; both docs were two different stale numbers (133, 151) vs actual 169."
    repo: QuADMESH
    severity: low
    frequency: occasional
    domi_issue: ""
    saved_min: 0
    wasted_tok: 0
    missing_skill: ""
  - pain: "caveman plugin still not loaded at bootstrap in routine env (DomI#268) — `Unknown skill` every slot, emulation-from-CLAUDE.md is the steady state. Container-baked plugin is the operator fix; nothing autonomous to do."
    repo: QuADMESH
    severity: low
    frequency: recurring
    domi_issue: "DomI#268"
    saved_min: 0
    wasted_tok: 0
    missing_skill: ""
```
