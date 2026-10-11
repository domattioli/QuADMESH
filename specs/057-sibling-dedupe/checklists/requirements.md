<!-- provenance: author=domattioli model=claude-opus-5-5 effort=low date=2026-10-10 skill=speckit-checklist repo=quadmesh session=unknown -->
# Requirements Quality Checklist: 057 sibling dedupe

**Purpose**: Unit tests for the requirements in spec.md. Each item checks whether a requirement is written well. It does not check whether the code works.
**Created**: 2026-10-10

## Completeness

- [ ] CHK001 Does every inventory row have a class and a disposition, with file:line citations on both sides? [Completeness, Spec §Redundancy inventory]
- [ ] CHK002 Is the fallback for each partial row stated, so that "no block" holds? [Completeness, FR-008, Clarifications Q4]
- [ ] CHK003 Are all release channels (GitHub tarball, Zenodo, sdist, wheel) covered by an explicit requirement? [Completeness, FR-013 to FR-017]
- [ ] CHK004 Is every human-facing document that the writing stack covers listed by name? [Completeness, FR-020]

## Clarity

- [ ] CHK005 Is the SC-002 parity tolerance (1e-6 absolute on mean and min, identical `n_elems`) unambiguous about which fixtures count? [Clarity, SC-002]
- [ ] CHK006 Is "0 hard tells" defined by a named source (ai-tells-scan.md hard vs weighted)? [Clarity, SC-008]
- [ ] CHK007 Is the ownership boundary with 056 stated at file level for `pyproject.toml`? [Clarity, FR-018]

## Consistency

- [ ] CHK008 Do FR-009 (chilmesh>=1.5.0) and the Assumptions agree on the floor and its rationale? [Consistency]
- [ ] CHK009 Does FR-007 (warn 0.3.0, remove 0.4.0) match the `two_part_smoother` row 5 and task T015? [Consistency]
- [ ] CHK010 Are the method-name rules (FR-002) consistent with AGENTS.md (`"quadmesh+"`, `"layered"`, and `ValueError` for `"matching"` and `"faithful"`)? [Consistency]

## Coverage and edge cases

- [ ] CHK011 Is the behavior defined when `submesh` drops `grid_name` or padded triangle rows? [Edge case, Spec §Edge Cases]
- [ ] CHK012 Is the reason the `[admesh]` extra is deferred (it pulls in Valence code) stated, along with the condition for revisiting it? [Clarity, FR-011]
- [ ] CHK013 Is the ban on any Valence dependency (runtime, extra, or dev) stated so that a reviewer can check it in `pyproject.toml`? [Measurability, FR-010]
- [ ] CHK014 Is the risk that `move_specs_to_domi.sh` deletes the specs of a parallel feature captured as a requirement or gate? [Gap, plan R11, task T033]

## Measurability

- [ ] CHK015 Can SC-003 (net LOC drop of about 70) be measured objectively given conditional T008? [Measurability]
- [ ] CHK016 Is the zero-interior-residual-triangle invariant measured by an unchanged test file (FR-001)? [Measurability]
