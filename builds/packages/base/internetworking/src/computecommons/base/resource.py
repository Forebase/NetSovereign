from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from computecommons.identity import QualifiedName


@dataclass(frozen=True, slots=True)
class Resource:
    """Stable identity and metadata for an addressable compute resource."""

    kind: QualifiedName
    id: str
    name: str | None = None
    labels: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Resource id cannot be empty")
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
