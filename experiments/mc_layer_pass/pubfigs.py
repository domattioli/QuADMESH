"""Publication-quality refinements of two MC layer-pass figures:
  pub_default_vs_random : start-vertex sensitivity of the leftover count.
  pub_drivers           : feature correlations with triangle pass-frequency.

Usage: python experiments/mc_layer_pass/pubfigs.py --tag wnat_hagen
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
from scipy.stats import gaussian_kde

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
FIGURES = HERE / "figures"

plt.rcParams.update({
    "savefig.dpi": 300, "figure.dpi": 150, "font.family": "DejaVu Sans",
    "font.size": 12, "axes.titlesize": 15, "axes.labelsize": 13,
    "xtick.labelsize": 11, "ytick.labelsize": 11, "legend.fontsize": 11,
    "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.9,
})

LABELS = {
    "is_OE": "outer-edge tri in layer (OE)",
    "is_IE": "inner-edge tri in layer (IE)",
    "size_ratio": "local size ratio (area / nbr area)",
    "deg_min": "min vertex degree", "deg_mean": "mean vertex degree",
    "deg_max": "max vertex degree", "n_tri_neighbours": "# triangle neighbours",
    "n_boundary_edges": "# boundary edges", "layer": "skeleton layer index",
    "area": "triangle area", "edge_min": "min edge length",
    "edge_max": "max edge length", "edge_mean": "mean edge length",
    "perimeter": "perimeter", "aspect_ratio": "aspect ratio",
    "min_angle_deg": "min interior angle", "max_angle_deg": "max interior angle",
    "radius_ratio": "shape quality (radius ratio)", "bdy_dist": "distance to boundary",
    "mean_valence": "mean vertex valence", "max_valence": "max vertex valence",
    "min_valence": "min vertex valence",
    "valence_irreg_mean": "mean valence irregularity",
    "valence_irreg_max": "max valence irregularity",
    "n_irregular_verts": "# irregular vertices",
    "flow_disorder": "local flow disorder",
    "flow_misalign": "flow misalignment vs nbrs",
    "log_size_gradient": "log size gradient",
    "layer_flow_misalign": "layer-flow misalignment",
}

RED = "#c1272d"
BLUE = "#2166ac"
LBLUE = "#9ecae1"
DBLUE = "#08519c"


def fig_default_vs_random(tag, per_run, meta, summary):
    rand = per_run["n_routed"].to_numpy(dtype=float)
    n_tris = int(meta["n_tris"])
    n_runs = int(meta["n_runs"])
    default_n = int(summary["default_start_routed"])
    mu, sd = rand.mean(), rand.std()

    fig, ax = plt.subplots(figsize=(8.6, 5.3))
    lo, hi = min(rand.min(), default_n), max(rand.max(), default_n)
    pad = max(2.0, 0.05 * (hi - lo + 1))
    bins = np.linspace(lo - pad, hi + pad, 24)
    ax.hist(rand, bins=bins, color=LBLUE, edgecolor="white", alpha=0.9,
            density=True, label=f"random start ({n_runs} runs)")
    if sd > 0:
        kde = gaussian_kde(rand)
        xs = np.linspace(lo - pad, hi + pad, 400)
        ax.plot(xs, kde(xs), color=DBLUE, lw=2.0)
        ax.axvspan(mu - sd, mu + sd, color=LBLUE, alpha=0.18, label="random mean ± 1 sd")
    ax.axvline(mu, color=DBLUE, lw=1.4, ls=":")
    ax.axvline(default_n, color=RED, lw=2.6, label="default (corner) start")

    delta = mu - default_n
    ax.annotate(
        f"default = {default_n}\nrandom mean = {mu:.0f} ± {sd:.0f}\n"
        f"gap = {delta:+.0f} tris ({delta / n_tris * 100:+.2f}% of mesh)",
        xy=(default_n, ax.get_ylim()[1] * 0.92), xytext=(0.03, 0.78),
        textcoords="axes fraction", fontsize=10.5,
        bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="0.7"),
    )

    def to_pct(x):
        return x / n_tris * 100.0

    def from_pct(p):
        return p / 100.0 * n_tris

    secax = ax.secondary_xaxis("top", functions=(to_pct, from_pct))
    secax.set_xlabel("leftover triangles as % of all triangles")

    ax.set_xlabel("triangles passed downstream per run")
    ax.set_ylabel("probability density")
    ax.set_title("Start-vertex choice barely changes the leftover count",
                 loc="left", fontweight="bold", fontsize=13)
    ax.margins(x=0.01)
    ax.grid(axis="y", color="0.85", lw=0.7)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    out = FIGURES / f"{tag}_pub_default_vs_random.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_drivers(tag, meta):
    cdf = pd.read_csv(RESULTS / f"{tag}_correlations.csv").dropna(subset=["spearman"])
    cdf["label"] = cdf["feature"].map(lambda f: LABELS.get(f, f))
    cdf = cdf.sort_values("spearman")
    vals = cdf["spearman"].to_numpy()
    labels = cdf["label"].tolist()
    colors = [RED if v > 0 else BLUE for v in vals]

    fig, ax = plt.subplots(figsize=(9.5, 9.2))
    ax.axvspan(-0.1, 0.1, color="0.6", alpha=0.10, zorder=0,
               label="|ρ| < 0.1  (negligible effect)")
    ax.barh(labels, vals, color=colors, edgecolor="white", height=0.74, zorder=3)
    ax.axvline(0, color="k", lw=0.9, zorder=4)
    xmax = max(0.16, float(np.abs(vals).max()) * 1.30)
    ax.set_xlim(-xmax, xmax)
    ax.set_ylim(-0.7, len(vals) - 0.3)
    for y, v in enumerate(vals):
        ax.text(v + (0.004 if v >= 0 else -0.004), y, f"{v:+.3f}",
                va="center", ha="left" if v >= 0 else "right",
                fontsize=8.5, color="0.25", zorder=5)
    ax.set_xlabel("Spearman ρ with triangle pass-frequency\n"
                  "red = passed downstream more often   ·   blue = less often")
    ax.set_title("No single feature dominates the leftover triangles\n"
                 "(weak, multifactorial drivers)",
                 loc="left", fontweight="bold", fontsize=13)
    ax.legend(loc="lower right", frameon=False, fontsize=10)
    ax.grid(axis="x", color="0.88", lw=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", labelsize=10)
    fig.tight_layout()
    out = FIGURES / f"{tag}_pub_drivers.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    FIGURES.mkdir(parents=True, exist_ok=True)
    per_run = pd.read_csv(RESULTS / f"{args.tag}_per_run.csv")
    meta = json.load(open(RESULTS / f"{args.tag}_meta.json"))
    summary = json.load(open(RESULTS / f"{args.tag}_explain_summary.json"))
    a = fig_default_vs_random(args.tag, per_run, meta, summary)
    b = fig_drivers(args.tag, meta)
    print("wrote", a)
    print("wrote", b)


if __name__ == "__main__":
    main()
