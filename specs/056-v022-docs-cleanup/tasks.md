<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# Tasks: QuADMESH v0.3.0 Documentation and Cleanup Release (feature 056)

**Input**: Design documents from `specs/056-v022-docs-cleanup/` (spec.md, plan.md, research.md, data-model.md, quickstart.md)
**Tests**: One test task (concept-DOI guard) is required by spec FR-017. No other test tasks.
**Organization**: Grouped by user story. Writing-stack tasks (spec FR-021) follow the content tasks of each story.
**Branch**: `development`. No feature branch, no tag, no push (operator instruction). Commits per DomI git policy when the coordinator says so.
**Coordination**: Feature 057 (sibling dedupe) also edits `pyproject.toml` dependencies, `AGENTS.md`, `docs/MAPPING.md`. This feature touches `pyproject.toml` version and description lines only, `AGENTS.md` line 32 only, and `docs/MAPPING.md` row 10 plus parity item only. 056 implements first.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependencies)
- **[Story]**: US1 (long-form doc), US2 (README and descriptions), US3 (metadata hygiene)

## Phase 1: Setup

- [x] T001 Read `~/.claude/skills/write-like-scientist/SKILL.md`, `~/.claude/skills/write-like-scientist/references/ai-tells-scan.md`, and `~/.claude/skills/asd-ste100-lens/SKILL.md`; write a short checklist of voice rules 1-10, hard-tell ids, and the lens five-step protocol to the scratchpad for reuse in every writing-stack task
- [x] T002 [P] (skipped: projectmem MCP not available) Run `precheck_file` (projectmem MCP) for each file in plan.md "files touched"; note any failure history in the scratchpad
- [x] T003 [P] Record a baseline: `pytest tests/ -q` result and `git diff --stat` empty, in the scratchpad (quickstart.md section 4 reference)

## Phase 2: Foundational

- [x] T004 Verify thesis chapter and section numbers to cite by reading `docs/Mattioli_Thesis.pdf` (chapters 3 and 4; layer construction, IE/OE/IV/OV sets, fold handling Figure 4.1, boundary-layer ordering section 4.2) and record the confirmed numbers in the scratchpad (research.md "Facts for the thesis section")
- [x] T005 Read `src/quadmesh/tri2quad.py` lines 96-278, 668-737, 805-995, 1040-1130 and `src/quadmesh/identify_edges.py` to confirm the dispatch facts in research.md Decision 1 and Decision 4 (including the exact `point_insert` gating at `:1118`); correct research.md if any line number drifted

## Phase 3: User Story 1 - Long-form algorithm document (P1)

**Goal**: `docs/algorithm.md` describes thesis algorithm, port as implemented, differences, experimental fallback, Blossom-Quad relation (fallback only), parity status.
**Independent test**: quickstart.md section 5.

- [x] T006 [US1] Create `docs/algorithm.md` with sections 1-4 per plan.md "docs/algorithm.md outline": plain summary, thesis algorithm (labelled), port as implemented with `tri2quad_routine` dispatch table and `file:line` pointers, thesis-vs-port difference table (spec FR-001, FR-002, FR-007)
- [x] T007 [US1] Append section 5 "Experimental fallback" to `docs/algorithm.md`: fold in `docs/algorithm_writeup.md` sections 1-8 (trimmed), relabel as port-side experiment with the operator's wording, state both trigger conditions (`tri2quad.py:1083-1093`, `:960-971`), replace the `_match_faithful.py` reference with current module names (spec FR-003, FR-015, FR-020)
- [x] T008 [US1] Append section 6 "Relation to Blossom-Quad" to `docs/algorithm.md`: thesis unrelated; fallback shares matching framing; four-plus differences; full Remacle et al. 2012 citation (spec FR-004; research.md Decision 4)
- [x] T009 [US1] Append section 7 "Parity status versus MATLAB" and section 8 "References" to `docs/algorithm.md` (spec FR-005)
- [x] T010 [US1] Delete `docs/algorithm_writeup.md`; annotate the reference at `docs/sessions/session-018.md:35` as historical pointing to `docs/algorithm.md` section 5 (spec FR-020)
- [x] T011 [US1] Edit `docs/MAPPING.md:10` so "MATLAB-faithful" reads as port intent with a pointer to `docs/algorithm.md` section 7; update parity item at `docs/MAPPING.md:87-89` to point to the same section; touch no other rows (057 edits this file) (spec FR-005)
- [x] T012 [US1] Grep `docs/algorithm.md` and `docs/MAPPING.md` for `faithful` and `matching`; confirm each hit is a removed-name notice or "faithfulness invariant" (spec FR-006)
- [x] T013 [US1] Writing stack, step 1-2 on `docs/algorithm.md`: re-render against voice rules 1-10; Golden rule G1-G17 self-scan; run `python3 ~/.claude/skills/write-like-scientist/scripts/banned_words.py --mode prose docs/algorithm.md` until exit 0 (spec FR-021)
- [x] T014 [US1] Writing stack, step 3 on `docs/algorithm.md`: apply `asd-ste100-lens` steps 1-5 to all prose (not code blocks, tables, inline code); keep method names and invariant wording verbatim; Golden rule wins conflicts (spec FR-021)
- [x] T015 [US1] Writing stack, step 4 on `docs/algorithm.md`: dispatch Haiku scanner per `references/ai-tells-scan.md`; if non-empty, dispatch Sonnet corrector then rescan; perform fact add/drop audit (list of technical claims before T013 vs after T015, zero added, zero dropped); record scanner JSON and audit result in the scratchpad (spec SC-008)
- [x] T016 [US1] Repeat T013-T015 for the edited prose in `docs/MAPPING.md` (spec FR-021)

