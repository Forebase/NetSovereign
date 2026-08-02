"""Focused revision, drift, reconciliation, and recovery coordination."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from .models import (
    DesiredRevision,
    DriftClassification,
    DriftRecord,
    LockLease,
    ObservedRecord,
)
from .repository import SQLiteControlPlaneRepository


def _digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


class DriftDetector:
    """Deterministically compares provider-neutral expected and observed resources."""

    def compare(
        self,
        revision: DesiredRevision,
        expected: dict[str, dict[str, Any]],
        observed: list[ObservedRecord],
        at: datetime,
    ) -> list[DriftRecord]:
        latest: dict[str, ObservedRecord] = {}
        for item in sorted(observed, key=lambda row: (row.observed_at, row.observation_id)):
            latest[item.resource_id] = item
        records: list[DriftRecord] = []
        for resource_id in sorted(set(expected) | set(latest)):
            wanted, actual = expected.get(resource_id), latest.get(resource_id)
            expected_digest = _digest(wanted) if wanted is not None else None
            if actual is None:
                classification = DriftClassification.MISSING
                provider, capability, observed_digest = "unbound", "unknown", None
            elif wanted is None:
                classification = DriftClassification.UNEXPECTED
                provider, capability, observed_digest = (
                    actual.provider_id,
                    actual.capability,
                    actual.digest,
                )
            elif actual.stale_after and actual.stale_after <= at:
                classification = DriftClassification.STALE
                provider, capability, observed_digest = (
                    actual.provider_id,
                    actual.capability,
                    actual.digest,
                )
            elif actual.health == "unavailable":
                classification = DriftClassification.PROVIDER_UNAVAILABLE
                provider, capability, observed_digest = (
                    actual.provider_id,
                    actual.capability,
                    actual.digest,
                )
            elif actual.health == "unhealthy":
                classification = DriftClassification.UNHEALTHY
                provider, capability, observed_digest = (
                    actual.provider_id,
                    actual.capability,
                    actual.digest,
                )
            elif actual.digest is None:
                classification = DriftClassification.UNVERIFIABLE
                provider, capability, observed_digest = actual.provider_id, actual.capability, None
            elif actual.digest != expected_digest:
                classification = DriftClassification.CHANGED
                provider, capability, observed_digest = (
                    actual.provider_id,
                    actual.capability,
                    actual.digest,
                )
            else:
                classification = DriftClassification.CONFORMANT
                provider, capability, observed_digest = (
                    actual.provider_id,
                    actual.capability,
                    actual.digest,
                )
            identity = _digest([revision.revision_id, resource_id, classification])[:24]
            records.append(
                DriftRecord(
                    drift_id=f"drift-{identity}",
                    world_id=revision.world_id,
                    resource_id=resource_id,
                    desired_revision_id=revision.revision_id,
                    expected_digest=expected_digest,
                    observed_digest=observed_digest,
                    provider_id=provider,
                    capability=capability,
                    classification=classification,
                    severity="info"
                    if classification == DriftClassification.CONFORMANT
                    else "warning",
                    first_detected_at=at,
                    last_detected_at=at,
                )
            )
        return records


class ControlPlaneService:
    """Small façade; provider calls remain outside repository transactions."""

    def __init__(self, repository: SQLiteControlPlaneRepository):
        self.repository = repository
        self.drift = DriftDetector()

    def accept_revision(self, revision: DesiredRevision) -> DesiredRevision:
        if revision.status != "accepted" or revision.admission.get("status") == "rejected":
            self.repository.put_immutable("desired", revision.revision_id, revision)
            self.repository.connection.commit()
            return revision
        active = self.repository.active_revision(revision.world_id)
        if active and revision.parent_revision_id != active.revision_id:
            raise ValueError("desired revision does not descend from the active revision")
        with self.repository.transaction():
            self.repository.put_immutable("desired", revision.revision_id, revision)
            self.repository.set_active_revision(revision.world_id, revision.revision_id)
        return revision

    def inspect_drift(self, world_id: str, at: datetime) -> list[DriftRecord]:
        revision = self.repository.active_revision(world_id)
        if revision is None:
            raise KeyError(f"no active desired revision for {world_id}")
        expected = revision.declaration.get("resources", {})
        observed = [
            o for o in self.repository.list("observed", ObservedRecord) if o.world_id == world_id
        ]
        records = self.drift.compare(revision, expected, observed, at)
        with self.repository.transaction():
            for item in records:
                self.repository.put_immutable("drift", item.drift_id, item)
        return records

    def acquire_world(
        self, world_id: str, owner: str, at: datetime, seconds: int = 30
    ) -> LockLease:
        lease = LockLease(
            key=f"world:{world_id}",
            owner=owner,
            acquired_at=at,
            expires_at=at + timedelta(seconds=seconds),
            fencing_token=0,
        )
        granted = self.repository.acquire_lock(lease)
        if granted is None:
            raise RuntimeError(f"world {world_id} is already being reconciled")
        return granted

    def recovery_report(self) -> dict[str, Any]:
        runs = self.repository.incomplete_reconciliations()
        return {
            "incomplete": [r.reconciliation_id for r in runs],
            "recommendation": "observe uncertain operations before retrying" if runs else "none",
        }
