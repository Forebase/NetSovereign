"""NetSovereign sovereign domain foundation."""

from .manifest import WorldManifest, build_manifest
from .planning import (
    AdmissionDecision,
    ReconciliationPlan,
    admit_change,
    build_plan,
    compare_worlds,
)
from .specification import WorldSpec
from .validation import Diagnostic, validate_spec

__all__ = [
    "AdmissionDecision",
    "Diagnostic",
    "ReconciliationPlan",
    "WorldManifest",
    "WorldSpec",
    "admit_change",
    "build_manifest",
    "build_plan",
    "compare_worlds",
    "validate_spec",
]
__version__ = "0.2.0"
