from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, TypeVar

from computecommons.identity import QualifiedName

T_co = TypeVar("T_co", covariant=True)


@dataclass(frozen=True, slots=True)
class Capability[T_co]:
    """A typed capability advertised by a resource or component."""

    name: QualifiedName
    version: str | None = None
    value: T_co | None = None
    properties: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))
