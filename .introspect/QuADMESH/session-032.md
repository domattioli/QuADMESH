# Introspection — QuADMESH session-032

- session_id: development@84ba4f4
- date: 2026-06-21T19:16Z
- rotation: hour-19 (maintenance track; #48 closed)
- model: claude-opus-4-8 (orchestrator) + haiku (coding-dispatch subagents)

## Outcome
Shipped #98 option A (opt-in `refuse_boundary_merge`, default OFF) — the slice
sessions 030/031 deferred on timeout. Offline-verified (87 passed / 55 skipped).
Found + pinned that A is a near no-op on offline fixtures (Block_O 273 unchanged);
the real lever is the pairing-merge acceptance criterion, not leftover routing.

## What worked
- **Located the defect's real source before trusting the prior session's claim.**
  Toggling `point_insert=False` + `remove_boundary_tris=False` isolated Block_O's
  273 to the main pairing merge in 1 measurement — contradicted the inherited
  "93% from `_tri_removal.py:347`" claim (which was WNAT-scale, untestable offline).
  Cheap experiment, high-value correction. Avoided the #168 false-win trap.
- **Coding-dispatch to Haiku with exact old/new blocks** → 5-file flag thread
  landed clean, syntax-checked, byte-identical default-OFF. Orchestrator reviewed
  the full diff + ran the gate before commit.
- **Pinned the honest negative result in a gate test** → next session won't
  re-characterize (breaks the session-030 churn loop).

## Pains (→ matrix rows; NO new request:skill per #203)
1. **Exact-signature contract test brittle to additive kwargs.** Appending an
   optional trailing keyword param to `run_pipeline` broke
   `test_run_pipeline_signature` (asserts `param_list == expected_params`). Cost:
   1 extra Haiku round-trip. The test SHOULD assert the required prefix + that new
   params are keyword-with-default, not exact list equality. Repo-local test-design
   fix, not a DomI skill gap. Logged here; no action required this session.
2. **Inherited cross-session claim was scale-scoped without flagging it.** The
   "93% from line 347" finding from session-031 was true at WNAT/ENPAC scale but a
   no-op on the only meshes validatable offline. Lesson: located-defect claims
   should state the mesh scale they were measured at, so the executing session
   knows whether the offline gate can confirm them. Captured in session-032 handoff.

## DomI hub
- No DomI bug/gap surfaced. `.domi-pin` current (`0a96f17` == DomI main HEAD).
  No new request:skill filed (#203).
