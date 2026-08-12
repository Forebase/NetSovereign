"""Provider-neutral runtime public API.

The implementation is split by responsibility while this module preserves the
original v0.3 import surface.
"""

from .compiler import compile_plan
from .executor import RuntimeExecutor, RuntimeFacts, offline_demo_facts
from .models import (
    TERMINAL_STATES,
    TRANSITIONS,
    Attempt,
    Evidence,
    EvidenceKind,
    ExecutableOperation,
    ExecutablePlan,
    ExecutionReport,
    ExecutionRun,
    FailurePosture,
    OperationExecution,
    OperationState,
    PlanStatus,
    RetryPolicy,
    Transition,
)
from .repository import ExecutionRepository, InMemoryExecutionRepository

__all__ = [
    "Attempt",
    "Evidence",
    "EvidenceKind",
    "ExecutableOperation",
    "ExecutablePlan",
    "ExecutionReport",
    "ExecutionRepository",
    "ExecutionRun",
    "FailurePosture",
    "InMemoryExecutionRepository",
    "OperationExecution",
    "OperationState",
    "PlanStatus",
    "RetryPolicy",
    "RuntimeExecutor",
    "RuntimeFacts",
    "TERMINAL_STATES",
    "TRANSITIONS",
    "Transition",
    "compile_plan",
    "offline_demo_facts",
]
