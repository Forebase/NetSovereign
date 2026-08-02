# ADR: Compile admitted plans into provider-bound executable operations

**Status:** Accepted

## Context

v0.2 plans express sovereign meaning and provenance. Provider selection inside them
would make replaceable implementation details canonical. Execution also needs
recovery state and attributable evidence that ordinary logs cannot provide.

## Decision

Keep reconciliation plans provider-neutral and add a deterministic compilation stage
that resolves capabilities into provider-bound executable operations. Provider apply
success and observed convergence remain separate records. Operation state and valid
transitions are explicit, and evidence is an execution product with authority,
mandate, resource, capability, provider, and revision provenance.

Providers do not offer a distributed transaction. The runtime may retry and perform
reverse-order semantic compensation, but does not promise atomicity, snapshots, or
equivalence between compensation, rollback, and cleanup. A complete in-memory fake
precedes operational providers so contracts and failures can be proven safely.

## Consequences

Compilation is deterministic and independently testable. Execution is explainable
and resumable within an injected in-memory repository. Callers must supply a registry
and bindings. Persistence, crash-safe recovery, and repeated reconciliation are
deferred to v0.4; operational naming is deferred to v0.5.
