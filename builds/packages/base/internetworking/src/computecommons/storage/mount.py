from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MountPoint:
    path: str
    device: str | None = None
    filesystem_type: str | None = None
    read_only: bool = False

    def __post_init__(self) -> None:
        if not self.path.startswith("/"):
            raise ValueError("Mount path must be absolute")
