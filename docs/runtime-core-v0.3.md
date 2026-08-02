# NetEngine runtime core (v0.3)

v0.3 adds a provider-neutral execution boundary without replacing the legacy
phase-oriented application. The phase runner and its operational handlers remain a
compatibility path; the runtime core never calls them and no existing handler is
presented as a provider.

## Pipeline and contracts

An admitted v0.2 `ReconciliationPlan` remains an intent artefact. `compile_plan`
topologically orders its steps and deterministically resolves the generic
`resource.manage` capability through an injected `ProviderRegistry`. It emits a
provider-bound `ExecutablePlan` with revision, authority, mandate, target, binding,
preconditions, expected result, idempotency key, retry policy, failure posture, and a
deterministic integrity fingerprint. Compilation describes providers but never calls
validation, mutation, or observation.

The provider protocol separates `validate`, `apply`, `observe`, `compensate`, and
`delete`. Apply acceptance is not convergence: only a later matching observation
verifies an operation. Resolution rejects missing, incompatible, ambiguous,
explicitly unsupported, and unhealthy providers with stable error codes.

## State, evidence, and recovery

Every operation owns explicit transitions, attempts, provider results, observations,
and failure classification. Invalid transitions fail closed. A run derives status
from operation state rather than logs. Evidence separately records validation,
application, observation, conformance, simulation, compensation, and failure with
world revision and authority provenance. Secret-looking mapping keys are redacted.

Retries repeat the same transition only for explicit retryable classes. Compensation
is a semantic counter-action and runs in reverse completion order; rollback represents
restoring prior state; cleanup removes orphaned artefacts. They are distinct and no
cross-provider atomicity is claimed. If interruption leaves an operation running
after apply, resume observes first and accepts convergence without applying twice.
Changed plan fingerprints are rejected. This lasts only as long as the in-memory
repository: crash-safe persistence belongs to v0.4.

## Dry run and demonstration

Dry run resolves and validates normally, records predictions and evidence, and never
calls a mutating method. Providers must declare dry-run support.

```bash
netsovereign plan examples/minimal/world.yaml proposed.yaml --output admitted-plan.json
netsovereign execute admitted-plan.json
netsovereign execute admitted-plan.json --dry-run
```

The fake supports deterministic create/update/delete-style application, observation,
idempotent replay, stable resource IDs, typed failure injection, and compensation
without network, process, container, database, DNS, or host access.

## Boundaries

v0.3 is sequential and in-process. It adds no daemon, polling, operational provider,
database journal, lock, infrastructure snapshot, distributed transaction, or API.
Durable storage and repeated reconciliation are v0.4; authoritative naming is v0.5.
