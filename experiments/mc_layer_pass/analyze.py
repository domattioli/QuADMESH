"""Analyze + visualize the MC layer-pass study.

Reads results/<tag>_merged.csv (per-triangle features + pass_freq),
results/<tag>_per_run.csv, results/<tag>_meta.json. Writes correlation tables to
results/ and figures to figures/.

Usage:
    python experiments/mc_layer_pass/analyze.py --tag wnat_hagen
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
from matplotlib.tri import Triangulation
from scipy.stats import spearmanr, pearsonr

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
FIGURES = HERE / "figures"

# Features to correlate against pass_freq (exclude ids / coords / the target).
FEATURE_COLS = [
    "area", "perimeter", "edge_min", "edge_max", "edge_mean", "aspect_ratio",
    "min_angle_deg", "max_angle_deg", "radius_ratio", "n_boundary_edges",
    "deg_mean", "deg_max", "deg_min", "layer", "is_IE", "is_OE",
    "n_tri_neighbours", "size_ratio", "bdy_dist",
]


def _load(tag):
    df = pd.read_csv(RESULTS / f"{tag}_merged.csv")
    runs = pd.read_csv(RESULTS / f"{tag}_per_run.csv")
    meta = json.load(open(RESULTS / f"{tag}_meta.json"))
    return df, runs, meta


def correlations(df, tag):
    """Spearman + Pearson of pass_freq vs each feature, written to csv."""
    y = df["pass_freq"].to_numpy()
    rows = []
    for col in FEATURE_COLS:
        if col not in df.columns:
            continue
        x = df[col].to_numpy(dtype=float)
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 10 or np.nanstd(x[mask]) == 0:
            rows.append((col, np.nan, np.nan, np.nan, np.nan))
            continue
        sr, sp = spearmanr(x[mask], y[mask])
        pr, pp = pearsonr(x[mask], y[mask])
        rows.append((col, sr, sp, pr, pp))
    cdf = pd.DataFrame(rows, columns=["feature", "spearman", "spearman_p", "pearson", "pearson_p"])
    cdf["abs_spearman"] = cdf["spearman"].abs()
    cdf = cdf.sort_values("abs_spearman", ascending=False).drop(columns="abs_spearman")
    cdf.to_csv(RESULTS / f"{tag}_correlations.csv", index=False)
    return cdf


def group_means(df, tag, n_runs):
    """Mean of each feature for never / swing / always-routed triangles."""
    pf = df["pass_freq"]
    grp = pd.Series(np.where(pf == 0, "never", np.where(pf >= 1.0, "always", "swing")),
                    index=df.index, name="group")
    cols = [c for c in FEATURE_COLS if c in df.columns]
    g = df[cols].replace([np.inf, -np.inf], np.nan).groupby(grp).mean()
    counts = grp.value_counts().rename("count")
    g = g.join(counts)
    g = g.reindex([x for x in ["never", "swing", "always"] if x in g.index])
    g.to_csv(RESULTS / f"{tag}_group_means.csv")
    return g


def by_layer(df, tag):
    """Pass-frequency aggregated by skeleton layer."""
    g = df.groupby("layer").agg(
        n_tris=("pass_freq", "size"),
        mean_pass_freq=("pass_freq", "mean"),
        frac_ever_routed=("pass_freq", lambda s: float((s > 0).mean())),
        frac_always_routed=("pass_freq", lambda s: float((s >= 1.0).mean())),
    ).reset_index()
    g.to_csv(RESULTS / f"{tag}_by_layer.csv", index=False)
    return g


def _mesh_geom(meta):
    from chilmesh import CHILmesh
    m = CHILmesh.read_from_fort14(meta["mesh"])
    conn = np.asarray(m.connectivity_list)[:, :3].astype(int)
    P = np.asarray(m.points)[:, :2].astype(float)
    return P[:, 0], P[:, 1], conn


def _tri_map(x, y, conn, facevals, title, cmap, out, vmin=None, vmax=None, label=""):
    triang = Triangulation(x, y, conn)
    fig, ax = plt.subplots(figsize=(11, 9))
    tpc = ax.tripcolor(triang, facecolors=np.asarray(facevals, dtype=float),
                       cmap=cmap, shading="flat", vmin=vmin, vmax=vmax)
    cb = fig.colorbar(tpc, ax=ax, shrink=0.8)
    cb.set_label(label or title)
    ax.set_aspect("equal")
    ax.set_title(title)
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)


def figures(df, runs, meta, tag):
    FIGURES.mkdir(parents=True, exist_ok=True)
    x, y, conn = _mesh_geom(meta)
    pf = df.sort_values("tri_idx")["pass_freq"].to_numpy() if "tri_idx" in df.columns else df["pass_freq"].to_numpy()
    # Ensure alignment with conn rows (df is tri_idx order already).
    pf = df["pass_freq"].to_numpy()

    # 1. pass-frequency map (KEY figure)
    _tri_map(x, y, conn, pf,
             f"{tag}: triangle pass-frequency (routed to leftover) over {meta['n_runs']} random-start runs",
             "inferno", FIGURES / f"{tag}_passfreq_map.png", vmin=0, vmax=1,
             label="pass frequency (fraction of runs routed)")

    # 2. quality map
    _tri_map(x, y, conn, df["radius_ratio"].to_numpy(),
             f"{tag}: triangle quality (radius ratio)", "viridis",
             FIGURES / f"{tag}_quality_map.png", vmin=0, vmax=1, label="radius ratio")

    # 3. area map (log10)
    la = np.log10(np.clip(df["area"].to_numpy(), 1e-12, None))
    _tri_map(x, y, conn, la, f"{tag}: triangle area (log10)", "viridis",
             FIGURES / f"{tag}_area_map.png", label="log10(area)")

    # 4. swing map: never (light), swing (orange), always (red)
    pfv = df["pass_freq"].to_numpy()
    cat = np.where(pfv == 0, 0.0, np.where(pfv >= 1.0, 2.0, 1.0))
    from matplotlib.colors import ListedColormap, BoundaryNorm
    cmap4 = ListedColormap(["#dddddd", "#ff8c00", "#d00000"])
    triang = Triangulation(x, y, conn)
    fig, ax = plt.subplots(figsize=(11, 9))
    tpc = ax.tripcolor(triang, facecolors=cat, cmap=cmap4,
                       norm=BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap4.N), shading="flat")
    cb = fig.colorbar(tpc, ax=ax, shrink=0.8, ticks=[0, 1, 2])
    cb.ax.set_yticklabels(["never routed", "swing (start-dependent)", "always routed"])
    ax.set_aspect("equal")
    ax.set_title(f"{tag}: structural (always) vs start-dependent (swing) routed triangles")
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    fig.tight_layout(); fig.savefig(FIGURES / f"{tag}_swing_map.png", dpi=150); plt.close(fig)

    # 5. per-run histogram
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(runs["n_routed"], bins=30, color="steelblue", edgecolor="k", alpha=0.8)
    ax.axvline(runs["n_routed"].mean(), color="r", ls="--", label=f"mean={runs['n_routed'].mean():.1f}")
    ax.set_xlabel("triangles routed per run"); ax.set_ylabel("count of runs")
    ax.set_title(f"{tag}: distribution of total routed triangles across {meta['n_runs']} random starts")
    ax.legend(); fig.tight_layout(); fig.savefig(FIGURES / f"{tag}_hist_perrun.png", dpi=150); plt.close(fig)

    # 6. correlation bar
    cdf = pd.read_csv(RESULTS / f"{tag}_correlations.csv").dropna(subset=["spearman"])
    cdf = cdf.iloc[::-1]
    fig, ax = plt.subplots(figsize=(8, 7))
    colors = ["#d00000" if v > 0 else "#0066cc" for v in cdf["spearman"]]
    ax.barh(cdf["feature"], cdf["spearman"], color=colors)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("Spearman correlation with pass_freq")
    ax.set_title(f"{tag}: feature correlation with triangle pass-frequency")
    fig.tight_layout(); fig.savefig(FIGURES / f"{tag}_corr_bar.png", dpi=150); plt.close(fig)

    # 7. scatter panel
    panel = ["radius_ratio", "aspect_ratio", "area", "deg_max", "bdy_dist", "min_angle_deg"]
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    for ax, col in zip(axes.ravel(), panel):
        xv = df[col].to_numpy(dtype=float)
        if col in ("area", "aspect_ratio"):
            xv = np.log10(np.clip(xv, 1e-12, None)); xlab = f"log10({col})"
        else:
            xlab = col
        m = np.isfinite(xv)
        ax.hexbin(xv[m], pf[m], gridsize=40, cmap="magma", bins="log", mincnt=1)
        ax.set_xlabel(xlab); ax.set_ylabel("pass_freq")
        ax.set_title(f"pass_freq vs {col}")
    fig.suptitle(f"{tag}: pass-frequency vs triangle features (hexbin, log count)")
    fig.tight_layout(); fig.savefig(FIGURES / f"{tag}_scatter_panel.png", dpi=150); plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    df, runs, meta = _load(args.tag)
    cdf = correlations(df, args.tag)
    gm = group_means(df, args.tag, meta["n_runs"])
    bl = by_layer(df, args.tag)
    figures(df, runs, meta, args.tag)
    print("=== correlations (sorted by |spearman|) ===")
    print(cdf.to_string(index=False))
    print("\n=== group means (never / swing / always routed) ===")
    print(gm.to_string())
    print("\n=== by layer ===")
    print(bl.to_string(index=False))
    print(f"\nfigures written to {FIGURES}")


if __name__ == "__main__":
    main()
