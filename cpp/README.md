# QuADMESH C++ port (MVP)

A C++17 port of the QuADMESH `tri2quad` pipeline. The Python package in `src/quadmesh/` stays the maintained implementation and the oracle. This directory is excluded from the wheel and the sdist.

## Build

Requirements: CMake 3.16 or newer and a C++17 compiler (Apple Clang or GCC). Eigen 3.4.0 and Catch2 v3.5.4 are vendored in `third_party/`, so the build makes no network requests.

```bash
cmake -S cpp -B cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build cpp/build -j
ctest --test-dir cpp/build --output-on-failure
```

The build compiles with `-ffp-contract=off` and without fast-math, so floating-point results match the Python oracle.

## Run

```bash
cpp/build/quadmesh input.14 -o output.14
```

The options mirror `python -m quadmesh.cli`. `--polygon` is not supported. On failure the command prints one error line on stderr, leaves no output file and exits non-zero: 1 bad arguments, 2 missing input, 3 malformed `.14`, 4 conversion failure, 5 write failure.

## Compare with the Python oracle

```bash
cpp/build/dump_driver --out <dir> --in .scratch/cpp-port/ground_truth/meshes --mesh Block_O
cpp/build/diff_tool --cpp <dir> --oracle .scratch/cpp-port/ground_truth/expected --mesh Block_O
```

`PORTING_NOTES.md` maps Python and CHILmesh names to their C++ equivalents and lists the deliberate differences.
