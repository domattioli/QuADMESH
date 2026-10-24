<h1 align="center">
  <img src="videos/quadmesh_logo.gif" alt="QuADMESH logo: triangles in, quads out" width="680">
</h1>

<p align="center">
  <strong>A Quadrangular ADvanced, automatic unstructured MESH generator for 2D shallow-water models.</strong><br>
  Python API and port of the MATLAB library and 'QuADMESH+' <a href="https://doi.org/10.5281/zenodo.23607233">
    <img src="https://img.shields.io/badge/Thesis-QuADMESH-ba0c2f?style=flat-square&logo=book&logoColor=white&labelColor=cfd4d8" alt="QuADMESH Thesis"></a> 
</p>

<p align="center">
  <strong><a href="https://scholar.google.com/citations?user=IBFSkOcAAAAJ&hl=en">Dominik Mattioli</a><sup>1†</sup>, <a href="https://scholar.google.com/citations?user=mYPzjIwAAAAJ&hl=en">Ethan Kubatko</a><sup>2</sup></strong><br>
  <sup>†</sup>Corresponding author | <sup>1</sup>Unaffiliated | <sup>2</sup>Ohio State University (<a href="https://ceg.osu.edu/computational-hydrodynamics-and-informatics-laboratory"><img src="https://img.shields.io/badge/The CHIL-a7b1b7?labelColor=ba0c2f&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHJlY3QgeD0iNCIgeT0iMiIgd2lkdGg9IjE2IiBoZWlnaHQ9IjIwIiByeD0iNyIgZmlsbD0iI2ZmZmZmZiIvPjxyZWN0IHg9IjguNSIgeT0iNyIgd2lkdGg9IjciIGhlaWdodD0iMTAiIHJ4PSIzIiBmaWxsPSIjYmEwYzJmIi8+PC9zdmc+" alt="CHIL"></a>)
</p>

- Converts an existing, validated shallow-water triangulation into quadrilaterals by merging adjacent triangle pairs.
- Reuses the input vertices; triangle pairing adds no points. `can_remove_edges=False` stops boundary-edge collapse.
- Leaves zero interior residual triangles (triangles with no domain-boundary edge), checked by `tests/test_no_interior_tris.py`.
- Adds points only to clear leftover boundary triangles; this step is on by default and `point_insert=False` turns it off.
- Returns a quad-pure mesh by default; `remove_boundary_tris=False` keeps leftover boundary triangles instead.

