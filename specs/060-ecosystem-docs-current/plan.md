<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-11 skill=speckit-pipeline repo=quadmesh session=4e33ac09 -->
# Implementation Plan: Ecosystem Docs Current

**Branch**: `060-ecosystem-docs-current` | **Date**: 2026-10-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/060-ecosystem-docs-current/spec.md` (clarified 2026-10-11)

## Summary

Bring every human-facing doc in CHILmesh, quadmesh, ADMESH and the Valence consumer token surfaces up to date (published-first version wording, working links, no private-repo links, automatic sign-up flow), prove that no agent-intended file ships in sdist, wheel or tag archive, run four recorded style passes on every in-scope human doc, cut each README to the `write-readme` budget, and publish one ecosystem wiki as a public section of the `domattioli.github.io` Astro site. No release, tag, PyPI upload, Zenodo deposit or Cloudflare Worker deploy happens in this feature.

## Technical Context

**Language/Version**: Markdown; Python 3 scripts (DomI `release_integrity.py`, `release_ignore.py`, `doc_provenance.py`); Astro 5 + Node >= 22 for the site; TypeScript string literals in `Valence/api/src/pages.ts`.
**Primary Dependencies**: DomI skills `write-readme`, `write-like-scientist` (+ `references/upstream-humanizer.md`, `references/ai-tells-scan.md`), `asd-ste100-lens`, `release-integrity`, `agent-doc-sweep`; `gh` (read-only except branch pushes by the implementer); `python -m build`; `git archive`; a link checker (`lychee` if installed, else a stdlib script).
**Storage**: Files in five git repos. Secret-term denylist and scan results in DomI (`specs/consumers/quadmesh/specs/060-ecosystem-docs-current/private/`), never in a public repo.
**Testing**: `pytest` unchanged; new doc gates are shell/python checks: version grep, link check, artifact listing grep, README `wc -l`, denylist scan, `release_ignore.py --check`, `release_integrity.py preflight` (no-tag mode), `npm run build` + `astro check` for the site.
**Target Platform**: GitHub (README render), PyPI (README render), Zenodo (tag zipball), Cloudflare Pages (site), Cloudflare Worker (token pages: copy only, deployed later by the operator).
**Project Type**: multi-repo documentation and packaging-hygiene change.
**Performance Goals**: n/a.
**Constraints**: releases on hold; Fable never pushes; implementer may push working branches and the site repo; no Worker deploy; Valence stays private; a private repo's Pages output is still public once the gate is lifted.
**Scale/Scope**: 3 READMEs (268, 311, 288 lines today), about 45 `docs/*.md` files across the three repos, 2 Valence copy surfaces, 1 site section of about 8 pages, 3 packaging configs.

## Constitution Check

Quadmesh constitution (v0.2.0) gates that apply:

| Principle | Gate | Status |
|---|---|---|
| VI Writing Stack For Human-Facing Docs | `write-like-scientist` voice 1-10, Golden rule G1-G17, `asd-ste100-lens` STE + ADHD, tell scan, in that order | PASS: FR-011 orders the passes this way and adds the humanizer reference as its own recorded pass |
| Governance: spec drives implementation | Deviations land in spec first | PASS |
| I-V (algorithm principles) | n/a, no code behaviour changes | n/a |

Repo rules: quadmesh default branch `development`; CHILmesh, ADMESH follow their own `AGENTS.md`; never push `main`; no `CLAUDE.md` anywhere. ADMESH `AGENTS.md` is read, not edited, except to add a `README line budget` line only if the operator wants an override (default: no override).

Re-check after design: PASS (no new violations).

## Research summary (see research.md)

- **Site**: `domattioli/domattioli.github.io` is private; GitHub Pages is configured `legacy` from `main:/` but `status: errored` and `https://domattioli.github.io/` returns 404. The live deploy is Cloudflare Pages from `main` to `https://domattioli.com` (returns 403: a temporary site-wide password gate in `functions/_middleware.ts`). Generator: Astro 5, static output, content collections in `src/content/`. An archived 15-page wiki already exists under `src/content/vault/wiki/` behind Cloudflare Access plus the gate; it names old versions (chilmesh 1.2.2, admesh2D 0.5.1), links private repos (Valence, MADMESHR) and carries a `status: Private` Valence page. `/ecosystem/` is preview-only (`showEcosystem()` false on the `main` build) and holds an overview plus the playground.
- **Decision**: build the public wiki as a new content collection `src/content/ecosystem-wiki/*.md` rendered at `/ecosystem/wiki/<slug>/` through a `[...slug].astro` route and the existing `DocsLayout`. Leave `vault/wiki` untouched and gated (it is not a public surface). Isolation is proven on the built output, not assumed, in two steps. Pre-push (local): build `dist/` with and without `CF_PAGES_BRANCH=main`, inspect HTML, sitemap, any search index or feed, client bundles and shared navigation, and confirm the new collection, route and layout do not reference or enumerate `vault/*`. Before the first push of a build that contains vault output, verify that Cloudflare Access covers the preview hostnames (`*.pages.dev`) as well as `domattioli.com`; if coverage cannot be confirmed, protection is unverified: the implementer stops and reports to the operator instead of pushing, and reports exposure only if an anonymous request to an existing preview URL actually returns vault content. Post-push: test anonymous access to `/vault/*` and `/ecosystem/wiki/*` on the preview URL of the pushed candidate and record the result. The production password gate is never assumed to protect previews. Do not copy text from `vault/wiki` into public pages without the disclosure review; write new pages from the public READMEs and docs. The GitHub Pages build is not the publishing path; the implementer does not touch it.
- **Public visibility is operator-gated twice**: `showEcosystem()` hides `/ecosystem/*` on production builds, and `_middleware.ts` passwords the whole site. Both flips are operator decisions outside this feature. The plan ships the pages on the site's `development` branch (site policy: work on `development`, promote to `main` by pull request, never push `main`), so they appear on the Cloudflare preview build of that branch. Canonical links (`https://domattioli.com/ecosystem/wiki/...`) are prepared in the READMEs but published only when their destinations are anonymously reachable; until then the README carries no wiki link and the link gate records gated publication as outstanding, not as passed.
- **Versions** (verified on PyPI and GitHub releases 2026-10-11): chilmesh 1.5.0 (GitHub v1.5.0), quadmesh 0.2.0 (no GitHub release), admesh2D 1.0.0 (GitHub v1.0.0). Pending in `pyproject.toml`: 1.5.5, 0.2.5, 1.0.5. Wording per Q1: "Current release: 1.5.0. Next: 1.5.5 (unreleased)."
- **Packaging**: CHILmesh and quadmesh carry the generated release-ignore block in `MANIFEST.in` and `.gitattributes`; ADMESH has `.release-ignore.toml` and `.zenodoignore` but no generated block in `MANIFEST.in` or `.gitattributes`, and `.zenodo.json` says 1.0.0 with `pip install admesh2D==1.0.0` in its description. ADMESH also tracks `CONTEXT.md` (agent glossary) and `.projectmem/`, neither export-ignored today.
- **Valence consumer copy**: `api/src/pages.ts` landing page is nearly right (30 days, limited downloads) but omits the number and says nothing about immediate issuance; `pendingPage` says "pending operator approval"; `tokenPage` ADMESH snippet is a `PLACEHOLDER`. `api/README.md` is an operator runbook; only its route table and the one line "GitHub sign-up and one-time token pickup" are consumer-facing. Code: `signup.ts` auto-issues when `AUTO_APPROVE` is true (default true), refuses accounts under `MIN_ACCOUNT_AGE_DAYS` (30), `index.ts` counts downloads per token digest per UTC day against `DAILY_DOWNLOAD_CAP` (500).
- **ADMESH API for the snippet**: to be verified by the implementer against `admesh.__all__` in the local checkout (`admesh.load_domain_from_registry` is exported in `__all__`; argument form and token handling still to confirm by running it). Recorded as research item R-7.
- **Skills**: `asd-ste100-lens` (ste, adhd), `write-like-scientist`, `write-readme`, `release-integrity`, `agent-doc-sweep` all present under `~/.claude/skills` and `~/Projects/DomI/skills`. No standalone humanizer (Q4 resolved).

## Project Structure

### Documentation (this feature)

```text
specs/060-ecosystem-docs-current/
├── spec.md
├── plan.md               # this file
├── research.md           # R-1..R-8 decisions
├── data-model.md         # ledger, inventory, denylist, link-audit schemas
├── quickstart.md         # how to run every gate locally
├── checklists/requirements.md
├── debate-log.md
└── tasks.md              # /speckit-tasks output
```

Private artifacts (denylist, scan output, disclosure-review notes) are written to `<DomI>/specs/consumers/quadmesh/specs/060-ecosystem-docs-current/private/` only.

### Touched paths by repo

```text
CHILmesh/            README.md, docs/*.md (inventory), docs/BENCHMARK.md (Valence clone step), CITATION.cff, CHANGELOG.md prose
quadmesh/            README.md, docs/*.md, docs/AI-USAGE.md (new), CITATION.cff, CHANGELOG.md prose
ADMESH/              README.md, docs/*.md (mkdocs sources), mkdocs.yml (wiki link), CITATION.cff, .zenodo.json,
                     MANIFEST.in, .gitattributes, .zenodoignore (generated blocks), zenodo/ (check contents)
Valence/             api/src/pages.ts (copy only), api/README.md (consumer lines only)
domattioli.github.io/ src/content/ecosystem-wiki/*.md (new), src/content.config.ts (collection),
                     src/pages/ecosystem/wiki/[...slug].astro (new), src/pages/ecosystem/[...root].astro (sidebar link)
DomI/                specs/consumers/quadmesh/specs/060-.../private/{denylist.txt,scan-*.txt,disclosure-review.md}; final spec move
```

**Structure Decision**: no new packages or tooling; each repo keeps its layout. The one structural addition is the `ecosystem-wiki` content collection in the site repo, chosen over (a) ungating `vault/wiki` (contains private material and stale facts) and (b) GitHub wikis per repo (Q2 ruled them out).

## Work breakdown (ordered; tasks.md expands)

1. **Inventory and gates first.** Build the doc inventory (every human-facing `.md` and copy surface in scope), the link audit, the version-string audit and the artifact listing for the current state, so every later change is measured against a baseline. Write the denylist in DomI.
2. **Packaging hygiene (US3).** ADMESH: regenerate release-ignore blocks with `release_ignore.py generate` (the DomI canon already names `CONTEXT.md` and `.projectmem/`), update `.zenodo.json` to the FR-007 policy. All three repos, on a committed candidate revision whose SHA is recorded: `release_ignore.py --check`, `python -m build --outdir <fresh tmp dir>`, `git archive <sha>`, list and grep against the artifact-path exclusion list. Fix, commit, and repeat on the new candidate until zero hits. After the final commit of the feature (including the spec move), repeat the affected gates on the final candidate before pushing.
3. **Content truth (US1, US2).** Version wording per Q1 in README, CITATION, CHANGELOG top, docs index; remove or replace private links (Valence, MADMESHR, QuADMesh-MATLAB if private); `docs/BENCHMARK.md` reproduction step becomes the verified `chilmesh.registry` call (`fetch_mesh_bytes(name)`; `fetch_mesh` does not exist, so the token page's CHILmesh snippet is wrong today as well); quadmesh `docs/AI-USAGE.md` created and linked by absolute URL; Valence copy per FR-004/FR-005 with the ADMESH snippet verified by running it.
4. **README diet (US1, FR-008).** Apply `write-readme`: move material to `docs/`, add doc map, hit the 150-line budget, link the wiki URL.
5. **Wiki (US4).** Author the 8 pages (Home, Ecosystem map, CHILmesh, quadmesh, ADMESH, Getting meshes through Valence, Glossary, FAQ + Contributing/support) in the site repo; wire the collection and route; `npm run build` on a preview branch; prepare canonical links for the three READMEs and ADMESH `mkdocs.yml` (published per the visibility rule above), and prepare a replacement or redirect stub for every one of ADMESH's 11 stale wiki pages (publication operator-only, US4.3). Opus and Sol co-author page text; the disclosure review runs before any push.
6. **Style passes (US5).** For every inventoried doc, the single sequence in data-model.md: write-like-scientist voice, Golden rule, humanizer reference, STE, ADHD, tell scan; one ledger row per pass (four passes).
7. **Verification and hand-off.** Re-run every gate from quickstart.md on the final candidate revision of each repo; produce the operator item list, grouped as: production visibility of the wiki, site `development` → `main` PR, ADMESH wiki settings and stub publication, Valence Worker deploy, releases; commit per repo on working branches; final task moves specs to DomI, then the gates run once more.

## Operator-only items (flag, do not perform)

- Production visibility: the operator decides the minimum visibility change that exposes `/ecosystem/wiki/` while keeping vault access controls (today: `showEcosystem()` hides `/ecosystem/*` on `main` builds and `functions/_middleware.ts` passwords the site). Until then the wiki is reachable only on the `development` preview build. The site repo is private; its Pages output becomes public the moment visibility changes, so the disclosure review must pass first.
- Merge the site `development` → `main` pull request (production deploys from `main`).
- Re-enable ADMESH's GitHub wiki (`has_wiki=false`) or leave it off; if on, push the prepared stub.
- Deploy the Valence Worker so the copy change goes live.
- Run the three releases, which re-check version strings via `release_integrity.py preflight`.

## Complexity Tracking

No constitution violations to justify.
