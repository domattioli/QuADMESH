"""Per-run metrics: residual triangles, boundary preservation, quality."""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

import numpy as np
from scipy.spatial import cKDTree

from ..quality_report import compute_quality_stats

STATUSES = ("ok", "failed", "not installed", "unsupported input", "timeout", "disabled")


@dataclass
class BenchmarkRow:
    mesh: str
    adapter: str
    status: str
    n_verts_in: Optional[int] = None
    n_verts_out: Optional[int] = None
    n_elems: Optional[int] = None
    quad_fraction: Optional[float] = None
    residual_tris_interior: Optional[int] = None
    residual_tris_boundary: Optional[int] = None
    skew_mean: Optional[float] = None
    skew_min: Optional[float] = None
    skew_std: Optional[float] = None
    pct_bad: Optional[float] = None
    n_concave: Optional[int] = None
    runtime_s: Optional[float] = None
    boundary_lost: Optional[int] = None
    boundary_added: Optional[int] = None
    message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def element_rows(conn) -> list[list[int]]:
    """Vertex lists per element; padded [a,b,c,c] and -1 padding give triangles."""
    out = []
    for r in np.asarray(conn):
        v = [int(x) for x in r if int(x) >= 0]
        if len(v) == 4 and len(set(v)) == 3:  # padded triangle ([a,b,c,c] or [a,b,c,a])
            v = list(dict.fromkeys(v))
        out.append(v)
    return out


def _edge_counts(elems) -> dict:
    cnt: dict = {}
    for el in elems:
        for i in range(len(el)):
            e = tuple(sorted((el[i], el[(i + 1) % len(el)])))
            cnt[e] = cnt.get(e, 0) + 1
    return cnt


def boundary_vertices(conn) -> set:
    """Vertices on domain-boundary edges (edges used by exactly one element)."""
    return {v for e, c in _edge_counts(element_rows(conn)).items() if c == 1 for v in e}


def residual_split(conn) -> tuple[int, int]:
    """(interior, boundary) triangle counts; interior = no domain-boundary edge."""
    elems = element_rows(conn)
    cnt = _edge_counts(elems)
    interior = boundary = 0
    for el in elems:
        if len(el) != 3:
            continue
        on_b = any(cnt[tuple(sorted((el[i], el[(i + 1) % 3])))] == 1 for i in range(3))
        boundary += on_b
        interior += not on_b
    return interior, boundary


def boundary_preservation(in_points, in_conn, out_points, out_conn) -> tuple[int, int]:
    """(lost, added): lost = input boundary vertices with no coordinate match in the
    output boundary; added = output boundary vertices with no match in the input
    boundary. Tolerance 1e-9 x bbox diagonal."""
    ip = np.asarray(in_points, float)[:, :2]
    op = np.asarray(out_points, float)[:, :2]
    ib = np.array(sorted(boundary_vertices(in_conn)), dtype=int)
    ob = np.array(sorted(boundary_vertices(out_conn)), dtype=int)
    if len(ib) == 0 or len(ob) == 0:
        return len(ib), len(ob)
    diag = float(np.linalg.norm(ip.max(0) - ip.min(0))) or 1.0
    tol = 1e-9 * diag
    a, b = ip[ib], op[ob]
    unmatched_in = int((cKDTree(b).query(a)[0] > tol).sum())
    new_out = int((cKDTree(a).query(b)[0] > tol).sum())
    return unmatched_in, new_out


def row_from_result(mesh_name: str, input_mesh, result) -> BenchmarkRow:
    """Build an ``ok`` or ``failed`` row from one AdapterResult."""
    n_in = int(input_mesh.n_verts)
    if not result.success or result.mesh is None:
        return BenchmarkRow(mesh_name, result.adapter, "failed", n_verts_in=n_in,
                            runtime_s=result.runtime_s, message=result.message)
    out = result.mesh
    conn = np.asarray(out.connectivity_list)
    elems = element_rows(conn)
    stats = compute_quality_stats(out)
    ri, rb = residual_split(conn)
    lost, added = boundary_preservation(input_mesh.points, input_mesh.connectivity_list,
                                          out.points, conn)
    nq = sum(len(e) == 4 for e in elems)
    return BenchmarkRow(
        mesh=mesh_name, adapter=result.adapter, status="ok", n_verts_in=n_in,
        n_verts_out=int(out.n_verts), n_elems=len(elems),
        quad_fraction=nq / len(elems) if elems else 0.0,
        residual_tris_interior=ri, residual_tris_boundary=rb,
        skew_mean=stats["mean"], skew_min=stats["min"], skew_std=stats["std"],
        pct_bad=stats["pct_bad"], n_concave=stats["n_concave"], runtime_s=float(result.runtime_s),
        boundary_lost=lost, boundary_added=added, message=result.message,
    )
