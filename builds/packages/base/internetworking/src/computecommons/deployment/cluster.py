from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class Cluster:
    id: str
    name: str | None = None
    environment_id: str | None = None
    region_id: str | None = None
    node_ids: tuple[str, ...] = ()
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Cluster id cannot be empty")
        if self.environment_id is not None and not self.environment_id.strip():
            raise ValueError("Cluster environment_id cannot be empty")
        if self.region_id is not None and not self.region_id.strip():
            raise ValueError("Cluster region_id cannot be empty")
        if any(not node_id.strip() for node_id in self.node_ids):
            raise ValueError("Cluster node_ids cannot contain empty values")
        object.__setattr__(self, "node_ids", tuple(self.node_ids))
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


__all__ = ["Cluster"]
