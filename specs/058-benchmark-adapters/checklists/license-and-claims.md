<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# License and Claims Checklist: Benchmark adapters for other quad meshers

**Purpose**: Prove, with evidence the lead reads directly, that the 0.3.0 harness keeps the license boundary and that every public claim is backed by a wired, tested adapter.
**Created**: 2026-10-10
**Feature**: [spec.md](../spec.md), [plan.md](../plan.md), [tasks.md](../tasks.md)

## License boundary

- [x] CHK001 No `import gmsh` anywhere under `src/` (`grep -rn "import gmsh" src/` returns nothing).
- [x] CHK002 Built wheel file list contains no path with `gmsh`, `comiso`, `qex`, `valence` (`tests/test_bench_packaging.py` output pasted here).
- [x] CHK003 `pyproject.toml` extras `bench*` list no GPL distribution; `pip install ".[bench]"` in a fresh venv installs nothing GPL (`pip list` transcript pasted here).
- [x] CHK004 Gmsh adapter docstring states: user-installed, GPL, subprocess only, nothing redistributed.
- [ ] CHK005 QuadriFlow adapter: MIT; if any code is vendored, `THIRD_PARTY_NOTICES.md` exists with the MIT text; if nothing is vendored, no notices file is created and this item records "nothing vendored".
- [x] CHK006 Greedy baseline displays as "greedy recombination (baseline)"; it appears only as a results-table row with one footnote ("Simple reference baseline: pairs adjacent triangles greedily; included for comparison only."), never in README prose or the pyproject description. Adapter docstring: short method paragraph plus "Standard greedy triangle recombination; a reference baseline, not a contribution of this package." (operator ruling 2026-10-10).
- [ ] CHK007 No Valence import, dependency, or code: `grep -rni valence src/ pyproject.toml` hits only comments in `tests/_mesh_provision.py` territory, never `src/`.
- [x] CHK008 `src/quadmesh/tri2quad.py` unchanged by this feature (`git diff 3b39fbb..HEAD -- src/quadmesh/tri2quad.py` empty).

## Install routes and opt-out

- [x] CHK009 Base install (`pip install .`): `quadmesh-bench --list` shows QuADMESH+ and greedy tri-merge available; QuadriFlow and Gmsh show their install route text.
- [x] CHK010 `QUADMESH_BENCH_DISABLE=<installed adapter>` removes its row; `--list` reads "disabled" (SC-009).
- [x] CHK011 `--strict` exits non-zero on a not-installed adapter; default exits 0 (FR-022).

## Claims

- [x] CHK012 `docs/benchmarks/0.3.0/results.md` and `results.json` exist and were produced by `quadmesh-bench --bundled --out docs/benchmarks/0.3.0`; the footer lists tool versions and date.
- [x] CHK013 Every adapter named in the README benchmark section and in the `pyproject.toml` description appears as a row in `results.md` (FR-021).
- [x] CHK014 `tests/test_bench_claims.py` green; it fails when a named adapter is unregistered (negative check run once and recorded).
- [ ] CHK015 README text and `results.md` prose passed the writing stack in order (voice 1-10, G1-G17, `asd-ste100-lens`, tell scan with fact add/drop audit); scan output pasted here with zero hard-rule findings (SC-007).
- [ ] CHK016 README says plainly that QuadriFlow remeshes and may not preserve the boundary, and that QuADMESH+ point insertion may add boundary points; no adapter is described as better than the table shows.

## Metrics and performance

- [ ] CHK017 Skew columns for the Gmsh row match `compute_quality_stats` on the saved output to four decimals (SC-003).
- [x] CHK018 Runner overhead under 50 percent of direct QuADMESH+ runtime on the largest bundled mesh (SC-008, relaxed by operator ruling); numbers recorded here.

## Notes

- A worker's self-reported PASS is not evidence. The lead re-runs CHK002, CHK003, CHK009, CHK013 and CHK014 before accepting (`~/Projects/DomI/.claude/policies/independent-verification.md`).

## Evidence (2026-10-10, session 4e33ac09; lead re-verifies)

- CHK001: `grep -rn "import gmsh" src/` returns 0 lines.
- CHK002: `pytest --runslow tests/test_bench_packaging.py` in scratch venv: 3 passed. Allow-list: `quadmesh/benchmark/adapters/gmsh_blossom.py` (own subprocess wrapper).
- CHK003: scratch venv, `pip install ".[bench]"`, `pip list | grep -i -E "gmsh|comiso|qex|quadriflow"` empty (17 packages).
- CHK004: docstring of `gmsh_blossom.py`. The Gmsh .geo script is NOT VERIFIED on a binary.
- CHK005: nothing vendored; no notices file. QuadriFlow behavior NOT VERIFIED (no binary). PyPI `pyquadriflow` 0.0.4 is MIT (LICENSE in wheel) but Linux/Windows only; now wired in the `bench-quadriflow` extra for those platforms (operator ruling), unverified.
- CHK006: done, operator ruling 2026-10-10 (label, README/description removal, footnote in `_report.NOTES`, docstring trimmed).
- CHK007: `grep -rni valence src/ pyproject.toml` hits only graph-valence comments and a TODO URL in `share_hint.py`; no Valence import.
- CHK008: `git diff 3b39fbb -- src/quadmesh/tri2quad.py` empty.
- CHK009: scratch venv `pip install .`, `quadmesh-bench --list`: greedy-tri-merge and quadmesh-plus available; gmsh-blossom and quadriflow "not installed" with hints.
- CHK010/011: `tests/test_bench_cli.py` and `tests/test_bench_runner.py` pass.
- CHK012: produced by the stated command; footer has versions, date, reproduce command. Not committed. Version is 0.3.0.
- CHK013: README and description name no benchmarked tool besides QuADMESH+ (the greedy baseline appears only as a results-table row with a footnote; harness clause dropped from the description, operator ruling 2026-10-10).
- CHK014: green; negative check run once (removed marker, `test_external_adapters_marked` failed, README restored).
- CHK015: PARTIAL. Voice and G1-G17 by eye, `banned_words.py --mode prose` exit 0, one G2 tail ("it does not stop the run") rewritten. Haiku scanner and Sonnet corrector were not dispatched. Fact audit: no facts added beyond table values; none dropped.
- CHK016: README says QuadriFlow may move or drop boundary vertices and gives QuADMESH+ boundary-change counts; results.md notes say the counts exceed the R5 expectation of "small". Not checked: no adapter is called better.
- CHK017: NOT DONE (no Gmsh).
- CHK018: PASS under relaxed SC-008 (50 percent). Block_O: direct `run_pipeline` 0.385 s and 0.370 s; `run_benchmark` total 0.538 s both runs (+40% to +45%); row runtime 0.433 s. Overhead includes file load, hashing, metrics and the adapter's mesh copy.
