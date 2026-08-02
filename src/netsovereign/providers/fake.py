"""Inspectable, deterministic provider with no operational side effects."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from typing import Any

from .contracts import (
    CapabilityDeclaration,
    FailureClass,
    ObservationResult,
    ProviderContext,
    ProviderDescriptor,
    ProviderResult,
    ValidationResult,
)


class FakeProvider:
    def __init__(self, provider_id: str = "fake", *, dry_run: bool = True) -> None:
        self.provider_id = provider_id
        self.dry_run = dry_run
        self.available = True
        self.healthy = True
        self.state: dict[str, Any] = {}
        self.call_history: list[tuple[str, str]] = []
        self.failures: dict[str, list[FailureClass]] = defaultdict(list)
        self.observation_mismatches: set[str] = set()

    def describe(self) -> ProviderDescriptor:
        capabilities = [
            "resource.manage",
            "declaration.storage",
            "registration.submit",
            "registry.admit",
            "trust.manage",
            "number.allocate",
            "naming.authoritative.manage",
            "route.manage",
            "boundary.expose",
            "identity.platform.manage",
            "identity.inworld.manage",
            "mail-domain.manage",
            "service-catalogue.manage",
        ]
        return ProviderDescriptor(
            id=self.provider_id,
            version="1.0",
            binding_id=f"{self.provider_id}:memory",
            available=self.available,
            healthy=self.healthy,
            capabilities=[
                CapabilityDeclaration(id=item, dry_run=self.dry_run) for item in capabilities
            ],
        )

    def inject_failure(self, operation_id: str, failure: FailureClass) -> None:
        self.failures[operation_id].append(failure)

    async def validate(self, operation: Any, context: ProviderContext) -> ValidationResult:
        self.call_history.append(("validate", operation.id))
        if context.dry_run and not self.dry_run:
            return ValidationResult(
                valid=False,
                failure=FailureClass.CAPABILITY_UNAVAILABLE,
                message="dry run is unsupported",
            )
        if (
            self.failures[operation.id]
            and self.failures[operation.id][0] == FailureClass.VALIDATION
        ):
            self.failures[operation.id].pop(0)
            return ValidationResult(
                valid=False, failure=FailureClass.VALIDATION, message="injected"
            )
        return ValidationResult(
            valid=True,
            predicted_action=f"{operation.operation_type}:{operation.target}",
            evidence={"validated": True},
        )

    async def apply(self, operation: Any, context: ProviderContext) -> ProviderResult:
        self.call_history.append(("apply", operation.id))
        if self.failures[operation.id]:
            failure = self.failures[operation.id].pop(0)
            return ProviderResult(
                success=False,
                failure=failure,
                retryable=failure == FailureClass.TRANSIENT,
                message="injected",
            )
        resource_id = "fake-" + sha256(operation.target.encode()).hexdigest()[:12]
        if operation.operation_type in {"remove", "delete"}:
            self.state.pop(operation.target, None)
        else:
            self.state[operation.target] = operation.expected
        return ProviderResult(
            success=True,
            provider_resource_id=resource_id,
            output={"action": operation.operation_type},
            evidence={"mutated": True},
        )

    async def observe(self, operation: Any, context: ProviderContext) -> ObservationResult:
        self.call_history.append(("observe", operation.id))
        actual = self.state.get(operation.target)
        expected = operation.expected
        matches = actual == expected and operation.id not in self.observation_mismatches
        return ObservationResult(
            observed=actual is not None,
            matches_expected=matches,
            state={"value": actual},
            evidence={"matches": matches},
        )

    async def compensate(self, operation: Any, context: ProviderContext) -> ProviderResult:
        self.call_history.append(("compensate", operation.id))
        if (
            self.failures[operation.id]
            and self.failures[operation.id][0] == FailureClass.COMPENSATION
        ):
            self.failures[operation.id].pop(0)
            return ProviderResult(
                success=False, failure=FailureClass.COMPENSATION, message="injected"
            )
        if operation.prior_value is None:
            self.state.pop(operation.target, None)
        else:
            self.state[operation.target] = operation.prior_value
        return ProviderResult(success=True, evidence={"compensated": True})

    async def delete(self, operation: Any, context: ProviderContext) -> ProviderResult:
        return await self.compensate(operation, context)
