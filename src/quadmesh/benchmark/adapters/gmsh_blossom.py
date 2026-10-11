"""Gmsh Blossom-Quad adapter (subprocess only).

Gmsh is GPL-2.0+ and is NOT part of this package. The user installs it
(``brew install gmsh``, ``apt install gmsh`` or the gmsh.info binary). This
module runs the ``gmsh`` executable as a subprocess, never imports its Python
bindings, and redistributes nothing from Gmsh. Set ``QUADMESH_GMSH`` to a
specific executable to override the PATH lookup.

NOT VERIFIED: no Gmsh binary was available when this was written. The ``.geo``
script below follows research.md R2 and was never run. ``RecombineMesh`` on a
merged discrete mesh may need ``CreateGeometry;`` or ``Mesh.RecombineAll = 1``
depending on the Gmsh version, and the batch flag (``-``) is also unchecked.
Verify on a machine with Gmsh installed (spec 058 tasks T019, T021) and record
the working script here.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

import numpy as np
from chilmesh import CHILmesh

from .. import _protocol as P
from .._io import read_msh2, write_msh2

GEO = """\
Merge "in.msh";
Mesh.MshFileVersion = 2.2;
Mesh.RecombinationAlgorithm = 1;   // Blossom
RecombineMesh;
Save "out.msh";
"""


def _exe() -> str | None:
    env = os.environ.get("QUADMESH_GMSH")
    if env:
        return env if shutil.which(env) or os.path.isfile(env) else None
    return shutil.which("gmsh")


@P.register
class GmshBlossom:
    name = "gmsh-blossom"
    display_name = "Gmsh Blossom-Quad"
    family = "indirect-recombine"
    license_tag = "GPL-subprocess"
    citation = ("Remacle, J.-F., Lambrechts, J., Seny, B., Marchandise, E., Johnen, A., "
                "Geuzaine, C. (2012). Blossom-Quad. Int. J. Numer. Meth. Eng. 89(9).")
    install_route = "external"
    install_hint = P.install_route_hint(
        "external", "brew install gmsh or apt install gmsh (GPL, requires user-installed tool)")
    accepts_mixed = False

    def probe(self) -> P.Availability:
        exe = _exe()
        if exe is None:
            return P.Availability(False, None, None, "gmsh executable not found")
        try:
            r = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
            text = (r.stdout + r.stderr).strip()
            m = re.search(r"\d+\.\d+(\.\d+)?", text)
            return P.Availability(True, m.group(0) if m else text[:40], exe, "")
        except (OSError, subprocess.SubprocessError) as exc:
            return P.Availability(False, None, exe, f"gmsh probe failed: {exc}")

    def run(self, mesh, options: P.AdapterOptions) -> P.AdapterResult:
        av = self.probe()
        if not av.installed:
            return P.AdapterResult(None, self.name, "", self.license_tag, success=False,
                                   message=av.message, vertex_order_preserved=False)
        t0 = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="qm-gmsh-") as td:
            td = Path(td)
            c0 = time.perf_counter()
            write_msh2(td / "in.msh", np.array(mesh.points), np.asarray(mesh.connectivity_list))
            (td / "job.geo").write_text(GEO)
            convert = time.perf_counter() - c0
            try:
                r = subprocess.run([av.path, "job.geo", "-"], cwd=td, capture_output=True,
                                   text=True, timeout=options.timeout_s)
            except subprocess.TimeoutExpired:
                return P.AdapterResult(None, self.name, av.version or "", self.license_tag,
                                       time.perf_counter() - t0, convert, False,
                                       "timeout", False)
            if r.returncode != 0 or not (td / "out.msh").exists():
                tail = "\n".join((r.stdout + r.stderr).splitlines()[-20:])
                return P.AdapterResult(None, self.name, av.version or "", self.license_tag,
                                       time.perf_counter() - t0, convert, False,
                                       tail or "gmsh produced no out.msh", False)
            c1 = time.perf_counter()
            pts, conn = read_msh2(td / "out.msh")
            out = CHILmesh(conn, pts[:, :2])
            convert += time.perf_counter() - c1
        return P.AdapterResult(out, self.name, av.version or "", self.license_tag,
                               time.perf_counter() - t0, convert, True, "", False)
