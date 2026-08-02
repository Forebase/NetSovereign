"""Compilation and execution of admitted plans against injected providers.

This module is intentionally in-memory and sequential.  It is a durable-*style*
contract, not the durable control plane or reconciliation daemon planned later.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol
from uuid import uuid4

from pydantic import Field

from .base import DomainModel
from .canonical import digest
from .planning import ReconciliationPlan
from .providers.contracts import (
    CapabilityRequirement,
    FailureClass,
    ObservationResult,
    ProviderContext,
    ProviderResult,
)
from .providers.registry import ProviderRegistry


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
    preconditions: list[dict[str, Any]]
    expected: Any
    idempotency_key: str
    retry_policy: RetryPolicy
    failure_posture: FailurePosture
    dry_run_compatible: bool
    order: int


class ExecutablePlan(DomainModel):
    id: str
    source_plan_id: str
    world_id: str
    from_revision: str
    desired_revision: str
    fingerprint: str
    operations: list[ExecutableOperation]


def _ordered_steps(plan: ReconciliationPlan) -> list[Any]:
    by_id = {step.id: step for step in plan.steps}
    remaining = set(by_id)
    ordered: list[Any] = []
    while remaining:
        ready = sorted(
            item for item in remaining if set(by_id[item].depends_on) <= {x.id for x in ordered}
        )
        if not ready:
            raise ValueError("dependency_cycle")
        for item in ready:
            ordered.append(by_id[item])
            remaining.remove(item)
    return ordered


def compile_plan(
    plan: ReconciliationPlan,
    registry: ProviderRegistry,
    bindings: dict[str, str] | None = None,
    *,
    retry_policy: RetryPolicy | None = None,
    failure_posture: FailurePosture = FailurePosture.STOP,
) -> ExecutablePlan:
    """Purely bind a copied v0.2 plan; providers are described but never invoked."""
    if not plan.admitted:
        raise ValueError("only admitted plans can be compiled")
    operations: list[ExecutableOperation] = []
    for order, step in enumerate(_ordered_steps(plan)):
        requirement = CapabilityRequirement(id="resource.manage")
        requested = (bindings or {}).get(step.id)
        provider = registry.resolve(requirement, requested)
        descriptor = provider.describe()
        expected = step.expected_outcomes[0].value if step.expected_outcomes else None
        stable = {"plan": plan.plan_digest, "step": step.id, "provider": descriptor.id}
        operations.append(
            ExecutableOperation(
                id="operation-" + digest(stable)[:16],
                source_step_id=step.id,
                authority_id=step.authority_id,
                mandate_id=step.mandate_id,
                target=step.target,
                operation_type=step.action,
                capability=requirement,
                provider_id=descriptor.id,
                provider_binding_id=descriptor.binding_id,
                depends_on=list(step.depends_on),
                preconditions=[item.model_dump(mode="json") for item in step.preconditions],
                expected=expected,
                idempotency_key=digest({**stable, "expected": expected}),
                retry_policy=retry_policy or RetryPolicy(),
                failure_posture=failure_posture,
                dry_run_compatible=next(
                    x for x in descriptor.capabilities if x.id == requirement.id
                ).dry_run,
                order=order,
            )
        )
    core = {
        "source": plan.plan_digest,
        "from": plan.from_revision,
        "to": plan.to_revision,
        "operations": [item.model_dump(mode="json") for item in operations],
    }
    fingerprint = digest(core)
    return ExecutablePlan(
        id="execution-plan-" + fingerprint[:16],
        source_plan_id=plan.plan_digest,
        world_id=plan.world_id,
        from_revision=plan.from_revision,
        desired_revision=plan.to_revision,
        fingerprint=fingerprint,
        operations=operations,
    )


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


class ExecutionRepository(Protocol):
    def create(self, plan: ExecutablePlan, dry_run: bool, now: datetime) -> ExecutionRun: ...
    def get(self, run_id: str) -> ExecutionRun: ...


class InMemoryExecutionRepository:
    def __init__(self) -> None:
        self.runs: dict[str, ExecutionRun] = {}

    def create(self, plan: ExecutablePlan, dry_run: bool, now: datetime) -> ExecutionRun:
        run = ExecutionRun(
            id=str(uuid4()),
            plan_id=plan.id,
            plan_fingerprint=plan.fingerprint,
            desired_revision=plan.desired_revision,
            dry_run=dry_run,
            created_at=now,
            operations={
                item.id: OperationExecution(operation_id=item.id) for item in plan.operations
            },
        )
        self.runs[run.id] = run
        return run

    def get(self, run_id: str) -> ExecutionRun:
        return self.runs[run_id]

    def list_by_status(self, run_id: str, status: OperationState) -> list[OperationExecution]:
        return [item for item in self.get(run_id).operations.values() if item.state == status]


Clock = Callable[[], datetime]
Delay = Callable[[float], Awaitable[None]]


class RuntimeExecutor:
    def __init__(
        self,
        registry: ProviderRegistry,
        repository: InMemoryExecutionRepository,
        *,
        clock: Clock | None = None,
        delay: Delay | None = None,
    ) -> None:
        self.registry = registry
        self.repository = repository
        self.clock = clock or (lambda: datetime.now(UTC))
        self.delay = delay or asyncio.sleep

    def _evidence(
        self,
        run: ExecutionRun,
        operation: ExecutableOperation,
        kind: EvidenceKind,
        payload: dict[str, Any],
    ) -> None:
        stable = {"run": run.id, "operation": operation.id, "kind": kind, "n": len(run.evidence)}
        run.evidence.append(
            Evidence(
                id="evidence-" + digest(stable)[:16],
                run_id=run.id,
                operation_id=operation.id,
                provider_id=operation.provider_id,
                capability_id=operation.capability.id,
                authority_id=operation.authority_id,
                mandate_id=operation.mandate_id,
                target_resource=operation.target,
                desired_revision=run.desired_revision,
                kind=kind,
                timestamp=self.clock(),
                payload=_redact(payload),
            )
        )

    async def execute(
        self, plan: ExecutablePlan, *, dry_run: bool = False, run_id: str | None = None
    ) -> ExecutionReport:
        if (
            digest(
                {
                    "source": plan.source_plan_id,
                    "from": plan.from_revision,
                    "to": plan.desired_revision,
                    "operations": [item.model_dump(mode="json") for item in plan.operations],
                }
            )
            != plan.fingerprint
        ):
            raise ValueError("execution plan integrity check failed")
        run = (
            self.repository.get(run_id)
            if run_id
            else self.repository.create(plan, dry_run, self.clock())
        )
        if run.plan_fingerprint != plan.fingerprint or run.dry_run != dry_run:
            raise ValueError("incompatible plan or execution mode for resume")
        completed: list[ExecutableOperation] = []
        failed = False
        operations_by_step = {item.source_step_id: item for item in plan.operations}
        for operation in plan.operations:
            record = run.operations[operation.id]
            if record.state == OperationState.VERIFIED:
                completed.append(operation)
                continue
            unmet_dependencies = [
                dependency
                for dependency in operation.depends_on
                if run.operations[operations_by_step[dependency].id].state
                != OperationState.VERIFIED
            ]
            if unmet_dependencies:
                if record.state == OperationState.PENDING:
                    record.transition(
                        OperationState.SKIPPED,
                        f"dependencies not verified: {', '.join(sorted(unmet_dependencies))}",
                        self.clock(),
                    )
                continue
            if failed and operation.failure_posture != FailurePosture.CONTINUE_INDEPENDENT:
                if record.state == OperationState.PENDING:
                    record.transition(
                        OperationState.SKIPPED, "prior operation failed", self.clock()
                    )
                continue
            provider = self.registry.resolve(operation.capability, operation.provider_id)
            context = ProviderContext(
                run_id=run.id,
                operation_id=operation.id,
                idempotency_key=operation.idempotency_key,
                dry_run=dry_run,
            )
            # An interrupted apply or observation is resolved by observing before replay.
            if record.state in {OperationState.RUNNING, OperationState.OBSERVING}:
                observed = await provider.observe(operation, context)
                record.observation = observed
                self._evidence(
                    run, operation, EvidenceKind.OBSERVATION, observed.model_dump(mode="json")
                )
                if observed.matches_expected:
                    if record.state == OperationState.RUNNING:
                        record.transition(
                            OperationState.SUCCEEDED,
                            "resume observation found applied state",
                            self.clock(),
                        )
                        record.transition(
                            OperationState.OBSERVING, "verify resumed operation", self.clock()
                        )
                    record.transition(
                        OperationState.VERIFIED, "expected state observed", self.clock()
                    )
                    completed.append(operation)
                    continue
                if record.state == OperationState.OBSERVING:
                    record.failure = FailureClass.OBSERVATION_MISMATCH
                    record.transition(
                        OperationState.FAILED,
                        "resumed observation did not converge",
                        self.clock(),
                    )
                    failed = True
                    continue
            if record.state != OperationState.PENDING:
                raise ValueError(f"operation {operation.id} cannot resume from {record.state}")
            validation = await provider.validate(operation, context)
            self._evidence(
                run, operation, EvidenceKind.VALIDATION, validation.model_dump(mode="json")
            )
            if not validation.valid:
                record.failure = validation.failure
                record.transition(
                    OperationState.FAILED, validation.message or "validation failed", self.clock()
                )
                self._evidence(
                    run,
                    operation,
                    EvidenceKind.FAILURE,
                    {"failure": validation.failure, "message": validation.message},
                )
                failed = True
                continue
            record.transition(OperationState.VALIDATED, "provider validation passed", self.clock())
            record.transition(OperationState.READY, "dependencies satisfied", self.clock())
            if dry_run:
                if not operation.dry_run_compatible:
                    record.transition(
                        OperationState.FAILED, "provider does not support dry run", self.clock()
                    )
                    failed = True
                    continue
                record.simulated = True
                record.transition(
                    OperationState.SUCCEEDED, "predicted without mutation", self.clock()
                )
                record.transition(OperationState.OBSERVING, "simulation conformance", self.clock())
                record.observation = ObservationResult(
                    observed=False,
                    matches_expected=True,
                    state={"predicted_action": validation.predicted_action},
                )
                record.transition(OperationState.VERIFIED, "simulation completed", self.clock())
                self._evidence(
                    run,
                    operation,
                    EvidenceKind.SIMULATION,
                    {"predicted_action": validation.predicted_action},
                )
                completed.append(operation)
                continue
            result: ProviderResult | None = None
            for number in range(1, operation.retry_policy.maximum_attempts + 1):
                record.transition(OperationState.RUNNING, f"attempt {number}", self.clock())
                attempt = Attempt(number=number, started_at=self.clock())
                record.attempts.append(attempt)
                result = await provider.apply(operation, context)
                attempt.completed_at = self.clock()
                attempt.result = result
                record.provider_result = result
                self._evidence(
                    run, operation, EvidenceKind.APPLICATION, result.model_dump(mode="json")
                )
                if result.success:
                    record.transition(
                        OperationState.SUCCEEDED, "provider apply succeeded", self.clock()
                    )
                    break
                record.failure = result.failure
                if (
                    number < operation.retry_policy.maximum_attempts
                    and result.retryable
                    and result.failure in operation.retry_policy.retryable
                ):
                    record.transition(
                        OperationState.RETRY_WAIT, "retry policy permits retry", self.clock()
                    )
                    await self.delay(operation.retry_policy.delay_seconds)
                else:
                    record.transition(
                        OperationState.FAILED,
                        result.message or "provider apply failed",
                        self.clock(),
                    )
                    failed = True
                    break
            if not result or not result.success:
                continue
            record.transition(OperationState.OBSERVING, "observe provider state", self.clock())
            observation = await provider.observe(operation, context)
            record.observation = observation
            self._evidence(
                run, operation, EvidenceKind.OBSERVATION, observation.model_dump(mode="json")
            )
            if observation.matches_expected:
                record.transition(OperationState.VERIFIED, "expected state observed", self.clock())
                self._evidence(run, operation, EvidenceKind.CONFORMANCE, {"converged": True})
                completed.append(operation)
            else:
                record.failure = FailureClass.OBSERVATION_MISMATCH
                record.transition(
                    OperationState.FAILED, "applied state did not converge", self.clock()
                )
                failed = True
        if (
            not dry_run
            and failed
            and any(
                item.failure_posture == FailurePosture.COMPENSATE_ALL for item in plan.operations
            )
        ):
            for operation in reversed(completed):
                record = run.operations[operation.id]
                if record.simulated:
                    continue
                record.transition(
                    OperationState.COMPENSATING, "reverse-order compensation", self.clock()
                )
                provider = self.registry.get(operation.provider_id)
                result = await provider.compensate(
                    operation,
                    ProviderContext(
                        run_id=run.id,
                        operation_id=operation.id,
                        idempotency_key=operation.idempotency_key,
                    ),
                )
                self._evidence(
                    run, operation, EvidenceKind.COMPENSATION, result.model_dump(mode="json")
                )
                record.transition(
                    OperationState.COMPENSATED if result.success else OperationState.FAILED,
                    "compensation completed" if result.success else "compensation failed",
                    self.clock(),
                )
                if not result.success:
                    record.failure = FailureClass.COMPENSATION
                    break
        return ExecutionReport(
            run=run,
            status=run.status,
            explanation=f"realised revision {run.desired_revision}: {run.status}",
        )
