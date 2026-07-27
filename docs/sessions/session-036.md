# Session 036 — 2026-07-27 (rotation hour-16)

## What changed
- **#97 CLOSED — pairing-leftover investigation converged** (`e201568`,
  development; rolling PR #115 rolled). Consolidated the five-session #97
  investigation into a single durable close-out section in
  `docs/benchmarks/layer-matching-bound.md` (§"#97 investigation status —
  converged"): the full "Proposed next steps" checklist with per-item
  disposition, the descriptive verdict (walk-start not a lever; leftovers
  multifactorial) from the PR #96 Monte-Carlo study, and the prescriptive
  verdict (no within-faithful pairing lever exists). Posted a nested-notes
  disposition comment on #97 and closed it as completed.

## Key decisions / findings
- **The #97 research question is comprehensively answered on both axes.**
  Descriptive: the per-layer walk-start vertex is not a lever (5,532 ± 11
  leftovers over 200 starts; corner start 5,509 already below the mean); routing
  is multifactorial (max |ρ| = 0.115). Prescriptive: the ~86% headroom above the
  every-other rule is augmenting-path-specific (Blossom, `method="matching"`,
  removed #46); every within-faithful greedy tested regresses (~2× on real ADCIRC
  meshes) or ties. Realistic within-faithful headroom ≈ zero.
- **The one unchecked box (1,000-run p = 1 vs p ≈ 0.99 split) is a non-lever
  refinement,** not a gate on closure — it sharpens the descriptive MC tail only
  and cannot create a lever the matching-bound + greedy experiments already ruled
  out. Recommended in the close comment that it be spun out as its own narrow
  issue if the split is ever independently needed.
- **The pairing-quality family (#17 / #18 / #26 / #77) is now closed to
  within-faithful pairing changes.** The single live lever for the #90
  boundary-quality tail is geometric (tangential boundary slide / geometric
  acceptance on point positions), not connectivity/pairing — consistent with the
  #98 negative boundary-connectivity result. This retires the pairing-research
  thread the #116 zoom-out flagged as recurring scope drift.

## Verification
- Docs-only slice — no product / locked-module / faithfulness-invariant change.
  The numbers cited in the new section are from prior sessions' already-committed
  experiment JSON (`experiments/layer_matching_bound/results/*.json`) + benchmark
  tables, unchanged; nothing re-measured. Faithfulness gate untouched.
- DomI pin `c430fc2` == remote DomI `origin/main` HEAD (✓ synced at session start)
  — no bump. (Note: the session-035 `check_pin.sh` HARD-STOP false positive did
  NOT recur this session — startup reported "✓ DomI pin synced".)

## What comes next
- **#90 geometric lever** remains the sole live path for the boundary-quality
  tail and now the sole live product direction for the whole pairing-quality
  family. Needs its own spec/session: a point-moving op (tangential boundary
  slide with per-step validity guard, or geometric acceptance on the pairing
  merge). Must NOT end in a global FEM pass (session-033 erasure result).
- **#116** (`status: needs-operator`) still owes operator decisions: spec-001
  Draft status, SC-007 MATLAB parity oracle (needs MATLAB, env-gated), #109
  CI-token (DomI-managed). Unchanged this session.
- **#109** QuADMESH-side EXPAND is satisfied (both test files now 119/129 LOC
  with quad-ratio / multi-fixture / multi-layer / offline coverage); the residual
  is the DomI-managed upstream Valence CI-token only.
- **#17 / #18 / #26 / #77** — brainstorm issues whose within-faithful pairing
  avenue is now closed by the #97 disposition; candidates for operator
  re-scoping toward the #90 geometric lever or closing as won't-do.

## Introspect (R5, consumer deposit → rolling PR #115 block + here)
- **Dispatches used: 0 of 3.** Docs-only, orchestrator-authored (no code
  written/edited → coding-dispatch policy does not apply). Outcome: 1 commit, #97
  closed with a durable synthesis + disposition comment. Slice-class: docs.
- Convergent outcome per #116: retires the recurring pairing-research thread
  rather than extending it — the honest drain of a genuinely-answered research
  issue (the opposite of the false "drained" claims #116 flagged).
- Pain (matrix-worthy, recurring): the rolling PR body is now large enough that a
  full-body MCP `update_pull_request` round-trip is the only edit path and is
  token-heavy + transcription-risky. Condensed the 07-12→07-20 blocks into
  one-liners this session (detail preserved here in `docs/sessions/`). A
  marker-delimited "latest-N-blocks + archive" body structure, or a body-append
  tool, would cut the round-trip cost.
