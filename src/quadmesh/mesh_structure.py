"""Unified entrypoint for mesh structure definitions (QuADMesh issue #55).

This module provides a single selectable entrypoint distinguishing three
related-but-distinct mesh structures:

- **layers**: outer/inner edge & vertex sets per layer decomposition ring,
  computed by CHILmesh and read from ``domain.layers``. Layer 0 = outermost
  (boundary), layer N-1 = innermost core. See ``LayerState`` in
  ``_layer_state.py`` for the mutable working copy the faithful sweep uses.

- **skeleton**: morphological skeleton via CHILmesh layer peeling. Identical
  layer data as ``layers`` mode but exposes ``skeleton_core`` / ``skeleton_core_verts``
  properties for the innermost (irreducible) layer. Per operator definition
  (issue #55, 2026-05-30): peel outermost elements iteratively inward until the
  irreducible core remains — same algorithm CHILmesh._skeletonize() implements.

- **medial_axis**: Voronoi-of-boundary interior ridges, deterministic approximation;
  fidelity scales with boundary sample density. Returns ``nodes`` / ``edges`` arrays.

Issue ref: domattioli/QuADMesh#55
Spec ref: specs/055-skeletonization-rename/spec.md
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple

from ._layer_state import LayerState

VALID_KINDS = ("layers", "skeleton", "medial_axis")


@dataclass
class MeshStructure:
    """Selectable mesh structure with kind, layer count, and optional layer state.

    For graph kinds (medial_axis), nodes and edges are populated instead of layers.
    For skeleton kind, use skeleton_core / skeleton_core_verts to access the innermost
    irreducible layer.
    """

    kind: str
    n_layers: int
    layers: Optional[LayerState] = None
    nodes: Optional["np.ndarray"] = None
    edges: Optional["np.ndarray"] = None

    @property
    def skeleton_core(self) -> Tuple["np.ndarray", "np.ndarray"]:
        """Elements of the innermost layer (morphological skeleton core).

        Layer ordering: 0 = outermost (first peeled), N-1 = innermost core.
        Returns (OE[-1], IE[-1]) — outer/inner edge elements of the irreducible core.
        Only valid when kind='skeleton'.
        """
        if self.kind != "skeleton":
            raise AttributeError("skeleton_core only available for kind='skeleton'")
        if self.layers is None or self.layers.n_layers == 0:
            return (np.empty(0, dtype=int), np.empty(0, dtype=int))
        return (self.layers.OE[-1], self.layers.IE[-1])

    @property
    def skeleton_core_verts(self) -> Tuple["np.ndarray", "np.ndarray"]:
        """Vertices of the innermost layer (morphological skeleton core).

        Returns (OV[-1], IV[-1]) — outer/inner vertices of the irreducible core.
        Only valid when kind='skeleton'.
        """
        if self.kind != "skeleton":
            raise AttributeError("skeleton_core_verts only available for kind='skeleton'")
        if self.layers is None or self.layers.n_layers == 0:
            return (np.empty(0, dtype=int), np.empty(0, dtype=int))
        return (self.layers.OV[-1], self.layers.IV[-1])


def compute_mesh_structure(domain, kind: str = "layers") -> MeshStructure:
    """Compute a mesh structure snapshot from a CHILmesh domain.

    Args:
        domain: A CHILmesh instance with layers attribute.
        kind: One of "layers", "skeleton", or "medial_axis". Defaults to "layers".

    Returns:
        A MeshStructure dataclass with the selected kind, layer count, and
        (for layers/skeleton) a deep-copied LayerState snapshot, or (for medial_axis)
        nodes and edges arrays.

    Raises:
        ValueError: If kind is not in VALID_KINDS.
    """
    if kind not in VALID_KINDS:
        raise ValueError(
            f"unknown kind {kind!r}; expected one of {VALID_KINDS}"
        )

    if kind == "layers":
        ls = LayerState.from_mesh(domain)
        n = getattr(domain, "n_layers", None)
        if n is None:
            n = ls.n_layers
        return MeshStructure(kind="layers", n_layers=int(n), layers=ls)

    if kind == "skeleton":
        # Morphological skeleton via CHILmesh layer peeling (issue #55, 2026-05-30).
        # CHILmesh._skeletonize() peels outermost->innermost: layer 0 = first-peeled
        # boundary elements, layer N-1 = irreducible core (the skeleton proper).
        # skeleton_core / skeleton_core_verts expose the innermost layer for comparison
        # against medial_axis as a tri-to-quad starting point (see spec 055).
        ls = LayerState.from_mesh(domain)
        n = getattr(domain, "n_layers", None)
        if n is None:
            n = ls.n_layers
        return MeshStructure(kind="skeleton", n_layers=int(n), layers=ls)

    if kind == "medial_axis":
        from ._medial_axis import medial_axis_graph
        nodes, edges = medial_axis_graph(domain)
        return MeshStructure(kind="medial_axis", n_layers=0, nodes=nodes, edges=edges)
