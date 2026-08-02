import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from netsovereign.authority import Authority
from netsovereign.boundary import BoundaryPolicy, TrustBundle, derive_resolver_policy
from netsovereign.cli import app
from netsovereign.defaults import default_authorities, default_institutions
from netsovereign.io import load_spec
from netsovereign.manifest import build_manifest
from netsovereign.specification import WorldSpec
from netsovereign.validation import has_errors, validate_spec

ROOT = Path(__file__).parents[1]


def test_example_round_trip_and_manifest():
    spec = load_spec(ROOT / "examples/minimal/world.yaml")
    assert (
        WorldSpec.model_validate(spec.model_dump(by_alias=True)).model_dump() == spec.model_dump()
    )
    assert not has_errors(validate_spec(spec))
    manifest = build_manifest(spec)
    assert manifest.world_id == "minimal" and manifest.authority_graph.edges
    assert manifest.provider_bindings[0].replaceable is True


def test_defaults_deterministic_and_local():
    assert default_authorities() == default_authorities()
    assert len(default_institutions()) == 1
    assert all(a.source == "local" for a in default_authorities())
    assert {a.lifecycle.status for a in default_authorities()[-2:]} == {"deferred"}


@pytest.mark.parametrize(
    "field,value", [("kind", "dns_server"), ("source", "coredns"), ("scope", {"kind": "planet"})]
)
def test_authority_enums_reject(field, value):
    data = {
        "id": "a",
        "kind": "world_root",
        "operator": "i",
        "scope": {"kind": "world"},
        "controls": ["declare"],
    }
    data[field] = value
    with pytest.raises(ValidationError):
        Authority.model_validate(data)


def test_provider_fields_rejected_from_domain():
    with pytest.raises(ValidationError):
        Authority.model_validate(
            {
                "id": "a",
                "kind": "world_root",
                "operator": "i",
                "scope": {"kind": "world"},
                "controls": ["declare"],
                "provider": "x",
            }
        )


@pytest.mark.parametrize("name", ["isolated", "shadowed", "mirrored", "peered", "federated"])
def test_boundary_fixtures(name):
    policy = BoundaryPolicy.model_validate(
        yaml.safe_load((ROOT / f"examples/boundaries/{name}.yaml").read_text())
    )
    resolver = derive_resolver_policy(policy)
    assert resolver.ordering
    if name == "peered":
        assert not resolver.imported_trust_recognised
    if name == "federated":
        assert resolver.imported_trust_recognised


def test_empty_imports_and_bad_federation():
    assert BoundaryPolicy().authority_imports == []
    with pytest.raises(ValidationError):
        TrustBundle(peer_id="p", mode="federated", provenance="x")
    with pytest.raises(ValidationError):
        BoundaryPolicy(real_internet="isolated", approved_upstream_resolvers=["ambient"])
    with pytest.raises(ValidationError):
        BoundaryPolicy.model_validate(
            {
                "cross_world": "peered",
                "peers": [{"id": "p"}],
                "authority_imports": [
                    {
                        "peer_id": "p",
                        "mode": "federated",
                        "oidc_issuer": "https://issuer.invalid",
                        "provenance": "test",
                    }
                ],
            }
        )


def test_boundary_rejects_duplicate_peers_and_exports_without_federation():
    with pytest.raises(ValidationError, match="peer identifiers must be unique"):
        BoundaryPolicy.model_validate(
            {
                "cross_world": "peered",
                "peers": [{"id": "duplicate"}, {"id": "duplicate"}],
            }
        )
    with pytest.raises(ValidationError, match="imports, or exports"):
        BoundaryPolicy(cross_world="none", authority_exports=["root-naming"])
    with pytest.raises(ValidationError, match="exports require federated"):
        BoundaryPolicy(
            cross_world="peered",
            peers=[{"id": "peer"}],
            authority_exports=["root-naming"],
        )


def test_semantic_failures_and_duplicates():
    spec = load_spec(ROOT / "examples/invalid/broken-operator.yaml")
    assert {d.code for d in validate_spec(spec)} >= {
        "missing_operator",
        "authority_without_mandate",
    }
    data = yaml.safe_load((ROOT / "examples/minimal/world.yaml").read_text())
    data["institutions"].append(data["institutions"][0])
    assert "duplicate_id" in {d.code for d in validate_spec(WorldSpec.model_validate(data))}


def test_schema_stable():
    expected = json.loads((ROOT / "schemas/world-v0alpha2.schema.json").read_text())
    assert expected == WorldSpec.model_json_schema(by_alias=True)


