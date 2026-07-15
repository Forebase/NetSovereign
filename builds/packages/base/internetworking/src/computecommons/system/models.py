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


@dataclass(frozen=True, slots=True)
class RuntimeEnvironment:
    implementation: str
    version: str
    executable: str | None = None
    variables: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "variables", MappingProxyType(dict(self.variables)))


@dataclass(frozen=True, slots=True)
class Host:
    machine: Machine
    operating_system: OperatingSystem
    runtime: RuntimeEnvironment | None = None
    domain_name: str | None = None
