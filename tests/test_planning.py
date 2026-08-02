import json
from copy import deepcopy
from pathlib import Path

import yaml
from typer.testing import CliRunner

from netsovereign.cli import app
from netsovereign.planning import (
    ObservedStateSnapshot,
    admit_change,
    build_plan,
    canonical_json,
    compare_worlds,
    digest,
)
from netsovereign.specification import WorldSpec

ROOT = Path(__file__).parents[1]


def worlds():
    current_data = yaml.safe_load((ROOT / "examples/minimal/world.yaml").read_text())
    proposed_data = deepcopy(current_data)
    proposed_data["world"]["revision"] = "2"
    proposed_data["providerBindings"][0]["provider"] = "another-replaceable-provider"
    return WorldSpec.model_validate(current_data), WorldSpec.model_validate(proposed_data)


def test_canonical_digest_is_order_independent():
    assert canonical_json({"b": [2, 1], "a": 1}) == canonical_json({"a": 1, "b": [1, 2]})
    assert digest({"b": [2, 1], "a": 1}) == digest({"a": 1, "b": [1, 2]})


def test_binding_change_is_separate_and_admitted():
    current, proposed = worlds()
    changes = compare_worlds(current, proposed)
    assert [change.classification for change in changes] == ["provider_binding"]
    decision = admit_change(current, proposed)
    assert decision.admitted and not decision.approval_gates
    plan = build_plan(decision)
    assert plan.execution == "not_permitted" and len(plan.steps) == 1
    assert plan.plan_digest == build_plan(decision).plan_digest


def test_identity_change_and_deletion_are_rejected():
    current, proposed = worlds()
    proposed.authorities[0].kind = "root_naming"
    proposed.resources = []
    decision = admit_change(current, proposed)
    codes = {issue.code for issue in decision.issues}
    assert {"authority_identity_redefined", "implicit_deletion"} <= codes
    assert not decision.admitted and build_plan(decision).steps == []


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
