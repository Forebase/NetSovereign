import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml

from netsovereign.controlplane.models import desired_revision_from_admission
from netsovereign.planning import admit_change, build_plan
from netsovereign.providers.fake import FakeProvider
from netsovereign.providers.registry import ProviderRegistry
from netsovereign.runtime import InMemoryExecutionRepository, RuntimeExecutor, compile_plan
from netsovereign.runtime.executor import RuntimeFacts
from netsovereign.specification import WorldSpec


def chain():
    data = yaml.safe_load((Path(__file__).parents[1] / "examples/minimal/world.yaml").read_text())
    proposed_data = deepcopy(data)
    proposed_data["world"]["revision"] = "2"
    proposed_data["providerBindings"][0]["provider"] = "fake"
    current = WorldSpec.model_validate(data)
    proposed = WorldSpec.model_validate(proposed_data)
    decision = admit_change(current, proposed)
    return proposed, decision, build_plan(decision)


def test_admission_and_plan_tampering_fail_closed():
    _, decision, plan = chain()
    decision.changes[0].explanation = "tampered"
    assert not decision.verify_integrity()
    plan.steps[0].expected_outcomes[0].value = "tampered"
    assert not plan.verify_integrity()


def test_pending_admission_cannot_activate_desired_state():
    proposed, decision, _ = chain()
    pending = decision.model_copy(update={"admitted": False, "status": "pending_approval"})
    pending.decision_digest = "tampered"
    with pytest.raises(ValueError, match="integrity"):
        desired_revision_from_admission(pending, proposed, accepted_at=datetime.now(UTC))


def test_stale_revision_precondition_prevents_provider_calls():
    _, _, plan = chain()
    provider = FakeProvider()
    registry = ProviderRegistry()
    registry.register(provider)
    executable = compile_plan(plan, registry)
    facts = RuntimeFacts(
        accepted_revision="stale",
        accepted_revision_digest="sha256:stale",
        proposed_declaration_digest=plan.proposed_revision_digest,
        active_desired_revision=plan.to_revision,
        evaluated_at=datetime.now(UTC),
    )
    report = asyncio.run(
        RuntimeExecutor(registry, InMemoryExecutionRepository()).execute(executable, facts=facts)
    )
    assert report.status == "failed"
    assert provider.call_history == []
