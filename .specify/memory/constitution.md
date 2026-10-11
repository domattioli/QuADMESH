<!-- provenance: author=domattioli model=unknown effort=unknown date=2026-09-24 skill=speckit-pipeline repo=quadmesh session=unknown -->
<!--
Sync Impact Report
Version: 0.1.0 -> 0.2.0 (MINOR: guidance materially changed, no principle removed)
Modified sections: III (fixture path), VI (writing stack for human-facing docs), Dependencies (chilmesh >= 1.5.0, matplotlib required)
Templates checked: .specify/templates/* (no change needed)
-->
# QuADMESH+ Constitution

Project: Python port of MATLAB QuADMESH+ tri→quad mesh generator.

## Core Principles

### I. Faithful Port

Algorithmic behaviour matches MATLAB source on canonical test cases (Test_Case_1, Block_O, Mixed_Test). Deviations require justification in commit + spec.

### II. Depend On chilmesh, No Reinvention

Mesh primitives (CHILmesh class, layers, boundary, adjacencies, paths_on_outer_vertices, MutableMesh, smoothers) come from `chilmesh`. Quadmesh adds only tri→quad logic. Touch a wheel, document the new spoke in the spec.

### III. Test-First Per Module

Each MATLAB routine ports with a paired pytest. Tests load real .14 fixtures from `tests/fixtures/meshes/` (provisioned by `tests/_mesh_provision.py`), with a fallback to the meshes bundled in `chilmesh/data`. Acceptance: quad mesh produced; element-quality stats sane; no orphan verts; no zero-area elems.

### IV. Layered Implementation

Bottom-up dependency order. Leaf helpers (CCW edges, merge pair) first. Then identify_edges + tri-removal sub-ops. Then tri2quad sweep. Then post-process (doublet, QVM, boundary cleanup). Smoothing reuses chilmesh.

### V. Index 0-Based Throughout

MATLAB uses 1-based; Python port stays 0-based, matching chilmesh. Sentinel for "no neighbour" in edge2elem = -1 (chilmesh convention).

### VI. Writing Stack For Human-Facing Docs

Human-facing docs (README, docs/, docstrings shown to users, issue and PR text) use the writing stack in order: `write-like-scientist` voice rules 1-10, then Golden rule G1-G17, then `asd-ste100-lens` STE + ADHD, then the tell scan. Caveman style stays for agent-facing files and terminal output (operator ruling 2026-10-10). Algorithmic invariants explicit.

## Scope

In scope:
- `00_Main/Main.m` → CLI + `run_pipeline`.
- `01_Create_Quad_Domain/` → polygon-mask subset selector (no GUI).
- `02_Tri2Quad_Routine/` → core sweep.
- `03_Layer_Paths/` → already in chilmesh.layer_paths.
- `04_Remove_Triangles/` → edge_insertion / bisection / removal.
- `05_Post-Process_Routine/`.
- `06_Cleanup_Boundary_Quads/` → CleanupBoundaryQuads_v2 only.
- `07_Doublet_Collapse/`.
- `08_Quad_Vertex_Merge/` → v2 only.
- `10_Remove_Unused_Vertices/`.
- `11_FEM_Smoothing/` → wrap chilmesh `direct_smoother` + `angle_based_smoother`.

Out of scope:
- `01_ADMESH_Library/` — distinct project; not ported here.
- `99_In_Progress/` — drafts.
- `.asv` autosave files.
- MATLAB UI calls (uigetdir, listdlg, questdlg, drawSubdomain interactive draw).
- `04_CHIL_Supporting_Functions/saveMesh.m` legacy file IO (chilmesh handles fort.14).

## Dependencies

- `chilmesh >= 1.5.0` (the Python port of CHILmesh.m).
- `numpy >= 1.24`, `scipy >= 1.10`, `matplotlib >= 3.6` (required).

## Quality Gates

- `pytest` green on Test_Case_1, Test_Case_2, Block_O.
- Output quad mesh: all elems CCW, no zero-area, vert count ≤ tri count + boundary buffer.
- README/CHILmesh future-work items filed as issues on `domattioli/CHILmesh`.

## Governance

Spec lives in `specs/<NNN>-<short-name>/`. Spec drives implementation; deviations land in `spec.md` clarifications first.

**Version**: 0.2.0 | **Ratified**: 2026-05-20 | **Last Amended**: 2026-10-10