## Phase 4: User Story 2 - README and package descriptions (P2)

**Goal**: short public surfaces with five value statements, honest quality tail, link to the long-form document, consistent descriptions.
**Independent test**: quickstart.md section 5 (README paragraph) and section 2.

- [x] T017 [US2] Edit `README.md` opening block (after line 10): add the five value statements as a short list using the FR-008 wording ("no point insertion by default"); opening section grows by at most ten lines, file stays within 214 lines (spec FR-008, SC-004)
- [x] T018 [US2] Edit `README.md:45` status banner: drop "(July 2026)" or replace with "0.3.0"; describe default as the per-layer sweep; remove fold-seam-as-default wording; add link to `docs/algorithm.md` (spec FR-009, FR-010)
- [x] T019 [US2] Confirm `README.md` lines 128-150 (ENPAC quality table and tail paragraph) are unchanged by diff (spec FR-009)
- [x] T020 [P] [US2] Edit `pyproject.toml:8` `description` to one sentence consistent with the README first value statement; touch no other line in this task (spec FR-011)
- [x] T021 [P] [US2] (draft only; gh repo edit NOT run per CoS, text in report) Draft the GitHub repository description (one sentence) in the scratchpad; **CoS confirms with operator before running** `gh repo edit domattioli/QuADMESH --description "<text>"` (outward-facing); if not confirmed or `gh` is denied, record the text in the final report for the operator (spec FR-011)
- [x] T022 [US2] Writing stack steps 1-4 on `README.md` prose (exempt: ENPAC table, code blocks, badge HTML): voice rules, Golden rule, `banned_words.py --mode prose README.md` exit 0, STE/ADHD lens, Haiku scan, Sonnet correction if needed, fact audit; record results (spec FR-021, SC-008)
- [x] T023 [US2] Writing stack steps 1-4 on the `pyproject.toml` description sentence and the GitHub description sentence (self-scan plus banned-word check; subagent scan may be batched with T022) (spec FR-021)

## Phase 5: User Story 3 - Release metadata hygiene (P3)

**Goal**: all version, author, DOI, and install-note surfaces agree; stale references removed; guard test in place.
**Independent test**: quickstart.md sections 1-4.

