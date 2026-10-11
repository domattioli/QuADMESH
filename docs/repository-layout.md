# Repository layout

```
src/quadmesh/       Python package (the maintained implementation)
tests/              pytest suite; tests/fixtures/meshes/ holds .14 test meshes
docs/               algorithm, MATLAB mapping, benchmarks, guides
scripts/            setup, fixture, benchmark, and diagnostic tools
videos/             demo assets (quadmesh_logo.gif, render scripts)
archive/matlab/     frozen MATLAB QuADMESH+ original (read-only, not installable)
```

`chilmesh` is an external dependency, not vendored. Regenerate the logo GIF with `python videos/scripts/render_logo_gif.py`.
