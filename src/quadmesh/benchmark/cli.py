"""quadmesh-bench console script (contracts/cli-and-results.md)."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import _protocol as P


def _csv(v):
    return [s.strip() for s in v.split(",") if s.strip()] if v else []


def _bundled() -> list:
    import chilmesh
    from chilmesh import CHILmesh

    d = Path(chilmesh.__file__).parent / "data"
    out = []
    for f in sorted(d.glob("*.14")):
        if CHILmesh.read_from_fort14(f).type == "Triangular":
            out.append(f)
    return out


def _list(adapters, disabled) -> int:
    for name, ad in sorted(adapters.items()):
        if P.is_disabled(name, disabled):
            state = "disabled"
        else:
            av = ad.probe()
            state = "available" if av.installed else f"not installed: {ad.install_hint}"
        print(f"{name}\t{ad.license_tag}\t{ad.install_route}\t{state}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="quadmesh-bench", description="Compare tri-to-quad meshers.")
    ap.add_argument("mesh", nargs="*", help=".14 mesh paths")
    ap.add_argument("--bundled", action="store_true", help="add every triangular chilmesh.data mesh")
    ap.add_argument("--adapters", help="comma-separated adapter names (default all)")
    ap.add_argument("--disable", help="comma-separated adapter names to skip")
    ap.add_argument("--out", help="directory for results.md and results.json")
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--strict", action="store_true", help="exit 1 if any row is not ok")
    ap.add_argument("--list", action="store_true", help="list adapters and exit")
    ap.add_argument("--show-disabled", action="store_true")
    a = ap.parse_args(argv)

    registry = P.get_adapters()
    disabled = _csv(a.disable)
    if a.list:
        return _list(registry, disabled)
    names = _csv(a.adapters) or None
    unknown = [n for n in (names or []) if n not in registry]
    if unknown:
        print(f"unknown adapters: {unknown}; known: {sorted(registry)}", file=sys.stderr)
        return 2
    meshes = list(a.mesh) + (_bundled() if a.bundled else [])
    if not meshes:
        ap.print_usage(sys.stderr)
        print("no meshes: give paths or --bundled", file=sys.stderr)
        return 2

    from ._runner import run_benchmark

    rec = run_benchmark(meshes, names, disabled, a.timeout, a.strict, a.show_disabled)
    rec.command = "quadmesh-bench " + " ".join(argv if argv is not None else sys.argv[1:])
    print(rec.to_markdown())
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "results.md").write_text(rec.to_markdown())
        rec.to_json(out / "results.json")
    if a.strict and any(r.status != "ok" for r in rec.rows):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
