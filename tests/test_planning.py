import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from netsovereign.cli import app
from netsovereign.planning import (
    AdmissionDecision,
    ApprovalEvidence,
    ObservedStateSnapshot,
    ParentRevisionReference,
    ReconciliationPlan,
    accepted_revision,
    admit_change,
    build_plan,
    canonical_json,
    compare_worlds,
    digest,
)
from netsovereign.specification import ExternalDependency, WorldSpec

ROOT = Path(__file__).parents[1]


def worlds():
    current_data = yaml.safe_load((ROOT / "examples/minimal/world.yaml").read_text())
    proposed_data = deepcopy(current_data)
    proposed_data["world"]["revision"] = "2"
    proposed_data["providerBindings"][0]["provider"] = "another-replaceable-provider"
    return WorldSpec.model_validate(current_data), WorldSpec.model_validate(proposed_data)


def test_canonical_digest_is_order_independent():
    assert canonical_json({"b": 2, "a": 1}) == canonical_json({"a": 1, "b": 2})
    assert digest({"controls": ["delegate", "declare"]}) == digest(
        {"controls": ["declare", "delegate"]}
    )
    with pytest.raises(ValueError, match="non-finite"):
        digest({"invalid": float("nan")})


def test_binding_change_is_separate_and_admitted():
    current, proposed = worlds()
    changes = compare_worlds(current, proposed)
    assert [change.classification for change in changes] == ["provider_binding"]
    decision = admit_change(current, proposed)
    assert decision.admitted and not decision.approval_gates
    plan = build_plan(decision)
    assert plan.execution == "not_permitted" and len(plan.steps) == 1
    assert plan.plan_digest == build_plan(decision).plan_digest
    assert decision.current.canonical_intent_digest == decision.proposed.canonical_intent_digest
    assert decision.current.materialization_digest != decision.proposed.materialization_digest


def test_identity_change_and_deletion_are_rejected():
    current, proposed = worlds()
    proposed.authorities[0].kind = "root_naming"
    proposed.resources = []
    decision = admit_change(current, proposed)
    codes = {issue.code for issue in decision.issues}
    assert {"authority_identity_redefined", "implicit_deletion"} <= codes
    assert not decision.admitted and build_plan(decision).steps == []


def test_resource_class_change_redefines_stable_identity():
    current, proposed = worlds()
    proposed.resources[0].resource_class = "domain"
    decision = admit_change(current, proposed)
    assert "resource_identity_redefined" in {issue.code for issue in decision.issues}


def test_lifecycle_resurrection_and_authority_redefinition_are_rejected():
    current, proposed = worlds()
    current.world.lifecycle = "retired"
    proposed.world.lifecycle = "active"
    proposed.authorities[1].operator_institution_id = "different-operator"
    codes = {issue.code for issue in admit_change(current, proposed).issues}
    assert {"invalid_lifecycle_transition", "authority_identity_redefined"} <= codes


def test_autonomy_improvement_is_not_a_regression():
    current, proposed = worlds()
    current.autonomy.target = "externally_dependent"
    proposed.autonomy.target = "authority_autonomous"
    change = next(
        change for change in compare_worlds(current, proposed) if change.path == "autonomy/target"
    )
    assert change.risk != "autonomy_regression"


def test_observation_is_drift_not_authority():
    current, proposed = worlds()
    observed = ObservedStateSnapshot.model_validate(
        {
            "world_id": "minimal",
            "observed_at": "2026-01-01T00:00:00Z",
            "provenance": "offline-test",
            "facts": [{"path": "world/name", "value": "Wrong"}],
        }
    )
    decision = admit_change(current, proposed, observed)
    assert decision.admitted and decision.drift[0].classification == "observed_drift"


def test_drift_only_plan_contains_a_convergence_step():
    current, _ = worlds()
    observed = ObservedStateSnapshot.model_validate(
        {
            "world_id": "minimal",
            "observed_at": "2026-01-01T00:00:00Z",
            "provenance": "offline-test",
            "facts": [{"path": "world/name", "value": "Stale materialised name"}],
        }
    )
    decision = admit_change(current, current, observed)
    plan = build_plan(decision)
    assert decision.changes == [] and len(decision.drift) == 1
    assert plan.steps[0].action == "reconcile_drift"
    assert plan.steps[0].expected_outcomes[0].path == "world/name"
    assert plan.steps[0].expected_outcomes[0].value == current.world.name
    assert plan.steps[0].preconditions[0].kind == "accepted_revision_equals"


