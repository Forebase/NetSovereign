"""Small, capability-oriented provider contract used by the runtime compiler."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import Field

from ..base import DomainModel


class FailureClass(StrEnum):
    VALIDATION = "validation"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    PRECONDITION = "precondition_failed"
    CONFLICT = "conflict"
    TRANSIENT = "transient_provider_failure"
    PERMANENT = "permanent_provider_failure"
    TIMEOUT = "timeout"
    OBSERVATION_MISMATCH = "observation_mismatch"
    COMPENSATION = "compensation_failure"
    INTERNAL = "internal_engine_failure"


class CapabilityRequirement(DomainModel):
    id: str
    version: str = "1.0"


class CapabilityDeclaration(DomainModel):
    id: str
    version: str = "1.0"
    dry_run: bool = True
    idempotent: bool = True
    compensation: bool = True
    limitations: list[str] = Field(default_factory=list)


class ProviderDescriptor(DomainModel):
    id: str
    version: str
    binding_id: str
    available: bool = True
    healthy: bool = True
    capabilities: list[CapabilityDeclaration]


class ProviderContext(DomainModel):
    run_id: str
    operation_id: str
    idempotency_key: str
    dry_run: bool = False
    world_id: str = ""
    source_plan_digest: str = ""
    admission_decision_digest: str = ""
    desired_revision: str = ""
    authority_id: str | None = None
    mandate_id: str | None = None
    capability_id: str = ""
    capability_version: str = ""
    provider_id: str = ""
    binding_id: str = ""
    expected_outcome_digest: str = ""
    fencing_token: int | None = None


class ValidationResult(DomainModel):
    valid: bool
    predicted_action: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    failure: FailureClass | None = None
    message: str | None = None


class ProviderResult(DomainModel):
    success: bool
    provider_resource_id: str | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    failure: FailureClass | None = None
    retryable: bool = False
    message: str | None = None


class ObservationResult(DomainModel):
    observed: bool
    matches_expected: bool
    state: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None


@runtime_checkable
class Provider(Protocol):
    def describe(self) -> ProviderDescriptor: ...
    async def validate(self, operation: Any, context: ProviderContext) -> ValidationResult: ...
    async def apply(self, operation: Any, context: ProviderContext) -> ProviderResult: ...
    async def observe(self, operation: Any, context: ProviderContext) -> ObservationResult: ...
    async def compensate(self, operation: Any, context: ProviderContext) -> ProviderResult: ...
    async def delete(self, operation: Any, context: ProviderContext) -> ProviderResult: ...
