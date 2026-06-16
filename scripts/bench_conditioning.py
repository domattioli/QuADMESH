#!/usr/bin/env python
"""Benchmark conditioning on chilmesh.examples or real .14 meshes.

Usage (no args: run 4 synthetic meshes):
    python bench_conditioning.py

Usage (real meshes via CLI):
    python bench_conditioning.py --mesh Test_Case_1 --mesh WNAT/onur@v1
    python bench_conditioning.py --mesh /path/to/mesh.14 --max-passes 5
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import tomllib
import traceback

import numpy as np
import chilmesh.examples as ex
from chilmesh import CHILmesh, element_quality

from quadmesh.pipeline import run_pipeline
from quadmesh.create_quad_domain import create_quad_domain
from quadmesh.precondition import condition_triangulation

DEFAULT_REGISTRY_DIR = os.environ.get(
    "QUADMESH_REGISTRY_DIR",
    "/workspace/Valence/registry_data/meshes"
)


def _normalize(row) -> tuple:
    """Return tuple of unique ints in row, or all ints if not a triangle."""
    vs = [int(v) for v in row]
    uniq = list(dict.fromkeys(vs))
    return tuple(uniq) if len(uniq) == 3 else tuple(vs)


def _edges(el: list) -> list[tuple[int, int]]:
    """Return sorted edge tuples for an element."""
    n = len(el)
    return [tuple(sorted((int(el[i]), int(el[(i + 1) % n])))) for i in range(n)]


def _total_tris(connectivity_list) -> int:
    """Count total triangles (3 unique vertices)."""
    count = 0
    for row in connectivity_list:
        if len(_normalize(row)) == 3:
            count += 1
    return count


def _interior_tris(connectivity_list) -> int:
    """Count interior triangles (no boundary edges).

    A boundary edge appears in exactly 1 element.
    An interior triangle has no boundary edges.
    """
    # Build edge-incidence map
    edge_count = {}
    for row in connectivity_list:
        for edge in _edges(row):
            edge_count[edge] = edge_count.get(edge, 0) + 1

    # Count tris with no boundary edge
    interior = 0
    for row in connectivity_list:
        norm = _normalize(row)
        if len(norm) != 3:
            continue
        # Check if any edge is a boundary edge (count == 1)
        has_boundary_edge = False
        for edge in _edges(row):
            if edge_count.get(edge, 0) == 1:
                has_boundary_edge = True
                break
        if not has_boundary_edge:
            interior += 1

    return interior


def _geometric_tri_count(points, connectivity_list, angle_thresh=178.0):
    """Count quad rows that are geometrically triangles: 4 distinct vertices but
    one interior angle >= angle_thresh degrees (a vertex colinear on an edge).
    Returns (total, interior) where interior = those whose underlying triangle has
    no domain-boundary edge."""
    P = np.asarray(points)[:, :2]
    # domain boundary edges (appear in exactly one element, over normalized elems)
    edge_count = {}
    for row in connectivity_list:
        el = _normalize(row)
        for e in _edges(el):
            edge_count[e] = edge_count.get(e, 0) + 1
    bset = {e for e, c in edge_count.items() if c == 1}
    total = 0
    interior = 0
    for row in connectivity_list:
        idx = [int(x) for x in row]
        if len(set(idx)) != 4:
            continue  # only genuine 4-distinct-index quads
        pts = P[idx]
        flat_pos = -1
        for i in range(4):
            v1 = pts[(i - 1) % 4] - pts[i]
            v2 = pts[(i + 1) % 4] - pts[i]
            n1 = np.linalg.norm(v1); n2 = np.linalg.norm(v2)
            if n1 < 1e-12 or n2 < 1e-12:
                flat_pos = i; break
            ang = np.degrees(np.arccos(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0)))
            if ang >= angle_thresh:
                flat_pos = i; break
        if flat_pos < 0:
            continue
        total += 1
        # "interior" iff none of the element's ACTUAL edges is a domain-boundary edge.
        # (Do NOT reconstruct the triangle's collapsed side — the flat vertex splits
        #  it into two real edges, so the reconstructed side is never a real edge.)
        elem_edges = _edges(_normalize(row))
        if not any(e in bset for e in elem_edges):
            interior += 1
    return total, interior


def _quad_rows(connectivity_list):
    """Yield normalized 4-vertex quad tuples (skip tris)."""
    out = []
    for row in connectivity_list:
        nrm = _normalize(row)
        if len(nrm) == 4:
            out.append(nrm)
    return out


def _high_valence_count(connectivity_list, n_pts, thresh=5):
    """# vertices whose element-incidence >= thresh (irregular/singular nodes; lower=better)."""
    inc = np.zeros(int(n_pts), dtype=int)
    for row in connectivity_list:
        for v in set(int(x) for x in _normalize(row)):
            if 0 <= v < inc.size:
                inc[v] += 1
    return int((inc >= thresh).sum())


