"""Pure compilation of admitted intent plans into provider-bound plans."""

from __future__ import annotations

from typing import Any

from ..canonical import digest
from ..planning import ReconciliationPlan
from ..providers.contracts import CapabilityRequirement
from ..providers.registry import ProviderRegistry
from .models import ExecutableOperation, ExecutablePlan, FailurePosture, RetryPolicy


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
