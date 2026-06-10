<!-- Session handoff + corpus entry. Caveman style. introspect@DomI v1.3. -->

# Session Handoff — QuADMesh · development_784efe6 · 2026-06-10

**Task:** #21 — does tri2quad + smoothing drift edge lengths from size function?
**Phase:** investigation/measurement
**Progress:** 100% of acceptance path (a) — bound measured + documented; per-layer breakdown not done (issue left open)
**Branch:** development
**Duration:** ~45 min active (long resume gap mid-session)
**Tool failures:** 1 (first smoke run killed by timeout — hang, root-caused below)
**Outcome:** code shipped (`scripts/size_drift_report.py`, 784efe6) + measured report on #21

## Pre-flight

- branch_policy_conflict: caught_and_resolved  <!-- system prompt named claude/awesome-johnson-385g5c; CLAUDE.md → development -->
- mcp_scope_gap: no
- label_scheme_mismatch: no

## What worked (top 3, with evidence)

1. Stage-by-stage faulthandler diagnosis nailed the hang in one run: `_skeletonize` (CHILmesh.py:1173) inside CHILmesh ctor at tri2quad.py:1059. (dump_traceback_later trace)
2. Root cause = sibling `../CHILmesh` checkout on stale harness branch `claude/tender-gates-385g5c` — #203 fix only on `development`. `git checkout -B development origin/development` → pipeline runs. (0.1s tri2quad after switch)
3. Haiku subagent one-shot the 228-line measurement script per coding-dispatch rule; compiled + correct on first review. (784efe6)

## What didn't (top 3, with evidence)

1. First smoke run burned 300s timeout before diagnosis — should have checked sibling-dep branch immediately, given #76 thread had flagged the exact same hang symptom one day earlier. (exit 143)
2. `dev_setup.sh` installs chilmesh from `../CHILmesh` at whatever branch the harness left it — silently stale dep. (root cause of 1)
3. n/a

## Recurring frictions (from local corpus)

- DomI contract plugins not installed mid-session (introspect/sync) — 2+ prior sessions; inline-script fallback used again
- stale sibling-dep branch hang — second consecutive session hitting CHILmesh-branch-related #203 symptom

## Pain → skill table

| Pain | Severity | DomI issue | Saved-min/session |
|---|---|---|---|
| sibling editable-dep checkout on stale harness branch → hang | med | none yet — dev_setup.sh could pin/checkout dep branch | ~10 |
| introspect plugin not loaded → inline script | low | #114 | ~2 |

## Pain corpus (machine-readable)

```yaml
session_id: development_784efe6
repo: QuADMesh
branch: development
date: 2026-06-10
duration_min: 45
pains:
  - pain: "sibling ../CHILmesh editable dep on stale harness branch -> _skeletonize hang; dev_setup.sh does not pin dep branch"
    severity: med
    skill_candidate: "dev_setup.sh checkout development on dep, or ensure-test-venv extension"
  - pain: "DomI contract plugins not installed mid-session (introspect/sync/request-from-domi)"
    severity: low
    skill_candidate: "#114 declarative settings.json enable"
```

## Next steps

- #21: operator decides close (acceptance (a) met, bound p95 ≤ 1.55, frac-in-band ≥ 0.977) or asks for per-skeleton-layer breakdown.
- Optional: feed `h_field()` output as `truss_fh` to `post_process_routine(truss_smooth=True)` if tail outliers (max 4–7× h) ever matter.
- T017/T018 still pending before `method="quadmesh+"` default flip.
- #76 fruit #1 implementation now unblocked downstream (CHILmesh #204 ctor flags landed on dev, `bd6d9b9`).

## Open questions

- Should `scripts/dev_setup.sh` force `../CHILmesh` onto `development`? (touches sibling repo state — operator call)
