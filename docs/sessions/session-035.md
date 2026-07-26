# Session 035 — 2026-07-26 (rotation hour-16)

## What changed
- **#97 advanced — within-faithful greedy pairing measured, is NOT the leftover
  lever** (`c54213c`, development; rolling PR #115 rolled). Added a third pairing
  track to `experiments/layer_matching_bound/bound.py`: a deterministic
  minimum-degree-first **greedy maximal matching** (`greedy_maximal_matching`) on
  the same legal tri-adjacency graph the optimal track uses. Answers the open
  question under last session's max-matching bound: *is the 64–86% headroom
  reachable by a within-faithful greedy, or only by the forbidden Blossom method?*
- **#97 non-WNAT replication (item 4, partial)** (`6f539fb`) — re-ran the
  three-track experiment on 4 independent domains (Baranja_Hill, Onion, Italy,
  Lake_Michigan). Both effects reproduce on every domain.
- **#17 / #18 advanced** — posted measured Option-1 (quality-aware merge
  selection) dispositions (advance-only, no label flip).

## Key decisions / findings
- **A single-pass greedy does NOT reach the matching ceiling and REGRESSES vs the
  production heuristic on 6 of 8 primary meshes + all 4 non-WNAT meshes.**
  WNAT_Hagen greedy 9,567 vs heuristic 5,509 vs optimal 755 (+73.7%); Deleware
  +106%; LakeErie +104%; Italy +106%; Lake_Michigan +115%. Reaches optimal only
  on the trivial structured mesh.
- **The 64–86% headroom is augmenting-path-specific (Blossom, `method="matching"`,
  removed #46), not "smarter greedy."** The every-other + T017/T018 walk is
  already a tuned pairing that a generic greedy underperforms — there is no easy
  greedy pass leaving pairs on the table.
- **Holds a fortiori for #17/#18 Option-1 (quality-aware greedy):** a quality-first
  ordering optimizes for quality not pairing cardinality, so it strands ≥ as many
  tris — it cannot capture the cardinality headroom either. **Disposition: pairing-
  rule changes are not a leftover-reduction lever; the #90 boundary-quality tail
  is a geometric problem (session-034: tangential boundary slide / geometric
  acceptance), not a topological one.**

## Verification
- Heuristic + optimal columns reproduce last session's `c5d8572` numbers
  **exactly** on all 8 meshes → harness validated; the greedy track is the only
  new signal.
- Faithfulness gate `test_no_interior_tris` **36 passed** at HEAD.
- Additive only — new experiment track + `results/greedy_track{,_nonwnat}.json` +
  a benchmark-doc section; no product / locked-module / faithfulness change.
  `networkx` is experiment-only. DomI pin verified synced (`c430fc2` == remote
  DomI main HEAD after fetch) — no bump.

## What comes next
- **#90 geometric lever** remains the sole live path for the boundary-quality
  tail — a point-moving op (tangential boundary slide with per-step validity
  guard, or geometric acceptance on the pairing merge). Needs its own spec/session;
  must not end in a global FEM pass (session-033 erasure).
- **#17 / #18** now carry a measured Option-1 disposition; operator call on
  re-scoping them toward the #90 geometric lever or closing as won't-do.
- **#97** remaining item: the 1,000-run structural/near-structural split (needs
  substantial compute; the walk-start MC harness is `experiments/mc_layer_pass/`).
- **#116** (needs-operator): spec-001 Draft / SC-007 MATLAB oracle / #109 CI-token
  decisions still owed by operator.

## Introspect (R5, consumer deposit → rolling PR #115 block + here)
- **Dispatches used: 1 of 3** (Haiku, the `bound.py` greedy-track edit — 6 anchored
  edits, one file). Orchestrator verified the diff on disk + ran the experiment +
  faithfulness gate before commit. Second slice (non-WNAT replication) was
  zero-dispatch (harness already built, run inline).
- **Slice outcome:** 2 commits shipped; #97 advanced (item 3 measured + item 4
  partial); #17/#18 advanced with measured dispositions. Convergent — reduces the
  open pairing-quality design space rather than adding to it (responsive to #116's
  "quality-research drift" flag).
- **Pain (minor, matrix-worthy):** session-start health check reported
  `DOMI PIN DRIFT — HARD STOP` (false positive). Ground truth: pin sha `c430fc2`
  == remote DomI `origin/main` HEAD after `git fetch` == local DomI == manifest
  hash match → zero drift. The `gh`-based drift check in `check_pin.sh` flagged
  drift that did not exist (likely a transient proxy/network read). Verified
  manually and proceeded. Recurrence pattern: worth a `check_pin.sh` robustness
  row (distinguish real drift from a failed upstream read → treat unreachable as
  gh-unavailable/warn, not behind/hard-stop).
