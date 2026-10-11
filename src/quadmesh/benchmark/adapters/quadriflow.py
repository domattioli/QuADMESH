"""QuadriFlow adapter (pyquadriflow module, else subprocess). Pre-alpha.

QuadriFlow (Huang et al. 2018) is MIT licensed. Nothing is vendored. Route 1:
the optional ``pyquadriflow`` package (``quadmesh[bench-quadriflow]``, Linux and
Windows only, pre-alpha), used when importable. Route 2: the ``quadriflow``
executable on PATH or named by ``QUADMESH_QUADRIFLOW``, run as a subprocess.

NOT VERIFIED: no QuadriFlow binary or pyquadriflow install was available when
this was written. The pyquadriflow call (``pyQuadriFlow.pyQuadriFlow.pyquadriflow``,
nine positional arguments, returns dict with ``vertices`` and ``faces``) was read
from the 0.0.4 wheel source and never run. The command line (``quadriflow -i in.obj -o out.obj -f N``) follows research.md R3
and was never run. The behavior on the open planar bundled meshes is unknown.
QuadriFlow remeshes from a cross field and expects a manifold, usually closed,
surface, so on an open planar domain it may move or drop boundary vertices or
fail. The boundary columns of the results table report what it did. Record the
observed behavior here after running spec 058 tasks T020 and T021 on a machine
with the executable.

PyPI: ``pyquadriflow`` 0.0.4 (MIT, pre-alpha) bundles only a Linux ``.so`` and
a Windows ``.dll``, so the extra carries a platform marker and macOS relies on
the executable route.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from chilmesh import CHILmesh

from .. import _protocol as P
from .._io import read_obj, write_obj


def _py_remesh():
    """Return the pyquadriflow function, or None when the package is not importable."""
    try:
        from pyQuadriFlow.pyQuadriFlow import pyquadriflow
    except Exception:  # missing package or missing native library
        return None
    return pyquadriflow


def _exe() -> str | None:
    env = os.environ.get("QUADMESH_QUADRIFLOW")
    if env:
        return env if shutil.which(env) or os.path.isfile(env) else None
    return shutil.which("quadriflow")


@P.register
class QuadriFlow:
    name = "quadriflow"
    display_name = "QuadriFlow"
    family = "indirect-field"
    license_tag = "MIT-external"
    citation = ("Huang, J., Zhou, Y., Niessner, M., Shewchuk, J. R., Guibas, L. J. (2018). "
                "QuadriFlow: A Scalable and Robust Method for Quadrangulation. CGF 37(5).")
    install_route = "external"
    install_hint = P.install_route_hint(
        "external", "pyquadriflow (extra bench-quadriflow, Linux/Windows) or quadriflow executable on "
        "PATH or QUADMESH_QUADRIFLOW (MIT, pre-alpha, requires user-installed tool)")
    accepts_mixed = False

    def probe(self) -> P.Availability:
        if _py_remesh() is not None:
            return P.Availability(True, "pyquadriflow", "pyquadriflow", "")
        exe = _exe()
        if exe is None:
            return P.Availability(False, None, None,
                                  "pyquadriflow not importable and quadriflow executable not found")
        return P.Availability(True, "unknown", exe, "")

    def _run_module(self, mesh, conn_in, faces, t0):
        """UNVERIFIED: argument order follows the pyquadriflow 0.0.4 source."""
        fn = _py_remesh()
        try:
            c0 = time.perf_counter()
            pts3 = np.c_[np.asarray(mesh.points, float)[:, :2], np.zeros(len(mesh.points))]
            convert = time.perf_counter() - c0
            res = fn(faces, 0, pts3.tolist(), np.asarray(conn_in)[:, :3].tolist(),
                     False, True, False, False, False)
            c1 = time.perf_counter()
            out = CHILmesh(np.asarray(res["faces"], int), np.asarray(res["vertices"], float)[:, :2])
            convert += time.perf_counter() - c1
        except Exception as exc:
            return P.AdapterResult(None, self.name, "pyquadriflow", self.license_tag,
                                   time.perf_counter() - t0, 0.0, False, str(exc), False)
        return P.AdapterResult(out, self.name, "pyquadriflow", self.license_tag,
                               time.perf_counter() - t0, convert, True, "", False)

    def run(self, mesh, options: P.AdapterOptions) -> P.AdapterResult:
        av = self.probe()
        if not av.installed:
            return P.AdapterResult(None, self.name, "", self.license_tag, success=False,
                                   message=av.message, vertex_order_preserved=False)
        t0 = time.perf_counter()
        conn_in = np.asarray(mesh.connectivity_list)
        faces = options.target_faces or max(1, len(conn_in) // 2)
        if av.path == "pyquadriflow":
            return self._run_module(mesh, conn_in, faces, t0)
        with tempfile.TemporaryDirectory(prefix="qm-qf-") as td:
            td = Path(td)
            c0 = time.perf_counter()
            write_obj(td / "in.obj", np.array(mesh.points), conn_in)
            convert = time.perf_counter() - c0
            try:
                r = subprocess.run([av.path, "-i", "in.obj", "-o", "out.obj", "-f", str(faces)],
                                   cwd=td, capture_output=True, text=True,
                                   timeout=options.timeout_s)
            except subprocess.TimeoutExpired:
                return P.AdapterResult(None, self.name, "unknown", self.license_tag,
                                       time.perf_counter() - t0, convert, False, "timeout", False)
            if r.returncode != 0 or not (td / "out.obj").exists():
                tail = "\n".join((r.stdout + r.stderr).splitlines()[-20:])
                return P.AdapterResult(None, self.name, "unknown", self.license_tag,
                                       time.perf_counter() - t0, convert, False,
                                       tail or "quadriflow produced no out.obj", False)
            c1 = time.perf_counter()
            pts, conn = read_obj(td / "out.obj")
            out = CHILmesh(conn, pts[:, :2])
            convert += time.perf_counter() - c1
        return P.AdapterResult(out, self.name, "unknown", self.license_tag,
                               time.perf_counter() - t0, convert, True, "", False)
