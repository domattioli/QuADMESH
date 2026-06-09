# Feature Specification: Quadmeshing Algorithm Survey & Benchmark Branch

**Feature Branch**: `002-quadmeshing-algorithm-survey`
**Created**: 2026-05-22
**Status**: Complete (gaps filled 2026-06-01; sub-issues pending operator baseline decision)
**Input**: Issues #9 (parent — survey popular quadmeshing algorithms for benchmarking against QuADMESH+), #10 (qmorph open-source availability)

## Purpose

Catalog popular direct and indirect quadrangular mesh generation algorithms. For each, record (a) algorithm class, (b) canonical reference, (c) open-source implementation availability, (d) license, (e) input/output compatibility with the chilmesh/QuADMESH pipeline, (f) suitability as a benchmarking baseline for QuADMESH+ on fully-quad and mixed-element targets.

Deliverable: this spec + per-algorithm sub-issues. NO algorithm implementations land in this branch — each candidate adopted for benchmarking gets its own follow-up issue and spec under `specs/003-...`, `specs/004-...`, etc.

## User Scenarios & Testing

### User Story 1 — Researcher locates baseline candidates (Priority: P1)

Researcher reviewing QuADMESH+ benchmark plan opens `specs/002-quadmeshing-algorithm-survey/spec.md`. Reads §"Algorithm Catalog". Picks 2–3 baselines whose license + I/O permit benchmarking and files an adoption sub-issue.

**Independent Test**: Open the spec; for each algorithm row, every column (class, reference, impl URL, license, I/O fit, benchmark suitability) is populated or marked `[GAP — research needed]`. A reader can decide adoption without external lookups for the populated rows.

**Acceptance Scenarios**:

1. **Given** the catalog table, **When** a row is marked "adopt", **Then** a tracking sub-issue exists with title `Adopt <algorithm> as QuADMESH+ benchmark baseline` and links back to this spec.
2. **Given** an algorithm with no open-source impl, **When** captured, **Then** it is still listed with `Impl: none` and rationale (write-from-paper effort estimate, or skip).

### User Story 2 — qmorph status answered (Priority: P2)

Issue #10 asker reads the spec's qmorph row and learns whether an open-source qmorph implementation exists, what license, and whether it is adoptable.

**Independent Test**: The qmorph row of the catalog table contains a concrete answer (URL or "none found after search of <sources>") plus a recommendation.

**Acceptance Scenarios**:

1. **Given** the catalog, **When** the reader searches "qmorph", **Then** they find a row with impl URL or explicit "none found" with sources searched.

### Edge Cases

- Algorithm has only commercial impl (Gmsh quad recombine plugin licensed differently than core): record license per binary, mark adoption blocker.
- Algorithm published but no code released and no clear pseudocode: mark `Impl: paper-only`, defer.
- Multiple impls of same algorithm (e.g., Blossom-Quad in Gmsh + standalone): list the cleanest dependency-wise.

## Requirements

### Functional Requirements

