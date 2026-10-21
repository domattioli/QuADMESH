"""Handle leftover tris after tri-pair merge in a layer.

Per MATLAB ``removeTrianglesFun``, each leftover tri is routed by:

    on_mesh_bdy?  + n boundary edges  →  operation
    ----------------------------------------------
    False, ≥1     → edge_bisection (case 2)
    True,  0      → edge_insertion (case 1)
    False, 0      → edge_insertion (case 2)
    True,  2 or 3 → edge_insertion (case 3)
    True,  1, can_remove → edge_removal
    True,  1, !can_remove → edge_bisection (case 1)

Port focuses on the algorithmic intent. Some MATLAB special-cases (the
re-triangulation of iLayer-1 in edge_insertion case 2) are non-trivial; we
keep them but mark precise edge-cases as TODO when they fall outside the
common path. Behaviour matches MATLAB on typical meshes (Test_Case_1, Block_O).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

import numpy as np

from chilmesh import CHILmesh


@dataclass
class LayerState:
    """Snapshot of OE/IE/OV/IV membership per layer. Tracks mutations.

    Route ops (edge_removal, edge_bisection, edge_insertion) can shift vertex
    membership across layers. Call ``sync`` after each layer to refresh the
    snapshot so subsequent identify_edges_in_layer calls see consistent state.
    """

    oe: List[np.ndarray]  # per-layer outer elements
    ie: List[np.ndarray]  # per-layer inner elements
    ov: List[np.ndarray]  # per-layer outer vertices
    iv: List[np.ndarray]  # per-layer inner vertices
    mutated: bool = False

    @classmethod
    def from_domain(cls, domain: CHILmesh) -> "LayerState":
        """Snapshot current layer membership from a domain CHILmesh."""
        layers = domain.layers
        nl = int(getattr(domain, "n_layers", 0) or 0)
        return cls(
            oe=[np.asarray(layers["OE"][i], dtype=int) for i in range(nl)],
            ie=[np.asarray(layers["IE"][i], dtype=int) for i in range(nl)],
            ov=[np.asarray(layers["OV"][i], dtype=int) for i in range(nl)],
            iv=[np.asarray(layers["IV"][i], dtype=int) for i in range(nl)],
        )

    def sync(self, domain: CHILmesh) -> None:
        """Refresh snapshot from domain after route ops have mutated it."""
        layers = domain.layers
        nl = int(getattr(domain, "n_layers", 0) or 0)
        for i in range(min(nl, len(self.oe))):
            self.oe[i] = np.asarray(layers["OE"][i], dtype=int)
            self.ie[i] = np.asarray(layers["IE"][i], dtype=int)
            self.ov[i] = np.asarray(layers["OV"][i], dtype=int)
            self.iv[i] = np.asarray(layers["IV"][i], dtype=int)
        self.mutated = False

    def mark_mutated(self) -> None:
        self.mutated = True


@dataclass
class WorkingMesh:
    """Mutable scratch state during tri2quad."""

    points: np.ndarray  # (n_verts, 3) — original points; not grown during sweep
    quads: List[np.ndarray]  # list of (4,) quad connectivity rows.
    tris: Optional[List[Optional[np.ndarray]]] = None
    _n_pts: int = field(default=0, init=False, repr=False)
    _extra_pts: List[np.ndarray] = field(default_factory=list, init=False, repr=False)
    # First id still held in ``_extra_pts``; advances on every flush so ids
    # buffered after a flush resolve to the right slot.
    _base: int = field(default=0, init=False, repr=False)
    # vertex id -> indices into ``quads`` that reference it.
    _v2q: Dict[int, Set[int]] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_n_pts", self.points.shape[0])
        object.__setattr__(self, "_base", self.points.shape[0])
        self.quads = [np.asarray(q, dtype=int).ravel() for q in self.quads]
        for i, q in enumerate(self.quads):
            for v in q.tolist():
                self._v2q.setdefault(int(v), set()).add(i)

    def add_quad(self, quad: np.ndarray) -> int:
        idx = len(self.quads)
        row = np.asarray(quad, dtype=int).ravel()
        self.quads.append(row)
        for v in row.tolist():
            self._v2q.setdefault(int(v), set()).add(idx)
        return idx

    def add_point(self, xyz: np.ndarray) -> int:
        # Buffer new points in a list; domain.points is synced at layer
        # boundaries / the end of the sweep via flush_points_to_domain().
        xyz = np.asarray(xyz, dtype=float).ravel()
        if xyz.size == 2:
            xyz = np.array([xyz[0], xyz[1], 0.0])
        idx = self._n_pts
        self._extra_pts.append(xyz)
        object.__setattr__(self, "_n_pts", idx + 1)
        return idx

    @property
    def n_pts(self) -> int:
        """Total point count including buffered new points."""
        return self._n_pts

    def get_extra_point(self, idx: int) -> np.ndarray:
        """Coordinates for a buffered (not yet flushed) new vertex."""
        return self._extra_pts[idx - self._base]

    def quads_with(self, v: int) -> Set[int]:
        """Indices of quads that reference vertex ``v``."""
        return self._v2q.get(int(v), set())

    def replace_vertex_in_quad(self, qi: int, old: int, new: int) -> None:
        """Rewrite ``old`` -> ``new`` in quad ``qi`` and keep the index current."""
        q = self.quads[qi]
        q[q == old] = new
        self._v2q.get(int(old), set()).discard(qi)
        self._v2q.setdefault(int(new), set()).add(qi)

    def flush_points_to_domain(self, domain) -> None:
        """Extend domain.points with all buffered new points in one vstack."""
        if not self._extra_pts:
            return
        extra = np.stack(self._extra_pts)
        domain.points = np.vstack([domain.points, extra])
        self._extra_pts.clear()
        object.__setattr__(self, "_base", self._n_pts)


def edge_removal(domain: CHILmesh, work: WorkingMesh, tri_elem_id: int,
                  bdy_edge_idx_in_tri: int) -> None:
    """Collapse one boundary edge of a tri. Two boundary verts merge to one.

    MATLAB ``edgeRemoval``: midpoint of the edge replaces the "side-1" vert;
    every reference to "side-2" vert is rewritten to "side-1". The tri vanishes
    from the mesh — it is not appended to ``work.quads``.
    """
    edge_ids = domain.elem2edge(tri_elem_id).ravel().astype(int)
    eid = int(edge_ids[bdy_edge_idx_in_tri])
    v_a, v_b = domain.edge2vert(eid).ravel().astype(int).tolist()

    mid = 0.5 * (domain.points[v_a] + domain.points[v_b])
    # Snap v_a to midpoint; rewrite v_b → v_a everywhere.
    domain.points[v_a] = mid
    cl = domain.connectivity_list
    cl[cl == v_b] = v_a
    # Rewrite any existing quads referencing v_b → v_a.
    for qi in list(work.quads_with(v_b)):
        work.replace_vertex_in_quad(qi, v_b, v_a)


def edge_bisection(domain: CHILmesh, work: WorkingMesh, tri_elem_id: int,
                    bdy_edge_idx_in_tri: int) -> Optional[int]:
    """Bisect one tri edge with a new midpoint. Tri becomes a quad.

    Returns the new vertex ID. The companion retriangulation of the opposite
    tri (MATLAB case 2) is performed by the caller (``route_leftover_tri``, the
    layer-interior branch) via ``_split_opposing_tri``.
    """
    edge_ids = domain.elem2edge(tri_elem_id).ravel().astype(int)
    eid = int(edge_ids[bdy_edge_idx_in_tri])
    v_a, v_b = domain.edge2vert(eid).ravel().astype(int).tolist()

    mid = 0.5 * (domain.points[v_a] + domain.points[v_b])
    np_id = work.add_point(mid)
    # np_id only used in work.quads connectivity; domain.points[np_id] never
    # read back so no need to grow domain.points here.

    # Build new quad by slotting np_id between the (v_a, v_b) edge in conn.
    conn = domain.connectivity_list[tri_elem_id, :3].astype(int)
    # Find positions of (v_a, v_b) in conn. Cap at 3 rolls (one full cycle); if the
    # edge appears reversed (ib → ia CCW) swap v_a/v_b so the insertion is consistent.
    for _ in range(3):
        ia = np.where(conn == v_a)[0]
        ib = np.where(conn == v_b)[0]
        if ia.size == 0 or ib.size == 0:
            return None
        if (ia[0] + 1) % 3 == ib[0]:
            break
        if (ib[0] + 1) % 3 == ia[0]:
            v_a, v_b = v_b, v_a  # edge is CCW as v_b→v_a; swap to match convention
            break
        conn = np.roll(conn, -1)
    else:
        return None  # degenerate — v_a or v_b not adjacent in this tri
    # quad = [conn[0], conn[1], np_id, conn[2]]? Not quite. MATLAB inserts
    # np_id between v_a and v_b: [..., v_a, np_id, v_b, ...].
    # Build by walking conn and slotting np_id in between the v_a,v_b pair.
    ia = int(np.where(conn == v_a)[0][0])
    if conn[(ia + 1) % 3] != v_b:
        v_a, v_b = v_b, v_a
        ia = int(np.where(conn == v_a)[0][0])
    quad = np.array([conn[ia], np_id, conn[(ia + 1) % 3], conn[(ia + 2) % 3]], dtype=int)
    work.add_quad(quad)

    # Flag tri as consumed by zeroing its connectivity (caller drops zero rows).
    domain.connectivity_list[tri_elem_id, :] = 0
    return np_id


def _ccw_tri(tri: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Return ``tri`` reordered to positive (CCW) signed area."""
    p = points[tri, :2]
    area = 0.5 * (
        (p[1, 0] - p[0, 0]) * (p[2, 1] - p[0, 1])
        - (p[2, 0] - p[0, 0]) * (p[1, 1] - p[0, 1])
    )
    return tri[::-1].copy() if area < 0 else tri


