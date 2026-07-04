# Feature Specification: Hierarchical Smoothing Routine

**Feature Branch**: `056-hierarchical-smoother` (operator-authorized 2026-07-03)
**Created**: 2026-07-03
**Status**: Implemented (US1 + US3); SC-001 gate MEASURED on WNAT_Onur 2026-07-04: **FAILED** (supplement 0.61×, gate needs ≥2×) — see Decision Log "SC-001 gate run"
**Driving issue**: [#104](https://github.com/domattioli/QuADMESH/issues/104)
**Input**: User description: "Hierarchical (selective/local-first) smoothing routine for QuADMESH+ post-processing. fem_smoother runs n_iter=3 GLOBAL Balendran FEM passes (2n×2n sparse assembly + spsolve each) and post_process_routine is 69.5% of total wall-clock on ENPAC2003 (537.6 s of 773.3 s), while quality defects are concentrated — per #90, 99.86% of sub-0.30-skew quads sit in skeleton layer 0 and interior layers are already ≥0.80 mean skew. Build an opt-in smoother that smooths only where it matters, hands the rest to a cheaper pass, cuts smoothing wall-clock ≥2× at WNAT scale, and improves or preserves mean/median skew — leveraging existing pieces (Balendran assembly with pinning, truss_smoother, layer decomposition, skew metric), no new smoother physics."

## Clarifications

### Session 2026-07-03

- Q: When the hierarchical smoother is enabled with no further options, does the cheap global pass run by default? → A: No — local-FEM-only is the default stage plan; the cheap pass is opt-in per stage plan.
- Q: What counts inside the "smoothing phase wall-clock" for the ≥2× gate (SC-001)? → A: End-to-end — skew scan, region selection, patch construction/merging, and all solves count; nothing excluded as "overhead".
- Q: Does the post_process_routine opt-in kwarg REPLACE the fem_smoother stage or SUPPLEMENT it? → A: Supplement — hierarchical local-FEM runs as a pre-pass, then the global FEM stage runs as today; the standalone callable remains available for replacement-style composition.
- Q: Default halt criterion for patch convergence iteration (FR-007)? → A: Quality delta — a patch stops iterating when its mean-skew improvement falls below epsilon (hard iteration cap still applies); displacement tolerance available as an alternative.
- Q: In supplement mode, how many global FEM passes follow the hierarchical pre-pass (needed to keep the ≥2× gate satisfiable)? → A: One global pass by default (configurable) — pre-pass + 1 global solve vs the baseline's 3 global solves is the arithmetic the 2× gate binds against; SC-001 unchanged.

## Problem

The post-process smoother spends global effort on a local problem. Every FEM pass
assembles and solves a whole-mesh system even though the elements that actually
need geometric relaxation are a thin, identifiable subset (worst-skew tail +
boundary band). At ENPAC scale this makes smoothing the single largest cost in
the pipeline (~70% of wall-clock). The mesh already carries everything needed to
target the effort: a per-element skew metric, a skeleton-layer decomposition,
element/vertex adjacency, and a FEM formulation whose pinning mechanism works for
*any* node set — not just the domain boundary.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fast opt-in hierarchical smoothing at parity quality (Priority: P1)

A pipeline user meshing a WNAT-scale domain opts into the hierarchical smoother
(new routine + a `post_process_routine` kwarg). The run completes with the
smoothing phase at least 2× faster than the current 3-pass global FEM smoother,
with mean/median skew no worse than the baseline and the zero-interior-residual-
triangle invariant intact. The default path (no opt-in) is untouched — byte-
identical output to today.

**Why this priority**: This is the entire point of #104 — smoothing is ~70% of
pipeline wall-clock; halving it cuts total ENPAC runtime by roughly a third.
Parity quality + faithfulness are the non-negotiable guardrails that make the
speedup usable.

**Independent Test**: Run the benchmark script on Test_Case_1 / Block_O /
WNAT_Onur with and without the opt-in flag; compare smoothing wall-clock, mean/
median skew, sub-0.30 tail count, and `tests/test_no_interior_tris.py` results.

**Acceptance Scenarios**:

1. **Given** a tri2quad output mesh at WNAT_Onur scale, **When** post-processing
   runs with the hierarchical smoother enabled, **Then** the smoothing phase
   wall-clock is ≤ 50% of the baseline `fem_smoother(n_iter=3)` phase on the
   same mesh and machine.
2. **Given** the same run, **When** quality is measured, **Then** mean and
   median skew are ≥ the baseline values minus 0.005 (parity tolerance), and the
   count of sub-0.30-skew elements is ≤ the baseline count.
3. **Given** any run with the hierarchical smoother enabled, **When**
   `tests/test_no_interior_tris.py` executes on the output, **Then** it passes
   (zero interior residual triangles, including the geometric 180°-corner check).
4. **Given** a run WITHOUT the opt-in, **When** post-processing runs, **Then**
   output vertices/connectivity are identical to the current release behavior.
5. **Given** two identical invocations with the same inputs and options,
   **When** both complete, **Then** outputs are bitwise identical (determinism).

---

### User Story 2 - Quality lift from converged local patches (Priority: P2)

Because patch-local solves are small, the user can afford to iterate them to
convergence (rather than the fixed 3 global passes). On the region that gets FEM
treatment, local quality improves beyond what 3 global passes deliver, lifting
the mesh-wide mean skew above baseline — not merely matching it.

**Why this priority**: "Improve avg mesh quality if possible" is the issue's
secondary goal. It is a natural free win of the hierarchical structure (cheap
local systems → more iterations affordable), but the P1 speedup must not be
sacrificed for it.

**Independent Test**: On Block_O and WNAT_Onur, compare mean skew of
hierarchical-converged output vs baseline 3-pass global output.

**Acceptance Scenarios**:

1. **Given** the hierarchical smoother with local-convergence iteration enabled,
   **When** run on at least one benchmark mesh, **Then** mesh-wide mean skew
   strictly exceeds the baseline 3-pass global result.
2. **Given** local iteration, **When** a patch stops improving (displacement or
   quality delta below tolerance), **Then** iteration on that patch halts (no
   fixed-iteration waste, no unbounded loops).

---

### User Story 3 - Strategy comparison report (Priority: P3)

A maintainer runs a benchmark script that sweeps the region-selection policies
(worst-percentile skew + 1-ring, layer-based, valence-based) and pass orderings
(local-FEM-then-cheap-global, cheap-global-then-local-FEM, local-FEM-only) on
the small→large mesh ladder, and reads a table (markdown + JSON) of wall-clock
and quality per variant — the evidence base for choosing the shipped default and
for the #104 issue write-up.

**Why this priority**: #104 explicitly asks for trial-and-error measurement
("test it all out on a smaller mesh like wnat onur before advancing"). The
comparison harness is how the brainstorm converts to a decision, but it serves
the first two stories rather than end users.

**Independent Test**: Run the bench script on Test_Case_1; confirm it emits one
row per (policy × ordering) variant with timing + quality columns and a
recommended-variant line.

**Acceptance Scenarios**:

1. **Given** the benchmark script and a registry mesh id, **When** executed,
   **Then** it produces a per-variant table with: smoothing wall-clock, mean/
   median skew, sub-0.30 count, faithfulness pass/fail — and writes it to a
   results file.
2. **Given** results across the mesh ladder, **When** the maintainer inspects
   them, **Then** a recommended default (policy + ordering) is recorded in the
   spec's decision log with the numbers that justify it.

---

### Edge Cases

- **Selection is empty** (mesh already high quality everywhere): the FEM stage
  is skipped entirely; the routine degrades to the cheap pass (or a no-op) and
  must still return a valid mesh.
- **Selection is nearly the whole mesh** (uniformly bad mesh): patches merge
  into one giant patch — cost approaches the global solve. The routine must not
  be *slower* than baseline by more than the selection overhead; if selected
  fraction exceeds a threshold, fall back to the global path.
- **Adjacent/overlapping patches**: two worst-element neighborhoods sharing
  nodes must be merged (or processed with a deterministic ordering) so a node is
  never solved in two patches with conflicting results.
- **Patch rim = domain boundary**: patches touching the domain boundary pin both
  the rim interface nodes and the true boundary nodes; boundary nodes never move
  (no boundary slide — #90/#98 territory, out of scope).
- **Tiny patches** (< a handful of interior nodes): solving is pointless or
  singular; merge into a neighbor patch or skip below a minimum size.
- **Mixed-element patches** (quads + padded boundary tris): the stiffness
  assembly must use the mixed path exactly as the global smoother does.
- **Smoother-induced bowties**: the existing post-smooth bowtie fix must run on
  the hierarchical output the same way it runs on the global output.
- **Cheap-pass regression risk**: an iterative global pass (springs/Laplacian)
  may *worsen* already-good elements; it must be quality-guarded (revert moves
  that reduce local quality below tolerance) or skipped when it doesn't pay.
- **Layer policy without layer data**: requesting layer-based selection on a
  mesh with no layer decomposition raises an error directing the caller to the
  skew policy; the smoother never triggers a skeletonization pass itself.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a new, opt-in hierarchical smoothing
  routine, exposed both as a standalone callable and as an opt-in parameter of
  the existing post-process entry point. In the post-process entry point the
  opt-in composes as a SUPPLEMENT: the hierarchical local-FEM pre-pass runs
  first, then the existing global FEM stage runs with a configurable number of
  global passes, DEFAULT 1 (vs the baseline's 3 — this is what makes the ≥2×
  gate satisfiable in supplement mode). The standalone callable supports
  replacement-style use. The
  default behavior of the existing smoother and the post-process routine with
  the opt-in absent MUST remain unchanged (additive only).
- **FR-002**: The routine MUST identify a target region for FEM smoothing via a
  pluggable selection policy, with at least three policies implemented:
  (a) worst-N% elements by skew quality plus their 1-ring neighborhoods
  (default N = 7.5%, configurable within and beyond 5–10); (b) skeleton-layer-based
  selection (layer 0, optionally 0–1) — requesting this policy on a mesh whose
  layer decomposition is absent is an error, not a silent skeletonization pass;
  (c) vertex-valence-irregularity-based selection. Policy choice and parameters
  MUST be caller-configurable.
- **FR-003**: The routine MUST smooth the selected region by patch-local FEM
  solves that reuse the existing Balendran stiffness formulation, pinning each
  patch's rim (interface) nodes and all domain-boundary nodes so that non-selected
  mesh geometry is never modified by the FEM stage.
- **FR-004**: Overlapping or adjacent patches MUST be merged or ordered
  deterministically such that every node's final position is independent of
  arbitrary iteration order (same input + options → bitwise-identical output).
- **FR-005**: The routine MUST support an optional cheap global pass (an
  existing iterative smoother: spring-force or guarded Laplacian) applied to the
  non-FEM region, with a quality guard that prevents net quality loss on
  already-good elements. The cheap pass is OFF in the default stage plan
  (local-FEM-only default); enabling it is an explicit stage-plan opt-in.
  SC-001/SC-002 are measured against the default plan.
- **FR-006**: The routine MUST support configurable stage ordering — at minimum
  local-FEM-then-cheap-global and cheap-global-then-local-FEM — so the ordering
  question in #104 is measurable rather than hard-coded.
- **FR-007**: Patch-local FEM solves MAY iterate to convergence. The default
  halt criterion is quality delta: a patch stops when its mean-skew improvement
  for a pass falls below a configurable epsilon; a displacement-tolerance
  criterion MUST be available as an alternative. A hard iteration cap always
  applies. Caps, epsilon, and criterion choice MUST be configurable with safe
  defaults.
- **FR-008**: Domain-boundary nodes MUST remain exactly pinned through every
  stage (no tangential slide).
- **FR-009**: The zero-interior-residual-triangle faithfulness invariant MUST
  hold on all outputs, verified by the existing invariant test, including the
  geometric (180°-corner) check.
- **FR-010**: The existing post-smooth bowtie repair MUST be applied after the
  hierarchical smoother exactly as after the global smoother.
- **FR-011**: A benchmark script MUST measure, per variant (selection policy ×
  ordering × cheap-pass on/off): smoothing wall-clock, mean/median skew,
  sub-0.30-skew element count, and faithfulness pass/fail — on a mesh ladder of
  Test_Case_1 and Block_O (fast iteration) and WNAT_Onur (the #104 decision
  mesh), emitting markdown + JSON results. ENPAC2003 measurement is a follow-up
  once a variant wins at WNAT scale, not a gate for this feature.
- **FR-012**: If the selected region exceeds a configurable fraction of the mesh
  (default ~50%), the routine MUST fall back to the existing global FEM path so
  the hierarchical machinery never costs more than baseline plus selection
  overhead.
- **FR-013**: When the selection is empty, the FEM stage MUST be skipped and the
  routine MUST still return a valid, unmodified-or-cheap-smoothed mesh.

### Key Entities

- **Selection policy**: A rule mapping (mesh, parameters) → set of target
  elements. Attributes: name, parameters (percentile / layer indices / valence
  thresholds), deterministic output.
- **Patch**: A connected set of selected elements plus its node partition into
  interior (free) nodes and rim (pinned interface) nodes. "Connected" means
  shared-EDGE adjacency between elements; the "1-ring" dilation of a selection
  is vertex-based (all elements sharing any vertex with a seed element).
  Patches are disjoint after merging; the union of patch interiors is the only
  geometry the FEM stage may move.
- **Stage plan**: Ordered list of smoothing stages (local-FEM, cheap-global)
  with per-stage configuration; the unit the benchmark sweeps over.
- **Benchmark record**: One row per (mesh, variant): timings, quality metrics,
  tail counts, invariant result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On WNAT_Onur, the smoothing phase completes in ≤ 50% of the
  baseline 3-pass global smoother's wall-clock (≥ 2× speedup), same machine,
  single thread. Measured end-to-end: selection scan, patch construction/merging,
  and all solves are inside the measured phase — no overhead is excluded. The
  gate binds the SUPPLEMENT default (hierarchical pre-pass + 1 global pass —
  what a pipeline user gets via the opt-in kwarg, per Clarifications Q3/Q5);
  the benchmark also reports standalone local-FEM-only rows for the decision
  record.
- **SC-002**: On every benchmarked mesh, mean and median skew of the
  hierarchical output are ≥ baseline − 0.005, and the sub-0.30-skew element
  count is ≤ baseline.
- **SC-003**: On at least one benchmarked mesh, mesh-wide mean skew strictly
  exceeds the baseline (the quality-lift goal), without violating SC-001 on
  WNAT_Onur.
- **SC-004**: The faithfulness invariant test passes on all hierarchical outputs
  across the benchmark ladder.
- **SC-005**: With the opt-in disabled, the full existing test suite passes
  unchanged and post-process output is identical to current behavior.
- **SC-006**: Two runs with identical inputs and options produce bitwise-
  identical outputs on every benchmarked mesh.
- **SC-007**: The benchmark report exists in the repo with one row per variant
  per mesh and a recorded recommended default backed by those numbers.

## Assumptions

- The `chilmesh` stiffness-assembly internals used by the current global
  smoother (`_tri_stiffness_assembly` / `_quad_stiffness_assembly` /
  `_mixed_stiffness_assembly`) are callable on submesh index sets, or a patch
  submesh can be constructed cheaply enough (vertex compaction) that per-patch
  assembly still wins; if neither holds for chilmesh 1.2.x, that is an upstream
  API gap to file, not a license to fork chilmesh code into this repo.
- Skeleton-layer indices for layer-based selection are recoverable from the
  existing `create_quad_domain` / skeletonization decomposition already computed
  in the pipeline (no extra skeletonization pass required for policy (b)).
- WNAT_Onur and the small fixtures resolve from the Valence registry checkout
  as in existing benchmarks (`manifest.toml` full_ids; token-gated provisioning
  per `tests/fixtures/README.md`); sessions without the fixture token can still
  develop and unit-test on synthetic/small meshes.
- The parity tolerance 0.005 on mean/median skew is small relative to
  run-to-run metric noise on these deterministic pipelines (which are exactly
  reproducible), so it functions as a strict no-regression bound with float
  headroom.
- Baseline numbers are measured fresh on the benchmarking machine within the
  same session as the hierarchical numbers (the README's ENPAC table is a
  different machine/version; never compare across machines).
- ENPAC2003-scale validation and any parallelization of independent patch
  solves (#38) are follow-ups, out of scope here.
- Boundary-node motion (tangential slide) stays out of scope (#90/#98 own it);
  this feature cannot fix boundary-pinned degenerate quads and is not measured
  against them beyond the tail-count guardrail.

---

## Decision Log (implementation, 2026-07-03)

### Bench results — Test_Case_1 (1251 quads) + Block_O (2726 quads)

End-to-end smoothing wall-clock, skew, sub-0.30 tail, interior-tri invariant.
Baseline = `fem_smoother(n_iter=3)`. Speedup = baseline / variant.

| mesh | variant | wall_s | speedup | mean skew | sub-0.30 | interior_tris |
|---|---|---|---|---|---|---|
| TC1 | baseline_global3 | 0.233 | 1.00 | 0.6959 | 104 | 0 |
| TC1 | supplement_skew_g1 | 0.599 | 0.39 | 0.6959 | 104 | 0 |
| TC1 | standalone_skew | 0.397 | 0.59 | 0.5707 | 101 | 0 |
| TC1 | standalone_valence | 0.031 | 7.52 | 0.5609 | 109 | 0 |
| Block_O | baseline_global3 | 0.577 | 1.00 | 0.6806 | 277 | 0 |
| Block_O | supplement_skew_g1 | 0.989 | 0.58 | 0.6806 | 277 | 0 |
| Block_O | standalone_skew | 0.875 | 0.66 | 0.5498 | 296 | 0 |

**Findings (honest):**

1. **Correctness gates all hold** on every variant + both meshes: zero interior
   residual tris, zero inverted elements (post the orientation guard fix),
   boundary pinned bitwise, deterministic. These are the non-negotiables and
   they pass.
2. **Supplement mode preserves quality exactly** — mean/median skew identical to
   the 3-pass baseline (the single final global pass dominates), satisfying
   SC-002 at parity. Standalone (local-only) mode is *lower* quality by design
   (it does strictly less smoothing than 3 global passes) — not the shipped
   default.
3. **No speed win at these scales** — supplement is 0.39–0.58× (SLOWER): on a
   ~1–3k-elem mesh the patch-build overhead exceeds the 2 saved global passes.
   This is exactly the spec Risk-section prediction. The `standalone_valence`
   7.5× "speedup" is an artifact of near-empty selection (few irregular verts →
   almost no work → also worse quality); not a real win.
4. **SC-001 (≥2× on WNAT_Onur) is DEFERRED, not met** — the 246k-elem gate mesh
   is not provisioned in-container and would not complete through pure-Python
   chilmesh here. The ≥2× arithmetic only turns positive where one giant global
   `spsolve` dominates patch overhead (WNAT scale); a hosted runner with the
   C++ chilmesh backend is required to measure it. **Do not claim SC-001 met.**
5. `standalone_layer` fell back to the global path on both meshes (layer-0
   selection exceeded `fallback_frac`=0.5) — the FR-012 safety valve firing
   correctly, visible as speedup≈1.0 + identical quality.

**Recommended default (pending WNAT confirmation):** `supplement_skew_g1` —
the only variant that holds baseline quality; ship it as the `hierarchical=True`
composition, gate the speed claim on a hosted WNAT_Onur run.

### Known limitations (review findings 4–5, LOW — deferred, not blocking)

- `_cheap_global_guarded` and the `valence` selection policy use pure-Python
  O(n_verts) loops → tens of seconds on WNAT-class meshes. Both are opt-in
  (cheap stage is off by default; valence is a non-default policy), so they do
  not affect the default `skew`+`local_fem` path. Vectorize before relying on
  either at scale.
- The post-smooth `_fix_bowties` rebuild uses the default `CHILmesh` ctor
  (re-runs layerization); with the pure-Python backend a bowtie rebuild on a
  large mesh is costly. Pass a fast-init path if this bites at scale.

### Pre-existing failure (NOT introduced here)

`tests/test_no_interior_tris.py::test_no_interior_geometric_tris[Test_Case_1.14]`
fails `2 == 0` on the clean tree (verified via git stash) — the known T019
boundary-tri routing residual (CLAUDE.md), on the DEFAULT pipeline this feature
does not touch. Out of scope for #104.

## Decision Log — SC-001 gate run, WNAT_Onur (2026-07-04, rotation session)

Gate mesh provisioned from the Valence sibling clone
(`/home/user/Valence/registry_data/meshes/WNAT_Onur.14`); chilmesh C++ backend
built in-container (`chilmesh_cpp 0.6.0.dev0`, `backend_info()` selected=cpp).
246,186 tris → pipeline snapshot 129,916 quads in 241.4 s. Bench:
`scripts/bench_hierarchical_smooth.py --mesh WNAT_Onur.14 --skip-cheap`
(single thread, same machine; `output/` is gitignored so the table is pinned here).

| variant | wall_s | speedup | mean skew | median | sub-0.30 | interior_tris |
|---|---|---|---|---|---|---|
| baseline_global3 | 33.542 | 1.00 | 0.6365 | 0.7148 | 16601 | 0 |
| standalone_skew | 42.181 | 0.80 | 0.5160 | 0.5789 | 18033 | 0 |
| standalone_layer | 37.490 | 0.89 | 0.6365 | 0.7148 | 16600 | 0 |
| standalone_valence | 4.410 | 7.61 | 0.5056 | 0.5693 | 18212 | 0 |
| supplement_skew_g1 | 55.029 | 0.61 | 0.6365 | 0.7148 | 16601 | 0 |

### Verdicts

- **SC-001 FAILED** (measured, not deferred): supplement default = 0.61× —
  SLOWER than the 3-pass baseline. The premise "one giant global solve dominates
  patch overhead at WNAT scale" is falsified on this machine: 3 global Balendran
  passes cost only 33.5 s at 130k quads, and the patch pre-pass ALONE
  (standalone_skew, 42.2 s) already exceeds that. The per-patch Python loop
  overhead scales with patch count and never amortizes.
- **SC-002 holds for the supplement default** (mean/median/sub-0.30 identical to
  baseline). Standalone variants violate it (quality regressions) — not defaults.
- **SC-003 FAILED**: no variant strictly lifts mean skew anywhere.
- **Faithfulness invariant holds** on every variant (0 interior tris);
  bench exit 0.

### Mechanism finding — the global Balendran pass ERASES any pre-pass

`supplement_skew_g1` starts its global pass from the pre-passed state that
standalone_skew measures at mean 0.5160, yet lands on 0.6365/0.7148/16601 —
**bit-for-bit the 3-pass baseline metrics** (same phenomenon on TC1 + Block_O:
supplement == baseline exactly). The global solve (K·u=0 interior, boundary
pinned via kinf) behaves as a connectivity-anchored equilibrium: any interior
pre-conditioning is mapped back to (numerically) the same fixed point.
Consequences:

1. **Supplement composition is architecturally incapable of a quality lift** —
   whatever the pre-pass does, the trailing global pass undoes. It can only add
   cost. The spec's supplement design (Clarifications Q3/Q5) is a dead end.
2. **Baseline passes 2–3 are no-ops**: supplement's SINGLE trailing global pass
   reproduces the 3-pass baseline metrics exactly → `fem_smoother(n_iter=3)`
   wastes ~2/3 of its wall-clock (~22 s of 33.5 s here). The cheap, real win
   #104 was hunting is `n_iter=1` (~3× smoothing cut, zero quality change on
   every mesh measured) — needs its own gate run + default-path byte-identity
   decision (follow-up, not this spec's opt-in surface). Note
   `fem_smoother`'s docstring claims early-stop-on-no-improvement; no such
   check exists in the code.
3. **Smoothing is not the WNAT_Onur bottleneck with the C++ chilmesh backend**:
   33.5 s smoothing vs 241.4 s sweep/cleanup (~12% of total). The 69.5% ENPAC
   figure that motivated #104 does not transfer to this configuration; re-profile
   before investing further in smoother wall-clock.

### Cheap-global orderings — measured at small scale (2026-07-04, operator ask)

The only compositions that do NOT end in a global FEM pass (hence not condemned
a priori by the erasure finding). Full sweep re-run on TC1 + Block_O:

| mesh | variant | wall_s | speedup | mean skew | sub-0.30 |
|---|---|---|---|---|---|
| TC1 | skew_local_then_cheap | 0.515 | 0.43 | 0.6150 | 101 |
| TC1 | skew_cheap_then_local | 0.529 | 0.41 | 0.6150 | 101 |
| Block_O | skew_local_then_cheap | 1.115 | 0.45 | 0.6025 | 286 |
| Block_O | skew_cheap_then_local | 1.120 | 0.44 | 0.6025 | 286 |

Both worse than baseline on quality (−0.08) AND slower; both orderings land on
identical metrics (ordering is irrelevant). Condemned at small scale. A
WNAT-scale run stays blocked on vectorizing `_cheap_global_guarded`
(pure-Python O(n_verts), Known limitations above) and has no quality signal to
chase. With this, all 7 grid variants are measured on TC1 + Block_O and 5 of 7
on WNAT_Onur; every composition is either erased by, or worse than, one global
Balendran pass — reinforcing the n_iter=1 recommendation (#107).

### Recommendation (supersedes "pending WNAT confirmation" above)

Do NOT promote `hierarchical=True` beyond opt-in; do not default it anywhere.
Keep the machinery + this negative result for the record (PR #105). Redirect
effort to (a) `n_iter=1` default gate run, (b) sweep/cleanup profiling (the
actual 88%), (c) if boundary-layer quality (#90) is the target, ops that don't
end in a global FEM pass.
