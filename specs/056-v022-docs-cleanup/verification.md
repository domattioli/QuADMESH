# Verification: feature 056 (2026-10-10)

| Check | Command | Result |
|---|---|---|
| Test suite | `.venv/bin/pytest -q` | 115 passed, 62 skipped (baseline 111 passed, 61 skipped; +4 passed, +1 skipped from `tests/test_release_metadata.py`) |
| Guard test | `.venv/bin/pytest -q tests/test_release_metadata.py` | 4 passed, 1 skipped (no `.zenodo.json`) |
| Stale versions | `grep -rn '0\.2\.[012]' src/quadmesh/__init__.py pyproject.toml CITATION.cff` | no output |
| Old DOI | `grep -rn 20351165 CITATION.cff README.md` | no output |
| Source diff | `git diff --stat -- src/` | `src/quadmesh/__init__.py` only |
| CITATION.cff | YAML parse (ruby) + fields | version 0.3.0; authors Mattioli, Kubatko; doi and identifier = concept DOI; cffconvert not installed |
| Old write-up | `test -e docs/algorithm_writeup.md` | deleted; `docs/algorithm.md` present |
| Banned words | `banned_words.py --mode prose` on algorithm.md, README.md, release notes, changelog entry, short surfaces | exit 0 each |
| SC-001 read-through | `docs/algorithm.md` section 3.1 | layered mesh: `_quadmesh_plus_per_layer`; layerless mesh: `_match_tris_to_quads` fallback |
| Residual SC-002 hits | `grep -rln 'not on PyPI\|_match_faithful'` | CONTRIBUTING.md:50, facts.yml, docs/parallelization-strategy-memo.md, docs/sessions/session-018.md (not task-named; left) |