def _split_opposing_tri(domain: CHILmesh, edge_id: int, np_id: int,
                         consumed_tri_id: int,
                         work: Optional["WorkingMesh"] = None) -> Optional[int]:
    """Split the iLayer-1 tri sharing ``edge_id`` at midpoint ``np_id``.

    MATLAB ``edgeBisection`` Case 2 (``edgeBisection.m:47-79``). When
    ``edge_bisection`` bisects an interior layer-boundary edge, the new midpoint
    ``np_id`` lands on that edge — leaving a hanging node on the neighbouring
    tri in iLayer-1. That neighbour must be re-triangulated so the working tri
    domain stays conforming.

    Because ``np_id`` lies *on* the shared edge, the only valid split is the
    neighbour's apex joined to ``np_id`` — exactly what MATLAB's
    ``delaunayTriangulation([opp_conn, np_id])`` yields once its degenerate
    collinear tri is dropped, so we build the two tris directly (no Delaunay).

    Returns the appended element id, or ``None`` if ``edge_id`` has no opposite
    tri (a true mesh-boundary edge) or the neighbour is not a clean triangle.
    """
    pair = domain.edge2elem(edge_id).ravel().astype(int).tolist()
    opp = [e for e in pair if e != consumed_tri_id and e >= 0]
    if not opp:
        return None
    opp_id = opp[0]

    opp_conn = domain.connectivity_list[opp_id, :3].astype(int)
    v_a, v_b = domain.edge2vert(edge_id).ravel().astype(int).tolist()
    apex = [v for v in opp_conn.tolist() if v != v_a and v != v_b]
    if len(apex) != 1:
        return None  # opp already consumed / not a tri on this edge.
    apex = apex[0]

    # #81: every id _ccw_tri indexes into domain.points must be resolvable.
    # np_id buffered in WorkingMesh is not flushed until the sweep ends, and a
    # prior split can leave apex/v_a/v_b pointing past the current point store.
    # Skip (leave the tri for the deferred pass) rather than index out of bounds.
    n_pts = domain.points.shape[0]
    if any(int(v) >= n_pts for v in (apex, v_a, v_b, np_id)):
        return None

    pts = domain.points
    tri1 = _ccw_tri(np.array([apex, v_a, np_id], dtype=int), pts)
    tri2 = _ccw_tri(np.array([apex, np_id, v_b], dtype=int), pts)

    width = domain.connectivity_list.shape[1]
    domain.connectivity_list[opp_id, :3] = tri1
    if width > 3:  # keep padded-triangle convention (repeat last vert)
        domain.connectivity_list[opp_id, 3:] = tri1[-1]

    new_id = domain.connectivity_list.shape[0]
    row = np.empty((1, width), dtype=domain.connectivity_list.dtype)
    row[0, :3] = tri2
    if width > 3:
        row[0, 3:] = tri2[-1]
    domain.connectivity_list = np.vstack([domain.connectivity_list, row])
    return new_id


