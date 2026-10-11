<!-- provenance: author=domattioli model=claude-opus-5-5 effort=low date=2026-10-10 skill=speckit-plan repo=quadmesh session=unknown -->
# Implementation Plan: Remove functionality duplicated in sibling packages

**Branch**: `development` (no feature branch) | **Date**: 2026-10-10 | **Spec**: `specs/057-sibling-dedupe/spec.md`
**Input**: Feature specification from `specs/057-sibling-dedupe/spec.md`

## Summary

QuADMESH delegates vertex compaction to `CHILmesh.submesh` and the FEM solve to CHILmesh `direct_smoother`, the latter only if fixture parity holds. It inlines its one-line CHILmesh shims and keeps every public name. Dependencies change as follows: the `chilmesh` floor rises to 1.5.0, `matplotlib` becomes a declared dependency, ADMESH becomes the optional extra `[admesh]`, and Valence joins the `[dev]` extra. Partial rows are recorded in `docs/MAPPING.md` under `downstream-api`. In parallel, the release-ignore blocks are regenerated from the DomI canon and extended, sandbox paths are scrubbed, and real artifacts are verified to carry no agent files. Target release: 0.3.0, jointly with feature 056, which lands first.

## Technical Context

**Language/Version**: Python >=3.10 (`pyproject.toml:10`)
**Primary Dependencies**: numpy>=1.24, scipy>=1.10, chilmesh>=1.5.0 (raised from 1.2.1), matplotlib>=3.6 (made explicit); no new extras (the `[admesh]` extra is deferred; no Valence dependency of any kind, per spec FR-010 and FR-011)
**Storage**: n/a (`.14` files through CHILmesh I/O)
**Testing**: pytest (`tests/`); Valence fixtures need `GITHUB_TOKEN`; the no-interior-triangle gate also runs on chilmesh-bundled meshes
**Target Platform**: PyPI sdist and wheel; Zenodo snapshot through `git archive`
**Project Type**: single library plus CLI (`src/quadmesh/`)
**Performance Goals**: post-process wall time no worse than baseline +10% on Test_Case_1, Block_O, and Mixed_Test (guards the cost of rebuilding layers in `submesh`)
**Constraints**: zero interior residual triangles; public API unchanged; no edits to files owned by feature 056 (spec FR-018)
**Scale/Scope**: about 8 source files touched, about 70 net lines removed from `src/`, 4 release-config files

## Constitution Check

| Principle | Status |
|---|---|
| I. Faithful port | PASS. SC-002 parity gate; if parity fails, the local `_balendran_smooth` stays. |
| II. Depend on chilmesh, no reinvention | PASS. This feature serves the principle directly. |
| III. Test-first per module | PASS. A baseline snapshot test is written before the swap (T005). |
| IV. Layered implementation | PASS. Leaf helpers (compaction, shims) change before the smoother. |
| V. 0-based indexing | PASS. No change. |
| VI. Caveman docs | Docstrings stay terse. Spec artifacts use plain prose (operator directive). |
| Constitution "Dependencies" lists `chilmesh >= 0.4.0` and an optional `matplotlib >= 3.6` | Justified deviation. FR-009 makes `matplotlib` a hard dependency. This is already true in practice: `create_quad_domain.py:15` imports it unconditionally, and chilmesh hard-requires it (`CHILmesh/pyproject.toml:43`). The chilmesh floor rises to 1.5.0. Operator ruling (2026-10-10): amend the constitution in task T026a (chilmesh floor 1.5.0, matplotlib required, current fixture path, version 0.1.0 → 0.2.0). |

Post-design re-check: PASS. No violations.

## Phase 0: Research (decisions)

