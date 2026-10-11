<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-11 skill=speckit-pipeline repo=quadmesh session=4e33ac09 -->
# Publication and Disclosure Checklist: Ecosystem Docs Current

**Purpose**: Unit tests for the requirements writing in spec.md, plan.md and tasks.md on the domain where this feature can do harm: what becomes public (docs, wiki, artifacts) and what must not (agent files, provenance, credentials). Each item asks whether the requirement is written well enough to be implemented and verified without guessing.
**Created**: 2026-10-11
**Feature**: [spec.md](../spec.md), [plan.md](../plan.md), [tasks.md](../tasks.md)
**Audience**: reviewer of the spec before implement; Sol lead at hand-off.

## Requirement completeness

- [ ] CHK001 Is every public surface that this feature can change enumerated (README, docs/, CHANGELOG, CITATION, .zenodo.json, mkdocs, token-service copy, site wiki pages, ADMESH wiki stubs), with none implied only by "docs"? [Completeness, Spec §Scope, §FR-011]
- [ ] CHK002 Is the agent-intended file set defined by reference to one canonical list (the DomI release-ignore canon plus repo extensions) rather than by examples? [Completeness, Spec §FR-006, §US3.1]
- [ ] CHK003 Are all three distribution channels (sdist, wheel, tag archive consumed by Zenodo) named for each package, and is the limit of local `git archive` as evidence stated? [Completeness, Spec §FR-006]
- [ ] CHK004 Are the authorization boundaries and conditional operator hand-offs explicit for each publication action (production visibility, site PR merge, ADMESH wiki setting, Worker deploy, releases, wiki-link insertion when the URL is not yet reachable)? [Completeness, Plan §Operator-only items, Tasks T040/T049]
- [ ] CHK005 Does the spec state what happens to documents that are both human- and agent-facing? [Completeness, Spec §Edge Cases]

## Requirement clarity

- [ ] CHK006 Does the version wording requirement demand a published label with an independently verified source and a pending label marked unreleased, with any date optional and verified rather than invented? [Clarity, Spec §Clarifications Q1, §FR-001, §FR-007]
- [ ] CHK007 Is "short README" quantified (150 lines by `wc -l`, or the `AGENTS.md` override), with the measurement command given? [Clarity, Spec §FR-008]
- [ ] CHK008 Does the registry-disclosure requirement distinguish permitted consumer facts ("meshes come through Valence", sign-in, 30 days, on-the-spot token, 500/day, usage snippets, mesh names already public) from prohibited disclosures (provenance, storage, internals, private URLs)? [Clarity, Spec §FR-004, §FR-010]
- [ ] CHK009 Are the four style passes named by exact skill path and layer, including the substitute for the missing humanizer skill and the expanded six-step sequence? [Clarity, Spec §US5 table, §FR-011, Tasks T042]
- [ ] CHK010 Is "anonymously reachable" defined operationally (no auth, redirects followed, GET fallback) for links and wiki URLs? [Clarity, Research R-8, Tasks T010/T052a]

## Requirement consistency

- [ ] CHK011 Do spec FR-009, research R-1, plan §Research summary and tasks T033-T040 agree on the wiki host (Astro site, Cloudflare Pages, `/ecosystem/wiki/`), with no residual mention of GitHub Pages or per-repo wikis as the host? [Consistency, Spec §FR-009, Research §R-1, Plan §Research summary, Tasks Phase 6]
- [ ] CHK012 Do FR-002 (links must resolve) and the gated-wiki rule agree on how an unreachable prepared URL is recorded (`outstanding`/`pending-push`, never `ok`)? [Consistency, Spec §FR-002, Data-model §Link audit]
- [ ] CHK013 Do FR-012 (agent docs not rewritten) and FR-014 (move specs to DomI) and T016 (regenerate ignore blocks) agree on which agent-file edits are permitted? [Consistency, Spec §FR-012, §FR-014]
- [ ] CHK014 Is the branch rule consistent across spec, plan and tasks (recorded policy-approved working branch, never `main`), with every repository-specific exception documented where it applies? [Consistency, Spec §FR-013, Tasks T002/T004/T032]
- [ ] CHK015 Is the style sequence in data-model.md and T042 compatible with the constitution VI order (voice, Golden rule, STE+ADHD, tell scan), with the added humanizer pass placed and justified? [Consistency, Constitution §VI, Data-model §Style-pass ledger, Tasks T042]