def edge_insertion(domain: CHILmesh, work: WorkingMesh, tri_elem_id: int,
                    bdy_vert_id: int) -> Optional[int]:
    """Split a triangle through one of its verts by inserting a new edge.

    Simplified port. New point sits along an interior edge attached to
    ``bdy_vert_id``; the tri splits into a quad whose connectivity is added
    to ``work.quads``. Returns the new vertex ID.

    The MATLAB original additionally retriangulates iLayer-1 to absorb the
    new vertex; we currently do that in a deferred pass after the layer sweep
    completes.
    """
    conn = domain.connectivity_list[tri_elem_id, :3].astype(int)
    if bdy_vert_id not in conn.tolist():
        # Fall back to first vert.
        bdy_vert_id = int(conn[0])

    # Pick an interior edge from bdy_vert_id (one whose other endpoint isn't on the layer bdy).
    edges = list(domain.get_vertex_edges(int(bdy_vert_id)))
    if not edges:
        return None

    other_verts = []
    for e in edges:
        u, v = domain.edge2vert(int(e)).ravel().astype(int).tolist()
        other = v if u == bdy_vert_id else u
        if other in conn.tolist() and other != bdy_vert_id:
            other_verts.append(other)
    if not other_verts:
        return None

    # New point at 1/3 of the way along the first opposing edge.
    other = other_verts[0]
    new_xyz = (
        (2.0 / 3.0) * domain.points[bdy_vert_id]
        + (1.0 / 3.0) * domain.points[other]
    )
    np_id = work.add_point(new_xyz)

    # Quad = [bdy_vert_id, np_id, other, third_vert_of_tri]
    third = int([v for v in conn if v not in (bdy_vert_id, other)][0])
    quad = np.array([bdy_vert_id, np_id, other, third], dtype=int)
    work.add_quad(quad)

    domain.connectivity_list[tri_elem_id, :] = 0
    return np_id


