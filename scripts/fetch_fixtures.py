#!/usr/bin/env python3
"""Provision QuADMESH test meshes from the domattioli/Valence registry into tests/fixtures/meshes/.

Requires GITHUB_TOKEN or GH_TOKEN with cross-repo read on domattioli/Valence.
Usage: python scripts/fetch_fixtures.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def main() -> int:
    """Provision test meshes and report results."""
    mod_path = Path(__file__).resolve().parent.parent / "tests" / "_mesh_provision.py"
    spec = importlib.util.spec_from_file_location("_mesh_provision", mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    results = mod.provision()

    for name in sorted(results):
        print(f"{name}: {results[name]}")

    errors = {n: s for n, s in results.items() if s.startswith("error")}
    skip_no_token = {n: s for n, s in results.items() if s == "skip-no-token"}
    present = {n: s for n, s in results.items() if s == "present"}
    fetched = {n: s for n, s in results.items() if s == "fetched"}

    if errors:
        print(f"\n{len(errors)} error(s)", file=sys.stderr)
        return 1

    if skip_no_token and not present and not fetched:
        print(
            "\nno GITHUB_TOKEN/GH_TOKEN with Valence read — nothing provisioned",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
