from __future__ import annotations

from dataclasses import dataclass

from computecommons.storage.capacity import StorageCapacity
from computecommons.storage.filesystem import FilesystemInfo


@dataclass(frozen=True, slots=True)
class Volume:
    id: str
    name: str | None = None
    capacity: StorageCapacity | None = None
    filesystem: FilesystemInfo | None = None
    device_id: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("Storage volume id cannot be empty")
        if self.device_id is not None and not self.device_id.strip():
            raise ValueError("Storage volume device_id cannot be empty")


StorageVolume = Volume

__all__ = ["StorageVolume", "Volume"]