# ── Conforming sweep state (QuADMESH tri2quad T-junction fix) ────────────────


def _corner_sines(poly: np.ndarray) -> np.ndarray:
    """Signed sine of each interior corner of a CCW polygon (> 0 = convex)."""
    k = poly.shape[0]
    out = np.empty(k)
    for i in range(k):
        e1 = poly[(i + 1) % k] - poly[i]
        e2 = poly[(i - 1) % k] - poly[i]
        n = float(np.hypot(*e1) * np.hypot(*e2))
        out[i] = (e1[0] * e2[1] - e1[1] * e2[0]) / n if n > 0.0 else -1.0
    return out


def _signed_area(poly: np.ndarray) -> float:
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(x @ np.roll(y, -1) - np.roll(x, -1) @ y)


class SweepContext:
    """Live mesh topology for the per-layer QuADMESH+ sweep.

    The sweep converts layers innermost first. A leftover triangle in layer
    ``L`` is closed into a quad by adding one vertex on its outer ring: the
    ring edge it shares with layer ``L - 1`` (still all triangles), or the
    domain boundary when ``L == 0``. The triangle across that ring edge is
    split at the new vertex, so the working mesh stays conforming and the
    inner layers never see a hanging node.

    Classification uses the live connectivity (``domain.connectivity_list``
    rows plus ``work.quads``), not the parent's adjacency tables, because the
    sweep appends rows and vertices as it goes. ``sync`` rebuilds the parent's
    adjacency at each layer start so ``identify_edges_in_layer`` sees the
    current mesh.
    """

    MAX_FAN = 64
    SPLIT_FRACTIONS = (0.5, 1.0 / 3.0, 0.25, 1.0 / 6.0)
    APEX_FRACTIONS = (0.15, 0.25, 1.0 / 3.0, 0.5)
    MIN_SINE = 0.06  # about 3.4 degrees from a straight or a zero angle

    def __init__(self, domain: CHILmesh, work: WorkingMesh, consumed: set,
                 refused: set, boundary_edges) -> None:
        self.domain = domain
        self.work = work
        self.consumed = consumed
        self.refused = refused
        nl = int(getattr(domain, "n_layers", 0) or 0)
        src = domain.layers
        self.layers: Dict[str, list] = {
            k: [np.asarray(a, dtype=int).copy() for a in src.get(k, [])]
            for k in ("OE", "IE", "OV", "IV", "bEdgeIDs")
        }
        domain.layers = self.layers  # private copy; caller restores the original
        self.elem_layer: Dict[int, Tuple[int, str]] = {}
        for li in range(nl):
            for kind in ("OE", "IE"):
                for e in self.layers[kind][li].tolist():
                    self.elem_layer.setdefault(int(e), (li, kind))
        self.v2t: Dict[int, Set[int]] = {}
        cl = domain.connectivity_list
        for r in range(cl.shape[0]):
            for v in set(int(x) for x in cl[r, :3]):
                self.v2t.setdefault(v, set()).add(r)
        self.dom_bdy: Set[frozenset] = {frozenset((int(a), int(b))) for a, b in boundary_edges}
        self.dom_bdy_verts: Set[int] = {v for e in self.dom_bdy for v in e}
        self.layer_idx = nl - 1
        self.dirty = False

    # -- geometry / topology queries ------------------------------------------

    def xy(self, v: int) -> np.ndarray:
        v = int(v)
        if v < self.domain.points.shape[0]:
            return np.asarray(self.domain.points[v, :2], dtype=float)
        return np.asarray(self.work.get_extra_point(v)[:2], dtype=float)

    def poly(self, verts) -> np.ndarray:
        return np.array([self.xy(v) for v in verts], dtype=float)

    def tri_row(self, r: int) -> List[int]:
        return [int(x) for x in self.domain.connectivity_list[r, :3]]

    def live(self, r: int) -> bool:
        """Row ``r`` is still a triangle of the working mesh."""
        if r in self.consumed and r not in self.refused:
            return False
        return len(set(self.tri_row(r))) == 3

    def _outer(self, r: int) -> bool:
        lay = self.elem_layer.get(r)
        return lay is not None and lay[0] < self.layer_idx and self.live(r)

    def outer_tris_on_edge(self, u: int, v: int) -> List[int]:
        both = self.v2t.get(u, set()) & self.v2t.get(v, set())
        return [r for r in both if self._outer(r)]

    def is_ring_edge(self, u: int, v: int) -> bool:
        if self.layer_idx == 0:
            return frozenset((u, v)) in self.dom_bdy
        return bool(self.outer_tris_on_edge(u, v))

    def is_ring_vert(self, v: int) -> bool:
        if self.layer_idx == 0:
            return v in self.dom_bdy_verts
        return any(self._outer(r) for r in self.v2t.get(v, ()))

    def elem_verts(self, el: Tuple[str, int]) -> List[int]:
        kind, i = el
        if kind == "q":
            return [int(x) for x in self.work.quads[i]]
        return self.tri_row(i)

    def elems_on_edge(self, u: int, v: int) -> List[Tuple[str, int]]:
        """Live quads and triangles that have ``(u, v)`` as an edge."""
        out: List[Tuple[str, int]] = []
        for qi in self.work.quads_with(u) & self.work.quads_with(v):
            q = [int(x) for x in self.work.quads[qi]]
            k = len(q)
            if any({q[j], q[(j + 1) % k]} == {u, v} for j in range(k)):
                out.append(("q", qi))
        for r in self.v2t.get(u, set()) & self.v2t.get(v, set()):
            if self.live(r):
                out.append(("t", r))
        return out

    # -- mutations ------------------------------------------------------------

    def _set_row(self, r: int, verts: List[int]) -> None:
        cl = self.domain.connectivity_list
        cl[r, :3] = verts
        if cl.shape[1] > 3:  # keep padded-triangle convention
            cl[r, 3:] = verts[-1]

    def retire_tri(self, r: int) -> None:
        """Remove triangle row ``r`` from the working mesh (zeroed row)."""
        for v in set(self.tri_row(r)):
            self.v2t.get(v, set()).discard(r)
        self.domain.connectivity_list[r, :] = 0

    def replace_vertex(self, el: Tuple[str, int], old: int, new: int) -> None:
        kind, i = el
        if kind == "q":
            self.work.replace_vertex_in_quad(i, old, new)
            return
        self._set_row(i, [new if v == old else v for v in self.tri_row(i)])
        self.v2t.get(old, set()).discard(i)
        self.v2t.setdefault(new, set()).add(i)

    def split_outer(self, r: int, x: int, y: int, m: int) -> int:
        """Split triangle ``r`` across its edge ``(x, y)`` at new vertex ``m``.

        Row ``r`` keeps the half on ``x``; the half on ``y`` is appended as a
        new row in the same layer list. Stored vertex order (orientation) is
        kept in both halves. Returns the new row id.
        """
        row = self.tri_row(r)
        keep = [m if v == y else v for v in row]
        new = [m if v == x else v for v in row]
        self._set_row(r, keep)
        cl = self.domain.connectivity_list
        add = np.zeros((1, cl.shape[1]), dtype=cl.dtype)
        add[0, :3] = new
        if cl.shape[1] > 3:
            add[0, 3:] = new[-1]
        nid = cl.shape[0]
        self.domain.connectivity_list = np.vstack([cl, add])
        self.v2t.get(y, set()).discard(r)
        self.v2t.setdefault(m, set()).add(r)
        for v in new:
            self.v2t.setdefault(v, set()).add(nid)
        lay = self.elem_layer.get(r)
        if lay is not None:
            li, kind = lay
            self.elem_layer[nid] = lay
            self.layers[kind][li] = np.append(self.layers[kind][li], nid)
            for key in ("IV", "OV"):
                arr = self.layers[key][li]
                if x in arr and y in arr:
                    self.layers[key][li] = np.append(arr, m)
        self.dirty = True
        return nid

    def split_ring_edge(self, x: int, y: int, m: int,
                        outer: Optional[int]) -> None:
        """Insert ``m`` on ring edge ``(x, y)``: split the outer tri, or the
        domain-boundary edge when sweeping layer 0."""
        if outer is not None:
            self.split_outer(outer, x, y, m)
        else:
            self.dom_bdy.discard(frozenset((x, y)))
            self.dom_bdy.add(frozenset((x, m)))
            self.dom_bdy.add(frozenset((m, y)))
            self.dom_bdy_verts.add(m)
        self.dirty = True

    def sync(self) -> None:
        """Make the parent CHILmesh match the working mesh (points, rows,
        adjacency) so per-layer identification sees the current topology."""
        if not self.dirty:
            return
        d = self.domain
        self.work.flush_points_to_domain(d)
        cl = d.connectivity_list
        for r in self.consumed:
            if r not in self.refused and r < cl.shape[0] and cl[r].any():
                self.retire_tri(r)
        d.n_verts = d.points.shape[0]
        d.n_elems = d.connectivity_list.shape[0]
        d._build_adjacencies(validate=False)
        self.dirty = False

    # -- leftover-triangle operations -----------------------------------------

    def _ring_target(self, x: int, y: int) -> Tuple[bool, Optional[int]]:
        """``(ok, outer_row)`` for ring edge ``(x, y)``; ok is False when the
        edge is not a clean two-element ring edge."""
        if self.layer_idx == 0:
            return frozenset((x, y)) in self.dom_bdy, None
        outer = self.outer_tris_on_edge(x, y)
        if len(outer) != 1:
            return False, None
        return True, outer[0]

    def _bisect_point(self, a: int, b: int, c: int,
                      outer: Optional[int]) -> Optional[np.ndarray]:
        """New vertex for closing ``(a, b, c)`` across ring edge ``(a, b)``.

        On the domain boundary (layer 0) it is the edge midpoint, as in MATLAB
        edgeBisection. Inside the mesh a midpoint would give the quad a
        180-degree corner (a geometric triangle), so the point moves from the
        midpoint toward the outer triangle's apex; the fraction with the best
        worst corner over the quad and both outer halves wins. ``None`` when
        no fraction keeps every corner above ``MIN_SINE``.
        """
        pa, pb, pc = self.xy(a), self.xy(b), self.xy(c)
        mid = 0.5 * (pa + pb)
        if outer is None:
            return mid
        apex = [v for v in self.tri_row(outer) if v not in (a, b)]
        if len(apex) != 1:
            return None
        pz = self.xy(apex[0])
        best = None
        for t in self.APEX_FRACTIONS:
            pm = mid + t * (pz - mid)
            worst = min(
                float(_corner_sines(np.array([pa, pm, pb, pc])).min()),
                float(_corner_sines(np.array([pa, pz, pm])).min()),
                float(_corner_sines(np.array([pm, pz, pb])).min()),
            )
            if worst > self.MIN_SINE and (best is None or worst > best[0]):
                best = (worst, pm)
        return None if best is None else best[1]

    def bisect(self, r: int, a: int, b: int, c: int, flat_ok: bool = False) -> bool:
        """Close CCW triangle ``(a, b, c)`` with ring edge ``(a, b)`` into the
        quad ``(a, m, b, c)`` and split the element across ``(a, b)`` at
        ``m`` (see ``_bisect_point``). ``flat_ok`` allows the edge midpoint
        inside the mesh as a last resort."""
        ok, outer = self._ring_target(a, b)
        if not ok:
            return False
        pm = self._bisect_point(a, b, c, outer)
        if pm is None:
            if not flat_ok:
                return False
            pm = 0.5 * (self.xy(a) + self.xy(b))
        m = self.work.add_point(np.append(pm, 0.0))
        self.work.add_quad(np.array([a, m, b, c], dtype=int))
        self.retire_tri(r)
        self.split_ring_edge(a, b, m, outer)
        return True

    def _fan(self, r: int, b: int, start: int) -> Optional[Tuple[int, List[Tuple[str, int]]]]:
        """Walk the elements around ``b`` from triangle ``r`` across edge
        ``(b, start)`` until a ring edge ``(b, s)``. Returns ``(s, elems)``
        or ``None`` when the walk is non-manifold, open, or too long."""
        prev: Tuple[str, int] = ("t", r)
        cur = start
        elems: List[Tuple[str, int]] = []
        for _ in range(self.MAX_FAN):
            if self.is_ring_edge(b, cur):
                return (cur, elems) if elems else None
            nxt_elems = [e for e in self.elems_on_edge(b, cur) if e != prev]
            if len(nxt_elems) != 1:
                return None
            el = nxt_elems[0]
            if el == ("t", r) or el in elems:
                return None
            vs = self.elem_verts(el)
            if vs.count(b) != 1:
                return None
            k = len(vs)
            i = vs.index(b)
            nbrs = [vs[(i - 1) % k], vs[(i + 1) % k]]
            if cur not in nbrs:
                return None
            nxt = nbrs[1] if nbrs[0] == cur else nbrs[0]
            elems.append(el)
            prev, cur = el, nxt
        return None

    def vertex_split(self, r: int, b: int, p: int, q: int) -> bool:
        """Close CCW triangle ``(b, p, q)`` whose only ring contact is vertex
        ``b``: move ``b`` to a new vertex ``n`` on ring edge ``(b, s)`` in the
        elements between the triangle and that edge, so the triangle gains a
        fourth corner. The element across ``(b, s)`` is split at ``n``.
        Picks the side and the split fraction with the best worst corner."""
        best = None
        for side, start in (("A", p), ("B", q)):
            fan = self._fan(r, b, start)
            if fan is None:
                continue
            s, elems = fan
            ok, outer = self._ring_target(b, s)
            if not ok:
                continue
            pb, ps = self.xy(b), self.xy(s)
            olds = []
            for el in elems:
                vs = self.elem_verts(el)
                sign = 1.0 if _signed_area(self.poly(vs)) >= 0.0 else -1.0
                olds.append((vs, sign, sign * _corner_sines(self.poly(vs))))
            for t in self.SPLIT_FRACTIONS:
                pn = pb + t * (ps - pb)
                worst = np.inf
                valid = True
                for vs, sign, o_sin in olds:
                    poly = np.array([pn if v == b else self.xy(v) for v in vs])
                    if sign * _signed_area(poly) <= 0.0:
                        valid = False
                        break
                    n_sin = sign * _corner_sines(poly)
                    convex = o_sin > 0.0
                    if np.any(n_sin[convex] <= np.minimum(self.MIN_SINE, o_sin[convex])):
                        valid = False
                        break
                    if convex.any():
                        worst = min(worst, float(n_sin[convex].min()))
                if not valid:
                    continue
                quad_pts = (
                    np.array([pb, pn, self.xy(p), self.xy(q)]) if side == "A"
                    else np.array([pb, self.xy(p), self.xy(q), pn])
                )
                if _signed_area(quad_pts) <= 0.0:
                    continue
                q_sin = _corner_sines(quad_pts)
                if q_sin.min() <= self.MIN_SINE:
                    continue
                worst = min(worst, float(q_sin.min()))
                if best is None or worst > best[0]:
                    best = (worst, side, t, s, elems, outer, pn)
        if best is None:
            return False
        _, side, _, s, elems, outer, pn = best
        n = self.work.add_point(np.append(pn, 0.0))
        for el in elems:
            self.replace_vertex(el, b, n)
        quad = [b, n, p, q] if side == "A" else [b, p, q, n]
        self.work.add_quad(np.array(quad, dtype=int))
        self.retire_tri(r)
        self.split_ring_edge(b, s, n, outer)
        return True

    def route(self, r: int, refuse_boundary_merge: bool) -> Optional[bool]:
        """Conforming ``removeTrianglesFun``: see ``route_leftover_tri``."""
        if not self.live(r):
            return None
        tri = self.tri_row(r)
        if _signed_area(self.poly(tri)) < 0.0:
            tri = tri[::-1]
        a, b, c = tri
        sides = ((a, b, c), (b, c, a), (c, a, b))
        ring = [s for s in sides if self.is_ring_edge(s[0], s[1])]
        if self.layer_idx == 0 and len(ring) >= 2 and refuse_boundary_merge:
            return False  # #98 option A: leave as a boundary triangle
        ring.sort(key=lambda s: -float(np.hypot(*(self.xy(s[0]) - self.xy(s[1])))))
        for x, y, z in ring:
            if self.bisect(r, x, y, z):
                return True
        for x, y, z in sides:
            if self.is_ring_vert(x) and self.vertex_split(r, x, y, z):
                return True
        for x, y, z in ring:
            if self.bisect(r, x, y, z, flat_ok=True):
                return True
        return None


