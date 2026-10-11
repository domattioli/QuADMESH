<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-plan repo=quadmesh session=4e33ac09 -->
# Contract: Adapter protocol (`quadmesh.benchmark`)

```python
from quadmesh.benchmark import register, Adapter, AdapterResult, Availability, AdapterOptions

@register
class MyAdapter:
    name = "my-adapter"
    display_name = "My Adapter"
    family = "indirect-recombine"
    license_tag = "project"
    citation = "Author (Year). Title. Venue."
    install_hint = ""
    accepts_mixed = False

    def probe(self) -> Availability: ...
    def run(self, mesh: "CHILmesh", options: AdapterOptions) -> AdapterResult: ...
```

Guarantees the runner relies on:

1. `probe()` is cheap (under 1 s), has no side effects, and never executes the mesher.
2. `run()` never mutates `mesh`; it works in a temp dir it creates and removes.
3. `run()` returns a result rather than raising for tool failures; the runner also catches any exception and turns it into `status="failed"`.
4. Output `mesh.connectivity_list` is 0-based, rows padded with -1 for triangles in a mixed array, matching CHILmesh conventions.
5. `license_tag == "GPL-subprocess"` adapters contain no `import` of the tool's Python bindings; the packaging test enforces it.

Shared contract tests (`tests/test_bench_contract.py`), parametrized over `get_adapters()`:

- probe returns an `Availability`; if not installed, the remaining tests skip for that adapter.
- run on `simple_test_case.14` (or the smallest `chilmesh.data` mesh) returns `success=True`.
- output elements are counter-clockwise, no zero-area, vertex count > 0.
- metadata fields present and typed.
- input mesh points and connectivity are unchanged after `run` (reuse the pattern from `tests/test_input_immutability.py`).
