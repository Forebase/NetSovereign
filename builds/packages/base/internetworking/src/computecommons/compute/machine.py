from __future__ import annotations

from dataclasses import dataclass

from computecommons.compute.cpu import CPUInfo
from computecommons.compute.memory import MemoryInfo


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


__all__ = ["Machine"]
