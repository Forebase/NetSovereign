# Sovereign change planning v0.2

v0.2 is an offline decision surface. It compares declarations, evaluates the authority already
accepted by the current world, classifies evidence, and emits a provider-neutral plan. It never
loads providers, contacts a network, invokes a subprocess, or mutates infrastructure.

## Artifact identities

Every revision exposes separate SHA-256 identities:

- **declaration digest** covers the normalized complete declaration;
- **canonical-intent digest** excludes revision metadata and replaceable provider bindings;
- **materialization digest** covers capabilities and provider bindings;
- **manifest digest** exists only for a semantically valid manifest.

A proposal may provide its expected parent revision and declaration digest. A mismatch is rejected
as stale lineage. Change and drift identifiers use full content digests, so approvals bind to the
exact reviewed before/after values.

## Admission states and time

Admission has three outcomes: `rejected`, `pending_approval`, and `admitted`. An approval-gated
proposal is not admitted until matching approval evidence is supplied. `evaluated_at` is an explicit
input used for mandate validity; observation timestamps describe evidence and never select the
admission time.

Mandates are matched against authority, governed action, resource classes, jurisdiction, validity,
and typed constraints (`operations`, `paths`, and `subject_ids`). Current accepted state is validated
before it can authorise a proposal.

## Observations and plans

Facts use stable semantic paths such as `resources/root-zone`, and distinguish `present`, `absent`,
`unknown`, and `unreadable`. Unknown or unreadable evidence does not manufacture drift. Actionable
drift carries its authority and mandate into a convergence step.

Plan preconditions and expected outcomes are typed JSON objects rather than prose. Dependencies form
a deterministic semantic DAG: for example, a changed provider binding depends on its changed
capability, while unrelated changes remain independent. Reversibility is explicitly classified and
remains `unknown` unless v0.2 can justify a stronger provider-neutral statement.

Schemas are published at:

- `schemas/observed-v0.2.schema.json`;
- `schemas/admission-v0.2.schema.json`;
- `schemas/plan-v0.2.schema.json`.

## CLI contract

```console
netsovereign diff current.yaml proposed.yaml
netsovereign admit current.yaml proposed.yaml \
  --evaluated-at 2026-08-02T12:00:00Z \
  --parent-revision 7 --parent-digest sha256:... \
  --observed observed.json --approval approval.yaml
netsovereign plan current.yaml proposed.yaml --format yaml --output plan.yaml
```

`admit` and `plan` exit with `0` when admitted, `1` when rejected, `2` for malformed input or CLI
usage, and `3` while approval is pending. `--format json|yaml`, `--compact`, and `--output` control
serialization without changing artifact identity.
