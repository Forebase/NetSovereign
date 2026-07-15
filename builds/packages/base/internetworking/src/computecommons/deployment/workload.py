from __future__ import annotations

from dataclasses import dataclass
from warnings import warn

from computecommons.deployment._warnings import NotImplementedWarning


@dataclass(frozen=True, slots=True)
class Workload:
    id: str
    name: str | None = None

    def __post_init__(self) -> None:
        warn("Workload is a v0.1 skeleton and is not implemented", NotImplementedWarning, stacklevel=2)
        if not self.id.strip():
            raise ValueError("Workload id cannot be empty")


__all__ = ["Workload"]
