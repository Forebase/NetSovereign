from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from computecommons.identity import QualifiedName


@dataclass(frozen=True, slots=True)
class Capability:
    """A named feature or behavior provided by a component or resource."""

    name: QualifiedName
    version: str | None = None
    properties: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))
