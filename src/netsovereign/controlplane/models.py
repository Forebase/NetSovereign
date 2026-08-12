"""Provider-neutral durable control-plane records.

These records intentionally do not import a database or provider implementation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from ..base import DomainModel
from ..canonical import CANONICALIZATION_PROFILE, digest
from ..manifest import build_manifest
from ..planning import AdmissionDecision, AdmissionStatus, verify_admission_integrity
from ..specification import WorldSpec

CONTROL_PLANE_SCHEMA_VERSION = 4
_SECRET_TERMS = ("password", "secret", "token", "private_key", "credential")


def now_utc() -> datetime:
    return datetime.now(UTC)


def _contains_secret(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            any(term in str(key).lower() for term in _SECRET_TERMS) or _contains_secret(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_secret(item) for item in value)
    return False


def _require_aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("control-plane timestamps must be timezone-aware")
    return value


class LegacyAdmissionRecord(DomainModel):
    """Explicit read adapter for v0.4 prototype records; never admission proof."""

    status: Literal["accepted", "rejected"]


class DesiredRevision(DomainModel):
    world_id: str
    revision_id: str
    parent_revision_id: str | None = None
    schema_version: str
    declaration_digest: str
    declaration: dict[str, Any]
    accepted_at: datetime
    admission: AdmissionDecision | LegacyAdmissionRecord
    actor: str | None = None
    authority_manifest_digest: str
    boundary_policy_digest: str | None = None
    compatibility: dict[str, Any] = Field(default_factory=dict)
    status: str = "accepted"
    declared_revision: str | None = None
    canonical_intent_digest: str | None = None
    materialization_digest: str | None = None
    manifest_digest: str | None = None
    admission_decision_digest: str | None = None
    canonicalization_profile: str = CANONICALIZATION_PROFILE

    _accepted_at_is_aware = field_validator("accepted_at")(_require_aware)


def desired_revision_from_admission(
    decision: AdmissionDecision,
    proposal: WorldSpec,
    *,
    accepted_at: datetime,
    actor: str | None = None,
) -> DesiredRevision:
    """The only integrity-preserving v0.2 -> control-plane activation adapter."""

    verify_admission_integrity(decision)
    if decision.status != AdmissionStatus.ADMITTED or not decision.admitted:
        raise ValueError("only an admitted decision can create desired state")
    if decision.approval_gates:
        raise ValueError("outstanding approval gates cannot create desired state")
    declaration = proposal.model_dump(mode="json", by_alias=True)
    if (
        proposal.world.id != decision.proposed.world_id
        or proposal.world.revision != decision.proposed.revision
    ):
        raise ValueError("proposal identity does not match admission")
    if digest(declaration) != decision.proposed.declaration_digest:
        raise ValueError("proposal declaration digest does not match admission")
    manifest_digest = digest(build_manifest(proposal))
    if manifest_digest != decision.proposed.manifest_digest:
        raise ValueError("proposal manifest digest does not match admission")
    if decision.proposed.parent_revision != decision.current.revision:
        raise ValueError("proposal parent is not the accepted revision")
    return DesiredRevision(
        world_id=proposal.world.id,
        revision_id=decision.proposed.revision_record_id,
        parent_revision_id=decision.current.revision_record_id,
        declared_revision=proposal.world.revision,
        schema_version=proposal.api_version,
        declaration_digest=decision.proposed.declaration_digest,
        canonical_intent_digest=decision.proposed.canonical_intent_digest,
        materialization_digest=decision.proposed.materialization_digest,
        manifest_digest=manifest_digest,
        declaration=declaration,
        accepted_at=accepted_at,
        admission=decision,
        admission_decision_digest=decision.decision_digest,
        actor=actor,
        authority_manifest_digest=manifest_digest,
        status="admitted",
    )


class AuthoritativeRecord(DomainModel):
    record_id: str
    world_id: str
    kind: str
    authority_id: str
    mandate_id: str | None = None
    desired_revision_id: str
    decision_reference: str
    status: str
    version: int = Field(ge=1)
    lifecycle: dict[str, Any] = Field(default_factory=dict)
    value: dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime


class ObservedRecord(DomainModel):
    observation_id: str
    world_id: str
    resource_id: str
    provider_id: str
    binding_id: str
    capability: str
    provider_resource_id: str | None = None
    observation_type: str
    representation: Any = None
    digest: str | None = None
    health: str = "unknown"
    conformance: str = "unknown"
    observed_at: datetime
    stale_after: datetime | None = None
    execution_run_id: str | None = None
    operation_id: str | None = None

    _timestamps_are_aware = field_validator("observed_at", "stale_after")(_require_aware)


class LockLease(DomainModel):
    key: str
    owner: str
    acquired_at: datetime
    expires_at: datetime
    fencing_token: int
    renewed_at: datetime | None = None
    released_at: datetime | None = None
    release_reason: str | None = None

    _timestamps_are_aware = field_validator(
        "acquired_at", "expires_at", "renewed_at", "released_at"
    )(_require_aware)

    @model_validator(mode="after")
    def validate_interval(self) -> LockLease:
        if self.expires_at < self.acquired_at:
            raise ValueError("lease expiry cannot precede acquisition")
        return self


class Checkpoint(DomainModel):
    checkpoint_id: str
    world_id: str
    desired_revision_id: str
    plan_fingerprint: str
    run_id: str
    completed_operations: list[str]
    incomplete_operations: list[str]
    latest_observation_ids: list[str]
    compensation: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    reason: str
    schema_version: int = CONTROL_PLANE_SCHEMA_VERSION
    previous_checkpoint_id: str | None = None

    _created_at_is_aware = field_validator("created_at")(_require_aware)

    @model_validator(mode="after")
    def reject_secrets(self) -> Checkpoint:
        if _contains_secret(self.compensation):
            raise ValueError("checkpoint compensation state must not contain secrets")
        return self


class ReconciliationRecord(DomainModel):
    reconciliation_id: str
    world_id: str
    trigger: str
    desired_revision_id: str
    observed_snapshot_id: str | None = None
    admission: dict[str, Any] = Field(default_factory=dict)
    plan: dict[str, Any] = Field(default_factory=dict)
    executable_plan_id: str | None = None
    execution_run_id: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    result: str = "running"
    drift_summary: dict[str, int] = Field(default_factory=dict)
    conformance_summary: dict[str, Any] = Field(default_factory=dict)

    _timestamps_are_aware = field_validator("started_at", "completed_at")(_require_aware)


class DriftClassification(StrEnum):
    MISSING = "missing_resource"
    UNEXPECTED = "unexpected_resource"
    CHANGED = "changed_resource"
    UNHEALTHY = "unhealthy_resource"
    UNVERIFIABLE = "unverifiable_resource"
    STALE = "stale_observation"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    CONFORMANT = "conformant_resource"


class DriftRecord(DomainModel):
    drift_id: str
    world_id: str
    resource_id: str
    desired_revision_id: str
    expected_digest: str | None
    observed_digest: str | None
    provider_id: str
    capability: str
    classification: DriftClassification
    severity: str
    first_detected_at: datetime
    last_detected_at: datetime
    status: str = "open"
    reconciliation_id: str | None = None

    _timestamps_are_aware = field_validator("first_detected_at", "last_detected_at")(_require_aware)
