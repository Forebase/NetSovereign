"""Institutions, authorities, mandates, and governed resources."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import Field

from .base import DomainModel


class AuthorityKind(StrEnum):
    WORLD_ROOT = "world_root"
    ROOT_NAMING = "root_naming"
    NUMBERING = "numbering"
    ORGANISATION_REGISTRY = "organisation_registry"
    NAMING_REGISTRY = "naming_registry"
    REGISTRAR = "registrar"
    TRUST = "trust"
    PLATFORM_IDENTITY = "platform_identity"
    INWORLD_IDENTITY = "inworld_identity"
    TRANSIT = "transit"
    MAIL = "mail"
    SERVICE_CATALOGUE = "service_catalogue"


class ScopeKind(StrEnum):
    WORLD = "world"
    PLATFORM = "platform"
    INWORLD = "inworld"
    ORG = "org"
    BOUNDARY = "boundary"
    PEER = "peer"
    EXTERNAL = "external"


class AuthoritySource(StrEnum):
    LOCAL = "local"
    DELEGATED_LOCAL = "delegated_local"
    MIRRORED = "mirrored"
    IMPORTED_PEER = "imported_peer"
    EXTERNAL = "external"


class LifecycleStatus(StrEnum):
    PROPOSED = "proposed"
    DEFERRED = "deferred"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    RETIRED = "retired"


class Institution(DomainModel):
    id: str
    name: str
    description: str | None = None
    status: LifecycleStatus = LifecycleStatus.ACTIVE


class AuthorityScope(DomainModel):
    kind: ScopeKind
    reference: str | None = None


class LifecycleMetadata(DomainModel):
    status: LifecycleStatus = LifecycleStatus.ACTIVE
    since: datetime | None = None
    revision: str | None = None


class Authority(DomainModel):
    id: str
    kind: AuthorityKind
    operator_institution_id: str = Field(alias="operator")
    scope: AuthorityScope
    controls: list[str] = Field(min_length=1)
    source: AuthoritySource = AuthoritySource.LOCAL
    description: str | None = None
    lifecycle: LifecycleMetadata | None = None


class ResourceClass(StrEnum):
    WORLD = "world"
    NAME = "name"
    NUMBER = "number"
    ORGANISATION = "organisation"
    DOMAIN = "domain"
    REGISTRATION = "registration"
    CERTIFICATE = "certificate"
    PLATFORM_IDENTITY = "platform_identity"
    INWORLD_IDENTITY = "inworld_identity"
    ROUTE = "route"
    MAIL_DOMAIN = "mail_domain"
    SERVICE = "service"


class Validity(DomainModel):
    not_before: datetime | None = None
    not_after: datetime | None = None


class MandateConstraints(DomainModel):
    """Portable v0.2 admission constraints."""

    operations: list[Literal["add", "modify", "remove"]] = Field(default_factory=list)
    paths: list[str] = Field(default_factory=list)
    subject_ids: list[str] = Field(default_factory=list)


class Mandate(DomainModel):
    id: str
    authority_id: str = Field(alias="authority")
    actions: list[str] = Field(min_length=1)
    resource_classes: list[ResourceClass] = Field(alias="resources", min_length=1)
    jurisdiction: str
    status: LifecycleStatus = LifecycleStatus.ACTIVE
    constraints: MandateConstraints = Field(default_factory=MandateConstraints)
    validity: Validity | None = None


class GovernedResource(DomainModel):
    id: str
    resource_class: ResourceClass = Field(alias="class")
    authority_id: str = Field(alias="authority")
    registry_authority_id: str | None = Field(default=None, alias="registry")
    registrar_authority_id: str | None = Field(default=None, alias="registrar")


class Registration(DomainModel):
    id: str
    resource_id: str
    registry_authority_id: str
    registrar_authority_id: str


class Allocation(DomainModel):
    id: str
    resource_id: str
    authority_id: str
    recipient: str


class Grant(DomainModel):
    id: str
    authority_id: str
    grantee: str
    actions: list[str]


class Delegation(DomainModel):
    id: str
    from_authority_id: str
    to_authority_id: str
    resource_classes: list[ResourceClass]
