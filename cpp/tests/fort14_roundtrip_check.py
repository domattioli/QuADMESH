"""T017 Python half: load the C++ writer's output with CHILmesh's reader.

Usage: fort14_roundtrip_check.py <ground_truth_dir> <roundtrip_dir> [mesh ...]

For each mesh, the Python reader loads (a) the input re-written by Python's
own write_to_fort14 and (b) the C++ output <roundtrip_dir>/<mesh>.cpp.14.
Points, connectivity, grid name and boundary segments must be identical, and
the C++ output's boundary block must be byte-identical to the input's.
Run with CHILMESH_BACKEND=python.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

MESHES = ["Block_O", "WNAT_Test", "Lake_Michigan_mesh", "structuredMesh1"]


def _boundary_bytes(path: Path, n_verts: int, n_elems: int) -> bytes:
    data = path.read_bytes()
    lines = data.split(b"\n")
    skip = 2 + n_verts + n_elems
    return b"\n".join(lines[skip:])


def _segs(m):
    return [(s["kind"], s["ibtype"], [int(x) for x in s["nodes"]]) for s in m.boundary_segments]


def check(gt: Path, rt: Path, name: str) -> list:
    from chilmesh import CHILmesh

    errs = []
    src = gt / "meshes" / f"{name}.14"
    cpp_out = rt / f"{name}.cpp.14"
    if not cpp_out.exists():
        return [f"{name}: missing {cpp_out}"]
    src_mesh = CHILmesh.read_from_fort14(src, compute_layers=False)
    with tempfile.TemporaryDirectory() as td:
        py_out = Path(td) / f"{name}.py.14"
        src_mesh.write_to_fort14(str(py_out))
        a = CHILmesh.read_from_fort14(py_out, compute_layers=False)
        py_head = py_out.read_bytes().split(b"\n")[: 2 + a.n_verts + a.n_elems]
    b = CHILmesh.read_from_fort14(cpp_out, compute_layers=False)
    if a.grid_name != b.grid_name:
        errs.append(f"{name}: grid_name {a.grid_name!r} != {b.grid_name!r}")
    if a.points.shape != b.points.shape or not np.array_equal(a.points, b.points):
        errs.append(f"{name}: points differ")
    if a.connectivity_list.shape != b.connectivity_list.shape or not np.array_equal(
        a.connectivity_list, b.connectivity_list
    ):
        errs.append(f"{name}: connectivity differs")
    if _segs(b) != _segs(src_mesh):
        errs.append(f"{name}: boundary segments differ from the input's")
    if b.boundaries_present != src_mesh.boundaries_present:
        errs.append(f"{name}: boundaries_present differs")
    cpp_head = cpp_out.read_bytes().split(b"\n")[: 2 + b.n_verts + b.n_elems]
    head_same = cpp_head == py_head
    if not head_same:
        errs.append(f"{name}: node/element text differs from Python's writer")
    if _boundary_bytes(cpp_out, b.n_verts, b.n_elems) != _boundary_bytes(src, b.n_verts, b.n_elems):
        errs.append(f"{name}: boundary block not byte-identical to the input")
    print(f"{name}: arrays {'ok' if not errs else 'FAIL'}; "
          f"node+element text identical to Python writer: {head_same}")
    return errs


def main() -> int:
    gt, rt = Path(sys.argv[1]), Path(sys.argv[2])
    names = sys.argv[3:] or MESHES
    errs = []
    for name in names:
        if not (gt / "meshes" / f"{name}.14").exists():
            print(f"{name}: skipped (fixture missing)")
            continue
        errs += check(gt, rt, name)
    for e in errs:
        print(e, file=sys.stderr)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
