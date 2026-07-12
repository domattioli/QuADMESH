# MATLAB legacy reference

The original MATLAB QuADMESH+ source, preserved for **citation and reference only**.
It is **not installable** and is **frozen** — embedded relative paths (e.g. to the
old `03_CHILMesh_Test_Cases/`) were **not** rewritten during the 2026-05 root
reorganization.

To run the MATLAB code, check out a pre-reorg commit (before the `003-root-reorg`
change) where the original `0X_*` directory layout is intact.

For the maintained, runnable implementation, use the Python port in
[`../src/quadmesh/`](../src/quadmesh/).

## Contents

| Dir | Was | What |
|---|---|---|
| `quadmesh/` | `02_QuADMESH_Library/` | Original MATLAB QuADMESH+ algorithm library (the port source). |
| `supporting/` | `04_CHIL_Supporting_Functions/` | CHIL helper functions (`saveMesh.m`, `MYcell2mat.m`). |

## Related

- The MATLAB CHILmesh class and ADMESH library that once sat beside this tree
  were deleted in the 2026-07 prune — they were dead duplicates of the
  independent [`domattioli/CHILmesh`](https://github.com/domattioli/CHILmesh)
  and [`domattioli/ADMESH`](https://github.com/domattioli/ADMESH) repos, which
  own their own MATLAB references now.
