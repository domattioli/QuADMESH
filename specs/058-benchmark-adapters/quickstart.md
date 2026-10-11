<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-plan repo=quadmesh session=4e33ac09 -->
# Quickstart: benchmark adapters

```bash
bash scripts/dev_setup.sh && . .venv/bin/activate
quadmesh-bench --list                       # adapters, license tags, install route, installed or disabled
pip install "quadmesh[bench-quadriflow]"    # optional; "quadmesh[bench]" installs every permissive adapter
quadmesh-bench --bundled --disable quadriflow   # runtime opt-out (or QUADMESH_BENCH_DISABLE=quadriflow)
quadmesh-bench --bundled                    # QuADMESH+ and greedy tri-merge rows on chilmesh.data meshes
brew install gmsh                           # optional, GPL tool stays outside the package
quadmesh-bench --bundled --adapters quadmesh-plus,gmsh-blossom --out docs/benchmarks/0.3.0
pytest tests/test_bench_*.py                # contract, io, metrics, runner, claims; packaging test is marked slow
pytest --runslow tests/test_bench_packaging.py
```

Verification for the lead (not the worker's self-report): open `docs/benchmarks/0.3.0/results.md`, confirm one table per bundled mesh with the FR-009 columns, confirm the README benchmark section names only adapters present in that table, and run the claims and packaging tests yourself.
