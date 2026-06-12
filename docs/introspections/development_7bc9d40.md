---
date: 2026-06-12
session: 2026-06-12T21Z-rotation
repo: domattioli/QuADMESH
severity: medium
freq: once
issues: [46, 85, 82, 48]
wasted_min: 5
wasted_tok: 2000
missing_skill: null
---

# Rotation 2026-06-12T21Z — #46 method removal (quadmesh+ sole/default)

## Summary

Hour-21 Q rotation slot, maintenance track (Q spec-048 slice complete as of
15Z). Picked up unaddressed operator directive on #46 (2026-06-11): removed
`"faithful"` + `"matching"` tri2quad methods entirely; `"quadmesh+"` now sole
+ default (`"layered"` alias kept). Default flip exposed a real bug — layered
sweep mutated the caller's mesh in place (coords, connectivity, point growth)
→ snapshot/restore fix + `test_input_immutability.py` regression test. Parity
pins re-captured under quadmesh+ (TC1 0.739→0.574, Block_O 0.744→0.251 —
documented WIP gap until T017/T018). Pin re-synced 04f5d53→3e46639 (#85
closed). Gate 271p/98s green incl. faithfulness gate. 3 Haiku subagents;
Fable 5 orchestration/review (caught CLAUDE.md naming-note contradiction the
subagent left, and the bad commit split). Caveman emulated (plugin absent at
bootstrap — #268 fix still gated on DomI PR #274 merge; third data point).

## Pain points

```yaml
pain_points:
  - pain: "Parallel Bash tool calls share one persistent cwd — update_pin.sh ran in the CHILmesh sibling clone instead of QuADMesh, writing CHILmesh/.domi-pin (cross-repo write, reverted). Same class as 'Shell cwd was reset' surprises in prior sessions."
    frequency: recurring
    severity: medium
    evidence: "This session: pin write landed in /home/user/CHILmesh; caught by git status check, reverted via checkout."
    existing_skill_should_have_caught_it: none
    missing_skill_would_have_prevented_it: "none — discipline fix: never combine cd-dependent parallel calls; always absolute-path or re-cd per call."
    domi_issue: null
    saved_time_estimate_min: 4
  - pain: "Session-scoped pytest fixtures + an API that mutates its input hid the mutation bug for the entire life of the layered path; it only surfaced when the default flipped and 10 unrelated tests failed in suite-order-dependent ways (pass in isolation)."
    frequency: once
    severity: medium
    evidence: "tests/conftest.py scope='session' CHILmesh fixtures; _tri_removal.py domain.points[v_a]=mid / connectivity zeroing / flush vstack."
    existing_skill_should_have_caught_it: none
    missing_skill_would_have_prevented_it: "none — fixed at API level (snapshot/restore) + immutability regression test now pins the contract."
    domi_issue: null
    saved_time_estimate_min: 0
  - pain: "Caveman plugin absent at bootstrap again (#168 fallback line emitted); DomI#268 warm-load fix inert until DomI rolling PR #274 merges (fix on development, containers fork main). Third consecutive data point."
    frequency: recurring
    severity: low
    evidence: "Skill call 'caveman:caveman ultra' → Unknown skill at 21:04Z."
    existing_skill_should_have_caught_it: none
    missing_skill_would_have_prevented_it: "none — already tracked on DomI#268; unblock = operator merging DomI#274."
    domi_issue: 268
    saved_time_estimate_min: 1
```

## Outcome

- `7bc9d40` on `development` → rolling PR #87 (description updated with slice).
- #85 closed (pin 3e46639); #46 + #82 + MADMESHing#48 updated.
- No new DomI issues filed (zero new bugs hit; #268 already tracked).
- No new `request: skill` (#203 probation respected).
