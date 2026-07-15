from computecommons.identity import QualifiedName
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
