---
date: 2026-06-13
session: 2026-06-13T03Z-rotation
repo: domattioli/QuADMESH
severity: low
freq: recurring
issues: [48, 76, 82, 46]
wasted_min: 6
wasted_tok: 3000
missing_skill: null
---

# Rotation 2026-06-13T03Z — spec-001 reconciliation (post-#46 + src-layout)

## Summary

Hour-03 Q rotation slot, maintenance track (Q spec-048 slice complete as of
06-12 21Z; pin in-sync at DomI `3e46639`, no drift). No unblocked + safe code
slice remained: T017/T018 (the handoff's "highest-value next work", quality
recovery from the 0.574/0.251 post-#46 default baseline) is a faithful port of
thesis Ch 4 heuristics — not safe to guess autonomously without the thesis,
faithfulness invariant is non-negotiable. Highest-leverage safe deliverable:
reconcile `specs/001-matlab-to-python-port/faithful-port-tasks.md`, which had
gone stale on two landed changes and was sitting directly in front of T017/T018
as friction. Fixed the load-bearing falsehoods (`method="faithful"` branch /
"keep matching fallback" — both removed #46, now `ValueError`; `python/` paths
— moved to `src/` layout in spec-003; T020 mechanism `_faithful_per_layer`
already landed; T036 default-flip done early by #46) + a global reconciliation
banner. `279cc2a` → rolling PR #87. Also corrected #76's stale `method="faithful"`
profiling snippet + flagged the 98k-WNAT CI-cost trap. Docs-only; no code, so
no Haiku dispatch; Fable 5 main session throughout. Caveman emulated (plugin
absent at bootstrap — 4th consecutive; see pains).

## Pain points

```yaml
pain_points:
  - pain: "A landed structural change (spec-003 root-reorg python/->src/) and a landed API change (#46 method removal) left specs/001 tasks.md stale, and the staleness sat exactly in front of the next-highest-value work (T017/T018). It was only discoverable by grepping for the removed method names + dead paths — nothing flags a spec task that references a method= value that now raises ValueError or a path that no longer exists."
    frequency: recurring
    severity: low
    evidence: "faithful-port-tasks.md T020/T035/T036 said method='faithful'/'matching' (removed #46); T001-T036 used python/ paths (reorged 2026-05-24). Grep for (faithful|matching) across *.md + the src tree was the only way to surface it."
    existing_skill_should_have_caught_it: "check-done (dedup) does not cover spec-vs-code drift; skill-review audits skills not repo specs."
    missing_skill_would_have_prevented_it: "a spec-drift linter (tasks referencing removed API tokens / nonexistent paths) — but #203 probation: no new request:skill. Logged as matrix row instead."
    domi_issue: null
    saved_time_estimate_min: 3
  - pain: "SDK harness injected branch claude/kind-pascal-mntrt7 as session default; its .domi-pin was stale (69fdeb7) vs development (3e46639), giving a momentary false drift signal until checkout development. Same harness-injection pattern documented across CHILmesh/DomI; precedence rule (repo CLAUDE.md says work on development) caught it."
    frequency: recurring
    severity: low
    evidence: "git rev-parse at start = claude/kind-pascal-mntrt7; .domi-pin sha 69fdeb7; development .domi-pin sha 3e46639 (current)."
    existing_skill_should_have_caught_it: "session-resume surfaces branch policy but the stale-branch pin readout still misleads for one step."
    missing_skill_would_have_prevented_it: "none — discipline: checkout development before reading .domi-pin."
    domi_issue: null
    saved_time_estimate_min: 1
  - pain: "Caveman plugin absent at bootstrap again (#168 SKILL.md fallback). DomI 3e46639 already includes the #268/#274 warm-load fix, but warm-load installs the plugin at session START via the routine onstart hook — it is not retroactive, so a session whose onstart did not warm-load still starts bare. 4th consecutive data point; not a new bug (fix is next-session-scoped), so no #268 comment."
    frequency: recurring
    severity: low
    evidence: "Skill 'caveman:caveman ultra' -> Unknown skill at 03:0xZ; pin already at 3e46639 (post-#274)."
    existing_skill_should_have_caught_it: none
    missing_skill_would_have_prevented_it: "none — tracked DomI#268; verify warm-load actually fires in the rotation onstart env (operator env-config check, not DomI code)."
    domi_issue: 268
    saved_time_estimate_min: 1
  - pain: "MADMESHing#48 get_comments (35 comments) exceeded the MCP single-response token cap; had to dump to file + python-parse to read the thread. Recurring for long coordination threads — the map of record is the worst offender."
    frequency: recurring
    severity: low
    evidence: "issue_read get_comments returned 69,863 chars -> truncated to file."
    existing_skill_should_have_caught_it: none
    missing_skill_would_have_prevented_it: "none — read with perPage paging or jq the dumped file."
    domi_issue: null
    saved_time_estimate_min: 1
```

## Outcome

- Shipped: `specs/001-matlab-to-python-port/faithful-port-tasks.md` reconciled
  (banner + T001/T017/T018/T020/T035/T036 + M2 quality comparator) — `279cc2a`,
  pushed to `development`, carried by rolling PR #87. Docs-only; faithfulness
  invariant (`tests/test_no_interior_tris.py`) untouched.
- Issue hygiene: #76 stale `method="faithful"` snippet corrected + WNAT CI-cost
  caveat; #48 checklist comment posted.
- No DomI bug filed (bootstrap clean, pin synced).

## What comes next

- **T017/T018** (Ch 4 interior IE-before-OE + boundary OE-before-IE/walkability
  heuristics) — now spec-accurate + clearly marked highest-value. Needs thesis
  Ch 4 (p64-66, p70); reserve for a thesis-equipped slot. Recovers default-path
  quality from 0.574 (TC1) / 0.251 (Block_O).
- Re-establish Block_O + WNAT_Hagen `quadmesh+` floors in
  `quality_baselines.json` (runslow lane — keep off default CI per #76 caveat).
- #46 hero image still blocked on ADMESH-Domains#93.
- #82 Q-dedup (T5/T7) complete — candidate to close once operator confirms.

## Matrix row (pains -> tracking, #203 probation: no new request:skill)

| pain | class | route |
|---|---|---|
| spec-vs-code drift (removed API tokens / dead paths in spec tasks) | tooling-gap | matrix row only; revisit if recurs across repos -> then propose via verify-plan/skill-review extension, not a new skill |
| stale-branch .domi-pin false signal | harness | known; precedence rule handles |
| caveman warm-load next-session-scoped | infra | DomI#268 (verify onstart fires) |
| long coord-thread get_comments truncation | mcp-ergonomics | page or jq dumped file |
