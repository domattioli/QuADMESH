# LOCAL.md — repo-local workflow registry (spec-010 v2.3)

Workflows listed here are intentionally repo-local (not DomI-managed copies). Adding a
new local workflow requires a row here in the same PR — unlisted local
workflows fail the workflow-conformance gate.

| Workflow | Justification |
|---|---|
| `publish.yml` | PyPI release, tag-triggered — repo-specific release pipeline |
