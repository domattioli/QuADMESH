# CLAUDE.md

## Faithfulness invariant (non-negotiable)

Interior residual triangle (tri with NO domain-boundary edge) after tri2quad = **NOT a faithful QuADMESH+ implementation**. Zero interior tris is mandatory — a properly-implemented QuADMESH+ never leaves one. Only **boundary** tris may remain (thesis minimizes even those; ≤1 typical). Pinned by `tests/test_no_interior_tris.py`.

Status: `method="quadmesh+"` (the published layer-ordered per-layer loop; `"layered"` mechanism alias) is the **sole and default** method — zero interior tris confirmed. `"matching"` and the deprecated `"faithful"` alias were **removed entirely** per operator directive on #46 (2026-06-12); both now raise `ValueError`. **T017/T018 landed 2026-06-13** (greedy interior-saturating pairing of post-sweep layer leftovers, thesis Ch 4.1 IE-before-OE + Ch 4.2 fold-seam forbiddance, wired into `_quadmesh_plus_per_layer`): post-process mean quality Test_Case_1 0.573→0.696, Block_O 0.251→0.680. Naming note: the per-layer loop is `_quadmesh_plus_per_layer` (renamed from `_faithful_per_layer` per #46 — code must not name the *method* "faithful"; the word still describes port *fidelity* only). Residual WIP: T019 isolated-tri edge-swap fixup; boundary-layer walkability still falls back to per-tri routing on a small residual.

