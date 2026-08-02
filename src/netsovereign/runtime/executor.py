"""Sequential runtime executor for provider-bound plans."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import Field, model_validator

from ..base import DomainModel
from ..canonical import digest
from ..planning import PredicateKind
from ..providers.contracts import FailureClass, ObservationResult, ProviderContext, ProviderResult
from ..providers.registry import ProviderRegistry
from .models import (
    Attempt,
    Evidence,
    EvidenceKind,
    ExecutableOperation,
    ExecutablePlan,
    ExecutionReport,
    ExecutionRun,
    FailurePosture,
    OperationState,
    _redact,
)
from .repository import InMemoryExecutionRepository

Clock = Callable[[], datetime]
Delay = Callable[[float], Awaitable[None]]


class RuntimeFacts(DomainModel):
    """Injected, immutable view of sovereign facts used by the precondition gate."""

    accepted_revision: str
    accepted_revision_digest: str
    proposed_declaration_digest: str
    active_desired_revision: str
    observations: dict[str, str] = Field(default_factory=dict)
    active_mandates: set[str] = Field(default_factory=set)
    verified_approvals: dict[str, str] = Field(default_factory=dict)
    provider_bindings: dict[str, str] = Field(default_factory=dict)
    observation_times: dict[str, datetime] = Field(default_factory=dict)
    evaluated_at: datetime

    @model_validator(mode="after")
    def timestamps_are_aware(self) -> RuntimeFacts:
        if self.evaluated_at.tzinfo is None or any(
            value.tzinfo is None for value in self.observation_times.values()
        ):
            raise ValueError("runtime fact timestamps must be timezone-aware")
        return self


def offline_demo_facts(plan: ExecutablePlan, evaluated_at: datetime) -> RuntimeFacts:
    """Explicitly synthesize facts for the non-operational CLI/demo provider only.

    Production callers must inject repository-backed facts instead. Keeping this
    unsafe convenience named and outside ``execute`` prevents accidental runtime
    authority fabrication.
    """

    predicates = [
        predicate for operation in plan.operations for predicate in operation.preconditions
    ]
    return RuntimeFacts(
        accepted_revision=plan.from_revision,
        accepted_revision_digest=next(
            (
                item.digest
                for item in predicates
                if item.kind == PredicateKind.ACCEPTED_REVISION_EQUALS
            ),
            "",
        )
        or "",
        proposed_declaration_digest=next(
            (
                item.digest
                for item in predicates
                if item.kind == PredicateKind.PROPOSED_DIGEST_EQUALS
            ),
            "",
        )
        or "",
        active_desired_revision=plan.desired_revision,
        observations={
            item.path: item.value_digest
            for item in predicates
            if item.kind == PredicateKind.OBSERVATION_EQUALS and item.path and item.value_digest
        },
        active_mandates={
            operation.mandate_id for operation in plan.operations if operation.mandate_id
        },
        verified_approvals={
            item.approval_id: item.digest
            for item in predicates
            if item.kind == PredicateKind.APPROVAL_PRESENT and item.approval_id and item.digest
        },
        provider_bindings={
            operation.source_step_id: operation.provider_binding_id for operation in plan.operations
        },
        evaluated_at=evaluated_at,
    )


def _failed_precondition(operation: ExecutableOperation, facts: RuntimeFacts) -> str | None:
    for predicate in operation.preconditions:
        ok = True
        if predicate.kind == PredicateKind.ACCEPTED_REVISION_EQUALS:
            ok = (
                predicate.revision == facts.accepted_revision
                and predicate.digest == facts.accepted_revision_digest
            )
        elif predicate.kind == PredicateKind.PROPOSED_DIGEST_EQUALS:
            ok = predicate.digest == facts.proposed_declaration_digest
        elif predicate.kind == PredicateKind.ACTIVE_DESIRED_REVISION_EQUALS:
            ok = predicate.revision == facts.active_desired_revision
        elif predicate.kind == PredicateKind.OBSERVATION_EQUALS:
            ok = (
                predicate.path is not None
                and facts.observations.get(predicate.path) == predicate.value_digest
            )
        elif predicate.kind == PredicateKind.MANDATE_ACTIVE:
            ok = predicate.mandate_id in facts.active_mandates
        elif predicate.kind == PredicateKind.APPROVAL_PRESENT:
            ok = facts.verified_approvals.get(predicate.approval_id or "") == predicate.digest
        elif predicate.kind == PredicateKind.OBSERVATION_FRESH:
            observed_at = facts.observation_times.get(predicate.path or "")
            ok = (
                observed_at is not None
                and predicate.maximum_age_seconds is not None
                and observed_at.tzinfo is not None
                and 0
                <= (facts.evaluated_at - observed_at).total_seconds()
                <= predicate.maximum_age_seconds
            )
        elif predicate.kind == PredicateKind.PROVIDER_BINDING_EQUALS:
            ok = facts.provider_bindings.get(operation.source_step_id) == predicate.binding_id
        if not ok:
            return f"{predicate.kind}:{predicate.model_dump(mode='json')}"
    return None


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
                id="evidence-" + digest(stable)[7:23],
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
        self,
        plan: ExecutablePlan,
        *,
        dry_run: bool = False,
        run_id: str | None = None,
        facts: RuntimeFacts | None = None,
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
        if facts is None and plan.operations:
            raise ValueError(
                "runtime facts are required; sovereign preconditions cannot be inferred"
            )
        assert facts is not None or not plan.operations
        for operation in plan.operations:
            assert facts is not None
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
            precondition_failure = _failed_precondition(operation, facts)
            if precondition_failure:
                record.failure = FailureClass.PRECONDITION
                record.transition(OperationState.FAILED, precondition_failure, self.clock())
                self._evidence(
                    run, operation, EvidenceKind.FAILURE, {"predicate": precondition_failure}
                )
                failed = True
                continue
            provider = self.registry.resolve(operation.capability, operation.provider_id)
            declaration = next(
                x for x in provider.describe().capabilities if x.id == operation.capability.id
            )
            if dry_run and not declaration.dry_run:
                raise ValueError("provider does not support dry run")
            context = ProviderContext(
                run_id=run.id,
                operation_id=operation.id,
                idempotency_key=operation.idempotency_key,
                dry_run=dry_run,
                world_id=plan.world_id,
                source_plan_digest=plan.source_plan_id,
                admission_decision_digest=plan.admission_decision_digest,
                desired_revision=plan.desired_revision,
                authority_id=operation.authority_id,
                mandate_id=operation.mandate_id,
                capability_id=operation.capability.id,
                capability_version=operation.capability.version,
                provider_id=operation.provider_id,
                binding_id=operation.provider_binding_id,
                expected_outcome_digest=operation.expected_outcome_digest,
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
                    and operation.provider_idempotent
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
                if not operation.provider_compensation:
                    continue
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