## Acceptance criteria quality

- [ ] CHK016 Can every SC be verified by a named helper or command whose failure mode is fail-closed (error never passes)? [Measurability, Spec §SC-001..007, Quickstart]
- [ ] CHK017 Is "zero secret-term hits" paired with a human disclosure review, since a denylist cannot be complete, and is the review's record format defined? [Measurability, Spec §FR-010, Tasks T037]
- [ ] CHK018 Does each helper have a stated test (clean, leaking, error) before it is trusted as a gate? [Measurability, Tasks T014a]
- [ ] CHK019 Are "pass" rows in the artifact inspection tied to a recorded candidate SHA, and is a re-run required after the last commit that changes the tree? [Measurability, Data-model §Artifact inspection, Tasks T020/T052]

## Scenario coverage

- [ ] CHK020 Is the `AUTO_APPROVE=false` fallback (pending page) covered so the copy is truthful in every state that renders it? [Coverage, Spec §FR-004, Tasks T030]
- [ ] CHK021 Is the case "Cloudflare Access coverage of preview hostnames cannot be confirmed" covered with a stop-and-report rule rather than an assumption? [Coverage, Plan §Research summary (Decision), Research §R-2, Tasks T048b]
- [ ] CHK022 Is the case "a snippet needs an unreleased version" covered (what the public page says until release)? [Coverage, Spec §FR-005, Tasks T029]
- [ ] CHK023 Is recovery from a failed post-push anonymous check defined as: fix, commit the corrected candidate, rerun affected gates against that revision, push, anonymously recheck, with unresolved failures blocking completion? [Coverage, Tasks T052a]
- [ ] CHK024 Is the case "a public doc today names a mesh" resolved (existing names stay, no origin, no new names)? [Coverage, Spec §FR-010, §Edge Cases]

## Non-functional and privacy

- [ ] CHK025 Is it stated that the denylist, ledger, inventory and scan outputs live only in DomI and that DomI's visibility is verified before any commit there? [Privacy, Spec §FR-010, Tasks T001/T051]
- [ ] CHK026 Is the credential-inspection rule for staged DomI files specific enough to avoid false positives on git SHAs and placeholders while catching real tokens, and does it forbid opening `.env`/`.dev.vars`? [Privacy, Tasks T051]
- [ ] CHK027 Is it stated that private repository visibility does not make the deployed output private (today's output is gated, and becomes public on a visibility change), and that the disclosure review must pass before any such change? [Privacy, Spec §Clarifications Q2, Plan §Operator-only items]
- [ ] CHK028 Is the token used to run snippets sourced from an operator-named location, with redaction of logs required? [Privacy, Research R-7, Tasks T029]

## Added after review (round 1)

- [ ] CHK029 Is a successful anonymous check defined by expected content (the page's own title or marker), not only by HTTP status, so a login or interstitial page cannot pass? [Measurability, Research §R-8, Tasks T010/T052a]
- [ ] CHK030 Are post-push preview checks required against actual protected child routes under `/vault/`, with the failure action (containment, report) stated? [Coverage, Plan §Research summary, Tasks T048b]
- [ ] CHK031 Are inventory rows for mixed files (`pages.ts`, `api/README.md`) scoped to exact string literals or sections rather than whole files? [Clarity, Data-model §Doc inventory, Tasks T006]
- [ ] CHK032 Does the spec distinguish feature completion from an implementation-ready hand-off when publication items remain outstanding? [Clarity, Spec §SC, Tasks T049]
- [ ] CHK033 Are evidence records (ledger, artifacts, links, disclosure) required to reference the final reviewed content revision, not an earlier draft? [Measurability, Data-model, Tasks T048/T052]

## Notes

- Items are checks on the requirement text, not on the implementation. Mark `[x]` when the cited section answers the question without inference; otherwise file the gap in analyze.
