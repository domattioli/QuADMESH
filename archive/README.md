# Archive — frozen MATLAB QuADMESH+ original

The original MATLAB QuADMESH+ source, preserved for **citation and reference
only**. It is **not installable**, **not maintained**, and **not on the Python
build/test/run path** — nothing imports it. It lives here (out of the Python
`src/` tree) so the reference the port descends from survives in-repo.

For the maintained, runnable implementation, use the Python port in
[`../src/quadmesh/`](../src/quadmesh/).

## Contents

| Dir | Was | What |
|---|---|---|
| `matlab/quadmesh/` | `02_QuADMESH_Library/` | Original MATLAB QuADMESH+ algorithm library (the port source). |
| `matlab/supporting/` | `04_CHIL_Supporting_Functions/` | CHIL helper functions (`saveMesh.m`, `MYcell2mat.m`). |

Embedded relative paths inside the `.m` files (e.g. to the old
`03_CHILMesh_Test_Cases/`) were **not** rewritten during the 2026-05 root
reorganization or this prune — to run the MATLAB code, check out a pre-reorg
commit where the original `0X_*` layout is intact.

## Removed in the 2026-07 prune

The following were deleted (recover any from git history:
`git log --all --full-history -- <path>` then `git show <sha>:<path>`):

- `chilmesh_class/` (`@CHILmesh` MATLAB class) and `admesh_library/` — dead
  duplicates of the now-independent [`domattioli/CHILmesh`](https://github.com/domattioli/CHILmesh)
  and [`domattioli/ADMESH`](https://github.com/domattioli/ADMESH) repos, which
  own their own MATLAB references.
- `matlab_test_cases/` — MATLAB-opaque `.mat` mesh binaries + `.14` meshes;
  the maintained meshes come from the [`domattioli/Valence`](https://github.com/domattioli/Valence)
  registry (see `tests/fixtures/README.md`).
- `results/` — old MATLAB result outputs.