def _quad_min_angles(points, connectivity_list):
    """Return np.array of per-quad minimum interior angle (degrees)."""
    P = np.asarray(points)[:, :2]
    mins = []
    for q in _quad_rows(connectivity_list):
        pts = P[list(q)]
        angs = []
        for i in range(4):
            prev = pts[(i - 1) % 4]; cur = pts[i]; nxt = pts[(i + 1) % 4]
            v1 = prev - cur; v2 = nxt - cur
            n1 = np.linalg.norm(v1); n2 = np.linalg.norm(v2)
            if n1 < 1e-12 or n2 < 1e-12:
                angs.append(0.0); continue
            c = float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
            angs.append(float(np.degrees(np.arccos(c))))
        mins.append(min(angs) if angs else 0.0)
    return np.asarray(mins, dtype=float)


def _grid_alignment_s4(points, connectivity_list):
    """4-fold order parameter over quad edge directions: |mean(exp(i*4*phi))|.

    1.0 = all edges aligned to one orthogonal frame (perfectly gridded);
    0.0 = isotropic/no directional structure. Higher = better grid adherence.
    """
    P = np.asarray(points)[:, :2]
    phis = []
    for q in _quad_rows(connectivity_list):
        pts = P[list(q)]
        for i in range(4):
            d = pts[(i + 1) % 4] - pts[i]
            if np.linalg.norm(d) < 1e-12:
                continue
            phis.append(np.arctan2(d[1], d[0]))
    if not phis:
        return 0.0
    phis = np.asarray(phis)
    return float(np.abs(np.mean(np.exp(1j * 4.0 * phis))))


def resolve_mesh(spec: str, registry_dir: str, manifest_path: str) -> tuple[CHILmesh, str]:
    """Resolve a mesh spec to a CHILmesh and display name.

    Args:
        spec: full_id (e.g. "WNAT/onur@v1"), bare name, or file path.
        registry_dir: directory containing mesh files.
        manifest_path: path to manifest.toml.

    Returns:
        (CHILmesh, display_name)

    Raises:
        FileNotFoundError: if spec cannot be resolved.
    """
    # Direct file path?
    if os.path.isfile(spec):
        return CHILmesh.read_from_fort14(spec), os.path.basename(spec)

    # Build full_id -> filename map from manifest
    id_to_file = {}
    if os.path.isfile(manifest_path):
        try:
            with open(manifest_path, "rb") as f:
                data = tomllib.load(f)
            for domain in data.get("domains", []):
                dn = domain.get("name")
                for mesh in domain.get("meshes", []):
                    fn = mesh.get("filename")
                    if dn and fn:
                        # Map full_id
                        full_id = f"{dn}/{mesh.get('id')}"
                        id_to_file[full_id] = fn
                        # Map aliases
                        for alias in mesh.get("aliases", []):
                            id_to_file[alias] = fn
                        # Map filename stem
                        stem = fn.rsplit(".", 1)[0] if "." in fn else fn
                        id_to_file[stem] = fn
        except Exception:
            pass

    # Try spec as full_id
    if spec in id_to_file:
        cand = os.path.join(registry_dir, id_to_file[spec])
        if os.path.isfile(cand):
            return CHILmesh.read_from_fort14(cand), spec

    # Try spec as bare name in registry_dir
    for candidate in [spec, spec + ".14"]:
        cand_path = os.path.join(registry_dir, candidate)
        if os.path.isfile(cand_path):
            return CHILmesh.read_from_fort14(cand_path), candidate

    # Case-insensitive match
    try:
        for fn in os.listdir(registry_dir):
            if fn.lower() == spec.lower() or fn.lower() == (spec + ".14").lower():
                cand_path = os.path.join(registry_dir, fn)
                if os.path.isfile(cand_path):
                    return CHILmesh.read_from_fort14(cand_path), fn
    except OSError:
        pass

    raise FileNotFoundError(
        f"could not resolve mesh spec: {spec!r} "
        f"(registry_dir={registry_dir}, manifest={manifest_path})"
    )


