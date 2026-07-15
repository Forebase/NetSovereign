from __future__ import annotations

from dataclasses import dataclass

from computecommons.units import ByteSize


@dataclass(frozen=True, slots=True)
class MemoryInfo:
    total: ByteSize
    available: ByteSize | None = None
    page_size: ByteSize | None = None
    swap_total: ByteSize | None = None
    swap_available: ByteSize | None = None

    def __post_init__(self) -> None:
        if self.available is not None and self.available > self.total:
            raise ValueError("available memory cannot exceed total memory")
        if (
            self.swap_total is not None
            and self.swap_available is not None
            and self.swap_available > self.swap_total
        ):
            raise ValueError("available swap cannot exceed total swap")


__all__ = ["MemoryInfo"]
