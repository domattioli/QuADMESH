# Quickstart: Hierarchical Smoothing (spec-056)

```python
from chilmesh import CHILmesh
from quadmesh.hierarchical_smooth import hierarchical_smoother

mesh = CHILmesh.read_from_fort14("tests/fixtures/meshes/Test_Case_1.14")
# ... tri2quad pipeline up to the smoothing stage ...

# Default: local-FEM-only on worst 7.5% skew + 1-ring
smoothed = hierarchical_smoother(mesh)

# Layer-0 policy, with metadata
smoothed, info = hierarchical_smoother(mesh, policy="layer", return_info=True)
print(info.timings["total"], info.n_patches, info.fell_back)
```

Pipeline composition (supplement: pre-pass + 1 global FEM pass):

```python
from quadmesh.post_process import post_process_routine
out = post_process_routine(mesh, hierarchical=True)          # default path untouched when False
```

Benchmark (baseline always included; token needed for WNAT_Onur fixture):

```bash
. .venv/bin/activate
python scripts/bench_hierarchical_smooth.py --mesh Test_Case_1
python scripts/bench_hierarchical_smooth.py --mesh WNAT_Onur   # SC-001 gate mesh
```

Tests: `pytest tests/test_hierarchical_smooth.py -q` (synthetic cases run tokenless).
