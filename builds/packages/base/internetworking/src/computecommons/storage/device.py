from __future__ import annotations

from dataclasses import dataclass

from computecommons.storage.capacity import StorageCapacity


@dataclass(frozen=True, slots=True)
class StorageDevice:
    id: str
    name: str | None = None
    capacity: StorageCapacity | None = None
    rotational: bool | None = None
    path: str | None = None
    model: str | None = None
    serial: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Storage device id cannot be empty")
        if self.path is not None and not self.path.startswith("/"):
            raise ValueError("Storage device path must be absolute")


__all__ = ["StorageDevice"]
