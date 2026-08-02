"""Deterministic minimal-world domain defaults."""

from __future__ import annotations

from typing import cast

from .authority import (
    Authority,
    AuthorityKind,
    AuthorityScope,
    Institution,
    LifecycleMetadata,
    LifecycleStatus,
    ScopeKind,
)


def default_institutions() -> list[Institution]:
    return [Institution(id="world-administration", name="World Administration")]


def default_authorities() -> list[Authority]:
    """Return powers, never services or implied provider deployments."""
    definitions = [
        ("world-root", "world_root", "world", ["declare", "delegate"], "active"),
        ("root-naming", "root_naming", "world", ["declare", "delegate"], "active"),
        ("numbering", "numbering", "world", ["allocate", "revoke"], "active"),
        ("organisation-registry", "organisation_registry", "world", ["admit", "revoke"], "active"),
        ("naming-registry", "naming_registry", "world", ["admit", "delegate"], "active"),
        ("default-registrar", "registrar", "world", ["declare", "submit"], "active"),
        ("trust", "trust", "world", ["certify", "revoke"], "active"),
        ("platform-identity", "platform_identity", "platform", ["admit", "revoke"], "active"),
        ("inworld-identity", "inworld_identity", "inworld", ["admit", "revoke"], "active"),
        ("transit", "transit", "boundary", ["route", "expose"], "active"),
        ("mail", "mail", "world", ["declare"], "deferred"),
        ("service-catalogue", "service_catalogue", "world", ["declare"], "deferred"),
    ]
    return [
        Authority(
            id=id_,
            kind=cast(AuthorityKind, kind),
            operator="world-administration",
            scope=AuthorityScope(kind=cast(ScopeKind, scope)),
            controls=controls,
            lifecycle=LifecycleMetadata(status=cast(LifecycleStatus, status)),
        )
        for id_, kind, scope, controls, status in definitions
    ]


def apply_defaults(
    institutions: list[Institution], authorities: list[Authority]
) -> tuple[list[Institution], list[Authority]]:
    inst = {item.id: item for item in default_institutions()}
    inst.update({item.id: item for item in institutions})
    auth = {item.id: item for item in default_authorities()}
    auth.update({item.id: item for item in authorities})
    return list(inst.values()), list(auth.values())
