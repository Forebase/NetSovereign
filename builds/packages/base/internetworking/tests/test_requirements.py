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
    capability = BaseCapability(QualifiedName("network", "ipv6"), properties={"stable": True})

    assert RequirementsCapability is BaseCapability
    assert capability.name == QualifiedName("network", "ipv6")
    assert capability.properties["stable"] is True


def test_requirement_match_uses_base_capability() -> None:
    requirement = CapabilityRequirement(QualifiedName("network", "ipv6"))
    capability = RequirementsCapability(QualifiedName("network", "ipv6"), version="1")
    match = RequirementMatch(requirement, MatchStatus.SATISFIED, capability=capability)

    assert isinstance(match.capability, BaseCapability)
