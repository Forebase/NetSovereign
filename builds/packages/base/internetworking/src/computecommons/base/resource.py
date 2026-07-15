from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from computecommons.base.entity import Entity
from computecommons.base.protocols import Provider
from computecommons.identity import QualifiedName


@dataclass(frozen=True, slots=True)
class Resource:
    """Stable base-layer identity for an addressable compute resource."""

    entity: Entity
    kind: QualifiedName
    provider: Provider[Any] | None = None
