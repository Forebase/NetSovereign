# NetSovereign roadmap

NetSovereign develops authority and intent before operational adapters. Versions v0.2 through v0.4
are a single dependency chain: real DNS, PKI, identity, or gateway providers must not begin until
change planning, the runtime core, and durable local control have established their boundaries.

| Version | Development outcome | Major boundary |
| --- | --- | --- |
| **v0.1 — Sovereign Domain Foundation** | Offline declarations, validation, manifests, authority graphs, and explanations. | No planning or infrastructure mutation. |
| **v0.2 — Sovereign Change Planning** | Compare current, proposed, and observed worlds; admit or reject changes; generate deterministic reconciliation plans. | No provider execution or infrastructure mutation. |
| **v0.3 — NetEngine Runtime Core** | Provider contracts, compilation pipeline, execution state machine, dry-run/mock provider, evidence, and rollback semantics. | Only simulated or non-operational providers. |
| **v0.4 — Durable Local Control Plane** | Persistent accepted state, journals, checkpoints, locks, recovery, drift detection, and repeated reconciliation. | Local single-node operation; no HA. |
| **v0.5 — Authoritative Naming Slice** | Registry/registrar to naming capability to generated authoritative DNS configuration. | Isolated local development environment only. |
| **v0.6 — Trust Authority** | Certificate policy, issuance lifecycle, revocation, and a replaceable step-ca-style provider. | No cross-world CA trust. |
| **v0.7 — Identity Authorities** | Separate platform and in-world identity; subjects, claims, credentials, and OIDC provider materialisation. | Federation remains explicitly opt-in. |
| **v0.8 — Registry and Numbering** | Organisation, name, and number allocation; registration, grant, delegation, and revocation workflows. | No real BGP or public-number claims. |
| **v0.9 — Boundary and Transit** | Materialise isolated, shadowed, mirrored, and exposed postures through resolver, routing, and policy providers. | Destructive or public exposure requires approval gates. |
| **v0.10 — Peering and Federation** | Cross-world discovery, signed exchange artefacts, and selective authority import/export. | Peering never implies trust. |
| **v0.11 — Mail and Service Catalogue** | Activate deferred authority families and their protocol surfaces. | Optional capabilities, not minimal-world requirements. |
| **v0.12 — Operational Product Surface** | Management API, CLI operations, audit views, lifecycle workflows, backup/restore, and multi-world administration. | Pre-1.0 until security and upgrade guarantees mature. |
| **v1.0 — Sovereign Runtime** | Stable schemas, migrations, conformance suite, hardened providers, upgrade guarantees, recovery, and documented security model. | Production compatibility commitment begins. |

## v0.2 acceptance boundary

Given an accepted world, a proposed declaration, and optional offline observations, v0.2 returns a
deterministic account of what changed, whether declared authority admits it, the applicable mandate,
risk and approval gates, existing drift, and provider-neutral convergence steps. Observations are
evidence rather than authority, admission does not authenticate a proposer, and plans cannot execute.

The planner distinguishes canonical intent, capabilities, replaceable provider bindings, and observed
drift. Stable world, authority, and resource identities cannot silently change meaning; retirement is
preferred to deletion; imported authority cannot silently become local; peering cannot gain trust by
ordinary update; imports and exports must remain explicit; and reductions in autonomy or new required
external dependencies are visible approval risks.

## Explicitly deferred from v0.2

Provider SDKs and concrete provider packages; subprocess, container, or network execution; CoreDNS,
step-ca, Keycloak, nftables, and PostgreSQL; durable databases and daemons; secrets; actual rollback;
provider discovery; live observation; and management APIs or user interfaces.
