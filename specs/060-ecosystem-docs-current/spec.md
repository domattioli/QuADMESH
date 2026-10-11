<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-11 skill=speckit-pipeline repo=quadmesh session=4e33ac09 -->
# Feature Specification: Ecosystem Docs Current

**Feature Branch**: `060-ecosystem-docs-current`
**Created**: 2026-10-11
**Status**: Clarified 2026-10-11
**Input**: Operator description: bring all human-facing documentation across CHILmesh, quadmesh, ADMESH (PyPI `admesh2D`) and the public-facing Valence consumer docs up to date; keep agent-intended docs out of PyPI and Zenodo artifacts; run four style passes on every human-intended doc; keep READMEs short; build an ecosystem wiki that presents the mesh registry only as "meshes come through Valence".

## Scope

Repos under `/Users/domattioli/Projects/MADMESHing`:

| Repo | Visibility | Pending local version | Public surfaces in scope |
|---|---|---|---|
| CHILmesh | public | chilmesh 1.5.5 (unreleased) | README, docs/, CHANGELOG, CITATION, GitHub wiki (empty today) |
| quadmesh | public | quadmesh 0.2.5 (unreleased) | README, docs/, CHANGELOG, CITATION, GitHub wiki (empty today) |
| ADMESH | public | admesh2D 1.0.5 (unreleased) | README, docs/ (mkdocs site), CHANGELOG, CITATION, `.zenodo.json`, existing GitHub wiki (11 pages, stale) |
| domattioli.github.io | **private** repo, public Pages output | n/a | New `/ecosystem/wiki/` section only (clarify Q2). The gated `/vault/wiki/` archive is out of scope. |
| Valence | **private** | n/a (not released) | Only the consumer-facing token service pages (`api/src/pages.ts`: landing, pending, token page) and the consumer API usage text (`api/README.md` routes section). Everything else in Valence is out of scope. |

