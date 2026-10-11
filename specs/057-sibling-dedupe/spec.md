<!-- provenance: author=domattioli model=claude-opus-5-5 effort=low date=2026-10-10 skill=speckit-specify repo=quadmesh session=unknown -->
# Feature Specification: Remove functionality duplicated in sibling packages

**Feature Branch**: none (spec-only turn; working branch `development`)
**Created**: 2026-10-10
**Status**: Draft
**Input**: User description: "Remove QuADMESH functionality redundant with sibling packages ADMESH, CHILmesh, Valence; declare them as dependencies and call their APIs instead."

## Context

QuADMESH 0.2.1 (`pyproject.toml:7`) depends on `chilmesh>=1.2.1` (`pyproject.toml:18`). The sibling checkouts in `/Users/domattioli/Projects/MADMESHing/` are CHILmesh 1.5.0 (`CHILmesh/pyproject.toml:7`), ADMESH, distributed as `admesh2D` 1.0.0 (`ADMESH/pyproject.toml:6-7`), and Valence, distributed as `valence-domains` 0.10.0 (`Valence/pyproject.toml:6-7`). Several QuADMESH modules re-implement logic that a sibling now provides publicly. Some of that logic was written before the sibling fix existed. For example, `_balendran_smooth` (`src/quadmesh/post_process.py:44`) works around chilmesh#173, and CHILmesh has since fixed that bug in `direct_smoother` (`CHILmesh/src/chilmesh/CHILmesh.py:2287-2289`).

This feature removes such duplicates, or turns them into thin delegations, while it keeps the algorithm output and the public API stable.

Out of scope: README, CITATION, version-string hygiene, and doc cleanup. A parallel feature, `specs/056-v022-docs-cleanup`, owns that work. This feature touches `docs/MAPPING.md` only to record new delegation rows.

## Clarifications

### Session 2026-10-10

- Q: How should ADMESH be declared? → A (superseded 2026-10-10; see FR-011): As an optional extra `[admesh]` (`admesh2D`) for the `quad_prep` pre-smoothing step (`ADMESH/src/admesh/quad_prep.py:57`). It is not a hard dependency.
- Q: How should Valence be declared? → A (superseded; see next item): Valence is the source of the test meshes. Add `valence-domains` to the `[dev]` extra and resolve fixture names from its manifest now. Draft a request for a Valence `fetch_mesh` API (text below, not filed). Keep the local fetch and hash code until that API lands.
- Q2 superseded (operator ruling 2026-10-10): Valence is proprietary, and its code must never land on a consumer machine. Do not add `valence-domains` to any extra, including `[dev]`. Keep the existing token-gated fetch in `tests/_mesh_provision.py`. The draft request below is for an authenticated remote API (an HTTP endpoint that serves mesh files and hashes). No client library ships. Leak risk: `valence-domains` 0.4.1 to 0.4.3 is public on PyPI, and `admesh2D` hard-depends on `valence-domains>=0.4.2` (`ADMESH/pyproject.toml:27`). This means the `[admesh]` extra would install Valence code; see FR-011.
- Q: What is the deprecation window? → A: Warn in 0.3.0, remove in 0.4.0.
- Q: Do missing upstream APIs (partial rows) block this release? → A: No. Track each one in `docs/MAPPING.md` under `downstream-api`.
- Q: What is the version target? → A: 0.3.0, released jointly with feature 056. Feature 056 owns the version strings, `CHANGELOG.md`, `README.md`, `CITATION.cff`, `docs/algorithm*.md`, and `src/quadmesh/__init__.py` `__version__`. Feature 057 owns the dependency lines in `pyproject.toml`. Feature 056 is implemented first.
- Q: What happens if the FEM parity check (SC-002) fails? → A: Keep the local `_balendran_smooth`.
- Scope addition (operator): Agent-only documents and personal data must stay out of the PyPI and Zenodo artifacts. See "Release-artifact hygiene inventory" and FR-013 to FR-019.

