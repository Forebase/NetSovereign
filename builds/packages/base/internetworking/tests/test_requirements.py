from dataclasses import FrozenInstanceError

import pytest

from computecommons.base import Capability as BaseCapability
from computecommons.identity import QualifiedName
from computecommons.requirements import (
    Capability as RequirementsCapability,
)
from computecommons.requirements import (
    CapabilityRequirement,
    MatchReport,
    MatchStatus,
    RequirementMatch,
)


def test_match_report_required_and_optional() -> None:
    required = CapabilityRequirement(QualifiedName("network", "ipv6"))
    optional = CapabilityRequirement(QualifiedName("cpu", "avx512"), optional=True)
    report = MatchReport(
        (
            RequirementMatch(required, MatchStatus.SATISFIED),
            RequirementMatch(optional, MatchStatus.UNSATISFIED),
        )
    )
    assert report.satisfied


def test_capability_imports_share_base_type() -> None:
    capability: BaseCapability[object] = BaseCapability(
        QualifiedName("network", "ipv6"), properties={"stable": True}
    )

    assert RequirementsCapability is BaseCapability
    assert capability.name == QualifiedName("network", "ipv6")
    assert capability.properties["stable"] is True


def test_base_capability_is_immutable_value_object() -> None:
    capability = BaseCapability[str](
        QualifiedName("network", "ipv6"),
        version="1",
        value="enabled",
        properties={"stable": True},
    )

    with pytest.raises(FrozenInstanceError):
        capability.version = "2"  # type: ignore[misc]
    with pytest.raises(TypeError):
        capability.properties["stable"] = False  # type: ignore[index]

    assert capability.name == QualifiedName("network", "ipv6")
    assert capability.value == "enabled"


def test_requirement_match_uses_base_capability() -> None:
    requirement = CapabilityRequirement(QualifiedName("network", "ipv6"))
    capability: RequirementsCapability[object] = RequirementsCapability(
        QualifiedName("network", "ipv6"), version="1"
    )
    match = RequirementMatch(requirement, MatchStatus.SATISFIED, capability=capability)

    assert isinstance(match.capability, BaseCapability)


def test_capability_requirement_is_immutable_value_object() -> None:
    requirement = CapabilityRequirement(
        QualifiedName("network", "ipv6"),
        minimum_version="1",
        required_properties={"stable": True},
    )

    with pytest.raises(FrozenInstanceError):
        requirement.minimum_version = "2"  # type: ignore[misc]
    with pytest.raises(TypeError):
        requirement.required_properties["stable"] = False  # type: ignore[index]

    assert requirement.name == QualifiedName("network", "ipv6")
    assert requirement.required_properties["stable"] is True
