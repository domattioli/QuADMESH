#!/usr/bin/env python
"""Mesh-rendering CLI script.

Renders quad/tri meshes from fort.14 files or NPZ snapshots.
Supports global views and windowed zoom regions.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

# Set matplotlib backend BEFORE importing pyplot
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from chilmesh import CHILmesh
from quadmesh.pipeline import run_pipeline


def is_quad(row):
    """Check if a row is a genuine quad (not a padded tri).

    Padded tri: 4th index == 3rd, OR 4th < 0, OR has duplicates.
    """
    row = np.asarray(row)
    if len(row) != 4:
        return False
    # Last vertex == third, or negative
    if row[3] == row[2] or row[3] < 0:
        return False
    # Any duplicates in the row
    if len(set(row)) != 4:
        return False
    return True


def count_elements(connectivity_list):
    """Count quads vs tris and compute bbox."""
    conn = np.asarray(connectivity_list)
    n_quads = sum(1 for row in conn if is_quad(row))
    n_tris = len(conn) - n_quads
    return n_quads, n_tris


def compute_bbox(points):
    """Compute bounding box from points."""
    if len(points) == 0:
        return 0, 0, 0, 0
    return (
        float(np.min(points[:, 0])),
        float(np.max(points[:, 0])),
        float(np.min(points[:, 1])),
        float(np.max(points[:, 1])),
    )


def filter_elements_by_centroid(connectivity_list, points, xmin, xmax, ymin, ymax):
    """Return indices of elements whose centroid is in bbox.

    Returns:
        list of (row_index, row) tuples for elements in bbox
    """
    conn = np.asarray(connectivity_list)
    points_arr = np.asarray(points)

    result = []
    for idx, row in enumerate(conn):
        # Compute centroid
        verts = row[row >= 0]  # Exclude -1 padding in tris
        if len(verts) == 0:
            continue
        centroid = points_arr[verts].mean(axis=0)
        if xmin <= centroid[0] <= xmax and ymin <= centroid[1] <= ymax:
            result.append((idx, row))
    return result


def build_edges_from_elements(elements_with_rows, points):
    """Build edge segments for rendering.

    Args:
        elements_with_rows: list of (idx, row) tuples
        points: (N, >=2) array of node coordinates (lon, lat, [z])

    Returns:
        list of (start_pt, end_pt) tuples for LineCollection
    """
    edges = []
    points_arr = np.asarray(points)
    # Use only (x, y) for rendering
    xy = points_arr[:, :2]

    for idx, row in elements_with_rows:
        row = np.asarray(row)
        is_q = is_quad(row)

        if is_q:
            # Quad: 4 edges
            v = row
            edges.append((xy[v[0]], xy[v[1]]))
            edges.append((xy[v[1]], xy[v[2]]))
            edges.append((xy[v[2]], xy[v[3]]))
            edges.append((xy[v[3]], xy[v[0]]))
        else:
            # Tri: 3 edges (filter out -1)
            v = row[row >= 0]
            edges.append((xy[v[0]], xy[v[1]]))
            edges.append((xy[v[1]], xy[v[2]]))
            edges.append((xy[v[2]], xy[v[0]]))

    return edges


def render_mesh(
    points,
    connectivity_list,
    out_path: Path,
    title: str,
    view_name: str = "global",
    n_elems_shown: int | None = None,
    xmin: float | None = None,
    xmax: float | None = None,
    ymin: float | None = None,
    ymax: float | None = None,
):
    """Render mesh to PNG.

    Args:
        points: (N, >=2) array
        connectivity_list: (M, 4) int array
        out_path: Path to save PNG
        title: Plot title
        view_name: "global" or zoom name
        n_elems_shown: Number of elements shown (for title)
        xmin, xmax, ymin, ymax: Bbox limits (for tight rendering)
    """
    conn = np.asarray(connectivity_list)

    # Compute element composition
    n_quads, n_tris = count_elements(conn)

    # Build elements list (all if no bbox, or filtered)
    if xmin is not None and xmax is not None and ymin is not None and ymax is not None:
        elements = filter_elements_by_centroid(conn, points, xmin, xmax, ymin, ymax)
    else:
        elements = [(i, row) for i, row in enumerate(conn)]

    if len(elements) == 0:
        print(f"ZOOM {view_name}: 0 elements in bbox")
        # Create empty plot
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.text(0.5, 0.5, "0 elements in region", ha="center", va="center")
        ax.set_title(title)
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return

    n_elems_shown = len(elements)

    # Separate quads and tris for coloring
    quad_edges = []
    tri_edges = []
    points_arr = np.asarray(points)
    xy = points_arr[:, :2]  # Use only (x, y) for rendering

    for idx, row in elements:
        row = np.asarray(row)
        is_q = is_quad(row)

        if is_q:
            # Quad: 4 edges
            v = row
            quad_edges.append((xy[v[0]], xy[v[1]]))
            quad_edges.append((xy[v[1]], xy[v[2]]))
            quad_edges.append((xy[v[2]], xy[v[3]]))
            quad_edges.append((xy[v[3]], xy[v[0]]))
        else:
            # Tri: 3 edges
            v = row[row >= 0]
            tri_edges.append((xy[v[0]], xy[v[1]]))
            tri_edges.append((xy[v[1]], xy[v[2]]))
            tri_edges.append((xy[v[2]], xy[v[0]]))

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))

    # Draw edges
    if quad_edges:
        lc_quads = LineCollection(quad_edges, linewidths=0.15, colors="#1f3b5c", alpha=0.8)
        ax.add_collection(lc_quads)

    if tri_edges:
        lc_tris = LineCollection(tri_edges, linewidths=0.15, colors="#c0392b", alpha=0.8)
        ax.add_collection(lc_tris)

    # Set limits
    if xmin is not None and xmax is not None and ymin is not None and ymax is not None:
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
    else:
        ax.autoscale()

    ax.set_aspect("equal")

    # Title
    ax.set_title(f"quadmesh+ {title} — {view_name} ({n_elems_shown} elems)", fontsize=12)

    # Legend
    if quad_edges and tri_edges:
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], color="#1f3b5c", linewidth=2, label="quads"),
            Line2D([0], [0], color="#c0392b", linewidth=2, label="tris"),
        ]
        ax.legend(handles=legend_elements, loc="upper right")

    # Save
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def load_mesh_from_fort14(path: Path) -> CHILmesh:
    """Load mesh from fort.14 file."""
    return CHILmesh.read_from_fort14(str(path))


def load_mesh_from_npz(path: Path) -> CHILmesh:
    """Load mesh from NPZ snapshot."""
    data = np.load(path)
    points = data["points"]
    conn = data["conn"]
    return CHILmesh(points=points, connectivity=conn, compute_layers=False)


def save_mesh_to_npz(mesh: CHILmesh, path: Path):
    """Save mesh to NPZ snapshot."""
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, points=mesh.points, conn=mesh.connectivity_list)


def parse_zoom_window(zoom_str: str) -> tuple[str, float, float, float, float]:
    """Parse --zoom NAME:xmin,xmax,ymin,ymax.

    Returns:
        (name, xmin, xmax, ymin, ymax)

    Raises:
        ValueError if format is invalid
    """
    parts = zoom_str.split(":")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid zoom format: {zoom_str}. Expected NAME:xmin,xmax,ymin,ymax"
        )

    name = parts[0]
    coords_str = parts[1]

    try:
        coords = [float(x.strip()) for x in coords_str.split(",")]
    except ValueError as e:
        raise ValueError(
            f"Invalid zoom coordinates: {coords_str}. Expected xmin,xmax,ymin,ymax"
        ) from e

    if len(coords) != 4:
        raise ValueError(
            f"Invalid zoom coordinates: {coords_str}. Expected 4 values, got {len(coords)}"
        )

    xmin, xmax, ymin, ymax = coords
    if xmin >= xmax or ymin >= ymax:
        raise ValueError(
            f"Invalid zoom window: xmin={xmin} >= xmax={xmax} or ymin={ymin} >= ymax={ymax}"
        )

    return name, xmin, xmax, ymin, ymax


def main():
    parser = argparse.ArgumentParser(
        description="Render quad/tri meshes from fort.14 or NPZ snapshots"
    )
    parser.add_argument("--mesh", type=str, help="Input fort.14 mesh file")
    parser.add_argument(
        "--run",
        action="store_true",
        help="Run quadmesh+ pipeline on input mesh",
    )
    parser.add_argument(
        "--no-post",
        action="store_true",
        help="If --run, skip post-processing",
    )
    parser.add_argument(
        "--save-npz",
        type=str,
        help="Save processed mesh to NPZ file",
    )
    parser.add_argument(
        "--in-npz",
        type=str,
        help="Load mesh from prior --save-npz (fast path, no pipeline)",
    )
    parser.add_argument(
        "--raw-input",
        action="store_true",
        help="Render input triangular mesh directly (no pipeline)",
    )
    parser.add_argument(
        "--out-dir",
        type=str,
        default="output/render",
        help="Output directory for PNG files (default: output/render)",
    )
    parser.add_argument(
        "--tag",
        type=str,
        default="mesh",
        help="Short label for titles/filenames (default: mesh)",
    )
    parser.add_argument(
        "--global",
        action="store_true",
        dest="emit_global",
        help="Emit global view PNG",
    )
    parser.add_argument(
        "--zoom",
        type=str,
        action="append",
        help="Repeatable zoom window: NAME:xmin,xmax,ymin,ymax",
    )

    args = parser.parse_args()

    # Validation
    if args.in_npz and args.run:
        parser.error("--in-npz and --run are mutually exclusive")

    if not args.in_npz and not args.run and not args.raw_input:
        parser.error("Must specify --run, --raw-input, or --in-npz")

    if args.in_npz and not args.mesh and not args.raw_input:
        # NPZ path required
        pass
    elif args.mesh is None:
        parser.error("--mesh is required unless --in-npz is used")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load mesh
    if args.in_npz:
        mesh = load_mesh_from_npz(Path(args.in_npz))
    elif args.mesh:
        mesh = load_mesh_from_fort14(Path(args.mesh))

        if args.run:
            # Run pipeline
            do_post = not args.no_post
            mesh = run_pipeline(mesh, do_post_process=do_post, method="quadmesh+")

            # Save NPZ if requested
            if args.save_npz:
                save_mesh_to_npz(mesh, Path(args.save_npz))
        elif not args.raw_input:
            # Default: render input as-is
            pass
    else:
        parser.error("No mesh source specified")

    # Print bbox and counts
    xmin, xmax, ymin, ymax = compute_bbox(mesh.points)
    n_quads, n_tris = count_elements(mesh.connectivity_list)
    n_nodes = len(mesh.points)
    n_elems = len(mesh.connectivity_list)

    print(f"{xmin} {xmax} {ymin} {ymax}")
    print(f"{n_nodes} nodes")
    print(f"{n_elems} elems")
    print(f"{n_quads} quads")
    print(f"{n_tris} tris")

    # Render global if requested
    if args.emit_global:
        out_path = out_dir / f"{args.tag}_global.png"
        render_mesh(
            mesh.points,
            mesh.connectivity_list,
            out_path,
            args.tag,
            view_name="global",
        )

    # Render zoom windows if requested
    if args.zoom:
        for zoom_spec in args.zoom:
            try:
                name, xmin_z, xmax_z, ymin_z, ymax_z = parse_zoom_window(zoom_spec)
            except ValueError as e:
                print(f"Error parsing zoom: {e}", file=sys.stderr)
                sys.exit(1)

            out_path = out_dir / f"{args.tag}_{name}.png"
            render_mesh(
                mesh.points,
                mesh.connectivity_list,
                out_path,
                args.tag,
                view_name=name,
                xmin=xmin_z,
                xmax=xmax_z,
                ymin=ymin_z,
                ymax=ymax_z,
            )


if __name__ == "__main__":
    main()
