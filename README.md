<p align="center">
  <img src="videos/quadmesh_logo.gif" alt="QuADMESH logo — triangles in, quads out" width="680">
</p>

<h1 align="center">QuADMESH</h1>

<p align="center">
  <strong>A Quadrangular ADvanced, automatic unstructured MESH generator for 2D shallow-water models.</strong><br>
  Python port of the MATLAB QuADMESH library and a Pythonic API.
</p>

<p align="center">
  <strong><a href="https://scholar.google.com/citations?user=IBFSkOcAAAAJ&hl=en">Dominik Mattioli</a><sup>1†</sup>, <a href="https://scholar.google.com/citations?user=mYPzjIwAAAAJ&hl=en">Ethan Kubatko</a><sup>2</sup></strong><br>
  <sup>†</sup>Corresponding author | <sup>1</sup>Unaffiliated | <sup>2</sup>Ohio State University (CHIL)
</p>

---

## Badges

<p align="center">
  <a href="https://github.com/domattioli/QuADMESH/actions/workflows/tests.yml"><img src="https://github.com/domattioli/QuADMESH/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20NC%20%2B%20No--AI-red.svg" alt="License"></a>
  <a href="https://doi.org/10.5281/zenodo.20351165"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.20351165.svg" alt="DOI"></a>
  <a href="https://github.com/domattioli/QuADMESH/issues"><img src="https://img.shields.io/github/issues/domattioli/QuADMESH.svg" alt="Open issues"></a>
</p>

<!-- TODO: Add PyPI badge once v0.1.0 is published -->

---

## Table of Contents

- [Status & Roadmap](#status--roadmap)
- [Installation](#installation)
- [Repository Layout](#repository-layout)
- [Quick Start](#quick-start)
- [Citation](#citation)
- [Related Projects](#related-projects)
- [Contact](#contact)
- [License](#license)

---

## Status & Roadmap

**Current status (June 2026):** the QuADMESH+ layer-ordered tri-to-quad conversion is implemented and is the default `method="quadmesh+"`. The interior-saturating per-layer sweep (thesis Ch 4.1 IE-before-OE, Ch 4.2 fold-seam forbiddance) leaves **zero interior residual triangles by construction** — the faithfulness invariant. Post-process mean element quality: Test_Case_1 0.696, Block_O 0.680.

- **Now:** edge-case fixups (isolated-triangle edge-swap; boundary-layer walkability) and quality tuning.
- **Next:** performance optimization; evaluate a C++ or Rust backend; wire `tri2quad(aggressive=)` to CHILmesh `merge_elements`.
- **Future:** formal integration within the unified ADMESH library.

**Attention MATLAB users:** This Python library is the actively-developed successor to the original MATLAB codebase. The original code (no longer maintained) is frozen under [`src/matlab/quadmesh`](https://github.com/domattioli/QuADMESH/tree/main/src/matlab/quadmesh).

---

## Installation

```bash
# From the repo root (src-layout package)
pip install -e .            # Basic install
pip install -e ".[dev]"     # + pytest for the test suite
pip install -e ".[plot]"    # + matplotlib for quality plots
```

Test the installation:

```bash
pytest -q                          # 133 tests
python -m quadmesh.cli in.14 -o out.14
```

<!-- TODO: PyPI publish v0.1.0; update installation with `pip install quadmesh` once released -->

---

## Repository Layout

```
src/quadmesh/       Python package (the maintained implementation)
tests/              pytest suite; tests/fixtures/meshes/ holds .14 test meshes
docs/               MAPPING.md (MATLAB → Python), session notes
specs/              speckit specs/plans/tasks
videos/             demo assets (quadmesh_logo.gif, render scripts)
src/matlab/         frozen legacy MATLAB reference (read-only, not installable)
archive/            in-repo holding pen: upstream dups, .mat binaries, old results
```

**Note on CHILmesh:** Functionality is **not vendored** — it is an external dependency (`chilmesh>=0.4.0`). The old MATLAB `@CHILmesh` class lives under `archive/` for historical reference only; see [CHILmesh](https://github.com/domattioli/CHILmesh).

---

## Quick Start

Convert a triangular `fort.14` mesh to quad-dominant with the default QuADMESH+ method:

```bash
python -m quadmesh.cli input.14 -o output.14
```

Useful flags: `--polygon domain.poly` (supply the domain boundary), `--no-post-process` (skip the quality smoother), `--n-smooth-iter N` (smoother iterations). Run `python -m quadmesh.cli --help` for the full list.

See [MAPPING.md](docs/MAPPING.md) for the MATLAB → Python function correspondence and current port status.

---

## Citation

**Algorithm & theory** (cite the original thesis):

> Mattioli, DO (2017). QuADMESH+: A Quadrangular ADvanced Mesh Generator for Hydrodynamic Models. The Ohio State University, OhioLINK - Electronic Theses and Dissertations Center. Master's Thesis. http://rave.ohiolink.edu/etdc/view?acc_num=osu1500627779532088

**This software** (cite the Zenodo release):

> Mattioli, DO, Kubatko, EJ (2026). QuADMESH: A Quadrangular ADvanced, automatic unstructured MESH generator for 2D hydrodynamic domains. Zenodo. https://doi.org/10.5281/zenodo.20351165

The DOI `10.5281/zenodo.20351165` resolves to the latest release; version-specific DOIs are listed on the [Zenodo record](https://doi.org/10.5281/zenodo.20351165).

<!-- TODO: Add CITATION.cff at repo root once port reaches v1.0.0; will enable GitHub's "Cite this repository" button and Zotero integration -->

---

## Related Projects

- **[ADMESH](https://github.com/domattioli/ADMESH)** — Python port of the ADMESH adaptive mesh generator with pythonic API.
- **[CHILmesh](https://github.com/domattioli/CHILmesh)** — Mesh data structure, smoother, and quality analysis for triangular and quadrilateral meshes.

---

## Contact

**Dominik Mattioli** (repo owner) — [GitHub](https://github.com/domattioli)  
**Ethan J. Kubatko** — [kubatko.3@osu.edu](mailto:kubatko.3@osu.edu)

---

## License

**Noncommercial / research use only.** Licensed under the PolyForm Noncommercial License 1.0.0 **with an additional No-AI/ML-training restriction** — see [LICENSE](LICENSE) and [AI-USAGE.md](AI-USAGE.md).

No commercial use and no use as AI/ML training data without a separate written license. Commercial or AI-training licenses: contact domattioli via mango-kooky-okay@duck.com

---

<p align="center">
  <sub>Regenerate logo GIF: <code>python videos/scripts/render_logo_gif.py</code> (matplotlib only, no ffmpeg).</sub>
</p>
