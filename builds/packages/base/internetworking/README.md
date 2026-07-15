# computecommons

`computecommons` is a dependency-light Python foundation for describing computing and networking infrastructure.

It provides immutable value objects, enums, protocols, capabilities, requirements, serialization helpers, and compact static registries. It deliberately does **not** inspect or mutate a host, configure a network, invoke shell commands, or orchestrate workloads.

> Describe infrastructure here. Discover and manage it elsewhere.

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e '.[dev]'
pytest
ruff check .
mypy src
```

## Example

```python
from ipaddress import ip_address, ip_network

from computecommons.compute import CPUInfo, Machine, MemoryInfo
from computecommons.enums import CPUArchitecture, InterfaceKind
from computecommons.network import InterfaceAddress, NetworkInterface
from computecommons.units import ByteSize, Frequency

machine = Machine(
    hostname="node-01",
    cpu=CPUInfo(
        architecture=CPUArchitecture.X86_64,
        logical_processors=16,
        physical_cores=8,
        maximum_frequency=Frequency.gigahertz(4.8),
    ),
    memory=MemoryInfo(total=ByteSize.gibibytes(32)),
)

interface = NetworkInterface(
    name="eth0",
    kind=InterfaceKind.ETHERNET,
    addresses=(
        InterfaceAddress(
            address=ip_address("192.0.2.10"),
            network=ip_network("192.0.2.0/24"),
        ),
    ),
)
```

## Scope of v0.1.0

- Common identity and entity primitives
- CPU, memory, machine, OS, host, and environment models
- IP, MAC, endpoint, interface, and route models
- Execution-context and virtualisation-layer models
- Capabilities, requirements, constraints, and match reports
- Byte-size, frequency, bandwidth, duration, and percentage value objects
- Predictable recursive conversion to JSON-compatible values
- Small architecture, protocol, and well-known-port registries
- Structural protocols for detectors, providers, parsers, and resolvers

## Package boundaries

Platform-specific behaviour belongs in companion packages such as:

- `computecommons-linux`
- `computecommons-windows`
- `computecommons-macos`
- `computecommons-docker`
- `computecommons-kubernetes`
- `computecommons-introspection`

## Stability

This is an alpha release. Public names exported from package `__init__.py` modules form the intended API, but models may still evolve before `1.0.0`.
