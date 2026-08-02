# Changelog
## 0.3.0 - 2026-08-02
- Added deterministic compilation of admitted plans, typed provider contracts and
  resolution, explicit execution state and evidence, dry run, retry, compensation,
  and interruption-safe in-memory resume through a non-operational fake provider.
- Added an `execute` demonstration command and runtime architecture ADR. Durable
  repeated reconciliation and operational providers remain deferred.

## 0.2.0 - 2026-08-02
- Added canonical world and manifest digests, revision lineage, semantic change sets, offline observed-state evidence, mandate-aware admission, explicit risks and approvals, and deterministic provider-neutral reconciliation plans.
- Added `diff`, `admit`, and `plan` commands. Planning is deliberately non-executable and keeps canonical intent, capabilities, provider bindings, and observed drift separate.
- Added explicit admission/approval states, typed mandate constraints and observation outcomes, lineage validation, separate intent/materialization digests, lifecycle policy, typed plan predicates, semantic dependency graphs, and published planning artifact schemas.

## 0.1.0 - 2026-08-01
- Added the v0alpha2 provider-neutral world model, semantic diagnostics, defaults, manifest, graph, resolver derivation, CLI, examples, schema, and documentation.
