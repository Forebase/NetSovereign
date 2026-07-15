from dataclasses import FrozenInstanceError

import pytest

from computecommons.compute.cpu import CPUInfo
from computecommons.compute.machine import Machine
from computecommons.compute.memory import MemoryInfo
from computecommons.enums import CPUArchitecture, InterfaceKind, TransportProtocol
from computecommons.network.endpoint import NetworkEndpoint
from computecommons.network.interface import NetworkInterface
from computecommons.serialization import to_primitive
from computecommons.units.bytes import ByteSize
from computecommons.units.frequency import Frequency


def test_compute_submodules_expose_stable_value_objects() -> None:
    cpu = CPUInfo(
        architecture=CPUArchitecture.X86_64,
        logical_processors=4,
        features=["sse4", "avx2"],
        maximum_frequency=Frequency.gigahertz(3.4),
    )
    machine = Machine(
        hostname="node-01",
        cpu=cpu,
        memory=MemoryInfo(total=ByteSize.gibibytes(8)),
    )

    assert cpu.features == frozenset({"sse4", "avx2"})
    assert to_primitive(machine)["cpu"]["architecture"] == "x86_64"
    assert to_primitive(machine)["memory"]["total"]["bytes"] == 8 * 1024**3

    with pytest.raises(FrozenInstanceError):
        machine.hostname = "node-02"  # type: ignore[misc]


def test_compute_submodule_validation() -> None:
    with pytest.raises(ValueError, match="logical_processors"):
        CPUInfo(architecture=CPUArchitecture.X86_64, logical_processors=0)

    with pytest.raises(ValueError, match="hostname"):
        Machine(
            hostname=" ",
            cpu=CPUInfo(architecture=CPUArchitecture.X86_64, logical_processors=1),
            memory=MemoryInfo(total=ByteSize(1)),
        )


def test_network_submodules_expose_stable_value_objects() -> None:
    endpoint = NetworkEndpoint("localhost", 443, TransportProtocol.TCP)
    interface = NetworkInterface(
        name="eth0",
        kind=InterfaceKind.ETHERNET,
        addresses=[],
    )

    assert interface.addresses == ()
    assert to_primitive(endpoint) == {
        "host": "localhost",
        "port": 443,
        "transport": "tcp",
    }

    with pytest.raises(FrozenInstanceError):
        endpoint.port = 80  # type: ignore[misc]


def test_network_submodule_validation() -> None:
    with pytest.raises(ValueError, match="port"):
        NetworkEndpoint("localhost", -1, TransportProtocol.TCP)

    with pytest.raises(ValueError, match="interface name"):
        NetworkInterface(name="", kind=InterfaceKind.ETHERNET)
