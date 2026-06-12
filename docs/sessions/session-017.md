# Session 017 — 2026-06-12 rotation h21

**Branch:** `development` (harness assigned `claude/gifted-carson-my1i10` → switched per `branching.md`).
**Model:** claude-fable-5 (+ 3 haiku subagents per coding-dispatch rule).
**Issue worked:** #46 operator directive (method removal); #85 (domi-sync).
**PR:** #87 — rolling `development → main` draft (description updated, commit `7bc9d40`).

## What changed

- **#46 directive (2026-06-11, was unaddressed)** — `"faithful"` + `"matching"`
  tri2quad method values removed entirely. `method="quadmesh+"` = sole +
  default (`"layered"` mechanism alias kept); removed values raise
  `ValueError`. `run_pipeline` default updated to match; CT(Q) default pin
  `matching`→`quadmesh+` same commit.
- **Bug fix** — layered sweep mutated the caller's mesh in place
  (`domain.points[v_a]=mid`, connectivity zeroing, point growth via
  `flush_points_to_domain`). Exposed by the default flip: 10 suite failures,
  all order-dependent (session-scoped fixtures), all passing in isolation.
  Fix: snapshot/restore `domain.points` + `connectivity_list` around
  `_faithful_per_layer` (try/finally). New `tests/test_input_immutability.py`
  pins the contract.
- **Baselines re-captured under quadmesh+** — `test_parity.py` EXPECTED:
  TC1 n_out 1083→1352 mean_q 0.739→0.574; Block_O n_out 2349→3851 mean_q
  0.744→0.251. `quality_baselines.json`: `|matching|` rows dropped,
  `|layered|` keys → `|quadmesh+|`. Block_O/WNAT quadmesh+ floors to be
  re-established (noted in JSON `_comment`).
- **CLAUDE.md** — Faithfulness-invariant Status + naming note updated
  (removal recorded; "must not be made default" guard superseded by
  operator directive; T017/T018 still the quality-recovery path).
- `.domi-pin` 04f5d53 → 3e46639 (sibling-clone re-sync; #85 closed).

## Key decisions

- Speckit skipped: operator directive was unambiguous + single-purpose;
  edits span 8 files but one logical change (removal + its fallout).
- Mutation fixed at API level (snapshot/restore), NOT by de-scoping session
  fixtures — downstream callers (MADMESHing) share the same hazard.
- Quality drop accepted knowingly: operator's "remove entirely" supersedes
  the prior don't-make-default guard; flagged in PR body + #46 comment.

## Validation

`pytest tests/` → **271 passed, 98 skipped** (was 268/102; delta = removed
deprecation test, +2 removed-method ValueError params, +2 immutability
tests, −4 dropped matching baseline params). Faithfulness gate
`test_no_interior_tris.py` green. py_compile + JSON lint clean.

## What comes next

- **T017 / T018** — now directly user-visible: default-path mean quality is
  0.574 (TC1) / 0.251 (Block_O) until the Ch 4 heuristics land. Highest-value
  next Q work.
- Re-establish Block_O + WNAT_Hagen `quadmesh+` rows in
  `quality_baselines.json` (runslow lane for WNAT).
- #46 hero image still blocked on ADMESH-Domains#93.
- #76 (WNAT profiling) unclaimed; #21 (size-function drift) `status: ready`.
- T9/T10 parked on operator D1.

## Open chilmesh issues

Non-blocking: #134 (superseded by #204), #139 (smoother perf). All
Q-blocking asks shipped.
