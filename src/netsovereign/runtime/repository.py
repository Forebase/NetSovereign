"""Execution-state repository contracts and the supported in-memory implementation."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import uuid4

from .models import ExecutablePlan, ExecutionRun, OperationExecution, OperationState


class ExecutionRepository(Protocol):
    def create(self, plan: ExecutablePlan, dry_run: bool, now: datetime) -> ExecutionRun: ...
    def get(self, run_id: str) -> ExecutionRun: ...


class InMemoryExecutionRepository:
    def __init__(self) -> None:
        self.runs: dict[str, ExecutionRun] = {}

    def create(self, plan: ExecutablePlan, dry_run: bool, now: datetime) -> ExecutionRun:
        run = ExecutionRun(
            id=str(uuid4()),
            plan_id=plan.id,
            plan_fingerprint=plan.fingerprint,
            desired_revision=plan.desired_revision,
            dry_run=dry_run,
            created_at=now,
            operations={
                item.id: OperationExecution(operation_id=item.id) for item in plan.operations
            },
        )
        self.runs[run.id] = run
        return run

    def get(self, run_id: str) -> ExecutionRun:
        return self.runs[run_id]

    def list_by_status(self, run_id: str, status: OperationState) -> list[OperationExecution]:
        return [item for item in self.get(run_id).operations.values() if item.state == status]
