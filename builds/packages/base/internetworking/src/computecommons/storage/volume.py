from __future__ import annotations

from dataclasses import dataclass

from computecommons.storage.capacity import StorageCapacity
from computecommons.storage.filesystem import FileSystem


@dataclass(frozen=True, slots=True)
class StorageVolume:
    id: str
    name: str | None = None
    capacity: StorageCapacity | None = None
    filesystem: FileSystem | None = None

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("Storage volume id cannot be empty")
