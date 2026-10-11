<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# Feature Specification: QuADMESH v0.3.0 Documentation and Cleanup Release (feature 056)

**Feature Branch**: `056-v022-docs-cleanup` (no git branch created; work stays on `development`)
**Created**: 2026-10-10
**Status**: Clarified (2026-10-10)
**Input**: User description: "QuADMESH v0.3.0 docs + cleanup release: robust in-repo documentation of the algorithm as actually implemented, honest comparison with the 2017 thesis sweep and with Blossom-Quad, short README and package description that state the algorithm's value and its known boundary-layer quality tail, and a hygiene pass (version, citation metadata, stale references, install notes, DOI check)."

## Context and Evidence

This section records what the repository says today, so that every requirement below can be checked against a file and line.

### How the port is dispatched today

- `tri2quad_routine` accepts `method="quadmesh+"` (default) and the alias `"layered"`; `"faithful"` and `"matching"` raise `ValueError` (`src/quadmesh/tri2quad.py:1054-1063`, `:1095`).
- When the input mesh carries skeleton layers, the default path is `_quadmesh_plus_per_layer`, documented in its docstring as the "True MATLAB Tri2QuadRoutine per-layer loop ... innermost layer first, per-layer identifyEdges -> mergeTriangles -> removeTriangles" (`src/quadmesh/tri2quad.py:805-818`, call site `:1076`).
- Inside that per-layer loop, any element not covered by a skeleton layer falls through to a global triangle-adjacency matcher, `_match_tris_to_quads`, called without a layer priority (`src/quadmesh/tri2quad.py:960-971`).
- When the mesh has no skeleton layers, the whole mesh goes to `_match_tris_to_quads` with a layer-ordered priority from `_layer_priority`, seeded by `_sweep_pairs`, and with fold-seam forbidden edges (`src/quadmesh/tri2quad.py:1083-1093`; priority rule `:668-689`; sweep and seams `:691-737`; matcher `:96-278`, forbidden-edge handling `:149-150`).
- `docs/algorithm_writeup.md` describes the algorithm entirely in the global-matching framing: adjacency graph (section 1), interior-saturating matching problem (section 2), fold-seam forbidden edges (section 3), layer-ordered vertex priority (section 4), seed matching (section 5), greedy extension (section 6), augmenting-path fixup (section 7), residual recombination (section 8). It cites a module `src/quadmesh/_match_faithful.py` that no longer exists (`docs/algorithm_writeup.md:4-7`).
- Operator statement (2026-10-10): the layer-ordered priority inside a global matching, together with the fold-seam forbidden edges, was an operator experiment and is distinct from the thesis layer-by-layer sweep.

### Parity status

- `tests/test_parity.py` pins the current Python output as a regression baseline, not MATLAB output; MATLAB ground-truth element counts were never captured (`tests/test_parity.py:1-13`, `:24-31`; `docs/MAPPING.md:87-89`).
- `docs/MAPPING.md:10` labels the `tri2quad_routine` port "MATLAB-faithful". No test substantiates that against MATLAB output.
- `tests/test_no_interior_tris.py` enforces the zero-interior-residual-triangle invariant (`tests/test_no_interior_tris.py:1-6`).

### Hygiene findings

