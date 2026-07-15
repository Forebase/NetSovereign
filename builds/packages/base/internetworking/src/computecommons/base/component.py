from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from computecommons.identity import QualifiedName
from computecommons.requirements import Capability


@dataclass(frozen=True, slots=True)
class Component:
    """A named software or infrastructure component with declared capabilities."""

    name: QualifiedName
    version: str | None = None
    capabilities: tuple[Capability, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
