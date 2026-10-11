<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# Feature Specification: Benchmark adapters for other quad meshers

**Feature Branch**: none (spec-only turn; working branch `development`)
**Created**: 2026-10-10
**Status**: Clarified (2026-10-10)
**Target release**: 0.3.0 (operator ruling 2026-10-10: folds into 0.3.0 with features 056, 057 and 059)
**Input**: User description: "Let QuADMESH honestly market itself as QuADMESH+ plus a benchmark harness that runs other quad meshers on the same shallow-water meshes. Adapter interface (tri mesh in, quad mesh out, metadata), optional extras per adapter, benchmark runner producing a comparison table from the existing quality metrics. Marketing claims only for adapters wired and tested."

## Context

QuADMESH ships one algorithm, QuADMESH+ (`src/quadmesh/tri2quad.py`, `_quadmesh_plus_per_layer`). The README (`README.md:49-53`) describes QuADMESH+ alone and compares it with nothing. Feature 002 (`specs/002-quadmeshing-algorithm-survey/spec.md`) cataloged twelve quad meshers, shortlisted five baselines (`spec.md:105-111`) and deferred the harness to a separate spec (`spec.md:118`). Its three open questions (`spec.md:133-135`: metric set, GPL threshold, paper-only reimplementation) are answered here.

The existing measurement tools are single-method: `scripts/bench_quadmesh_plus.py` times the QuADMESH+ phases and reports skew quality for one mesh; `compute_quality_stats` (`src/quadmesh/quality_report.py:10-31`) returns mean, min, max, std, `n_bad` (skew below 0.3), `pct_bad` and `n_elems`. Test meshes come from the private Valence registry through a token-gated fetch (`tests/_mesh_provision.py:1-5,17-20`) with a fallback to `chilmesh.data`.

QuADMESH is licensed PolyForm-Noncommercial-1.0.0 with a No-AI restriction (`LICENSE:1-5`, `README.md:194-198`). That license is incompatible with bundling GPL code, so each third-party mesher joins the harness in the way its license allows.

## Clarifications

### Session 2026-10-10

- Q: Which adapters ship in the first slice (0.3.0)? → A: Greedy tri-merge (built-in), QuadriFlow (MIT, permissive), Gmsh Blossom-Quad (GPL, subprocess only). One adapter per license class.
- Q: Is clean-room Q-Morph in scope? → A: Dropped permanently. The "reserve/upgrade slot: Q-Morph" in `specs/002-quadmeshing-algorithm-survey/spec.md:113` is withdrawn by this ruling; 002 is not edited (it is a closed spec), this line is the cross-reference. FR-007 keeps the clean-room rule for the greedy tri-merge and any future paper-only adapter.
- Q: Where do committed results live? → A: `docs/benchmarks/<release>/results.md` plus `results.json` beside it. README links to the release folder.
- Q: When does the README/description claim land? → A: Only in the same change as a results table over the `chilmesh.data` bundled meshes. No claim text before results exist.
- Q: What happens when a named external tool is missing? → A: The row reads "not installed" with an install hint and the run exits 0. A `--strict` flag makes a missing or failed adapter exit non-zero.
- Q: How do users choose which adapters to install? → A (operator): Each adapter is its own pip extra, for example `quadmesh[bench-quadriflow]`. The base install is QuADMESH+ plus the built-in greedy tri-merge only. An aggregate extra `quadmesh[bench]` installs every permissively licensed adapter. GPL tools (Gmsh) are never installable through a pip extra; the user installs them separately and the adapter detects the executable on `PATH`. A runtime opt-out (CLI flag and config) disables any adapter even when it is installed.
- Coordination (CoS, 2026-10-10): feature 057 is committed (`ec97ba5`), so `pyproject.toml` extras are free to add in 058. Feature 059 (boundary-layer routing rework) is committed (`3b39fbb`, `src/quadmesh/tri2quad.py` changed) and holds 0.3.0. 058 folds into 0.3.0 and never edits `tri2quad.py`; the QuADMESH+ adapter calls `run_pipeline` and inherits 059's behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Researcher compares QuADMESH+ against a baseline on one mesh (Priority: P1)

