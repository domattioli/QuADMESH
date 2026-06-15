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


def benchmark_mesh(name: str, mesh: CHILmesh, max_passes: int | None = None,
                   quality_aware: bool = False) -> dict | None:
    """Run baseline and conditioned pipeline, return comparison dict.

    Args:
        name: display name for the mesh.
        mesh: CHILmesh instance.
        max_passes: optional max_passes_per_layer for conditioning.

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
        n_elems_base = np.asarray(baseline.connectivity_list).shape[0]

        # Conditioned
        t0 = time.time()
        cond_kwargs = {}
        if max_passes is not None:
            cond_kwargs["max_passes_per_layer"] = max_passes
        if quality_aware:
            cond_kwargs["quality_aware"] = True
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
        n_elems_cond = np.asarray(conditioned.connectivity_list).shape[0]

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
            "unmatched_before": unmatched_before,
            "unmatched_after": unmatched_after,
            "swaps": swaps,
            "n_layers": n_layers,
            "baseline_secs": baseline_secs,
            "cond_secs": cond_secs,
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
    parser.add_argument(
        "--max-passes",
        type=int,
        default=None,
        help="Max passes per layer for conditioning (optional)."
    )
    parser.add_argument(
        "--quality-aware",
        action="store_true",
        help="Accept a swap only if it also does not lower worst incident triangle quality."
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
            result = benchmark_mesh(name, mesh, max_passes=args.max_passes,
                                    quality_aware=args.quality_aware)
            if result is not None:
                results.append(result)

    # If --mesh given, resolve and run each
    else:
        print(f"Resolving meshes from {args.registry_dir}...")
        for spec in args.mesh:
            try:
                mesh, display_name = resolve_mesh(spec, args.registry_dir, args.manifest)
                result = benchmark_mesh(display_name, mesh, max_passes=args.max_passes,
                                        quality_aware=args.quality_aware)
                if result is not None:
                    results.append(result)
            except Exception as e:
                print(f"Error resolving {spec!r}: {e}")

    print_table(results)


if __name__ == "__main__":
    main()
