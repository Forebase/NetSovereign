from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping
from uuid import UUID, uuid4


def _freeze_str_mapping(value: Mapping[str, str]) -> Mapping[str, str]:
    return MappingProxyType(dict(value))


@dataclass(frozen=True, slots=True)
class EntityId:
    value: UUID = field(default_factory=uuid4)

    @classmethod
    def parse(cls, value: str | UUID) -> EntityId:
        return cls(value if isinstance(value, UUID) else UUID(value))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class Entity:
    id: EntityId = field(default_factory=EntityId)
    name: str | None = None
    labels: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "labels", _freeze_str_mapping(self.labels))