A coastal-modeling researcher has a validated shallow-water triangulation and wants to know how QuADMESH+ output compares with a naive tri-pair merge and, if installed, with an external quad mesher. They run one command that converts the same input through every available adapter and prints a comparison table.

**Why this priority**: This is the claim the project wants to make in public. Without one working comparison there is nothing to market.

**Independent Test**: Run the benchmark on a bundled `chilmesh.data` mesh with no third-party tool installed. The table lists QuADMESH+ and the built-in greedy tri-merge, with every metric column filled, and marks each unavailable adapter as "not installed" rather than failing.

**Acceptance Scenarios**:

1. **Given** a `.14` triangulation and no external tools, **When** the user runs the benchmark, **Then** the output table has one row per adapter (QuADMESH+, greedy tri-merge) with element count, quad fraction, residual-triangle count, skew mean/min/std, percent below 0.3, wall-clock time, and boundary-vertex lost and added counts.
2. **Given** an external mesher is installed and on `PATH`, **When** the user runs the benchmark, **Then** that adapter's row appears with the same columns and a version string in the metadata.
3. **Given** an adapter is selected by name but not installed, **When** the user runs the benchmark, **Then** the run completes, the row reads "not installed" with the install hint, and the exit status is zero unless the user asked for strict mode.

---

### User Story 2 - Maintainer adds a new adapter without touching the runner (Priority: P2)

A maintainer wants to add a mesher from the 002 catalog. They implement one adapter against a small contract (triangulation in, quad mesh plus metadata out, availability probe, license tag) and register it. The runner, table and tests pick it up without changes.

**Why this priority**: The marketing claim is "a harness that runs other meshers"; the harness must accept new meshers cheaply or the claim decays to a one-off script.

**Independent Test**: Write a trivial adapter that returns its input unchanged, register it, run the shared adapter contract tests and the benchmark; both include the new adapter with no runner edits.

**Acceptance Scenarios**:

1. **Given** a registered adapter, **When** the contract test suite runs, **Then** every adapter passes the same checks: output is a valid CHILmesh, all elements counter-clockwise, no zero-area elements, metadata carries name, version, license tag and runtime.
2. **Given** an adapter whose license tag is GPL, **When** the package is built, **Then** the adapter contains no imported GPL code and invokes the tool only as a separate user-installed executable.

---

### User Story 3 - Reader of the README sees honest, checkable claims (Priority: P2)

A prospective user reads the README or the PyPI description. It says what the harness compares against today, names the adapters that are wired and tested, and links to a reproducible results table. It makes no claim about an adapter that is not wired.

**Why this priority**: The feature exists to permit a specific public claim. Wording is a deliverable, and over-claiming is the main failure mode.

**Independent Test**: Every adapter named in README, `pyproject.toml` description or docs maps to a registered adapter with passing contract tests. A test enforces the mapping.

**Acceptance Scenarios**:

1. **Given** the README benchmark section, **When** a reader follows the reproduce command on a bundled mesh, **Then** they obtain a table with the same adapter rows the README names.
2. **Given** an adapter is removed or its tests are skipped by default, **When** the claim test runs, **Then** it fails until the README no longer names that adapter.

---

### User Story 5 - User installs only the meshers they want (Priority: P2)

A user installs the base package and later adds one comparison mesher with one pip extra, or installs all permissive ones with `quadmesh[bench]`. They install Gmsh themselves if they want it. They can switch any adapter off without uninstalling it.

**Why this priority**: Opt-in installation keeps the base install light and the license story clean.

**Independent Test**: `pip install quadmesh` then `quadmesh-bench --list` shows QuADMESH+ and greedy tri-merge available, QuadriFlow "not installed (pip install quadmesh[bench-quadriflow])", Gmsh "not installed (install Gmsh separately)". After `pip install quadmesh[bench-quadriflow]` the QuadriFlow row becomes available. With `--disable quadriflow` it shows disabled.