## Redundancy inventory

Classes: **redundant** means a sibling provides an equivalent public API and QuADMESH can call it directly. **partial** means a sibling covers part of the behavior, so delegation needs either a sibling API change (label `downstream-api`) or a parity check first. **unique** means the logic is QuADMESH algorithm logic or test policy, so QuADMESH keeps it.

| # | QuADMESH item | Sibling equivalent | Class | Notes |
|---|---|---|---|---|
| 1 | `.14` read and write in the CLI: `CHILmesh.read_from_fort14` / `write_to_fort14` (`src/quadmesh/cli.py:55,74`) | `CHILmesh/src/chilmesh/CHILmesh.py:2844,1525` | already delegated | No QuADMESH-owned parser exists. ADMESH (`ADMESH/src/admesh/fort14.py:116,322`) and Valence (`Valence/packages/valence_domains/fort14.py:119`) each have their own parser, but QuADMESH should not switch to them. |
| 2 | `remove_unused_vertices` (`src/quadmesh/remove_unused.py:15`) | `CHILmesh.submesh(all_elem_ids)` compacts and renumbers vertices (`CHILmesh.py:163`, added in 1.1.0 per `CHILmesh/CHANGELOG.md:177`) | redundant | Callers must accept a full rebuild (layers and adjacency). Pass `compute_layers=False` where the old path skipped them. |
| 3 | `_balendran_smooth` (`src/quadmesh/post_process.py:44-88`), which is the core of `fem_smoother` | `CHILmesh.direct_smoother` with interior RHS F=0 after the #173 fix (`CHILmesh.py:2276,2287-2289,2350`), reached through `smooth_mesh('fem')` (`CHILmesh.py:1672,1705`) | redundant, gated on parity | Replace it only if quality stats on the fixture set match within tolerance (see SC-002). The docstring at `post_process.py:47-55` documents the bug that CHILmesh fixed. |
| 4 | `fem_smoother` public wrapper (`post_process.py:263`) | as row 3 | unique (keep as a thin wrapper) | Public API with QuADMESH semantics: compacts first, short-circuits after one FEM pass (#107), reverts on exception. The name stays. |
| 5 | `two_part_smoother` deprecated alias (`post_process.py:318`) | none | unique (deprecated) | It already emits `DeprecationWarning`. MADMESHing `compare.py` still imports it (`post_process.py:321-322`). Removal follows the deprecation window (Q3). |
| 6 | `truss_smoother` (`post_process.py:90`), quad-to-4-tri spring smoother | `chilmesh.optimize_with_admesh_truss[_arrays]` (`CHILmesh/src/chilmesh/admesh_warmstart.py:409,563`) and vendored ADMESH truss (`CHILmesh/src/chilmesh/_vendor_admesh_truss.py:4-16`) | partial | The upstream path is triangle-only and SDF-driven (`CHILmesh.py:1680-1683`). QuADMESH runs it on quads through a centroid fan with a frozen edge set. Delegation needs a CHILmesh quad- or mixed-element truss entry point (`downstream-api`). |
| 7 | `_topology.ccw_edges_around_vert`, `merge_tri_pair(s)` (`src/quadmesh/_topology.py:9-24`) | `CHILmesh.ccw_edges_around_vert` (`CHILmesh.py:882`), `chilmesh.quad_from_tri_pair` / `quads_from_tri_pairs` (`CHILmesh/src/chilmesh/mesh_topology.py:126,200`) | redundant (shim layer) | These are one-line adapters over public CHILmesh calls. Inline them at the call sites, or keep the module as a private shim. They are not public API. |
| 8 | `_build_tri_adjacency` (`src/quadmesh/_match_quadmesh_plus.py:22-36`) | CHILmesh `adjacencies["Edge2Elem"]` via `CHILmesh(compute_adjacencies=True)` (already used at `src/quadmesh/identify_edges.py:84,97`) | partial | It runs on a raw `(N,3)` array, not on a mesh. Delegation means building a submesh or adjacency per layer, which can cost more. Replace it only if benchmark parity holds; otherwise keep it. |
| 9 | `create_quad_domain` polygon mask through matplotlib `Path` (`src/quadmesh/create_quad_domain.py:15,46-51`) | `admesh._stages.in_polygon.in_polygon` (`ADMESH/src/admesh/_stages/in_polygon.py:21`); `CHILmesh.submesh` (`CHILmesh.py:163`) | partial | The selection logic is QuADMESH-specific: any vertex inside selects the element, and the point list stays unchanged so the result aligns with the parent mesh in `tri2quad(parent=...)`. `submesh` renumbers vertices, so it is not a drop-in. Taking ADMESH only for `in_polygon` would add a heavy dependency. Recommendation: keep it, and declare `matplotlib` explicitly, because today it arrives only transitively through chilmesh (`CHILmesh/pyproject.toml:43`). |
| 10 | Quality stats: `compute_quality_stats` / `format_quality_report` (`src/quadmesh/quality_report.py:10,32`) | `chilmesh.element_quality(metric="skew")` (`CHILmesh/src/chilmesh/quality.py:219`), already called | already delegated (keep the wrapper) | Public API. The summary dict and the 0.3 "bad" threshold are QuADMESH reporting policy. |
| 11 | Layers and skeletonization: `identify_edges_in_layer` (`src/quadmesh/identify_edges.py:51`) | CHILmesh `layers["OE"/"IE"/"OV"/"IV"]` (consumed at `identify_edges.py:64-88`); `chilmesh.layer_paths.paths_on_outer_vertices` (`CHILmesh/src/chilmesh/layer_paths.py:51`) | unique | Layer peeling already comes from CHILmesh. Per-layer edge selection is QuADMESH+ algorithm logic. |
| 12 | Tri-to-quad core: `tri2quad.py`, `_match_quadmesh_plus.py`, `_tri_removal.py`, `_recombine.py` | `MutableMesh.merge_elements`, `swap_edge`, `split_edge` (`CHILmesh/src/chilmesh/mutations.py:341,277,109`) | unique | Algorithm core. Wiring `merge_elements` is reserved for `tri2quad(aggressive=)` (AGENTS.md; `docs/MAPPING.md:95`). Out of scope here, so the zero-interior-triangle invariant is not put at risk. |
| 13 | Post-process topology ops: `doublet_collapse` (`src/quadmesh/doublet_collapse.py:25`), `quad_vertex_merge` (`src/quadmesh/quad_vertex_merge.py:26`), `cleanup_boundary_quads` (`src/quadmesh/cleanup_boundary_quads.py:115`) | `MutableMesh.collapse_edge`, `remove_vertex` (`mutations.py:483,393`) are triangle-oriented primitives | unique | No quad-aware equivalent exists upstream. |
| 14 | `repair.py` (`_fix_bowties` :90, `_ear_clip` :157, `_merge_tri_pairs_to_quads` :222, `repair_mesh` :437, `repair_chilmesh` :463) | none found; `quads_from_tri_pairs` covers only pair merging (`mesh_topology.py:200`) | partial (`_merge_tri_pairs_to_quads` only); rest unique | Public `repair_*` stays. Its internal tri-pair merge can call `chilmesh.quads_from_tri_pairs` if the vertex order matches. |
| 15 | `quadmesh.validation` package (validator, predicates, broadphase, fixtures; `src/quadmesh/validation/__init__.py:1-5`) | none in CHILmesh (no `validate` or bowtie code under `CHILmesh/src/chilmesh/`) | partial (upstream gap) | `validation/__init__.py:4-5` says promotion to `chilmesh.validate` is tracked at issue #142. This needs a CHILmesh API (`downstream-api`). Until then it stays. |
| 16 | Plotting: `scripts/render_quadmesh.py` (raw matplotlib, `:15-21,156,190`) | `chilmesh.chilplotting.plot`, `plot_layer`, `plot_quality` (`CHILmesh/src/chilmesh/chilplotting.py:397,535,565`) | partial | Mesh drawing can delegate. Overlays specific to the QuADMESH diagnosis (legend, highlighted elements) stay. Script only, no package API. |
| 17 | Fixture fetch and hash check: `tests/_mesh_provision.py` (GitHub API download `:57`, git-blob SHA-1 `:51`, pinned `MANIFEST` `:34-40`, chilmesh data fallback `:23`); `scripts/fetch_fixtures.py:14-19` | Valence: manifest loader (`Valence/packages/valence_domains/manifest.py:39-49`), `Mesh.path` / `compute_content_uid` SHA-256 (`Valence/packages/valence_domains/schema.py:382,402`) | partial (upstream gap) | Valence resolves meshes only from a local `base_dir` or `registry_data`. It has no authenticated remote fetch, and it hashes with canonical SHA-256 instead of git-blob SHA-1. Delegation needs a Valence `fetch_mesh(name) -> Path` API with verification (`downstream-api`). Test-only. |
| 18 | ADMESH as a whole | `admesh.quad_prep.smooth_for_quadrangulation` (`ADMESH/src/admesh/quad_prep.py:57`) is a pre-quadrangulation tri smoother | none redundant | QuADMESH duplicates no ADMESH function. `quad_prep` is new optional pre-processing, not a duplicate. |

Summary: 3 redundant (rows 2, 3, 7), 7 partial (rows 6, 8, 9, 14, 15, 16, 17), and the rest are unique or already delegated. ADMESH has no redundancy with QuADMESH.

## Release-artifact hygiene inventory

Canon: DomI `skills/release-integrity/policy/release-ignore.toml` `[baseline]`, version 1.5.0. The repo extends it in `.release-ignore.toml`, and the canon generates the marker blocks in `.gitattributes`, `.zenodoignore`, and `MANIFEST.in`. The Zenodo snapshot and the GitHub tarball come from `git archive`, so `.gitattributes export-ignore` controls them. PyPI is controlled by `MANIFEST.in` (sdist) and `[tool.setuptools.packages.find] where=["src"]` (wheel, `pyproject.toml:28-30`).

| # | Path or item | Tracked? | PyPI (sdist/wheel) | Zenodo/GitHub (`export-ignore`) | Finding |
|---|---|---|---|---|---|
| H1 | Generated ignore blocks | yes | n/a | n/a | Stale against the canon. The blocks lack `.specify/`, `CONTEXT.md`, `.projectmem/`, `AGENT.md`, `GEMINI.md`, `CLAUDE.local.md`, `.agents/`, `.codex/`, `.gemini/`, `.cursor/`, `.cursorrules`, `.windsurfrules`, `.aider*`, `.mcp.json`, `.github/copilot-instructions.md`, and `CLAUDE.md` (`.gitattributes:5-25`; `MANIFEST.in` block). The `MANIFEST.in` block also has no `# <<< release-ignore:end` marker, unlike `.gitattributes:25` and `.zenodoignore`, so the generator's `--check` mode may fail on it. |
| H2 | `.claude/` (`AI-USAGE.md`, `settings.json`) | yes | excluded | excluded | OK. |
| H3 | `AGENTS.md`, `.domi-pin`, `.release-ignore.toml`, `.zenodoignore` | yes | excluded | excluded | OK. |
| H4 | `.specify/`, `specs/` (spec-kit, untracked now) | no | not included | `specs/` excluded; `.specify/` missing | `.specify/` must be added through regeneration (H1). Both folders move to DomI at the end of the feature. |
| H5 | `docs/sessions/` (36 session logs) | yes | excluded (`prune docs`) | excluded | OK for artifacts. agent-doc-sweep classes them `review`, because `.github/labels.yml` references them. Relocating them to DomI is a separate operator decision. |
| H6 | `docs/speckit-quadmesh-plus-layers-wnat-audit.md` | yes | excluded | excluded (`docs/speckit-*`) | OK. |
| H7 | `experiments/layer_matching_bound/` (6 files) | yes | not in sdist (only `src` plus explicit includes) | **shipped** | This is an agent experiment. Add it to `.release-ignore.toml` `[extend]`. |
| H8 | `facts.yml` (doc-vs-reality fact manifest, DomI spec-019) | yes | not included | **shipped** | Agent tooling. Add it to `[extend]`. |
| H9 | `scripts/instructions_on_start.sh` | yes | excluded | excluded | OK. |
| H10 | `scripts/onstart_local.sh` | yes | excluded (`prune scripts`) | **shipped** | Agent session hook. Add it to `[extend]`. |
| H11 | `archive/`, `videos/` | yes | excluded | excluded | OK. |
| H12 | `dist/` (stale 0.1.1 builds) | no (`.gitignore:8`) | n/a | not in `git archive` | OK. The 0.1.1 sdist holds only `src/`, `LICENSE`, `README.md`, `MANIFEST.in`, `PKG-INFO`, `pyproject.toml`, and `setup.cfg`, and the wheel holds only `quadmesh/` and its dist-info. Rebuild and verify these for 0.3.0. |
| H13 | `.projectmem/` | not in this repo (it lives in the parent `MADMESHing/`) | n/a | n/a | Covered after regeneration (H1). |
| H14 | `.claude/handoffs/` | not present | n/a | n/a | Already in the global gitignore. Covered by `.claude/`. |
| P1 | Personal path: `docs/benchmarks/refuse-boundary-merge-real-meshes.md:8` (`/home/user/Valence/...`) | yes | excluded (`prune docs`) | **shipped** | This is a generic cloud-sandbox path, not the operator's home directory. Replace it with a relative or placeholder path. |
| P2 | Personal path: `scripts/exp_refuse_boundary_merge.py:156` (default `/home/user/Valence/registry_data/meshes`) | yes | excluded | **shipped** | Replace it with a path relative to the sibling checkout, or with the Valence manifest lookup (FR-010). |
| P3 | Sandbox path: `scripts/instructions_on_start.sh:442` (`/home/claude/.ssh/...`) | yes | excluded | excluded | OK. The file is an agent script and is already ignored. |
| P4 | Contact emails: `LICENSE:138`, `README.md:190,198` | yes | shipped | shipped | Intentional public contacts (relay addresses and a co-author's institutional email). Keep them. `README.md` belongs to feature 056. |
| P5 | `/Users/domattioli` in tracked files outside the agent paths | none found | — | — | Scanned with `git ls-files` plus a grep for `/Users/`, `/home/<name>`, and email patterns. |

Release-integrity tooling (`release_ignore.py verify`) checks the real artifact file lists. Implementation runs it against a fresh `python -m build` and a fresh `git archive`.

## Valence API request (draft, not filed)

Title: `request: authenticated remote API serving registry meshes and hashes` (label `downstream-api`)

> Valence is proprietary, and no Valence code may be installed on consumer machines. QuADMESH tests download `.14` fixtures through the authenticated GitHub contents API and verify a pinned git-blob SHA-1 (`quadmesh/tests/_mesh_provision.py:23-60`). Please provide a token-gated HTTP endpoint with two routes: `GET /meshes/{name}`, which returns the file bytes, and `GET /meshes/{name}/hash`, which returns the canonical SHA-256 `content_uid` (`schema.py:402`). Errors: 401 when the token is missing or invalid, 404 for an unknown name. Consumers call the endpoint with plain HTTP (`urllib`), so no client library ships. When the endpoint exists, QuADMESH, ADMESH, and CHILmesh can swap their GitHub-contents fetch for it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Smoothing and compaction delegate to CHILmesh (Priority: P1)

A QuADMESH user runs `run_pipeline` or `post_process` and gets the same quad mesh as before. The FEM smoothing and unused-vertex compaction now run in CHILmesh, so fixes made there (such as #173) reach QuADMESH without a local copy.

**Why this priority**: This removes the largest duplicated numerical code (`_balendran_smooth`, `remove_unused_vertices`). It is also the change most likely to shift output, so it needs a parity gate.

**Independent Test**: Run the full pytest suite, including `tests/test_no_interior_tris.py`, `tests/test_smoother.py`, `tests/test_quality_regression.py`, and `tests/test_parity.py`, against the delegated implementation. Compare `compute_quality_stats` before and after on every available fixture.

**Acceptance Scenarios**:

1. **Given** a triangular fixture mesh, **When** `run_pipeline` runs with defaults, **Then** zero interior residual triangles remain, and the element count and quality stats match the pre-change baseline within tolerance.
2. **Given** existing code that calls `quadmesh.fem_smoother(mesh, n_iter=3)`, **When** it runs, **Then** it works unchanged and emits no new warning.

---

### User Story 2 - Thin internal shims replaced with direct sibling calls (Priority: P2)

A maintainer reading `src/quadmesh/` finds no private wrapper around a public CHILmesh call unless that wrapper adds QuADMESH semantics.

**Why this priority**: Lower risk than P1 and mostly mechanical.

**Independent Test**: Grep for the inventory rows marked redundant (row 7, and row 14 internals). Each one either calls the sibling API directly or has a recorded reason to stay.

**Acceptance Scenarios**:

1. **Given** the refactor is done, **When** the test suite runs, **Then** all tests pass with no change in output.

---

### User Story 3 - Upstream gaps tracked, not hidden (Priority: P2)

For each "partial" row, the maintainer can see which sibling API is missing and where the gap is tracked. QuADMESH keeps a working local implementation until the sibling API ships.

**Why this priority**: Without tracking, the duplicates come back or stay forever.

**Independent Test**: `docs/MAPPING.md` gains a delegation table that lists every partial row with its sibling, its gap, and its `downstream-api` reference.

**Acceptance Scenarios**:

1. **Given** a partial row (for example validation, fixture fetch, or the quad truss smoother), **When** a maintainer looks it up in `docs/MAPPING.md`, **Then** the entry names the missing sibling API and the local fallback.

---

### User Story 4 - Dependencies declared explicitly (Priority: P3)

A user who installs `quadmesh` gets every runtime import it needs, declared in `pyproject.toml`, with lower bounds that include the sibling APIs it calls.

**Independent Test**: In a clean virtual environment, `pip install .` followed by `python -c "import quadmesh; quadmesh.run_pipeline"` succeeds. Every runtime import resolves to a declared dependency.

**Acceptance Scenarios**:

1. **Given** the `chilmesh` lower bound is raised to a version that includes the #173 fix and `submesh`, **When** a lower version is installed, **Then** pip refuses the install, and QuADMESH does not fail at runtime.

### User Story 5 - Release artifacts carry no agent files or personal data (Priority: P2)

A PyPI or Zenodo user downloads 0.3.0 and finds only library code, license, and readme (PyPI), or the human-facing repository (Zenodo). Agent instructions, spec-kit files, session logs, experiments, and personal paths are absent.

**Independent Test**: Build the sdist and wheel, list `git archive HEAD`, and run `release_ignore.py verify` on all three. Grep the shipped files for absolute home paths.

**Acceptance Scenarios**:

1. **Given** a fresh build, **When** `release_ignore.py verify` runs, **Then** it exits 0.
2. **Given** a `git archive` listing, **When** it is searched for `experiments/`, `facts.yml`, `.specify/`, `AGENTS.md`, or `docs/sessions/`, **Then** none is found.

### Edge Cases

- The parity check for the CHILmesh FEM smoother fails on some fixture, for example because boundary pinning or the kinf default differs. In that case `_balendran_smooth` stays, and the gap is recorded as partial.
- On a mixed-element (padded-triangle) connectivity array, `submesh` must keep the padded triangle rows (`[v0,v1,v2,v2]`) intact.
- `submesh` rebuilds layers by default (`CHILmesh.py:166`). The replacement must not add layer-peeling cost inside the post-process loop.
- Valence-dependent tests still skip cleanly when no token is set (`tests/conftest.py:90-124`).
- External callers (MADMESHing `compare.py`) import `two_part_smoother`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `tri2quad` MUST leave zero interior residual triangles on every fixture that `tests/test_no_interior_tris.py` exercises. The feature MUST NOT modify that test's assertions.
- **FR-002**: `method="quadmesh+"` MUST stay the default. `"layered"` MUST stay an alias, and `"matching"` and `"faithful"` MUST still raise `ValueError`.
- **FR-003**: Every name in `quadmesh.__all__` (`src/quadmesh/__init__.py:12-21`) and the lazy names `create_quad_domain` and `run_pipeline` (`__init__.py:23-30`) MUST stay importable with unchanged signatures in this release.
- **FR-004**: `remove_unused_vertices` MUST delegate vertex compaction to CHILmesh (`submesh` or an equivalent public API). The module may remain as a private shim.
- **FR-005**: `fem_smoother(method="fem")` MUST delegate the FEM solve to CHILmesh `smooth_mesh('fem')` or `direct_smoother`, provided SC-002 passes. If SC-002 fails, the local solver stays and the gap is recorded per FR-008.
- **FR-006**: `_topology.py` helpers and any other wrapper that only forwards to a public CHILmesh API MUST be inlined or reduced to a documented pass-through.
- **FR-007**: Removing a public function, or changing its behavior visibly, MUST emit a `DeprecationWarning` in 0.3.0 and MUST NOT remove the function before 0.4.0. `two_part_smoother` keeps its warning in 0.3.0; the warning text MUST name 0.4.0 as the removal version.
- **FR-008**: Each partial inventory row MUST get an entry in `docs/MAPPING.md` that names the sibling, the missing API, and the `downstream-api` label. This feature does not file the issues.
- **FR-009**: `pyproject.toml` MUST declare every package that QuADMESH imports at runtime. The `chilmesh` lower bound MUST be raised to the lowest version that includes every API the code calls. `matplotlib` MUST be declared, because `create_quad_domain.py:15` imports it.
- **FR-010**: No Valence package (`valence-domains`) may be a dependency of any kind (runtime, extra, or dev). Fixture provisioning keeps the existing token-gated GitHub fetch with SHA-1 verification (`tests/_mesh_provision.py`) unchanged, until the authenticated remote API (draft below) exists.
- **FR-011**: The `[admesh]` extra and `run_pipeline(pre_smooth=...)` are deferred. `admesh2D` hard-depends on `valence-domains` (`ADMESH/pyproject.toml:27`), so the extra would install Valence code (FR-010). Revisit only once ADMESH drops or makes optional that dependency. Default output does not change.
- **FR-012**: Unique rows (11, 12, 13, and the public parts of 14) MUST NOT change.
- **FR-013**: The generated blocks in `.gitattributes`, `.zenodoignore`, and `MANIFEST.in` MUST be regenerated from the current release-ignore canon (H1). The `release_ignore.py generate --check` drift gate MUST pass.
- **FR-014**: `.release-ignore.toml` `[extend].exclude` MUST add `experiments/`, `facts.yml`, and `scripts/onstart_local.sh` (H7, H8, H10).
- **FR-015**: `release_ignore.py verify` MUST report zero leaks on a fresh `git archive HEAD` listing and on the sdist and wheel built by `python -m build`.
- **FR-016**: Tracked files that ship in any artifact MUST NOT contain personal or sandbox absolute paths (P1, P2). Intentional public contacts (P4) are allowed.
- **FR-017**: The wheel MUST contain only `quadmesh/**` and its `*.dist-info`. The sdist MUST contain only `src/**`, `LICENSE`, `README.md`, `pyproject.toml`, `MANIFEST.in`, `PKG-INFO`, and `setup.cfg`.
- **FR-018**: This feature MUST NOT edit `README.md`, `CITATION.cff`, `CHANGELOG.md`, `docs/algorithm*.md`, or `src/quadmesh/__init__.py` `__version__`, because feature 056 owns them. Of `pyproject.toml`, it edits only `dependencies` and `[project.optional-dependencies]`.
- **FR-020**: Every human-facing text this feature writes or edits MUST pass through the writing stack, in this order, after its content is final: (1) `write-like-scientist` voice rules 1-10; (2) Golden rule G1-G17; (3) `asd-ste100-lens` STE + ADHD layers, keeping technical terms verbatim (the Golden rule wins on conflict); (4) a tell scan last (Haiku scan plus Sonnet correction per `write-like-scientist/references/ai-tells-scan.md`, with a fact add/drop audit). This covers `docs/MAPPING.md` prose, deprecation messages and touched docstrings, the drafted Valence `fetch_mesh` request, `docs/benchmarks/refuse-boundary-merge-real-meshes.md`, and `CONTRIBUTING.md` or `tests/fixtures/README.md` if edited. `AGENTS.md` is agent-facing and exempt.
- **FR-019**: Relocating `docs/sessions/` to DomI is out of scope. It is recorded as a follow-up because `.github/labels.yml` references those files (H5).

### Key Entities

- **Inventory row**: a QuADMESH item, its sibling equivalent, its class (redundant, partial, or unique), and its disposition.
- **Sibling API gap**: a missing sibling API that blocks delegation, tracked under the `downstream-api` label.

## Success Criteria *(mandatory)*

- **SC-001**: The full test suite passes, and the no-interior-triangle gate is exercised (not skipped) on at least the chilmesh-bundled meshes.
- **SC-002**: On every available fixture, the post-change `compute_quality_stats` mean and min differ from the baseline by at most 1e-6 (absolute), and the element count is identical.
- **SC-003**: Net lines of code in `src/quadmesh/` drop by at least 20 (the `_topology.py` deletion plus the `remove_unused_vertices` shim). If the T006 parity check passes, the drop is at least 60 (adding `_balendran_smooth`). `quadmesh.__all__` gains no names.
- **SC-004**: `docs/MAPPING.md` lists all 18 inventory rows with their disposition.
- **SC-006**: `release_ignore.py verify` exits 0 for the GitHub/Zenodo, sdist, and wheel channels, and `generate --check` exits 0.
- **SC-007**: A grep for `/Users/` and `/home/[a-z]` across shipped files finds nothing.
- **SC-008**: Each document under FR-020 has 0 hard tells in its final tell scan, and the fact audit shows no added or dropped facts.
- **SC-005**: A clean-environment install with only the declared dependencies imports and runs `run_pipeline` on a bundled mesh.

## Assumptions

- The PyPI versions of `chilmesh` include `submesh` (1.1.0+, `CHILmesh/CHANGELOG.md:177`). `CHILmesh/CHANGELOG.md` does not name the first release with the #173 fix, so the floor is `chilmesh>=1.5.0`, which `valence-domains` already requires (`Valence/pyproject.toml:28`).
- `admesh2D` is pip-installable. Its package name comes from `ADMESH/pyproject.toml:6`, and a local wheel exists in `ADMESH/dist/`. `valence-domains` is pip-installable too, because `admesh2D` depends on `valence-domains>=0.4.2` (`ADMESH/pyproject.toml:27`) and a local wheel exists in `Valence/dist/`.
- The bundled Valence wheel ships the manifest (`manifest.py:41-47`) but not the mesh files, so the fetch-and-hash duty cannot move to Valence without a new API.
- The parallel feature 056 owns the version string mismatch (`pyproject.toml:7` says 0.2.1, `src/quadmesh/__init__.py:4` says 0.2.0) and the version bump.
- `.specify/feature.json` was not written in this turn because writes are confined to `specs/057-sibling-dedupe/`.
