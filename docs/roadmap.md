# Versioned roadmap

This roadmap orders delivery by what must be proved, not by which server is easiest to
run. A version's outcome is the capability that the release must establish; its
boundary is an explicit non-goal, not an implied promise.

Only v0.1 is complete. Every later section describes planned work rather than current
functionality. In particular, v0.3 is not complete—and must not be represented as
complete—until every item in its completion gate has passed after v0.2 is accepted.

## Dependency rule

The foundation is a strict chain:

**v0.1 declared intent -> v0.2 admission against observed state -> v0.3
provider-neutral compilation -> v0.4 reconciliation and durable operations.**

Each link consumes the stable artefacts and semantics of the preceding link. Work on
an operational DNS, PKI, identity, or gateway provider **must not start until the
entire chain through v0.4 is complete and its acceptance points pass**. Provider
prototypes, containers, and service configuration do not count as progress on an
earlier link and must not be used to define the domain model.

## v0.1 — Sovereign intent foundation (complete)

- **Development outcome:** declare and strictly validate provider-neutral worlds;
  derive deterministic manifests and authority graphs; explain authority and
  assurance posture offline.
- **Boundary / explicit non-goal:** no observation, admission decision, compilation,
  reconciliation, provider execution, operational infrastructure, or security
  guarantee.

## v0.2 — Observation and admission

### Governing question

**Given declared world intent and a supplied snapshot of reality, is that reality
admissible under the world's authorities, mandates, capabilities, boundaries, and
assurance requirements—and why?**

### Required functionality

- Define a versioned, provider-neutral observed-state document with stable resource
  identities, provenance, collection time, and explicit unknown or unavailable
  values.
- Strictly parse and validate observed state without discovering it from a network or
  provider.
- Compare one validated snapshot with one validated world manifest and emit a
  deterministic, machine-readable admission report.
- Report each relevant requirement as `admitted`, `rejected`, or `indeterminate`,
  with stable diagnostic codes, evidence references, and an aggregate decision.
- Explain an admission report in terms of the governing institution, authority,
  mandate, required capability, boundary, and evidence that determined it.
- Preserve enough input identity and version information for the same inputs to
  reproduce the same report.

### Semantic rules

- Intent remains canonical; observed state is evidence about reality and may never
  amend, infer, or silently default intent.
- Admission is evaluation, not convergence. It is read-only and causes no provider,
  network, credential, or state mutation.
- Evidence is evaluated only within the authority and mandate that governs the
  resource. A provider claim cannot create authority or broaden a mandate.
- Missing, stale, contradictory, unverifiable, or out-of-scope evidence is
  `indeterminate`, never silently treated as success. Demonstrated violation is
  `rejected`; `admitted` requires all applicable mandatory checks to pass.
- Unknown observations are distinct from known absence. Extra observed resources are
  surfaced and evaluated according to explicit intent rather than silently ignored.
- Ordering, filesystem location, wall-clock time, and provider-specific spelling may
  not change a decision. Time-sensitive checks use the snapshot's declared collection
  time and policy inputs.
- Schema, world, and report versions are checked explicitly; incompatible versions
  fail closed with diagnostics.

### Deferred functionality

v0.2 does not collect observations, poll providers, persist a live inventory, plan
changes, compile provider configuration, reconcile drift, execute a provider, manage
secrets, or operate DNS, PKI, identity, gateways, networks, databases, mail, storage,
or orchestration systems. Streaming observation and historical/stateful policy are
also deferred.

### CLI contract

The v0.2 command surface will add:

```console
netsovereign observed validate observed-state.yaml
netsovereign admit world.yaml observed-state.yaml --output admission.json
netsovereign admission explain admission.json
```

All three commands are offline and deterministic. `admit` exits successfully only
for an aggregate `admitted` decision, uses a distinct non-zero status for `rejected`
and `indeterminate`, and never contacts or changes the described systems.

### Acceptance point

v0.2 is complete when versioned fixtures prove reproducible admission and explanation
for admitted, rejected, indeterminate, extra-resource, stale-evidence, conflicting-
evidence, and incompatible-version cases; malformed inputs and semantic violations
produce stable diagnostics; and tests demonstrate that the command path performs no
network access or mutation.

## v0.3 — Provider-neutral compilation

- **Development outcome:** compile admitted intent and capability requirements into a
  deterministic provider-neutral desired-state plan with dependencies, ownership,
  sensitive-value references, and explainable change sets.
- **Boundary / explicit non-goal:** no apply, provider API call, credential custody,
  durable operation, or convergence loop; compilation does not make a provider
  authoritative.
