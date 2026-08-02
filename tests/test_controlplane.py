from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from netsovereign.controlplane.models import (
    Checkpoint,
    DesiredRevision,
    DriftClassification,
    ObservedRecord,
)
from netsovereign.controlplane.repository import SQLiteControlPlaneRepository
from netsovereign.controlplane.service import ControlPlaneService

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def revision(revision_id: str = "r1", parent: str | None = None) -> DesiredRevision:
    return DesiredRevision(
        world_id="world",
        revision_id=revision_id,
        parent_revision_id=parent,
        schema_version="v0alpha2",
        declaration_digest=revision_id,
        declaration={"resources": {"resource": {"enabled": True}}},
        accepted_at=NOW,
        admission={"status": "accepted"},
        actor="test",
        authority_manifest_digest="authority",
        status="accepted",
    )


def test_revision_is_immutable_active_and_restart_safe(tmp_path):
    path = tmp_path / "control.db"
    first = SQLiteControlPlaneRepository(path)
    ControlPlaneService(first).accept_revision(revision())
    first.connection.close()
    second = SQLiteControlPlaneRepository(path)
    assert second.active_revision("world") == revision()
    with pytest.raises(ValueError, match="immutable"):
        second.put_immutable("desired", "r1", revision().model_copy(update={"actor": "other"}))


def test_child_history_and_rejected_revision(tmp_path):
    repo = SQLiteControlPlaneRepository(tmp_path / "cp.db")
    service = ControlPlaneService(repo)
    service.accept_revision(revision())
    service.accept_revision(revision("r2", "r1"))
    rejected = revision("bad", "r2").model_copy(
        update={"status": "rejected", "admission": {"status": "rejected"}}
    )
    service.accept_revision(rejected)
    assert repo.active_revision("world").revision_id == "r2"  # type: ignore[union-attr]
    assert len(repo.list("desired", DesiredRevision)) == 3


def test_lock_fencing_owner_and_expiry(tmp_path):
    service = ControlPlaneService(SQLiteControlPlaneRepository(tmp_path / "cp.db"))
    one = service.acquire_world("world", "one", NOW, 10)
    with pytest.raises(RuntimeError, match="already"):
        service.acquire_world("world", "two", NOW, 10)
    assert not service.repository.release_lock(one.key, "two", "wrong", NOW)
    two = service.acquire_world("world", "two", NOW + timedelta(seconds=11), 10)
    assert two.fencing_token == one.fencing_token + 1


def test_lock_fencing_survives_release_and_reacquire(tmp_path):
    service = ControlPlaneService(SQLiteControlPlaneRepository(tmp_path / "cp.db"))
    one = service.acquire_world("world", "one", NOW, 10)
    assert service.repository.release_lock(one.key, "one", "complete", NOW)
    two = service.acquire_world("world", "two", NOW, 10)
    assert two.fencing_token == one.fencing_token + 1
    assert not service.repository.release_lock(one.key, "one", "duplicate", NOW)


def test_active_same_owner_acquire_is_idempotent(tmp_path):
    service = ControlPlaneService(SQLiteControlPlaneRepository(tmp_path / "cp.db"))
    one = service.acquire_world("world", "one", NOW, 10)
    duplicate = service.acquire_world("world", "one", NOW + timedelta(seconds=1), 20)
    assert duplicate == one


@pytest.mark.parametrize(
    ("record", "classification"),
    [
        (None, DriftClassification.UNVERIFIABLE),
        ({"digest": None, "observation_type": "absent"}, DriftClassification.MISSING),
        ({"digest": "wrong"}, DriftClassification.CHANGED),
        ({"digest": None}, DriftClassification.UNVERIFIABLE),
        ({"digest": "wrong", "health": "unhealthy"}, DriftClassification.UNHEALTHY),
        ({"digest": "wrong", "health": "unavailable"}, DriftClassification.PROVIDER_UNAVAILABLE),
        ({"digest": "wrong", "stale_after": NOW}, DriftClassification.STALE),
    ],
)
def test_drift_classifications(tmp_path, record, classification):
    repo = SQLiteControlPlaneRepository(tmp_path / "cp.db")
    service = ControlPlaneService(repo)
    service.accept_revision(revision())
    if record is not None:
        observed = ObservedRecord(
            observation_id="o1",
            world_id="world",
            resource_id="resource",
            provider_id="fake",
            binding_id="fake",
            capability="test",
            observation_type=record.get("observation_type", "state"),
            representation={},
            observed_at=NOW - timedelta(seconds=1),
            health=record.get("health", "healthy"),
            digest=record["digest"],
            stale_after=record.get("stale_after"),
        )
        repo.put_immutable("observed", "o1", observed)
        repo.connection.commit()
    assert service.inspect_drift("world", NOW)[0].classification == classification


