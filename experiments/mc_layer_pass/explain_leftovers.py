"""Explain the common leftover (routed) triangles from the MC layer-pass study.

Adds, on top of analyze.py:
  1. default-start vs random-start total routed (is the deterministic corner
     start better/worse than a random start? upper bound on achievable gain).
  2. motif breakdown of always-routed (pass_freq==1) and frequent (>=0.5) tris.
  3. de-confounded correlations: pass_freq vs features within OE-only and within
     interior-only (n_boundary_edges==0) subsets.
  4. spatial clustering: do always-routed tris cluster (strip ends / regions) or
     scatter? clustering coeff vs random baseline.

Usage: python experiments/mc_layer_pass/explain_leftovers.py --tag wnat_hagen
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
FIGURES = HERE / "figures"

FEATURE_COLS = [
    "area", "perimeter", "edge_mean", "aspect_ratio", "min_angle_deg",
    "radius_ratio", "n_boundary_edges", "deg_mean", "deg_max",
    "n_tri_neighbours", "size_ratio", "bdy_dist", "layer", "is_IE", "is_OE",
]


def default_total(meta):
    """Total routed under the deterministic default (corner) start."""
    from chilmesh import CHILmesh
    import quadmesh.identify_edges as ie
    from quadmesh.tri2quad import _quadmesh_plus_per_layer as run
    m = CHILmesh.read_from_fort14(meta["mesh"])
    tris = np.asarray(m.connectivity_list)[:, :3].astype(int)
    ie._START_INDEX_SELECTOR = None
    tr = {}
    run(m, tris, True, trace=tr)
    return set(int(x) for x in tr.get("routed", ())), tris


def _adjacency(conn):
    edge2tris = {}
    for i in range(conn.shape[0]):
        t = conn[i]
        for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            edge2tris.setdefault((int(min(e)), int(max(e))), []).append(i)
    adj = [[] for _ in range(conn.shape[0])]
    for inc in edge2tris.values():
        if len(inc) == 2:
            adj[inc[0]].append(inc[1])
            adj[inc[1]].append(inc[0])
    return adj


def clustering(mask, adj):
    """Mean fraction of a flagged tri's neighbours that are also flagged."""
    idx = np.where(mask)[0]
    if idx.size == 0:
        return 0.0, 0.0
    fr = []
    for i in idx:
        nb = adj[i]
        if nb:
            fr.append(np.mean([mask[j] for j in nb]))
    obs = float(np.mean(fr)) if fr else 0.0
    baseline = float(mask.mean())  # random expectation
    return obs, baseline