**Acceptance Scenarios**:

1. **Given** the base install, **When** the user lists adapters, **Then** only project-licensed adapters are available and every other one names its install route.
2. **Given** an installed adapter named in `QUADMESH_BENCH_DISABLE`, **When** the benchmark runs, **Then** no row is produced for it and the listing says "disabled".
3. **Given** `pip install quadmesh[bench]`, **When** the dependency set is inspected, **Then** it contains no GPL-licensed distribution.

---

### User Story 4 - Maintainer publishes a results table for the release (Priority: P3)

Before a release, the maintainer runs the benchmark over the offline-available mesh set and over the Valence set when a token is present, and commits a results document that the README links to.

**Why this priority**: Results make the claim concrete, but the harness is useful before any results are published.

**Independent Test**: Run the benchmark in batch mode over `chilmesh.data` meshes; a Markdown table and a machine-readable record are written to the configured results location with mesh name, adapter, metrics, tool versions and date.

**Acceptance Scenarios**:

1. **Given** no `GITHUB_TOKEN`, **When** batch mode runs, **Then** only bundled meshes are processed and the record states which meshes were skipped and why.
2. **Given** a results record from a prior release, **When** the new record is compared, **Then** per-adapter rows align by mesh name and metric for diffing.

### Edge Cases

- An external tool exits non-zero, hangs, or writes an unreadable file: the adapter reports failure in its row with the captured stderr tail; the run continues for other adapters; a per-adapter timeout applies.
- An external mesher returns a quad-dominant mesh with leftover triangles: the residual-triangle column records them; the harness never silently drops elements.
- An external mesher adds, removes or moves boundary vertices: the boundary-vertex lost and added columns record the counts. Quality metrics are still computed.
- An external mesher needs a different input format (OBJ or PLY) and a 3D embedding: the adapter converts, preserving vertex order, and converts back; vertex-order loss is reported in metadata.
- The input mesh already contains quads (mixed input): adapters that accept only triangles report "unsupported input" rather than failing.
- Two adapters wrap the same executable with different options (for example Blossom with and without frontal-Delaunay prep): they register under distinct names.
- Mesh too large for an external tool's default limits: the row records the failure and timing to the failure point.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The package MUST define an adapter contract: input triangulation plus options; output quad (or quad-dominant) mesh in the project's mesh type plus a metadata record (adapter name, tool version or "built-in", license tag, wall-clock time, success flag, message).
- **FR-002**: Each adapter MUST expose an availability probe that reports installed/not installed, the install route (base, pip extra name, or external install hint) and the tool version without running the mesher.
- **FR-003**: The package MUST ship a built-in greedy tri-merge adapter (own code, no external dependency) as the sanity floor named in `specs/002-quadmeshing-algorithm-survey/spec.md:111`.
- **FR-004**: The package MUST register QuADMESH+ itself as an adapter so the table always contains the reference row.
- **FR-005**: GPL-licensed meshers (Gmsh Blossom-Quad, Frontal-Delaunay+Blossom, CoMISo/libQEx) MUST be reached only through a separate user-installed executable invoked as a subprocess. The package MUST NOT import, vendor, link or declare a dependency on GPL code in any install extra.
- **FR-006**: Permissively licensed meshers (QuadriFlow MIT, Instant Meshes BSD-3-Clause) MAY be vendored or called; any vendored or redistributed code MUST be listed with its license text in a `THIRD_PARTY_NOTICES.md` file. The 0.3.0 slice calls executables and vendors nothing, so no notices file is created unless that changes.
- **FR-007**: Clean-room adapters written from a paper (greedy tri-merge now; Paving or others later) MUST be original code under the project license. The spec and the adapter docstring MUST cite the paper and MUST carry a note that patent status (for example Paving, 1991) was not verified and is not legal advice; the operator confirms before any such adapter is advertised.
- **FR-008**: No Valence code and no dependency on the Valence package MAY be present. Meshes arrive only through the existing token-gated fetch in `tests/_mesh_provision.py` or `chilmesh.data`.
- **FR-009**: A benchmark runner MUST accept one or more meshes and one or more adapter names, run each available adapter, and emit a comparison table with these columns per row: adapter, element count, quad fraction, residual-triangle count (interior and boundary separately), skew mean, min, std, percent below 0.3, wall-clock seconds, boundary vertices lost and boundary vertices added (two counts), vertex count in/out.
- **FR-010**: Quality columns MUST come from the existing `compute_quality_stats` so that numbers match `scripts/bench_quadmesh_plus.py` and the README quality section.
- **FR-011**: The runner MUST isolate adapter failures: one adapter's error, timeout or non-zero exit never aborts the other rows; the failure text is kept in that row.
- **FR-012**: The runner MUST write results as a Markdown table and as a machine-readable record that includes mesh name, mesh hash, adapter metadata, metric values, date and package version.
- **FR-013**: The base install MUST contain QuADMESH+ and the built-in greedy tri-merge only, with no new hard dependency. Every other adapter MUST have its own optional extra named `bench-<adapter>` (for example `quadmesh[bench-quadriflow]`). An aggregate extra `quadmesh[bench]` MUST install every permissively licensed adapter and nothing GPL. GPL tools MUST NOT appear in any extra; their adapters are always present in the package as thin subprocess wrappers and activate only when the user-installed executable is found. Feature 057 is committed (`ec97ba5`), so these extras are new entries in `pyproject.toml`.
- **FR-023**: Users MUST be able to disable any adapter at runtime even when it is installed: a CLI flag (`--disable NAME[,NAME]`), a Python option, and an environment variable `QUADMESH_BENCH_DISABLE`. A disabled adapter appears in `--list` as "disabled" and produces no row unless the user asks for disabled rows.
- **FR-014**: A shared contract test suite MUST run against every registered adapter: valid mesh out, counter-clockwise elements, no zero-area elements, metadata fields present. External-tool adapters skip (not fail) when the tool is absent.
- **FR-015**: A test MUST verify that every adapter named in `README.md` and in the `pyproject.toml` description is registered and has non-skipped contract tests in the default offline CI run, or is explicitly marked "requires user-installed tool" in the text.
- **FR-016**: README and PyPI description text MUST name only adapters that pass FR-015. Wording is a deliverable and passes the writing stack in this order: `write-like-scientist` voice, Golden rule G1-G17, `asd-ste100-lens`, tell scan.
- **FR-017**: The faithfulness invariant (zero interior residual triangles, `tests/test_no_interior_tris.py`) applies to the QuADMESH+ row only. Other adapters report residual triangles; they are not required to have zero.
- **FR-018**: The harness MUST NOT alter QuADMESH+ output or `tri2quad` behavior. `src/quadmesh/tri2quad.py` (059, committed `3b39fbb`) is untouched by this feature.
- **FR-019**: The 0.3.0 slice ships the QuADMESH+ reference row plus exactly three comparison adapters: greedy tri-merge (built-in), QuadriFlow (permissive, optional extra or user-installed executable), Gmsh Blossom-Quad (GPL, subprocess). Instant Meshes and MIQ/libQEx are later features. Q-Morph is dropped permanently (Clarifications).
- **FR-020**: Committed results live at `docs/benchmarks/<release>/results.md` and `docs/benchmarks/<release>/results.json`, where `<release>` is the package version (for example `0.3.0`). `tests/fixtures/baselines/` (used by 057) is not reused.
- **FR-021**: README and `pyproject.toml` description claim text lands only in the same change as a committed results table (FR-020) produced on the `chilmesh.data` bundled meshes. The claim names the adapters in that table and no others.
- **FR-022**: In default mode a missing external tool yields a "not installed" row with an install hint and exit status 0. With `--strict`, a missing or failed adapter yields a non-zero exit status.

