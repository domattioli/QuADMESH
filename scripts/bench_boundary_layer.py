#!/usr/bin/env python
"""Boundary-layer quality diagnostic for QuADMESH+ output.

Reproduces issue #90/#98 finding: low-quality quads are dominated by geometric
triangles (quads with ~180° corner) that touch the domain boundary.

Read-only measurement script — never modifies mesh algorithm code.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from chilmesh import CHILmesh, element_quality
from quadmesh import tri2quad
from quadmesh.quality_report import compute_quality_stats


def _normalize(row: list | np.ndarray) -> list[int]:
    """Normalize an element row: drop padding, keep distinct indices."""
    idx = [int(x) for x in row]
    uniq = []
    for v in idx:
        if v not in uniq:
            uniq.append(v)
    return uniq


def _edges(el: list[int]) -> list[tuple[int, int]]:
    """Generate edges from normalized element vertices (cyclic)."""
    n = len(el)
    return [tuple(sorted((el[i], el[(i + 1) % n]))) for i in range(n)]


def build_boundary_edge_set(
    connectivity_list: np.ndarray,
) -> set[tuple[int, int]]:
    """Build boundary edge set (edges appearing in exactly one element)."""
    ecount = {}
    for row in connectivity_list:
        normalized = _normalize(row)
        for edge in _edges(normalized):
            ecount[edge] = ecount.get(edge, 0) + 1
    return {e for e, c in ecount.items() if c == 1}


def is_geometric_triangle(
    quad_vertices: np.ndarray, threshold_angle_deg: float = 178.0
) -> bool:
    """Check if quad has a ~180° corner (degenerate geometric triangle).

    Args:
        quad_vertices: shape (4, 2), the quad's corner points
        threshold_angle_deg: angle >= this is considered degenerate

    Returns:
        True if any corner has angle >= threshold_angle_deg
    """
    for i in range(4):
        v_center = quad_vertices[i]
        v_prev = quad_vertices[(i - 1) % 4]
        v_next = quad_vertices[(i + 1) % 4]

        # Vectors from center to prev and next
        vec1 = v_prev - v_center
        vec2 = v_next - v_center

        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        # Degenerate if either vector is near-zero
        if norm1 < 1e-12 or norm2 < 1e-12:
            return True

        # Compute angle via dot product
        cos_angle = np.clip(
            np.dot(vec1, vec2) / (norm1 * norm2), -1.0, 1.0
        )
        angle_deg = np.degrees(np.arccos(cos_angle))

        if angle_deg >= threshold_angle_deg:
            return True

    return False


def _count_geo_tris(mesh) -> int:
    """Count geometric triangles (4-vertex quads with ~180° corner) in mesh.

    Args:
        mesh: CHILmesh object

    Returns:
        Total count of geometric triangles
    """
    P = np.asarray(mesh.points)[:, :2]
    cl = np.asarray(mesh.connectivity_list)
    count = 0
    for row in cl:
        normalized = _normalize(row)
        if len(normalized) == 4:
            quad_verts = P[normalized]
            if is_geometric_triangle(quad_verts):
                count += 1
    return count


def diagnose_ops(q, threshold: float):
    """Diagnose why cleanup_boundary_quads operators fail to clear boundary geo-triangles.

    Measures:
    - COLLAPSE: how many geo-tris flagged but rejected (not collapsed)
    - SHIFT: skew improvement + interior geo-tri count after shift iterations

    Args:
        q: CHILmesh post-tri2quad
        threshold: quality threshold (for context; not used in this diagnostic)
    """
    from quadmesh import cleanup_boundary_quads as _cbq
    from chilmesh import element_quality

    print("\n=== DIAGNOSE_OPS ===")

    # Collapse diagnostic
    print("collapse diagnostic:")
    m = q
    geo_before_collapse = _count_geo_tris(m)
    print(f"  geo-tris before: {geo_before_collapse}")

    pass_num = 1
    total_removed = 0
    pass1_flagged = None
    pass1_removed = None

    while pass_num <= 15:
        flagged = len(list(_cbq._scan_bad_quads(m)))
        n_before = m.n_elems
        m = _cbq.cleanup_boundary_quads(m, can_remove_edges=True)
        n_after = m.n_elems
        removed = n_before - n_after

        if pass_num == 1:
            pass1_flagged = flagged
            pass1_removed = removed

        total_removed += removed

        if removed == 0:
            break

        pass_num += 1

    geo_after_collapse = _count_geo_tris(m)

    # Compute pass1 rejection rate
    pass1_rejection = 0.0
    if pass1_flagged is not None and pass1_flagged > 0:
        pass1_rejection = 100.0 * (pass1_flagged - pass1_removed) / pass1_flagged

    print(f"  collapse: flagged_pass1={pass1_flagged} total_removed={total_removed} "
          f"over {pass_num-1} passes; pass1 rejection={pass1_rejection:.0f}% "
          f"(flagged-but-not-collapsed)")
    print(f"  geo-tris after collapse: {geo_after_collapse}")

    # Shift diagnostic
    print("shift diagnostic (6 iterations):")
    m = q
    qual_before = element_quality(m.points, m.connectivity_list, metric="skew")
    mean_skew_before = np.mean(qual_before)
    min_skew_before = np.min(qual_before)
    geo_before_shift = _count_geo_tris(m)
    print(f"  geo-tris before shift: {geo_before_shift}")
    print(f"  skew before: mean={mean_skew_before:.3f} min={min_skew_before:.3f}")

    for _ in range(6):
        m = _cbq.cleanup_boundary_quads(m, can_remove_edges=False)

    qual_after = element_quality(m.points, m.connectivity_list, metric="skew")
    mean_skew_after = np.mean(qual_after)
    min_skew_after = np.min(qual_after)
    geo_after_shift = _count_geo_tris(m)

    # Count interior geo-tris after shift
    P = np.asarray(m.points)[:, :2]
    cl = np.asarray(m.connectivity_list)
    bset = build_boundary_edge_set(cl)
    interior_geo_count = 0
    for row in cl:
        normalized = _normalize(row)
        if len(normalized) == 4:
            quad_verts = P[normalized]
            if is_geometric_triangle(quad_verts):
                edges = _edges(normalized)
                if not any(e in bset for e in edges):
                    interior_geo_count += 1

    print(f"  skew after:  mean={mean_skew_after:.3f} min={min_skew_after:.3f}")
    print(f"  geo-tris after shift: {geo_after_shift} (interior={interior_geo_count})")


def main():
    parser = argparse.ArgumentParser(
        description="Boundary-layer quality diagnostic for QuADMESH+ output."
    )
    parser.add_argument(
        "--mesh",
        required=True,
        help="Mesh filename (resolved to tests/fixtures/meshes/) or full path",
    )
    parser.add_argument(
        "--quality-threshold",
        type=float,
        default=0.3,
        help="Quality threshold for 'bad' classification",
    )
    parser.add_argument(
        "--diagnose-ops",
        action="store_true",
        help="Measure why cleanup_boundary_quads ops leave boundary geo-triangles (collapse-rejection rate + shift-mode effect).",
    )
    args = parser.parse_args()

    # Resolve mesh path
    mesh_path = Path(args.mesh)
    if "/" not in args.mesh and not mesh_path.is_absolute():
        mesh_path = Path(__file__).parent.parent / "tests" / "fixtures" / "meshes" / args.mesh

    if not mesh_path.exists():
        print(f"mesh not found: {mesh_path}")
        sys.exit(2)

    # Load and process
    try:
        mesh = CHILmesh.read_from_fort14(str(mesh_path))
    except Exception as e:
        print(f"error loading mesh: {e}")
        sys.exit(1)

    # Run tri2quad
    try:
        q = tri2quad(mesh, method="quadmesh+")
    except Exception as e:
        print(f"error in tri2quad: {e}")
        sys.exit(1)

    # Extract points and connectivity
    P = np.asarray(q.points)[:, :2]
    cl = np.asarray(q.connectivity_list)

    # Build boundary edge set
    bset = build_boundary_edge_set(cl)

    # Compute quality stats
    stats = compute_quality_stats(q)
    n_elems = len(cl)

    # Compute per-element quality
    qual = element_quality(q.points, q.connectivity_list, metric="skew")
    bad_mask = qual < args.quality_threshold

    # Derive n_bad and pct_bad from threshold-based bad_mask (not hardcoded 0.3)
    n_bad = int(bad_mask.sum())
    pct_bad = (100.0 * n_bad / n_elems) if n_elems > 0 else 0.0

    # Geometric triangle detection
    geo_total = 0
    geo_interior = 0
    bad_boundary_contact = {
        ">=2 boundary edges": 0,
        "exactly 1 boundary edge": 0,
        "0 edges, >=2 bdy verts": 0,
        "0 edges, 1 bdy vert": 0,
        "0 boundary contact": 0,
    }

    for idx, row in enumerate(cl):
        normalized = _normalize(row)

        # Only check quads (4 distinct vertices)
        if len(normalized) == 4:
            quad_verts = P[normalized]
            if is_geometric_triangle(quad_verts):
                geo_total += 1
                # Check boundary contact
                edges = _edges(normalized)
                if not any(e in bset for e in edges):
                    geo_interior += 1

    # Bad quad boundary contact breakdown
    boundary_verts = set()
    for edge in bset:
        boundary_verts.add(edge[0])
        boundary_verts.add(edge[1])

    for idx, row in enumerate(cl):
        if not bad_mask[idx]:
            continue

        normalized = _normalize(row)
        edges = _edges(normalized)

        # Count boundary edges and boundary verts
        n_bdy_edges = sum(1 for e in edges if e in bset)
        n_bdy_verts = sum(1 for v in normalized if v in boundary_verts)

        # Classify into bucket
        if n_bdy_edges >= 2:
            bad_boundary_contact[">=2 boundary edges"] += 1
        elif n_bdy_edges == 1:
            bad_boundary_contact["exactly 1 boundary edge"] += 1
        elif n_bdy_verts >= 2:
            bad_boundary_contact["0 edges, >=2 bdy verts"] += 1
        elif n_bdy_verts == 1:
            bad_boundary_contact["0 edges, 1 bdy vert"] += 1
        else:
            bad_boundary_contact["0 boundary contact"] += 1

    # Output report
    print(f"mesh: {mesh_path.name}")
    print(
        f"quads: {n_elems}  mean={stats.get('mean', 0.0):.3f} "
        f"min={stats.get('min', 0.0):.3f} std={stats.get('std', 0.0):.3f}  "
        f"bad(<{args.quality_threshold})={n_bad}/{n_elems} ({pct_bad:.1f}%)"
    )
    print(
        f"geometric triangles (~180 deg corner): "
        f"total={geo_total}  interior={geo_interior}  boundary={geo_total - geo_interior}"
    )
    print("bad-quad boundary contact:")
    for bucket, count in bad_boundary_contact.items():
        pct = (100.0 * count / n_bad) if n_bad > 0 else 0.0
        print(f"  {bucket:30s}: {count:3d} ({pct:5.1f}%)")

    # Assertion-style note
    if geo_interior != 0:
        print(
            f"WARN: interior geometric triangles present (faithfulness violation)"
        )
    else:
        print(f"OK: zero interior geometric triangles (invariant holds)")

    # Run diagnostic if requested
    if args.diagnose_ops:
        diagnose_ops(q, args.quality_threshold)


if __name__ == "__main__":
    main()
