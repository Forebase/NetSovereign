from __future__ import annotations

from dataclasses import dataclass

from computecommons.enums import CPUArchitecture, Endianness
from computecommons.units import ByteSize, Frequency


@dataclass(frozen=True, slots=True)
class CPUInfo:
    architecture: CPUArchitecture
    logical_processors: int
    physical_cores: int | None = None
    sockets: int | None = None
    vendor: str | None = None
    model: str | None = None
    minimum_frequency: Frequency | None = None
    maximum_frequency: Frequency | None = None
    endianness: Endianness = Endianness.UNKNOWN
    features: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        if self.logical_processors < 1:
            raise ValueError("logical_processors must be at least 1")
        if self.physical_cores is not None and self.physical_cores < 1:
            raise ValueError("physical_cores must be at least 1")
        if self.sockets is not None and self.sockets < 1:
            raise ValueError("sockets must be at least 1")
        object.__setattr__(self, "features", frozenset(self.features))


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


@dataclass(frozen=True, slots=True)
class Machine:
    hostname: str
    cpu: CPUInfo
    memory: MemoryInfo
    machine_id: str | None = None
    firmware: str | None = None
    chassis_type: str | None = None

    def __post_init__(self) -> None:
        if not self.hostname.strip():
            raise ValueError("hostname cannot be empty")
