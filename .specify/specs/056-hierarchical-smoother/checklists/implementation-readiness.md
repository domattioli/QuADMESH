# Checklist: Implementation Readiness — Hierarchical Smoother (spec-056)

**Purpose**: Unit-test the requirements (spec + plan + contracts) for implementer-readiness — completeness/clarity, determinism + faithfulness gates, benchmark validity
**Created**: 2026-07-03
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [contracts/api.md](../contracts/api.md)

## Requirement Completeness

- [x] CHK001 - Are all three selection policies specified with their parameters, defaults, and output invariants? [Completeness, Spec §FR-002, Contract §select_region]
- [x] CHK002 - Is the patch definition complete — component rule, overlap handling, minimum size, rim/interior partition? [Completeness, Spec §FR-003/FR-004 + Edge Cases, Data-model §Patch]
- [x] CHK003 - Are BOTH composition modes (supplement kwarg, standalone replacement) and their default global-pass counts specified? [Completeness, Spec §FR-001 + Clarifications Q3/Q5]
- [x] CHK004 - Is the cheap-global stage fully specified (scope, guard semantics, default-off, orderings)? [Completeness, Spec §FR-005/FR-006 + Clarification Q1, Research §R7]
- [x] CHK005 - Are fallback and empty-selection behaviors defined with thresholds and return semantics? [Completeness, Spec §FR-012/FR-013]
- [x] CHK006 - Are the halt criterion, its epsilon, the alternative criterion, and the hard cap all specified with defaults? [Completeness, Spec §FR-007 + Clarification Q4]

## Requirement Clarity

- [x] CHK007 - Is "smoothing phase wall-clock" unambiguously bounded (what is inside/outside the measured phase)? [Clarity, Spec §SC-001 + Clarification Q2]
- [x] CHK008 - Is "parity" quantified (tolerance value and direction) for mean/median skew and tail count? [Clarity, Spec §SC-002 + Assumptions]
- [x] CHK009 - Is the baseline defined precisely enough to re-measure (config, pass count, measurement protocol, same-machine rule)? [Clarity, Spec §SC-001 + Assumptions, Research §R6]
- [x] CHK010 - Is "worst 5–10% by skew" pinned to a single default value rather than a range at implementation time? [Ambiguity, Spec §FR-002 vs Plan §Selection stage — plan says 0.075; spec says "default N in 5–10, configurable"]
- [x] CHK011 - Are "1-ring neighborhood" and "connected" (edge- vs vertex-adjacency) defined for both dilation and patch components? [Ambiguity, Spec §FR-002/Key Entities vs Plan §Patch construction — plan pins edge-adjacency for components and vertex-based 1-ring for dilation; spec silent]

## Requirement Consistency

- [x] CHK012 - Do the supplement-mode default (pre-pass + 1 global pass) and SC-001's ≥2× gate remain jointly satisfiable as written? [Consistency, Spec §FR-001 + Clarification Q5 + SC-001]
- [x] CHK013 - Is the measured default plan consistent everywhere (local-FEM-only in FR-005 vs "default stage plan" language in SC-001 vs supplement default in FR-001 — which plan does SC-001 gate)? [Conflict, Spec §FR-005/SC-001/FR-001]
- [x] CHK014 - Are boundary-pinning statements consistent across stages (FEM patches, cheap pass, bowtie repair)? [Consistency, Spec §FR-008 + Edge Cases]
- [x] CHK015 - Does the additive-only constraint align with the post_process_routine kwarg change described in contracts (same function, new kwargs, byte-identical when absent)? [Consistency, Spec §FR-001/SC-005, Contract §post_process_routine]

## Acceptance Criteria Quality / Measurability

- [x] CHK016 - Is every SC verifiable with data the bench emits (wall-clock, skew stats, tail count, invariant flag, bitwise determinism)? [Measurability, Spec §SC-001…SC-007, Data-model §BenchRecord]
- [x] CHK017 - Is the determinism requirement testable as stated (two identical runs → bitwise-identical outputs, on every benchmarked mesh)? [Measurability, Spec §SC-006/FR-004]
- [x] CHK018 - Is the faithfulness gate tied to a named, existing test (including the geometric 180°-corner check)? [Measurability, Spec §FR-009/SC-004]

## Scenario & Edge Case Coverage

- [x] CHK019 - Are empty-selection, near-whole-mesh selection, overlapping patches, boundary-touching patches, tiny patches, and mixed-element patches ALL covered by requirements? [Coverage, Spec §Edge Cases + FR-012/FR-013]
- [x] CHK020 - Is behavior specified when the layer policy is requested but layer data is absent? [Edge Case, Research §R3 — ValueError; spec Edge Cases silent] 
- [x] CHK021 - Is the cheap-pass quality-regression scenario covered with a defined guard outcome (revert semantics)? [Coverage, Spec §Edge Cases + FR-005, Research §R7]
- [x] CHK022 - Are token-less environments (no WNAT fixture) addressed — what lands, what defers, how it is recorded? [Coverage, Spec §Assumptions, Tasks §T014]

## Dependencies & Assumptions

- [x] CHK023 - Is the chilmesh submesh-construction dependency validated against the shipped chilmesh version (fast-init flags exist and suffice), with the upstream-gap escape hatch documented? [Assumption, Spec §Assumptions, Research §R1]
- [x] CHK024 - Is the assumption that patch rim pinning ≡ far-field freezing justified somewhere the implementer can check? [Assumption, Research §R2]
- [x] CHK025 - Is the no-extra-skeletonization assumption consistent between spec and research (layer policy reads existing decomposition only)? [Consistency, Spec §Assumptions, Research §R3]

## Benchmark Validity

- [x] CHK026 - Does the bench design isolate variants (fresh deep-copied pre-smoothing state per variant, baseline measured in-session)? [Completeness, Research §R6, Tasks §T012]
- [x] CHK027 - Is the baseline row mandatory in every bench output, and is speedup defined relative to it? [Completeness, Contract §CLI, Data-model §BenchRecord]
- [x] CHK028 - Are bench failure semantics defined (invariant failure → nonzero exit) so a "fast but unfaithful" variant cannot silently win? [Coverage, Contract §CLI]