| # | Decision | Rationale | Alternatives rejected |
|---|---|---|---|
| R1 | `remove_unused_vertices` becomes a private shim: `mesh.submesh(np.arange(mesh.n_elems))`. It keeps the early return when every vertex is used (`remove_unused.py:17-18`). | One public CHILmesh API (`CHILmesh.py:163`). The shim keeps the 5 call sites unchanged (`doublet_collapse.py:80`, `quad_vertex_merge.py:84`, `cleanup_boundary_quads.py:168`, `post_process.py:296`). | Deleting the module and editing every call site causes churn for no gain. |
| R2 | Check that `submesh` preserves `grid_name` and padded triangle rows. If it does not, the shim reattaches `grid_name`. | The current code passes `grid_name` (`remove_unused.py:25`). | — |
| R3 | `fem_smoother(method="fem")` calls `mesh.direct_smoother()` (the interior-RHS fix is at `CHILmesh.py:2287`) and writes the returned points, only if T006 shows parity at ≤1e-6. Otherwise `_balendran_smooth` stays and MAPPING records it as partial. | Operator ruling: keep local code on parity failure. | Accepting drift was rejected. |
| R4 | `_topology.ccw_edges_around_vert` and `merge_tri_pair(s)` are inlined at `identify_edges.py:23` and `tri2quad.py:822`; `_topology.py` is deleted. | Private module; it only forwards (`_topology.py:9-24`). | — |
| R5 | `_build_tri_adjacency`, `truss_smoother`, `create_quad_domain`, repair internals, and `validation/` stay. Each gets a MAPPING `downstream-api` row. | Spec rows 6, 8, 9, 14, 15 are partial; the operator ruled no block. | — |
| R6 | Raise the chilmesh floor to `>=1.5.0`. | Matches the local sibling version and the `valence-domains` floor (`Valence/pyproject.toml:28`). No changelog line dates the #173 fix, so the latest verified version is the safe floor. | 1.2.1 may lack the #173 fix. |
| R7 (superseded 2026-10-10) | `[admesh]` extra deferred: admesh2D pulls in valence-domains (spec FR-011). |
| R7-old | `[admesh]` extra plus `run_pipeline(pre_smooth=False)`, with a lazy import of `admesh.quad_prep.smooth_for_quadrangulation` (`ADMESH/src/admesh/quad_prep.py:57`). | Operator Q1. The default path does not import admesh. | — |
| R8 (superseded 2026-10-10) | No Valence dependency anywhere; `_mesh_provision.py` unchanged; see spec FR-010. |
| R8-old | When `valence_domains` imports, `_mesh_provision.py` checks that every local `MANIFEST` key exists in `valence_domains.manifest`; the provisioned set and the SHA-1 hash pins stay local (spec FR-010). | Valence uses SHA-256 `content_uid`, not git-blob SHA-1 (`schema.py:402`). The download path stays local until `fetch_mesh` exists. | — |
| R9 | Hygiene: add `experiments/`, `facts.yml`, and `scripts/onstart_local.sh` to `.release-ignore.toml` `[extend]`. Run DomI `release_ignore.py generate` (read-only fetch of the tool from the DomI checkout), then `verify` on a `git archive` listing and on `python -m build` output. | Spec H1 to H10. | Hand-editing generated blocks is forbidden (the marker comment says so). |
| R10 | Replace the `/home/user/Valence/...` default (`scripts/exp_refuse_boundary_merge.py:156`) with a path relative to the sibling checkout, `Path(__file__).parents[2] / "Valence/registry_data/meshes"`, while `QUADMESH_REGISTRY_DIR` still overrides it. Reword `docs/benchmarks/refuse-boundary-merge-real-meshes.md:8` to "sibling Valence checkout (`../Valence/registry_data/meshes/`)". | Spec P1, P2. | — |
| R12 | Writing stack (spec FR-020) runs per document after its content task: voice → Golden rule → STE/ADHD lens → tell scan (Haiku scan, Sonnet fix, fact audit). The gate is 0 hard tells. Docstrings get the stack in the light form (one sentence each). | Operator scope add, 2026-10-10. | Running the stack once at the end over all text: the fact audit loses per-doc traceability. |
| R11 | Only task T033 of this feature runs `move_specs_to_domi.sh --apply`, and only after the implementations of both 056 and 057 are done. The script copies all of `specs/` (lines 196-204) before it runs `rm -rf .specify specs` (line 258), so one run at the end moves both features. Feature 056 has no move task of its own. | Coordinator ruling, 2026-10-10. | A separate move per feature: the first run would delete the other feature's local specs. |

## Phase 1: Design

**Data model**: no new entities. Inventory rows and API gaps are documentation only (spec "Key Entities").

**Contracts (public API, unchanged)**:
- `quadmesh.__all__`: `tri2quad`, `post_process`, `fem_smoother`, `compute_quality_stats`, `format_quality_report`, `repair_mesh`, `repair_chilmesh`, `__version__`. Lazy names: `create_quad_domain`, `run_pipeline`.
- New optional keyword `run_pipeline(..., pre_smooth: bool = False)`. This is an additive change.
- `two_part_smoother`: the warning text changes to "deprecated; removed in 0.4.0; use fem_smoother".

**Quickstart (verification)**:
```bash
. .venv/bin/activate && pip install -e '.[dev]'
pytest tests/                                    # SC-001
pytest tests/test_dedupe_parity.py -v            # SC-002 (new)
python -m build && git archive --format=tar HEAD | tar t > /tmp/ga.txt
python ~/Projects/DomI/skills/release-integrity/scripts/release_ignore.py verify ...   # SC-006
```

**Project structure (touched)**:
```text
pyproject.toml                         # deps + extras only
.release-ignore.toml, .gitattributes, .zenodoignore, MANIFEST.in
src/quadmesh/remove_unused.py, post_process.py, _topology.py (delete),
             identify_edges.py, tri2quad.py, pipeline.py
tests/_mesh_provision.py, tests/test_dedupe_parity.py (new), tests/test_smoother.py
scripts/exp_refuse_boundary_merge.py, docs/benchmarks/refuse-boundary-merge-real-meshes.md
docs/MAPPING.md
```

**Agent context update**: skipped (no `.specify/scripts/`; AGENTS.md is project-owned).
