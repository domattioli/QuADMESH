<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# Implementation Plan: QuADMESH v0.3.0 Documentation and Cleanup Release (feature 056)

**Branch**: `development` (no feature branch; operator instruction) | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/056-v022-docs-cleanup/spec.md`

## Summary

Replace the single-framing algorithm write-up with `docs/algorithm.md`, which describes the thesis per-layer sweep as the default path, the hybrid layer-priority global matcher as an experimental fallback, the relation of that fallback alone to Blossom-Quad, and the real parity status. Shorten and sharpen the README and package descriptions. Align all release metadata on 0.3.0, add Kubatko to `CITATION.cff`, switch every DOI to the Zenodo concept DOI with a guard test, and correct the stale chilmesh install notes. Every human-facing document then passes the write-like-scientist stack with the STE/ADHD lens and a Haiku/Sonnet tell scan. No algorithm code changes; no tag or release (joint ceremony with feature 057 later).

## Technical Context

**Language/Version**: Python 3.10+ (per `pyproject.toml`); Markdown and YAML for the deliverables
**Primary Dependencies**: `chilmesh>=1.2.1` (PyPI; unchanged), numpy, scipy; pytest for the guard test. `cffconvert` or the `cff` schema check is optional for SC-006 (fall back to a YAML parse plus field check if not installed)
**Storage**: N/A (files in repo)
**Testing**: `pytest tests/`; new `tests/test_release_metadata.py` from DomI `templates/tests/test_release_metadata.py.tmpl`; `python3 ~/.claude/skills/write-like-scientist/scripts/banned_words.py --mode prose <file>`
**Target Platform**: repository docs; PyPI and GitHub project pages
**Project Type**: library + CLI (single project)
**Performance Goals**: N/A
**Constraints**: zero behaviour change in `tri2quad`; no edits to `pyproject.toml` dependency lines (feature 057 owns them); no edits to `docs/MAPPING.md` beyond the `tri2quad_routine` row and the parity paragraph (057 also edits that file); writes to `AGENTS.md` limited to the chilmesh install sentence at line 32
**Scale/Scope**: about 12 files touched; one new doc (~250-400 lines); one deleted doc; one new test

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|---|---|---|
| I. Faithful Port | PASS with clarification | The constitution's "matches MATLAB on canonical cases" claim is not test-backed (`tests/test_parity.py` pins a Python self-baseline). This feature documents that gap (FR-005) rather than closing it. No algorithm change, so no new deviation. |
| II. Depend on chilmesh | PASS | No new primitives. Install notes corrected to the PyPI route. |
| III. Test-First Per Module | PASS | Only new test is the release-metadata guard; no module port. |
| IV. Layered Implementation | N/A | Docs and metadata only. |
| V. Index 0-Based | N/A | |
| VI. Caveman Docs | CONFLICT, resolved via 057 T026a | Constitution says docstrings and READMEs are terse caveman. Operator (2026-10-10) directed the write-like-scientist stack with STE/ADHD lens on all human-facing docs. Human-facing prose follows the operator ruling; docstrings and code comments (not touched here) stay caveman. The constitution amendment lands in feature 057 task T026a (single writer on `.specify/memory/constitution.md`); 056 makes no constitution edit. |

Post-design re-check: unchanged. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/056-v022-docs-cleanup/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0: decisions with evidence
├── data-model.md        # Phase 1: document and metadata entities
├── quickstart.md        # Phase 1: verification walkthrough
├── tasks.md             # Phase 2 (speckit-tasks)
└── checklists/requirements.md
```

No `contracts/`: the feature exposes no new programmatic interface.

### Source Code (repository root) - files touched

```text
README.md                          # value statements, status banner, link, DOI, citation line, TODO removal
CHANGELOG.md                       # [0.3.0] - Unreleased entry; 0.2.1 never-tagged note
CITATION.cff                       # version 0.3.0, add Kubatko, concept DOI, abstract wording
pyproject.toml                     # version line and description line ONLY
AGENTS.md                          # line 32 chilmesh install sentence
src/quadmesh/__init__.py           # __version__ = "0.3.0"
scripts/dev_setup.sh               # PyPI default, sibling checkout optional override
docs/algorithm.md                  # NEW long-form document
docs/algorithm_writeup.md          # DELETED after folding in
docs/MAPPING.md                    # row 10 wording; parity item 5 pointer
docs/sessions/session-018.md       # link annotation (historical)
tests/test_release_metadata.py     # NEW concept-DOI guard
```

**Structure Decision**: single project; no new directories.

## Phase 0: Research (see research.md)

All five clarifications were answered by the operator; no NEEDS CLARIFICATION remains. Research consolidated the code-path facts needed to write `docs/algorithm.md` accurately and located the DOI guard template.

## Phase 1: Design

### docs/algorithm.md outline (FR-001 to FR-007, FR-020)

