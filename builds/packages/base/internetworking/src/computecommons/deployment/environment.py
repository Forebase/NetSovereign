from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class DeploymentEnvironment:
    id: str
    name: str | None = None
    kind: str | None = None
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Deployment environment id cannot be empty")
        if self.kind is not None and not self.kind.strip():
            raise ValueError("Deployment environment kind cannot be empty")
        object.__setattr__(self, "labels", MappingProxyType(dict(self.labels)))


Environment = DeploymentEnvironment

__all__ = ["DeploymentEnvironment", "Environment"]
