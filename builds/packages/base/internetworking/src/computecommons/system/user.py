from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class User:
    name: str
    uid: int | None = None
    home: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("User name cannot be empty")
        if self.uid is not None and self.uid < 0:
            raise ValueError("User uid cannot be negative")
