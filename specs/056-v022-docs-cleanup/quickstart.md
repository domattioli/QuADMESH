<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-plan repo=quadmesh session=4e33ac09 -->
# Quickstart: verifying feature 056

Run from `/Users/domattioli/Projects/MADMESHing/quadmesh` with `.venv` active.

## 1. Versions agree

```bash
grep -n '__version__' src/quadmesh/__init__.py        # 0.3.0
grep -n '^version' pyproject.toml                      # 0.3.0
grep -n '^version' CITATION.cff                        # 0.3.0
sed -n 7,9p CHANGELOG.md                               # [0.3.0] - Unreleased
grep -rn '0\.2\.[012]' --include='*.py' --include='*.toml' --include='*.cff' --include='*.md' . \
  | grep -v '^./CHANGELOG.md\|^./specs\|^./.specify\|^./docs/sessions'   # expect no output
```

## 2. Stale strings gone

```bash
grep -rn '_match_faithful' . --exclude-dir=.git --exclude-dir=specs --exclude-dir=.specify   # none
grep -n 'not on PyPI\|not available from PyPI' AGENTS.md scripts/dev_setup.sh                 # none
grep -n 'TODO: Add CITATION.cff' README.md                                                     # none
test ! -e docs/algorithm_writeup.md && test -e docs/algorithm.md && echo OK
```

## 3. DOI and citation

```bash
grep -n 'zenodo\.' README.md CITATION.cff            # only 10.5281/zenodo.20350483
grep -n -A1 'family-names' CITATION.cff              # Mattioli then Kubatko
pytest tests/test_release_metadata.py -q
```

## 4. Behaviour unchanged

```bash
pytest tests/test_no_interior_tris.py tests/test_parity.py -q
pytest tests/ -q
git diff --stat -- src/ | grep -v __init__.py          # expect nothing else under src/
```

## 5. Document content

Open `docs/algorithm.md` and confirm, by reading:
- a section labelled as the thesis algorithm describing the per-layer sweep as the default;
- a section labelled as the experimental fallback naming `_match_tris_to_quads`, `_layer_priority`, `_sweep_pairs`, fold-seam forbidden edges, augmenting-path fixup, and when it runs;
- a Blossom-Quad section that says the thesis is unrelated and compares only the fallback, citing Remacle et al. 2012, IJNME 89(9);
- a parity section stating `tests/test_parity.py` pins a Python self-baseline;
- "faithful" appears only as a removed method name or in "faithfulness invariant".

Confirm `README.md` links `docs/algorithm.md`, carries the five value statements, and retains the ENPAC table.

## 6. Writing stack

For each file in spec FR-021:

```bash
python3 ~/.claude/skills/write-like-scientist/scripts/banned_words.py --mode prose <file>   # exit 0
```

Then the Haiku scanner JSON for each file is an empty array (or only `weighted_alone: true` entries), and the fact add/drop audit notes zero added and zero dropped claims. Record both results in the task log.