def test_foundational_relationships_are_validated_and_preserved():
    data = yaml.safe_load((ROOT / "examples/minimal/world.yaml").read_text())
    data["registrations"] = [
        {
            "id": "reg",
            "resource_id": "root-zone",
            "registry_authority_id": "naming-registry",
            "registrar_authority_id": "default-registrar",
        }
    ]
    data["allocations"] = [
        {
            "id": "allocation",
            "resource_id": "root-zone",
            "authority_id": "root-naming",
            "recipient": "world-administration",
        }
    ]
    data["grants"] = [
        {
            "id": "grant",
            "authority_id": "root-naming",
            "grantee": "world-administration",
            "actions": ["declare"],
        }
    ]
    data["delegations"] = [
        {
            "id": "delegation",
            "from_authority_id": "root-naming",
            "to_authority_id": "naming-registry",
            "resource_classes": ["name"],
        }
    ]
    spec = WorldSpec.model_validate(data)
    assert not has_errors(validate_spec(spec))
    manifest = build_manifest(spec)
    assert [item.id for item in manifest.registrations] == ["reg"]
    assert [item.id for item in manifest.allocations] == ["allocation"]
    assert [item.id for item in manifest.grants] == ["grant"]
    assert [item.id for item in manifest.delegations] == ["delegation"]
    node_ids = {node.id for node in manifest.authority_graph.nodes}
    assert all(
        edge.source in node_ids and edge.target in node_ids
        for edge in manifest.authority_graph.edges
    )


@pytest.mark.parametrize(
    ("collection", "value", "code"),
    [
        (
            "registrations",
            {
                "id": "x",
                "resource_id": "missing",
                "registry_authority_id": "naming-registry",
                "registrar_authority_id": "default-registrar",
            },
            "missing_registration_resource",
        ),
        (
            "allocations",
            {"id": "x", "resource_id": "root-zone", "authority_id": "missing", "recipient": "x"},
            "missing_allocation_authority",
        ),
        (
            "grants",
            {"id": "x", "authority_id": "missing", "grantee": "x", "actions": ["declare"]},
            "missing_grant_authority",
        ),
        (
            "delegations",
            {
                "id": "x",
                "from_authority_id": "missing",
                "to_authority_id": "root-naming",
                "resource_classes": ["name"],
            },
            "missing_delegation_source",
        ),
    ],
)
def test_broken_foundational_references(collection, value, code):
    data = yaml.safe_load((ROOT / "examples/minimal/world.yaml").read_text())
    data[collection] = [value]
    assert code in {item.code for item in validate_spec(WorldSpec.model_validate(data))}


def test_mandate_action_must_be_controlled():
    data = yaml.safe_load((ROOT / "examples/minimal/world.yaml").read_text())
    data["mandates"][0]["actions"] = ["revoke"]
    assert "mandate_action_not_controlled" in {
        item.code for item in validate_spec(WorldSpec.model_validate(data))
    }


def test_provider_binding_requires_declared_capability():
    data = yaml.safe_load((ROOT / "examples/minimal/world.yaml").read_text())
    data["providerBindings"][0]["capability"] = "misspelled-capability"
    diagnostics = validate_spec(WorldSpec.model_validate(data))
    assert "missing_binding_capability" in {item.code for item in diagnostics}
    assert has_errors(diagnostics)


def test_delegation_target_must_support_resource_class():
    data = yaml.safe_load((ROOT / "examples/minimal/world.yaml").read_text())
    data["delegations"] = [
        {
            "id": "bad-target",
            "from_authority_id": "root-naming",
            "to_authority_id": "transit",
            "resource_classes": ["name"],
        }
    ]
    diagnostics = validate_spec(WorldSpec.model_validate(data))
    assert "incompatible_delegation_target" in {item.code for item in diagnostics}
    assert has_errors(diagnostics)


def test_cli_success_failure_and_output():
    runner = CliRunner()
    path = str(ROOT / "examples/minimal/world.yaml")
    assert runner.invoke(app, ["validate", path]).exit_code == 0
    result = runner.invoke(app, ["manifest", path])
    assert result.exit_code == 0 and '"world_id": "minimal"' in result.stdout
    result = runner.invoke(app, ["explain", path])
    assert result.exit_code == 0 and "replaceable materialisation" in result.stdout
    assert (
        runner.invoke(
            app, ["validate", str(ROOT / "examples/invalid/broken-operator.yaml")]
        ).exit_code
        == 1
    )