- **Dependency:** starts only after v0.2 observation and admission are accepted, and
  consumes an admitted report rather than bypassing admission.

### v0.3 completion gate

All of the following work is required before v0.3 may be called complete:

- Define and version the provider-neutral desired-state plan schema.
- Compile every admitted authority and capability in the supported world schema, or
  produce a stable diagnostic for a capability that cannot be compiled.
- Encode resource identity, ownership, dependencies, lifecycle constraints, and
  references to sensitive values without embedding secret material.
- Produce deterministic create, update, replace, and delete change sets from identical
  world, admission, and prior-plan inputs.
- Reject missing, rejected, indeterminate, stale, incompatible, or mismatched admission
  reports instead of compiling around them.
- Explain every planned resource and change back to its world declaration, governing
  authority and mandate, required capability, and admission evidence.
- Prove with versioned fixtures that ordering, filesystem location, wall-clock time,
  and provider-specific configuration do not affect compilation output.
- Publish compatibility and migration rules for the plan schema and stable diagnostic
  codes, with tests for malformed and incompatible inputs.
- Demonstrate in tests that compilation performs no network access, provider calls,
  credential lookup, durable mutation, apply, or reconciliation.

The v0.3 acceptance point is a reproducible plan and explanation corpus covering every
supported capability and change kind, with all completion-gate tests passing. Partial
schema or compiler work remains a v0.3 development snapshot, not a completed release
and not permission to begin v0.4 or an operational provider.

## v0.4 — Reconciliation and durable operations

- **Development outcome:** implement the provider-agnostic reconciliation contract:
  durable/idempotent operations, checkpoints, retries, cancellation, drift handling,
  audit records, recovery, and safe plan/apply separation against test doubles.
- **Boundary / explicit non-goal:** no operational DNS, PKI, identity, or gateway
  provider; passing synthetic contract tests is not a production service or security
  guarantee.
- **Dependency:** starts only after v0.3 compilation is accepted, and reconciles only
  compiled plans backed by v0.2 admission. Completion of v0.4 completes the mandatory
  v0.1 -> v0.2 -> v0.3 -> v0.4 chain.

## v0.5 — Operational DNS

- **Development outcome:** deliver the first replaceable DNS provider conforming to
  the v0.4 operation contract, including authoritative naming, resolver materialisation,
  drift reporting, rollback, and provider conformance evidence.
- **Boundary / explicit non-goal:** DNS does not establish PKI trust, identity, gateway
  policy, public ingress, global availability, or DNSSEC key-rotation guarantees.

## v0.6 — Operational PKI

- **Development outcome:** add replaceable PKI materialisation for declared trust
  authorities, certificate lifecycle operations, revocation, audit, and recovery
  under the same admission/compilation/reconciliation path.
- **Boundary / explicit non-goal:** no identity provider, OIDC federation, CA
  cross-signing, hardware-root guarantee, or gateway implementation; certificates do
  not by themselves confer institutional authority.

## v0.7 — Operational identity

- **Development outcome:** add a replaceable identity provider for declared principals,
  credentials, groups, and policy bindings, with lifecycle, revocation, drift, and
  recovery exercised through durable operations.
- **Boundary / explicit non-goal:** no gateway, universal SSO, social/external identity
  federation, or assumption that an account is an authority or mandate.

## v0.8 — Operational gateway

- **Development outcome:** materialise declared exposure and transit policy through a
  replaceable gateway provider, with identity- and trust-aware policy, audit, rollback,
  and drift reconciliation.
- **Boundary / explicit non-goal:** no general firewall/routing/NAT/BGP platform,
  arbitrary service mesh, unrestricted public ingress, or claim that a gateway is the
  source of naming, trust, or identity authority.

## v0.9 — Integrated release candidate

- **Development outcome:** prove clean-room deployment, upgrade, backup/restore,
  failure recovery, provider replacement, and end-to-end conformance of the DNS, PKI,
  identity, and gateway slices; freeze candidate schemas and compatibility policy.
- **Boundary / explicit non-goal:** no new authority classes or major provider surface;
  SMTP, object storage, Kubernetes, WireGuard, management API/UI, HA, and broader
  federation remain outside the release candidate.

## v1.0 — Stable sovereign runtime

- **Development outcome:** publish a supported, security-reviewed contract for intent,
  observation, admission, compilation, reconciliation, and the four operational
  provider classes, with documented upgrades, recovery objectives, compatibility,
  and operator runbooks.
- **Boundary / explicit non-goal:** v1.0 guarantees the documented contract and tested
  deployment profiles, not absolute sovereignty or security, universal protocol
  coverage, every provider, zero-downtime HA, or automatic trust between worlds.
