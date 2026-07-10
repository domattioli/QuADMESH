# Security Policy

QuADMESH is a Python port of the MATLAB QuADMESH+ algorithm for triangular
mesh-to-quadrilateral conversion. It is a scientific / geometry library, not a
network service or data-processing backend.

## Supported versions

| Version | Supported |
|---|---|
| `0.2.x` (current PyPI) | ✅ — receives fixes |
| `< 0.2` | ⚠️ — best-effort only |

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report privately through GitHub's
[private vulnerability reporting](https://github.com/domattioli/QuADMESH/security/advisories/new)
for this repository. If that is unavailable to you, contact a maintainer via
their GitHub profile ([@domattioli](https://github.com/domattioli)) and request
a private channel.

When reporting, please include:

- A description of the issue and its impact.
- Steps to reproduce (a minimal proof of concept where practical).
- Affected module / components (e.g., `src/quadmesh/distmesh.py`, specific function).
- Any suggested remediation.

We aim to acknowledge a report within a reasonable window and will coordinate a
fix and disclosure timeline with you.

## Scope notes

- **Secrets.** No tokens, database URLs, or production credentials are committed.
  The repository contains no external service integrations, API keys, or signing
  keys.
- **Supply chain.** Dependencies are pinned in `pyproject.toml`. Review
  [`pyproject.toml`](pyproject.toml) for the dependency list (numpy, scipy,
  chilmesh, and optional matplotlib).
- **Input robustness.** This library processes geometric/mesh data supplied by
  callers. Malformed or adversarially-crafted mesh inputs may trigger crashes,
  infinite loops, or numerical errors. These are **normal issues** unless they
  cause arbitrary code execution or memory corruption. Report them as such.
- **Scientific correctness.** The implementation is a faithful Python port of
  the MATLAB QuADMESH+ algorithm. Numerical differences from the original are
  expected and not a security concern; report them as performance or
  compatibility issues instead.

## Out of scope

- Findings that require a compromised developer machine or stolen credentials.
- Findings arising from use of the library in ways explicitly documented as
  unsupported (e.g., calling private functions prefixed with `_`).