def benchmark_mesh(name: str, mesh: CHILmesh) -> dict | None:
    """Run baseline and conditioned pipeline, return comparison dict.

    Args:
        name: display name for the mesh.
        mesh: CHILmesh instance.

    Returns:
        dict with metrics, or None on exception.
    """
    print(f"{name}...", end=" ", flush=True)

    try:
        # Baseline
        t0 = time.time()
        baseline = run_pipeline(mesh, precondition=False)
        baseline_secs = time.time() - t0

        baseline_qual = element_quality(
            baseline.points, baseline.connectivity_list, metric="aspect_ratio"
        )
        baseline_aspect_mean = float(np.nanmean(baseline_qual))
        baseline_aspect_min = float(np.nanmin(baseline_qual))

        baseline_skew = element_quality(
            baseline.points, baseline.connectivity_list, metric="skew"
        )
        baseline_skew_mean = float(np.nanmean(baseline_skew))
        baseline_skew_min = float(np.nanmin(baseline_skew))

        baseline_total_tris = _total_tris(baseline.connectivity_list)
        baseline_interior_tris = _interior_tris(baseline.connectivity_list)
        baseline_geo_total, baseline_geo_interior = _geometric_tri_count(baseline.points, baseline.connectivity_list)
        n_elems_base = np.asarray(baseline.connectivity_list).shape[0]

        baseline_high_valence = _high_valence_count(baseline.connectivity_list, np.asarray(baseline.points).shape[0])
        baseline_ma = _quad_min_angles(baseline.points, baseline.connectivity_list)
        baseline_mean_min_angle = float(np.nanmean(baseline_ma)) if baseline_ma.size else 0.0
        baseline_n_low_angle45 = int((baseline_ma < 45).sum())
        baseline_n_low_angle30 = int((baseline_ma < 30).sum())
        baseline_grid_s4 = _grid_alignment_s4(baseline.points, baseline.connectivity_list)

        # Conditioned
        t0 = time.time()
        cond_kwargs = {}
        conditioned = run_pipeline(mesh, precondition=True, precondition_kwargs=cond_kwargs)
        cond_secs = time.time() - t0

        cond_qual = element_quality(
            conditioned.points, conditioned.connectivity_list, metric="aspect_ratio"
        )
        cond_aspect_mean = float(np.nanmean(cond_qual))
        cond_aspect_min = float(np.nanmin(cond_qual))

        cond_skew = element_quality(
            conditioned.points, conditioned.connectivity_list, metric="skew"
        )
        cond_skew_mean = float(np.nanmean(cond_skew))
        cond_skew_min = float(np.nanmin(cond_skew))

        cond_total_tris = _total_tris(conditioned.connectivity_list)
        cond_interior_tris = _interior_tris(conditioned.connectivity_list)
        cond_geo_total, cond_geo_interior = _geometric_tri_count(conditioned.points, conditioned.connectivity_list)
        n_elems_cond = np.asarray(conditioned.connectivity_list).shape[0]

        cond_high_valence = _high_valence_count(conditioned.connectivity_list, np.asarray(conditioned.points).shape[0])
        cond_ma = _quad_min_angles(conditioned.points, conditioned.connectivity_list)
        cond_mean_min_angle = float(np.nanmean(cond_ma)) if cond_ma.size else 0.0
        cond_n_low_angle45 = int((cond_ma < 45).sum())
        cond_n_low_angle30 = int((cond_ma < 30).sum())
        cond_grid_s4 = _grid_alignment_s4(conditioned.points, conditioned.connectivity_list)

        # Conditioning stats (same conditioning kwargs as the pipeline run)
        domain = create_quad_domain(mesh)
        _, stats = condition_triangulation(domain, collect_stats=True, **cond_kwargs)
        unmatched_before = sum(s.get("unmatched_before", 0) for s in stats)
        unmatched_after = sum(s.get("unmatched_after", 0) for s in stats)
        swaps = sum(s.get("swaps", 0) for s in stats)
        n_layers = len(stats)

        print("✓")

        return {
            "name": name,
            "baseline_aspect_mean": baseline_aspect_mean,
            "baseline_aspect_min": baseline_aspect_min,
            "cond_aspect_mean": cond_aspect_mean,
            "cond_aspect_min": cond_aspect_min,
            "aspect_mean_delta": cond_aspect_mean - baseline_aspect_mean,
            "aspect_min_delta": cond_aspect_min - baseline_aspect_min,
            "baseline_skew_mean": baseline_skew_mean,
            "cond_skew_mean": cond_skew_mean,
            "skew_mean_delta": cond_skew_mean - baseline_skew_mean,
            "baseline_skew_min": baseline_skew_min,
            "cond_skew_min": cond_skew_min,
            "n_elems_base": n_elems_base,
            "n_elems_cond": n_elems_cond,
            "baseline_total_tris": baseline_total_tris,
            "cond_total_tris": cond_total_tris,
            "baseline_interior_tris": baseline_interior_tris,
            "cond_interior_tris": cond_interior_tris,
            "baseline_geo_tri": baseline_geo_total,
            "baseline_geo_tri_interior": baseline_geo_interior,
            "cond_geo_tri": cond_geo_total,
            "cond_geo_tri_interior": cond_geo_interior,
            "unmatched_before": unmatched_before,
            "unmatched_after": unmatched_after,
            "swaps": swaps,
            "n_layers": n_layers,
            "baseline_secs": baseline_secs,
            "cond_secs": cond_secs,
            "baseline_high_valence": baseline_high_valence,
            "cond_high_valence": cond_high_valence,
            "baseline_mean_min_angle": baseline_mean_min_angle,
            "cond_mean_min_angle": cond_mean_min_angle,
            "mean_min_angle_delta": cond_mean_min_angle - baseline_mean_min_angle,
            "baseline_n_low_angle45": baseline_n_low_angle45,
            "cond_n_low_angle45": cond_n_low_angle45,
            "baseline_n_low_angle30": baseline_n_low_angle30,
            "cond_n_low_angle30": cond_n_low_angle30,
            "baseline_grid_s4": baseline_grid_s4,
            "cond_grid_s4": cond_grid_s4,
            "grid_s4_delta": cond_grid_s4 - baseline_grid_s4,
        }

    except Exception as e:
        print(f"✗ ({type(e).__name__})")
        traceback.print_exc()
        return None


