# Session 033 — 2026-07-04 (rotation hour-03)

## What changed
- **spec-056 SC-001 gate run EXECUTED on WNAT_Onur** (`056-hierarchical-smoother`
  @ `0565104`, `80fed16`; PR #105 body refreshed; #104 commented). Yesterday's
  "mesh not provisioned in-container" deferral was void here: `WNAT_Onur.14`
  present in the Valence sibling clone (`/home/user/Valence/registry_data/meshes/`)
  and the chilmesh C++ backend built in-container
  (`pip install /home/user/CHILmesh/src/chilmesh_cpp` → `chilmesh_cpp 0.6.0.dev0`,
  `backend_info()` selected=cpp).
- **Gate verdict: SC-001 FAILED, measured** — supplement default 0.61×
  (55.0 s vs baseline 33.5 s at 129,916 quads; gate needed ≥2×). SC-003 failed.
  SC-002 holds for supplement only. Invariant (0 interior tris) holds everywhere.
- **Cheap-global orderings measured on TC1/Block_O** (operator mid-session ask):
  both worse (−0.08 mean skew) + slower; ordering irrelevant (identical outputs).
  All 7 grid variants now measured at small scale.
- **#107 filed**: `fem_smoother` passes 2–3 are no-ops → `n_iter=1` default is a
  free ~3× smoothing cut; docstring claims an early-stop that doesn't exist.
- `.domi-pin` drift found at bootstrap; a concurrent session had already pushed
  the same refresh (`b605d94`) — redundant local commit dropped via rebase-skip.

## Key decisions / findings
- **Mechanism: the global Balendran pass ERASES any pre-pass.** Supplement
  enters its global pass from mean-skew 0.516 and exits bit-for-bit at the
  3-pass baseline (0.6365/0.7148/16601) — same exact parity on TC1 + Block_O.
  The solve (K·u=0 interior, kinf-pinned boundary) is a connectivity-anchored
  equilibrium ⇒ hierarchical-then-global composition can never lift quality.
- **The #104 premise doesn't transfer**: with the C++ chilmesh backend, smoothing
  is ~12% of WNAT_Onur wall-clock (33.5 s vs 241.4 s sweep/cleanup), not the
  ~70% ENPAC figure. Re-profile (#76) before more smoother-perf work.
- Recommendation recorded (spec-056 Decision Log): keep `hierarchical=True`
  opt-in only; operator call on merging PR #105 as honest-negative + harness
  vs closing unmerged.

## Verification
- WNAT bench exit 0 (invariant gate clean); tables pinned in spec-056 Decision
  Log (output/ is gitignored). No production code touched this session
  (docs/bench only — 0 Haiku dispatches, within budget).

## What comes next
- Operator: merge-or-close call on PR #105; #104 disposition (hierarchical
  hypothesis answered negative; remaining live lever = #107 n_iter=1).
- #107 gate run: n_iter=1 vs 3 byte-identity on the mesh ladder → default flip.
- Re-profile WNAT/ENPAC with C++ backend (#76) — sweep/cleanup is the 88%.
- #90 boundary-layer quality: any fix must not end in a global FEM pass
  (erasure), and interior smoothing is already at its fixed point.