def test_observed_collection_path_resolves_stable_id():
    current, _ = worlds()
    resource = current.resources[0].model_dump(mode="json")
    observed = ObservedStateSnapshot.model_validate(
        {
            "world_id": "minimal",
            "observed_at": "2026-01-01T00:00:00Z",
            "provenance": "offline-test",
            "facts": [{"path": "resources/root-zone", "value": resource}],
        }
    )
    assert admit_change(current, current, observed).drift == []


def test_typed_observation_distinguishes_absent_unknown_and_null():
    current, _ = worlds()
    absent = ObservedStateSnapshot.model_validate(
        {
            "world_id": "minimal",
            "observed_at": "2026-01-01T00:00:00Z",
            "provenance": "offline-test",
            "facts": [{"path": "world/name", "status": "absent"}],
        }
    )
    decision = admit_change(current, current, absent)
    assert decision.drift[0].operation == "add"
    assert decision.drift[0].authority_id == "world-root"
    unknown = absent.model_copy(
        update={"facts": [absent.facts[0].model_copy(update={"status": "unknown"})]}
    )
    assert admit_change(current, current, unknown).drift == []
    with pytest.raises(ValidationError, match="must be unique"):
        ObservedStateSnapshot.model_validate(
            {
                "world_id": "minimal",
                "observed_at": "2026-01-01T00:00:00Z",
                "provenance": "offline-test",
                "facts": [
                    {"path": "world/name", "value": None},
                    {"path": "world/name", "status": "absent"},
                ],
            }
        )


def test_provider_configuration_arrays_remain_ordered():
    current, proposed = worlds()
    current.provider_bindings[0].configuration = {"fallbacks": ["primary", "secondary"]}
    proposed.provider_bindings[0].configuration = {"fallbacks": ["secondary", "primary"]}
    changes = compare_worlds(current, proposed)
    assert len(changes) == 1 and changes[0].classification == "provider_binding"
    assert digest(current) != digest(proposed)


def test_mandate_must_cover_action_resource_and_jurisdiction():
    current, proposed = worlds()
    proposed.resources.append(
        proposed.resources[0].model_copy(update={"id": "domain", "resource_class": "domain"})
    )
    decision = admit_change(current, proposed)
    change = next(change for change in decision.changes if change.path == "resources/domain")
    assert change.authority_id == "root-naming" and change.mandate_id is None
    assert "missing_applicable_mandate" in {issue.code for issue in decision.issues}


def test_mandate_constraints_are_typed_and_governance_is_explained():
    current, proposed = worlds()
    proposed.resources[0].registrar_authority_id = None
    change = next(
        change
        for change in compare_worlds(current, proposed)
        if change.path == "resources/root-zone"
    )
    assert change.governance is not None
    assert change.governance.action == "declare"
    assert change.governance.resource_classes == ["name"]
    with pytest.raises(ValidationError, match="unknown_constraint"):
        current.mandates[0].__class__.model_validate(
            {
                **current.mandates[0].model_dump(mode="json"),
                "constraints": {"unknown_constraint": True},
            }
        )


def test_change_and_plan_digests_bind_exact_proposed_content():
    current, first = worlds()
    second = first.model_copy(deep=True)
    first.world.name = "First proposed name"
    second.world.name = "Second proposed name"
    first_decision = admit_change(current, first)
    second_decision = admit_change(current, second)
    first_name = next(change for change in first_decision.changes if change.path == "world/name")
    second_name = next(change for change in second_decision.changes if change.path == "world/name")
    assert first_name.id != second_name.id
    assert build_plan(first_decision).plan_digest != build_plan(second_decision).plan_digest


def test_plan_dependencies_form_a_semantic_dag_not_a_linear_chain():
    current, _ = worlds()
    proposed = current.model_copy(deep=True)
    proposed.world.revision = "2"
    proposed.capabilities.append(
        proposed.capabilities[0].model_copy(update={"id": "new-capability"})
    )
    proposed.provider_bindings.append(
        proposed.provider_bindings[0].model_copy(update={"capability": "new-capability"})
    )
    plan = build_plan(admit_change(current, proposed))
    capability_step = next(
        step for step in plan.steps if step.target == "capabilities/new-capability"
    )
    binding_step = next(
        step for step in plan.steps if step.target == "provider_bindings/new-capability"
    )
    assert capability_step.depends_on == []
    assert binding_step.depends_on == [capability_step.id]