1. Plain-language summary (what goes in, what comes out, the one invariant).
2. The thesis algorithm (Mattioli 2017, chapters 3 and 4): skeletonization into layers; innermost-first sweep; per layer identify edges, merge pairs, route leftovers; interior-element-before-outer-element ordering; boundary layer handled last. Label: "thesis algorithm".
3. The port as implemented: `tri2quad_routine` dispatch table (method names, `ValueError` cases); default path `_quadmesh_plus_per_layer` (`src/quadmesh/tri2quad.py:805`); supporting modules `identify_edges.py`, `_tri_removal.py`, `_topology.py`; post-process stages; the zero-interior-residual-triangle invariant and its gate `tests/test_no_interior_tris.py`.
4. Thesis-versus-port difference table: per row, thesis behaviour, port behaviour, where in code, status (same / differs / port-only).
5. Experimental fallback: the hybrid layer-priority global matching (`_match_tris_to_quads`, `_layer_priority`, `_sweep_pairs`, fold-seam forbidden edges, augmenting-path fixup). When it runs (layerless mesh `:1083-1093`; uncovered elements `:960-971`). Operator's statement that it was an experiment. Folded-in content from the old write-up sections 1-8, trimmed and relabelled.
6. Relation to Blossom-Quad (Remacle et al. 2012): applies to section 5 only; shared framing (matching on triangle adjacency / dual graph); differences (layer ordering, fold-seam exclusion, boundary-residual steering, no point insertion in the default path, greedy plus augmenting-path rather than min-cost perfect matching). Explicit sentence that the thesis algorithm (section 2) is unrelated to Blossom-Quad.
7. Parity status versus MATLAB: what `tests/test_parity.py` pins; MATLAB counts never captured; "MATLAB-faithful" in `docs/MAPPING.md` is intent.
8. References.

### README changes (FR-008 to FR-011, FR-013, FR-014, FR-017)

- Opening block under the logo: five value statements as a short list.
- Status banner (line 45): drop "(July 2026)"; describe default as the per-layer sweep; link `docs/algorithm.md`; remove the sentence that names fold-seam forbiddance as part of the default.
- Citation section: concept DOI in badge (line 25), citation (172), note (174); remove TODO (176).
- No algorithm sections restated; the ENPAC table and tail paragraph stay verbatim.

### Metadata changes (FR-012, FR-013, FR-016, FR-017)

- Version 0.3.0 in `__init__.py`, `pyproject.toml` version line, `CITATION.cff` version; `date-released` keeps `2026-07-13` plus a YAML comment that the `release` skill sets it at tag time (a CFF date field must stay a valid date, so no placeholder value).
- `CITATION.cff` authors: Mattioli, Dominik D.; Kubatko, Ethan J. (affiliation Ohio State University).
- DOI `10.5281/zenodo.20350483` everywhere; guard test copied from the DomI template with `CONCEPT_DOI` set.
- `AGENTS.md:32` and `scripts/dev_setup.sh`: default `pip install -e ".[dev]"` pulls chilmesh from PyPI; sibling checkout becomes an opt-in override via the environment variable `QUADMESH_CHILMESH_SRC=<path>` (editable-install that path when set) and its absence is no longer an error.
- GitHub repository description edit is outward-facing: the CoS confirms the sentence with the operator before `gh repo edit` runs.

### Writing stack (FR-021, SC-008)

Runs after content tasks for each document in FR-021. Order per `~/.claude/skills/write-like-scientist/SKILL.md` "Writing stack" and "Procedure": voice rules 1-10, Golden rule G1-G17 plus `banned_words.py --mode prose`, `asd-ste100-lens` STE and ADHD layer on the whole document (operator override of the lens's default "summary blocks only" scope; technical terms verbatim; Golden rule wins conflicts), then Haiku scanner and Sonnet corrector per `references/ai-tells-scan.md`, with a fact add/drop audit (diff of claims before and after). Code blocks, inline code, tables of numbers, and the ENPAC table are exempt from the lens.

### Coordination with feature 057

- 056 implements first. 057 edits `pyproject.toml` dependencies, `AGENTS.md`, `docs/MAPPING.md` afterwards and must rebase on 056's edits.
- Tag, GitHub release, Zenodo and PyPI publish: one ceremony after both land, operator-run via the `release` skill. tasks.md carries a flagged, not-executed task for it. The "Move specs to DomI" step is feature 057 task T033 (single move of all `specs/`); 056 has only a pointer note.

### Agent context update

DomI `AGENTS.md` SPECKIT markers: not applicable (this run is in the quadmesh repo; the plan skill forbids editing another repo's `AGENTS.md`). Skipped.

## Risks

- The lens on a scientific body can flatten compound technical modifiers; mitigated by the verbatim-terms rule and the fact audit.
- Deleting `docs/algorithm_writeup.md` breaks external links; mitigated by keeping the fallback section heading text searchable and noting the move in the changelog.
- Guard test will fail until every DOI is switched; order tasks so the switch precedes the test addition in the same commit.
