from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FilesystemInfo:
    type: str
    label: str | None = None
    uuid: str | None = None
    mount_options: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.type.strip():
            raise ValueError("Filesystem type cannot be empty")
        if any(not option.strip() for option in self.mount_options):
            raise ValueError("Filesystem mount_options cannot contain empty values")
        object.__setattr__(self, "mount_options", tuple(self.mount_options))


FileSystem = FilesystemInfo

__all__ = ["FileSystem", "FilesystemInfo"]
