"""Benchmark runner: per-adapter isolation, timeout, results record."""
from __future__ import annotations

import datetime
import hashlib
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
from chilmesh import CHILmesh

from .. import __version__
from . import _protocol as P
from ._metrics import BenchmarkRow, row_from_result


@dataclass
class ResultsRecord:
    quadmesh_version: str
    date: str
    tools: dict
    meshes: list
    rows: list
    schema_version: int = 1
    command: str = "quadmesh-bench --bundled"

    def to_markdown(self) -> str:
        from ._report import to_markdown
        return to_markdown(self)

    def to_json(self, path=None) -> str:
        from ._report import to_json
        return to_json(self, path)


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def _load(item) -> tuple:
    """(name, mesh, sha1) from a path or an in-memory CHILmesh."""
    if isinstance(item, (str, os.PathLike)):
        path = Path(item)
        return path.name, CHILmesh.read_from_fort14(path), _git_blob_sha1(path.read_bytes())
    mesh = item
    blob = np.asarray(mesh.points).tobytes() + np.asarray(mesh.connectivity_list).tobytes()
    return (getattr(mesh, "grid_name", None) or "mesh"), mesh, _git_blob_sha1(blob)


def _has_quads(mesh) -> bool:
    from ._metrics import element_rows
    return any(len(r) == 4 for r in element_rows(mesh.connectivity_list))


def _call_with_timeout(fn, timeout_s: float):
    box: dict = {}

    def target():
        try:
            box["value"] = fn()
        except BaseException as exc:  # noqa: BLE001
            box["error"] = exc

    th = threading.Thread(target=target, daemon=True)
    th.start()
    th.join(timeout_s)
    if th.is_alive():
        return "timeout", None
    if "error" in box:
        return "error", box["error"]
    return "ok", box["value"]


def run_benchmark(meshes, adapters=None, disabled=None, timeout_s: float = 600,
                  strict: bool = False, show_disabled: bool = False,
                  env=None) -> ResultsRecord:
    """Run adapters over meshes. Never raises for an adapter failure."""
    registry = P.get_adapters()
    names = list(adapters) if adapters else list(registry)
    unknown = [n for n in names if n not in registry]
    if unknown:
        raise KeyError(f"unknown adapters {unknown}; known: {sorted(registry)}")
    rows, tools, mesh_info = [], {}, []
    for item in meshes:
        name, mesh, sha1 = _load(item)
        mesh_info.append({"name": name, "sha1": sha1, "n_verts": int(mesh.n_verts),
                          "n_tris": int(mesh.n_elems)})
        mixed = _has_quads(mesh)
        for an in names:
            ad = registry[an]
            if P.is_disabled(an, disabled, env):
                if show_disabled:
                    rows.append(BenchmarkRow(name, an, "disabled", message="disabled by opt-out"))
                continue
            av = ad.probe()
            if not av.installed:
                msg = av.message or "not installed"
                hint = ad.install_hint or ""
                rows.append(BenchmarkRow(name, an, "not installed",
                                         message=f"{msg}; {hint}".rstrip("; ")))
                continue
            tools[an] = av.version or "built-in"
            if mixed and not ad.accepts_mixed:
                rows.append(BenchmarkRow(name, an, "unsupported input",
                                         message="input holds quads; adapter takes triangles only"))
                continue
            opts = P.AdapterOptions(timeout_s=timeout_s)
            t0 = time.perf_counter()
            kind, val = _call_with_timeout(lambda: ad.run(mesh, opts), timeout_s)
            wall = time.perf_counter() - t0
            if kind == "timeout":
                rows.append(BenchmarkRow(name, an, "timeout", runtime_s=wall,
                                         message=f"exceeded {timeout_s} s"))
            elif kind == "error":
                rows.append(BenchmarkRow(name, an, "failed", runtime_s=wall,
                                         message=f"{type(val).__name__}: {val}"))
            else:
                try:
                    rows.append(row_from_result(name, mesh, val))
                except Exception as exc:  # noqa: BLE001
                    rows.append(BenchmarkRow(name, an, "failed", runtime_s=wall,
                                             message=f"metrics: {type(exc).__name__}: {exc}"))
    return ResultsRecord(
        quadmesh_version=__version__, date=datetime.date.today().isoformat(),
        tools=tools, meshes=mesh_info, rows=rows,
    )
