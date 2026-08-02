"""NetSovereign sovereign domain foundation."""

from .manifest import WorldManifest, build_manifest
from .planning import (
    AdmissionDecision,
    AdmissionStatus,
    ApprovalEvidence,
    ObservedStateSnapshot,
    ParentRevisionReference,
    ReconciliationPlan,
    admit_change,
    build_plan,
    compare_worlds,
    verify_admission_integrity,
    verify_plan_integrity,
)
from .specification import WorldSpec
from .validation import Diagnostic, validate_spec

__all__ = [
    "AdmissionDecision",
    "AdmissionStatus",
    "ApprovalEvidence",
    "Diagnostic",
    "ObservedStateSnapshot",
    "ParentRevisionReference",
    "ReconciliationPlan",
    "WorldManifest",
    "WorldSpec",
    "admit_change",
    "build_manifest",
    "build_plan",
    "compare_worlds",
    "validate_spec",
    "verify_admission_integrity",
    "verify_plan_integrity",
]
__version__ = "0.4.1"
