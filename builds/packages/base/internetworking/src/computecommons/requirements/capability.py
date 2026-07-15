from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any, Mapping

from computecommons.identity import QualifiedName


@dataclass(frozen=True, slots=True)
class Capability:
    name: QualifiedName
    version: str | None = None
    properties: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "properties", MappingProxyType(dict(self.properties)))


@dataclass(frozen=True, slots=True)
class CapabilityRequirement:
    name: QualifiedName
    minimum_version: str | None = None
    required_properties: Mapping[str, Any] = field(default_factory=dict)
    optional: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "required_properties",
            MappingProxyType(dict(self.required_properties)),
        )


class MatchStatus(StrEnum):
    SATISFIED = "satisfied"
    UNSATISFIED = "unsatisfied"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RequirementMatch:
    requirement: CapabilityRequirement
    status: MatchStatus
    capability: Capability | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class MatchReport:
    matches: tuple[RequirementMatch, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "matches", tuple(self.matches))

    @property
    def satisfied(self) -> bool:
        return all(
            match.status is MatchStatus.SATISFIED or match.requirement.optional
            for match in self.matches
        )
