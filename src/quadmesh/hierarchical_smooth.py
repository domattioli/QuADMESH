"""Hierarchical (selective local-first) smoothing. Spec-056, issue #104.

Smooth only where defects live: select worst region (skew / layer / valence
policy), split into edge-connected patches, solve each patch with the existing
Balendran FEM formulation on a small compacted submesh — the submesh's own
boundary is exactly (patch rim) + (true domain boundary), so
``_balendran_smooth``'s kinf pinning holds the far field + domain boundary
fixed with zero solver changes. Optional guarded cheap global pass. Default
stage plan = local-FEM only. Deterministic: no RNG, id-ordered tie-breaks.
Additive: default pipeline untouched.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np

from chilmesh import CHILmesh, element_quality

from .remove_unused import remove_unused_vertices


@dataclass
class HierarchicalResult:
    """Metadata for a hierarchical_smoother run (spec-056 data-model)."""
    n_selected: int = 0
    n_patches: int = 0
    fell_back: bool = False
    patch_iters: list = field(default_factory=list)
    timings: dict = field(default_factory=dict)


@dataclass
class Patch:
    """One edge-connected selected component, compacted to a submesh.

    free_mask marks submesh vertices NOT on the submesh boundary — the only
    vertices a patch solve may move (rim + domain boundary stay pinned).
    """
    elem_ids: np.ndarray
    vert_map: np.ndarray
    submesh: CHILmesh
    free_mask: np.ndarray


def _mean_skew(points: np.ndarray, conn: np.ndarray) -> float:
    return float(np.mean(element_quality(points, conn, metric="skew")))


def select_region(
    mesh: CHILmesh,
    policy: str = "skew",
    *,
    frac: float = 0.075,
    layers: tuple = (0,),
    dev: int = 2,
    dilate: bool = True,
) -> np.ndarray:
    """Select target element ids for FEM smoothing. Pure, deterministic.

    Policies (spec-056 FR-002): 'skew' = worst-frac by skew quality + optional
    1-ring; 'layer' = elements of the given domain layers (error when layer
    data absent — never triggers skeletonization); 'valence' = elements
    incident to interior vertices with |valence - 4| >= dev + optional 1-ring.
    """
    conn = np.asarray(mesh.connectivity_list)
    n = int(mesh.n_elems)
    if policy == "skew":
        k = int(np.ceil(frac * n))
        if k <= 0:
            return np.empty(0, dtype=int)
        q = element_quality(mesh.points, conn, metric="skew")
        order = np.lexsort((np.arange(n), q))  # ascending q, id tie-break
        seed = order[:k]
    elif policy == "layer":
        lay = getattr(mesh, "layers", None)
        if not lay or not lay.get("OE"):
            raise ValueError(
                "layer policy needs a layer decomposition on the mesh; "
                "use policy='skew' (spec-056 R3 — no implicit skeletonization)"
            )
        parts = [np.asarray(mesh.elements_in_layer(i)) for i in layers]
        seed = np.concatenate(parts) if parts else np.empty(0, dtype=int)
        if seed.size == 0:
            return np.empty(0, dtype=int)
        seed = np.unique(seed.astype(int))
    elif policy == "valence":
        bverts = set(np.unique(mesh.edge2vert(mesh.boundary_edges()).ravel()).tolist())
        bad_elems = []
        for v in range(int(mesh.n_verts)):
            if v in bverts:
                continue
            inc = mesh.get_vertex_elements(v)
            if abs(len(inc) - 4) >= dev:
                bad_elems.extend(inc)
        if not bad_elems:
            return np.empty(0, dtype=int)
        seed = np.unique(np.asarray(bad_elems, dtype=int))
    else:
        raise ValueError(f"unknown selection policy: {policy!r}")

    if dilate and policy in ("skew", "valence") and seed.size:
        verts = np.unique(conn[seed].ravel())
        ring = set(seed.tolist())
        for v in verts.tolist():
            ring.update(mesh.get_vertex_elements(int(v)))
        seed = np.asarray(sorted(ring), dtype=int)

    return np.unique(seed.astype(int))


def _build_patches(mesh: CHILmesh, elem_ids: np.ndarray, min_interior: int = 4) -> list:
    """Edge-connected components of the selection, compacted to submeshes.

    Components smaller than min_interior FREE vertices are skipped (maximal
    components have no selected neighbor to merge into). Shared vertices
    between two components are rim in both (their element stars are split),
    so write-backs never conflict.
    """
    conn = np.asarray(mesh.connectivity_list)
    sel = np.unique(np.asarray(elem_ids, dtype=int))
    if sel.size == 0:
        return []
    in_sel = np.zeros(int(mesh.n_elems), dtype=bool)
    in_sel[sel] = True

    e2e = mesh.edge2elem()  # (n_edges, 2), -1 = boundary
    both = (e2e[:, 0] >= 0) & (e2e[:, 1] >= 0)
    pairs = e2e[both]
    pairs = pairs[in_sel[pairs[:, 0]] & in_sel[pairs[:, 1]]]

    nbr = {int(e): [] for e in sel.tolist()}
    for a, b in pairs.tolist():
        nbr[int(a)].append(int(b))
        nbr[int(b)].append(int(a))

    seen = set()
    patches = []
    for start in sel.tolist():  # ascending id -> deterministic components
        s = int(start)
        if s in seen:
            continue
        comp = []
        stack = [s]
        seen.add(s)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nb in sorted(nbr.get(cur, ())):
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comp = np.asarray(sorted(comp), dtype=int)

        vert_map = np.unique(conn[comp].ravel())
        new_idx = np.full(int(mesh.n_verts), -1, dtype=int)
        new_idx[vert_map] = np.arange(vert_map.size)
        conn_sub = new_idx[conn[comp]]
        pts_sub = np.asarray(mesh.points)[vert_map].copy()
        sub = CHILmesh(
            connectivity=conn_sub,
            points=pts_sub,
            compute_layers=False,
            compute_adjacencies=True,
            build_spatial_indices=False,
            validate=False,
        )
        bsub = np.unique(sub.edge2vert(sub.boundary_edges()).ravel())
        free_mask = np.ones(vert_map.size, dtype=bool)
        free_mask[bsub] = False
        if int(free_mask.sum()) < min_interior:
            continue
        patches.append(Patch(elem_ids=comp, vert_map=vert_map, submesh=sub, free_mask=free_mask))
    return patches


def _solve_patch(patch: Patch, eps: float = 1e-3, max_patch_iter: int = 10) -> int:
    """Iterate Balendran FEM on the patch submesh to a quality-delta halt.

    Best-so-far coordinates kept; a worsening pass reverts and halts
    (spec-056 FR-007, clarification Q4). Returns passes applied.
    """
    from .post_process import _balendran_smooth

    sub = patch.submesh
    conn = np.asarray(sub.connectivity_list)
    best_pts = np.asarray(sub.points).copy()
    best_q = _mean_skew(best_pts, conn)
    prev_q = best_q
    iters = 0
    for _ in range(int(max_patch_iter)):
        try:
            new_pts = _balendran_smooth(sub)
        except Exception:
            break
        sub.points[:, :2] = new_pts[:, :2]
        iters += 1
        q = _mean_skew(np.asarray(sub.points), conn)
        if q > best_q:
            best_q = q
            best_pts = np.asarray(sub.points).copy()
        if q - prev_q < eps:
            break
        prev_q = q
    sub.points[...] = best_pts
    return iters


def _cheap_global_guarded(mesh: CHILmesh, sel_ids: np.ndarray) -> bool:
    """One guarded Laplacian pass on the complement's interior vertices.

    Whole-stage revert when complement mean skew drops (spec-056 FR-005,
    research R7). Returns True when the pass was kept.
    """
    conn = np.asarray(mesh.connectivity_list)
    n_elems = int(mesh.n_elems)
    in_sel = np.zeros(n_elems, dtype=bool)
    if np.asarray(sel_ids).size:
        in_sel[np.asarray(sel_ids, dtype=int)] = True
    comp_elems = np.nonzero(~in_sel)[0]
    if comp_elems.size == 0:
        return False

    sel_verts = set(np.unique(conn[in_sel].ravel()).tolist()) if in_sel.any() else set()
    bverts = set(np.unique(mesh.edge2vert(mesh.boundary_edges()).ravel()).tolist())

    pts = np.asarray(mesh.points)
    before = pts.copy()
    q_before = _mean_skew(before, conn[comp_elems])

    new_xy = pts[:, :2].copy()
    for v in range(int(mesh.n_verts)):
        if v in bverts or v in sel_verts:
            continue
        inc = sorted(mesh.get_vertex_elements(v))
        if not inc:
            continue
        ring = np.unique(conn[inc].ravel())
        ring = ring[ring != v]
        if ring.size == 0:
            continue
        new_xy[v] = pts[ring, :2].mean(axis=0)
    mesh.points[:, :2] = new_xy

    q_after = _mean_skew(np.asarray(mesh.points), conn[comp_elems])
    if q_after < q_before:
        mesh.points[...] = before
        return False
    return True


def hierarchical_smoother(
    mesh: CHILmesh,
    policy: str = "skew",
    stage_plan: tuple = ("local_fem",),
    *,
    frac: float = 0.075,
    layers: tuple = (0,),
    dev: int = 2,
    dilate: bool = True,
    eps: float = 1e-3,
    max_patch_iter: int = 10,
    min_interior: int = 4,
    fallback_frac: float = 0.5,
    return_info: bool = False,
):
    """Opt-in hierarchical smoother (spec-056 contracts/api.md).

    Guarantees: domain-boundary coords bitwise-unchanged; non-selected coords
    bitwise-unchanged on the default plan; deterministic; empty selection
    skips the FEM stage; selection > fallback_frac delegates to the global
    fem_smoother (FR-012); bowtie repair applied before return (FR-010).
    """
    from .post_process import fem_smoother
    from .repair import _fix_bowties

    t0 = time.perf_counter()
    info = HierarchicalResult()

    mesh = remove_unused_vertices(mesh)

    t_sel0 = time.perf_counter()
    sel = select_region(mesh, policy, frac=frac, layers=layers, dev=dev, dilate=dilate)
    info.n_selected = int(sel.size)
    info.timings["selection"] = time.perf_counter() - t_sel0

    if sel.size > fallback_frac * int(mesh.n_elems):
        info.fell_back = True
        mesh = fem_smoother(mesh, n_iter=3)
    else:
        for stage in stage_plan:
            if stage == "local_fem":
                if sel.size == 0:
                    continue
                t_p0 = time.perf_counter()
                patches = _build_patches(mesh, sel, min_interior=min_interior)
                info.n_patches = len(patches)
                info.timings["patch_build"] = time.perf_counter() - t_p0
                t_s0 = time.perf_counter()
                for p in patches:
                    iters = _solve_patch(p, eps=eps, max_patch_iter=max_patch_iter)
                    info.patch_iters.append(iters)
                    free_old = p.vert_map[p.free_mask]
                    mesh.points[free_old, :2] = np.asarray(p.submesh.points)[p.free_mask, :2]
                info.timings["solves"] = time.perf_counter() - t_s0
            elif stage == "cheap_global":
                _cheap_global_guarded(mesh, sel)
            else:
                raise ValueError(f"unknown stage: {stage!r}")

    conn = np.asarray(mesh.connectivity_list).copy()
    conn_fixed, n_bt = _fix_bowties(conn, mesh.points)
    if n_bt:
        mesh = CHILmesh(
            conn_fixed, mesh.points, grid_name=getattr(mesh, "grid_name", None)
        )

    info.timings["total"] = time.perf_counter() - t0
    if return_info:
        return mesh, info
    return mesh