def test_list_shaped_world_resources_are_normalized(tmp_path):
    repo = SQLiteControlPlaneRepository(tmp_path / "cp.db")
    service = ControlPlaneService(repo)
    listed = revision().model_copy(
        update={"declaration": {"resources": [{"id": "resource", "enabled": True}]}}
    )
    service.accept_revision(listed)
    assert service.inspect_drift("world", NOW)[0].resource_id == "resource"


def test_repeated_drift_detection_appends_history(tmp_path):
    repo = SQLiteControlPlaneRepository(tmp_path / "cp.db")
    service = ControlPlaneService(repo)
    service.accept_revision(revision())
    first = service.inspect_drift("world", NOW)[0]
    second = service.inspect_drift("world", NOW + timedelta(seconds=1))[0]
    assert first.drift_id != second.drift_id
    assert len(repo.list("drift", type(first))) == 2


def test_active_parent_is_read_inside_write_transaction(tmp_path):
    class TransactionCheckingRepository(SQLiteControlPlaneRepository):
        checked = False

        def active_revision(self, world_id: str) -> DesiredRevision | None:
            if super().active_revision(world_id) is not None:
                self.checked = self.connection.in_transaction
            return super().active_revision(world_id)

    repo = TransactionCheckingRepository(tmp_path / "cp.db")
    service = ControlPlaneService(repo)
    service.accept_revision(revision())
    service.accept_revision(revision("r2", "r1"))
    assert repo.checked


def test_revision_acceptance_is_idempotent_and_initial_parent_fails(tmp_path):
    repo = SQLiteControlPlaneRepository(tmp_path / "cp.db")
    service = ControlPlaneService(repo)
    assert service.accept_revision(revision()) == revision()
    assert service.accept_revision(revision()) == revision()
    other = SQLiteControlPlaneRepository(tmp_path / "other.db")
    with pytest.raises(ValueError, match="initial.*parent"):
        ControlPlaneService(other).accept_revision(revision("r2", "r1"))


def test_repository_cannot_activate_revision_for_another_world(tmp_path):
    repo = SQLiteControlPlaneRepository(tmp_path / "cp.db")
    with repo.transaction():
        repo.put_immutable("desired", "r1", revision())
        with pytest.raises(ValueError, match="different world"):
            repo.set_active_revision("other", "r1")


def test_schema_version_is_upgraded_and_future_version_rejected(tmp_path):
    path = tmp_path / "cp.db"
    repo = SQLiteControlPlaneRepository(path)
    repo.connection.execute("UPDATE cp_metadata SET value='1' WHERE key='schema_version'")
    repo.connection.commit()
    repo.connection.close()
    upgraded = SQLiteControlPlaneRepository(path)
    assert upgraded.connection.execute(
        "SELECT value FROM cp_metadata WHERE key='schema_version'"
    ).fetchone() == ("4",)
    upgraded.connection.execute("UPDATE cp_metadata SET value='5' WHERE key='schema_version'")
    upgraded.connection.commit()
    upgraded.connection.close()
    with pytest.raises(RuntimeError, match="incompatible"):
        SQLiteControlPlaneRepository(path)


def test_checkpoint_rejects_secret_material():
    with pytest.raises(ValueError, match="must not contain secrets"):
        Checkpoint(
            checkpoint_id="checkpoint",
            world_id="world",
            desired_revision_id="r1",
            plan_fingerprint="fingerprint",
            run_id="run",
            completed_operations=[],
            incomplete_operations=[],
            latest_observation_ids=[],
            compensation={"access_token": "sensitive"},
            created_at=NOW,
            reason="test",
        )


def test_control_plane_timestamps_must_be_timezone_aware():
    payload = revision().model_dump()
    payload["accepted_at"] = NOW.replace(tzinfo=None)
    with pytest.raises(ValueError, match="timezone-aware"):
        DesiredRevision.model_validate(payload)


def test_transaction_rolls_back(tmp_path):
    repo = SQLiteControlPlaneRepository(tmp_path / "cp.db")
    with pytest.raises(RuntimeError), repo.transaction():
        repo.put_immutable("desired", "r1", revision())
        raise RuntimeError("crash")
    assert repo.get("desired", "r1", DesiredRevision) is None
