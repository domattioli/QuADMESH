#!/usr/bin/env python
"""Benchmark conditioning on chilmesh.examples meshes."""
from __future__ import annotations

import traceback
import numpy as np
import chilmesh.examples as ex
from chilmesh import element_quality

from quadmesh.pipeline import run_pipeline
from quadmesh.create_quad_domain import create_quad_domain
from quadmesh.precondition import condition_triangulation

def _count_tris(connectivity_list):
    """Count residual triangles (detected as width-3 row or padded tri)."""
    count = 0
    for row in np.asarray(connectivity_list):
        if len(row) == 3:
            count += 1
        elif len(row) >= 4 and row[2] == row[3]:
            count += 1
    return count

def benchmark_mesh(name, mesh):
    """Run baseline and conditioned pipeline, return comparison dict."""
    print(f"\n{name}...", end=" ", flush=True)

    # Baseline
    baseline = run_pipeline(mesh, precondition=False)
    baseline_qual = element_quality(baseline.points, baseline.connectivity_list, metric="aspect_ratio")
    baseline_mean = float(np.nanmean(baseline_qual))
    baseline_min = float(np.nanmin(baseline_qual))
    baseline_tris = _count_tris(baseline.connectivity_list)

    # Conditioned
    conditioned = run_pipeline(mesh, precondition=True)
    cond_qual = element_quality(conditioned.points, conditioned.connectivity_list, metric="aspect_ratio")
    cond_mean = float(np.nanmean(cond_qual))
    cond_min = float(np.nanmin(cond_qual))
    cond_tris = _count_tris(conditioned.connectivity_list)

    # Conditioning stats
    domain = create_quad_domain(mesh)
    _, stats = condition_triangulation(domain, collect_stats=True)
    total_before = sum(s['unmatched_before'] for s in stats)
    total_after = sum(s['unmatched_after'] for s in stats)

    print("✓")
    return {
        'name': name,
        'baseline_mean': baseline_mean,
        'baseline_min': baseline_min,
        'conditioned_mean': cond_mean,
        'conditioned_min': cond_min,
        'mean_delta': cond_mean - baseline_mean,
        'min_delta': cond_min - baseline_min,
        'baseline_tris': baseline_tris,
        'conditioned_tris': cond_tris,
        'unmatched_before': total_before,
        'unmatched_after': total_after,
    }

def main():
    meshes = [
        ("annulus", ex.annulus()),
        ("donut", ex.donut()),
        ("block_o", ex.block_o()),
        ("structured", ex.structured()),
    ]

    results = []
    for name, mesh in meshes:
        try:
            result = benchmark_mesh(name, mesh)
            results.append(result)
        except Exception as e:
            print(f"✗ ({type(e).__name__})")
            traceback.print_exc()

    # Print table
    print("\n" + "="*140)
    print(f"{'Mesh':<15} | {'Baseline Mean':<13} | {'Cond Mean':<13} | {'Mean Δ':<10} | "
          f"{'Baseline Min':<13} | {'Cond Min':<13} | {'Min Δ':<10} | "
          f"{'Base Tris':<10} | {'Cond Tris':<10} | {'Unmatched B→A':<15}")
    print("="*140)

    for r in results:
        print(f"{r['name']:<15} | {r['baseline_mean']:>12.4f} | {r['conditioned_mean']:>12.4f} | "
              f"{r['mean_delta']:>9.4f} | {r['baseline_min']:>12.4f} | {r['conditioned_min']:>12.4f} | "
              f"{r['min_delta']:>9.4f} | {r['baseline_tris']:>9d} | {r['conditioned_tris']:>9d} | "
              f"{r['unmatched_before']:>5d}→{r['unmatched_after']:>5d}")
    print("="*140)

if __name__ == "__main__":
    main()
