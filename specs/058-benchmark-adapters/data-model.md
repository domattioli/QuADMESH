<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# Data Model: Benchmark adapters

## Adapter (Protocol)

| Field / method | Type | Rule |
|---|---|---|
| `name` | str | Unique registry key, lower-kebab (`quadmesh-plus`, `greedy-tri-merge`, `gmsh-blossom`, `quadriflow`) |
| `display_name` | str | Public name used in tables and README (`QuADMESH+`, `greedy recombination (baseline)`, `Gmsh Blossom-Quad`, `QuadriFlow`) |
| `family` | str | From the 002 catalog (`direct`, `indirect-recombine`, `indirect-field`) |
| `license_tag` | enum | `project`, `MIT-external`, `BSD-external`, `GPL-subprocess`, `clean-room` |
| `citation` | str | Canonical reference |
| `install_route` | enum | `base`, `extra:<name>` (pip extra), `external` (user-installed executable; always the case for GPL) |
| `install_hint` | str | One line, shown in a "not installed" row; generated from `install_route` plus an adapter-specific suffix |
| `enabled` | bool (runtime) | False when named in `--disable`, the Python argument or `QUADMESH_BENCH_DISABLE` |
| `probe()` | `Availability` | Never runs the mesher; returns installed flag, version string or None, executable path or None |
| `run(mesh, options)` | `AdapterResult` | Pure function of input; writes only to a temp dir it owns |

## Availability

`installed: bool`, `version: str | None`, `path: str | None`, `message: str`.

## AdapterOptions

`timeout_s: float = 600`, `target_faces: int | None`, `extra: dict[str, str]` (passed to external tools as documented per adapter).

## AdapterResult

| Field | Type | Rule |
|---|---|---|
| `mesh` | CHILmesh or None | None on failure |
| `adapter` | str | registry key |
| `version` | str | tool version or `"built-in"` |
| `license_tag` | enum | copied from adapter |
| `runtime_s` | float | wall-clock of `run`, including format conversion |
| `convert_s` | float | time spent in format conversion; reported so readers can subtract it |
| `success` | bool | |
| `message` | str | empty on success; stderr tail (last 20 lines) on failure |
| `vertex_order_preserved` | bool | True for recombination methods |

## BenchmarkRow

Derived from one `AdapterResult` on one mesh. Columns in FR-009 order:

`mesh`, `adapter`, `status` (`ok`, `failed`, `not installed`, `unsupported input`, `timeout`), `n_verts_in`, `n_verts_out`, `n_elems`, `quad_fraction`, `residual_tris_interior`, `residual_tris_boundary`, `skew_mean`, `skew_min`, `skew_std`, `pct_bad`, `n_concave`, `runtime_s`, `boundary_lost`, `boundary_added`, `message`.

Status transitions: `disabled` (opt-out) → no row unless `--show-disabled`; `not installed` (probe false) → never runs; `ok` / `failed` / `timeout` from `run`; `unsupported input` when the input holds quads and the adapter declares `accepts_mixed=False`.

## ResultsRecord

`schema_version: 1`, `quadmesh_version`, `date` (ISO), `tools: {adapter: version}`, `meshes: [{name, sha1, n_verts, n_tris}]`, `rows: [BenchmarkRow]`. Serialized to `results.json`; `results.md` is a view.

## ClaimMapping (test-only)

Set of `display_name` for adapters whose contract tests run in offline CI, plus the set that requires a user-installed tool. README and description text are checked against both sets.
