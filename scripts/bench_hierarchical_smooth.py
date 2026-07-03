#!/usr/bin/env python3
"""Bench: hierarchical vs global FEM smoothing (spec-056 US3/FR-011, #104).

Per-variant END-TO-END smoothing wall-clock (clarification Q2: selection +
patch build + solves all counted), skew stats, sub-0.30 tail, interior-tri
invariant. Baseline fem_smoother(n_iter=3) always included; speedup relative
to it. Nonzero exit if any variant breaks the invariant.

Usage:
    python scripts/bench_hierarchical_smooth.py --mesh Test_Case_1
    python scripts/bench_hierarchical_smooth.py --mesh tests/fixtures/meshes/Block_O.14
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from chilmesh import CHILmesh, element_quality

from quadmesh.hierarchical_smooth import hierarchical_smoother
from quadmesh.pipeline import run_pipeline
from quadmesh.post_process import fem_smoother, post_process_routine


def _resolve(mesh_arg: str) -> Path:
    p = Path(mesh_arg)
    if p.exists():
        return p
    cand = Path("tests/fixtures/meshes") / f"{mesh_arg}.14"
    if cand.exists():
        return cand
    sys.exit(f"mesh not found: {mesh_arg} (provision via scripts/fetch_fixtures.py)")


def _interior_tris(mesh: CHILmesh) -> int:
    """Topological triangles (padded rows) with no domain-boundary edge."""
    conn = np.asarray(mesh.connectivity_list)
    if conn.shape[1] < 4:
        return 0
    tri_rows = np.nonzero(conn[:, 2] == conn[:, 3])[0]
    if tri_rows.size == 0:
        return 0
    bedges = mesh.boundary_edges()
    belems = set(np.unique(mesh.edge2elem(bedges).ravel()).tolist()) - {-1}
    return int(sum(1 for t in tri_rows.tolist() if t not in belems))


def _metrics(mesh: CHILmesh) -> dict:
    q = element_quality(mesh.points, mesh.connectivity_list, metric="skew")
    return {
        "mean_skew": float(q.mean()),
        "median_skew": float(np.median(q)),
        "sub030_count": int((q < 0.30).sum()),
        "interior_tris": _interior_tris(mesh),
    }


def _fresh(conn, pts, name):
    return CHILmesh(connectivity=conn.copy(), points=pts.copy(), grid_name=name)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--out", default=None, help="output stem (default output/hier_smooth_bench_<mesh>)")
    ap.add_argument("--skip-cheap", action="store_true", help="skip cheap_global ordering variants")
    args = ap.parse_args()

    path = _resolve(args.mesh)
    stem = args.out or f"output/hier_smooth_bench_{path.stem}"
    Path(stem).parent.mkdir(parents=True, exist_ok=True)

    print(f"loading {path} ...")
    tri = CHILmesh.read_from_fort14(str(path))
    print(f"tri mesh: {tri.n_elems} elems, {tri.n_verts} verts")

    t0 = time.perf_counter()
    quad = run_pipeline(tri, do_post_process=False)
    quad = post_process_routine(quad, n_smooth_iter=0)  # collapse/cleanup, NO smoothing
    print(f"pre-smoothing snapshot: {quad.n_elems} elems ({time.perf_counter()-t0:.1f}s)")
    conn = np.asarray(quad.connectivity_list).copy()
    pts = np.asarray(quad.points).copy()
    name = getattr(quad, "grid_name", None)

    def run_variant(label, fn):
        m = _fresh(conn, pts, name)
        t = time.perf_counter()
        try:
            m = fn(m)
        except Exception as exc:  # record, don't abort the sweep
            return {"variant": label, "error": f"{type(exc).__name__}: {exc}"}
        wall = time.perf_counter() - t
        row = {"variant": label, "wall_s": round(wall, 3)}
        row.update(_metrics(m))
        return row

    variants = [
        ("baseline_global3", lambda m: fem_smoother(m, n_iter=3)),
        ("standalone_skew", lambda m: hierarchical_smoother(m)),
        ("standalone_layer", lambda m: hierarchical_smoother(m, policy="layer")),
        ("standalone_valence", lambda m: hierarchical_smoother(m, policy="valence")),
        ("supplement_skew_g1", lambda m: fem_smoother(hierarchical_smoother(m), n_iter=1)),
    ]
    if not args.skip_cheap:
        variants += [
            ("skew_local_then_cheap", lambda m: hierarchical_smoother(
                m, stage_plan=("local_fem", "cheap_global"))),
            ("skew_cheap_then_local", lambda m: hierarchical_smoother(
                m, stage_plan=("cheap_global", "local_fem"))),
        ]

    rows = [run_variant(lbl, fn) for lbl, fn in variants]

    base = next(r for r in rows if r["variant"] == "baseline_global3")
    base_wall = base.get("wall_s")
    for r in rows:
        if "wall_s" in r and base_wall:
            r["speedup_vs_baseline"] = round(base_wall / r["wall_s"], 2)

    Path(f"{stem}.json").write_text(json.dumps({"mesh": path.stem, "rows": rows}, indent=2))
    hdr = "| variant | wall_s | speedup | mean_skew | median | sub-0.30 | interior_tris |"
    sep = "|---|---|---|---|---|---|---|"
    lines = [f"# hierarchical-smoother bench — {path.stem}", "", hdr, sep]
    for r in rows:
        if "error" in r:
            lines.append(f"| {r['variant']} | ERROR: {r['error']} | | | | | |")
        else:
            lines.append(
                f"| {r['variant']} | {r['wall_s']} | {r.get('speedup_vs_baseline','')} "
                f"| {r['mean_skew']:.4f} | {r['median_skew']:.4f} "
                f"| {r['sub030_count']} | {r['interior_tris']} |")
    Path(f"{stem}.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))

    bad = [r for r in rows if r.get("interior_tris", 0) > 0]
    if bad:
        sys.exit(f"FAITHFULNESS VIOLATION in: {[r['variant'] for r in bad]}")


if __name__ == "__main__":
    main()
