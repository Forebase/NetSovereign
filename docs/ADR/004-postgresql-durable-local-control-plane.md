# ADR 004: PostgreSQL-backed durable local control plane

## Status

Accepted for v0.4.

## Decision

Ordinary PostgreSQL is the production reference state provider. Repository contracts remain
provider-neutral and a SQLite DB-API implementation supports hermetic local operation and contract
tests. PostgreSQL JSONB stores documented JSON-compatible representations; it is not a canonical
world model. Explicit tables partition desired revisions, authoritative decisions, observations,
plans, runs, operations, attempts, transitions, evidence, checkpoints, leases, reconciliation, and
drift. Secret material is not accepted by checkpoints or ordinary evidence.

Events and logs may notify or diagnose, but never replace current projections and append-only
operation history. Desired declarations are not authoritative decisions; authoritative decisions
are not observations; observations are not provider results.

Provider calls never occur inside a database transaction. The executor first commits `running`,
calls the provider, then commits its result and next transition. Recovery treats an interruption
between those transactions as uncertain: it observes before policy permits retry. Durable scoped
idempotency keys reject conflicting content and prevent a verified effect being applied twice.

World, run, resource, and maintenance leases are explicit rows. Atomic acquisition, expiry,
owner-checked release, and monotonically increasing fencing tokens allow safe stale-lock recovery
and inspection. These are local-process coordination semantics, not distributed leadership.

Checkpoints are immutable logical journal summaries made before execution, after verified batches,
before compensation, and at finalisation. They are not infrastructure snapshots. Resume rejects a
different executable-plan fingerprint or schema version.

## Consequences

The transaction gap is visible and recoverable rather than hidden. PostgreSQL backup and restore
preserves the entire schema, while metadata export is diagnostic only and excludes secrets. v0.4 is
strictly single-node: HA, consensus, leader election, remote agents, operational providers, and
continuous reconciliation are deferred. v0.5 supplies the first authoritative naming provider
slice; it must consume these seams rather than alter their domain meaning.
