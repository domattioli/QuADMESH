"""Focus+context ("hybrid") cartograms: compress elements whose pass-frequency
is near a reference statistic (mean / median / mode / max / min), expanding the
rest. Each element's allocated visual width (unrolled) or drawn size (geographic)
is proportional to |pass_freq - reference| + EPS, so the bulk of elements near
the reference collapses to slivers and the deviating (interesting) elements
dominate.

Usage:
  python experiments/mc_layer_pass/cartogram_hybrid.py --tag wnat_hagen --reference mode
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
from matplotlib.collections import PolyCollection
from matplotlib import cm
from matplotlib.colors import Normalize

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
FIGURES = HERE / "figures"
CMAP = "inferno"
EPS = 0.004


def _reference(pf, name):
    if name == "mean":
        return float(np.mean(pf))
    if name == "median":
        return float(np.median(pf))
    if name == "max":
        return float(np.max(pf))
    if name == "min":
        return float(np.min(pf))
    if name == "mode":
        vals, counts = np.unique(np.round(pf, 6), return_counts=True)
        return float(vals[int(np.argmax(counts))])
    raise ValueError(name)


def _load(tag):
    df = pd.read_csv(RESULTS / f"{tag}_merged.csv")
    meta = json.load(open(RESULTS / f"{tag}_meta.json"))
    from chilmesh import CHILmesh
    m = CHILmesh.read_from_fort14(meta["mesh"])
    conn = np.asarray(m.connectivity_list)[:, :3].astype(int)
    P = np.asarray(m.points)[:, :2].astype(float)
    return df, meta, conn, P


def unrolled_hybrid(tag, df, ref, refname):
    pf = df["pass_freq"].to_numpy()
    cx = df["cx"].to_numpy(); cy = df["cy"].to_numpy()
    layer = df["layer"].to_numpy().astype(int)
    ang = np.arctan2(cy - cy.mean(), cx - cx.mean())
    w_all = EPS + np.abs(pf - ref)
    layers = sorted([l for l in np.unique(layer) if l >= 0])
    nb = len(layers)
    bh = 1.0
    polys, colors, yticks, ylabels = [], [], [], []
    for i, li in enumerate(layers):
        sel = np.where(layer == li)[0]
        sel = sel[np.argsort(ang[sel])]
        w = w_all[sel]
        x = np.concatenate([[0.0], np.cumsum(w)])
        if x[-1] <= 0:
            continue
        x = x / x[-1]
        y0 = (nb - 1 - i) * bh
        y1 = y0 + bh * 0.92
        for j in range(sel.size):
            polys.append([[x[j], y0], [x[j + 1], y0], [x[j + 1], y1], [x[j], y1]])
            colors.append(pf[sel[j]])
        yticks.append(y0 + bh * 0.46)
        ylabels.append(f"L{li} (n={sel.size})")
    pc = PolyCollection(polys, array=np.array(colors), cmap=CMAP, edgecolors="none")
    pc.set_clim(0, 1)
    fig, ax = plt.subplots(figsize=(13, 8.5))
    ax.add_collection(pc)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, nb * bh)
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=7)
    ax.set_xlabel(f"element width ∝ |pass_freq − {refname}|  (elements near {refname} compressed)")
    ax.set_title(f"{tag}: hybrid unrolled cartogram — compress near {refname} ({ref:.3f})\n"
                 "wide cells = elements far from the reference (the interesting ones)",
                 fontsize=12, fontweight="bold", loc="left")
    sm = cm.ScalarMappable(norm=Normalize(0, 1), cmap=CMAP)
    cb = fig.colorbar(sm, ax=ax, shrink=0.8)
    cb.set_label("pass frequency")
    fig.tight_layout()
    out = FIGURES / f"{tag}_hybrid_unrolled_{refname}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def geographic_hybrid(tag, df, conn, P, ref, refname):
    pf = df["pass_freq"].to_numpy()
    area = df["area"].to_numpy()
    verts = P[conn]
    cent = verts.mean(axis=1, keepdims=True)
    w = EPS + np.abs(pf - ref)
    target = float(np.median(area))
    base = np.sqrt(target / np.clip(area, 1e-12, None))
    wn = w / (np.median(w) + 1e-9)
    scale = np.clip(base * np.sqrt(wn), 0.05, 10.0)[:, None, None]
    scaled = cent + (verts - cent) * scale
    order = np.argsort(pf)
    fig, ax = plt.subplots(figsize=(10, 8.5))
    pc = PolyCollection(scaled[order], array=pf[order], cmap=CMAP,
                        edgecolors="none", alpha=0.9)
    pc.set_clim(0, 1)
    ax.add_collection(pc)
    ax.autoscale_view()
    ax.set_aspect("equal")
    ax.set_title(f"{tag}: hybrid geographic cartogram — size ∝ |pass_freq − {refname}|\n"
                 f"(elements near {refname}={ref:.3f} compressed)",
                 fontsize=12, fontweight="bold")
    ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
    cb = fig.colorbar(pc, ax=ax, shrink=0.8)
    cb.set_label("pass frequency")
    fig.tight_layout()
    out = FIGURES / f"{tag}_hybrid_geographic_{refname}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--reference", default="mode",
                    choices=["mean", "median", "mode", "max", "min"])
    args = ap.parse_args()
    FIGURES.mkdir(parents=True, exist_ok=True)
    df, meta, conn, P = _load(args.tag)
    pf = df["pass_freq"].to_numpy()
    ref = _reference(pf, args.reference)
    print(f"reference {args.reference} = {ref:.4f}")
    print("wrote", unrolled_hybrid(args.tag, df, ref, args.reference))
    print("wrote", geographic_hybrid(args.tag, df, conn, P, ref, args.reference))


if __name__ == "__main__":
    main()