- **FR-001**: Catalog MUST cover both direct (advancing-front, paving, qmorph) and indirect (tri→quad merging, mixed-integer, Blossom-Quad) families.
- **FR-002**: Each catalog entry MUST record: name, family, year, canonical citation, open-source impl URL (or "none"), license, input mesh format, output mesh format, dependency on geometry/PDE solver, fit-with-chilmesh comment.
- **FR-003**: Catalog MUST include qmorph (resolves #10).
- **FR-004**: Spec MUST close with a "Recommended Baselines" shortlist of ≤5 candidates flagged for sub-issue creation.
- **FR-005**: Each shortlisted candidate MUST have a sub-issue opened on `domattioli/QuADMesh` before #9 closes.
- **FR-006**: No algorithm implementation lands in this branch. Spec-only.

### Key Entities

- **Algorithm Catalog Row**: name, family, year, citation, impl_url, license, input_fmt, output_fmt, deps, chilmesh_fit, adoption_status.

## Algorithm Catalog

### Direct methods (advancing-front / boundary-propagation)

| Name | Family | Year | Citations (approx.) | Impl URL | License | Input | Output | Deps | chilmesh fit | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| **Paving** | direct advancing-front | 1991 | ~600–800 (FEM/CAE lit; 35-yr accumulation) | None open. Coreform Cubit (commercial, free ≤50k elem) | Proprietary | boundary loops | all-quad | none | candidate — boundary-loop matches chilmesh output | paper-only for OSS |
| **Q-Morph** | direct advancing-front (tri-input) | 1999 | ~200–300 | None found. CUBIT/Coreform only; searched Verdict, Mesquite, INRIA Yams, GitHub | None open | tri mesh | all-quad | tri mesh + front | strong fit — tri input is chilmesh native | no-open-impl; resolves #10 |

### Indirect methods (tri-recombine / global parametrization / field-guided)

| Name | Family | Year | Citations (approx.) | Impl URL | License | Input | Output | Deps | chilmesh fit | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| **Blossom-Quad** | indirect tri-recombine + min-cost perfect-matching | 2012 | ~200–300 | https://gmsh.info (`Mesh.RecombinationAlgorithm=1`) | GPL-2.0+ | tri mesh | all-quad | Gmsh runtime | strong — accepts tri input | candidate |
| **Frontal-Delaunay + Blossom** | indirect frontal-Delaunay prep + Blossom recombination | 2013 | ~100–150 | Gmsh built-in (`Mesh.Algorithm=6` + recombine) | GPL-2.0+ | CAD surfaces | all-quad | Gmsh runtime | strong — natural companion to Blossom-Quad | candidate |
| **Mixed-Integer Quadrangulation** | indirect global param + MIP | 2009 | ~536 (most cited single quad paper in graphics) | CoMISo: https://www.graphics.rwth-aachen.de/software/comiso/ ; libQEx: https://github.com/hcebke/libQEx | GPL-3.0 | tri mesh + cross-field | quad mesh | CoMISo, libQEx | heavy deps; benchmark-only | candidate |
| **Integer-Grid Maps** | indirect global param (improved MIQ) | 2013 | ~233 | libQEx: https://github.com/hcebke/libQEx | GPL-3.0 | tri mesh + frame field | quad mesh | CoMISo, libQEx | same pipeline as MIQ, cleaner extraction | research |
| **Instant Field-Aligned Meshes** | indirect field-guided | 2015 | ~400–500 (SGP Award 2020; SIGGRAPH Asia ToT Award 2025) | https://github.com/wjakob/instant-meshes (~6,100 stars) | BSD-3-Clause | tri mesh (.obj/.ply) | quad-dominant (.obj/.ply) | none external | strong candidate, light deps | candidate |
| **QuadriFlow** | indirect field-guided (scalable Instant Meshes derivative) | 2018 | ~57–120 (~832 GitHub stars) | https://github.com/hjwdzh/QuadriFlow | MIT | tri mesh (.obj) | quad mesh (.obj) | Boost, Eigen | strong — MIT, minimal deps | candidate |
| **QuadCover** | indirect cross-field + global param | 2007 | ~150–200 | No standalone OSS; avaxman/Directional has related cross-field tools | None open | tri mesh | quad | — | research | research |
| **Spectral Surface Quadrangulation** | indirect spectral / Morse-Smale | 2006 | ~150–200 | No open standalone impl | None open | tri mesh | coarse quad layout | — | weak — requires downstream refinement | research |
| **Tri-Merge (greedy)** | indirect tri-pair merge | classical | many | Trivial reimplementation | n/a | tri mesh | quad-dominant | none | weak baseline; sanity floor | reimplement-stub |
| **Catmull-Clark on coarse quad** | refinement | 1978 | many | many | varies | coarse quad | refined quad | none | not a generator; out of scope | reject |

### Citation ranking by family

**Indirect / parametrization (geometry processing venues — SIGGRAPH/CGF):**
1. MIQ (Bommes 2009) — ~536 citations — most cited single quad paper
2. Instant Meshes (Jakob 2015) — ~400–500 — most cited field-guided method
3. Integer-Grid Maps (Bommes 2013) — ~233

**Direct / FEM-engineering (IJNME/IMR venues):**
1. Paving (Blacker 1991) — ~600–800 (35-year FEM/CAE accumulation — likely highest absolute count)
2. Q-Morph (Owen 1999) — ~200–300
3. Blossom-Quad (Remacle 2012) — ~200–300

Note: the two communities largely cite different works; "most cited" depends on venue.

### Blossom + layer-wise decomposition — complexity analysis

The original Blossom algorithm has worst-case O(n^{2.5}) (Edmonds 1965; Kolmogorov Blossom-V 2009). Gmsh's Blossom-Quad is already a pragmatic simplification — it enriches the adjacency graph to near-trivalent and runs Kolmogorov's Blossom-V on that enriched graph, not a naive O(n³) global matching.

**Layer-by-layer Blossom:** If Blossom is run independently per layer of k triangles (k ≪ n), cost per layer is O(k^{2.5}) and total is O((n/k) * k^{2.5}) = O(n * k^{1.5}), which improves over O(n^{2.5}) only when k ≪ n. The practical downside: the matching is no longer globally optimal across layer boundaries — valence irregularities and leftover triangles appear at seams. Gmsh's Frontal-Delaunay+Blossom (2013) achieves a similar speedup organically by pre-aligning the triangulation with a cross-field so the matching graph is near-block-diagonal without explicit layer decomposition.

**Verdict:** A strict layer-by-layer Blossom would reduce worst-case complexity but would not clearly improve over the Gmsh Frontal-Delaunay approach, and would require careful seam handling.

## Recommended Baselines

1. **Blossom-Quad via Gmsh** — GPL, tri input, all-quad, well-maintained. Use `Mesh.RecombinationAlgorithm=1` + Frontal-Delaunay (`Mesh.Algorithm=6`).
2. **Instant Meshes** (Jakob 2015) — BSD-3-Clause, minimal deps (self-contained binary), OBJ/PLY I/O, widely cited, 6,100 GitHub stars.
3. **QuadriFlow** (Huang 2018) — MIT, minimal deps (Boost+Eigen), OBJ I/O, scalability comparison target.
4. **Mixed-Integer Quadrangulation** (Bommes 2009 / libQEx + CoMISo) — GPL-3, ~536 citations, highest-quality indirect reference despite heavy deps.
5. **Greedy Tri-Merge (reimplementation)** — trivial, no deps, sanity floor confirming QuADMESH+ outperforms naive pair merging.

Reserve/upgrade slot: Q-Morph (if clean-room impl scoped as sub-issue) or Frontal-Delaunay+Blossom (more FEM-domain appropriate).

## Out of Scope

- Implementing any of the listed algorithms in this branch.
- Benchmark harness itself (separate spec: `003-quadmesh-benchmark-harness` — file as sub-issue).
- Hexahedral mesh generators.
- GUI / interactive tools (CUBIT, Gmsh GUI workflows).

## Sub-Issues to File (after spec merges)

- `Adopt Blossom-Quad (Gmsh) as QuADMESH+ benchmark baseline` — parent #9.
- `Adopt Instant Meshes as QuADMESH+ benchmark baseline` — parent #9.
- `Adopt QuadriFlow as QuADMESH+ benchmark baseline` — parent #9.
- `Investigate Q-Morph open-source availability and adoption path` — parent #9, resolves #10.
- `Implement greedy tri-merge floor baseline` — parent #9.
- `Spec the QuADMESH+ benchmark harness` — parent #9 (precondition for any baseline being useful).

## Open Questions / Clarifications

- **NEEDS CLARIFICATION**: Benchmark targets — fully-quad only, or include mixed-element acceptance criteria from chilmesh? (Issue #9 says both; confirm metric set.)
- **NEEDS CLARIFICATION**: License threshold — is GPL acceptable in the benchmark harness, or restrict to permissive (BSD/MIT/MPL)?
- **NEEDS CLARIFICATION**: Are paper-only algorithms (no code) in scope for clean-room reimplementation, or strictly compare against existing impls?
