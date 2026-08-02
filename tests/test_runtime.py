import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from netsovereign.planning import admit_change, build_plan
from netsovereign.providers.contracts import CapabilityRequirement, FailureClass
from netsovereign.providers.fake import FakeProvider
from netsovereign.providers.registry import ProviderRegistry, ProviderResolutionError
from netsovereign.runtime import (
    FailurePosture,
    InMemoryExecutionRepository,
    OperationExecution,
    OperationState,
    RetryPolicy,
    RuntimeExecutor,
    compile_plan,
)
from netsovereign.specification import WorldSpec

ROOT = Path(__file__).parents[1]


def admitted_plan(two=False):
    current_data = yaml.safe_load((ROOT / "examples/minimal/world.yaml").read_text())
    proposed_data = deepcopy(current_data)
    proposed_data["world"]["revision"] = "2"
    proposed_data["providerBindings"][0]["provider"] = "fake"
    current = WorldSpec.model_validate(current_data)
    proposed = WorldSpec.model_validate(proposed_data)
    plan = build_plan(admit_change(current, proposed))
    if two:
        second = plan.steps[0].model_copy(
            update={"id": plan.steps[0].id + "-second", "target": "resources/second"}
        )
        plan.steps.append(second)
    return current, proposed, plan


def setup(provider=None):
    registry = ProviderRegistry()
    registry.register(provider or FakeProvider())
    return registry


def run(awaitable):
    return asyncio.run(awaitable)


def test_registry_contract_and_resolution_errors():
    provider = FakeProvider()
    registry = setup(provider)
    assert registry.resolve(CapabilityRequirement(id="resource.manage")).describe().id == "fake"
    assert registry.resolve(CapabilityRequirement(id="resource.manage"), "fake") is provider
    with pytest.raises(ProviderResolutionError, match="registered"):
        registry.register(provider)
    with pytest.raises(ProviderResolutionError) as absent:
        registry.resolve(CapabilityRequirement(id="resource.manage"), "absent")
    assert absent.value.code == "requested_provider_absent"
    with pytest.raises(ProviderResolutionError) as missing:
        registry.resolve(CapabilityRequirement(id="missing"))
    assert missing.value.code == "no_provider_supports_capability"
    with pytest.raises(ProviderResolutionError) as incompatible:
        registry.resolve(CapabilityRequirement(id="resource.manage", version="2.0"))
    assert incompatible.value.code == "capability_version_incompatible"
    registry.register(FakeProvider("other"))
    with pytest.raises(ProviderResolutionError) as ambiguous:
        registry.resolve(CapabilityRequirement(id="resource.manage"))
    assert ambiguous.value.code == "ambiguous_provider"
    provider.available = False
    with pytest.raises(ProviderResolutionError) as unavailable:
        setup(provider).resolve(CapabilityRequirement(id="resource.manage"))
    assert unavailable.value.code == "provider_unavailable"


def test_compilation_is_stable_preserves_provenance_and_does_not_mutate():
    _, _, plan = admitted_plan()
    original = plan.model_dump(mode="json")
    first = compile_plan(plan, setup())
    second = compile_plan(plan, setup())
    assert first == second and first.fingerprint == second.fingerprint
    assert plan.model_dump(mode="json") == original
    operation = first.operations[0]
    step = plan.steps[0]
    assert (operation.authority_id, operation.mandate_id, operation.target) == (
        step.authority_id,
        step.mandate_id,
        step.target,
    )
    broken = plan.model_copy(deep=True)
    broken.steps[0].depends_on = [broken.steps[0].id]
    with pytest.raises(ValueError, match="dependency_cycle"):
        compile_plan(broken, setup())


def test_state_machine_fails_closed_and_records_time():
    now = datetime.now(UTC)
    record = OperationExecution(operation_id="one")
    record.transition(OperationState.VALIDATED, "ok", now)
    assert record.transitions[0].at == now
    with pytest.raises(ValueError, match="invalid transition"):
        record.transition(OperationState.VERIFIED, "skip", now)


