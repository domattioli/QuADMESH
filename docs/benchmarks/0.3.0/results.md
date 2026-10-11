### Block_O.14

| Adapter | Status | Elems | Quad % | Resid tris (int/bnd) | Skew mean | Skew min | Skew std | % < 0.3 | Concave quads | Time (s) | Bnd verts lost | Bnd verts added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| quadmesh-plus | ok | 2726 | 100.0 | 0/0 | 0.677 | 0.000 | 0.256 | 10.1 | 108 | 0.80 | 12 | 728 |
| greedy recombination (baseline) | ok | 2888 | 80.5 | 435/127 | 0.691 | 0.194 | 0.128 | 0.3 | 0 | 0.29 | 0 | 0 |
| gmsh-blossom | not installed: gmsh executable not found; install the tool separately and put it on PATH; brew install gmsh or apt install gmsh (GPL, requires user-installed tool) |  |  |  |  |  |  |  |  |  |  |  |
| quadriflow | not installed: pyquadriflow not importable and quadriflow executable not found; install the tool separately and put it on PATH; pyquadriflow (extra bench-quadriflow, Linux/Windows) or quadriflow executable on PATH or QUADMESH_QUADRIFLOW (MIT, pre-alpha, requires user-installed tool) |  |  |  |  |  |  |  |  |  |  |  |

### annulus_200pts.fort.14

| Adapter | Status | Elems | Quad % | Resid tris (int/bnd) | Skew mean | Skew min | Skew std | % < 0.3 | Concave quads | Time (s) | Bnd verts lost | Bnd verts added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| quadmesh-plus | ok | 325 | 100.0 | 0/0 | 0.325 | 0.000 | 0.291 | 45.8 | 66 | 0.15 | 18 | 221 |
| greedy recombination (baseline) | ok | 365 | 58.9 | 52/98 | 0.455 | 0.012 | 0.193 | 26.6 | 0 | 0.03 | 0 | 0 |
| gmsh-blossom | not installed: gmsh executable not found; install the tool separately and put it on PATH; brew install gmsh or apt install gmsh (GPL, requires user-installed tool) |  |  |  |  |  |  |  |  |  |  |  |
| quadriflow | not installed: pyquadriflow not importable and quadriflow executable not found; install the tool separately and put it on PATH; pyquadriflow (extra bench-quadriflow, Linux/Windows) or quadriflow executable on PATH or QUADMESH_QUADRIFLOW (MIT, pre-alpha, requires user-installed tool) |  |  |  |  |  |  |  |  |  |  |  |

### donut_domain.fort.14

| Adapter | Status | Elems | Quad % | Resid tris (int/bnd) | Skew mean | Skew min | Skew std | % < 0.3 | Concave quads | Time (s) | Bnd verts lost | Bnd verts added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| quadmesh-plus | ok | 166 | 100.0 | 0/0 | 0.344 | 0.000 | 0.297 | 45.2 | 26 | 0.05 | 4 | 115 |
| greedy recombination (baseline) | ok | 169 | 63.3 | 7/55 | 0.574 | 0.111 | 0.186 | 7.7 | 0 | 0.02 | 0 | 0 |
| gmsh-blossom | not installed: gmsh executable not found; install the tool separately and put it on PATH; brew install gmsh or apt install gmsh (GPL, requires user-installed tool) |  |  |  |  |  |  |  |  |  |  |  |
| quadriflow | not installed: pyquadriflow not importable and quadriflow executable not found; install the tool separately and put it on PATH; pyquadriflow (extra bench-quadriflow, Linux/Windows) or quadriflow executable on PATH or QUADMESH_QUADRIFLOW (MIT, pre-alpha, requires user-installed tool) |  |  |  |  |  |  |  |  |  |  |  |

### structuredMesh1.14

| Adapter | Status | Elems | Quad % | Resid tris (int/bnd) | Skew mean | Skew min | Skew std | % < 0.3 | Concave quads | Time (s) | Bnd verts lost | Bnd verts added |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| quadmesh-plus | ok | 340 | 100.0 | 0/0 | 0.623 | 0.000 | 0.175 | 6.2 | 6 | 0.08 | 2 | 55 |
| greedy recombination (baseline) | ok | 330 | 100.0 | 0/0 | 1.000 | 1.000 | 0.000 | 0.0 | 0 | 0.03 | 0 | 0 |
| gmsh-blossom | not installed: gmsh executable not found; install the tool separately and put it on PATH; brew install gmsh or apt install gmsh (GPL, requires user-installed tool) |  |  |  |  |  |  |  |  |  |  |  |
| quadriflow | not installed: pyquadriflow not importable and quadriflow executable not found; install the tool separately and put it on PATH; pyquadriflow (extra bench-quadriflow, Linux/Windows) or quadriflow executable on PATH or QUADMESH_QUADRIFLOW (MIT, pre-alpha, requires user-installed tool) |  |  |  |  |  |  |  |  |  |  |  |

Tools: greedy-tri-merge built-in, quadmesh-plus 0.3.0. Date: 2026-10-10. quadmesh 0.3.0.
Reproduce: `quadmesh-bench --bundled --out docs/benchmarks/0.3.0`

Notes:

- Lost is the number of input boundary vertices with no match in the output boundary. Added is the number of new output boundary vertices. QuADMESH+ point insertion adds boundary vertices (R5). The QuADMESH+ lost count comes from the boundary-quad cleanup step in post-processing, which collapses boundary quads. Smoothing does not move boundary vertices.
- QuADMESH+ skew min is 0.000 on every bundled mesh in this table.
- Simple reference baseline: pairs adjacent triangles greedily; included for comparison only.
- A "not installed" row means the executable was absent on the machine that produced this table. Gmsh and QuadriFlow were absent, so neither has a measured row.
- QuadriFlow remeshes from a cross field and may move or drop boundary vertices (R3). Read its boundary columns when a row exists.
