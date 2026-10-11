<!-- provenance: author=domattioli model=claude-fable-5-1 effort=low date=2026-10-10 skill=speckit-analyze repo=quadmesh session=4e33ac09 -->
# Data Model: feature 056

The feature manipulates documents and metadata, not runtime data. Entities below are the files and the invariants that bind them.

## Entities

### LongFormDocument (`docs/algorithm.md`)
- Sections (ordered): plain summary; thesis algorithm; port as implemented; thesis-vs-port table; experimental fallback; Blossom-Quad relation; parity status; references.
- Invariants: every named function carries a `file:line` or function pointer; "faithful"/"matching" appear only as removed names; the zero-interior-residual-triangle invariant is stated once with its gate test; Blossom-Quad comparison references only the fallback section.
- Lifecycle: created; `docs/algorithm_writeup.md` folded in then deleted; passes writing stack; linked from README.

### ReadmeSurface (`README.md`)
- Fields: tagline; value statements (5); status banner; install; ENPAC quality table (verbatim); citation block; DOI badge.
- Invariants: links to LongFormDocument; no restated algorithm sections; DOI = concept DOI; authors = CITATION.cff authors; no CITATION TODO comment.

### ReleaseMetadata
- Members: `src/quadmesh/__init__.py.__version__`, `pyproject.toml.version`, `CITATION.cff.version`, `CHANGELOG.md` top entry.
- Invariant: all equal `0.3.0`; changelog top entry is `[0.3.0] - Unreleased`; `[0.2.1]` retained with never-tagged note.

### CitationRecord (`CITATION.cff`)
- Fields: authors [Mattioli D.D., Kubatko E.J.]; version 0.3.0; date-released unchanged (`2026-07-13`, comment: set by `release` skill); identifiers.doi = `10.5281/zenodo.20350483`; abstract (prose, writing stack applies); preferred-citation (thesis, unchanged).
- Invariant: validates as CFF 1.2.0; author list equals README author list.

### DoiGuard (`tests/test_release_metadata.py`)
- Field: `CONCEPT_DOI = "10.5281/zenodo.20350483"`.
- Invariant: fails on any other DOI in `CITATION.cff` or `README.md`; passes in `pytest tests/`.

### InstallNotes (`AGENTS.md:32`, `scripts/dev_setup.sh`, README install section)
- Invariant: all state chilmesh installs from PyPI; sibling checkout is optional; absence of sibling checkout is not an error.

### PackageDescription (`pyproject.toml.description`, GitHub repo description)
- Invariant: one sentence each; consistent with README first value statement; GitHub description change is an operator or `gh repo edit` step recorded in tasks.

## Relationships

- ReadmeSurface -> LongFormDocument (link).
- ReadmeSurface.authors == CitationRecord.authors.
- ReadmeSurface.doi == CitationRecord.doi == DoiGuard.CONCEPT_DOI.
- ReleaseMetadata members mutually equal.
- Every prose entity -> WritingStackPass (voice, Golden rule, STE/ADHD lens, tell scan, fact audit) before done.
