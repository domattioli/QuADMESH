"""Markdown and JSON reports (contracts/cli-and-results.md)."""
from __future__ import annotations

import json
from pathlib import Path

from ._metrics import BenchmarkRow

_COLS = ["Adapter", "Status", "Elems", "Quad %", "Resid tris (int/bnd)", "Skew mean",
         "Skew min", "Skew std", "% < 0.3", "Concave quads", "Time (s)", "Bnd verts lost",
         "Bnd verts added"]


_LABELS = {"greedy-tri-merge": "greedy recombination (baseline)"}


def _f(x, nd=3):
    return "" if x is None else f"{x:.{nd}f}"


def _md_row(r: BenchmarkRow) -> str:
    ok = r.status == "ok"
    cells = [_LABELS.get(r.adapter, r.adapter), r.status if ok else f"{r.status}: {r.message}".rstrip(": ")]
    if ok:
        cells += [str(r.n_elems), f"{100 * r.quad_fraction:.1f}",
                  f"{r.residual_tris_interior}/{r.residual_tris_boundary}",
                  _f(r.skew_mean), _f(r.skew_min), _f(r.skew_std), _f(r.pct_bad, 1), str(r.n_concave),
                  _f(r.runtime_s, 2), str(r.boundary_lost),
                  str(r.boundary_added)]
    else:
        cells += [""] * (len(_COLS) - 2)
    return "| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in cells) + " |"


NOTES = [
    "Notes:",
    "",
    "- Lost is the number of input boundary vertices with no match in the output boundary. "
    "Added is the number of new output boundary vertices. QuADMESH+ point insertion adds "
    "boundary vertices (R5). The QuADMESH+ lost count comes from the boundary-quad cleanup "
    "step in post-processing, which collapses boundary quads. Smoothing does not move "
    "boundary vertices.",
    "- QuADMESH+ skew min is 0.000 on every bundled mesh in this table.",
    "- Simple reference baseline: pairs adjacent triangles greedily; included for comparison only.",
    "- A \"not installed\" row means the executable was absent on the machine that produced "
    "this table. Gmsh and QuadriFlow were absent, so neither has a measured row.",
    "- QuadriFlow remeshes from a cross field and may move or drop boundary vertices (R3). "
    "Read its boundary columns when a row exists.",
]


def to_markdown(record) -> str:
    out = []
    for m in record.meshes:
        out += [f"### {m['name']}", "", "| " + " | ".join(_COLS) + " |",
                "|" + "---|" * len(_COLS)]
        out += [_md_row(r) for r in record.rows if r.mesh == m["name"]]
        out.append("")
    tools = ", ".join(f"{k} {v}" for k, v in sorted(record.tools.items())) or "none"
    out += [f"Tools: {tools}. Date: {record.date}. quadmesh {record.quadmesh_version}.",
            f"Reproduce: `{record.command}`", "", *NOTES, ""]
    return "\n".join(out)


def to_json(record, path=None) -> str:
    data = {"schema_version": record.schema_version,
            "quadmesh_version": record.quadmesh_version, "date": record.date,
            "tools": record.tools, "meshes": record.meshes,
            "rows": [r.to_dict() for r in record.rows]}
    text = json.dumps(data, indent=2) + "\n"
    if path is not None:
        Path(path).write_text(text)
    return text


def load_json(path):
    from ._runner import ResultsRecord

    d = json.loads(Path(path).read_text())
    return ResultsRecord(
        quadmesh_version=d["quadmesh_version"], date=d["date"], tools=d["tools"],
        meshes=d["meshes"], rows=[BenchmarkRow(**r) for r in d["rows"]],
        schema_version=d["schema_version"],
    )
