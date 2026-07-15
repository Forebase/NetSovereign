from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Service:
    name: str
    state: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Service name cannot be empty")
