---
date: 2026-06-13
session: 2026-06-13T09Z-rotation
repo: domattioli/QuADMESH
severity: low
freq: one-off
issues: [88, 82, 48]
wasted_min: 3
wasted_tok: 2500
missing_skill: null
---

# Rotation 2026-06-13T09Z — #88 truss_smoother arity bug (maintenance track)

## Summary

Hour-09 Q rotation slot. Q spec-048 slice (T3/T5/T7) already complete (06-12);
`.domi-pin` current at DomI `main@3e46639`, no drift. No open overhaul slice →
maintenance track = top of issue queue. Top item: **#88** (`type: bug`, filed
this morning 03:50Z) — `truss_smoother` mis-selects padded boundary tris as
quads because `len(elem) == 4` is always true on a rectangular N×4
`connectivity_list`.

Verified the actual padding convention before trusting the issue's suggested
fix: the issue body's prose said padded tri `= [v0,v1,v2,v0]`, but
`tri2quad.py:1045` pads as `[v0,v1,v2,v2]` (repeats the **last** vertex), so the
canonical test `row[2] != row[3]` (`_is_quad_row`, `doublet_collapse.py:22`) is
correct and the prose was a typo. Had the prose been taken literally the "fix"
would have left the bug live.

Fix dispatched to a Haiku subagent (CLAUDE.md coding-dispatch): extracted a pure
`_quad_rows()` helper reusing `_is_quad_row` (removed what would have been a 4th
parallel copy of the arity test — same cross-repo dedup spirit as #48), plus 5
regression unit tests. Fable 5 main session planned/reviewed/integrated.

## Pain points

```yaml
pain_points:
  - pain: "Issue #88's body gave the padded-tri layout as [v0,v1,v2,v0] in prose but the suggested one-line fix (row[2]!=row[3]) implied [v0,v1,v2,v2]. The two are mutually inconsistent; applying the prose literally would have kept the bug. Only resolvable by grepping the actual padding site (tri2quad.py:1045) + the existing _is_quad_row convention."
    frequency: one-off
    severity: low
    evidence: "Issue body: 'padded triangles ([v0,v1,v2,v0])'. Code: tris_padded = np.hstack([surviving_tris, surviving_tris[:, [2]]]) -> [v0,v1,v2,v2]."
    existing_skill_should_have_caught_it: "none — this is normal verify-before-fix diligence; a fix taken on faith from the issue text would have regressed."
    missing_skill_would_have_prevented_it: "none — #203 probation; discipline (verify the convention in-repo before trusting an issue's prose) is the mitigation."
    domi_issue: null
    saved_time_estimate_min: 2
  - pain: "Caveman plugin absent at bootstrap again (#168 SKILL.md fallback line emitted). 5th consecutive rotation data point. DomI main@3e46639 carries the #268 warm-load fix but warm-load fires at session START via the routine onstart hook and is not retroactive for a session whose onstart env did not run it. Not a new code bug (fix is env/onstart-scoped); no #268 comment."
    frequency: recurring
    severity: low
    evidence: "Skill 'caveman:caveman ultra' -> Unknown skill at bootstrap; pin already 3e46639 (post-#274)."
    existing_skill_should_have_caught_it: none
    missing_skill_would_have_prevented_it: "none — tracked DomI#268; operator should verify warm-load actually fires in the rotation onstart env-config (not a DomI code gap)."
    domi_issue: 268
    saved_time_estimate_min: 1
  - pain: "MADMESHing#48 get_comments (now 30+ comments) again exceeded the MCP single-response token cap (60,140 chars); had to dump to file + python-parse to read the map of record. Recurring — same pain logged by the 03Z slot; the coordination thread is the worst offender and grows every rotation."
    frequency: recurring
    severity: low
    evidence: "issue_read get_comments -> 60,140 chars across 1 line, truncated to tool-results file."
    existing_skill_should_have_caught_it: none
    missing_skill_would_have_prevented_it: "none — page or jq the dumped file. Structural: #48 is unboundedly long; a periodic digest-and-archive of the thread would cap the read cost."
    domi_issue: null
    saved_time_estimate_min: 1
```

## Outcome

- Shipped: `truss_smoother` arity fix (`_quad_rows()` + 5 regression tests) —
  `c467ea6`, pushed to `development`, carried by rolling PR #87. Faithfulness
  gate `tests/test_no_interior_tris.py` green; full suite 276 passed / 98
  skipped (zero regressions).
- Issue hygiene: #88 fix comment (auto-closes on PR #87 merge); #48 checklist
  comment (Q slice complete + this maintenance ship).
- No DomI bug filed (bootstrap clean, pin synced). No new `request: skill`
  (#203 probation) — pains logged as matrix rows above.