def subset_corr(df, sub_mask, label):
    y = df["pass_freq"].to_numpy()
    rows = []
    for col in FEATURE_COLS:
        x = df[col].to_numpy(dtype=float)
        m = sub_mask & np.isfinite(x) & np.isfinite(y)
        if m.sum() < 30 or np.nanstd(x[m]) == 0 or np.nanstd(y[m]) == 0:
            continue
        sr, sp = spearmanr(x[m], y[m])
        rows.append((col, sr, sp, int(m.sum())))
    out = pd.DataFrame(rows, columns=["feature", "spearman", "p", "n"])
    out["abs"] = out["spearman"].abs()
    out = out.sort_values("abs", ascending=False).drop(columns="abs")
    out.insert(0, "subset", label)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    tag = args.tag

    df = pd.read_csv(RESULTS / f"{tag}_merged.csv")
    meta = json.load(open(RESULTS / f"{tag}_meta.json"))
    runs = pd.read_csv(RESULTS / f"{tag}_per_run.csv")
    N = len(df)
    pf = df["pass_freq"].to_numpy()

    # 1. default vs random
    droute, conn = default_total(meta)
    default_n = len(droute)
    rand_n = runs["n_routed"].to_numpy()
    summary = {
        "tag": tag,
        "n_tris": int(N),
        "default_start_routed": int(default_n),
        "random_mean_routed": float(rand_n.mean()),
        "random_min_routed": int(rand_n.min()),
        "random_max_routed": int(rand_n.max()),
        "best_random_vs_default_delta": int(default_n - rand_n.min()),
        "n_never_routed": int((pf == 0).sum()),
        "n_swing_routed": int(((pf > 0) & (pf < 1)).sum()),
        "n_always_routed": int((pf >= 1.0).sum()),
        "n_frequent_ge50pct": int((pf >= 0.5).sum()),
        "pct_routed_that_are_structural": float(
            (pf >= 1.0).sum() / max(1, (pf > 0).sum())
        ),
    }

    # 2. motif breakdown
    groups = {
        "always (pf==1)": pf >= 1.0,
        "frequent (pf>=0.5)": pf >= 0.5,
        "swing (0<pf<1)": (pf > 0) & (pf < 1),
        "never (pf==0)": pf == 0,
        "all": np.ones(N, dtype=bool),
    }
    motif_rows = []
    for name, m in groups.items():
        sub = df[m]
        if len(sub) == 0:
            continue
        nb = sub["n_boundary_edges"].to_numpy()
        motif_rows.append({
            "group": name, "count": int(m.sum()),
            "frac_is_OE": float(sub["is_OE"].mean()),
            "frac_interior(nb==0)": float((nb == 0).mean()),
            "frac_nb==1": float((nb == 1).mean()),
            "frac_nb>=2": float((nb >= 2).mean()),
            "mean_layer": float(sub["layer"].mean()),
            "mean_radius_ratio": float(sub["radius_ratio"].mean()),
            "mean_aspect": float(sub["aspect_ratio"].replace([np.inf, -np.inf], np.nan).mean()),
            "mean_n_tri_nbrs": float(sub["n_tri_neighbours"].mean()),
        })
    motif = pd.DataFrame(motif_rows)
    motif.to_csv(RESULTS / f"{tag}_leftover_motifs.csv", index=False)

    # 3. de-confounded correlations
    oe_mask = df["is_OE"].to_numpy().astype(bool)
    int_mask = (df["n_boundary_edges"].to_numpy() == 0)
    sc = pd.concat([
        subset_corr(df, oe_mask, "OE-only"),
        subset_corr(df, int_mask, "interior-only"),
    ], ignore_index=True)
    sc.to_csv(RESULTS / f"{tag}_deconfounded_corr.csv", index=False)

    # 4. clustering
    adj = _adjacency(conn)
    always_mask = (pf >= 1.0)
    obs, base = clustering(always_mask, adj)
    summary["always_clustering_obs"] = obs
    summary["always_clustering_baseline"] = base
    summary["always_clustering_ratio"] = float(obs / base) if base > 0 else float("nan")

    with open(RESULTS / f"{tag}_explain_summary.json", "w") as fh:
        json.dump(summary, fh, indent=2)

    # figure: motif bar (boundary-edge composition per group)
    FIGURES.mkdir(parents=True, exist_ok=True)
    gnames = [r["group"] for r in motif_rows if r["group"] != "all"]
    interior = [r["frac_interior(nb==0)"] for r in motif_rows if r["group"] != "all"]
    nb1 = [r["frac_nb==1"] for r in motif_rows if r["group"] != "all"]
    nb2 = [r["frac_nb>=2"] for r in motif_rows if r["group"] != "all"]
    fig, ax = plt.subplots(figsize=(9, 5))
    xpos = np.arange(len(gnames))
    ax.bar(xpos, interior, label="interior (0 bdy edges)", color="#2c7fb8")
    ax.bar(xpos, nb1, bottom=interior, label="1 bdy edge", color="#7fcdbb")
    ax.bar(xpos, nb2, bottom=np.array(interior) + np.array(nb1), label=">=2 bdy edges", color="#edf8b1")
    ax.set_xticks(xpos); ax.set_xticklabels(gnames, rotation=20, ha="right")
    ax.set_ylabel("fraction of group"); ax.set_ylim(0, 1)
    ax.set_title(f"{tag}: boundary-edge composition by routing group")
    ax.legend(); fig.tight_layout()
    fig.savefig(FIGURES / f"{tag}_leftover_motif_bar.png", dpi=150); plt.close(fig)

    # figure: default vs random totals
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(rand_n, bins=25, color="steelblue", edgecolor="k", alpha=0.8, label="random starts")
    ax.axvline(default_n, color="r", ls="--", lw=2, label=f"default (corner) start = {default_n}")
    ax.axvline(rand_n.mean(), color="k", ls=":", label=f"random mean = {rand_n.mean():.0f}")
    ax.set_xlabel("total triangles routed per run"); ax.set_ylabel("count of runs")
    ax.set_title(f"{tag}: default-start vs random-start total routed")
    ax.legend(); fig.tight_layout()
    fig.savefig(FIGURES / f"{tag}_default_vs_random.png", dpi=150); plt.close(fig)

    print("=== explain summary ===")
    print(json.dumps(summary, indent=2))
    print("\n=== leftover motifs ===")
    print(motif.to_string(index=False))
    print("\n=== de-confounded correlations (top per subset) ===")
    print(sc.to_string(index=False))


if __name__ == "__main__":
    main()
