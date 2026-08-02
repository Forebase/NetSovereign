# NetSovereign

> **Experimental / pre-alpha:** v0.1 models intent only. v0.2 is specifically scoped
> to offline admission against supplied observed-state snapshots; it provides no
> operational infrastructure or security guarantees.

NetSovereign defines sovereign digital worlds. **NetEngine** follows a versioned path:
v0.2 observation and admission, v0.3 provider-neutral compilation, and v0.4 durable
reconciliation, after which replaceable operational providers may be developed.
Operational DNS, PKI, identity, and gateway work is prohibited before that chain is
complete. Sovereignty means that recognised institutions can govern a world's naming,
numbering, registry, trust, identity, transit, mail, and catalogue authority without
making any particular service canonical.

## Install and use

Requires Python 3.12+. `uv sync --all-extras`, or install the wheel with pip. Commands are local, deterministic, and do not contact providers or networks:

```console
netsovereign validate examples/minimal/world.yaml
netsovereign manifest examples/minimal/world.yaml
netsovereign explain examples/minimal/world.yaml
```

See [the domain guide](docs/domain-model.md), [v0alpha2 schema guide](docs/schema-v0alpha2.md), and [roadmap](docs/roadmap.md). The broader example is illustrative: assurance claims and provider-shaped seams are declarations, not implemented guarantees.
