#!/usr/bin/env python
"""Mesh quality diagnostic script for QuADMESH+ output.

Identifies low-quality quads, classifies by layer and boundary contact.
Outputs markdown + JSON report.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np

# Probe mode: detect actual CHILmesh API shapes before running full analysis
PROBE_MODE = False


def is_quad(row: np.ndarray) -> bool:
    """Check if a row is a genuine quad (not a padded tri).

    Padded tri: 4th index == 3rd, OR 4th < 0, OR has duplicates.
    """
    row = np.asarray(row)
    if len(row) != 4:
        return False
    # Last vertex == third, or negative
    if row[3] == row[2] or row[3] < 0:
        return False
    # Any duplicates in the row
    if len(set(row)) != 4:
        return False
    return True


def load_mesh(path: Path) -> tuple[np.ndarray, np.ndarray, object]:
    """Load mesh from fort.14 or NPZ file.

    Returns:
        (points, connectivity_list, mesh_object)
        mesh_object is CHILmesh for .14, None for .npz
    """
    from chilmesh import CHILmesh

    path = Path(path)

    if path.suffix == '.14':
        mesh = CHILmesh.read_from_fort14(path)
        return mesh.points, mesh.connectivity_list, mesh
    elif path.suffix == '.npz':
        data = np.load(path)
        points = data['points']
        conn = data['conn'] if 'conn' in data.files else data['connectivity_list']
        mesh = CHILmesh(connectivity=conn, points=points)
        return points, conn, mesh
    else:
        raise ValueError(f"Unsupported format: {path.suffix}")


def run_pipeline_and_save(fort14_path: Path) -> tuple[np.ndarray, np.ndarray, object]:
    """Run quadmesh+ pipeline on a fort.14 file.

    Returns:
        (points, connectivity_list, quad_mesh)
    """
    from chilmesh import CHILmesh
    from quadmesh.pipeline import run_pipeline

    mesh = CHILmesh.read_from_fort14(fort14_path)
    quad = run_pipeline(mesh, method="quadmesh+", do_post_process=True)
    return quad.points, quad.connectivity_list, quad


def probe_chilmesh_api(mesh_obj: object) -> None:
    """Print CHILmesh API shapes for adaptation."""
    print("\n=== PROBE: CHILmesh API Introspection ===")

    if mesh_obj is None:
        print("mesh_obj is None (loaded from NPZ, not from fort.14)")
        return

    # Check attributes
    attrs = ['n_elems', 'n_verts', 'n_edges', 'n_layers', 'centroids',
             'points', 'connectivity_list', 'layers', 'adjacencies']

    for attr in attrs:
        if hasattr(mesh_obj, attr):
            val = getattr(mesh_obj, attr)
            if isinstance(val, np.ndarray):
                print(f"  {attr}: ndarray {val.shape} dtype={val.dtype}")
            elif isinstance(val, dict):
                print(f"  {attr}: dict with keys={list(val.keys())}")
                # Introspect dict contents
                if attr == 'layers':
                    for k, v in val.items():
                        if isinstance(v, list):
                            if len(v) > 0:
                                print(f"    {k}: list of {len(v)} items, [0] type={type(v[0])}")
                                if isinstance(v[0], (list, np.ndarray)):
                                    print(f"           [0] shape={np.asarray(v[0]).shape if v[0] is not None else 'None'}")
                        else:
                            print(f"    {k}: {type(v).__name__} shape={v.shape if hasattr(v, 'shape') else 'N/A'}")
                elif attr == 'adjacencies':
                    for k, v in val.items():
                        if isinstance(v, np.ndarray):
                            print(f"    {k}: ndarray {v.shape} dtype={v.dtype}")
                        elif isinstance(v, (dict, list)):
                            print(f"    {k}: {type(v).__name__}")
            else:
                print(f"  {attr}: {type(val).__name__} = {val}")
        else:
            print(f"  {attr}: NOT PRESENT")

    print("=== END PROBE ===\n")


def compute_elem_layers(mesh_obj: object, n_elems: int) -> tuple[np.ndarray, int]:
    """Compute layer index for each element.

    Returns:
        (elem_layer, n_layers)
        elem_layer: (n_elems,) array, layer index per element. -1 if not in any layer.
        n_layers: number of layers detected.
    """
    elem_layer = np.full(n_elems, -1, dtype=int)

    if mesh_obj is None or not hasattr(mesh_obj, 'layers'):
        return elem_layer, 0

    layers_dict = mesh_obj.layers
    if not isinstance(layers_dict, dict):
        return elem_layer, 0

    # Each layer k has keys 'OE' (outer elements) and 'IE' (inner elements)
    # OE/IE are lists of numpy arrays, one per layer
    oe_list = layers_dict.get('OE', [])
    ie_list = layers_dict.get('IE', [])

    n_layers = max(len(oe_list), len(ie_list))

    # OE and IE are lists indexed by layer; each element is a numpy array of element ids
    for k in range(n_layers):
        # OE[k] = numpy array of element ids in outer band of layer k
        if k < len(oe_list) and oe_list[k] is not None:
            for elem_id in oe_list[k]:
                if 0 <= elem_id < n_elems:
                    elem_layer[int(elem_id)] = k

        # IE[k] = numpy array of element ids in inner band of layer k
        if k < len(ie_list) and ie_list[k] is not None:
            for elem_id in ie_list[k]:
                if 0 <= elem_id < n_elems:
                    elem_layer[int(elem_id)] = k

    return elem_layer, n_layers


def compute_boundary_edges(adjacencies: dict) -> set[int]:
    """Find all boundary edge ids.

    Boundary edge: Edge2Elem row contains -1.

    Returns:
        set of edge ids that are on the domain boundary.
    """
    boundary_edges = set()
    if 'Edge2Elem' in adjacencies:
        edge2elem = adjacencies['Edge2Elem']
        for edge_id, row in enumerate(edge2elem):
            if -1 in row:
                boundary_edges.add(edge_id)
    return boundary_edges


def compute_boundary_verts(adjacencies: dict, boundary_edges: set[int]) -> set[int]:
    """Find all boundary vertices.

    Boundary vertex: appears in any boundary edge.

    Returns:
        set of vertex ids on the domain boundary.
    """
    boundary_verts = set()
    if 'Edge2Vert' in adjacencies:
        edge2vert = adjacencies['Edge2Vert']
        for edge_id in boundary_edges:
            if edge_id < len(edge2vert):
                for v_id in edge2vert[edge_id]:
                    if v_id >= 0:
                        boundary_verts.add(v_id)
    return boundary_verts


def classify_bad_quad(elem_id: int, elem_edges: list[int],
                      boundary_edges: set[int], boundary_verts: set[int],
                      elem_verts: list[int]) -> str:
    """Classify a bad quad by boundary contact.

    Returns:
        One of:
        - ">=2_boundary_edges"
        - "1_boundary_edge"
        - "1_boundary_vert"
        - ">=2_boundary_verts"
        - "0_boundary"
    """
    # Count boundary edges this element touches
    n_bedge = sum(1 for eid in elem_edges if eid in boundary_edges)

    # Count boundary vertices this element touches
    n_bvert = sum(1 for vid in elem_verts if vid >= 0 and vid in boundary_verts)

    if n_bedge >= 2:
        return ">=2_boundary_edges"
    elif n_bedge == 1:
        return "1_boundary_edge"
    elif n_bedge == 0:
        if n_bvert >= 2:
            return ">=2_boundary_verts"
        elif n_bvert == 1:
            return "1_boundary_vert"
        else:
            return "0_boundary"

    return "0_boundary"


def compute_min_interior_angle(elem_verts: np.ndarray, points: np.ndarray) -> float:
    """Compute minimum interior angle (in degrees) of an element.

    For quads: compute angles at each of 4 corners.
    For tris: compute angles at each of 3 corners.

    Returns:
        Minimum angle in degrees (0-180).
    """
    verts = elem_verts[elem_verts >= 0]
    if len(verts) < 3:
        return 0.0

    coords = points[verts, :2]
    min_angle = 180.0

    for i in range(len(verts)):
        # Angle at vertex i
        p0 = coords[(i - 1) % len(verts)]
        p1 = coords[i]
        p2 = coords[(i + 1) % len(verts)]

        v1 = p0 - p1
        v2 = p2 - p1

        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-12)
        cos_angle = np.clip(cos_angle, -1.0, 1.0)
        angle = np.degrees(np.arccos(cos_angle))
        min_angle = min(min_angle, angle)

    return min_angle


def compute_element_area(elem_verts: np.ndarray, points: np.ndarray) -> float:
    """Compute area of element using shoelace formula.

    Works for both triangles and quadrilaterals.
    """
    verts = elem_verts[elem_verts >= 0]
    if len(verts) < 3:
        return 0.0

    coords = points[verts, :2]

    # Shoelace formula
    x = coords[:, 0]
    y = coords[:, 1]
    area = 0.5 * abs(sum(x[i] * y[(i + 1) % len(verts)] -
                          x[(i + 1) % len(verts)] * y[i]
                          for i in range(len(verts))))
    return area


def compute_vertex_valence(adjacencies: dict) -> dict[int, int]:
    """Compute valence (incident element count) for each vertex.

    Returns:
        dict: {vertex_id -> valence}
    """
    valence = {}
    if 'Vert2Elem' in adjacencies:
        vert2elem = adjacencies['Vert2Elem']
        if isinstance(vert2elem, dict):
            # Dictionary: {vertex_id -> list of element ids}
            for v_id, elem_list in vert2elem.items():
                valence[v_id] = len(elem_list) if elem_list is not None else 0
        else:
            # Fallback: iterable (list-like)
            for v_id, elem_list in enumerate(vert2elem):
                valence[v_id] = len(elem_list) if elem_list is not None else 0
    return valence


def analyze_mesh(points: np.ndarray, connectivity_list: np.ndarray,
                 mesh_obj: object, bad_thresh: float = 0.30) -> dict:
    """Comprehensive analysis of bad quad distribution.

    Returns:
        dict with all diagnostic results.
    """
    from chilmesh import element_quality

    conn = np.asarray(connectivity_list)
    n_elems = len(conn)

    # Compute quality for all elements
    quality = element_quality(points, conn, metric="skew")

    # Find bad elements
    bad_mask = quality < bad_thresh
    bad_elem_ids = np.where(bad_mask)[0]
    n_bad = len(bad_elem_ids)

    # Get adjacencies and layers
    adjacencies = mesh_obj.adjacencies if hasattr(mesh_obj, 'adjacencies') else {}

    # Compute layer assignment
    if mesh_obj and hasattr(mesh_obj, 'layers'):
        elem_layer, n_layers = compute_elem_layers(mesh_obj, n_elems)
    else:
        elem_layer = np.full(n_elems, -1, dtype=int)
        n_layers = 0

    # A. LAYER BREAKDOWN
    layer_stats = {}
    for layer_idx in range(n_layers):
        elems_in_layer = np.where(elem_layer == layer_idx)[0]
        bad_in_layer = np.sum(bad_mask[elems_in_layer])
        n_in_layer = len(elems_in_layer)
        pct_bad = 100.0 * bad_in_layer / n_in_layer if n_in_layer > 0 else 0.0
        mean_skew = np.mean(quality[elems_in_layer]) if n_in_layer > 0 else 0.0

        layer_stats[layer_idx] = {
            "n_elems": int(n_in_layer),
            "n_bad": int(bad_in_layer),
            "pct_bad": float(pct_bad),
            "mean_skew": float(mean_skew),
        }

    # Count unassigned bad quads
    unassigned = np.where(elem_layer == -1)[0]
    bad_unassigned = np.sum(bad_mask[unassigned])
    n_unassigned = len(unassigned)

    layer_stats[-1] = {
        "n_elems": int(n_unassigned),
        "n_bad": int(bad_unassigned),
        "pct_bad": 100.0 * bad_unassigned / n_unassigned if n_unassigned > 0 else 0.0,
        "mean_skew": float(np.mean(quality[unassigned])) if n_unassigned > 0 else 0.0,
    }

    # Totals
    bad_layer0 = layer_stats.get(0, {}).get('n_bad', 0)
    bad_interior = sum(layer_stats.get(k, {}).get('n_bad', 0) for k in range(1, n_layers))
    bad_unassigned_total = layer_stats[-1]['n_bad']

    # B. BOUNDARY CONTACT CLASSIFICATION
    boundary_edges = compute_boundary_edges(adjacencies)
    boundary_verts = compute_boundary_verts(adjacencies, boundary_edges)

    boundary_buckets = {
        ">=2_boundary_edges": {"count": 0, "pct": 0.0},
        "1_boundary_edge": {"count": 0, "pct": 0.0},
        ">=2_boundary_verts": {"count": 0, "pct": 0.0},
        "1_boundary_vert": {"count": 0, "pct": 0.0},
        "0_boundary": {"count": 0, "pct": 0.0},
    }

    # Same buckets for ALL quads (denominator)
    all_quads_buckets = {
        ">=2_boundary_edges": {"count": 0, "pct": 0.0},
        "1_boundary_edge": {"count": 0, "pct": 0.0},
        ">=2_boundary_verts": {"count": 0, "pct": 0.0},
        "1_boundary_vert": {"count": 0, "pct": 0.0},
        "0_boundary": {"count": 0, "pct": 0.0},
    }

    n_all_quads = sum(1 for row in conn if is_quad(np.asarray(row)))
    n_bad_quads = sum(1 for elem_id in bad_elem_ids if is_quad(np.asarray(conn[elem_id])))

    for elem_id in range(n_elems):
        if not is_quad(np.asarray(conn[elem_id])):
            continue

        elem_verts = conn[elem_id]
        elem_edges = adjacencies.get('Elem2Edge', np.array([]))[elem_id] if 'Elem2Edge' in adjacencies else []

        bucket = classify_bad_quad(elem_id, elem_edges, boundary_edges, boundary_verts, elem_verts)
        all_quads_buckets[bucket]["count"] += 1

        if bad_mask[elem_id]:
            boundary_buckets[bucket]["count"] += 1

    # Compute percentages
    for bucket in all_quads_buckets:
        all_quads_buckets[bucket]["pct"] = (
            100.0 * all_quads_buckets[bucket]["count"] / n_all_quads
            if n_all_quads > 0 else 0.0
        )

    for bucket in boundary_buckets:
        boundary_buckets[bucket]["pct"] = (
            100.0 * boundary_buckets[bucket]["count"] / n_bad_quads
            if n_bad_quads > 0 else 0.0
        )

    # C. OTHER DIAGNOSTICS

    # Degenerate count
    degenerate_exact = np.sum(quality == 0.0)
    near_degenerate = np.sum(quality < 0.05)

    # Min interior angle distribution for bad quads
    bad_min_angles = []
    for elem_id in bad_elem_ids:
        if is_quad(np.asarray(conn[elem_id])):
            angle = compute_min_interior_angle(conn[elem_id], points)
            bad_min_angles.append(angle)

    bad_min_angles = np.array(bad_min_angles)
    if len(bad_min_angles) > 0:
        angle_stats = {
            "min": float(np.min(bad_min_angles)),
            "p5": float(np.percentile(bad_min_angles, 5)),
            "median": float(np.median(bad_min_angles)),
            "p95": float(np.percentile(bad_min_angles, 95)),
            "max": float(np.max(bad_min_angles)),
            "count_<15deg": int(np.sum(bad_min_angles < 15.0)),
        }
    else:
        angle_stats = {}

    # Irregular vertex correlation
    vertex_valence = compute_vertex_valence(adjacencies)
    bad_quads_with_irregular_vert = 0
    for elem_id in bad_elem_ids:
        if is_quad(np.asarray(conn[elem_id])):
            for v_id in conn[elem_id]:
                if v_id >= 0 and vertex_valence.get(v_id, 4) != 4:
                    bad_quads_with_irregular_vert += 1
                    break

    # Area distribution
    bad_areas = []
    for elem_id in bad_elem_ids:
        if is_quad(np.asarray(conn[elem_id])):
            area = compute_element_area(conn[elem_id], points)
            bad_areas.append(area)

    bad_areas = np.array(bad_areas)
    if len(bad_areas) > 0:
        median_area = np.median(bad_areas)
        sliver_count = np.sum(bad_areas < 0.01 * median_area) if median_area > 0 else 0
        area_stats = {
            "median": float(median_area),
            "sliver_count": int(sliver_count),
        }
    else:
        area_stats = {}

    # Clustering: bad quads sharing edges
    bad_set = set(bad_elem_ids)
    clustered_count = 0
    isolated_count = 0

    if 'Edge2Elem' in adjacencies:
        edge2elem = adjacencies['Edge2Elem']
        for elem_id in bad_elem_ids:
            if not is_quad(np.asarray(conn[elem_id])):
                continue

            elem_edges = adjacencies.get('Elem2Edge', np.array([]))[elem_id] if 'Elem2Edge' in adjacencies else []
            has_bad_neighbor = False
            for edge_id in elem_edges:
                if edge_id < len(edge2elem):
                    neighbors = edge2elem[edge_id]
                    for neighbor_id in neighbors:
                        if neighbor_id >= 0 and neighbor_id != elem_id and neighbor_id in bad_set:
                            has_bad_neighbor = True
                            break
                if has_bad_neighbor:
                    break

            if has_bad_neighbor:
                clustered_count += 1
            else:
                isolated_count += 1

    clustering_stats = {
        "clustered": int(clustered_count),
        "isolated": int(isolated_count),
    }

    return {
        "summary": {
            "n_elems": int(n_elems),
            "n_bad": int(n_bad),
            "n_all_quads": int(n_all_quads),
            "n_bad_quads": int(n_bad_quads),
            "pct_bad": 100.0 * n_bad / n_elems if n_elems > 0 else 0.0,
            "pct_bad_quads": 100.0 * n_bad_quads / n_all_quads if n_all_quads > 0 else 0.0,
            "bad_threshold": float(bad_thresh),
            "n_layers": int(n_layers),
        },
        "layer_analysis": layer_stats,
        "layer_summary": {
            "bad_layer0": int(bad_layer0),
            "bad_interior_layers": int(bad_interior),
            "bad_unassigned": int(bad_unassigned_total),
        },
        "boundary_contact_bad": boundary_buckets,
        "boundary_contact_all": all_quads_buckets,
        "degeneracy": {
            "exact_zero": int(degenerate_exact),
            "near_degenerate": int(near_degenerate),
        },
        "min_angle_stats": angle_stats,
        "area_stats": area_stats,
        "irregular_vertex_correlation": {
            "bad_quads_with_irregular_vert": int(bad_quads_with_irregular_vert),
            "total_bad_quads": int(n_bad_quads),
        },
        "clustering": clustering_stats,
    }


def format_markdown_report(diagnostics: dict, tag: str) -> str:
    """Format diagnostic results as markdown."""
    md = []

    summary = diagnostics["summary"]
    layer_stats = diagnostics["layer_analysis"]
    layer_summary = diagnostics["layer_summary"]
    boundary_bad = diagnostics["boundary_contact_bad"]
    boundary_all = diagnostics["boundary_contact_all"]

    md.append(f"# Mesh Quality Diagnostic Report: {tag}\n")

    # Executive summary
    md.append("## Executive Summary\n")
    interior_bad = layer_summary["bad_interior_layers"]
    boundary_bad_count = sum(layer_stats.get(0, {}).get("n_bad", 0) for _ in [0])

    if interior_bad > 0:
        md.append(f"**Interior low-quality quads detected:** {interior_bad} bad quads in interior layers "
                  f"(vs {layer_summary['bad_layer0']} at boundary layer).\n")
    else:
        md.append(f"**Interior low-quality quads:** None. All {layer_summary['bad_layer0']} bad quads at "
                  f"boundary or unassigned.\n")

    md.append("\n**Boundary contact distribution of bad quads:**\n")
    for bucket in [">=2_boundary_edges", "1_boundary_edge", ">=2_boundary_verts",
                    "1_boundary_vert", "0_boundary"]:
        count = boundary_bad[bucket]["count"]
        pct = boundary_bad[bucket]["pct"]
        md.append(f"  - {bucket}: {count} ({pct:.1f}%)\n")

    md.append(f"\nTotal elements: {summary['n_elems']}, Bad elements (quality < {summary['bad_threshold']:.2f}): "
              f"{summary['n_bad']} ({summary['pct_bad']:.1f}%)\n")
    md.append(f"Total quads: {summary['n_all_quads']}, Bad quads: {summary['n_bad_quads']} "
              f"({summary['pct_bad_quads']:.1f}%)\n\n")

    # Layer breakdown table
    md.append("## Layer Breakdown\n\n")
    md.append("| Layer | N Elems | N Bad | Pct Bad | Mean Skew |\n")
    md.append("|-------|---------|-------|---------|----------|\n")

    for k in sorted(layer_stats.keys()):
        stats = layer_stats[k]
        if k == -1:
            layer_label = "Unassigned"
        else:
            layer_label = str(k)
        md.append(f"| {layer_label} | {stats['n_elems']} | {stats['n_bad']} | "
                  f"{stats['pct_bad']:.1f}% | {stats['mean_skew']:.3f} |\n")

    md.append("\n")

    # Boundary contact classification
    md.append("## Boundary Contact Classification\n\n")
    md.append("### Bad Quads by Contact Type\n\n")
    md.append("| Contact Type | Count | % of Bad Quads |\n")
    md.append("|---|---|---|\n")

    for bucket in [">=2_boundary_edges", "1_boundary_edge", ">=2_boundary_verts",
                    "1_boundary_vert", "0_boundary"]:
        count = boundary_bad[bucket]["count"]
        pct = boundary_bad[bucket]["pct"]
        md.append(f"| {bucket} | {count} | {pct:.1f}% |\n")

    md.append("\n### All Quads by Contact Type (Bad-rate per category)\n\n")
    md.append("| Contact Type | Total | N Bad | Bad Rate |\n")
    md.append("|---|---|---|---|\n")

    for bucket in [">=2_boundary_edges", "1_boundary_edge", ">=2_boundary_verts",
                    "1_boundary_vert", "0_boundary"]:
        total = boundary_all[bucket]["count"]
        bad_count = boundary_bad[bucket]["count"]
        bad_rate = 100.0 * bad_count / total if total > 0 else 0.0
        md.append(f"| {bucket} | {total} | {bad_count} | {bad_rate:.1f}% |\n")

    md.append("\n")

    # Other diagnostics
    md.append("## Other Diagnostics\n\n")

    degeneracy = diagnostics["degeneracy"]
    md.append(f"**Degeneracy:**\n")
    md.append(f"  - Exact zero-area elements: {degeneracy['exact_zero']}\n")
    md.append(f"  - Near-degenerate (quality < 0.05): {degeneracy['near_degenerate']}\n\n")

    angle_stats = diagnostics.get("min_angle_stats", {})
    if angle_stats:
        md.append(f"**Minimum interior angle (bad quads):**\n")
        md.append(f"  - Min: {angle_stats['min']:.1f}°\n")
        md.append(f"  - P5: {angle_stats['p5']:.1f}°\n")
        md.append(f"  - Median: {angle_stats['median']:.1f}°\n")
        md.append(f"  - P95: {angle_stats['p95']:.1f}°\n")
        md.append(f"  - Quads with min-angle < 15°: {angle_stats['count_<15deg']}\n\n")

    irreg_vert = diagnostics["irregular_vertex_correlation"]
    md.append(f"**Irregular vertex correlation:**\n")
    md.append(f"  - Bad quads touching irregular interior vert (valence != 4): "
              f"{irreg_vert['bad_quads_with_irregular_vert']} / {irreg_vert['total_bad_quads']}\n\n")

    area_stats = diagnostics.get("area_stats", {})
    if area_stats:
        md.append(f"**Area distribution (bad quads):**\n")
        md.append(f"  - Median area: {area_stats['median']:.3e}\n")
        md.append(f"  - Sliver quads (area < 1% of median): {area_stats['sliver_count']}\n\n")

    clustering = diagnostics["clustering"]
    md.append(f"**Clustering:**\n")
    md.append(f"  - Clustered (share edge with another bad quad): {clustering['clustered']}\n")
    md.append(f"  - Isolated: {clustering['isolated']}\n")

    return "".join(md)


def main():
    parser = argparse.ArgumentParser(
        description="Diagnose low-quality quads in quadmesh+ output."
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--mesh", type=Path, help="Path to fort.14 mesh file")
    input_group.add_argument("--in-npz", type=Path, help="Path to NPZ file with points+connectivity_list")

    parser.add_argument("--bad-thresh", type=float, default=0.30,
                       help="Quality threshold below which quads are bad (default 0.30)")
    parser.add_argument("--out-dir", type=Path, default=Path("output/diag"),
                       help="Output directory (default output/diag)")
    parser.add_argument("--tag", type=str, default="mesh",
                       help="Tag for output filenames (default 'mesh')")
    parser.add_argument("--probe", action="store_true",
                       help="Print CHILmesh API introspection and exit")

    args = parser.parse_args()

    # Create output directory
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Load mesh
    print(f"Loading mesh...", file=sys.stderr)
    if args.mesh:
        if args.probe:
            points, conn, mesh_obj = load_mesh(args.mesh)
        else:
            print(f"Running quadmesh+ pipeline on {args.mesh}...", file=sys.stderr)
            points, conn, mesh_obj = run_pipeline_and_save(args.mesh)
    else:
        points, conn, mesh_obj = load_mesh(args.in_npz)

    # Probe mode
    if args.probe:
        probe_chilmesh_api(mesh_obj)
        return

    print(f"Analyzing mesh ({len(conn)} elements)...", file=sys.stderr)

    # Run analysis
    diagnostics = analyze_mesh(points, conn, mesh_obj, bad_thresh=args.bad_thresh)

    # Write outputs
    md_path = args.out_dir / f"{args.tag}_diag.md"
    json_path = args.out_dir / f"{args.tag}_diag.json"

    md_report = format_markdown_report(diagnostics, args.tag)
    with open(md_path, 'w') as f:
        f.write(md_report)
    print(f"Wrote {md_path}", file=sys.stderr)

    with open(json_path, 'w') as f:
        json.dump(diagnostics, f, indent=2)
    print(f"Wrote {json_path}", file=sys.stderr)

    # Print summary to stdout
    print(md_report)


if __name__ == "__main__":
    main()
