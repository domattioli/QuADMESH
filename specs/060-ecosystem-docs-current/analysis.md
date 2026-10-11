<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-11 skill=speckit-pipeline repo=quadmesh session=4e33ac09 -->
# Specification Analysis Report: 060-ecosystem-docs-current

Read-only cross-artifact analysis of spec.md, plan.md, research.md, data-model.md, quickstart.md, tasks.md and checklists/publication.md against the quadmesh constitution (v0.2.0). Findings from the checklist review (Astra, checklist round 1) are included. Remediation cycle 1 was applied to the artifacts after this table was drafted; the Status column records it.

| ID | Category | Severity | Location(s) | Summary | Recommendation | Status |
|---|---|---|---|---|---|---|
| I1 | Inconsistency | HIGH | spec FR-002 vs data-model link audit, tasks T010/T024 | FR-002 demanded every link resolve unconditionally while tasks introduce `outstanding` and `pending-push` staged states | State the staged states in FR-002 as reported-not-passed, resolved anonymously at completion | fixed (cycle 1) |
| I2 | Inconsistency | HIGH | spec FR-004, US2, Edge Cases; research R-5; tasks T030 | FR-004 limited the pending page to `AUTO_APPROVE=false`; T030 also covers a pre-existing `pending` record; R-5 and Edge Cases repeated the old scope | Every-renderable-state rule in all four places; US2 scoped to the default automatic flow | fixed (cycle 2) |
| I3 | Inconsistency | MEDIUM | quickstart `check_versions.py` per-repo call vs tasks T011 inventory-driven | Quickstart would have skipped site pages and token snippets | Single inventory-driven invocation with per-package published/pending files | fixed (cycle 1) |
| I4 | Ordering | HIGH | tasks T052a | Recovery ran gates before committing the corrected revision, so artifact evidence would not match the pushed tree | Fix, commit, rerun gates on that revision, push, recheck | fixed (cycle 1) |
| U1 | Underspecification | MEDIUM | research R-8, tasks T010/T052a | Anonymous pass defined by HTTP status only; a gate or login page would pass | Content marker required in `--anonymous` mode | fixed (cycle 1) |
| U2 | Underspecification | MEDIUM | tasks T048b | Preview check hit `/vault/` only, not protected child routes; no containment action | Two existing child routes, expected denial defined, stop-and-report, operator containment with fresh GET evidence | fixed (cycle 2) |
| U3 | Underspecification | LOW | data-model inventory | Mixed files inventoried whole, not by string literal or section | `section` column added | fixed (cycle 1) |
| U4 | Underspecification | MEDIUM | spec SC-001..SC-004 | SCs cited "grep" while the plan requires fail-closed helpers and a human disclosure review | SCs name the helpers and the review | fixed (cycle 1) |
| U5 | Underspecification | LOW | spec (missing section) | No definition of done versus hand-off with outstanding publication items | Two states: implementation delivered (requires T052a clear) versus public rollout complete (operator) | fixed (cycle 2) |
| U6 | Underspecification | LOW | data-model, tasks T012 | Evidence rows not tied to a content revision; T051 changes quadmesh after T048 | `section` + `content_sha` columns in all three schemas; verified blob-hash carry-forward in T012; `worktree:` form for uncommitted stubs | fixed (cycle 2) |
| G1 | Coverage gap | HIGH | spec FR-013, tasks T048a, T052, T052a | Pushing Valence could trigger a Worker deploy through workflow automation | Read-only trigger trace (yml/yaml, reusable workflows, scripts, provider hooks safe fields) with verdict none/deploys/unknown before every push; deploys or unknown keeps the push pending, classified prepared-blocked in the spec's done definition | fixed (cycle 3) |
| I7 | Inconsistency | MEDIUM | tasks T048a vs T048b | Blanket "deploys blocks the push" would also block the authorized Pages preview deployment | Behaviour and authorization recorded separately; only `none`, or `deploys`+`authorized` (site preview), may push | fixed (cycle 4) |
| U9 | Underspecification | LOW | quickstart | `$MM` used but undefined under `set -u`; unquoted paths | `MM` defined; `repo=sha` arguments quoted | fixed (cycle 4) |
| I6 | Inconsistency | MEDIUM | tasks T048b vs plan operator-only visibility | T048b demanded anonymous 200 on the wiki even when the gate intentionally denies | Expected denial recorded as publication limitation with local build proof; never counted as anonymous success | fixed (cycle 3) |
| U8 | Underspecification | LOW | quickstart, tasks T052 | `check_style_coverage.py` run without `--final-sha`; T052 refreshed artifacts only | Quickstart passes final SHAs per repo; T052 reruns all evidence gates after T051; `worktree:` rows compared by direct SHA-256 | fixed (cycle 3) |
| U7 | Underspecification | LOW | tasks T010, T024 | `pending-push-targets.txt` format and creation undefined | T024 writes `<url>\t<marker>` lines | fixed (cycle 2) |
| I5 | Inconsistency | LOW | tasks dependencies | "T052 is the last push" contradicted T052a's loop | Reworded | fixed (cycle 2) |
| A1 | Ambiguity | LOW | spec §Scope table | CHILmesh/quadmesh rows still list "GitHub wiki (empty today)" as a public surface after Q2 moved the wiki to the site | Keep as a factual surface (existing wikis link to the site per FR-009); no change | accepted as-is |
| C1 | Constitution | n/a | constitution VI vs data-model, T042 | Humanizer pass inserted between Golden rule and STE; order of the four constitution steps preserved | Compatible; justified in FR-011 | pass |
| T1 | Terminology | LOW | spec, plan | "tag archive", "tag zipball", "git archive" used for the same channel | Plan FR-006 wording already defines the relation; no change | accepted as-is |

## Coverage summary

| Requirement | Tasks | Covered |
|---|---|---|
| FR-001 | T011, T022, T024, T025, T026, T027 | yes |
| FR-002 | T010, T023, T024, T025, T027, T052a | yes |
| FR-003 | T024, T052a | yes |
| FR-004 | T028, T030, T031 | yes |
| FR-005 | T029, T030 | yes |
| FR-006 | T007, T009, T016, T019, T020, T052 | yes |
| FR-007 | T017, T018, T021 | yes |
| FR-008 | T022, T024, T025, T027 | yes |
| FR-009 | T033-T036, T038, T040, T048b | yes |
| FR-010 | T008, T013, T037, T047a | yes |
| FR-011 | T042-T047, T047a | yes |
| FR-012 | T016, T050, T051 (permitted edits only) | yes |
| FR-013 | T002, T004, T049 | yes |
| FR-014 | T051 | yes |
| SC-001..SC-007 | T048 (all gates), T052, T052a | yes |

Coverage: 14/14 FRs and 7/7 SCs have at least one task. Tasks without a requirement mapping: T001, T003, T005, T014a, T015 (setup and verifier tests; legitimate).

## Constitution alignment issues

None. Principle VI order preserved; no `CLAUDE.md`; spec drives implementation; specs move to DomI last.

## Unmapped tasks

None beyond setup/verification tasks listed above.

## Metrics

- Total requirements: 14 FR + 7 SC
- Total tasks: 57
- Coverage: 100%
- Ambiguity count: 1 (accepted)
- Duplication count: 0
- Critical issues: 0
- High issues: 4 (all fixed by cycle 2)

## Next actions

Remediation cycles 1 to 4 applied (cycle 2 from Astra's analyze round 1 review). If Astra confirms, the pipeline is ready for the implement hand-off; the implementer should treat `analysis.md` as closed and rely on `tasks.md` plus `quickstart.md`.
