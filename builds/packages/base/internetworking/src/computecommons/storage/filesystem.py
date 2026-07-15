from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FileSystem:
    type: str
    label: str | None = None
    uuid: str | None = None

    def __post_init__(self) -> None:
        if not self.type:
            raise ValueError("Filesystem type cannot be empty")
