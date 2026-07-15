from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class Node:
    id: str
    name: str | None = None
    cluster_id: str | None = None
    zone_id: str | None = None
    addresses: tuple[str, ...] = ()
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Node id cannot be empty")
        if self.cluster_id is not None and not self.cluster_id.strip():
            raise ValueError("Node cluster_id cannot be empty")
        if self.zone_id is not None and not self.zone_id.strip():
            raise ValueError("Node zone_id cannot be empty")
        if any(not address.strip() for address in self.addresses):
            raise ValueError("Node addresses cannot contain empty values")
        object.__setattr__(self, "addresses", tuple(self.addresses))
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


__all__ = ["Node"]
