<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# Research: Benchmark adapters for other quad meshers

Date: 2026-10-10. Decisions R1 to R10 are summarized in `plan.md`; this file records rationale and alternatives. No network was used; tool behavior notes come from documented command-line interfaces and must be verified in T012/T014 against the installed binaries.

## R1 Adapter contract shape

- Decision: `typing.Protocol` plus a `@register` decorator writing into a module dict; `AdapterResult` is a frozen dataclass.
- Alternatives: abstract base class (forces inheritance; Protocol lets a plain module-level object qualify); entry-point plugins (over-engineering for four adapters; can be added later without breaking the Protocol).

## R2 Gmsh Blossom-Quad as a subprocess

- Decision: write the triangulation to `in.msh` (format 2.2 ASCII), write `job.geo`:
  ```
  Merge "in.msh";
  Mesh.RecombinationAlgorithm = 1;   // Blossom
  RecombineMesh;
  Save "out.msh";
  ```
  run `gmsh -0 job.geo` (or `gmsh job.geo -` ) with `cwd` set to a temp dir and a timeout. Parse `out.msh` elements of type 2 (triangle) and 3 (quad).
- Version probe: `gmsh --version` (prints to stderr).
- License: GPL-2.0+. Nothing from Gmsh enters the package; the user installs Gmsh (`brew install gmsh`, `apt install gmsh`, or the gmsh.info binary). The adapter docstring states this.
- Risk: `RecombineMesh` on a merged discrete mesh may need `CreateGeometry;` or `Mesh.RecombineAll = 1` depending on the Gmsh version. T012 verifies on the installed binary and records the working script in the adapter.
- Rejected: `pip install gmsh` SDK (GPL wheel; would be a dependency, which FR-005 forbids even as an extra); `import gmsh` under try/except (still GPL linkage in distributed code).

## R3 QuadriFlow as an external executable

- Decision: write `in.obj` with z=0, run `quadriflow -i in.obj -o out.obj -f <target_faces>` where `<target_faces>` defaults to half the input triangle count (a recombination-equivalent count), parse `out.obj` quads. Probe: executable on `PATH` or `QUADMESH_QUADRIFLOW`.
- License: MIT. Vendoring the C++ source would require a compiled extension and Boost/Eigen at build time; rejected for 0.3.0. If vendored later, `THIRD_PARTY_NOTICES.md` carries the MIT text (FR-006).
- Known behavior: QuadriFlow remeshes from a cross field and expects a manifold surface, usually closed. For an open planar domain it may move or drop boundary vertices or fail. The adapter never hides that: `vertex_order_preserved=False`, boundary preservation counts reported, failure captured in the row. The results table footnote says so.
- Rejected: Instant Meshes for the first slice (BSD, handles boundaries better, but has GUI dependencies in its default build; a later feature).

## R4 Interchange I/O

- `.msh` 2.2 ASCII: `$MeshFormat 2.2 0 8`, `$Nodes` (1-based id x y z), `$Elements` (id type ntags tags... nodes). Read types 2 and 3 only; ignore 1 (lines) and 15 (points).
- `.obj`: `v x y z` lines, `f a b c [d]` lines, 1-based, strip `/` texture indices.
- Round-trip tests on `Test_Case_1.14`-sized bundled meshes guard the offsets.

## R5 Boundary-vertex preservation metric

- Input boundary vertices: CHILmesh boundary edges on the input. Output boundary vertices: CHILmesh boundary edges on the output (after `CHILmesh(points, conn)` construction).
- Match by coordinates with a KD-tree (`scipy.spatial.cKDTree`), tolerance 1e-9 × bounding-box diagonal.
- Report two integers (operator ruling): `boundary_lost` (input boundary vertices with no match in the output boundary) and `boundary_added` (output boundary vertices with no match in the input boundary). A preserved boundary reads 0 and 0.
- QuADMESH+ default point insertion adds boundary points, so its `boundary_added` may be nonzero; the README text explains this rather than hiding it.

## R6 Residual triangle split

- Reuse the definition from `tests/test_no_interior_tris.py`: a triangle is interior when none of its edges is a domain-boundary edge. Report `residual_tris_interior` and `residual_tris_boundary`.

## R7 Results record

- JSON keys: `schema_version` (1), `quadmesh_version`, `date`, `tools` ({adapter: version}), `meshes` ([{name, sha1, n_verts, n_tris}]), `rows` ([{mesh, adapter, status, columns...}]).
- Markdown: one table per mesh, columns in FR-009 order, status column first.
- Path: `docs/benchmarks/<quadmesh_version>/results.{md,json}`. MANIFEST.in prunes `docs/`, so results are repo-only, which is intended.

## R8 Claim test

- Build a set of display names from the registry (for example "QuadriFlow", "Gmsh", "Blossom-Quad", "greedy tri-merge"). Scan `README.md` and the `description` in `pyproject.toml`. Each hit must be a registered adapter, and the sentence must either refer to an adapter that runs in offline CI or contain the phrase "requires user-installed tool". Also assert that `docs/benchmarks/<version>/results.md` exists when README contains the benchmark section (FR-021).

## R9 Packaging test

- `python -m build --wheel --outdir <scratch>`; `zipfile` listing; forbidden substrings in paths: `gmsh`, `comiso`, `qex`, `valence`. Import check: run `python -c "import sys, quadmesh.benchmark; assert 'gmsh' not in sys.modules"` in a subprocess. Marked `slow`; CI runs it.

## R10 Greedy tri-merge

- Build edge-to-element map with CHILmesh adjacencies (`CHILmesh(compute_adjacencies=True)`); for each triangle in index order that is still unmerged, collect candidate neighbors across non-boundary edges, compute the skew of each candidate quad with `chilmesh.element_quality(metric="skew")`, merge the best if skew >= 0.1, else leave. Output quads plus leftover triangles. Deterministic, O(n).
- Docstring: one short method paragraph plus "Standard greedy triangle recombination; a reference baseline, not a contribution of this package." No 002 path, no patent note (operator ruling 2026-10-10).
- Displayed as "greedy recombination (baseline)"; named only as a results-table row with one footnote, not in README prose or the pyproject description (operator ruling 2026-10-10).

## R11 Install routes and opt-out

- Base install: QuADMESH+ and greedy tri-merge. No `bench` code is excluded from the wheel; what varies is which executables or packages are present.
- `bench-quadriflow` (operator ruling): `["pyquadriflow; sys_platform == 'linux' or sys_platform == 'win32'"]`. `pyquadriflow` 0.0.4 on PyPI is MIT (LICENSE in the wheel) and pre-alpha; its wheel carries a Linux `.so` and a Windows `.dll` only. macOS installs nothing from the extra and keeps PATH / `QUADMESH_QUADRIFLOW` detection. The adapter uses the Python module when importable, else the executable. The pyquadriflow call is read from the wheel source and is unverified.
- `bench`: union of permissive `bench-*` extras. Never lists Gmsh, CoMISo, libQEx.
- Opt-out precedence: CLI `--disable`, then Python argument, then `QUADMESH_BENCH_DISABLE`. Disabled adapters show in `--list` as "disabled" and emit no rows.
- Rejected: a config file (`~/.quadmesh/bench.toml`); the environment variable is enough for 0.3.0. Rejected: excluding adapter modules from the wheel per extra (one wheel; the wrappers are license-neutral).

## Open items carried to tasks

- Gmsh script variant verification (T012).
- QuadriFlow face-count flag name and boundary behavior on an open domain (T014).
