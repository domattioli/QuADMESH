# CLAUDE.md

## Faithfulness invariant (non-negotiable)

Interior residual triangle (tri with NO domain-boundary edge) after tri2quad = **NOT a faithful QuADMESH+ implementation**. Zero interior tris is mandatory — a properly-implemented QuADMESH+ never leaves one. Only **boundary** tris may remain (thesis minimizes even those; ≤1 typical). Pinned by `tests/test_no_interior_tris.py`.

Status: `method="matching"` has zero interior tris by construction (faithful on this axis). `method="quadmesh+"` (layer-ordered per-layer loop, T020/T004; `"layered"` mechanism-alias + `"faithful"` deprecated alias, kept for back-compat through v0.2) now implemented — zero interior tris confirmed, quality 0.375→0.573 on Test_Case_1. **Still WIP** — Ch 4 IE-before-OE interior heuristics (T017) and boundary-layer OE-before-IE + walkability pre-pass (T018) are not yet implemented; until those land, `method="quadmesh+"` must not be made default.

> Naming note (#46): canonical `method=` value for the layer-ordered sweep is **`"quadmesh+"`** — the published algorithm name (QuADMESH+, alternative to blossom-quad / paving), per operator 2026-06-09. `"layered"` (the mechanism name) is accepted as an alias; `"faithful"` is a deprecated alias (still works, emits `DeprecationWarning`). History: `"faithful"` named a *philosophy* (faithful MATLAB port), a category error next to `"matching"` (which names its mechanism) → renamed `"layered"` → now `"quadmesh+"`. The word "faithful" still describes port *fidelity* throughout the code; only the `method=` input value changed.

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

External Python dep. Issues filed against it for missing/slow APIs: #132 (`merge_elements`), #133 (`ccw_edges_around_vert`), #134 (adjacencies flag), #138 (`submesh`), #139 (`angle_based_smoother` perf).

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

All coding work (writing or editing source code) MUST be dispatched to a subagent running the Haiku model (`claude-haiku-4-5`) — not written inline by the main session. The orchestrator session plans, reviews, and integrates; implementation is delegated to the Haiku subagent.

- **Default**: for any code-writing/editing task, spawn a subagent with `model: haiku`.
- **Exception**: only when the operator explicitly directs otherwise (e.g. "do it inline", "use Sonnet/Opus for this"). Explicit operator instruction only — never assumed.
- **Scope**: applies to code. Non-coding work (planning, research, docs, git/PR orchestration, review) stays on the main session.
