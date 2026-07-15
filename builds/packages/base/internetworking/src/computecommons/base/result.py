from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar

T_co = TypeVar("T_co", covariant=True)
E_co = TypeVar("E_co", covariant=True)


@dataclass(frozen=True, slots=True)
class Result[T_co, E_co]:
    """Neutral success/error carrier for base-layer operations."""

    value: T_co | None = None
    error: E_co | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(frozen=True, slots=True)
class Report:
    """Small neutral report with optional machine-readable details."""

    summary: str
    details: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", tuple(self.details))
