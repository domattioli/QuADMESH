---
date: 2026-06-13
session: 2026-06-13T15Z-rotation
repo: domattioli/QuADMESH
severity: low
freq: recurring
issues: [48, 82, 46]
wasted_min: 8
wasted_tok: 12000
missing_skill: null
---

# Rotation 2026-06-13T15Z — T017/T018 quadmesh+ quality recovery

## Summary

Hour-15 Q rotation, overhaul track. Shipped the highest-value ungated Q slice:
**T017/T018** (Ch 4.1/4.2 layer heuristics) — deferred by the last two Q slots
as "needs thesis, unsafe to guess." Key unlock: the thesis IS in-repo
(`docs/Mattioli_Thesis.pdf`) and a **vetted faithful transcription** already
existed (`docs/algorithm_writeup.md`, cites thesis p64-70). Combined with an
empirical diagnostic, the "do not guess semantics" guard resolved safely.

Diagnosis (measure-first): the default `_quadmesh_plus_per_layer` merged the
structured-sweep `removed_edge_ids` then routed **every** remaining layer tri
individually. Instrumented: 97% of Block_O post-sweep leftovers (72% TC1) had
an unmatched neighbor → pairable into quads but sliver-recombined. That, not a
faithfulness defect, was the 0.21/0.48 collapse. Fix = insert greedy
interior-saturating pairing (reuse the already-present-but-**unwired**
`_match_faithful.match_layer_heuristic`: T1 fewest-eligible, T2 ladder,
IE/OE order) between the sweep-merge and leftover-routing loops; wire fold-seam
`flagged_vert_pairs` (was a `pass` no-op).

Quality (post-process): TC1 0.573→0.696, Block_O 0.251→0.680; raw Block_O
0.21→0.54. Zero-interior gate green; 276 pass / 98 skip (4 parity pins
re-tightened). Code edits dispatched to Haiku subagents (2); main session
diagnosed/designed/reviewed/integrated. Operator mid-session flagged the
`_faithful_per_layer` name → renamed `_quadmesh_plus_per_layer` (#46: code must
not name the method "faithful"). Caveman: honest fallback at bootstrap, real
Skill call succeeded mid-session after marketplace late-connect.

## Pain points