- [x] T024 [P] [US3] Set `__version__ = "0.3.0"` in `src/quadmesh/__init__.py:4` (spec FR-012)
- [x] T025 [P] [US3] Set `version = "0.3.0"` at `pyproject.toml:7`; touch no dependency line (spec FR-012)
- [x] T026 [US3] Edit `CITATION.cff`: `version: 0.3.0`; add second author Kubatko, Ethan J. (affiliation Ohio State University); replace `10.5281/zenodo.20351165` with `10.5281/zenodo.20350483` and update the identifier description to "Zenodo concept DOI (all versions)"; keep `date-released: "2026-07-13"` unchanged and add a YAML comment above it that the `release` skill sets it at tag time (spec FR-012, FR-013, FR-017)
- [x] T027 [US3] Edit `README.md`: DOI badge at line 25 (both occurrences), citation line 172, note line 174 to `10.5281/zenodo.20350483`; delete the TODO comment at line 176; confirm author line 12-13 and citation line 172 match CITATION.cff authors (spec FR-013, FR-014, FR-017)
- [x] T028 [US3] Copy `~/Projects/DomI/templates/tests/test_release_metadata.py.tmpl` to `tests/test_release_metadata.py`, set `CONCEPT_DOI = "10.5281/zenodo.20350483"`, adapt the `.zenodo.json` branch to the file's absence if the template assumes it exists, run `pytest tests/test_release_metadata.py -q` to green (spec FR-017, SC-007)
- [x] T029 [US3] Add `## [0.3.0] - Unreleased` entry to `CHANGELOG.md` above `[0.2.1]` listing: new `docs/algorithm.md` and removal of `docs/algorithm_writeup.md`; README rewrite; Kubatko added to CITATION.cff; concept DOI switch and guard test; chilmesh install notes corrected; version alignment. Add a note under `[0.2.1]` that it was never tagged or published (spec FR-012)
- [x] T030 [P] [US3] Edit `AGENTS.md:32` to state chilmesh installs from PyPI (`chilmesh>=1.2.1`) and that the sibling `../CHILmesh` editable install is an optional developer override; touch no other line (057 edits this file) (spec FR-016)
- [x] T031 [P] [US3] Edit `scripts/dev_setup.sh`: default path installs `quadmesh[dev]` (chilmesh from PyPI); sibling checkout becomes opt-in via `QUADMESH_CHILMESH_SRC=<path>` (editable-install when set); missing checkout is a notice, not an error; update header comment lines 5-7 (spec FR-016, plan.md Metadata changes)
- [x] T032 [US3] Run quickstart.md sections 1-4 end to end; fix any residual `0.2.0`/`0.2.1`/stale string hits outside historical files; confirm `pytest tests/ -q` green and `git diff --stat -- src/` shows only `__init__.py` (spec FR-018, FR-019, SC-002, SC-003, SC-005)
- [x] T033 [US3] Validate `CITATION.cff` against CFF 1.2.0 (`cffconvert --validate` if installed, else `python3 -c "import yaml; yaml.safe_load(open('CITATION.cff'))"` plus a field check for `authors`, `version`, `identifiers`) (spec SC-006)
- [x] T034 [US3] Writing stack steps 1-4 on the `CHANGELOG.md` `[0.3.0]` entry and the `CITATION.cff` `abstract` (G17 is exempt in changelogs; banned-word check exit 0; lens on prose; Haiku scan may be batched; fact audit) (spec FR-021, SC-008)

## Phase 6: Polish and cross-cutting

- [x] T035 Draft release notes for 0.3.0 (feature 056 portion) at `specs/056-v022-docs-cleanup/release-notes-draft.md`, then run writing stack steps 1-4 on it (spec FR-021, SC-008)
- [x] T036 Run the full `pytest tests/ -q` and quickstart.md sections 1-6 once more, including the section 5 read-through of `docs/algorithm.md` that a reviewer can identify default vs fallback path from the document alone (spec SC-001); write a verification table (check, command, result) to `specs/056-v022-docs-cleanup/verification.md`
- [x] T037 Report to the coordinator: files changed, scanner results per document, fact-audit results, GitHub description text if T021 could not apply it, and confirmation that no constitution edit was made (amendment is 057 T026a)
- [ ] T038 (skipped: operator-run) **OPERATOR-RUN, DO NOT EXECUTE IN THIS FEATURE**: tag and release 0.3.0 via the `release` skill after features 056 and 057 both land (sets `CITATION.cff` `date-released`, changes `[0.3.0] - Unreleased` to the release date, creates tag, GitHub release, Zenodo and PyPI publish). Listed here so the ceremony is not forgotten
- [ ] T039 (skipped: no-op pointer to 057 T033) No-op pointer: the move of `.specify/` and `specs/` to DomI (`move_specs_to_domi.sh --apply`) is feature 057 task T033 and runs once after both features implement. Do not run the move from this feature. Depends on every other task (marks 056 complete)

## Dependencies

- Phase 1 and 2 before all stories. T004, T005 block T006-T009.
- US1 (T006-T016) before US2 T018 (link target must exist).
- US3 T026-T027 before T028 (guard test must see the concept DOI everywhere). T024-T025 before T029 and T032.
- Writing-stack tasks (T013-T016, T022-T023, T034, T035) run after the content tasks of their story and before T036.
- T038 is flagged, not executed. T039 is a pointer to 057 T033 (single spec move); nothing in 056 runs the move.

## Parallel execution examples

- After Phase 2: T006 (US1 doc) in parallel with T024, T025, T030, T031 (US3 single-line metadata edits in distinct files).
- T020 and T021 in parallel with T017-T018.
- Haiku scans for T022, T023, T034 can be batched into one scanner dispatch per document set.

## Implementation strategy

MVP = US1 (the long-form document and the deletion of the misleading write-up). US3 is small and can land alongside. US2 last because the README links to US1's output. Total tasks: 39 (US1: 11, US2: 7, US3: 11, setup/foundation: 5, polish: 5).
