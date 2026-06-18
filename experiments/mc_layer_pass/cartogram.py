"""Size-controlled cartograms of triangle pass-frequency.

The plain geographic map lets large elements (coarse open ocean) dominate the
canvas while small refined elements (coastlines) vanish. These two views
equalize visual weight per element, analogous to an electoral cartogram:

  cartogram_noncontig : each triangle redrawn at EQUAL area about its own
    centroid, kept in geographic position. Large tris shrink, small tris grow.
  cartogram_unrolled  : skeleton layers unrolled into equal-height bands; within
    a band each element is an equal-width cell ordered by angular position. Pure
    mesh-intrinsic coordinates, zero geographic-size bias.

Usage: python experiments/mc_layer_pass/cartogram.py --tag wnat_hagen
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

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
FIGURES = HERE / "figures"
CMAP = "inferno"


def _load(tag):
    df = pd.read_csv(RESULTS / f"{tag}_merged.csv")
    meta = json.load(open(RESULTS / f"{tag}_meta.json"))
    from chilmesh import CHILmesh
    m = CHILmesh.read_from_fort14(meta["mesh"])
    conn = np.asarray(m.connectivity_list)[:, :3].astype(int)
    P = np.asarray(m.points)[:, :2].astype(float)
    return df, meta, conn, P


def fig_noncontig(tag, df, meta, conn, P):
    pf = df["pass_freq"].to_numpy()
    area = df["area"].to_numpy()
    verts = P[conn]                                  # (N,3,2)
    cent = verts.mean(axis=1, keepdims=True)         # (N,1,2)
    target = float(np.median(area))                  # equalize to median area
    scale = np.sqrt(target / np.clip(area, 1e-12, None))
    scale = np.clip(scale, 0.15, 8.0)[:, None, None]
    scaled = cent + (verts - cent) * scale           # (N,3,2)

    order = np.argsort(pf)                            # high pass_freq drawn last
    fig, (axg, axc) = plt.subplots(1, 2, figsize=(18, 8.2))

    pcg = PolyCollection(verts[order], array=pf[order], cmap=CMAP, edgecolors="none")
    pcg.set_clim(0, 1)
    axg.add_collection(pcg)
    axg.autoscale_view()
    axg.set_aspect("equal")
    axg.set_title("Geographic (area-weighted): large elements dominate")
    axg.set_xlabel("longitude"); axg.set_ylabel("latitude")

    pcc = PolyCollection(scaled[order], array=pf[order], cmap=CMAP,
                         edgecolors="none", alpha=0.9)
    pcc.set_clim(0, 1)
    axc.add_collection(pcc)
    axc.autoscale_view()
    axc.set_aspect("equal")
    axc.set_title("Non-contiguous cartogram: every element at equal area")
    axc.set_xlabel("longitude"); axc.set_ylabel("latitude")

    cb = fig.colorbar(pcc, ax=[axg, axc], shrink=0.7)
    cb.set_label("pass frequency (fraction of runs routed downstream)")
    fig.suptitle(f"{tag}: triangle pass-frequency — geographic vs size-controlled cartogram",
                 fontsize=14, fontweight="bold")
    out = FIGURES / f"{tag}_cartogram_noncontig.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def fig_unrolled(tag, df, meta, conn, P):
    pf = df["pass_freq"].to_numpy()
    cx = df["cx"].to_numpy(); cy = df["cy"].to_numpy()
    layer = df["layer"].to_numpy().astype(int)
    cxc, cyc = float(cx.mean()), float(cy.mean())
    angle = np.arctan2(cy - cyc, cx - cxc)

    layers = sorted([l for l in np.unique(layer) if l >= 0])
    n_bands = len(layers)
    fig, ax = plt.subplots(figsize=(13, 8.5))
    band_h = 1.0
    yticks, ylabels = [], []
    last_mesh = None
    for i, li in enumerate(layers):
        sel = np.where(layer == li)[0]
        order = sel[np.argsort(angle[sel])]
        row = pf[order][None, :]                       # (1, n_i)
        y0 = (n_bands - 1 - i) * band_h                # layer 0 at top
        last_mesh = ax.imshow(row, extent=[0, 1, y0, y0 + band_h * 0.92],
                              aspect="auto", cmap=CMAP, vmin=0, vmax=1,
                              interpolation="nearest")
        yticks.append(y0 + band_h * 0.46)
        ylabels.append(f"L{li} (n={sel.size})")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, n_bands * band_h)
    ax.set_yticks(yticks)
    ax.set_yticklabels(ylabels, fontsize=7)
    ax.set_xlabel("angular position around domain  (−π → π)")
    ax.set_title(f"{tag}: pass-frequency unrolled by skeleton layer\n"
                 "(equal band height per layer; each cell = one element, equal width)",
                 fontsize=13, fontweight="bold", loc="left")
    cb = fig.colorbar(last_mesh, ax=ax, shrink=0.8)
    cb.set_label("pass frequency")
    fig.tight_layout()
    out = FIGURES / f"{tag}_cartogram_unrolled.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()
    FIGURES.mkdir(parents=True, exist_ok=True)
    df, meta, conn, P = _load(args.tag)
    a = fig_noncontig(args.tag, df, meta, conn, P)
    b = fig_unrolled(args.tag, df, meta, conn, P)
    print("wrote", a)
    print("wrote", b)


if __name__ == "__main__":
    main()