### Key Entities *(include if feature involves data)*

- **Adapter**: a named converter from triangulation to quad mesh. Attributes: name, family (from the 002 catalog), license tag (project, MIT, BSD-3, GPL-subprocess, clean-room), availability probe, install route (base, pip extra `bench-<name>`, or external executable), enabled flag, citation.
- **Adapter result**: output mesh plus metadata: adapter name, tool version, wall-clock time, success flag, message, vertex-order preserved flag.
- **Benchmark row**: one adapter result on one mesh, reduced to the FR-009 columns.
- **Results record**: a set of benchmark rows with mesh name and hash, date, package version, and tool versions; written as Markdown and machine-readable form.
- **Claim mapping**: the set of adapter names the public text may use; derived from registered adapters with passing contract tests.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On a fresh install with no third-party tools, the benchmark completes on every `chilmesh.data` mesh and produces a table with at least two rows (QuADMESH+, greedy tri-merge) and all FR-009 columns filled.
- **SC-002**: Adding a pass-through adapter takes one new file and one registration line; the runner and contract tests need zero edits (verified by doing it in the test suite).
- **SC-003**: With Gmsh installed, the Blossom-Quad row appears and its skew statistics match `compute_quality_stats` applied to the same output file to the fourth decimal.
- **SC-004**: An adapter failure (simulated non-zero exit) leaves every other row intact and the run exits zero in default mode.
- **SC-005**: The default offline CI run exercises every adapter the README names, or the README marks it "requires user-installed tool"; the FR-015 test enforces this and is green.
- **SC-006**: `pip install quadmesh` installs no new hard dependency; the wheel contains no GPL code and no Valence code (checked by a packaging test over the built wheel's file list and import graph). `pip install quadmesh[bench]` resolves no GPL-licensed distribution (checked by a test over the declared extras).
- **SC-009**: With `QUADMESH_BENCH_DISABLE=quadriflow` set and QuadriFlow installed, the benchmark produces no QuadriFlow row and `--list` shows it as disabled.
- **SC-007**: Public text for this feature passes the writing stack and a tell scan with zero hard-rule findings before merge.
- **SC-008**: Per-mesh benchmark overhead (table assembly, metric computation outside the adapters) is under 50 percent of the direct QuADMESH+ pipeline runtime on the largest bundled mesh (relaxed from 5 percent by operator ruling to accept the measured overhead of about 40 percent: 0.385 s direct versus 0.538 s via `run_benchmark` on Block_O; the overhead includes file load, hashing, metrics and the adapter mesh copy).

## Assumptions

- Target release 0.3.0. Features 056, 057 (`ec97ba5`) and 059 (`3b39fbb`) are committed for 0.3.0; this feature never edits `tri2quad.py`. It adds the benchmark entry to the `CHANGELOG.md` 0.3.0 block and new entries to `pyproject.toml`.
- The 002 catalog is the adapter source of truth; no new mesher survey is done here.
- "Boundary-vertex preservation" means the set of boundary vertex coordinates in the output equals the input set within floating tolerance; QuADMESH+ with default point insertion may add boundary points and records them honestly.
- The comparison metric set covers both all-quad and quad-dominant outputs (answers 002 open question 1). GPL tools are allowed as subprocess only (answers question 2). Paper-only algorithms are in scope as clean-room code, gated on operator patent review (answers question 3); Q-Morph itself is dropped.
- External tools are the user's responsibility to install; the harness never downloads them. No network access during tests beyond the existing Valence fetch.
- Catmull-Clark, Spectral Surface Quadrangulation and QuadCover are excluded: refinement-only or no open implementation (`specs/002-quadmeshing-algorithm-survey/spec.md:88-90`).
- Existing `scripts/bench_quadmesh_plus.py` and `scripts/diagnose_bad_quads.py` remain; the new runner may call the same helpers but does not replace them in this release.

## Out of Scope

- Any change to the QuADMESH+ algorithm or its quality.
- Hexahedral meshers, GUI workflows, 3D surface quadrangulation beyond what an adapter needs to round-trip a planar mesh.
- Downloading, building or packaging third-party executables.
- A hosted results dashboard.
- Smoothing other adapters' output with QuADMESH post-processing (a possible later "post-process everything" mode).