Out of scope: releasing anything (releases wait for the operator's go), behavioural code changes (consumer-facing copy and example snippets inside `api/src/pages.ts` and `api/README.md` are in scope), `admesh3D`, `SegmentAnyMesh`, Valence's web app (`apps/`), Valence's operator runbooks.

## Clarifications

### Session 2026-10-11

- Q: Version wording in docs before the held releases ship? → A: Lead with the verified published version (chilmesh 1.5.0, quadmesh 0.2.0, admesh2D 1.0.0); show the pending one as "next: 1.5.5 / 0.2.5 / 1.0.5 (unreleased)"; no invented DOI or date.
- Q: Which repo hosts the canonical ecosystem wiki? → A: None of the three. The wiki lives in the `domattioli/domattioli.github.io` site (private repo, GitHub Pages) as pages or sections of that site. Repo READMEs and existing wikis link to it. ADMESH's stale wiki is an operator-only item. The plan must check whether Pages is enabled and published and which generator or layout the site uses, and must flag that a private repo's Pages output can still be public.
- Q: README length budget? → A: `write-readme` default, 150 lines by `wc -l`, or the per-repo `README line budget: N` override in `AGENTS.md`.
- Q: Humanizer pass, since no standalone skill exists? → A: DomI has no standalone humanizer skill (checked); run `write-like-scientist/references/upstream-humanizer.md` as its own recorded pass.
- Q: Delivery boundary for the implementing agent? → A: Edit repos on working branches and push the wiki/site; no Worker deploy and no releases.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A newcomer installs and runs one package from its README (Priority: P1)

A hydrodynamic modeller lands on the CHILmesh, quadmesh or ADMESH GitHub page or PyPI page. The README, within the `write-readme` line budget, tells them what the package does, which version is published and which is pending, how to install, one working example, and where the longer docs live. Every link resolves. No version string claims an unreleased version as published.

**Why this priority**: READMEs are the first and most-read doc; stale versions and broken links are the known defects.

**Independent Test**: Open each README from a clean checkout; run a link checker; grep for version strings; compare against `pyproject.toml` and `CHANGELOG.md`.

**Acceptance Scenarios**:

1. **Given** the CHILmesh README, **When** a reader looks for the version, **Then** the independently verified latest published release (PyPI and GitHub release checked 2026-10-11: chilmesh 1.5.0, quadmesh 0.2.0, admesh2D 1.0.0; quadmesh has no GitHub release) and the pending 1.5.5 are labelled per the Q1 policy; the version-specific DOI text names only a version that has a DOI; nothing presents 1.5.5 as shipped before it is.
2. **Given** the ADMESH README, **When** a reader looks for the version, **Then** 1.0.0 is no longer presented as the only or latest state; 1.0.5 appears with the Q1 label, and `.zenodo.json` follows the release-stage metadata policy in FR-007.
3. **Given** the quadmesh README, **When** a reader clicks the license's AI-usage link, **Then** the link resolves (the target file exists at the linked path).
4. **Given** any public README or doc, **When** a reader clicks any link to a GitHub repository, **Then** the target repository is public; no link points to `domattioli/Valence` or another private repo.
5. **Given** any of the three READMEs, **When** measured, **Then** it is at or under the agreed length budget and every section longer than the budget has moved to a linked doc.

---

### User Story 2 - A consumer gets a mesh token and uses it (Priority: P1)

A user of any of the three packages wants a test mesh. The docs say: sign in with GitHub, meet the account-age rule, receive a token at once, and use it from CHILmesh, quadmesh or ADMESH. No doc says a human approves the request in the default automatic flow.

**Why this priority**: The sign-up flow changed to automatic; the docs still describe manual approval, which actively misleads users.

**Independent Test**: Read the token service landing page, pending page and token page text, plus the consumer routes text in `api/README.md`; confirm the described flow matches `AUTO_APPROVE="true"`, `MIN_ACCOUNT_AGE_DAYS="30"`, `DAILY_DOWNLOAD_CAP="500"` in `api/wrangler.toml`.

**Acceptance Scenarios**:

1. **Given** the landing page, **When** read, **Then** it states: GitHub sign-in, account at least 30 days old, token issued immediately, 500 downloads per token per day.
2. **Given** the consumer-facing API usage text, **When** read, **Then** it contains no "approve", "pending operator approval" or "the operator then approves" step for the default flow. The pending page text is truthful in every state the code can render it (FR-004).
3. **Given** the token page's ADMESH snippet, **When** read, **Then** it is a real, tested ADMESH call, not the `PLACEHOLDER` comment that exists today.
4. **Given** any public doc that explains where meshes come from, **When** read, **Then** it says meshes come through Valence (a token-gated registry service) and nothing more about storage, provenance, hosting, or internal tooling.

---

### User Story 3 - A maintainer builds release artifacts and nothing agent-intended ships (Priority: P1)

A maintainer runs an sdist and wheel build for each package and produces the GitHub release tarball that Zenodo archives. None of the artifacts contains agent-intended files.

**Why this priority**: Shipping agent instructions in a scientific software release is a reputational and licensing hazard; ADMESH's `MANIFEST.in` and `.gitattributes` have no release-ignore block today.

**Independent Test**: For each repo, build sdist + wheel and `git archive HEAD`, list contents, and grep for the agent-doc denylist.

**Acceptance Scenarios**:

1. **Given** a fresh sdist, wheel and `git archive` of CHILmesh, quadmesh and ADMESH, **When** listed, **Then** none contains `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md`, `.claude/`, `.projectmem/`, `.specify/`, `specs/`, `.claude/handoffs/`, `docs/sessions/`, `docs/introspections/`, `*introspect*`, `facts.yml`, `.domi-pin`, `.release-ignore.toml`, `.zenodoignore`, `GEMINI.md`, `CODEX.md`, `.cursorrules` or other files named in the DomI release-ignore canon.
2. **Given** ADMESH, **When** its `MANIFEST.in` and `.gitattributes` are compared with `.release-ignore.toml`, **Then** both carry the generated `release-ignore:begin/end` block, as CHILmesh and quadmesh already do.
3. **Given** `.zenodo.json` (ADMESH) and `CITATION.cff` (all three), **When** read, **Then** they follow the release-stage metadata policy (FR-007): version equals the pending `pyproject.toml` version so the release-time preflight passes, no DOI or date is invented for it, and the description names no agent tooling.
4. **Given** quadmesh's rendered PyPI description, **When** the AI-usage link is followed, **Then** it resolves (absolute URL to the public GitHub file).

---

### User Story 4 - A reader finds the ecosystem wiki and understands how the four pieces fit (Priority: P2)

A reader opens the ecosystem wiki (on the domattioli.github.io site) from any of the three public repos. One wiki describes the whole ecosystem: what CHILmesh, quadmesh and ADMESH each do, how they depend on each other, how to get meshes (through Valence), and where each repo's own docs live.

**Why this priority**: Only ADMESH has a wiki, and it is stale (names ADMESH-Domains, MADMESHR and a 0.1.0 gate). CHILmesh and quadmesh wikis are enabled but empty.

**Independent Test**: Clone the site repo read-only; confirm the page set exists; grep for secret terms; run link check; confirm each README links to it.

**Acceptance Scenarios**:

1. **Given** the wiki, **When** opened, **Then** it has at minimum: Home, Ecosystem map, one page per package (CHILmesh, quadmesh, ADMESH), Getting meshes (Valence), Glossary, FAQ, Contributing/support.
2. **Given** any wiki page, **When** scanned against the DomI denylist and read in the disclosure review, **Then** it meets FR-010: no mesh provenance, storage or dataset identifiers, internal service components, private repo URLs or old registry names; published scientific attribution is allowed.
3. **Given** the stale ADMESH wiki pages, **When** the canonical wiki is ready, **Then** each stale page has a reviewed replacement or redirect stub prepared; these publish when the ADMESH wiki is enabled and publication is authorized, otherwise publication is recorded as outstanding and ADMESH's public docs link the canonical wiki. No prepared page names ADMESH-Domains, MADMESHR or a "0.1.0 gate" as current.

---

### User Story 5 - Every human doc passes the four style passes (Priority: P2)

A reviewer takes any human-intended doc in scope, changed by this feature or not, and checks it against the four style passes the operator named.

**Why this priority**: Consistent plain-English, scientist-voice prose is a standing operator rule (quadmesh constitution VI); it depends on the P1 content being correct first.

**Independent Test**: For every inventoried in-scope human document, record in a style-pass ledger which pass ran, with what skill, and the result.

**Skill resolution on disk** (checked 2026-10-11 under `~/.claude/skills` and `~/Projects/DomI/skills`):

| Operator's name | Skill on disk | Status |
|---|---|---|
| "ADHD English" | `asd-ste100-lens`, `adhd` layer (Step 5) | present |
| "ASD-ist English" | `asd-ste100-lens`, `ste` layer (Steps 1-4) | present |
| "humanizer" | no standalone skill; `write-like-scientist/references/upstream-humanizer.md` holds the upstream humanizer text | **missing as a separate skill**; run the embedded reference as its own recorded pass (clarify Q4) |
| "write-like-scientist" | `write-like-scientist` | present |

**Acceptance Scenarios**:

1. **Given** an in-scope human doc, **When** the ledger is read, **Then** it shows four separately recorded passes, the humanizer one citing `upstream-humanizer.md`.
2. **Given** an in-scope human doc, **When** the `write-like-scientist` tell scan is run, **Then** it reports zero hard-rule (G1-G17 hard) violations.

---

### Edge Cases

- A doc is both human- and agent-facing (for example `CONTRIBUTING.md`): treat as human-facing; agent-only material moves to `AGENTS.md`.
- A README section is factual but too long: move it to `docs/` and leave a one-line pointer. Obsolete or confidential facts are removed, not moved.
- A public doc names a registry mesh: keep names already public today, say "available through Valence", never link the Valence repo, never state origin.
- The benchmark docs cite `git clone https://github.com/domattioli/Valence` as the reproduction step (CHILmesh `docs/BENCHMARK.md:367`): replace with the token-based fetch path.
- Valence turns `AUTO_APPROVE` off later: the pending-page text must be truthful in every state the code can render it (FR-004).
- `.zenodo.json` exists only in ADMESH; CHILmesh and quadmesh rely on `CITATION.cff` plus the GitHub release. Do not add `.zenodo.json` where the release skill does not expect it unless the plan says so.
- ADMESH's wiki repository has pages but the repo setting `has_wiki=false` hides them; `mkdocs.yml` links "Ecosystem wiki" to domattioli.com. Enabling a wiki is an operator-only repo setting.
- Pending versions are unreleased while the docs are written; clarify Q1 sets whether docs lead with the published version or the pending one with an explicit label.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Docs MUST distinguish the published release from the pending development version (clarify Q1 sets the wording). Install examples MUST work against the version they name. No version-specific DOI, release date or "shipped" claim may be invented for an unreleased version. Dependency pins and historical references (benchmark rows, changelog entries) are exempt. `release_integrity.py preflight` (pyproject, CITATION.cff, .zenodo.json, CHANGELOG consistency) MUST pass for each repo at the pending version; the script creates no tag and falls back to `v<version>` when no exact tag exists.
- **FR-002**: Every hyperlink in public docs MUST resolve anonymously at completion; links to private GitHub repositories MUST be removed or replaced with public text ("available through Valence"). Two staged states are permitted during the work and reported, never passed: `outstanding` (a prepared wiki URL not yet reachable; inserted only when reachable, otherwise an operator item) and `pending-push` (a URL to a file that exists locally and is re-checked anonymously after its push).
- **FR-003**: quadmesh's README AI-usage link MUST resolve both on GitHub and in the rendered PyPI description (absolute URL, or a path PyPI rewrites). The target file MUST exist with human-facing content consistent with CHILmesh's `docs/AI-USAGE.md`.
- **FR-004**: Consumer-facing Valence text MUST describe the eligibility flow as the code implements it (`api/src/signup.ts`, `api/src/index.ts`), not only as `wrangler.toml` configures it: GitHub sign-in, account-age refusal under 30 days, token issued in the same visit when auto-approve is on, daily download accounting per token with its reset rule, and the pending (manual-approval) page worded so it is truthful in every state the code can render it (`AUTO_APPROVE=false`, or a pre-existing `pending` record on the fallback branch). Copy edits in `pages.ts` and `api/README.md` are allowed; behaviour changes are not.
- **FR-005**: The token page's ADMESH snippet MUST be an executable call verified against ADMESH's public API, stating whether it needs the unreleased 1.0.5.
- **FR-006**: For each public package, the built sdist, the built wheel, and a local `git archive HEAD` of the candidate commit (verifies the `export-ignore` rules that GitHub's tag zipball, the input to Zenodo's GitHub integration, also applies; it is a verification of the rules, not an identity claim about the final artifact) MUST contain none of the inventoried agent-intended files. `release_ignore.py --check` MUST report no drift in every repo; ADMESH MUST adopt the generated block in `MANIFEST.in`, `.gitattributes` and `.zenodoignore`. Verification is by listing built contents, not by reading config.
- **FR-007**: Release-stage metadata policy: `.zenodo.json` (ADMESH) and `CITATION.cff` (all three) carry the version in `pyproject.toml` so the release-time preflight passes, carry no invented DOI or release date for an unreleased version, and name no agent tooling. Human prose that cites a version-specific DOI cites only a DOI that exists.
- **FR-008**: Each README MUST meet the `write-readme` line budget (default 150 lines by `wc -l`, overridable per repo in `AGENTS.md`; clarify Q3) and carry the skill's required sections; moved material lives in `docs/` or the wiki and is linked from a doc map.
- **FR-009**: One canonical ecosystem wiki MUST exist with at least the page set in US4.1, hosted as a section of the `domattioli/domattioli.github.io` Astro site, which Cloudflare Pages deploys from `main` to domattioli.com (clarify Q2; GitHub Pages is configured but errored and unused). Links to it are published only once the pages are anonymously reachable. The three repos' READMEs and any existing GitHub wikis MUST link to it; none hosts a second copy. Fact: ADMESH's wiki repository holds 11 pages but the repository has `has_wiki=false`, so those pages are not reachable from the repo page today.
- **FR-010**: Public docs and wiki pages MUST describe mesh availability only as "meshes come through Valence" plus the approved consumer-facing token text. They MUST NOT disclose mesh provenance (origin institutions, data owners, acquisition path), storage host or dataset identifiers, internal service components, or private repository URLs. Published scientific attribution (for example the 2012 ADMESH paper) is not a secret. Mesh names already present in public docs today may stay; no new registry names are introduced. The secret-term denylist and the scan results MUST live outside the public repos (DomI), and the mechanical scan MUST be paired with a human disclosure review.
- **FR-011**: Every human-intended doc in scope (README, `docs/**/*.md`, CHANGELOG prose, CONTRIBUTING, SECURITY, wiki pages, token-service copy), changed or not, MUST receive four separately recorded reviews: ADHD (`asd-ste100-lens` `adhd` layer), ASD-STE (`asd-ste100-lens` `ste` layer), humanizer (`write-like-scientist/references/upstream-humanizer.md` applied as its own pass, since no standalone humanizer skill exists on disk), and `write-like-scientist` (voice + G1-G17 tell scan). The ledger records doc, pass, skill path, findings, correction and disposition.
- **FR-012**: Agent-intended docs (`AGENTS.md`, `CONTEXT.md`, `.claude/`, `.projectmem/`, specs, handoffs) are out of the style passes and MUST NOT be rewritten by this feature, except to keep them out of release artifacts and for the FR-014 move of `.specify/` and `specs/` to DomI.
- **FR-013**: No release, tag, PyPI upload or Zenodo deposit MAY happen in this feature. Edits land on each repo's default working branch per that repo's branch policy (quadmesh: `development`); the operator triggers releases later.
- **FR-014**: The feature MUST end by moving `.specify/` and `specs/` to DomI (`move_specs_to_domi.sh --apply`), as the operator brief and `speckit-pipeline` § Spec root require.

### Key Entities

- **Public surface**: a file or page that an unauthenticated reader can see (README, docs/, wiki, PyPI page, Zenodo record, token service pages).
- **Agent-intended doc**: a file whose reader is an AI agent (release-ignore canon list).
- **Secret term**: a word or URL on the provenance denylist.
- **Style-pass ledger**: table of (doc, pass, skill, date, result).

## Success Criteria *(mandatory)*

- **SC-001**: Zero version strings on any public inventory surface that claim an unreleased version as published, and zero stale "current release" strings (`check_versions.py`, fail-closed, plus `release_integrity.py preflight`).
- **SC-002**: Zero `broken|private|inaccessible|error` links in public docs; `outstanding` and `pending-push` rows are reported as open items, not passes (`check_links.py`).
- **SC-003**: Zero artifact-path-exclusion hits in the sdist, wheel and `git archive` of the three packages at their final candidate SHAs (`check_artifacts.py`, one `pass` row per artifact).
- **SC-004**: Zero secret-term hits in public docs and wiki (`check_disclosure.py`) and a recorded human disclosure review verdict for every public surface.
- **SC-005**: Every README at or under the length budget.
- **SC-006**: Style-pass ledger covers 100% of in-scope human docs with four recorded passes each; tell scan reports zero hard violations.
- **SC-007**: Token service text matches the implemented behaviour (account-age refusal, same-visit issuance, per-token daily accounting and reset, fallback) as read from `signup.ts` and `index.ts`, with the numbers from `wrangler.toml` (30 days, 500/day).

## Definition of done versus hand-off

Two states are distinguished.

**Implementation delivered.** Every SC gate passes on the final committed revisions; every push in T048a, T048b and T052 is verified or classified **prepared, blocked pending operator action** (a push the deploy-trigger check in T048a shows would deploy or publish); a feature with any blocked push is reported as **prepared**, not delivered; T052a has cleared every `pending-push` row to `ok`; the operator hand-off (T049) lists every remaining item. Items that remain **outstanding** by design (production visibility of the wiki, site `development` → `main` merge, ADMESH wiki setting and stubs, Worker deploy, releases, wiki-link insertions that need the wiki to be reachable) do not block this state; they are reported as open, never as passed checks.

**Public rollout complete.** Operator-only: the wiki is anonymously reachable in production, the `outstanding` wiki links are inserted and re-checked, and FR-009's link requirement is met. The implementer does not claim this state.

## Assumptions

- The version numbers in `pyproject.toml` (1.5.5, 0.2.5, 1.0.5) are the intended next releases; if they change before release, version strings are re-checked by `release_integrity.py preflight` at release time.
- The DomI `release-integrity` skill owns the release-ignore canon; this feature regenerates blocks, it does not invent a new list.
- The wiki is a section of the existing `domattioli.github.io` Pages site; ADMESH's mkdocs site stays and links to it.
- Valence stays private; only the two consumer-facing text surfaces named in Scope change.

## Delivery context (not a product requirement)

Operator direction: implementation by a gpt-6.1-sol lead with a haiku worker after operator approval; Opus and Sol co-author wiki content; Fable orchestrates only. Fable makes no pushes or network writes.

## Open questions for clarify

All five resolved in `## Clarifications`.
