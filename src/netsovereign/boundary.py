"""Provider-independent boundary and resolver policy."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .base import DomainModel


class InternetPosture(StrEnum):
    ISOLATED = "isolated"
    SHADOWED = "shadowed"
    MIRRORED = "mirrored"
    EXPOSED = "exposed"
    CUSTOM = "custom"


class CrossWorldPosture(StrEnum):
    NONE = "none"
    PEERED = "peered"
    FEDERATED = "federated"


class Peer(DomainModel):
    id: str
    display_name: str | None = None
    dns_suffixes: list[str] = Field(default_factory=list)
    active: bool = True


class TrustBundle(DomainModel):
    peer_id: str
    display_name: str | None = None
    mode: CrossWorldPosture
    dns_suffixes: list[str] = Field(default_factory=list)
    root_ca: str | None = None
    trust_anchor: str | None = None
    oidc_issuer: str | None = None
    accepted_audiences: list[str] = Field(default_factory=list)
    mail_domains: list[str] = Field(default_factory=list)
    dkim_policy: str | None = None
    provenance: str
    revision: str | None = None
    expires_at: str | None = None

    @model_validator(mode="after")
    def coherent_import(self) -> TrustBundle:
        trust = any(
            (
                self.root_ca,
                self.trust_anchor,
                self.oidc_issuer,
                self.accepted_audiences,
                self.mail_domains,
                self.dkim_policy,
            )
        )
        if self.mode == CrossWorldPosture.PEERED and trust:
            raise ValueError("peered bundles may import discovery only, not trust")
        if self.mode == CrossWorldPosture.FEDERATED and not trust:
            raise ValueError("federated bundles require an explicit authority/trust surface")
        if self.mode == CrossWorldPosture.NONE:
            raise ValueError("an import bundle mode must be peered or federated")
        return self


class Mirror(DomainModel):
    suffix: str
    source: str


class BoundaryPolicy(DomainModel):
    real_internet: InternetPosture = InternetPosture.ISOLATED
    cross_world: CrossWorldPosture = CrossWorldPosture.NONE
    ingress: list[str] = Field(default_factory=list)
    egress: list[str] = Field(default_factory=list)
    approved_upstream_resolvers: list[str] = Field(default_factory=list)
    admit_upstreams_with_mirrors: bool = False
    mirrors: list[Mirror] = Field(default_factory=list)
    peers: list[Peer] = Field(default_factory=list)
    authority_imports: list[TrustBundle] = Field(default_factory=list)
    authority_exports: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def coherent(self) -> BoundaryPolicy:
        active = [p for p in self.peers if p.active]
        if self.real_internet == InternetPosture.ISOLATED and self.approved_upstream_resolvers:
            raise ValueError("isolated posture cannot use upstream resolvers")
        if self.real_internet == InternetPosture.SHADOWED and not self.approved_upstream_resolvers:
            raise ValueError("shadowed posture requires approved upstream resolvers")
        if self.real_internet == InternetPosture.MIRRORED and not self.mirrors:
            raise ValueError("mirrored posture requires a mirror table")
        if self.cross_world == CrossWorldPosture.NONE and (active or self.authority_imports):
            raise ValueError("cross-world none cannot have active peers or imports")
        if (
            self.cross_world in (CrossWorldPosture.PEERED, CrossWorldPosture.FEDERATED)
            and not active
        ):
            raise ValueError("peered/federated posture requires an active peer")
        if self.cross_world == CrossWorldPosture.FEDERATED and not any(
            i.mode == CrossWorldPosture.FEDERATED for i in self.authority_imports
        ):
            raise ValueError("federation requires an explicit federated authority import")
        if self.cross_world == CrossWorldPosture.PEERED and any(
            i.mode != CrossWorldPosture.PEERED for i in self.authority_imports
        ):
            raise ValueError("peered posture accepts discovery-only peered imports")
        return self


class ResolverPolicy(DomainModel):
    ordering: list[str]
    upstream_resolvers: list[str]
    upstream_enabled: bool
    peer_suffixes: dict[str, list[str]]
    imported_trust_recognised: bool


def derive_resolver_policy(policy: BoundaryPolicy) -> ResolverPolicy:
    """Purely derive resolution semantics; this performs no DNS or network activity."""
    ordering = ["local_roots"]
    upstreams = policy.approved_upstream_resolvers
    enabled = bool(upstreams)
    if policy.real_internet == InternetPosture.MIRRORED:
        ordering = ["declared_mirrors", "local_roots"]
        enabled = policy.admit_upstreams_with_mirrors and bool(upstreams)
    elif policy.real_internet == InternetPosture.SHADOWED:
        ordering = ["local_roots", "approved_upstreams"]
    if enabled and "approved_upstreams" not in ordering:
        ordering.append("approved_upstreams")
    peer_suffixes = {p.id: sorted(p.dns_suffixes) for p in policy.peers if p.active}
    if peer_suffixes:
        ordering.append("peer_suffix_delegations")
    recognised = policy.cross_world == CrossWorldPosture.FEDERATED and any(
        item.mode == CrossWorldPosture.FEDERATED for item in policy.authority_imports
    )
    return ResolverPolicy(
        ordering=ordering,
        upstream_resolvers=sorted(upstreams),
        upstream_enabled=enabled,
        peer_suffixes=dict(sorted(peer_suffixes.items())),
        imported_trust_recognised=recognised,
    )
