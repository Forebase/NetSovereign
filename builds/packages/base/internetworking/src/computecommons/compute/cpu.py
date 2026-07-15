from __future__ import annotations

from dataclasses import dataclass

from computecommons.enums import CPUArchitecture, Endianness
from computecommons.units import Frequency


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


__all__ = ["CPUInfo"]