def print_table(results: list[dict]) -> None:
    """Print results table."""
    if not results:
        return

    # Filter out None results
    results = [r for r in results if r is not None]

    print("\n" + "=" * 160)
    print(f"{'Mesh':<20} | {'Base Asp▲':<10} | {'Cond Asp▲':<10} | {'Asp Δ':<8} | "
          f"{'Base Asp◀':<10} | {'Cond Asp◀':<10} | {'Base Skew':<10} | "
          f"{'Cond Skew':<10} | {'Skew Δ':<8}")
    print("=" * 160)

    for r in results:
        print(f"{r['name']:<20} | {r['baseline_aspect_mean']:>9.4f} | "
              f"{r['cond_aspect_mean']:>9.4f} | {r['aspect_mean_delta']:>7.4f} | "
              f"{r['baseline_aspect_min']:>9.4f} | {r['cond_aspect_min']:>9.4f} | "
              f"{r['baseline_skew_mean']:>9.4f} | {r['cond_skew_mean']:>9.4f} | "
              f"{r['skew_mean_delta']:>7.4f}")

    print("=" * 160)
    print(f"{'Mesh':<20} | {'Base Int▲':<10} | {'Cond Int▲':<10} | {'Cond Tot▲':<10} | "
          f"{'Unmatched B':<10} | {'Unmatched A':<10} | {'Swaps':<8} | {'n_elems':<10} | "
          f"{'Cond Secs':<10}")
    print("=" * 160)

    for r in results:
        print(f"{r['name']:<20} | {r['baseline_interior_tris']:>9d} | "
              f"{r['cond_interior_tris']:>9d} | {r['cond_total_tris']:>9d} | "
              f"{r['unmatched_before']:>9d} | {r['unmatched_after']:>9d} | "
              f"{r['swaps']:>7d} | {r['n_elems_cond']:>9d} | "
              f"{r['cond_secs']:>9.2f}")

    print("=" * 160)
    print(f"{'Mesh':<20} | {'Base HiVal':<10} | {'Cond HiVal':<10} | {'Base MinAng':<12} | "
          f"{'Cond MinAng':<12} | {'MinAng Δ':<10} | {'Base <45':<8} | {'Cond <45':<8} | "
          f"{'Base GridS4':<12} | {'Cond GridS4':<12} | {'S4 Δ':<10}")
    print("=" * 160)

    for r in results:
        print(f"{r['name']:<20} | {r.get('baseline_high_valence', 'N/A'):>9} | "
              f"{r.get('cond_high_valence', 'N/A'):>9} | "
              f"{r.get('baseline_mean_min_angle', 'N/A'):>11} | "
              f"{r.get('cond_mean_min_angle', 'N/A'):>11} | "
              f"{r.get('mean_min_angle_delta', 'N/A'):>9} | "
              f"{r.get('baseline_n_low_angle45', 'N/A'):>7} | "
              f"{r.get('cond_n_low_angle45', 'N/A'):>7} | "
              f"{r.get('baseline_grid_s4', 'N/A'):>11} | "
              f"{r.get('cond_grid_s4', 'N/A'):>11} | "
              f"{r.get('grid_s4_delta', 'N/A'):>9}")

    print("=" * 160)
    print(f"{'Mesh':<20} | {'Base GeoTri':<12} | {'Cond GeoTri':<12} | {'Base GeoTri Int':<15} | {'Cond GeoTri Int':<15}")
    print("=" * 160)

    for r in results:
        print(f"{r['name']:<20} | {r.get('baseline_geo_tri', 'N/A'):>11} | "
              f"{r.get('cond_geo_tri', 'N/A'):>11} | "
              f"{r.get('baseline_geo_tri_interior', 'N/A'):>14} | "
              f"{r.get('cond_geo_tri_interior', 'N/A'):>14}")

    print("=" * 160)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark mesh conditioning. "
        "No args: run 4 synthetic meshes. With --mesh: run real meshes."
    )
    parser.add_argument(
        "-m", "--mesh",
        action="append",
        default=None,
        help="Mesh spec (full_id, name, or path). Repeatable. "
             "Resolves against manifest.toml in registry."
    )
    parser.add_argument(
        "--registry-dir",
        default=DEFAULT_REGISTRY_DIR,
        help=f"Directory containing mesh files (default: {DEFAULT_REGISTRY_DIR})"
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Path to manifest.toml. If not given, inferred from registry-dir."
    )
    args = parser.parse_args()

    # Infer manifest path if not given
    if args.manifest is None:
        registry_parent = os.path.dirname(args.registry_dir.rstrip("/"))
        args.manifest = os.path.join(registry_parent, "manifest.toml")

    results = []

    # If no --mesh given, use synthetic meshes
    if args.mesh is None:
        print("Running 4 synthetic meshes...")
        meshes = [
            ("annulus", ex.annulus()),
            ("donut", ex.donut()),
            ("block_o", ex.block_o()),
            ("structured", ex.structured()),
        ]
        for name, mesh in meshes:
            result = benchmark_mesh(name, mesh)
            if result is not None:
                results.append(result)

    # If --mesh given, resolve and run each
    else:
        print(f"Resolving meshes from {args.registry_dir}...")
        for spec in args.mesh:
            try:
                mesh, display_name = resolve_mesh(spec, args.registry_dir, args.manifest)
                result = benchmark_mesh(display_name, mesh)
                if result is not None:
                    results.append(result)
            except Exception as e:
                print(f"Error resolving {spec!r}: {e}")

    print_table(results)


if __name__ == "__main__":
    main()