def route_leftover_tri(
    domain: CHILmesh,
    work: WorkingMesh,
    tri_elem_id: int,
    layer_idx: int,
    on_mesh_boundary: bool,
    can_remove_edges: bool,
    sub_b_edge_set: set,
    sub_b_vert_set: set,
    refuse_boundary_merge: bool = False,
    preserve_boundary_verts: bool = False,
    ctx: Optional[SweepContext] = None,
) -> Optional[bool]:
    """Apply the right sub-op given tri's boundary-edge count.

    Mirrors MATLAB ``removeTrianglesFun`` switch. ``sub_b_edge_set`` is the
    set of sub-mesh boundary edge IDs in *parent* indexing; ``sub_b_vert_set``
    likewise for verts.

    Returns ``True`` if the tri was converted (paired, cleared, or consumed in
    place), ``False`` if it was refused (left as a boundary triangle) because
    ``refuse_boundary_merge`` is set, and ``None`` if no sub-op applied and the
    tri is unchanged. The caller passes unchanged tris on to the closing pass.

    A boundary-edge collapse (``edgeRemoval``) is replaced by a boundary-edge
    bisection when the collapse would merge two vertices of an emitted quad;
    the collapse would turn that quad into a triangle, or when
    ``preserve_boundary_verts`` is set (a collapse would move two original
    boundary vertices).

    With ``ctx`` (the per-layer sweep), the tri is classified on its live
    outer ring instead of ``sub_b_edge_set`` / ``sub_b_vert_set``, and every
    op keeps the mesh conforming: a ring-edge bisection splits the element
    across the edge, and a tri that touches the ring at one vertex is closed
    by a vertex split (``SweepContext.vertex_split``). Edges are never
    collapsed. ``None`` leaves the tri for the closing passes.
    """
    if ctx is not None:
        return ctx.route(tri_elem_id, refuse_boundary_merge)
    edge_ids = domain.elem2edge(tri_elem_id).ravel().astype(int)
    bdy_edges_local = [
        i for i, e in enumerate(edge_ids) if int(e) in sub_b_edge_set
    ]
    n_bdy = len(bdy_edges_local)

    conn = domain.connectivity_list[tri_elem_id, :3].astype(int)
    bdy_verts_in_tri = [int(v) for v in conn if int(v) in sub_b_vert_set]

    # 059: with preserve_boundary_verts, a collapse of a domain-boundary edge
    # would move two original boundary vertices; bisect that edge instead.
    on_domain_boundary = preserve_boundary_verts and on_mesh_boundary

    def _collapse_is_safe(local_idx: int) -> bool:
        v_a, v_b = domain.edge2vert(int(edge_ids[local_idx])).ravel().astype(int).tolist()
        return not any(
            (q == v_a).any() and (q == v_b).any() for q in work.quads
        )

    if not on_mesh_boundary and n_bdy >= 1:
        # MATLAB edgeBisection Case 2: bisect the layer-interior edge, then
        # re-triangulate the iLayer-1 neighbour at the new midpoint so the
        # working tri domain stays conforming (edgeBisection.m:47-79).
        eid = int(edge_ids[bdy_edges_local[0]])
        np_id = edge_bisection(domain, work, tri_elem_id, bdy_edges_local[0])
        if np_id is not None:
            _split_opposing_tri(domain, eid, np_id, tri_elem_id, work)
    elif on_mesh_boundary and n_bdy == 0:
        if not bdy_verts_in_tri:
            return None
        edge_insertion(domain, work, tri_elem_id, bdy_verts_in_tri[0])
    elif not on_mesh_boundary and n_bdy == 0:
        if not bdy_verts_in_tri:
            return None
        edge_insertion(domain, work, tri_elem_id, bdy_verts_in_tri[0])
    elif on_mesh_boundary and n_bdy in (2, 3):
        if refuse_boundary_merge:
            return False  # #98 option A: leave as a boundary triangle
        if not bdy_verts_in_tri:
            return None
        edge_insertion(domain, work, tri_elem_id, bdy_verts_in_tri[0])
    elif (on_mesh_boundary and n_bdy == 1 and can_remove_edges
          and not on_domain_boundary
          and _collapse_is_safe(bdy_edges_local[0])):
        edge_removal(domain, work, tri_elem_id, bdy_edges_local[0])
    elif on_mesh_boundary and n_bdy == 1:
        # MATLAB removeTrianglesFun: edgeBisection(1) when canRemoveEdges=false;
        # also used when a collapse would degenerate an emitted quad.
        if edge_bisection(domain, work, tri_elem_id, bdy_edges_local[0]) is None:
            return None
    else:
        return None  # no sub-op applies; tri unchanged
    return True