def test_approval_is_a_distinct_admission_state():
    current, proposed = worlds()
    proposed.world.name = "Approval-gated name"
    pending = admit_change(current, proposed)
    assert pending.status == "pending_approval" and not pending.admitted
    evidence = ApprovalEvidence(
        approval_id=pending.approval_gates[0],
        approved_at=datetime(2026, 1, 1, tzinfo=UTC),
        provenance="offline-review",
    )
    admitted = admit_change(current, proposed, approvals=[evidence])
    assert admitted.status == "admitted" and admitted.approval_gates == []


def test_invalid_current_world_cannot_authorise_change():
    current, proposed = worlds()
    current.provider_bindings[0].capability = "missing"
    decision = admit_change(current, proposed)
    assert decision.status == "rejected"
    assert any(issue.code.startswith("invalid_current_") for issue in decision.issues)


def test_duplicate_binding_and_dependency_keys_are_rejected():
    current, _ = worlds()
    current.provider_bindings.append(current.provider_bindings[0].model_copy())
    current.external_dependencies.extend(
        [
            ExternalDependency(id="duplicate", description="one"),
            ExternalDependency(id="duplicate", description="two"),
        ]
    )
    current = WorldSpec.model_validate(current.model_dump(mode="json", by_alias=True))
    codes = {issue.code for issue in admit_change(current, current).issues}
    assert "invalid_current_duplicate_provider_binding" in codes
    assert "invalid_current_duplicate_id" in codes


def test_stale_parent_digest_is_rejected_and_change_ids_are_full_length():
    current, proposed = worlds()
    decision = admit_change(
        current,
        proposed,
        parent=ParentRevisionReference(revision="1", declaration_digest="sha256:stale"),
    )
    assert "stale_parent_revision" in {issue.code for issue in decision.issues}
    assert len(decision.changes[0].id.removeprefix("change-")) == 64
    reference = accepted_revision(current)
    assert reference.declaration_digest == reference.world_digest


def test_cli_diff_admit_and_plan(tmp_path):
    current, proposed = worlds()
    current_path, proposed_path = tmp_path / "current.yaml", tmp_path / "proposed.yaml"
    current_path.write_text(yaml.safe_dump(current.model_dump(mode="json", by_alias=True)))
    proposed_path.write_text(yaml.safe_dump(proposed.model_dump(mode="json", by_alias=True)))
    runner = CliRunner()
    diff = runner.invoke(app, ["diff", str(current_path), str(proposed_path)])
    assert (
        diff.exit_code == 0 and json.loads(diff.stdout)[0]["classification"] == "provider_binding"
    )
    admitted = runner.invoke(app, ["admit", str(current_path), str(proposed_path)])
    assert admitted.exit_code == 0 and json.loads(admitted.stdout)["admitted"]
    plan = runner.invoke(app, ["plan", str(current_path), str(proposed_path)])
    assert plan.exit_code == 0 and json.loads(plan.stdout)["execution"] == "not_permitted"


def test_cli_pending_exit_code_and_yaml_output(tmp_path):
    current, proposed = worlds()
    proposed.world.name = "Approval required"
    current_path, proposed_path = tmp_path / "current.yaml", tmp_path / "proposed.yaml"
    output_path = tmp_path / "decision.yaml"
    current_path.write_text(yaml.safe_dump(current.model_dump(mode="json", by_alias=True)))
    proposed_path.write_text(yaml.safe_dump(proposed.model_dump(mode="json", by_alias=True)))
    result = CliRunner().invoke(
        app,
        [
            "admit",
            str(current_path),
            str(proposed_path),
            "--format",
            "yaml",
            "--output",
            str(output_path),
        ],
    )
    assert result.exit_code == 3
    assert yaml.safe_load(output_path.read_text())["status"] == "pending_approval"


@pytest.mark.parametrize(
    ("filename", "model"),
    [
        ("observed-v0.2.schema.json", ObservedStateSnapshot),
        ("admission-v0.2.schema.json", AdmissionDecision),
        ("plan-v0.2.schema.json", ReconciliationPlan),
    ],
)
def test_planning_artifact_schemas_are_stable(filename, model):
    expected = json.loads((ROOT / "schemas" / filename).read_text())
    assert expected == model.model_json_schema(by_alias=True)
