#!/usr/bin/env python3
"""Measure mesh size-field drift through tri2quad + smoothing.

Issue #21: Quantify whether tri2quad and post-processing smoothing cause
mesh edge lengths to diverge from the input mesh's implied size function h(x,y).

h_local is the mean length of unique incident edges in the input triangular mesh,
sampled at each edge via nearest input-mesh vertex to the edge midpoint.
Ratio = edge_length / h_local. Healthy range ≈ [0.5, 2.0].
"""

import argparse
import numpy as np
from scipy.spatial import cKDTree
import time
from pathlib import Path


def h_field(points, tris):
    """Compute per-vertex h from input triangular mesh.

    h = mean length of unique incident edges per vertex.

    Args:
        points: (N, 2 or 3) ndarray of vertex coordinates
        tris: (M, 3) int ndarray of triangle connectivity

    Returns:
        tree: cKDTree over points[:, :2]
        h: (N,) ndarray with per-vertex h values
    """
    points_2d = points[:, :2]
    tree = cKDTree(points_2d)

    h_sum = np.zeros(len(points))
    h_count = np.zeros(len(points), dtype=int)

    # Extract unique undirected edges from triangles
    edges_set = set()
    for tri in tris:
        for i in range(3):
            v0, v1 = tri[i], tri[(i + 1) % 3]
            edge = tuple(sorted([v0, v1]))
            if edge[0] != edge[1]:  # Skip degenerate
                edges_set.add(edge)

    # Accumulate edge lengths at incident vertices
    for v0, v1 in edges_set:
        length = np.linalg.norm(points_2d[v1] - points_2d[v0])
        h_sum[v0] += length
        h_count[v0] += 1
        h_sum[v1] += length
        h_count[v1] += 1

    # Compute h = mean incident edge length
    h = np.full(len(points), np.nan)
    mask = h_count > 0
    h[mask] = h_sum[mask] / h_count[mask]

    # Fill orphan vertices with global mean
    global_mean = np.nanmean(h)
    h[~mask] = global_mean if not np.isnan(global_mean) else 1.0

    return tree, h


def edge_ratios(mesh, tree, h):
    """Compute L/h_local for all edges in mesh.

    Args:
        mesh: CHILmesh object
        tree: cKDTree from h_field over input points
        h: per-vertex h array from input mesh

    Returns:
        (n_edges,) ndarray of ratios
    """
    points = np.asarray(mesh.points)[:, :2]
    connectivity = np.asarray(mesh.connectivity_list)

    edges_set = set()

    for row in connectivity:
        # Drop consecutive duplicates (including wraparound)
        unique_seq = []
        for v in row:
            if v < 0:  # Padding marker
                break
            if not unique_seq or unique_seq[-1] != v:
                unique_seq.append(v)

        # Remove trailing duplicate if it matches start
        if len(unique_seq) > 1 and unique_seq[0] == unique_seq[-1]:
            unique_seq = unique_seq[:-1]

        # Form cyclic consecutive pairs
        for i in range(len(unique_seq)):
            v0 = unique_seq[i]
            v1 = unique_seq[(i + 1) % len(unique_seq)]
            edge = tuple(sorted([v0, v1]))
            if edge[0] != edge[1]:
                edges_set.add(edge)

    ratios = []
    for v0, v1 in edges_set:
        L = np.linalg.norm(points[v1] - points[v0])
        midpoint = (points[v0] + points[v1]) / 2
        _, nearest_idx = tree.query(midpoint)
        h_loc = h[nearest_idx]
        ratio = L / h_loc if h_loc > 0 else 1.0
        ratios.append(ratio)

    return np.array(ratios)


def stats(r):
    """Compute per-stage statistics."""
    return {
        "n": len(r),
        "p5": float(np.percentile(r, 5)),
        "p50": float(np.percentile(r, 50)),
        "p95": float(np.percentile(r, 95)),
        "mean": float(np.mean(r)),
        "frac_in_band": float(np.sum((r >= 0.5) & (r <= 2.0)) / len(r)),
        "min": float(np.min(r)),
        "max": float(np.max(r)),
    }