| Item | Evidence |
|---|---|
| Version split | `src/quadmesh/__init__.py:4` says `0.2.0`; `pyproject.toml:7` says `0.2.1`; `CITATION.cff` says `version: 0.2.1`, `date-released: 2026-07-13`; `CHANGELOG.md:7` has a `[0.2.1] - 2026-07-13` entry. No `v0.2.1` git tag or GitHub release exists (`git tag` lists `v0.1.0`, `v0.1.1`, `v0.2.0`; `gh release list` matches). |
| CITATION authors | `CITATION.cff` lists one author (Mattioli). `README.md:12-13` lists Mattioli and Kubatko as authors; `README.md:172` gives the software citation as "Mattioli, DO, Kubatko, EJ (2026)". |
| Stale README TODO | `README.md:176` is an HTML comment saying to add `CITATION.cff` once the port reaches v1.0.0; `CITATION.cff` already exists at repo root. |
| Stale module name | `docs/algorithm_writeup.md:6` references `src/quadmesh/_match_faithful.py`, removed in #46 (`tests/test_parity.py:24-25`). |
| chilmesh install route | `pyproject.toml:18` depends on `chilmesh>=1.2.1` from PyPI. `AGENTS.md:32` says "CHILmesh is not available from PyPI". `scripts/dev_setup.sh:5-7`, `:19`, `:29` repeat the claim and fail hard without a sibling checkout. Operator confirmed 2026-10-10 that chilmesh is published on PyPI (https://pypi.org/project/chilmesh/). Resolution: the PyPI dependency is correct; `AGENTS.md` and `scripts/dev_setup.sh` are stale. |
| DOI type | `CITATION.cff:21` and `README.md:25,172,174` carry `10.5281/zenodo.20351165`, which the operator confirmed (2026-10-10) is a version DOI. The concept (all-versions) DOI is `10.5281/zenodo.20350483`. No guard test exists in `tests/`, `scripts/`, or `.github/`. |
| README status banner | `README.md:45` says "Current status (July 2026)" and describes the default method as "the interior-saturating per-layer sweep (thesis Ch 4.1 IE-before-OE, Ch 4.2 fold-seam forbiddance)". |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reader learns what the port actually does (Priority: P1)

A hydrodynamic modeller or a reviewer opens the repository to decide whether to trust QuADMESH on their own triangulation. They need a single long-form document that explains, in order: the thesis QuADMESH+ algorithm (2017), what the Python port implements today, where the two differ, and how the approach relates to Blossom-Quad (Remacle et al. 2012). They also need to know what "parity with MATLAB" currently means.

**Why this priority**: The existing write-up describes a framing the operator now calls an experiment and cites a module that no longer exists. A reader who follows it will misdescribe the software in a paper or a review. This is the core deliverable of the release.

**Independent Test**: Open the long-form document and, for each function and code path named in the Context section (`tri2quad_routine`, `_quadmesh_plus_per_layer`, `_match_tris_to_quads`, `_layer_priority`, `_sweep_pairs`, fold-seam forbidden edges, augmenting-path fixup, `_point_insert_tri_pairs`), find a sentence that says whether it is on the default path, the fallback path, or both, with a `file:line` or function-name pointer. Confirm the document contains a thesis-versus-port difference table and a Blossom-Quad comparison paragraph.

**Acceptance Scenarios**:

1. **Given** the long-form document, **When** a reader looks for the default conversion path, **Then** they find the per-layer sweep (`_quadmesh_plus_per_layer`) described as the default for meshes with skeleton layers, and the global matcher described as the fallback for layerless meshes and for elements not covered by any layer.
2. **Given** the long-form document, **When** a reader looks for the thesis algorithm, **Then** they find a description of the thesis layer-by-layer sweep (chapters 3 and 4 of Mattioli 2017) that is labelled as the thesis algorithm and does not claim the port reproduces it byte-for-byte.
3. **Given** the long-form document, **When** a reader looks for the layer-ordered priority, fold-seam forbidden edges, and augmenting-path fixup, **Then** these are labelled as a port-side experiment distinct from the thesis sweep, with the code path where they are active named.
4. **Given** the long-form document, **When** a reader looks for Blossom-Quad, **Then** they find a comparison that states the shared framing (dual-graph or triangle-adjacency matching) and the differences (layer ordering, fold seams, boundary-residual steering, no point insertion on QuADMESH's default path, with the opt-in `point_insert` routine named as the exception, versus Blossom-Quad's min-cost perfect matching with point insertion), with a full citation to Remacle et al. 2012.
5. **Given** the long-form document, **When** a reader looks for parity status, **Then** they find a statement that `tests/test_parity.py` pins a Python self-baseline, that MATLAB counts were never captured, and that "MATLAB-faithful" wording elsewhere refers to port intent, not a verified result.
6. **Given** any document in the repository, **When** a reader searches for "faithful" as a method name, **Then** every match is either a removed-name notice (the `ValueError` message, the changelog) or the phrase "faithfulness invariant", and no document presents it as a usable method.

---

### User Story 2 - Visitor gets the pitch and the caveats in under a minute (Priority: P2)

A visitor lands on the GitHub repository page or the PyPI project page. They need to understand in a few lines what QuADMESH does, why it is worth using, and what its known weakness is, with links to the long-form document for anything deeper.

**Why this priority**: The README and package description are the most-read surfaces. They must stay short while remaining honest. This story depends on Story 1 for the link target.

**Independent Test**: Read the README from the top to the end of the status banner and confirm each of the five value statements is present, the boundary-layer quality tail is acknowledged, and the long-form document is linked. Read `pyproject.toml` `description` and the GitHub repository description and confirm they fit in one sentence each and do not contradict the README.

**Acceptance Scenarios**:

1. **Given** the README, **When** a visitor reads the opening section, **Then** they find all five value statements: converts an existing validated shallow-water triangulation in place; preserves boundary vertices; zero interior residual triangles; no point insertion by default; a quad-pure output option.
2. **Given** the README, **When** a visitor reads the quality section, **Then** the ENPAC table (`README.md:137-143`) and the explanation that the sub-0.30 tail is a boundary-layer artifact (`README.md:145`) remain present and are not softened.
3. **Given** the README, **When** a visitor wants the algorithm detail, **Then** a link to the long-form document appears near the status banner and the README itself does not restate sections 1 to 8 of the algorithm.
4. **Given** the README status banner (`README.md:45`), **When** a visitor reads it, **Then** it no longer carries a stale month stamp and does not describe the default method in terms that the long-form document labels an experiment.
5. **Given** the package metadata, **When** a visitor reads the PyPI description, **Then** it is one sentence, matches the README's first value statement, and links to the repository.

---

### User Story 3 - Maintainer cuts a consistent 0.3.0 (Priority: P3)

A maintainer prepares the release. Every place that states a version, an author list, an install route, or a DOI agrees with every other place, and nothing in the repository refers to files or modules that no longer exist.

**Why this priority**: These are small edits, but a release with a version mismatch between the package and the citation file produces a wrong Zenodo record that cannot be corrected without a new version.

**Independent Test**: Run a text search for `0.2.0`, `0.2.1`, `_match_faithful`, `not on PyPI`, `not available from PyPI`, and the README TODO comment; confirm every version string that denotes the current release reads `0.3.0`, and the other strings only appear in historical entries (changelog, git history).

**Acceptance Scenarios**:

1. **Given** the repository after the change, **When** the maintainer compares `src/quadmesh/__init__.py`, `pyproject.toml`, `CITATION.cff`, and the new `CHANGELOG.md` entry, **Then** all four say `0.3.0`.
2. **Given** `CHANGELOG.md`, **When** the maintainer reads the top entry, **Then** a `[0.3.0]` entry lists the documentation and cleanup changes, and the existing `[0.2.1]` entry is retained with a note that 0.2.1 was never tagged or published.
3. **Given** `CITATION.cff`, **When** the maintainer reads the `authors` list, **Then** it matches the decision recorded in the Clarifications section of this spec, and the README citation line (`README.md:172`) matches the same list.
4. **Given** `README.md`, **When** the maintainer searches for the CITATION TODO comment, **Then** it is gone.
5. **Given** `docs/algorithm_writeup.md` or its successor, **When** the maintainer searches for `_match_faithful`, **Then** there are no matches.
6. **Given** `AGENTS.md` and `scripts/dev_setup.sh`, **When** the maintainer reads the chilmesh install notes, **Then** they say chilmesh installs from PyPI and that a sibling editable checkout is an optional developer override, matching `pyproject.toml:18`.
7. **Given** `CITATION.cff` and `README.md`, **When** the maintainer searches for `zenodo.`, **Then** every DOI reads `10.5281/zenodo.20350483` (the concept DOI), and `tests/test_release_metadata.py` fails if any other DOI appears.

---

### Edge Cases

- A reader runs `tri2quad` on a mesh with no skeleton layers. The long-form document must say explicitly that this path uses the global matcher with layer priority and fold seams, so the reader is not surprised that the behaviour differs from the per-layer description.
- Feature 057 (sibling dedupe) edits `pyproject.toml` dependencies, `AGENTS.md`, and `docs/MAPPING.md` in the same release window. This feature touches only the `version` line of `pyproject.toml` and the chilmesh install sentences of `AGENTS.md`; the implementer must rebase on 057's edits rather than overwrite them if 057 lands first. Planned order: 056 first, then 057.
- `0.2.1` was never tagged. Bumping to `0.3.0` leaves a gap in the tag series; the changelog note in Story 3 scenario 2 is the only mitigation required. The tag and release ceremony is not part of this feature: it runs once, operator-driven via the `release` skill, after both 056 and 057 land.

## Requirements *(mandatory)*

### Functional Requirements

Documentation of the algorithm:

- **FR-001**: The repository MUST contain one long-form algorithm document at `docs/algorithm.md` that covers, in separate labelled sections: the thesis QuADMESH+ algorithm (Mattioli 2017, chapters 3 and 4); the port as implemented; a thesis-versus-port difference table; the relation to Blossom-Quad (Remacle et al. 2012); and parity status versus MATLAB.
- **FR-002**: The "port as implemented" section MUST describe the actual dispatch in `tri2quad_routine`: per-layer sweep as default when skeleton layers exist; global matcher as fallback for layerless meshes and for elements no layer covers. Every function named MUST carry a pointer to its location in the source.
- **FR-003**: The document MUST label the layer-ordered priority inside the global matcher, the fold-seam forbidden edges, and the augmenting-path fixup as a port-side experiment (operator's words, 2026-10-10: "the hybrid blossom-layers was just an experiment"), retained as the fallback path, and state on which code path each is active. The thesis algorithm MUST be presented as the per-layer sweep (`_quadmesh_plus_per_layer`), which is the default.
- **FR-004**: The Blossom-Quad comparison MUST state that the thesis algorithm has no functional relation to Blossom-Quad (operator, 2026-10-10: "the original thesis did not involve anything related functionally to blossom"), that the shared matching framing applies ONLY to the experimental fallback, and MUST name at least these four differences between that fallback and Blossom-Quad: layer ordering, fold-seam exclusion, steering of residual triangles to the boundary, and absence of point insertion in the default path. It MUST cite Remacle, Lambrechts, Seny, Marchandise, Johnen, Geuzaine (2012), "Blossom-Quad: a non-uniform quadrilateral mesh generator using a minimum cost perfect matching algorithm", International Journal for Numerical Methods in Engineering, 89(9), 1102-1119.
- **FR-005**: The parity section MUST state that `tests/test_parity.py` pins a Python self-baseline, that MATLAB element counts were never captured, and MUST reconcile the "MATLAB-faithful" wording at `docs/MAPPING.md:10` so it reads as intent, not verified result.
- **FR-006**: No document MAY present "faithful" or "matching" as a usable method name. The phrase "faithfulness invariant" for the zero-interior-residual-triangle guarantee remains allowed.
- **FR-007**: The document MUST state the zero-interior-residual-triangle invariant, define an interior residual triangle as a triangle with no domain-boundary edge, and cite `tests/test_no_interior_tris.py` as the gate.

README and package description:

- **FR-008**: The README MUST state the five value statements listed in Story 2 scenario 1 within its opening section, using the same wording as that scenario ("no point insertion by default", not an absolute claim, because `tri2quad(point_insert=True)` exists at `src/quadmesh/tri2quad.py:529`, `:1118`).
- **FR-009**: The README MUST keep the ENPAC quality table and the boundary-layer tail explanation, and MUST link to the long-form document instead of restating algorithm sections.
- **FR-010**: The README status banner MUST drop the hard-coded month stamp or replace it with the release version, and MUST describe the default method in terms consistent with FR-002 and FR-003.
- **FR-011**: The `pyproject.toml` `description` and the GitHub repository description MUST each be one sentence, consistent with the README first value statement.

Hygiene:

- **FR-012**: `src/quadmesh/__init__.py`, `pyproject.toml` (`version` line only; dependency lines belong to feature 057), and `CITATION.cff` MUST all read `0.3.0`, and `CHANGELOG.md` MUST gain an `[0.3.0] - Unreleased` entry with a note that `[0.2.1]` was never tagged. `CITATION.cff` `date-released` keeps its current value (`2026-07-13`) with a YAML comment stating that the `release` skill sets it at tag time; this feature MUST NOT invent a release date. The git tag and GitHub/Zenodo release are NOT part of this feature; they run once, operator-driven via the `release` skill, after features 056 and 057 both land.
- **FR-013**: `CITATION.cff` `authors` MUST list Dominik D. Mattioli first and Ethan J. Kubatko second; `README.md:12-13` and `README.md:172` already name both and MUST remain consistent with the file.
- **FR-014**: The stale TODO comment at `README.md:176` MUST be removed.
- **FR-015**: Every reference to `_match_faithful.py` MUST be removed or replaced with the current module name.
- **FR-020**: `docs/algorithm_writeup.md` MUST be folded into `docs/algorithm.md` as the fallback-path section and then deleted; every link to the old file (`docs/sessions/session-018.md:35` is the only in-repo reference outside `specs/`) MUST be updated or annotated as historical.
- **FR-016**: `AGENTS.md:32` and `scripts/dev_setup.sh` MUST state that chilmesh installs from PyPI (`chilmesh>=1.2.1` per `pyproject.toml:18`); the sibling-checkout path MAY remain as an optional developer override and MUST NOT be a hard failure when the checkout is absent.
- **FR-017**: `CITATION.cff` and every README DOI reference (badge at `README.md:25`, citation at `:172`, note at `:174`) MUST use the concept DOI `10.5281/zenodo.20350483`, and a guard test `tests/test_release_metadata.py` (from the DomI template `templates/tests/test_release_metadata.py.tmpl`, `release-setup` skill section 6) MUST fail when any other DOI appears in those files.

Writing quality (operator scope addition, 2026-10-10):

- **FR-021**: Every human-facing document this feature touches (`README.md`, `docs/algorithm.md`, the `CHANGELOG.md` `[0.3.0]` entry, the `CITATION.cff` `abstract`, the `pyproject.toml` `description`, the GitHub repository description text, `docs/MAPPING.md` prose, and the release-notes draft) MUST pass the writing stack in this order after its content is complete: (1) `write-like-scientist` voice rules 1-10; (2) Golden rule G1-G17, where any hard tell is a defect; (3) `asd-ste100-lens` STE and ADHD layer applied to the whole document, not only summary blocks, keeping method names, invariant wording, and other exact technical terms verbatim, with the Golden rule still overriding the lens; (4) the two-stage tell scan (Haiku scanner, Sonnet corrector) from `write-like-scientist` `references/ai-tells-scan.md`, together with a fact add/drop audit confirming no technical claim was added or lost by the rewrite.

Hard rules (from `quadmesh/AGENTS.md`):

- **FR-018**: No change in this feature MAY alter the behaviour of `tri2quad`; `tests/test_no_interior_tris.py` and `tests/test_parity.py` MUST pass unchanged.
- **FR-019**: `method="quadmesh+"` remains canonical and default, `"layered"` remains the alias, and `"faithful"` and `"matching"` continue to raise `ValueError`.

### Key Entities

- **Long-form algorithm document**: `docs/algorithm.md`, the single in-repo source of truth for how the algorithm works; sections per FR-001; supersedes and absorbs `docs/algorithm_writeup.md` (FR-020).
- **README**: the short public surface; links to the long-form document; carries value statements and the ENPAC quality table.
- **Release metadata**: `pyproject.toml` (version line), `src/quadmesh/__init__.py`, `CITATION.cff`, `CHANGELOG.md`; all must agree on `0.3.0`. GitHub release and Zenodo record are produced later by the joint 056+057 release ceremony.
- **Install notes**: `AGENTS.md`, `scripts/dev_setup.sh`, README install section; all must agree that chilmesh comes from PyPI.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader with no prior exposure to the project can, from the long-form document alone, correctly answer which code path runs by default on a layered mesh and which runs on a layerless mesh (checked by a reviewer reading the document against `tri2quad_routine`).
- **SC-002**: A repository-wide text search for `_match_faithful`, `not on PyPI`, `not available from PyPI`, and the README CITATION TODO returns zero matches outside `CHANGELOG.md` and git history.
- **SC-003**: A repository-wide search for version strings returns `0.3.0` in all four release-metadata files and no `0.2.0` or `0.2.1` outside historical changelog entries.
- **SC-004**: The README opening section (above the table of contents) states all five value statements and grows by at most ten lines; the whole file does not exceed 214 lines (204 today).
- **SC-005**: The full test suite passes with no test modified, demonstrating that the release is documentation and metadata only.
- **SC-006**: `CITATION.cff` validates against the CFF 1.2.0 schema, and the author list equals the README author list.
- **SC-007**: `tests/test_release_metadata.py` exists, pins `10.5281/zenodo.20350483`, and passes.
- **SC-008**: The tell scan reports 0 hard tells (G1-G3, G5-G7, G9-G13, G16-G17) for each document listed in FR-021, and the fact add/drop audit for each document reports zero added and zero dropped technical claims. `python3 ~/.claude/skills/write-like-scientist/scripts/banned_words.py --mode prose <file>` exits 0 for each.

## Assumptions

- The long-form document is written in English prose for human readers; it may use the graph-theory lexicon of the existing write-up but must also carry a plain-language summary at the top.
- The thesis PDF at `docs/Mattioli_Thesis.pdf` is the authoritative description of the 2017 algorithm; chapter and section numbers cited in the document come from it.
- Blossom-Quad is cited from the published 2012 IJNME paper; no attempt is made to benchmark against a Blossom-Quad implementation.
- The operator's statement that the layer-ordered global matching was an experiment is taken as fact; the document records it as such and does not reinterpret the code's intent.
- The chilmesh PyPI question is resolved: chilmesh is on PyPI; `pyproject.toml:18` is correct; `AGENTS.md` and `scripts/dev_setup.sh` are stale (operator statement 2026-10-10).
- `0.2.1` was never released; `0.3.0` is the next version and the first release since `v0.2.0` (2026-07-05). It is a joint release with feature 057 (sibling dedupe); the version jump from 0.2.x to 0.3.0 is the operator's call.
- The feature directory keeps its original name `056-v022-docs-cleanup` even though the version is now 0.3.0 (operator: rename optional).
- Spec-kit artifacts stay in `specs/056-v022-docs-cleanup/` during the work. The single move to DomI `specs/consumers/quadmesh/` runs as feature 057 task T033 after both features implement (`move_specs_to_domi.sh` moves all of `specs/`); this feature does not run the move.
- The constitution principle VI (caveman docs) conflict with the writing-stack requirement is resolved by a constitution amendment in feature 057 task T026a; this feature does not edit `.specify/memory/constitution.md`.

## Out of Scope

- Any change to the conversion algorithm, smoothing, or post-processing.
- Changing which path is default or removing the experimental fallback.
- Tagging, GitHub release, Zenodo publish, PyPI publish (joint 056+057 ceremony, operator-run via the `release` skill).
- `pyproject.toml` dependency changes, matplotlib extras, chilmesh version floor (feature 057).
- Re-running the ENPAC benchmark or regenerating figures.
- Capturing MATLAB ground-truth counts for `tests/test_parity.py`.
- Changes to the CHILmesh, ADMESH, or Valence repositories.
- Changes under `~/Projects/DomI`.

## Clarifications

### Session 2026-10-10

- Q: Is Ethan Kubatko a `CITATION.cff` author? → A: Yes; add as second author (FR-013).
- Q: Where does the long-form algorithm document live? → A: New `docs/algorithm.md`; fold `docs/algorithm_writeup.md` in as the fallback-path section; delete the old file and update links (FR-001, FR-020).
- Q: Bump version and cut a release now, or docs-only? → A: Version is 0.3.0 (not 0.2.2), a joint release with feature 057. This feature sets version strings to 0.3.0 and notes in the changelog that 0.2.1 was never tagged. Tag and release happen once, operator-run via the `release` skill, after both features land (FR-012).
- Q: How to present the layer-ordered global matching and fold-seam experiment? → A: Thesis algorithm = per-layer sweep (`_quadmesh_plus_per_layer`), the default. Hybrid global matching with layer priority and fold seams = experiment, retained as fallback. Blossom-Quad's shared framing applies only to the experimental fallback; the thesis has no functional relation to Blossom-Quad (FR-003, FR-004).
- Scope addition (operator, same session): all human-facing documents touched get the full writing stack including the STE and ADHD lens on the whole document, then a Haiku/Sonnet tell scan with fact audit (FR-021, SC-008).
- Q: DOI verification? → A: Concept DOI is `10.5281/zenodo.20350483`; current `10.5281/zenodo.20351165` is a version DOI. Fix `CITATION.cff` and README to the concept DOI and add the concept-DOI guard test from `release-setup` section 6. No network check needed (FR-017, SC-007).
- Resolved outside the question set: chilmesh is on PyPI; `pyproject.toml:18` is correct; `AGENTS.md:32` and `scripts/dev_setup.sh` are stale (FR-016).
