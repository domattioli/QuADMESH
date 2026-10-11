<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# Research: feature 056 (v0.3.0 docs and cleanup)

All clarifications were resolved by the operator on 2026-10-10. This file records the decisions and the code evidence the implementer needs to write `docs/algorithm.md` without re-deriving it.

## Decision 1: Which code path is "the algorithm"

- Decision: the thesis algorithm is the per-layer sweep `_quadmesh_plus_per_layer`; it is the default when skeleton layers exist. The hybrid layer-priority global matcher is an experiment, retained as the fallback.
- Rationale: operator statement; code agrees. `tri2quad_routine` (`src/quadmesh/tri2quad.py:995`) maps `"quadmesh+"` to `"layered"` (`:1054-1057`), raises on `"faithful"`/`"matching"` (`:1059-1063`), calls `_quadmesh_plus_per_layer` when `n_layers > 0` (`:1065-1081`), else `_layer_priority` + `_sweep_pairs` + `_match_tris_to_quads` (`:1083-1093`). Inside the per-layer loop, uncovered elements go to `_match_tris_to_quads` without priority (`:960-971`).
- Alternatives considered: describing the global matcher as the main algorithm (current `docs/algorithm_writeup.md` framing). Rejected: contradicts the default path.

## Decision 2: Document home

- Decision: new `docs/algorithm.md`; fold `docs/algorithm_writeup.md` sections 1-8 into it as the fallback section; delete the old file.
- Links to update: `docs/sessions/session-018.md:35` (historical session note; annotate rather than rewrite). No references in `README.md`, `AGENTS.md`, `src/`, or `docs/MAPPING.md`.

## Decision 3: Version and release

- Decision: 0.3.0 across `src/quadmesh/__init__.py:4`, `pyproject.toml:7`, `CITATION.cff` `version`, `CHANGELOG.md` new entry. No tag. `CITATION.cff` `date-released` unchanged (`2026-07-13`) plus a comment; the `release` skill sets it. `CHANGELOG.md` keeps `[0.2.1] - 2026-07-13` and adds a note that it was never tagged (tags present: `v0.1.0`, `v0.1.1`, `v0.2.0`).
- Joint release with feature 057; ceremony via `release` skill, operator-run.

## Decision 4: Blossom-Quad framing

- Decision: comparison applies only to the experimental fallback. Thesis algorithm has no functional relation to Blossom-Quad.
- Citation: Remacle, J.-F., Lambrechts, J., Seny, B., Marchandise, E., Johnen, A., Geuzaine, C. (2012). Blossom-Quad: a non-uniform quadrilateral mesh generator using a minimum cost perfect matching algorithm. International Journal for Numerical Methods in Engineering, 89(9), 1102-1119.
- Differences to state: layer ordering (`_layer_priority`, `:668-689`); fold-seam forbidden edges (`_sweep_pairs` returns them, matcher skips at `:149-150`); residuals steered to the boundary (interior saturation, augmenting path `:184`); no point insertion on the default path (`_point_insert_tri_pairs` exists at `:529` and is gated by `point_insert` and `method == "layered"` at `:1118`; the document must state this precisely rather than claim "never inserts points"); greedy plus augmenting-path rather than min-cost perfect matching.

## Decision 5: DOI

- Decision: concept DOI `10.5281/zenodo.20350483`. Replace `10.5281/zenodo.20351165` at `CITATION.cff:21`, `README.md:25` (badge, two occurrences in one line), `README.md:172`, `README.md:174`.
- Guard test: copy `~/Projects/DomI/templates/tests/test_release_metadata.py.tmpl` to `tests/test_release_metadata.py`, set `CONCEPT_DOI`. Per `release-setup` SKILL.md section 6 the test fails when `CITATION.cff` or the README names another DOI, when `.zenodo.json` carries a DOI field (no `.zenodo.json` exists here), or when the README lacks a `doi.org` link to the concept DOI. Read the template before copying; adapt the `.zenodo.json` branch if it assumes the file exists.

## Decision 6: chilmesh install notes

- Decision: chilmesh is on PyPI; `pyproject.toml:18` (`chilmesh>=1.2.1`) is correct. Fix `AGENTS.md:32` ("CHILmesh is not available from PyPI") and `scripts/dev_setup.sh:5-7,19-30` (hard error without sibling checkout). Keep the sibling editable install as an opt-in developer override.
- Do not touch the dependency floor: feature 057 owns `pyproject.toml` dependency lines.

## Decision 7: Writing stack scope

- Decision (operator): voice rules 1-10, Golden rule G1-G17, STE+ADHD lens on whole documents (overriding the lens's default scope of summary blocks only), Haiku/Sonnet tell scan with fact add/drop audit. Applies to: `README.md`, `docs/algorithm.md`, `CHANGELOG.md` `[0.3.0]` entry, `CITATION.cff` abstract, `pyproject.toml` description, GitHub repo description, `docs/MAPPING.md` prose, release-notes draft.
- Tooling: `~/.claude/skills/write-like-scientist/SKILL.md` (stack order, procedure), `references/ai-tells-scan.md` (scanner and corrector prompts; hard vs weighted cue table), `scripts/banned_words.py --mode prose`; `~/.claude/skills/asd-ste100-lens/SKILL.md` (five-step protocol, step 4 verifies zero factual loss).
- Constitution VI (caveman docs) conflicts for human-facing prose; operator ruling wins; amendment lands in feature 057 task T026a, not here.

## Facts for the thesis section

- Thesis PDF: `docs/Mattioli_Thesis.pdf`. Chapters 3 and 4 cover layer construction, IE/OE/IV/OV sets, fold handling (Figure 4.1, section 4.1), boundary-layer ordering (section 4.2). The implementer must verify chapter and section numbers against the PDF before citing them; existing docstrings cite "Ch 4.1", "4.2", "§3.2.2" (`src/quadmesh/tri2quad.py:669-676, 705-711`; `docs/algorithm_writeup.md:60-61`).

## Current public descriptions

- `pyproject.toml:8` description: "QuADMESH+: Quadrangular ADvanced Mesh generator. Python port of MATLAB QuADMESH library."
- GitHub repository description: "The Quad sequel to ADMESH".
- README tagline (`README.md:6`): "A Quadrangular ADvanced, automatic unstructured MESH generator for 2D shallow-water models."

## Implementer corrections (T005, 2026-10-10)

Line numbers above still match `src/quadmesh/tri2quad.py`. Three facts differ from Decisions 1 and 4:

- `point_insert` defaults to `True` (`tri2quad.py:1003`), so `_point_insert_tri_pairs` runs by default on lone residual triangles (`:1118`). "No point insertion by default" is therefore not accurate for `tri2quad()` as shipped.
- The default per-layer path also adds and moves points: `route_leftover_tri` (`_tri_removal.py:308`) calls `edge_bisection` (`:143`) and `edge_insertion` (`:260`), which add points, and `edge_removal` (`:121`), which collapses a boundary edge when `can_remove_edges=True` (the default). These are the thesis section 4.2.2 removal operations.
- Fold-seam (flagged-edge) exclusion is also active on the default path: `match_layer_heuristic` (`_match_quadmesh_plus.py:220`) receives the flagged pairs (`tri2quad.py:888-917`). Flagged edges are thesis section 3.2.1 (Figure 3.19) and section 4.1 (Figure 4.1), so they are thesis behaviour, not a port-side experiment. The experiment is the global matcher with layer priority and augmenting-path fixup.

`docs/algorithm.md` and `README.md` use the accurate wording; the spec FR-008 phrase is replaced by "pairing inserts no points" plus the `point_insert` and routing exceptions.