> **Attention MATLAB users:** This Python library is the actively developed successor to the original MATLAB code, which is no longer maintained and is frozen under [`archive/matlab`](https://github.com/domattioli/quadmesh/tree/development/archive/matlab).

<p align="center">
  <a href="https://pypi.org/project/quadmesh/"><img src="https://img.shields.io/pypi/v/quadmesh.svg?label=PyPI" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+"></a>
  <a href="https://github.com/domattioli/QuADMESH/actions/workflows/tests.yml"><img src="https://github.com/domattioli/QuADMESH/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/domattioli/QuADMESH/issues"><img src="https://img.shields.io/github/issues/domattioli/QuADMESH.svg" alt="Open issues"></a>
  <a href="https://doi.org/10.5281/zenodo.20350483"><img src="https://zenodo.org/badge/DOI/10.5281/zenodo.20350483.svg" alt="DOI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-PolyForm%20NC%20%2B%20No--AI-red.svg" alt="License"></a>
</p>

## Table of Contents

1. [Status & Roadmap](#1-status--roadmap)
2. [Installation](#2-installation)
3. [Quick Start](#3-quick-start)
4. [Meshes from the Valence registry](#4-meshes-from-the-valence-registry)
5. [Limitations](#5-limitations)
6. [Documentation](#6-documentation)
7. [Citation](#7-citation)
8. [Related Projects](#8-related-projects)
9. [Contributing & Contact](#9-contributing--contact)
10. [License](#10-license)

---

## 1. Status & Roadmap

**Current release: 0.2.5 (2026-10-12); see [CHANGELOG](CHANGELOG.md).**

The default `method="quadmesh+"` runs the thesis per-layer sweep and leaves zero interior residual triangles; CI checks this on the meshes bundled with `chilmesh.data`. Algorithm and MATLAB parity status: [`docs/algorithm.md`](docs/algorithm.md).

- **Now:** boundary-layer quality, including the ENPAC2003 low-skew tail ([#90](https://github.com/domattioli/QuADMESH/issues/90)); right-size the test suite ([#109](https://github.com/domattioli/QuADMESH/issues/109)).
- **Next:** boundary-type-aware layer seeding ([#77](https://github.com/domattioli/QuADMESH/issues/77)); a MATLAB parity oracle ([#116](https://github.com/domattioli/QuADMESH/issues/116)); wire `tri2quad(aggressive=)` to CHILmesh `merge_elements`.
- **Later:** parallelization ([#38](https://github.com/domattioli/QuADMESH/issues/38)); evaluate a C++ or Rust backend; formal integration within a unified ecosystem including <a href="https://github.com/domattioli/ADMESH"><img src="https://img.shields.io/pypi/v/admesh2D?label=ADMESH&color=9ae6b4&labelColor=2f855a&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjEuNSIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIj48cGF0aCBkPSJNMiAyMSBMMTIgMiBMMjIgMjEgWiBNMTIgMiBMNyAyMSBNMTIgMiBMMTcgMjEgTTcgMjEgTDEyIDEyIEwxNyAyMSBNMTIgMTIgTDEyIDIiLz48L3N2Zz4=" alt="ADMESH PyPI version"></a> and <a href="https://github.com/domattioli/CHILmesh"><img src="https://img.shields.io/pypi/v/chilmesh?label=CHILmesh&color=caf0f8&labelColor=0077b6&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjEuOCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIj48cGF0aCBkPSJNMSA4IHEzIC00IDYgMCB0NiAwIHQ2IDAgdDYgMCBNMSAxMyBxMyAtNCA2IDAgdDYgMCB0NiAwIHQ2IDAgTTEgMTggcTMgLTQgNiAwIHQ2IDAgdDYgMCB0NiAwIi8%2BPC9zdmc%2B" alt="CHILmesh PyPI version"></a>

Headline result: on ENPAC2003 (531,680 triangles), QuADMESH 0.1.0 with chilmesh 1.0.0 produced 274,321 quads with zero interior residual triangles in 773 s, single-threaded. Details: [docs/benchmarks](docs/benchmarks/README.md).

[Back to top](#table-of-contents)

## 2. Installation

```bash
pip install quadmesh                # release from PyPI
pip install -e ".[dev]"             # from a clone, plus pytest
pip install -e ".[plot]"            # plus matplotlib for quality plots
```

`chilmesh` is an external dependency and is not vendored. Mesh-dependent tests need a Valence token; see [tests/fixtures/README.md](tests/fixtures/README.md).

[Back to top](#table-of-contents)

## 3. Quick Start

```bash
python -m quadmesh.cli input.14 -o output.14
```

Useful flags: `--polygon domain.poly` (domain boundary), `--no-post-process`, `--n-smooth-iter N`, `--preserve-boundary`. Run `python -m quadmesh.cli --help` for all of them. The MATLAB to Python function map is in [MAPPING.md](docs/MAPPING.md).

[Back to top](#table-of-contents)

## 4. Meshes from the Valence registry

`quadmesh --from-registry NAME -o out.14` ships in 0.2.5 (unreleased). Test meshes are available through Valence, a token-gated mesh service.

1. Sign in with GitHub at https://valence-api.iqh766c2.workers.dev .
2. A GitHub account at least 30 days old gets a token at once. The page shows it once; copy it then.
3. A token allows 500 downloads per day (reset at midnight UTC) and expires after one year.

```bash
export VALENCE_TOKEN=<your token>; quadmesh --from-registry Block_O.14 -o out.14
```

[Back to top](#table-of-contents)

## 5. Limitations

- Converts an existing, validated triangulation. It does not generate meshes from scratch.
- Boundary-layer quads have the lowest quality, and some can be concave ([#90](https://github.com/domattioli/quadmesh/issues/90)).
- The default post-process may drop boundary vertices; use `preserve_boundary=True` to keep them.

[Back to top](#table-of-contents)

## 6. Documentation

- [Algorithm](docs/algorithm.md) and [MATLAB mapping](docs/MAPPING.md)
- [Python quickstart](docs/python-quickstart.md)
- [Performance and benchmarks](docs/benchmarks/README.md) (`quadmesh-bench`, diagnostics)
- [Repository layout](docs/repository-layout.md), [share your mesh](docs/share-your-mesh.md)

[Back to top](#table-of-contents)

## 7. Citation

**Algorithm and theory** (cite the original thesis):

> Mattioli, DO (2017). QuADMESH+: A Quadrangular ADvanced Mesh Generator for Hydrodynamic Models. The Ohio State University, OhioLINK - Electronic Theses and Dissertations Center. Master's Thesis. http://rave.ohiolink.edu/etdc/view?acc_num=osu1500627779532088

A corrected PDF of the thesis, with every cross-reference and citation resolved, is archived at https://doi.org/10.5281/zenodo.23607233 and attached to each [GitHub release](https://github.com/domattioli/QuADMESH/releases). The OhioLINK copy prints `??` for figure, chapter and citation references because it was compiled without the bibliography pass.

**This software** (cite the Zenodo release):

> Mattioli, DO, Kubatko, EJ (2026). QuADMESH: A Quadrangular ADvanced, automatic unstructured MESH generator for 2D hydrodynamic domains. Zenodo. https://doi.org/10.5281/zenodo.20350483

The DOI resolves to the latest release; version DOIs are on the [Zenodo record](https://doi.org/10.5281/zenodo.20350483).

[Back to top](#table-of-contents)

## 8. Related Projects

- [ADMESH](https://github.com/domattioli/ADMESH): Python port of the ADMESH adaptive mesh generator.
- [CHILmesh](https://github.com/domattioli/CHILmesh): mesh data structure, smoother, and quality analysis.

[Back to top](#table-of-contents)

## 9. Contributing & Contact

See [CONTRIBUTING.md](CONTRIBUTING.md). To share a mesh, open an issue in this repository (https://github.com/domattioli/quadmesh/issues/new).

Dominik Mattioli (repo owner): [GitHub](https://github.com/domattioli) | Ethan J. Kubatko: [OSU profile](https://people.engineering.osu.edu/people/kubatko.3)

[Back to top](#table-of-contents)

## 10. License

Noncommercial and research use only. PolyForm Noncommercial License 1.0.0 with an additional No-AI/ML-training restriction; see [LICENSE](LICENSE) and [AI-USAGE.md](https://github.com/domattioli/quadmesh/blob/development/docs/AI-USAGE.md).

Commercial or AI-training licenses: contact the author through [GitHub](https://github.com/domattioli)

[Back to top](#table-of-contents)
