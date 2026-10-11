<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# Requirements Quality Checklist: feature 056 (v0.3.0 docs and cleanup)

**Purpose**: unit tests for the requirements in spec.md; validates completeness, clarity, consistency, measurability and coverage. Not an implementation test.
**Created**: 2026-10-10
**Depth**: standard. **Audience**: reviewer (coordinator analyze pass) and implementer (opus worker).
**Focus**: (a) algorithm-description accuracy requirements, (b) release-metadata consistency, (c) writing-stack requirements.

## Requirement Completeness

- [ ] CHK001 Are the sections of `docs/algorithm.md` enumerated so an implementer can tell when the document is complete? [Completeness, Spec FR-001]
- [ ] CHK002 Are both trigger conditions for the experimental fallback (layerless mesh; uncovered elements) required to be documented? [Completeness, Spec FR-002, FR-003]
- [ ] CHK003 Is the point-insertion behaviour specified precisely enough (default path vs `point_insert` option) that "no point insertion" cannot be written as an absolute claim? [Completeness, Spec FR-004, research.md Decision 4]
- [ ] CHK004 Are all DOI occurrences to change listed (badge, citation, note, CITATION.cff)? [Completeness, Spec FR-017]
- [ ] CHK005 Are every human-facing document covered by the writing-stack requirement listed by name, including the release-notes draft and GitHub description? [Completeness, Spec FR-021]
- [ ] CHK006 Is the set of files that feature 057 also edits named, with the exact lines this feature may touch in each? [Completeness, Spec Edge Cases, plan.md Constraints]
- [ ] CHK007 Is the handling of `CITATION.cff` `date-released` for an unreleased 0.3.0 specified? [Gap, Spec FR-012]

## Requirement Clarity

- [ ] CHK008 Is "short" for the README quantified (opening section growth limit, no restated algorithm sections)? [Clarity, Spec FR-009, SC-004]
- [ ] CHK009 Is "labelled as a port-side experiment" defined with the operator's exact wording so the label is not paraphrased into something weaker? [Clarity, Spec FR-003]
- [ ] CHK010 Is the distinction between "faithful" as a banned method name and "faithfulness invariant" as allowed wording explicit? [Clarity, Spec FR-006]
- [ ] CHK011 Is "optional developer override" for the sibling chilmesh checkout specific about failure behaviour when the checkout is absent? [Clarity, Spec FR-016]
- [ ] CHK012 Is the lens scope ("whole document, technical terms verbatim, Golden rule wins") unambiguous about what counts as a technical term? [Ambiguity, Spec FR-021]
- [ ] CHK013 Is the fact add/drop audit defined with a concrete procedure (claims list before vs after)? [Clarity, Spec FR-021, SC-008]

## Requirement Consistency

- [ ] CHK014 Do FR-003 (per-layer sweep is the thesis algorithm and default) and the README status-banner requirement FR-010 describe the default identically? [Consistency, Spec FR-003, FR-010]
- [ ] CHK015 Does FR-004 (Blossom-Quad applies only to the fallback) agree with the User Story 1 acceptance scenario 4 wording? [Consistency, Spec US1-4, FR-004]
- [ ] CHK016 Do FR-012 (no tag in this feature) and tasks T038/T039 (operator-run ceremony; move specs after 057) agree on sequencing? [Consistency, Spec FR-012, tasks.md]
- [ ] CHK017 Does the constitution principle VI (caveman docs) conflict with FR-021 and is the resolution recorded? [Conflict, plan.md Constitution Check]
- [ ] CHK018 Does the feature-directory name `056-v022-docs-cleanup` versus version 0.3.0 have a recorded rationale so it is not "fixed" by a later agent? [Consistency, Spec Assumptions]

## Acceptance Criteria Quality

- [ ] CHK019 Is SC-001 (reader can identify default vs fallback path) verifiable without the reviewer re-deriving the code? [Measurability, Spec SC-001]
- [ ] CHK020 Are SC-002 and SC-003 search terms exhaustive for the stale strings known today (`_match_faithful`, PyPI claims, TODO, `0.2.0`, `0.2.1`)? [Measurability, Spec SC-002, SC-003]
- [ ] CHK021 Is SC-008 "0 hard tells" tied to the hard-tell id list in `ai-tells-scan.md` so weighted-alone hits do not fail the criterion? [Measurability, Spec SC-008]
- [ ] CHK022 Is SC-006 (CFF validates) achievable offline if `cffconvert` is absent, and is the fallback check defined? [Measurability, Spec SC-006, tasks T033]

## Scenario and Edge Case Coverage

- [ ] CHK023 Are requirements defined for a reader following an external link to the deleted `docs/algorithm_writeup.md`? [Coverage, Spec FR-020, plan.md Risks]
- [ ] CHK024 Are requirements defined for the case where feature 057 lands first and this feature must rebase on its `AGENTS.md`/`pyproject.toml` edits? [Edge Case, Spec Edge Cases]
- [ ] CHK025 Are requirements defined for the GitHub description change failing (no `gh` permission)? [Exception Flow, tasks T021]
- [ ] CHK026 Is the ordering requirement (DOI switch before guard test) stated so the test does not fail mid-implementation? [Coverage, plan.md Risks, tasks Dependencies]

## Dependencies and Assumptions

- [ ] CHK027 Is the assumption that the thesis PDF chapter numbers match the docstring citations flagged for verification before use? [Assumption, research.md "Facts for the thesis section", tasks T004]
- [ ] CHK028 Is the dependency on the DomI template `templates/tests/test_release_metadata.py.tmpl` and its `.zenodo.json` behaviour documented? [Dependency, research.md Decision 5]
- [ ] CHK029 Is the operator's statement that chilmesh is on PyPI recorded as the basis for FR-016, with the stale lines enumerated? [Assumption, Spec Context table]

## Ambiguities and Open Items

- [ ] CHK030 Does the spec state who sets `date-released` and when, or is it left implicit in "release ceremony"? [Ambiguity, Spec FR-012]
- [ ] CHK031 Is the term "value statement" used consistently (five items, same wording) across US2, FR-008 and SC-004? [Terminology, Spec US2-1, FR-008, SC-004]

## Notes

- Items CHK007 and CHK030 (date-released handling): resolved in analyze cycle 1; spec FR-012 now states the field keeps `2026-07-13` with a comment and the `release` skill sets it.
- CHK012 is the main residual ambiguity: the lens's "technical term" boundary is defined by example (method names, invariant wording) rather than rule. Acceptable for the implementer; flag if the tell scan or lens rewrites alter a term.
