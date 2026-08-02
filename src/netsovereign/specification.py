"""The v0alpha2 world declaration."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from .authority import (
    Allocation,
    Authority,
    Delegation,
    GovernedResource,
    Grant,
    Institution,
    Mandate,
    Registration,
)
from .base import DomainModel
from .boundary import BoundaryPolicy


class WorldIdentity(DomainModel):
    id: str
    name: str
    revision: str
    lifecycle: Literal["proposed", "active", "suspended", "retired"] = "proposed"
    description: str | None = None


class AutonomyDeclaration(DomainModel):
    target: Literal["authority_autonomous", "partially_autonomous", "externally_dependent"]
    claims: list[str] = Field(default_factory=list)


class CapabilityRequirement(DomainModel):
    id: str
    description: str | None = None
    status: Literal["required", "deferred"] = "required"


class ProviderBinding(DomainModel):
    capability: str
    provider: str
    configuration: dict[str, Any] = Field(default_factory=dict)
    replaceable: Literal[True] = True


class ExternalDependency(DomainModel):
    id: str
    description: str
    required: bool = True


class WorldSpec(DomainModel):
    api_version: Literal["netsovereign.io/v0alpha2"] = Field(alias="apiVersion")
    kind: Literal["World"] = "World"
    world: WorldIdentity
    autonomy: AutonomyDeclaration
    institutions: list[Institution] = Field(default_factory=list)
    authorities: list[Authority] = Field(default_factory=list)
    mandates: list[Mandate] = Field(default_factory=list)
    resources: list[GovernedResource] = Field(default_factory=list)
    registrations: list[Registration] = Field(default_factory=list)
    allocations: list[Allocation] = Field(default_factory=list)
    grants: list[Grant] = Field(default_factory=list)
    delegations: list[Delegation] = Field(default_factory=list)
    capabilities: list[CapabilityRequirement] = Field(default_factory=list)
    provider_bindings: list[ProviderBinding] = Field(default_factory=list, alias="providerBindings")
    boundary: BoundaryPolicy = Field(default_factory=BoundaryPolicy)
    external_dependencies: list[ExternalDependency] = Field(
        default_factory=list, alias="externalDependencies"
    )
