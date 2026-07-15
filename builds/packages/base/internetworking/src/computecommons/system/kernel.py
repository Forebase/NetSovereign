from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Kernel:
    name: str
    version: str | None = None
    release: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Kernel name cannot be empty")
