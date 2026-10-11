# Security Policy

QuADMESH is a Python port of the MATLAB QuADMESH+ algorithm for triangular
mesh-to-quadrilateral conversion. It is a scientific geometry library. It has no
network service and no data-processing backend.

## Supported versions

| Version | Supported |
|---|---|
| `0.2.x` (current PyPI) | ✅ receives fixes |
| `< 0.2` | ⚠️ best-effort only |

## Reporting a vulnerability

Do not open a public issue for security problems.

Report privately through GitHub's
[private vulnerability reporting](https://github.com/domattioli/QuADMESH/security/advisories/new)
for this repository. If that is unavailable to you, contact a maintainer via
their GitHub profile ([@domattioli](https://github.com/domattioli)) and request
a private channel.

When you report, include:

- A description of the issue and its impact.
- Steps to reproduce (a minimal proof of concept where practical).
- Affected module or component (for example `src/quadmesh/distmesh.py`, or a specific function).
- Any suggested remediation.

We acknowledge a report within a reasonable window. We then agree a fix and
disclosure timeline with you.

## Scope notes

- Secrets: the repository holds no tokens, database URLs, or production
  credentials. It has no external service integrations, API keys, or signing keys.
- Supply chain: dependencies are pinned in `pyproject.toml`. The list is numpy,
  scipy, chilmesh, and optional matplotlib.
- Input robustness: the library processes mesh data supplied by callers.
  Malformed or adversarially crafted mesh inputs can trigger crashes, infinite
  loops, or numerical errors. These are normal issues, unless they cause
  arbitrary code execution or memory corruption. Report them as normal issues.
- Scientific correctness: the implementation is a faithful Python port of the
  MATLAB QuADMESH+ algorithm. Numerical differences from the original are
  expected. Report them as performance or compatibility issues; they are not a
  security concern.

## Out of scope

- Findings that require a compromised developer machine or stolen credentials.
- Findings arising from use of the library in ways explicitly documented as
  unsupported (for example, calling private functions prefixed with `_`).
