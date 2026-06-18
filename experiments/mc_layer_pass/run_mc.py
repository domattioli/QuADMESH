"""Monte-Carlo study: randomize the QuADMESH+ per-layer walk start vertex and
record which triangles get routed to the leftover handler ("passed to the next
layer" because they were not merged into a quad within their layer).

Each run uses a different random start vertex for every outer-vertex path in
every layer (the ``_START_INDEX_SELECTOR`` hook in quadmesh.identify_edges); the
default algorithm starts at the first outer "corner". Across N runs we count,
per original triangle, how often it was routed (pass_freq). Fewer routed
triangles == better, so high-pass-frequency triangles mark problem areas.

Usage:
    python experiments/mc_layer_pass/run_mc.py --mesh /tmp/WNAT_Hagen.14 \
        --runs 200 --workers 4 --tag wnat_hagen
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"

# Per-worker global state (loaded once per process by the Pool initializer).
_G: dict = {}


def _init_worker(mesh_path: str) -> None:
    from chilmesh import CHILmesh
    m = CHILmesh.read_from_fort14(mesh_path)
    tris = np.asarray(m.connectivity_list)[:, :3].astype(int)
    _G["mesh"] = m
    _G["tris"] = tris
    _G["pts0"] = m.points.copy()
    _G["cl0"] = np.asarray(m.connectivity_list).copy()


def _run_one(seed: int):
    """Run the per-layer sweep with a random start for one seed; return summary."""
    import quadmesh.identify_edges as ie
    from quadmesh.tri2quad import _quadmesh_plus_per_layer as run

    m = _G["mesh"]
    tris = _G["tris"]
    rng = np.random.default_rng(seed)
    ie._START_INDEX_SELECTOR = lambda verts, counts: int(rng.integers(0, len(verts)))
    trace: dict = {}
    m.points = _G["pts0"].copy()
    m.connectivity_list = _G["cl0"].copy()
    t0 = time.time()
    quads, leftover, _ = run(m, tris, True, trace=trace)
    dt = time.time() - t0
    # restore + reset hook
    m.points = _G["pts0"].copy()
    m.connectivity_list = _G["cl0"].copy()
    ie._START_INDEX_SELECTOR = None
    routed = np.fromiter(trace.get("routed", ()), dtype=np.int32)
    return {
        "seed": int(seed),
        "n_routed": int(routed.size),
        "n_merged": int(len(trace.get("merged", ()))),
        "n_quads": int(len(quads)),
        "n_leftover_final": int(len(leftover)),
        "seconds": float(dt),
        "routed": routed,
    }


def main() -> int:
    import multiprocessing as mp
    from features import compute_tri_features  # same dir on sys.path
    from features_extra import compute_extra_features
    from chilmesh import CHILmesh

    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--runs", type=int, default=200)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--base-seed", type=int, default=0)
    args = ap.parse_args()

    RESULTS.mkdir(parents=True, exist_ok=True)
    mesh_path = str(Path(args.mesh).resolve())

    # Static per-triangle features + mesh meta (computed once in the parent).
    base = CHILmesh.read_from_fort14(mesh_path)
    n_tris = int(np.asarray(base.connectivity_list).shape[0])
    n_verts = int(base.n_verts)
    n_layers = int(base.n_layers)
    feats = compute_tri_features(base)
    feats.update(compute_extra_features(base))
    feat_keys = list(feats.keys())

    seeds = [args.base_seed + i for i in range(args.runs)]
    pass_count = np.zeros(n_tris, dtype=np.int64)
    per_run = []

    t0 = time.time()
    ctx = mp.get_context("spawn")
    with ctx.Pool(
        processes=args.workers, initializer=_init_worker, initargs=(mesh_path,)
    ) as pool:
        for i, res in enumerate(pool.imap_unordered(_run_one, seeds, chunksize=1)):
            routed = res.pop("routed")
            np.add.at(pass_count, routed, 1)
            per_run.append(res)
            if (i + 1) % 10 == 0 or (i + 1) == len(seeds):
                print(f"  {i + 1}/{len(seeds)} runs done", flush=True)
    total_s = time.time() - t0

    n_runs = len(seeds)
    pass_freq = pass_count / float(n_runs)

    tag = args.tag
    # features.csv
    import csv
    with open(RESULTS / f"{tag}_features.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(feat_keys)
        for r in range(n_tris):
            w.writerow([feats[k][r] for k in feat_keys])
    # pass.csv
    with open(RESULTS / f"{tag}_pass.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["tri_idx", "routed_count", "pass_freq", "n_runs"])
        for r in range(n_tris):
            w.writerow([r, int(pass_count[r]), float(pass_freq[r]), n_runs])
    # merged.csv (features + pass)
    with open(RESULTS / f"{tag}_merged.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(feat_keys + ["routed_count", "pass_freq"])
        for r in range(n_tris):
            w.writerow([feats[k][r] for k in feat_keys] + [int(pass_count[r]), float(pass_freq[r])])
    # per_run.csv
    with open(RESULTS / f"{tag}_per_run.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        cols = ["seed", "n_routed", "n_merged", "n_quads", "n_leftover_final", "seconds"]
        w.writerow(cols)
        for row in sorted(per_run, key=lambda d: d["seed"]):
            w.writerow([row[c] for c in cols])

    nr = np.array([d["n_routed"] for d in per_run], dtype=float)
    meta = {
        "mesh": mesh_path,
        "tag": tag,
        "n_runs": n_runs,
        "n_tris": n_tris,
        "n_verts": n_verts,
        "n_layers": n_layers,
        "total_seconds": total_s,
        "mean_n_routed": float(nr.mean()),
        "std_n_routed": float(nr.std()),
        "min_n_routed": float(nr.min()),
        "max_n_routed": float(nr.max()),
        "n_tris_ever_routed": int((pass_count > 0).sum()),
        "n_tris_always_routed": int((pass_count == n_runs).sum()),
    }
    with open(RESULTS / f"{tag}_meta.json", "w") as fh:
        json.dump(meta, fh, indent=2)

    print(json.dumps(meta, indent=2))
    print(f"wrote {tag}_features.csv, {tag}_pass.csv, {tag}_merged.csv, "
          f"{tag}_per_run.csv, {tag}_meta.json to {RESULTS}")
    return 0


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE))  # make features.py importable
    raise SystemExit(main())