> **Update 2026-06-16 (PR #94) — "quad-pure" is index-based and INSUFFICIENT alone.** `test_no_interior_tris` counts vertex *indices*, so a **degenerate quad** (4 distinct indices but a ~180° corner = geometrically a triangle with a colinear node) passes as a clean quad. quadmesh+ was emitting **~100–274 such degenerate elements per mesh** from two bugs: (1) **non-cyclic quad vertex order** out of `chilmesh.quad_from_tri_pair` + the leftover-insertion builders, and (2) **`route_leftover_tri` faking unpairable leftovers into degenerate quads** via on-edge point insertion (`edge_bisection`/`edge_insertion` — *faithful to MATLAB*, which `edgeBisection.m` itself calls a "(degenerate) quad", but wrong). Fixes: a **CCW vertex-reorder** (`_topology._ccw_order` in `merge_tri_pair` + a global pass in `tri2quad_routine`), and `route_leftover_tri` now **defers** those leftovers (returns `bool`; only `edge_removal` consumes) to the genuine `_point_insert_tri_pairs` pairing (neighbour quad + interior point → 2 real quads). Result (chilmesh `element_quality`): degenerate (aspect<0.01) **~100–274 → 1–3**, mean aspect **0.55→0.67**, zero interior/strict triangles, zero bowties. Gate added: `test_no_degenerate_quads` (chilmesh-aspect, order-independent) — the index-based check stayed green through the whole degeneracy, so always pair it with the aspect gate.

> Naming note (#46): canonical `method=` value for the layer-ordered sweep is **`"quadmesh+"`** — the published algorithm name (QuADMESH+, alternative to blossom-quad / paving), per operator 2026-06-09. `"layered"` (the mechanism name) is accepted as an alias; `"faithful"` was a deprecated alias (now removed — raises `ValueError`). History: `"faithful"` named a *philosophy* (faithful MATLAB port), a category error next to `"matching"` (which names its mechanism) → renamed `"layered"` → now `"quadmesh+"`. The word "faithful" still describes port *fidelity* throughout the code; only the `method=` input value changed. Update 2026-06-12: operator directed removal of `"faithful"` and `"matching"` entirely (#46 comment 2026-06-11); `"quadmesh+"`/`"layered"` are the only accepted values.

## Routine

Routine lives in `DomI/claude_routine_instructions.md` (private). Textbox payload format + per-repo profile knobs in §6–7 there. Do not duplicate routine prose here.

## Branch rule

All ongoing work goes on `development` (the long-lived staging branch per DomI `branching.md`; supersedes the deprecated `daily-maintenance`, itself renamed from `daily-issue-fixing`). Do not push to `master`/`main` directly — promotion to `main` is via PR `development → main` only. Do not push to historical branches (`daily-maintenance`, `python-porting-project`, `claude/affectionate-heisenberg-prShD`, `claude/awesome-goodall-cqPYK`, `claude/awesome-goodall-Tbur3`).

New session branches discouraged — work directly on `development`, PR → `main`. `branch_guard.sh` (DomI plugin) blocks non-allowlisted names.

## Layout

Conventional src-layout Python package (reorganized 2026-05-24, was numeric-prefix MATLAB-project layout):

- `src/quadmesh/` — Python port of QuADMESH+ (the package; `pip install -e .` from root).
- `tests/` — pytest suite; `tests/fixtures/meshes/` holds the `.14` test meshes.
- `docs/MAPPING.md` — MATLAB → Python function map + chilmesh gaps.
- `docs/sessions/session-NNN.md` — per-session handoff notes.
- `specs/001-matlab-to-python-port/`, `specs/003-root-reorg/` — speckit spec/plan/tasks.
- `matlab/` — frozen legacy MATLAB reference (was `02_QuADMESH_Library/`, `04_CHIL_Supporting_Functions/`). Not installable.
- `archive/` — in-repo holding pen for future removal: MATLAB `@CHILmesh`/ADMESH dups of upstream repos, `.mat` binaries, old results.
- `videos/` — README demo assets.

## chilmesh

External Python dep. The five API issues QuADMESH filed against it (#132 `merge_elements`, #133 `ccw_edges_around_vert`, #134 adjacencies flag, #138 `submesh`, #139 `angle_based_smoother` perf) are **all closed upstream (2026-05-22…24) and consumed here**: `identify_edges.py` + `_topology.py` use the public `ccw_edges_around_vert` / `CHILmesh(compute_adjacencies=...)` APIs (no private calls remain); `two_part_smoother` is deprecated in favor of `fem_smoother` (moots #138 adoption); `tri2quad(aggressive=)` stays reserved — wiring it to upstream `merge_elements` is the v0.3 feature ticket. Do not re-file these.

## Test + run

A fresh container has no numpy/scipy/chilmesh/pytest, and `chilmesh` is not on
PyPI — it must be editable-installed from the sibling `../CHILmesh` checkout.
`scripts/dev_setup.sh` provisions the `pytest tests/` gate idempotently:

```
bash scripts/dev_setup.sh         # venv + editable chilmesh + quadmesh[dev]
. .venv/bin/activate
pytest tests/                     # 87 tests, ~20s
python -m quadmesh.cli <input.14> -o <out.14>
```

## Session lifecycle

**Start of session**: invoke `session-resume` skill from DomI upstream (read latest `docs/sessions/session-NNN.md`, restore context: branch, PR, in-progress tasks, blockers). If skill not yet available upstream, do the equivalent manually: read latest handoff + `specs/001-matlab-to-python-port/tasks.md`.

**End of session**: invoke `handoff` skill from DomI upstream to write `docs/sessions/session-NNN.md` (next N) with: what changed, key decisions, files touched, what comes next, branch/PR state, open chilmesh issues. If skill not yet available upstream, do the equivalent manually.

DomI skill names tracked; replace manual prose with skill invocation once landed.

## Repo-local labels (issue #20 triage 2026-06-03)

These labels have no DomI canonical equivalent — kept repo-local by operator decision.

| Label | Meaning | Decision |
|---|---|---|
| `downstream-api` | Tracks needed CHILmesh API changes that QuADMESH requires | repo-local keep |

Deleted (no open issues, label definitions pending `gh`-equipped cleanup):
- `brainstorm` → migrate to `status: brainstorming`
- `domi-sync` → delete (not promoted to DomI canon)
- `investigation` → migrate to `request: research`
- `literature-review` → migrate to `request: research`

## Coding dispatch — Haiku subagent default

**Binding:** all code writing/editing MUST be dispatched to a Haiku subagent (`model: haiku`); the main session plans/reviews/integrates and verifies subagent output before commit. Non-code work (planning, research, docs, git/PR, review, editing memory) stays on main. Exception only on explicit operator instruction — never assumed.

Canonical policy + rationale: DomI [`.claude/policies/coding-dispatch.md`](https://github.com/domattioli/DomI/blob/main/.claude/policies/coding-dispatch.md) (governance authority; #83). This is the binding summary.
