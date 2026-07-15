from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from computecommons.base.capability import Capability
from computecommons.base.resource import Resource


@dataclass(frozen=True, slots=True)
class Component:
    """Runtime or infrastructure component attached to a resource."""

    resource: Resource
    state: Any | None = None
    capabilities: tuple[Capability[Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
