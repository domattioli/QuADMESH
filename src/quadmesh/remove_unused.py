"""Drop unreferenced vertices from a mesh. Port of MATLAB RemoveUnusedVertices.

In MATLAB, ``removedVertIDs`` was provided by the caller. Here we simply
detect unreferenced verts from the connectivity list itself — robust to
any path through post-process. Compaction is delegated to ``CHILmesh.submesh``.
"""

from __future__ import annotations

import numpy as np

from chilmesh import CHILmesh


def remove_unused_vertices(mesh: CHILmesh) -> CHILmesh:
    """Drop verts not referenced by connectivity_list. Renumber + rebuild mesh."""
    used = np.unique(mesh.connectivity_list.ravel())
    if used.size == mesh.n_verts or mesh.n_elems == 0:
        return mesh

    new_mesh = mesh.submesh(np.arange(mesh.n_elems))
    # submesh suffixes grid_name with "_submesh"; keep the caller's name.
    new_mesh.grid_name = getattr(mesh, "grid_name", None)
    return new_mesh
