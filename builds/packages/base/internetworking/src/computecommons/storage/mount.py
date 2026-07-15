from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Mount:
    path: str
    device: str | None = None
    filesystem_type: str | None = None
    read_only: bool = False
    options: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.path.startswith("/"):
            raise ValueError("Mount path must be absolute")
        if self.device is not None and not self.device.strip():
            raise ValueError("Mount device cannot be empty")
        if self.filesystem_type is not None and not self.filesystem_type.strip():
            raise ValueError("Mount filesystem_type cannot be empty")
        if any(not option.strip() for option in self.options):
            raise ValueError("Mount options cannot contain empty values")
        object.__setattr__(self, "options", tuple(self.options))


MountPoint = Mount

__all__ = ["Mount", "MountPoint"]
