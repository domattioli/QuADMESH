"""Recompute base+extra per-triangle features and re-join with saved MC pass
counts (results/<tag>_pass.csv) — no MC re-run needed. Rewrites
results/<tag>_features.csv and results/<tag>_merged.csv."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from chilmesh import CHILmesh

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
sys.path.insert(0, str(HERE))
from features import compute_tri_features
from features_extra import compute_extra_features


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    meta = json.load(open(RES / f"{args.tag}_meta.json"))
    m = CHILmesh.read_from_fort14(meta["mesh"])
    feats = compute_tri_features(m)
    feats.update(compute_extra_features(m))
    keys = list(feats.keys())
    N = len(feats["tri_idx"])

    p = pd.read_csv(RES / f"{args.tag}_pass.csv").sort_values("tri_idx")
    rc = p["routed_count"].to_numpy()
    pf = p["pass_freq"].to_numpy()
    assert len(rc) == N, f"pass rows {len(rc)} != n_tris {N}"

    with open(RES / f"{args.tag}_features.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(keys)
        for r in range(N):
            w.writerow([feats[k][r] for k in keys])
    with open(RES / f"{args.tag}_merged.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(keys + ["routed_count", "pass_freq"])
        for r in range(N):
            w.writerow([feats[k][r] for k in keys] + [int(rc[r]), float(pf[r])])
    print(f"rebuilt {args.tag} with {len(keys)} features (added valence + flow)")


if __name__ == "__main__":
    main()
