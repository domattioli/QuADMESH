# Changelog

All notable changes to this project will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.6] - 2026-10-23

Patch release: the per-layer sweep no longer leaves hanging nodes, and the thesis PDF is replaced by a copy with every reference resolved.

### Fixed
- The per-layer QuADMESH+ sweep is conforming again. It compared sub-mesh boundary edge ids with parent edge ids, so most leftover triangles fell through to `edge_insertion`, whose opposite-triangle split is blocked by the #81 guard; each insertion left a hanging node. The sweep now classifies each leftover triangle on its live outer ring and closes it by a ring-edge split or a vertex split. It never collapses an edge. `tri2quad_routine` saves and restores the caller's mesh state. `DEFAULT_LOST` rises in the default pipeline; `preserve_boundary=True` still loses no boundary vertex. Parity pins re-measured: Test_Case_1 mean quality 0.696 to 0.811, Block_O 0.680 to 0.801.

### Changed
- `docs/Mattioli_Thesis.pdf` is a rebuild of the 2017 thesis from its LaTeX source with every cross-reference and citation resolved. The OhioLINK copy prints `??` and `[?]`. The corrected PDF is archived at [10.5281/zenodo.23607233](https://doi.org/10.5281/zenodo.23607233) and attached to each GitHub release; README, `CITATION.cff` and `.zenodo.json` point at that DOI.
- Contact lines use GitHub profile links in place of email addresses.
- CI runs the DomI release-docs lint on README, `CITATION.cff` and `.zenodo.json` changes.

### Removed
- `quadmesh._topology`: private wrapper module with no source callers. Code calls `CHILmesh.ccw_edges_around_vert`, `chilmesh.quad_from_tri_pair` and `chilmesh.quads_from_tri_pairs` directly. Other CHILmesh 1.5.5 overlaps (MSH 2.2 I/O, benchmark metrics, `create_quad_domain`, `repair` edge map and merge, quality report, signed-area predicates) stay in quadmesh because the CHILmesh versions differ in padding, precision, vertex renumbering, output keys or are private.

## [0.2.5] - 2026-10-12

Documentation and metadata release, with one algorithm fix: the boundary layer is now routed as the thesis specifies.

### Added
- `quadmesh-bench` and `quadmesh.benchmark`: adapter harness comparing QuADMESH+ with other triangle-to-quad methods and, when the executables are installed, Gmsh Blossom-Quad and QuadriFlow (subprocess only, nothing vendored). Results for the bundled meshes are in `docs/benchmarks/0.3.0/`.
- `n_concave` in `compute_quality_stats` and `concave=N` in `format_quality_report`: count of quads with a reflex corner.
- `docs/algorithm.md`: one long-form document for the thesis algorithm, the port as implemented, a thesis-versus-port difference table, the experimental global-matching fallback, its relation to Blossom-Quad (Remacle et al. 2012), and MATLAB parity status.
- `tests/test_release_metadata.py`: guard test that fails when `CITATION.cff` or `README.md` names a DOI other than the Zenodo concept DOI `10.5281/zenodo.20350483`.
- Ethan J. Kubatko (Ohio State University) as second author in `CITATION.cff`.

- `preserve_boundary` option (default `False`) on `run_pipeline` and `post_process_routine`, plus `protected_points` on `post_process_routine` and `cleanup_boundary_quads`, and the CLI flag `--preserve-boundary`. With it on, boundary-quad cleanup skips any collapse that would delete an original boundary vertex and any shift that would move one. On the four bundled meshes this changes vertices lost from 12, 18, 4 and 2 to 0, at a cost of 1 to 9 extra elements and 0.001 to 0.011 mean skew. The default stays MATLAB-faithful.

### Known limitations
- Some boundary-layer quads can be concave. Smoothing can push a wide pinned boundary corner past 180 degrees. Both are tracked for a later release.

### Changed
- Test fixtures now come from the Valence API through `chilmesh.registry` (`VALENCE_TOKEN`), pinned by SHA-256. The GitHub contents fetcher, the `GITHUB_TOKEN` path and the git-blob pins are removed. `Mixed_Test.14` left the registry (Valence#347), so its tests skip.
- Dependency pin raised to `chilmesh>=1.5.5`.
- README opening states what the conversion keeps and adds, and links to `docs/algorithm.md`. The status banner no longer carries a month stamp.
- `CITATION.cff` and `README.md` cite the Zenodo concept DOI `10.5281/zenodo.20350483` in place of the version DOI `10.5281/zenodo.20351165`.
- Version is 0.2.5 in `pyproject.toml`, `src/quadmesh/__init__.py`, and `CITATION.cff`.
- `scripts/dev_setup.sh` installs chilmesh from PyPI by default. Set `QUADMESH_CHILMESH_SRC=<path>` to editable-install a local CHILmesh checkout instead.

### Fixed
- The per-layer sweep flagged the innermost layer (`n_layers - 1`) as the boundary layer. It now flags layer 0, which is the boundary layer in `chilmesh` and in `removeTrianglesFun.m`. Output keeps zero interior residual triangles, is quad-pure by default, and keeps every original boundary vertex. Mean skew on the bundled `structuredMesh1` changes from 0.696 to 0.647, and the expected values in the quality tests were updated (spec 059).
- `fem_smoother` now restores the exact coordinates of every boundary vertex after each pass. `CHILmesh.direct_smoother` pins the boundary with a penalty and left up to 2e-10 of drift (no fixed-vertices argument exists). `tests/test_boundary_pinned_smoothing.py` covers all bundled triangular meshes. By default `run_pipeline` can still drop original boundary vertices, because `cleanup_boundary_quads` collapses boundary quads as the MATLAB code does; smoothing does not cause it. Pass `preserve_boundary=True` (CLI: `--preserve-boundary`) to keep all of them.
- `AGENTS.md` and `scripts/dev_setup.sh` stated that chilmesh is not on PyPI. It is (`chilmesh>=1.2.1`).

### Removed
- `docs/algorithm_writeup.md`. Its content is section 5 of `docs/algorithm.md`, relabelled as the experimental fallback path.

## [0.2.1] - 2026-07-13

Never tagged or published. Its changes ship in 0.2.5.

### Fixed
- Faithfulness invariant RED→GREEN: reject near-flat pairing merges in the `quadmesh+` per-layer loop, so a merge whose result has a corner ≥ 177° is skipped and no degenerate quad is emitted. Interior geometric triangles are now 0 across all fixtures (#108).
- `fem_smoother` `method="fem"` now short-circuits after the first pass (the stiffness system lands on its fixed point in one pass; passes 2+ re-solved an identical system), plus a docstring correction that removes the implied convergence early-stop (#107).
- Validator layer auto-trigger is CHILmesh 1.4.0-tolerant: prefer the public `peel_layers()` and fall back to `_skeletonize()` for chilmesh < 1.4.0. Under 1.4.0 (which removed `_skeletonize`) the `hasattr` guard had gone `False` and the FR-007 layer check silently stopped firing.

### Added
- Token-free offline test coverage: the zero-interior-triangle faithfulness gate and the #21 size-drift report now run in CI on the `chilmesh.data` bundled meshes (annulus + donut), without a Valence PAT (#109, #21).

### Changed
- Pruned dead MATLAB duplicates of the now-independent `domattioli/CHILmesh` and `domattioli/ADMESH` repos, plus MATLAB-opaque `.mat`/`.14` mesh binaries (Valence provides meshes) and old result outputs. Relocated the frozen MATLAB QuADMESH+ original out of the Python `src/` tree (`src/matlab/` → `archive/matlab/`). No effect on the distributed package: all of it was already excluded from the wheel/sdist.

## [0.2.0] - 2026-07-05

### Added
- Opt-in `refuse_boundary_merge` flag (#98 option A): guards boundary-layer merges that produced geometric defects on offline boundary geo-tri baseline.
- Offline boundary geo-tri baseline pinned as #98 CI regression gate.

### Changed
- Tests CI minimized: PR-to-main + single Python 3.11 lane (#265-style conformance).
- Agent/dev-process files de-vendored (routine instructions read from DomI canon; retros moved to DomI central corpus).

## [0.1.1] - 2026-06-15

### Changed
- `chilmesh` runtime-dependency pin raised `>=0.4.0 → >=1.2.1` (tracks released chilmesh 1.2.1).
- Source archives (git archive / sdist / GitHub-release tarball / Zenodo) exclude agent + dev-process files via `.gitattributes` `export-ignore`.

### Added / Fixed (since 0.1.0)
- `method="quadmesh+"` (the published layer-ordered per-layer loop; `"layered"` alias) is the sole and default tri-to-quad method; `"faithful"` and `"matching"` removed (now raise `ValueError`) (#46).
- Greedy interior-saturating pairing of post-sweep layer leftovers (T017/T018): zero interior triangles; post-process mean quality up (Test_Case_1 0.573 → 0.696, Block_O 0.251 → 0.680).
- Test `.14` fixtures provisioned on demand from the `domattioli/Valence` registry instead of being vendored.

## [0.1.0]

- Initial Python port of QuADMESH+ (tri-to-quad generator on top of chilmesh).
