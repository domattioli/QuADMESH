<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-11 skill=speckit-pipeline repo=quadmesh session=4e33ac09 -->
# Data model: 060-ecosystem-docs-current

Every evidence row carries `section` (from the inventory) and `content_sha`: the commit of the repo the content belongs to, or `worktree:<sha256 of the file>` for content not yet committed (for example DomI stubs). `check_style_coverage.py` (T012) accepts a row for the final revision only when either its `content_sha` is that revision, or the file's blob hash (`git hash-object`) at the final revision equals the blob hash at the row's `content_sha` (verified carry-forward). For `worktree:` rows the test is a direct SHA-256 comparison of the current file bytes against the recorded digest. Rows that fail both tests are superseded, not counted. Agent-side bookkeeping only; every file lives in `<DomI>/specs/consumers/quadmesh/specs/060-ecosystem-docs-current/private/`; nothing here ships or enters a public repo.

## Doc inventory (`inventory.csv`, DomI private dir)
`repo, path, section, audience (human|agent|mixed), surface (readme|docs|changelog|wiki|copy), in_style_scope (bool), notes`
`section` scopes a mixed file to exact string literals or headings (for example `pages.ts: landingPage, pendingPage, tokenPage`; `api/README.md: ## Routes`). Rule: `mixed` is treated as human within `section`; agent-only material moves to `AGENTS.md`.

## Style-pass ledger (`style-ledger.csv`)
`repo, path, section, content_sha, pass (adhd|ste|humanizer|wls), skill_path, date, findings, correction, disposition (clean|fixed|deferred+issue)`
Four rows per inventoried human doc. Order of application: wls voice, Golden rule, humanizer reference, ste, adhd, tell scan. A `deferred` row never satisfies SC-006; hard G1-G17 violations must be `fixed`.

## Link audit (`links.csv`)
`repo, path, section, content_sha, line, url, kind (relative|github|external|wiki), status (ok|broken|private|inaccessible|outstanding|pending-push|error), action`
Per R-8: `private` only when `gh api repos/<owner>/<repo>` returns a visibility other than `public`; `inaccessible` for 404 without a visibility answer; `outstanding` for a prepared wiki URL not yet anonymously reachable; `pending-push` only for a URL listed in `pending-push-targets.txt` whose target file exists locally in the inventoried repo but is not yet pushed; `error` for any lookup failure. `broken`, `private`, `inaccessible` and `error` fail the gate; `outstanding` and `pending-push` are reported, never passed, and must be re-checked anonymously after the push.

## Version audit (`versions.csv`)
`repo, path, section, content_sha, line, string, class (published|pending|historical|dependency), ok (bool)`

## Artifact-path exclusion list (`artifact-exclusions.txt`)
The DomI release-ignore canon plus each repo's `.release-ignore.toml` extension, as path patterns. Distinct from the secret-term denylist.

## Artifact inspection (`artifacts.csv`)
`repo, candidate_sha, artifact (sdist|wheel|archive), member_count, exclusion_hits, status (pass|fail|error)`
One row per artifact per candidate; a build or listing error is `error`, never `pass`.

## Secret-term denylist (`denylist.txt`, DomI private only)
One pattern per line: provenance terms, data-owner names, storage host and dataset identifiers, internal component names, private repo URLs, retired registry names. Paired with a human disclosure review note per wiki page (`disclosure-review.md`).

## Wiki page (`src/content/ecosystem-wiki/<slug>.md`)
Frontmatter: `title, summary, order, updated`. Required slugs: `index, ecosystem, chilmesh, quadmesh, admesh, getting-meshes, glossary, faq`.
