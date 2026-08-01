"""Semantic validation, intentionally separate from Pydantic structural parsing."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from .authority import AuthorityKind, ResourceClass, ScopeKind
from .base import DomainModel
from .specification import WorldSpec


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class Diagnostic(DomainModel):
    code: str
    severity: Severity
    location: str
    message: str


_COMPATIBLE: dict[ResourceClass, set[AuthorityKind]] = {
    ResourceClass.WORLD: {AuthorityKind.WORLD_ROOT},
    ResourceClass.NAME: {AuthorityKind.ROOT_NAMING, AuthorityKind.NAMING_REGISTRY},
    ResourceClass.NUMBER: {AuthorityKind.NUMBERING},
    ResourceClass.ORGANISATION: {AuthorityKind.ORGANISATION_REGISTRY},
    ResourceClass.DOMAIN: {AuthorityKind.ROOT_NAMING, AuthorityKind.NAMING_REGISTRY},
    ResourceClass.REGISTRATION: {AuthorityKind.REGISTRAR},
    ResourceClass.CERTIFICATE: {AuthorityKind.TRUST},
    ResourceClass.PLATFORM_IDENTITY: {AuthorityKind.PLATFORM_IDENTITY},
    ResourceClass.INWORLD_IDENTITY: {AuthorityKind.INWORLD_IDENTITY},
    ResourceClass.ROUTE: {AuthorityKind.TRANSIT},
    ResourceClass.MAIL_DOMAIN: {AuthorityKind.MAIL},
    ResourceClass.SERVICE: {AuthorityKind.SERVICE_CATALOGUE},
}


def _duplicates(items: list[Any], namespace: str) -> list[Diagnostic]:
    seen: set[str] = set()
    out: list[Diagnostic] = []
    for i, item in enumerate(items):
        identifier = str(item.id)
        if identifier in seen:
            out.append(
                Diagnostic(
                    code="duplicate_id",
                    severity=Severity.ERROR,
                    location=f"{namespace}[{i}].id",
                    message=f"duplicate {namespace} ID: {identifier}",
                )
            )
        seen.add(identifier)
    return out


def validate_spec(spec: WorldSpec) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for name in (
        "institutions",
        "authorities",
        "mandates",
        "resources",
        "registrations",
        "allocations",
        "grants",
        "delegations",
        "capabilities",
    ):
        diagnostics.extend(_duplicates(getattr(spec, name), name))
    institutions = {x.id for x in spec.institutions}
    authorities = {x.id: x for x in spec.authorities}
    for i, authority in enumerate(spec.authorities):
        if authority.operator_institution_id not in institutions:
            diagnostics.append(
                Diagnostic(
                    code="missing_operator",
                    severity=Severity.ERROR,
                    location=f"authorities[{i}].operator",
                    message=f"institution {authority.operator_institution_id!r} does not exist",
                )
            )
        if (
            authority.scope.reference
            and authority.scope.kind == ScopeKind.ORG
            and authority.scope.reference not in institutions
        ):
            diagnostics.append(
                Diagnostic(
                    code="invalid_scope_reference",
                    severity=Severity.ERROR,
                    location=f"authorities[{i}].scope.reference",
                    message="organisation scope references a missing institution",
                )
            )
    mandated: set[str] = set()
    for i, mandate in enumerate(spec.mandates):
        mandate_authority = authorities.get(mandate.authority_id)
        if not mandate_authority:
            diagnostics.append(
                Diagnostic(
                    code="broken_mandate_authority",
                    severity=Severity.ERROR,
                    location=f"mandates[{i}].authority",
                    message="mandate references a missing authority",
                )
            )
            continue
        mandated.add(mandate_authority.id)
        for mandate_resource in mandate.resource_classes:
            if mandate_authority.kind not in _COMPATIBLE[mandate_resource]:
                diagnostics.append(
                    Diagnostic(
                        code="incompatible_mandate_resource",
                        severity=Severity.ERROR,
                        location=f"mandates[{i}].resources",
                        message=f"{mandate_authority.kind} cannot govern {mandate_resource}",
                    )
                )
    for i, governed in enumerate(spec.resources):
        governed_authority = authorities.get(governed.authority_id)
        if governed_authority is None:
            diagnostics.append(
                Diagnostic(
                    code="missing_resource_authority",
                    severity=Severity.ERROR,
                    location=f"resources[{i}].authority",
                    message="resource references a missing authority",
                )
            )
        elif governed_authority.kind not in _COMPATIBLE[governed.resource_class]:
            diagnostics.append(
                Diagnostic(
                    code="incompatible_resource_authority",
                    severity=Severity.ERROR,
                    location=f"resources[{i}].authority",
                    message="resource and authority kinds are incompatible",
                )
            )
        for field, expected, code in (
            (
                governed.registry_authority_id,
                {AuthorityKind.ORGANISATION_REGISTRY, AuthorityKind.NAMING_REGISTRY},
                "invalid_registry_reference",
            ),
            (
                governed.registrar_authority_id,
                {AuthorityKind.REGISTRAR},
                "invalid_registrar_reference",
            ),
        ):
            if field and (field not in authorities or authorities[field].kind not in expected):
                diagnostics.append(
                    Diagnostic(
                        code=code,
                        severity=Severity.ERROR,
                        location=f"resources[{i}]",
                        message=f"invalid authority reference: {field}",
                    )
                )
    for current_authority in spec.authorities:
        status = current_authority.lifecycle.status if current_authority.lifecycle else "active"
        if status == "active" and current_authority.id not in mandated:
            diagnostics.append(
                Diagnostic(
                    code="authority_without_mandate",
                    severity=Severity.WARNING,
                    location=f"authorities.{current_authority.id}",
                    message="active authority has no explicit mandate; assurance is incomplete",
                )
            )
    peer_ids = {p.id for p in spec.boundary.peers}
    for i, item in enumerate(spec.boundary.authority_imports):
        if item.peer_id not in peer_ids:
            diagnostics.append(
                Diagnostic(
                    code="missing_import_peer",
                    severity=Severity.ERROR,
                    location=f"boundary.authority_imports[{i}].peer_id",
                    message="import references an undeclared peer",
                )
            )
    return diagnostics


def has_errors(diagnostics: list[Diagnostic]) -> bool:
    return any(item.severity == Severity.ERROR for item in diagnostics)
