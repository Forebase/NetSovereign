from __future__ import annotations

import re
from dataclasses import dataclass

from computecommons.enums import CPUArchitecture, OperatingSystemFamily
from computecommons.static import (
    normalize_architecture,
    normalize_operating_system,
    operating_system_family,
)

_SEPARATOR = re.compile(r"[/:,\s]+")
_RUNTIME_NAMES = frozenset(
    {"cpython", "python", "pypy", "node", "nodejs", "java", "jvm", "go", "wasm", "wasmtime"}
)


@dataclass(frozen=True, slots=True)
class RuntimeDescriptor:
    name: str
    version: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("runtime name cannot be empty")
        object.__setattr__(self, "name", self.name.strip().lower())
        if self.version is not None and not self.version.strip():
            raise ValueError("runtime version cannot be empty")

    def __str__(self) -> str:
        return self.name if self.version is None else f"{self.name}@{self.version}"


@dataclass(frozen=True, slots=True)
class PlatformTag:
    os: str
    architecture: str
    variant: str | None = None
    runtime: RuntimeDescriptor | None = None

    def __post_init__(self) -> None:
        if not self.os.strip() or not self.architecture.strip():
            raise ValueError("Platform tags require os and architecture")
        object.__setattr__(self, "os", self.os.strip().lower())
        object.__setattr__(self, "architecture", self.architecture.strip().lower())
        if self.variant is not None and not self.variant.strip():
            raise ValueError("variant cannot be empty")

    @property
    def cpu_architecture(self) -> CPUArchitecture:
        return normalize_architecture(self.architecture)

    @property
    def os_family(self) -> OperatingSystemFamily:
        return operating_system_family(self.os)

    def __str__(self) -> str:
        platform = "/".join(part for part in (self.os, self.architecture, self.variant) if part)
        return platform if self.runtime is None else f"{platform}/{self.runtime}"


def _runtime_from_token(token: str) -> RuntimeDescriptor | None:
    name, sep, version = token.partition("@")
    if name.lower() in _RUNTIME_NAMES:
        return RuntimeDescriptor(name, version or None)
    if sep:
        return RuntimeDescriptor(name, version)
    return None


def parse_platform_tag(value: str) -> PlatformTag:
    """Parse neutral platform strings such as linux/amd64 or cpython@3.12/linux/arm64."""
    text = value.strip().lower()
    if not text:
        raise ValueError("Platform tag cannot be empty")
    parts = [part for part in _SEPARATOR.split(text) if part]
    if len(parts) < 2 or len(parts) > 4:
        raise ValueError(
            "Platform tags must contain os and architecture, with optional variant/runtime"
        )

    runtime = _runtime_from_token(parts[0])
    if runtime is not None and len(parts) >= 3:
        parts = parts[1:]
    else:
        tail_runtime = _runtime_from_token(parts[-1]) if len(parts) >= 3 else None
        if tail_runtime is not None:
            runtime = tail_runtime
            parts = parts[:-1]

    if len(parts) not in (2, 3):
        raise ValueError("Platform tags must be 'os/architecture[/variant]' with optional runtime")

    os_name = normalize_operating_system(parts[0]) or parts[0]
    return PlatformTag(os_name, parts[1], parts[2] if len(parts) == 3 else None, runtime)
