from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class Region:
    id: str
    name: str | None = None
    provider: str | None = None
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Region id cannot be empty")
        if self.provider is not None and not self.provider.strip():
            raise ValueError("Region provider cannot be empty")
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


__all__ = ["Region"]
