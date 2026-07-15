from __future__ import annotations

from dataclasses import dataclass

from computecommons.storage.capacity import StorageCapacity


@dataclass(frozen=True, slots=True)
class StorageDevice:
    id: str
    name: str | None = None
    capacity: StorageCapacity | None = None
    rotational: bool | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Storage device id cannot be empty")
