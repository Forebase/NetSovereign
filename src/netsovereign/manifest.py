"""Deterministic world manifest, authority graph, and explanation."""

from __future__ import annotations

from typing import Any

from .authority import Authority, Institution, Mandate
from .base import DomainModel
from .boundary import ResolverPolicy, derive_resolver_policy
from .specification import AutonomyDeclaration, ProviderBinding, WorldSpec
from .validation import Diagnostic, has_errors, validate_spec


class GraphNode(DomainModel):
    id: str
    type: str
    attributes: dict[str, Any] = {}


class GraphEdge(DomainModel):
    source: str
    target: str
    type: str


class AuthorityGraph(DomainModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class AssuranceResult(DomainModel):
    claim: str
    result: str
    detail: str


class WorldManifest(DomainModel):
    api_version: str = "netsovereign.io/manifest/v0alpha2"
    world_id: str
    name: str
    revision: str
    lifecycle: str
    autonomy: AutonomyDeclaration
    institutions: list[Institution]
    authorities: list[Authority]
    authority_sources: dict[str, list[str]]
    primary_authority_roles: dict[str, str]
    mandates: list[Mandate]
    uncovered_authorities: list[str]
    boundary_posture: dict[str, str]
    resolver: ResolverPolicy
    imports: list[dict[str, Any]]
    exports: list[str]
    required_capabilities: list[str]
    deferred_capabilities: list[str]
    provider_bindings: list[ProviderBinding]
    external_dependencies: list[dict[str, Any]]
    assurance: list[AssuranceResult]
    warnings: list[Diagnostic]
    authority_graph: AuthorityGraph


def authority_graph(spec: WorldSpec) -> AuthorityGraph:
    nodes = [
        GraphNode(id=f"institution:{x.id}", type="institution", attributes={"name": x.name})
        for x in spec.institutions
    ]
    nodes += [
        GraphNode(id=f"authority:{x.id}", type="authority", attributes={"kind": x.kind})
        for x in spec.authorities
    ]
    nodes += [
        GraphNode(id=f"resource:{x.id}", type="resource", attributes={"class": x.resource_class})
        for x in spec.resources
    ]
    edges = [
        GraphEdge(
            source=f"institution:{x.operator_institution_id}",
            target=f"authority:{x.id}",
            type="operates",
        )
        for x in spec.authorities
    ]
    edges += [
        GraphEdge(
            source=f"authority:{x.authority_id}", target=f"mandate:{x.id}", type="holds_mandate"
        )
        for x in spec.mandates
    ]
    edges += [
        GraphEdge(source=f"authority:{x.authority_id}", target=f"resource:{x.id}", type="governs")
        for x in spec.resources
    ]
    edges += [
        GraphEdge(
            source=f"authority:{x.registrar_authority_id}",
            target=f"authority:{x.registry_authority_id}",
            type="submits_to",
        )
        for x in spec.resources
        if x.registrar_authority_id and x.registry_authority_id
    ]
    edges += [
        GraphEdge(
            source=f"world:{spec.world.id}", target=f"peer:{x.peer_id}", type="imports_authority"
        )
        for x in spec.boundary.authority_imports
    ]
    return AuthorityGraph(
        nodes=sorted(nodes, key=lambda x: x.id),
        edges=sorted(edges, key=lambda x: (x.source, x.target, x.type)),
    )


def build_manifest(spec: WorldSpec) -> WorldManifest:
    diagnostics = validate_spec(spec)
    if has_errors(diagnostics):
        raise ValueError("cannot generate a manifest from a semantically invalid world")
    mandated = {x.authority_id for x in spec.mandates}
    uncovered = sorted(
        x.id
        for x in spec.authorities
        if (not x.lifecycle or x.lifecycle.status == "active") and x.id not in mandated
    )
    sources: dict[str, list[str]] = {}
    roles: dict[str, str] = {}
    for item in spec.authorities:
        sources.setdefault(str(item.source), []).append(item.id)
        roles.setdefault(str(item.kind), item.id)
    sources = {key: sorted(value) for key, value in sorted(sources.items())}
    assurance = [
        AssuranceResult(
            claim=claim,
            result="declared_unverified",
            detail="v0.1 records this target but does not enforce runtime guarantees",
        )
        for claim in spec.autonomy.claims
    ]
    if uncovered:
        assurance.append(
            AssuranceResult(
                claim="mandate coverage",
                result="incomplete",
                detail=f"No explicit mandate: {', '.join(uncovered)}",
            )
        )
    return WorldManifest(
        world_id=spec.world.id,
        name=spec.world.name,
        revision=spec.world.revision,
        lifecycle=spec.world.lifecycle,
        autonomy=spec.autonomy,
        institutions=spec.institutions,
        authorities=spec.authorities,
        authority_sources=sources,
        primary_authority_roles=dict(sorted(roles.items())),
        mandates=spec.mandates,
        uncovered_authorities=uncovered,
        boundary_posture={
            "real_internet": spec.boundary.real_internet,
            "cross_world": spec.boundary.cross_world,
        },
        resolver=derive_resolver_policy(spec.boundary),
        imports=[x.model_dump(mode="json") for x in spec.boundary.authority_imports],
        exports=sorted(spec.boundary.authority_exports),
        required_capabilities=sorted(x.id for x in spec.capabilities if x.status == "required"),
        deferred_capabilities=sorted(x.id for x in spec.capabilities if x.status == "deferred"),
        provider_bindings=spec.provider_bindings,
        external_dependencies=[x.model_dump(mode="json") for x in spec.external_dependencies],
        assurance=assurance,
        warnings=[x for x in diagnostics if x.severity == "warning"],
        authority_graph=authority_graph(spec),
    )


def explain_manifest(manifest: WorldManifest) -> str:
    lines = [
        f"World {manifest.name} ({manifest.world_id}), revision {manifest.revision}, is {manifest.lifecycle}.",
        f"Autonomy target: {manifest.autonomy.target}.",
        "Institutions and authorities:",
    ]
    operators = {x.id: x.name for x in manifest.institutions}
    for item in manifest.authorities:
        mandate_ids = [x.id for x in manifest.mandates if x.authority_id == item.id]
        lines.append(
            f"- {item.id}: {item.kind} ({item.source}), operated by {operators.get(item.operator_institution_id, item.operator_institution_id)}; scope={item.scope.kind}; controls={', '.join(item.controls)}; mandates={', '.join(mandate_ids) or 'none'}"
        )
    lines += [
        f"Boundary: internet={manifest.boundary_posture['real_internet']}, cross-world={manifest.boundary_posture['cross_world']}.",
        f"Resolver order: {', '.join(manifest.resolver.ordering)}; imported trust recognised={str(manifest.resolver.imported_trust_recognised).lower()}.",
        f"Capabilities: required={', '.join(manifest.required_capabilities) or 'none'}; deferred={', '.join(manifest.deferred_capabilities) or 'none'}.",
        f"Imports={len(manifest.imports)}; exports={', '.join(manifest.exports) or 'none'}; external dependencies={len(manifest.external_dependencies)}.",
        f"Provider bindings ({len(manifest.provider_bindings)}) are replaceable materialisation choices, not canonical world meaning.",
    ]
    lines.extend(f"Assurance {x.result}: {x.claim} — {x.detail}" for x in manifest.assurance)
    return "\n".join(lines)
