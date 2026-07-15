from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from computecommons.compute import Machine
from computecommons.enums import OperatingSystemFamily


@dataclass(frozen=True, slots=True)
class OperatingSystem:
    family: OperatingSystemFamily
    name: str
    version: str | None = None
    release: str | None = None
    kernel_name: str | None = None
    kernel_version: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Operating system name cannot be empty")


@dataclass(frozen=True, slots=True)
class KernelInfo:
    name: str
    version: str | None = None
    release: str | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Kernel name cannot be empty")


@dataclass(frozen=True, slots=True)
class RuntimeEnvironment:
    implementation: str
    version: str
    executable: str | None = None
    variables: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.implementation.strip():
            raise ValueError("Runtime implementation cannot be empty")
        if not self.version.strip():
            raise ValueError("Runtime version cannot be empty")
        if self.executable is not None and not self.executable.strip():
            raise ValueError("Runtime executable cannot be empty")
        object.__setattr__(self, "variables", MappingProxyType(dict(self.variables)))


@dataclass(frozen=True, slots=True)
class Host:
    machine: Machine
    operating_system: OperatingSystem
    runtime: RuntimeEnvironment | None = None
    domain_name: str | None = None
    kernel: KernelInfo | None = None

    def __post_init__(self) -> None:
        if self.domain_name is not None and not self.domain_name.strip():
            raise ValueError("Host domain_name cannot be empty")


__all__ = ["Host", "KernelInfo", "OperatingSystem", "RuntimeEnvironment"]
