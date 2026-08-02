# NetEngine v0.4 durable local control plane

v0.4 turns the v0.3 provider-neutral runtime into a restart-safe, repeatedly operable single-node
control plane. `controlplane.models` defines immutable desired, authoritative, observed, checkpoint,
lease, reconciliation, and drift records. `ControlPlaneRepository` is independent of SQL dialect;
the PostgreSQL migration is the durable production schema and SQLite provides a local/test adapter.

Acceptance stores an immutable revision and changes the active pointer in one transaction. Rejected
admission is retained but never activated. Observations are versioned independently from apply
results. Idempotency is unique per world and content conflicts fail closed. Provider calls occur
between transactions; recovery observes any uncertain operation before retry.

Leases cover worlds, execution runs, resources, and maintenance. Expiry permits recovery with a
higher fencing token; only the owner releases an active lease. Checkpoints are logical journal
summaries, not infrastructure snapshots, and reject an incompatible plan fingerprint or schema.

Drift comparison deterministically classifies missing, unexpected, changed, unhealthy,
unverifiable, stale, unavailable, and conformant resources. Reconciliation is explicitly invoked
and bounded: observe, compare, plan, compile, execute, observe, assess. A conformant repeat is a
no-op; v0.4 has no daemon loop.

Production uses `NETENGINE_CONTROL_PLANE_DATABASE_URL`; local CLI tests may use
`NETENGINE_CONTROL_PLANE_PATH`. Back up with
`pg_dump --schema=netengine_control --format=custom DATABASE > control-plane.dump` and restore with
`pg_restore --dbname=DATABASE control-plane.dump`. This preserves the v0.4 schema but is neither
world portability nor a secret or infrastructure backup.

Legacy JSON phase state, queues, exports, and logs remain intact and are not live workflow state.
Real DNS, trust, identity, routing, workload, and public providers are deferred to v0.5 and later,
as are HA, distributed locks, leader election, remote agents, and polished backup orchestration.
