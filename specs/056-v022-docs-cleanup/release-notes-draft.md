# QuADMESH 0.3.0: algorithm documentation, concept DOI, and metadata alignment

Release 0.3.0 changes documentation and metadata only. `tri2quad` output is unchanged, and the full test suite passes without test edits. This draft covers feature 056; feature 057 adds its own notes before the joint release.

## Documentation

- `docs/algorithm.md` describes the thesis per-layer sweep, which is the default path, and the port as implemented, with `file:line` pointers.
- The same document lists seven differences between the thesis and the port. One is an open defect: the per-layer sweep treats the innermost layer as the boundary layer.
- The global layer-priority matcher is labelled an experimental fallback. It runs on layerless meshes and on elements that no layer covers. Section 6 compares this fallback, and only this fallback, with Blossom-Quad (Remacle et al. 2012).
- MATLAB parity is stated as port intent. `tests/test_parity.py` pins a Python baseline because MATLAB element counts were never captured.
- `docs/algorithm_writeup.md` is removed; its content is section 5 of `docs/algorithm.md`.

## README and package metadata

- The README opens with five statements about what the conversion keeps and adds, and links to `docs/algorithm.md`.
- The PyPI description is one sentence that matches the README.

## Citation and release metadata

- `CITATION.cff` lists Ethan J. Kubatko (Ohio State University) as second author.
- `CITATION.cff` and the README cite the Zenodo concept DOI 10.5281/zenodo.20350483, which resolves to every version. `tests/test_release_metadata.py` fails if another Zenodo DOI appears.
- Version 0.3.0 is set in `pyproject.toml`, `src/quadmesh/__init__.py`, and `CITATION.cff`. Version 0.2.1 was never tagged; its changes ship here.

## Developer setup

- `scripts/dev_setup.sh` installs chilmesh from PyPI (`chilmesh>=1.2.1`). Set `QUADMESH_CHILMESH_SRC=<path>` to use a local CHILmesh checkout.
