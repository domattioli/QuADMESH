# C++ port sorts ties, marks triangles with -1, and peels layers once

Status: accepted (2026-11-06)

The C++ port reimplements the CHILmesh subset QuADMESH needs, and uses the Python package as the oracle. Three choices differ from a literal copy of the Python behavior.

**Ties are broken by smallest ID, not by CPython set order.** Several Python tie-breaks depend on set iteration order (`doublet_collapse.py:43-45`, `_tri_removal.py:301-315`, `_tri_removal.py:426,448-455`). That order is a hash-slot accident, so copying it would need a CPython-compatible hash set. The C++ port sorts instead. Ground truths are compared by element count, vertex count, quality statistics and zero interior residual triangles, not by bytes. Byte equality is measured and logged on each ground-truth mesh, but it does not gate.

**Triangles in mixed rows end in `-1`.** Python writes a triangle as `[a,b,c,c]`, the CHILmesh constructor rewrites it as `[a,b,c,a]` whenever it computes layers or adjacencies (`CHILmesh.py:602-603`, probed 2026-11-06), and the checks `row[2] == row[3]` in `doublet_collapse.py:23` and `quad_vertex_merge.py:37` then never match. `chilmesh_cpp` already marks triangles with trailing `-1` (`halfedge.cpp:36-37`) and never compares vertices, so the port follows it. The core stage emits no triangles on the three ground-truth meshes, so its output does not change.

**Layers are computed once.** Python rebuilds a CHILmesh after every post-process step and so re-peels the mesh each time, but no post-process module reads layers. The port computes layers before the sweep and skips the re-peel.

## Considered options

- Emulate CPython set order: exact match to Python, but brittle and slow to write.
- Copy the repeated-vertex marker: bit-for-bit with Python, but it copies a defect and diverges from `chilmesh_cpp`.
- Keep the re-peel for parity: costs time and code, with no difference in output.

## Consequences

- A ground-truth diff can pass while connectivity differs from Python. Reviewers must read the diff report, not only the pass/fail line.
- If a later post-process step needs layers, it must request them explicitly.
