"""Provider-neutral durable control-plane records.

These records intentionally do not import a database or provider implementation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from ..base import DomainModel


def now_utc() -> datetime:
    return datetime.now(UTC)


class DesiredRevision(DomainModel):
    world_id: str
    revision_id: str
    parent_revision_id: str | None = None
    schema_version: str
    declaration_digest: str
    declaration: dict[str, Any]
    accepted_at: datetime
    admission: dict[str, Any]
    actor: str | None = None
    authority_manifest_digest: str
    boundary_policy_digest: str | None = None
    compatibility: dict[str, Any] = Field(default_factory=dict)
    status: str = "accepted"


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


class LockLease(DomainModel):
    key: str
    owner: str
    acquired_at: datetime
    expires_at: datetime
    fencing_token: int
    renewed_at: datetime | None = None
    released_at: datetime | None = None
    release_reason: str | None = None


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
    schema_version: int = 1
    previous_checkpoint_id: str | None = None


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