def test_apply_observe_evidence_and_idempotent_reexecution():
    _, _, plan = admitted_plan()
    provider = FakeProvider()
    registry = setup(provider)
    executable = compile_plan(plan, registry)
    repository = InMemoryExecutionRepository()
    executor = RuntimeExecutor(registry, repository)
    report = run(executor.execute(executable))
    assert report.status == "succeeded"
    operation = report.run.operations[executable.operations[0].id]
    assert operation.provider_result and operation.observation and operation.state == "verified"
    assert {item.kind for item in report.run.evidence} >= {
        "provider_validation",
        "provider_application",
        "provider_observation",
        "conformance",
    }
    count = len([call for call in provider.call_history if call[0] == "apply"])
    resumed = run(executor.execute(executable, run_id=report.run.id))
    assert resumed.status == "succeeded"
    assert len([call for call in provider.call_history if call[0] == "apply"]) == count
    evidence = report.run.evidence[0]
    assert {"authority_id", "mandate_id", "target_resource", "desired_revision"} <= set(
        evidence.model_dump()
    )


def test_dry_run_validates_without_mutation_and_reports_prediction():
    _, _, plan = admitted_plan()
    provider = FakeProvider()
    registry = setup(provider)
    report = run(
        RuntimeExecutor(registry, InMemoryExecutionRepository()).execute(
            compile_plan(plan, registry), dry_run=True
        )
    )
    assert report.status == "succeeded" and provider.state == {}
    assert not any(call[0] == "apply" for call in provider.call_history)
    assert any(item.kind == "simulation" for item in report.run.evidence)


def test_validation_observation_and_retry_failure_semantics():
    _, _, plan = admitted_plan()
    provider = FakeProvider()
    registry = setup(provider)
    executable = compile_plan(plan, registry, retry_policy=RetryPolicy(maximum_attempts=2))
    op = executable.operations[0]
    provider.inject_failure(op.id, FailureClass.TRANSIENT)
    report = run(
        RuntimeExecutor(
            registry, InMemoryExecutionRepository(), delay=lambda _: asyncio.sleep(0)
        ).execute(executable)
    )
    assert report.status == "succeeded" and len(report.run.operations[op.id].attempts) == 2
    provider.observation_mismatches.add(op.id)
    second = run(RuntimeExecutor(registry, InMemoryExecutionRepository()).execute(executable))
    assert second.status == "failed"
    assert second.run.operations[op.id].failure == "observation_mismatch"


def test_partial_failure_compensates_completed_operations_in_reverse_order():
    _, _, plan = admitted_plan(two=True)
    provider = FakeProvider()
    registry = setup(provider)
    executable = compile_plan(plan, registry, failure_posture=FailurePosture.COMPENSATE_ALL)
    assert len(executable.operations) >= 2
    provider.inject_failure(executable.operations[-1].id, FailureClass.PERMANENT)
    report = run(RuntimeExecutor(registry, InMemoryExecutionRepository()).execute(executable))
    compensated = [item for item in report.run.operations.values() if item.state == "compensated"]
    assert compensated and not provider.state
    calls = [op_id for action, op_id in provider.call_history if action == "compensate"]
    assert calls == [item.id for item in reversed(executable.operations[:-1])]


def test_interruption_after_apply_resumes_by_observation_without_duplicate():
    _, _, plan = admitted_plan()
    provider = FakeProvider()
    registry = setup(provider)
    executable = compile_plan(plan, registry)
    repository = InMemoryExecutionRepository()
    run_record = repository.create(executable, False, datetime.now(UTC))
    operation = executable.operations[0]
    record = run_record.operations[operation.id]
    record.transition(OperationState.VALIDATED, "validated", datetime.now(UTC))
    record.transition(OperationState.READY, "ready", datetime.now(UTC))
    record.transition(OperationState.RUNNING, "interrupted apply", datetime.now(UTC))
    context = __import__(
        "netsovereign.providers.contracts", fromlist=["ProviderContext"]
    ).ProviderContext(
        run_id=run_record.id, operation_id=operation.id, idempotency_key=operation.idempotency_key
    )
    run(provider.apply(operation, context))
    report = run(RuntimeExecutor(registry, repository).execute(executable, run_id=run_record.id))
    assert report.status == "succeeded"
    assert len([call for call in provider.call_history if call[0] == "apply"]) == 1
    changed = executable.model_copy(update={"fingerprint": "changed"})
    with pytest.raises(ValueError):
        run(RuntimeExecutor(registry, repository).execute(changed, run_id=run_record.id))
