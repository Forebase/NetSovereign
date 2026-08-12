"""Serializable execution plans, state, evidence, and reports."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from ..base import DomainModel
from ..planning import PlanPredicate, Reversibility
from ..providers.contracts import (
    CapabilityRequirement,
    FailureClass,
    ObservationResult,
    ProviderResult,
)


class FailurePosture(StrEnum):
    STOP = "stop"
    COMPENSATE_ALL = "compensate_all"
    CONTINUE_INDEPENDENT = "continue_independent"
    CLEANUP = "best_effort_cleanup"


class OperationState(StrEnum):
    PENDING = "pending"
    VALIDATED = "validated"
    READY = "ready"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    OBSERVING = "observing"
    VERIFIED = "verified"
    RETRY_WAIT = "retry_wait"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


TERMINAL_STATES = {
    OperationState.VERIFIED,
    OperationState.COMPENSATED,
    OperationState.ROLLED_BACK,
    OperationState.FAILED,
    OperationState.CANCELLED,
    OperationState.SKIPPED,
}
TRANSITIONS: dict[OperationState, set[OperationState]] = {
    OperationState.PENDING: {
        OperationState.VALIDATED,
        OperationState.FAILED,
        OperationState.SKIPPED,
    },
    OperationState.VALIDATED: {OperationState.READY, OperationState.FAILED},
    OperationState.READY: {
        OperationState.RUNNING,
        OperationState.SUCCEEDED,
        OperationState.FAILED,
    },
    OperationState.RUNNING: {
        OperationState.SUCCEEDED,
        OperationState.RETRY_WAIT,
        OperationState.FAILED,
    },
    OperationState.SUCCEEDED: {OperationState.OBSERVING, OperationState.COMPENSATING},
    OperationState.OBSERVING: {OperationState.VERIFIED, OperationState.FAILED},
    OperationState.RETRY_WAIT: {OperationState.RUNNING, OperationState.FAILED},
    OperationState.VERIFIED: {OperationState.COMPENSATING, OperationState.ROLLING_BACK},
    OperationState.COMPENSATING: {OperationState.COMPENSATED, OperationState.FAILED},
    OperationState.ROLLING_BACK: {OperationState.ROLLED_BACK, OperationState.FAILED},
}


class PlanStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partially_succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class RetryPolicy(DomainModel):
    maximum_attempts: int = Field(default=1, ge=1)
    delay_seconds: float = Field(default=0, ge=0)
    retryable: set[FailureClass] = Field(
        default_factory=lambda: {FailureClass.TRANSIENT, FailureClass.TIMEOUT}
    )


class ExecutableOperation(DomainModel):
    id: str
    source_step_id: str
    authority_id: str | None
    mandate_id: str | None
    target: str
    operation_type: str
    capability: CapabilityRequirement
    provider_id: str
    provider_binding_id: str
    depends_on: list[str]
    preconditions: list[PlanPredicate]
    expected: Any
    idempotency_key: str
    retry_policy: RetryPolicy
    failure_posture: FailurePosture
    dry_run_compatible: bool
    order: int
    reversibility: Reversibility = Reversibility.UNKNOWN
    prior_value: Any = None
    expected_outcome_digest: str = ""
    provider_idempotent: bool = True
    provider_compensation: bool = True


class ExecutablePlan(DomainModel):
    id: str
    source_plan_id: str
    world_id: str
    from_revision: str
    desired_revision: str
    fingerprint: str
    operations: list[ExecutableOperation]
    admission_decision_digest: str = ""


class Transition(DomainModel):
    from_state: OperationState
    to_state: OperationState
    at: datetime
    reason: str


class Attempt(DomainModel):
    number: int
    started_at: datetime
    completed_at: datetime | None = None
    result: ProviderResult | None = None


class EvidenceKind(StrEnum):
    VALIDATION = "provider_validation"
    APPLICATION = "provider_application"
    OBSERVATION = "provider_observation"
    CONFORMANCE = "conformance"
    COMPENSATION = "compensation"
    FAILURE = "execution_failure"
    SIMULATION = "simulation"


_SECRET_KEYS = {"password", "secret", "token", "private_key", "credential"}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]"
            if any(word in key.lower() for word in _SECRET_KEYS)
            else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class Evidence(DomainModel):
    id: str
    run_id: str
    operation_id: str
    provider_id: str
    capability_id: str
    authority_id: str | None
    mandate_id: str | None
    target_resource: str
    desired_revision: str
    kind: EvidenceKind
    timestamp: datetime
    payload: dict[str, Any]
    sensitivity: str = "redacted"


class OperationExecution(DomainModel):
    operation_id: str
    state: OperationState = OperationState.PENDING
    attempts: list[Attempt] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    provider_result: ProviderResult | None = None
    observation: ObservationResult | None = None
    failure: FailureClass | None = None
    simulated: bool = False

    def transition(self, target: OperationState, reason: str, now: datetime) -> None:
        if target not in TRANSITIONS.get(self.state, set()):
            raise ValueError(f"invalid transition {self.state} -> {target}")
        self.transitions.append(
            Transition(from_state=self.state, to_state=target, at=now, reason=reason)
        )
        self.state = target


class ExecutionRun(DomainModel):
    id: str
    plan_id: str
    plan_fingerprint: str
    desired_revision: str
    dry_run: bool
    created_at: datetime
    operations: dict[str, OperationExecution]
    evidence: list[Evidence] = Field(default_factory=list)

    @property
    def status(self) -> PlanStatus:
        states = {item.state for item in self.operations.values()}
        if not states:
            return PlanStatus.SUCCEEDED
        if states and states <= {OperationState.VERIFIED}:
            return PlanStatus.SUCCEEDED
        if states and states <= {OperationState.COMPENSATED}:
            return PlanStatus.ROLLED_BACK
        if OperationState.CANCELLED in states:
            return PlanStatus.CANCELLED
        if OperationState.FAILED in states:
            return (
                PlanStatus.PARTIAL
                if states & {OperationState.VERIFIED, OperationState.COMPENSATED}
                else PlanStatus.FAILED
            )
        if states == {OperationState.PENDING}:
            return PlanStatus.PENDING
        return PlanStatus.RUNNING


class ExecutionReport(DomainModel):
    run: ExecutionRun
    status: PlanStatus
    explanation: str
