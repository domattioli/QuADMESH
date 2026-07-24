#!/usr/bin/env python
"""Measure QuADMESH+ option A (refuse_boundary_merge) at-scale on real ADCIRC meshes.

Compares baseline vs. refuse_boundary_merge=True, tracking degenerate-boundary-quad
population and quad quality across meshes. Tests issue #98.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
from chilmesh import CHILmesh, element_quality

from quadmesh import tri2quad


# --- Helpers copied verbatim from tests/test_no_interior_tris.py ---


def _edges(el):
    n = len(el)
    return [tuple(sorted((int(el[i]), int(el[(i + 1) % n])))) for i in range(n)]


def _normalize(row):
    """Padded quad [a,b,c,c] (any duplicated vertex) -> the underlying triangle."""
    vs = [int(x) for x in row]
    uniq = list(dict.fromkeys(vs))
    return tuple(uniq) if len(uniq) == 3 else tuple(vs)


def _geo_tri_counts(mesh: CHILmesh) -> tuple[int, int, int]:
    """Return (total, interior, boundary) geometric-triangle counts.

    A geometric triangle is a 4-distinct-index quad with a corner angle
    >= 178 deg (or a zero-length edge). interior = no element edge is a
    domain-boundary edge; boundary = at least one edge is a boundary edge.
    """
    P = np.asarray(mesh.points)[:, :2]
    cl = np.asarray(mesh.connectivity_list)
    ecount: dict = {}
    for row in cl:
        for e in _edges(_normalize(row)):
            ecount[e] = ecount.get(e, 0) + 1
    bset = {e for e, c in ecount.items() if c == 1}
    total = interior = boundary = 0
    for row in cl:
        idx = [int(x) for x in row]
        if len(set(idx)) != 4:
            continue
        pts = P[idx]
        flat = False
        for i in range(4):
            v1 = pts[(i - 1) % 4] - pts[i]
            v2 = pts[(i + 1) % 4] - pts[i]
            n1 = np.linalg.norm(v1)
            n2 = np.linalg.norm(v2)
            if n1 < 1e-12 or n2 < 1e-12:
                flat = True
                break
            ang = np.degrees(
                np.arccos(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))
            )
            if ang >= 178.0:
                flat = True
                break
        if not flat:
            continue
        total += 1
        if any(e in bset for e in _edges(_normalize(row))):
            boundary += 1
        else:
            interior += 1
    return total, interior, boundary


# --- Additional helper ---


def _quad_count(cl):
    """Count rows in connectivity list with 4 distinct vertex indices (true quads)."""
    return sum(1 for row in cl if len(set(int(x) for x in row)) == 4)


# --- Measurement function ---


def run_one(name, path):
    """Run tri2quad with both refuse_boundary_merge=False (baseline) and True (optionA).

    Returns dict with results, or None on error.
    """
    try:
        mesh = CHILmesh.read_from_fort14(path)
        n_tris_in = np.asarray(mesh.connectivity_list).shape[0]

        results = {"name": name, "n_tris_in": n_tris_in, "baseline": {}, "optionA": {}}

        for label, flag in [("baseline", False), ("optionA", True)]:
            t0 = time.time()
            q = tri2quad(mesh, method="quadmesh+", refuse_boundary_merge=flag)
            secs = time.time() - t0

            total, interior, boundary = _geo_tri_counts(q)
            quads = _quad_count(np.asarray(q.connectivity_list))
            n_elems = np.asarray(q.connectivity_list).shape[0]
            skew = element_quality(q.points, q.connectivity_list, metric="skew")
            skew_mean = float(np.nanmean(skew))
            skew_min = float(np.nanmin(skew))

            results[label] = {
                "geo_total": total,
                "geo_interior": interior,
                "geo_boundary": boundary,
                "quads": quads,
                "n_elems": n_elems,
                "skew_mean": skew_mean,
                "skew_min": skew_min,
                "secs": secs,
            }

        return results

    except Exception as e:
        print(f"  {name}: FAILED ({type(e).__name__}: {e})")
        return None


# --- Main ---


def main():
    parser = argparse.ArgumentParser(
        description="Measure refuse_boundary_merge at-scale on ADCIRC meshes."
    )
    parser.add_argument(
        "-m",
        "--mesh",
        action="append",
        dest="meshes",
        help="Mesh name (bare) or absolute .14 path. Repeatable. Default: Test_Case_1, Block_O, LakeErie_5k_500, Deleware_Bay",
    )
    args = parser.parse_args()

    default_meshes = ["Test_Case_1", "Block_O", "LakeErie_5k_500", "Deleware_Bay"]
    mesh_specs = args.meshes if args.meshes else default_meshes

    # Resolve registry dir
    import os

    registry_dir = Path(
        os.environ.get(
            "QUADMESH_REGISTRY_DIR", "/home/user/Valence/registry_data/meshes"
        )
    )

    # Resolve paths
    mesh_paths = []
    for spec in mesh_specs:
        spec_path = Path(spec)
        if spec_path.is_absolute():
            mesh_paths.append((spec_path.stem, spec_path))
        else:
            # Try as <dir>/<name>.14, then <dir>/<name>
            p14 = registry_dir / f"{spec}.14"
            p_base = registry_dir / spec
            if p14.exists():
                mesh_paths.append((spec, p14))
            elif p_base.exists():
                mesh_paths.append((spec, p_base))
            else:
                print(f"  {spec}: SKIP (not found: {p14} or {p_base})")

    # Run measurements
    all_results = []
    for name, path in mesh_paths:
        result = run_one(name, path)
        if result is not None:
            all_results.append(result)

    # Print results table
    if all_results:
        print("\n" + "=" * 150)
        print("RESULTS TABLE")
        print("=" * 150)
        print(
            f"{'Mesh':<25} {'n_tris_in':<12} {'baseline geo_total':<20} {'baseline geo_interior':<20} {'baseline quads':<15} {'baseline skew_mean':<18} {'baseline skew_min':<18} {'baseline secs':<12} {'optionA geo_total':<18} {'optionA geo_interior':<20} {'optionA quads':<15} {'optionA skew_mean':<18} {'optionA skew_min':<18} {'optionA secs':<12} {'Δgeo_total':<15} {'Δgeo_interior':<15}"
        )
        print("-" * 150)

        for r in all_results:
            baseline = r["baseline"]
            optionA = r["optionA"]
            delta_total = optionA["geo_total"] - baseline["geo_total"]
            delta_interior = optionA["geo_interior"] - baseline["geo_interior"]

            print(
                f"{r['name']:<25} {r['n_tris_in']:<12d} {baseline['geo_total']:<20d} {baseline['geo_interior']:<20d} {baseline['quads']:<15d} {baseline['skew_mean']:<18.4f} {baseline['skew_min']:<18.4f} {baseline['secs']:<12.3f} {optionA['geo_total']:<18d} {optionA['geo_interior']:<20d} {optionA['quads']:<15d} {optionA['skew_mean']:<18.4f} {optionA['skew_min']:<18.4f} {optionA['secs']:<12.3f} {delta_total:<15d} {delta_interior:<15d}"
            )

        # Print interior-invariant audit
        print("\n" + "=" * 150)
        print("INTERIOR-INVARIANT AUDIT")
        print("=" * 150)
        for r in all_results:
            baseline_interior = r["baseline"]["geo_interior"]
            optionA_interior = r["optionA"]["geo_interior"]
            print(f"{r['name']:<25}: baseline={baseline_interior}, optionA={optionA_interior}", end="")
            if baseline_interior == 0 and optionA_interior == 0:
                print(" ✓ PASS")
            else:
                print(" *** INTERIOR INVARIANT VIOLATED ***")

        # Final summary
        print("\n" + "=" * 150)
        print("SUMMARY")
        print("=" * 150)
        print(f"Total meshes run: {len(all_results)}")
        reduced = sum(1 for r in all_results if r["optionA"]["geo_total"] < r["baseline"]["geo_total"])
        if reduced > 0:
            print(f"Meshes where optionA reduced geo_total: {reduced}")
        else:
            print("No meshes reduced geo_total with optionA")


if __name__ == "__main__":
    main()
