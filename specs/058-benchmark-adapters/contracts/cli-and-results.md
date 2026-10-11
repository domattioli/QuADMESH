<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-plan repo=quadmesh session=4e33ac09 -->
# Contract: `quadmesh-bench` CLI and results files

## CLI

```
quadmesh-bench MESH [MESH ...] [--adapters NAME[,NAME...]] [--disable NAME[,NAME...]] [--out DIR] [--timeout S] [--strict] [--list] [--show-disabled]
```

- `MESH`: `.14` paths. `--bundled` adds every mesh in `chilmesh.data`.
- `--adapters`: default all registered. Unknown name: exit 2 with the list of known names.
- `--out DIR`: writes `results.md` and `results.json`; default prints the Markdown table to stdout only.
- `--timeout S`: per adapter per mesh; default 600.
- `--strict`: exit 1 if any row has status other than `ok`. Default exit 0 regardless of row status (FR-022).
- `--disable`: skip named adapters even if installed; merged with `QUADMESH_BENCH_DISABLE` (comma-separated).
- `--list`: print adapters with license tag, install route and probe result (`available`, `not installed: <hint>`, `disabled`), exit 0.
- `--show-disabled`: include disabled adapters as rows with status `disabled`.

Install routes:

```
pip install quadmesh                      # QuADMESH+ and greedy tri-merge
pip install "quadmesh[bench-quadriflow]"  # one permissive adapter
pip install "quadmesh[bench]"             # every permissive adapter; never GPL
brew install gmsh  /  apt install gmsh    # GPL tool, outside pip; detected on PATH
```

## Python API

```python
from quadmesh.benchmark import run_benchmark, get_adapters
record = run_benchmark(meshes=[path1, path2], adapters=None, disabled=None, timeout_s=600)
record.to_markdown(); record.to_json(path)
```

## results.json (schema_version 1)

See `data-model.md` ResultsRecord. Rows carry every FR-009 column; numeric fields are null when status is not `ok`.

## results.md

One H3 per mesh, then a table with columns: Adapter, Status, Elems, Quad %, Resid tris (int/bnd), Skew mean, Skew min, Skew std, % < 0.3, Time (s), Bnd verts lost, Bnd verts added. A footer lists tool versions, date, package version, and the reproduce command.
