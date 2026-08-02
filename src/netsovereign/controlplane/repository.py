"""Durable repository interfaces and the restart-safe local implementation."""

from __future__ import annotations

import builtins
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Protocol, TypeVar

from pydantic import BaseModel

from .models import Checkpoint, DesiredRevision, LockLease, ReconciliationRecord

T = TypeVar("T", bound=BaseModel)


class ControlPlaneRepository(Protocol):
    """Storage contract; callers never depend on PostgreSQL-specific concepts."""

    def put_immutable(self, partition: str, key: str, value: BaseModel) -> None: ...
    def get(self, partition: str, key: str, model: type[T]) -> T | None: ...
    def list(self, partition: str, model: type[T]) -> list[T]: ...
    def set_active_revision(self, world_id: str, revision_id: str) -> None: ...
    def active_revision(self, world_id: str) -> DesiredRevision | None: ...
    def acquire_lock(self, lease: LockLease) -> LockLease | None: ...
    def release_lock(self, key: str, owner: str, reason: str, at: datetime) -> bool: ...


class SQLiteControlPlaneRepository:
    """DB-API reference used locally/tests; PostgreSQL uses the same partition contract.

    SQLite is deliberately not presented as the production reference. It makes the
    CLI restart-safe without requiring a server and exercises transaction semantics.
    """

    SCHEMA_VERSION = 1

    def __init__(self, path: Path | str):
        self.path = str(path)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.migrate()

    def migrate(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS cp_metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cp_records(
              partition TEXT NOT NULL, key TEXT NOT NULL, payload TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY(partition,key));
            CREATE TABLE IF NOT EXISTS cp_active_revisions(
              world_id TEXT PRIMARY KEY, revision_id TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cp_locks(
              lock_key TEXT PRIMARY KEY, owner TEXT NOT NULL, acquired_at TEXT NOT NULL,
              expires_at TEXT NOT NULL, fencing_token INTEGER NOT NULL,
              payload TEXT NOT NULL);
            """
        )
        row = self.connection.execute(
            "SELECT value FROM cp_metadata WHERE key='schema_version'"
        ).fetchone()
        if row and int(row[0]) > self.SCHEMA_VERSION:
            raise RuntimeError(f"incompatible control-plane schema version {row[0]}")
        self.connection.execute(
            "INSERT OR IGNORE INTO cp_metadata VALUES('schema_version',?)",
            (str(self.SCHEMA_VERSION),),
        )
        self.connection.commit()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            yield
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise

    def put_immutable(self, partition: str, key: str, value: BaseModel) -> None:
        payload = value.model_dump_json()
        existing = self.connection.execute(
            "SELECT payload FROM cp_records WHERE partition=? AND key=?", (partition, key)
        ).fetchone()
        if existing:
            if json.loads(existing[0]) != json.loads(payload):
                raise ValueError(f"immutable record conflict: {partition}/{key}")
            return
        self.connection.execute(
            "INSERT INTO cp_records VALUES(?,?,?,CURRENT_TIMESTAMP)", (partition, key, payload)
        )

    def get(self, partition: str, key: str, model: type[T]) -> T | None:
        row = self.connection.execute(
            "SELECT payload FROM cp_records WHERE partition=? AND key=?", (partition, key)
        ).fetchone()
        return model.model_validate_json(row[0]) if row else None

    def list(self, partition: str, model: type[T]) -> list[T]:
        rows = self.connection.execute(
            "SELECT payload FROM cp_records WHERE partition=? ORDER BY key", (partition,)
        ).fetchall()
        return [model.model_validate_json(row[0]) for row in rows]

    def set_active_revision(self, world_id: str, revision_id: str) -> None:
        if self.get("desired", revision_id, DesiredRevision) is None:
            raise KeyError(revision_id)
        self.connection.execute(
            "INSERT INTO cp_active_revisions VALUES(?,?) ON CONFLICT(world_id) DO UPDATE SET revision_id=excluded.revision_id",
            (world_id, revision_id),
        )

    def active_revision(self, world_id: str) -> DesiredRevision | None:
        row = self.connection.execute(
            "SELECT revision_id FROM cp_active_revisions WHERE world_id=?", (world_id,)
        ).fetchone()
        return self.get("desired", row[0], DesiredRevision) if row else None

    def acquire_lock(self, lease: LockLease) -> LockLease | None:
        with self.transaction():
            row = self.connection.execute(
                "SELECT owner,expires_at,fencing_token FROM cp_locks WHERE lock_key=?", (lease.key,)
            ).fetchone()
            if row and datetime.fromisoformat(row[1]) > lease.acquired_at and row[0] != lease.owner:
                return None
            token = (int(row[2]) + 1) if row else 1
            granted = lease.model_copy(update={"fencing_token": token})
            self.connection.execute(
                "INSERT OR REPLACE INTO cp_locks VALUES(?,?,?,?,?,?)",
                (
                    granted.key,
                    granted.owner,
                    granted.acquired_at.isoformat(),
                    granted.expires_at.isoformat(),
                    token,
                    granted.model_dump_json(),
                ),
            )
            return granted

    def release_lock(self, key: str, owner: str, reason: str, at: datetime) -> bool:
        with self.transaction():
            row = self.connection.execute(
                "SELECT owner FROM cp_locks WHERE lock_key=?", (key,)
            ).fetchone()
            if not row or row[0] != owner:
                return False
            self.connection.execute("DELETE FROM cp_locks WHERE lock_key=?", (key,))
            self.put_immutable(
                "lock_history",
                f"{key}:{at.isoformat()}",
                LockLease(
                    key=key,
                    owner=owner,
                    acquired_at=at,
                    expires_at=at,
                    fencing_token=0,
                    released_at=at,
                    release_reason=reason,
                ),
            )
            return True

    def latest_checkpoint(self, run_id: str, fingerprint: str) -> Checkpoint | None:
        matches = [c for c in self.list("checkpoint", Checkpoint) if c.run_id == run_id]
        if not matches:
            return None
        latest = max(matches, key=lambda item: item.created_at)
        if latest.plan_fingerprint != fingerprint or latest.schema_version != self.SCHEMA_VERSION:
            raise RuntimeError("checkpoint is incompatible with the executable plan or schema")
        return latest

    def incomplete_reconciliations(self) -> builtins.list[ReconciliationRecord]:
        return [
            r for r in self.list("reconciliation", ReconciliationRecord) if r.completed_at is None
        ]
