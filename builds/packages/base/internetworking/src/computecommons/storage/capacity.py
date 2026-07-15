from __future__ import annotations

from dataclasses import dataclass

from computecommons.units import ByteSize


@dataclass(frozen=True, slots=True)
class StorageCapacity:
    total: ByteSize
    available: ByteSize | None = None

    def __post_init__(self) -> None:
        if self.available is not None and self.available > self.total:
            raise ValueError("Available capacity cannot exceed total capacity")
