"""Adapter protocol, registry, availability, options, result (spec 058).

An adapter turns a triangular CHILmesh into a quad (or mixed) CHILmesh and
reports metadata. Register one with ``@register``; the runner, CLI and
contract tests pick it up with no other edit.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Iterable, Optional, Protocol, runtime_checkable

LICENSE_TAGS = ("project", "MIT-external", "BSD-external", "GPL-subprocess", "clean-room")
ENV_DISABLE = "QUADMESH_BENCH_DISABLE"


@dataclass(frozen=True)
class Availability:
    installed: bool
    version: Optional[str] = None
    path: Optional[str] = None
    message: str = ""


@dataclass
class AdapterOptions:
    timeout_s: float = 600
    target_faces: Optional[int] = None
    extra: dict = field(default_factory=dict)


@dataclass
class AdapterResult:
    mesh: object  # CHILmesh or None on failure
    adapter: str
    version: str = "built-in"
    license_tag: str = "project"
    runtime_s: float = 0.0
    convert_s: float = 0.0
    success: bool = True
    message: str = ""
    vertex_order_preserved: bool = True


@runtime_checkable
class Adapter(Protocol):
    name: str
    display_name: str
    family: str
    license_tag: str
    citation: str
    install_route: str
    install_hint: str
    accepts_mixed: bool

    def probe(self) -> Availability: ...

    def run(self, mesh, options: AdapterOptions) -> AdapterResult: ...


_REGISTRY: dict[str, Adapter] = {}


def register(obj):
    """Register an adapter class or instance (usable as a decorator)."""
    inst = obj() if isinstance(obj, type) else obj
    _REGISTRY[inst.name] = inst
    return obj


def unregister(name: str) -> None:
    _REGISTRY.pop(name, None)


def get_adapters() -> dict[str, Adapter]:
    """Registered adapters by name (built-ins load on first call)."""
    from . import adapters  # noqa: F401  (import registers built-ins)

    return dict(_REGISTRY)


def install_route_hint(route: str, suffix: str = "") -> str:
    """One-line install hint generated from an install route."""
    if route == "base":
        text = "included in the base install: pip install quadmesh"
    elif route.startswith("extra:"):
        extra = route.split(":", 1)[1]
        text = f'pip install "quadmesh[{extra}]"'
    elif route == "external":
        text = "install the tool separately and put it on PATH"
    else:
        raise ValueError(f"unknown install route: {route!r}")
    return f"{text}; {suffix}" if suffix else text


def _split(value: Optional[str]) -> list[str]:
    return [s.strip() for s in (value or "").split(",") if s.strip()]


def is_disabled(name: str, disabled: Optional[Iterable[str]] = None, env=None) -> bool:
    """True when ``name`` is in ``disabled`` or in QUADMESH_BENCH_DISABLE."""
    env = os.environ if env is None else env
    return name in set(disabled or ()) | set(_split(env.get(ENV_DISABLE)))
