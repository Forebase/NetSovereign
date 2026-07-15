from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class Zone:
    id: str
    name: str | None = None
    region_id: str | None = None
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Zone id cannot be empty")
        if self.region_id is not None and not self.region_id.strip():
            raise ValueError("Zone region_id cannot be empty")
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


__all__ = ["Zone"]