def run_fixture(path):
    """Process one fixture through tri2quad + smoothing pipeline."""
    from chilmesh import CHILmesh
    from quadmesh.tri2quad import tri2quad_routine
    from quadmesh.post_process import post_process_routine

    result = {}

    try:
        # Load input mesh
        mesh = CHILmesh.read_from_fort14(path, compute_layers=False)
        pts = np.asarray(mesh.points)
        tris = np.asarray(mesh.connectivity_list)[:, :3].astype(int)

        # Compute h field from input
        tree, h = h_field(pts, tris)

        # Stage 1: input triangles
        r_input = edge_ratios(mesh, tree, h)
        result["input-tris"] = stats(r_input)

        # Stage 2: tri2quad
        t0 = time.time()
        try:
            quad = tri2quad_routine(mesh)
            result["post-tri2quad"] = stats(edge_ratios(quad, tree, h))
        except Exception as e:
            result["post-tri2quad"] = {"error": str(type(e).__name__)}
        tri2quad_time = time.time() - t0

        # Stage 3: post-smooth
        t0 = time.time()
        try:
            smoothed = post_process_routine(quad)
            result["post-smooth"] = stats(edge_ratios(smoothed, tree, h))
        except Exception as e:
            result["post-smooth"] = {"error": str(type(e).__name__)}
        smooth_time = time.time() - t0

        result["timings"] = {
            "tri2quad_sec": tri2quad_time,
            "smooth_sec": smooth_time,
        }

    except Exception as e:
        print(f"Error processing {path}: {type(e).__name__}: {e}")
        return result

    return result


def offline_fixtures():
    """Provision token-free .14 meshes bundled in ``chilmesh.data`` to temp files.

    annulus (concentric) + donut (hole) are uniform-h by construction, so they
    are ideal #21 probes: any |edge|/h_local drift is pipeline-induced, not an
    input size-transition artifact. Lets this report run in CI / offline when the
    Valence-only fixtures under tests/fixtures/meshes/ are absent (no PAT).
    """
    from importlib import resources
    import tempfile

    out = []
    for name in ("annulus_200pts.fort.14", "donut_domain.fort.14"):
        try:
            raw = resources.files("chilmesh").joinpath("data", name).read_text()
        except (FileNotFoundError, ModuleNotFoundError, AttributeError):
            continue
        stem = name.split(".")[0]
        fd = tempfile.NamedTemporaryFile("w", prefix=f"{stem}_", suffix=".14", delete=False)
        fd.write(raw)
        fd.close()
        out.append(fd.name)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixtures",
        nargs="*",
        default=[
            "tests/fixtures/meshes/Test_Case_1.14",
            "tests/fixtures/meshes/LakeErie_5k_500.14",
            "tests/fixtures/meshes/Deleware_Bay_hmin_100_hmax_20000.14",
        ],
        help="Paths to .14 fixture files",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Ignore fixture paths; use chilmesh.data bundled meshes (no PAT).",
    )
    args = parser.parse_args()

    fixtures = args.fixtures
    if args.offline or not any(Path(f).exists() for f in fixtures):
        offline = offline_fixtures()
        if offline:
            print("_(offline mode — chilmesh.data bundled meshes; no Valence PAT)_")
            fixtures = offline

    for fixture_path in fixtures:
        p = Path(fixture_path)
        if not p.exists():
            print(f"⚠ {fixture_path} not found, skipping")
            continue

        print(f"\n## {p.name}\n")

        result = run_fixture(fixture_path)

        # Header
        print("| stage | n_edges | p5 | p50 | p95 | mean | frac in [0.5,2.0] | min | max |")
        print("|---|---|---|---|---|---|---|---|---|")

        # Rows
        for stage in ["input-tris", "post-tri2quad", "post-smooth"]:
            if stage not in result:
                continue
            st = result[stage]
            if "error" in st:
                print(f"| {stage} | ERROR: {st['error']} |||||||||")
            else:
                print(
                    f"| {stage} | {st['n']} | {st['p5']:.3f} | {st['p50']:.3f} | {st['p95']:.3f} | "
                    f"{st['mean']:.3f} | {st['frac_in_band']:.3f} | {st['min']:.3f} | {st['max']:.3f} |"
                )

        if "timings" in result:
            t = result["timings"]
            print(f"\n**Timing**: tri2quad {t['tri2quad_sec']:.2f}s, smooth {t['smooth_sec']:.2f}s")


if __name__ == "__main__":
    main()
