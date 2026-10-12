"""Interchange I/O: Gmsh .msh 2.2 ASCII and Wavefront .obj.

CHILmesh has .14 I/O only, so these small helpers live here (research R4).
Files are 1-based; arrays in memory are 0-based. Element rows are triangles
(3 columns) or quads (4); a mixed array uses (n, 4) with a triangle padded
as [a, b, c, c] (negative entries are also dropped on write).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np


def _verts(row) -> list[int]:
    out = [int(v) for v in row if int(v) >= 0]
    if len(out) == 4 and len(set(out)) == 3:  # padded triangle
        out = list(dict.fromkeys(out))
    return out


def _pack(rows: list[list[int]]) -> np.ndarray:
    if not rows:
        return np.zeros((0, 3), dtype=int)
    if all(len(r) == 3 for r in rows):
        return np.array(rows, dtype=int)
    return np.array([r if len(r) == 4 else r + [r[2]] for r in rows], dtype=int)


def _fmt(x: float) -> str:
    return repr(float(x)).removesuffix(".0")


def _xyz(points) -> np.ndarray:
    pts = np.asarray(points, dtype=float)
    out = np.zeros((len(pts), 3))
    out[:, : min(pts.shape[1], 2)] = pts[:, :2]  # z = 0 embedding
    return out


def write_msh2(path, points, conn) -> None:
    pts = _xyz(points)
    lines = ["$MeshFormat", "2.2 0 8", "$EndMeshFormat", "$Nodes", str(len(pts))]
    lines += [f"{i + 1} {_fmt(x)} {_fmt(y)} {_fmt(z)}" for i, (x, y, z) in enumerate(pts)]
    lines += ["$EndNodes", "$Elements"]
    elems = [_verts(r) for r in np.asarray(conn)]
    lines.append(str(len(elems)))
    for i, e in enumerate(elems):
        etype = 2 if len(e) == 3 else 3
        lines.append(f"{i + 1} {etype} 0 " + " ".join(str(v + 1) for v in e))
    lines.append("$EndElements")
    Path(path).write_text("\n".join(lines) + "\n")


def read_msh2(path) -> tuple[np.ndarray, np.ndarray]:
    """Read nodes and element types 2 (tri) and 3 (quad); ignore the rest."""
    lines = Path(path).read_text().splitlines()
    i = lines.index("$Nodes")
    n = int(lines[i + 1])
    ids, pts = {}, []
    for k, ln in enumerate(lines[i + 2 : i + 2 + n]):
        t = ln.split()
        ids[int(t[0])] = k
        pts.append([float(t[1]), float(t[2]), float(t[3])])
    j = lines.index("$Elements")
    m = int(lines[j + 1])
    rows = []
    for ln in lines[j + 2 : j + 2 + m]:
        t = ln.split()
        etype, ntags = int(t[1]), int(t[2])
        if etype in (2, 3):
            rows.append([ids[int(v)] for v in t[3 + ntags :]])
    return np.array(pts, dtype=float).reshape(-1, 3), _pack(rows)


def write_obj(path, points, conn) -> None:
    pts = _xyz(points)
    lines = [f"v {_fmt(x)} {_fmt(y)} {_fmt(z)}" for x, y, z in pts]
    for r in np.asarray(conn):
        lines.append("f " + " ".join(str(v + 1) for v in _verts(r)))
    Path(path).write_text("\n".join(lines) + "\n")


def read_obj(path) -> tuple[np.ndarray, np.ndarray]:
    pts, rows = [], []
    for ln in Path(path).read_text().splitlines():
        t = ln.split()
        if not t:
            continue
        if t[0] == "v":
            pts.append([float(t[1]), float(t[2]), float(t[3]) if len(t) > 3 else 0.0])
        elif t[0] == "f":
            v = [int(x.split("/")[0]) - 1 for x in t[1:]]
            if len(v) in (3, 4):
                rows.append(v)
    return np.array(pts, dtype=float).reshape(-1, 3), _pack(rows)
