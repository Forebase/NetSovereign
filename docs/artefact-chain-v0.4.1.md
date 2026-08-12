# Enforceable artefact chain (v0.4.1)

NetEngine keeps declaration, decision, evidence, materialisation and execution distinct:

`WorldSpec → diagnostics → WorldManifest → AcceptedWorldRevision → AdmissionDecision → ReconciliationPlan → ExecutablePlan → ExecutionRun`.

Declarations and manifests are canonical sovereign artefacts. Admission is a mandate-aware
decision; approvals and observations are evidence, never authority. Provider bindings are
replaceable materialisation choices. Plans and executable plans are derived artefacts.

## Integrity and gates

Persistent integrity envelopes use `netsovereign.canonical-json/v1` and `sha256:<hex>`.
Admissions bind revisions, changes, evidence, issues, gates and status. Plans bind their source
decision, revision and manifest digests, approval set, predicates, dependencies, capabilities,
outcomes and reversibility. Compilation verifies a loaded plan unconditionally.

Execution evaluates sovereign predicates against an injected `RuntimeFacts` snapshot before
provider validation or mutation. A failure records the exact predicate as evidence. Provider
validation is a later, separate gate. The executor never infers facts from a plan; the explicitly
named `offline_demo_facts()` helper is restricted to the fake-provider CLI demonstration.

Capabilities are provider-neutral and versioned. Compilation resolves the declared requirement,
binds the descriptor into the executable fingerprint, and rejects incompatible versions, unsafe
retry, dry-run and compensation postures. Compensation restores retained prior state; delete is
not presumed reversible.

## Security boundary and compatibility

Approval authentication remains a pre-alpha seam. Only evidence explicitly marked `verified`,
unexpired, and bound to the exact proposal digest and gate satisfies admission. This release does
not provide signatures, operational providers, PostgreSQL runtime integration, restart recovery,
high availability or daemon reconciliation.

Approval evidence IDs identify evidence records and are distinct from gate IDs. Admission clears
the referenced gate ID, and requires an explicit timezone-aware `evaluated_at` whenever approvals
are supplied so expiry is never evaluated against an approval's own historical timestamp.

The v0.2 admission and plan schemas gain integrity-envelope fields. New v0.4.1 approval,
executable-plan and desired-revision schemas are published. The typed desired-revision adapter is
the supported activation path; legacy prototype records remain readable but are not admission
proof. Their compatibility shape is an explicit typed adapter rather than an arbitrary dictionary.
