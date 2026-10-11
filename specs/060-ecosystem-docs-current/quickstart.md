<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-11 skill=speckit-pipeline repo=quadmesh session=4e33ac09 -->
# Quickstart: run every gate locally

Prerequisites: bash 3.2+ (macOS default is fine; no associative arrays used), python3 >= 3.11, `gh` authenticated read-only, `npm` with Node >= 22, the three repos and a `development` clone of the site. Gates are fail-closed: a build, listing or lookup error fails the gate; only a clean inspection passes. Bookkeeping lives in `$PRIV` (DomI private dir), never in a public repo. The six `check_*.py` helpers are written in the foundational tasks and stored in `$PRIV`; each exits non-zero on any failure or error and prints the offending rows.

```bash
set -euo pipefail
DOMI=~/Projects/DomI; RI=$DOMI/skills/release-integrity/scripts
PRIV=$DOMI/specs/consumers/quadmesh/specs/060-ecosystem-docs-current/private
MM="$HOME/Projects/MADMESHing"                           # CHILmesh, quadmesh, ADMESH, Valence checkouts
SITE=${SITE:-$HOME/Projects/domattioli.github.io}      # development-branch clone; set SITE= to override
pkg() { case "$1" in CHILmesh) echo chilmesh;; quadmesh) echo quadmesh;; ADMESH) echo admesh2D;; esac; }

for r in CHILmesh quadmesh ADMESH; do
  cd ~/Projects/MADMESHing/$r
  test -z "$(git status --porcelain)" || { echo "FAIL $r: dirty tree"; exit 1; }
  sha=$(git rev-parse HEAD)
  python3 $RI/release_ignore.py --check
  python3 $RI/release_integrity.py preflight --package "$(pkg $r)"   # no tag created; falls back to v<version>
  # builds sdist+wheel into a fresh tmp dir, git-archives $sha, matches members path-aware against the
  # exclusion patterns (fnmatch on normalized paths, archive root stripped), writes one row per artifact
  # (sdist|wheel|archive) with status pass|fail|error to $PRIV/artifacts.csv, exits non-zero on any fail|error
  python3 $PRIV/check_artifacts.py --repo . --sha "$sha" --exclusions "$PRIV/artifact-exclusions.txt" --out "$PRIV/artifacts.csv"
  cap=$(grep -oiE 'README line budget: *[0-9]+' AGENTS.md 2>/dev/null | grep -oE '[0-9]+$' || echo 150)
  lines=$(wc -l < README.md | tr -d ' '); [ "$lines" -le "$cap" ] || { echo "FAIL $r: README $lines/$cap"; exit 1; }
  curl -fsS "https://pypi.org/pypi/$(pkg $r)/json" | python3 -c 'import sys,json;print(json.load(sys.stdin)["info"]["version"])' > "$PRIV/published-$(pkg $r).txt"
  python3 -c 'import tomllib;print(tomllib.load(open("pyproject.toml","rb"))["project"]["version"])' > "$PRIV/pending-$(pkg $r).txt"
done
# versions: one inventory-driven run over every public surface (three repos, Valence copy, site wiki pages)
python3 $PRIV/check_versions.py --inventory "$PRIV/inventory.csv" --published-dir "$PRIV" --out "$PRIV/versions.csv"

# inventory-driven gates (cover CHILmesh, quadmesh, ADMESH, Valence copy surfaces and site wiki pages alike)
python3 $PRIV/check_links.py --inventory "$PRIV/inventory.csv" --out "$PRIV/links.csv"            # fails on broken|private|inaccessible|error; wiki URLs -> outstanding; listed unpushed targets -> pending-push (both reported, never passed)
python3 $PRIV/check_style_coverage.py --inventory "$PRIV/inventory.csv" --ledger "$PRIV/style-ledger.csv" \
  --final-sha "CHILmesh=$(git -C "$MM/CHILmesh" rev-parse HEAD)" --final-sha "quadmesh=$(git -C "$MM/quadmesh" rev-parse HEAD)" \
  --final-sha "ADMESH=$(git -C "$MM/ADMESH" rev-parse HEAD)" --final-sha "Valence=$(git -C "$MM/Valence" rev-parse HEAD)" --final-sha "site=$(git -C "$SITE" rev-parse HEAD)"
  # 4 rows per human doc, none deferred, hard tells fixed; rows count only for the final revision or an unchanged blob (data-model content_sha rule). Rerun after T051 changes quadmesh (T052).
python3 $PRIV/check_disclosure.py --inventory "$PRIV/inventory.csv" --denylist "$PRIV/denylist.txt"        # fails on any hit in a public surface

# site, pre-push: build both ways, type-check, prove vault isolation and required routes on the built output
cd "$SITE" && git rev-parse --abbrev-ref HEAD | grep -qx development
npm ci
npx astro check
# preview-mode build, then the isolation checker; each is its own command so set -e stops on any failure.
# The checker inspects every file under dist/ (HTML, sitemap*.xml, feeds, search indexes, JS/CSS bundles),
# fails on any reference to vault/ outside dist/vault/, on any vault page title or summary string copied
# into a non-vault file (strings loaded from src/content/vault/**/frontmatter), and on a missing required route.
CF_PAGES_BRANCH=development npm run build
python3 $PRIV/check_site_isolation.py --dist dist --vault-src src/content/vault --nav-scope ecosystem/wiki \
  --require-routes ecosystem/wiki/index.html ecosystem/wiki/{ecosystem,chilmesh,quadmesh,admesh,getting-meshes,glossary,faq}/index.html
CF_PAGES_BRANCH=main npm run build
python3 $PRIV/check_site_isolation.py --dist dist --vault-src src/content/vault --nav-scope ecosystem/wiki
# site, post-push (implementer, after the development push): anonymous GET of /vault/ and /ecosystem/wiki/ on the
# candidate's preview URL; record status codes in $PRIV/site-preview-check.md. Before the FIRST push, confirm
# Cloudflare Access covers *.pages.dev; if coverage cannot be confirmed, protection is unverified: stop and report, do not push.
```

Expected result: every command exits 0; `links.csv` holds only `ok`, `outstanding` and `pending-push` (the last two re-checked with `check_links.py --anonymous` after the pushes); `artifacts.csv` has three `pass` rows per repo for the final candidate SHA.
