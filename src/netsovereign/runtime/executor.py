"""Sequential runtime executor for provider-bound plans."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from ..canonical import digest
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