```yaml
pain_points:
  - pain: "T017/T018 (highest-value Q work) sat undone for 2+ slots because the task text says 'Needs thesis Ch 4 — do not guess semantics' but never says the thesis is in-repo (docs/Mattioli_Thesis.pdf) nor that a vetted faithful transcription exists (docs/algorithm_writeup.md). The guard read as 'blocked, defer to a thesis-equipped slot' when the reference was sitting in docs/ the whole time. The 06-13T03Z introspection literally wrote 'not safe to guess autonomously without the thesis.'"
    frequency: recurring
    severity: low
    evidence: "faithful-port-tasks.md T017 line: 'Needs thesis Ch 4 — do not guess semantics' with no path; thesis at docs/Mattioli_Thesis.pdf; algorithm_writeup.md §6 transcribes T1/T2 with thesis page cites. 03Z slot deferred on this basis."
    existing_skill_should_have_caught_it: "session-resume surfaces 'highest-value next work' but not the in-repo reference that unblocks it."
    missing_skill_would_have_prevented_it: "none new (#203 probation) — fix is a one-line task-text edit linking the in-repo reference. Logged as matrix row + done this session (T017 text now cites docs/Mattioli_Thesis.pdf)."
    domi_issue: null
    saved_time_estimate_min: 0
  - pain: "match_layer_heuristic (the full T1/T2/IE-OE matcher) existed in _match_faithful.py but was UNWIRED — only tests/test_faithful_pairing.py called it, never the production _quadmesh_plus_per_layer. It read as 'heuristics implemented' when grep of call sites showed it was dead relative to the default path. Cost: had to trace the two divergent code paths (full _match_tris_to_quads vs the simpler per-layer loop) to find the default path skipped the heuristics."
    frequency: recurring
    severity: low
    evidence: "grep match_layer_heuristic -> only test + def; default method=quadmesh+ runs _quadmesh_plus_per_layer which merged removed_edge_ids then route_leftover_tri, no T1/T2."
    existing_skill_should_have_caught_it: none
    missing_skill_would_have_prevented_it: "none — discipline: grep production call sites before assuming a helper is on the live path."
    domi_issue: null
    saved_time_estimate_min: 4
  - pain: "Correct branch (development) was not even present in the fresh clone — only main + the harness-injected claude/kind-pascal-0vh68n. Had to git fetch origin development + checkout before the rolling-PR #87 history was visible. Without it, a session could ship onto the wrong branch and miss 06-12's landed work."
    frequency: recurring
    severity: low
    evidence: "git branch -a at start = main + claude/kind-pascal-0vh68n only; development fetched explicitly; PR #87 head=development."
    existing_skill_should_have_caught_it: "session-resume should fetch + report the repo's real default/staging branch, not just the injected one."
    missing_skill_would_have_prevented_it: "none — CLAUDE.md precedence rule + explicit fetch handled it."
    domi_issue: null
    saved_time_estimate_min: 2
  - pain: "Caveman plugin absent at bootstrap (#168 fallback), warm-load only after marketplace late-connect mid-session. 5th+ consecutive data point; fix gated on DomI PR #274 merge (containers fork from main, onstart curls main). Not new."
    frequency: recurring
    severity: low
    evidence: "Skill 'caveman:caveman ultra' -> Unknown skill at bootstrap; succeeded ~15:1xZ after late-connect."
    existing_skill_should_have_caught_it: none
    missing_skill_would_have_prevented_it: "none — tracked DomI#268/#274."
    domi_issue: 268
    saved_time_estimate_min: 1
```

## Outcome

- Shipped `development @ 14c5b87` → rolling PR #87: T017 (greedy interior
  pairing) + T018 partial (OE-before-IE + fold-seam wiring) in
  `_quadmesh_plus_per_layer`; rename from `_faithful_per_layer`; parity pins
  re-tightened; CLAUDE.md + faithful-port-tasks.md status updated.
- 276 pass / 98 skip; faithfulness gate green; Block_O default quality +156% raw.
- #48 checklist comment posted. No DomI bug filed (bootstrap clean modulo the
  known #268 caveman warm-load).

## What comes next

- **T018 finish** — walkability edge-flip pre-pass on RE_L still falls back to
  per-tri routing on the small boundary residual; wire full `walk_isolated_tri`
  chaining if boundary quality regresses.
- **T019** — isolated-tri intentional vertex-pairing + post-match edge-swap
  fixup (CR-5, thesis p66); depends on T013+T017 (now done).
- Re-establish Block_O + WNAT_Hagen `quadmesh+` floors in
  `quality_baselines.json` at the new (higher) levels (runslow lane).
- Operator go/no-go on the broader "faithful"-as-mechanism rename
  (`_faithful_sweep.py`, `_match_faithful.py`, `test_faithful_pairing.py`).
- T9/T13/T14 stay parked on operator D1/D5.

## Matrix row (pains -> tracking, #203 probation: no new request:skill)

| pain | class | route |
|---|---|---|
| 'needs thesis' task guard never links the in-repo thesis/writeup → highest-value work deferred 2+ slots | spec-ergonomics | FIXED this session (T017 text now cites docs/Mattioli_Thesis.pdf); generalize: spec tasks citing an external reference should link the in-repo copy if present |
| full matcher helper existed but unwired from the live path (looked done) | code-discoverability | matrix only; discipline = grep production call sites before assuming a helper is live |
| staging branch (development) absent from fresh clone; only harness claude/* + main | harness | session-resume should fetch+report real staging branch (DomI lever) |
| caveman warm-load next-session-scoped | infra | DomI#268 / PR #274 |
