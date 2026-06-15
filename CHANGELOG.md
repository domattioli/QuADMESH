# Changelog

All notable changes to this project will be documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.1] — 2026-06-15

### Changed
- `chilmesh` runtime-dependency pin raised `>=0.4.0 → >=1.2.1` (tracks released chilmesh 1.2.1).
- Source archives (git archive / sdist / GitHub-release tarball / Zenodo) exclude agent + dev-process files via `.gitattributes` `export-ignore`.

### Added / Fixed (since 0.1.0)
- `method="quadmesh+"` (the published layer-ordered per-layer loop; `"layered"` alias) is the sole and default tri-to-quad method; `"faithful"` and `"matching"` removed (now raise `ValueError`) (#46).
- Greedy interior-saturating pairing of post-sweep layer leftovers (T017/T018): zero interior triangles; post-process mean quality up — Test_Case_1 0.573 → 0.696, Block_O 0.251 → 0.680.
- Test `.14` fixtures provisioned on demand from the `domattioli/Valence` registry instead of being vendored.

## [0.1.0]

- Initial Python port of QuADMESH+ (tri-to-quad generator on top of chilmesh).
