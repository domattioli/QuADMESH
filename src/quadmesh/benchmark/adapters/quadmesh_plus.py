"""QuADMESH+ reference adapter: wraps ``run_pipeline`` with default options."""
from __future__ import annotations

import time

import numpy as np
from chilmesh import CHILmesh

from .. import _protocol as P
from ... import __version__


@P.register
class QuadmeshPlus:
    name = "quadmesh-plus"
    display_name = "QuADMESH+"
    family = "direct"
    license_tag = "project"
    citation = "Mattioli, D. QuADMESH+ (https://github.com/domattioli/QuADMESH)."
    install_route = "base"
    install_hint = P.install_route_hint("base")
    accepts_mixed = False

    def probe(self) -> P.Availability:
        return P.Availability(True, __version__, None, "")

    def run(self, mesh, options: P.AdapterOptions) -> P.AdapterResult:
        from ...pipeline import run_pipeline

        t0 = time.perf_counter()
        # Work on a copy so the caller's mesh is never touched (FR-018).
        work = CHILmesh(np.array(mesh.connectivity_list), np.array(mesh.points))
        out = run_pipeline(work)
        return P.AdapterResult(
            mesh=out, adapter=self.name, version=__version__,
            license_tag=self.license_tag, runtime_s=time.perf_counter() - t0,
            vertex_order_preserved=True,
        )
