#!/usr/bin/env python
"""Benchmark script for quadmesh+ tri→quad pipeline.

Measures per-phase wall-clock time, quality metrics before/after, and element composition.
Outputs: PNG histogram, JSON report, Markdown summary, stdout summary.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

# Set matplotlib backend BEFORE importing pyplot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import numpy as np
from chilmesh import CHILmesh, element_quality

from quadmesh.create_quad_domain import create_quad_domain
from quadmesh.post_process import post_process_routine
from quadmesh.tri2quad import tri2quad_routine


def _is_quad_row(row):
    """Check if a row is a genuine quad (not a padded tri)."""
    row = np.asarray(row)
    # Quad: all 4 vertices distinct
    # Padded tri: row[2] == row[3] or row[2] is negative or duplicated
    if len(row) != 4:
        return False
    # Padded tri: last vertex repeats third, or is negative
    if row[3] == row[2] or row[3] < 0:
        return False
    # Check for any duplicates in the row
    if len(set(row)) != 4:
        return False
    return True


def element_composition(connectivity_list):
    """Count genuine quads vs tris in connectivity list.

    Returns:
        (n_quads, n_tris, pct_quads)
    """
    conn = np.asarray(connectivity_list)
    n_quads = sum(1 for row in conn if _is_quad_row(row))
    n_tris = len(conn) - n_quads
    pct_quads = 100.0 * n_quads / len(conn) if len(conn) > 0 else 0.0
    return n_quads, n_tris, pct_quads


def quality_stats(q_array):
    """Compute quality statistics from an array of element qualities.

    Args:
        q_array: 1D numpy array of quality values [0, 1].

    Returns:
        dict with keys: mean, min, max, std, median, n_bad (<0.30), pct_bad, n_elems
    """
    q = np.asarray(q_array, dtype=float)
    if len(q) == 0:
        return {
            "mean": np.nan,
            "min": np.nan,
            "max": np.nan,
            "std": np.nan,
            "median": np.nan,
            "n_bad": 0,
            "pct_bad": 0.0,
            "n_elems": 0,
        }
    n_bad = np.sum(q < 0.30)
    return {
        "mean": float(np.mean(q)),
        "min": float(np.min(q)),
        "max": float(np.max(q)),
        "std": float(np.std(q)),
        "median": float(np.median(q)),
        "n_bad": int(n_bad),
        "pct_bad": float(100.0 * n_bad / len(q)),
        "n_elems": int(len(q)),
    }


def bench_quadmesh_plus(
    mesh_path: str | Path,
    out_dir: str | Path = "output/bench",
    no_post_process: bool = False,
    profile: bool = False,
    write_out: str | Path | None = None,
) -> dict:
    """Run quadmesh+ pipeline with per-phase timing.

    Args:
        mesh_path: Path to input .14 mesh.
        out_dir: Directory for outputs (created if needed).
        no_post_process: If True, skip post-process step.
        profile: If True, run a second pass under cProfile.
        write_out: Optional path to write output mesh.

    Returns:
        Dict with benchmark results: phase_times, quality_before/after, composition, etc.
    """
    mesh_path = Path(mesh_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mesh_stem = mesh_path.stem

    # Load input mesh
    print(f"[BENCH] Loading {mesh_path}...", flush=True)
    t0 = time.perf_counter()
    input_mesh = CHILmesh.read_from_fort14(str(mesh_path))
    t_load = time.perf_counter() - t0
    print(f"  load: {t_load:.3f}s", flush=True)

    n_nodes_in = input_mesh.n_verts
    n_elems_in = input_mesh.n_elems

    # Compute input quality (tri metric)
    print(f"[BENCH] Computing input quality...", flush=True)
    q_before = element_quality(input_mesh.points, input_mesh.connectivity_list, metric="skew")

    # Phase 1: create_quad_domain
    print(f"[BENCH] Phase 1: create_quad_domain", flush=True)
    t0 = time.perf_counter()
    domain = create_quad_domain(input_mesh, polygon=None)
    t_create_domain = time.perf_counter() - t0
    print(f"  create_quad_domain: {t_create_domain:.3f}s", flush=True)

    # Phase 2: tri2quad_routine
    print(f"[BENCH] Phase 2: tri2quad_routine", flush=True)
    t0 = time.perf_counter()
    quad = tri2quad_routine(domain, can_remove_edges=True, parent=input_mesh, method="quadmesh+")
    t_tri2quad = time.perf_counter() - t0
    print(f"  tri2quad_routine: {t_tri2quad:.3f}s", flush=True)

    n_elems_after_tri2quad = quad.n_elems

    # Phase 3: post_process_routine (optional)
    if no_post_process:
        result = quad
        t_post_process = 0.0
    else:
        print(f"[BENCH] Phase 3: post_process_routine", flush=True)
        t0 = time.perf_counter()
        result = post_process_routine(
            quad,
            can_remove_edges=True,
            n_smooth_iter=3,
            max_outer_iter=5,
            max_inner_iter=5,
            truss_smooth=False,
            truss_fh=None,
        )
        t_post_process = time.perf_counter() - t0
        print(f"  post_process_routine: {t_post_process:.3f}s", flush=True)

    n_elems_out = result.n_elems
    n_nodes_out = result.n_verts

    # Compute output quality
    print(f"[BENCH] Computing output quality...", flush=True)
    q_after = element_quality(result.points, result.connectivity_list, metric="skew")

    # Element composition
    n_quads_out, n_tris_out, pct_quads_out = element_composition(result.connectivity_list)

    # Wall-clock summary
    t_total = t_load + t_create_domain + t_tri2quad + t_post_process

    phase_times = {
        "load": t_load,
        "create_quad_domain": t_create_domain,
        "tri2quad_routine": t_tri2quad,
        "post_process_routine": t_post_process,
    }

    # Optional write
    if write_out:
        print(f"[BENCH] Writing output to {write_out}...", flush=True)
        result.write_to_fort14(str(write_out))

    # Optional cProfile pass
    subphase_times = None
    if profile:
        print(f"[BENCH] Running cProfile pass (no post-process for consistency)...", flush=True)
        import cProfile
        import pstats
        from io import StringIO

        input_mesh2 = CHILmesh.read_from_fort14(str(mesh_path))
        domain2 = create_quad_domain(input_mesh2, polygon=None)

        profiler = cProfile.Profile()
        profiler.enable()
        quad2 = tri2quad_routine(domain2, can_remove_edges=True, parent=input_mesh2, method="quadmesh+")
        profiler.disable()

        s = StringIO()
        ps = pstats.Stats(profiler, stream=s)
        ps.strip_dirs()
        ps.sort_stats("cumulative")

        # Extract cumulative times for key functions
        func_names = [
            "tri2quad_routine",
            "_quadmesh_plus_per_layer",
            "_match_tris_to_quads",
            "_remove_boundary_tris",
            "_edge_swap_tri_pairs",
            "_point_insert_tri_pairs",
            "post_process_routine",
            "doublet_collapse",
            "quad_vertex_merge",
            "cleanup_boundary_quads",
            "fem_smoother",
            "_fix_bowties",
            "read_from_fort14",
            "element_quality",
        ]

        subphase_times = {}
        for func in ps.stats:
            func_basename = func[2] if len(func) > 2 else ""
            for target in func_names:
                if target in func_basename:
                    ct = ps.stats[func][3]  # cumulative time
                    if target not in subphase_times:
                        subphase_times[target] = ct

    # Build report dict
    report = {
        "mesh": str(mesh_path),
        "mesh_stem": mesh_stem,
        "n_nodes_in": int(n_nodes_in),
        "n_nodes_out": int(n_nodes_out),
        "n_elems_in": int(n_elems_in),
        "n_elems_after_tri2quad": int(n_elems_after_tri2quad),
        "n_elems_out": int(n_elems_out),
        "n_quads_out": int(n_quads_out),
        "n_tris_out": int(n_tris_out),
        "pct_quads_out": float(pct_quads_out),
        "phase_times": phase_times,
        "total_s": float(t_total),
        "subphase_times": subphase_times,
        "quality_before": quality_stats(q_before),
        "quality_after": quality_stats(q_after),
    }

    # Write JSON
    json_path = out_dir / f"{mesh_stem}_bench.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[BENCH] JSON report written: {json_path}", flush=True)

    # Write Markdown
    md_path = out_dir / f"{mesh_stem}_bench.md"
    with open(md_path, "w") as f:
        f.write(f"# Benchmark Report: {mesh_stem}\n\n")
        f.write(f"**Mesh:** {mesh_path}\n")
        f.write(f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Phase Timing\n\n")
        f.write("| Phase | Time (s) | % of Total |\n")
        f.write("|-------|----------|------------|\n")
        for phase, t_s in phase_times.items():
            pct = 100.0 * t_s / t_total if t_total > 0 else 0.0
            f.write(f"| {phase} | {t_s:.4f} | {pct:.1f}% |\n")
        f.write(f"| **Total** | **{t_total:.4f}** | **100.0%** |\n\n")

        f.write("## Quality (Skew Metric)\n\n")
        f.write("| Metric | Before | After |\n")
        f.write("|--------|--------|-------|\n")
        f.write(
            f"| Mean | {report['quality_before']['mean']:.4f} | {report['quality_after']['mean']:.4f} |\n"
        )
        f.write(
            f"| Min | {report['quality_before']['min']:.4f} | {report['quality_after']['min']:.4f} |\n"
        )
        f.write(
            f"| Max | {report['quality_before']['max']:.4f} | {report['quality_after']['max']:.4f} |\n"
        )
        f.write(
            f"| Std | {report['quality_before']['std']:.4f} | {report['quality_after']['std']:.4f} |\n"
        )
        f.write(
            f"| Median | {report['quality_before']['median']:.4f} | {report['quality_after']['median']:.4f} |\n"
        )
        f.write(
            f"| % Bad (<0.30) | {report['quality_before']['pct_bad']:.1f}% | {report['quality_after']['pct_bad']:.1f}% |\n"
        )
        f.write(f"| N Elements | {report['quality_before']['n_elems']} | {report['quality_after']['n_elems']} |\n\n")

        f.write("## Element Composition\n\n")
        f.write(f"- **Input:** {n_elems_in} tris\n")
        f.write(f"- **After tri2quad:** {n_elems_after_tri2quad} mixed elements\n")
        f.write(f"- **Output:** {n_quads_out} quads + {n_tris_out} tris ({pct_quads_out:.1f}% quads)\n\n")

        if subphase_times:
            f.write("## Sub-phase Times (cProfile, if run with --profile)\n\n")
            f.write("| Function | Time (s) |\n")
            f.write("|----------|----------|\n")
            for fname, t_s in sorted(subphase_times.items(), key=lambda x: x[1], reverse=True):
                f.write(f"| {fname} | {t_s:.4f} |\n")

    print(f"[BENCH] Markdown report written: {md_path}", flush=True)

    # Write PNG histogram
    print(f"[BENCH] Generating quality histogram...", flush=True)
    fig, ax = plt.subplots(figsize=(10, 6), dpi=140)

    bins = np.linspace(0, 1, 41)  # 40 bins
    ax.hist(q_before, bins=bins, alpha=0.5, label="Input tris", edgecolor="black", linewidth=0.5)
    ax.hist(q_after, bins=bins, alpha=0.5, label="quadmesh+ output", edgecolor="black", linewidth=0.5)

    ax.axvline(report["quality_after"]["mean"], color="red", linestyle="--", linewidth=2, label=f"Output mean ({report['quality_after']['mean']:.3f})")
    ax.axvline(0.30, color="orange", linestyle="--", linewidth=2, label="Bad threshold (0.30)")

    ax.set_xlabel("Skew Quality (1 = ideal)", fontsize=12)
    ax.set_ylabel("Element Count", fontsize=12)
    ax.set_title(f"quadmesh+ Skew Quality — {mesh_stem} ({n_elems_in} → {n_elems_out} elements)", fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    png_path = out_dir / f"{mesh_stem}_quality_hist.png"
    fig.savefig(png_path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"[BENCH] PNG histogram written: {png_path}", flush=True)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark quadmesh+ tri→quad pipeline."
    )
    parser.add_argument("--mesh", type=str, required=True, help="Path to input .14 mesh.")
    parser.add_argument(
        "--out-dir",
        type=str,
        default="output/bench",
        help="Output directory for reports (default: output/bench).",
    )
    parser.add_argument(
        "--no-post",
        action="store_true",
        help="Skip post-process step.",
    )
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Run a second pass under cProfile.",
    )
    parser.add_argument(
        "--write-out",
        type=str,
        default=None,
        help="Optional path to write output mesh.",
    )

    args = parser.parse_args()

    report = bench_quadmesh_plus(
        args.mesh,
        out_dir=args.out_dir,
        no_post_process=args.no_post,
        profile=args.profile,
        write_out=args.write_out,
    )

    # Print summary
    print("\n" + "=" * 70, flush=True)
    print("BENCHMARK SUMMARY", flush=True)
    print("=" * 70, flush=True)
    print(f"Mesh: {report['mesh_stem']}", flush=True)
    print(f"Nodes: {report['n_nodes_in']} → {report['n_nodes_out']}", flush=True)
    print(f"Elements: {report['n_elems_in']} → {report['n_elems_out']} ({report['pct_quads_out']:.1f}% quads)", flush=True)
    print(f"\nPhase Timing:", flush=True)
    for phase, t_s in report["phase_times"].items():
        pct = 100.0 * t_s / report["total_s"] if report["total_s"] > 0 else 0.0
        print(f"  {phase:25s}: {t_s:8.4f}s ({pct:5.1f}%)", flush=True)
    print(f"  {'Total':25s}: {report['total_s']:8.4f}s (100.0%)", flush=True)
    print(f"\nQuality (Skew):", flush=True)
    print(f"  Mean: {report['quality_before']['mean']:.4f} → {report['quality_after']['mean']:.4f}", flush=True)
    print(f"  Min:  {report['quality_before']['min']:.4f} → {report['quality_after']['min']:.4f}", flush=True)
    print(f"  Max:  {report['quality_before']['max']:.4f} → {report['quality_after']['max']:.4f}", flush=True)
    print(f"  Median: {report['quality_before']['median']:.4f} → {report['quality_after']['median']:.4f}", flush=True)
    print(f"  Bad (<0.30): {report['quality_before']['pct_bad']:.1f}% → {report['quality_after']['pct_bad']:.1f}%", flush=True)
    print("=" * 70, flush=True)


if __name__ == "__main__":
    main()