# ── T019 — isolated-tri handling ─────────────────────────────────────────────

def handle_isolated_tris(
    layer_conn: np.ndarray,
    layer_global_ids: np.ndarray,
    consumed: set,
    pts: np.ndarray,
    work: WorkingMesh,
) -> set:
    """Pair remaining isolated tris in a layer via edge-swap fixup (CR-5, p66).

    After the main pairing sweep, some tris may be isolated (no eligible
    neighbour in the same layer). For each such tri, attempt walk_isolated_tri
    to flip its neighbourhood so it gains a pairable neighbour, then merge.

    Thesis CR-5 (p66): intentional vertex-pairing + post-match edge-swap fixup.
    Returns the set of newly consumed global IDs.
    """
    from ._recombine import walk_isolated_tri

    adj: dict = {}
    edge2tris: dict = {}
    for i, row in enumerate(layer_conn):
        a, b, c = int(row[0]), int(row[1]), int(row[2])
        for e in (tuple(sorted((a, b))), tuple(sorted((b, c))), tuple(sorted((a, c)))):
            edge2tris.setdefault(e, []).append(i)
    for tris_list in edge2tris.values():
        if len(tris_list) == 2:
            adj.setdefault(tris_list[0], []).append(tris_list[1])
            adj.setdefault(tris_list[1], []).append(tris_list[0])

    global_to_local = {int(g): i for i, g in enumerate(layer_global_ids)}
    local_consumed = set(
        global_to_local[g] for g in consumed if g in global_to_local
    )

    work.tris = [row.copy() for row in layer_conn]
    newly_consumed: set = set()

    n = len(layer_conn)
    for li in range(n):
        if li in local_consumed:
            continue
        nbs = [nb for nb in adj.get(li, []) if nb not in local_consumed]
        if nbs:
            continue  # has neighbour — will be handled by main sweep
        # Isolated: attempt walk.
        walk_isolated_tri(work, li, pts, max_hops=4)
        # Refresh adjacency for this tri after potential flip.
        tri_new = work.tris[li]
        if tri_new is None:
            continue
        a, b, c = int(tri_new[0]), int(tri_new[1]), int(tri_new[2])
        new_nbs = []
        for e in (tuple(sorted((a, b))), tuple(sorted((b, c))), tuple(sorted((a, c)))):
            for nb in edge2tris.get(e, []):
                if nb != li and nb not in local_consumed:
                    new_nbs.append(nb)
        if not new_nbs:
            continue
        nb = new_nbs[0]
        # Merge li + nb → quad.
        try:
            va_set = set(int(v) for v in work.tris[li][:3])
            vb_set = set(int(v) for v in work.tris[nb][:3])
            shared = list(va_set & vb_set)
            if len(shared) != 2:
                continue
            unique_a = list(va_set - vb_set)[0]
            unique_b = list(vb_set - va_set)[0]
            s1, s2 = shared
            quad = np.array([unique_a, s1, unique_b, s2], dtype=int)
            work.add_quad(quad)
            local_consumed.add(li)
            local_consumed.add(nb)
            ga = int(layer_global_ids[li])
            gb = int(layer_global_ids[nb])
            newly_consumed.add(ga)
            newly_consumed.add(gb)
        except (IndexError, ValueError):
            continue

    return newly_consumed
