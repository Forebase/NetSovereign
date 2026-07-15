from __future__ import annotations

import json
from datetime import UTC, datetime
from ipaddress import ip_address, ip_network
from types import MappingProxyType
from uuid import UUID

from computecommons.base import (
    Capability,
    Component,
    Entity,
    EntityId,
    Report,
    Resource,
    Result,
    Snapshot,
)
from computecommons.compute import CPUInfo, Machine, MemoryInfo
from computecommons.deployment import (
    Cluster,
    DeploymentEnvironment,
    Environment,
    Node,
    Region,
    Topology,
    Workload,
    Zone,
)
from computecommons.enums import (
    CPUArchitecture,
    Endianness,
    InterfaceKind,
    IsolationKind,
    OperatingSystemFamily,
    TransportProtocol,
)
from computecommons.identity import QualifiedName
from computecommons.network import (
    InterfaceAddress,
    MACAddress,
    NetworkEndpoint,
    NetworkInterface,
    Route,
)
from computecommons.network.dns import DNSRecord
from computecommons.network.socket import SocketAddressFamily, SocketDescriptor, SocketKind
from computecommons.requirements import (
    CapabilityRequirement,
    MatchReport,
    MatchStatus,
    RequirementMatch,
)
from computecommons.serialization import dumps, to_primitive
from computecommons.static import (
    Filesystem,
    MediaType,
    OperatingSystemRelease,
    RegistryMetadata,
    ServicePort,
    Vendor,
)
from computecommons.storage import (
    FileSystem,
    FilesystemInfo,
    Mount,
    MountPoint,
    StorageCapacity,
    StorageDevice,
    StorageVolume,
    Volume,
)
from computecommons.system import (
    Host,
    Kernel,
    KernelInfo,
    OperatingSystem,
    RuntimeEnvironment,
    Service,
    User,
)
from computecommons.units import Bandwidth, ByteSize, Duration, Frequency, Percentage
from computecommons.virtualisation import ExecutionContext, ExecutionLayer


def _assert_json_compatible(value: object) -> None:
    primitive = to_primitive(value)
    json.dumps(primitive, sort_keys=True)


def test_core_serialization_converts_supported_primitives() -> None:
    payload = {
        "uuid": UUID("12345678-1234-5678-1234-567812345678"),
        "datetime": datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC),
        "enum": CPUArchitecture.ARM64,
        "mapping": MappingProxyType({"address": ip_address("2001:db8::1")}),
        "tuple": (Frequency.gigahertz(3),),
        "frozenset": frozenset({"sse4", "aes"}),
        "network": ip_network("192.0.2.0/24"),
    }

    primitive = to_primitive(payload)

    assert primitive == {
        "uuid": "12345678-1234-5678-1234-567812345678",
        "datetime": "2026-01-02T03:04:05+00:00",
        "enum": "arm64",
        "mapping": {"address": "2001:db8::1"},
        "tuple": [{"hertz": 3_000_000_000}],
        "frozenset": ["aes", "sse4"],
        "network": "192.0.2.0/24",
    }


def test_dataclass_and_enum_serialization() -> None:
    cpu = CPUInfo(architecture=CPUArchitecture.ARM64, logical_processors=4)
    value = to_primitive(cpu)
    assert value["architecture"] == "arm64"
    assert '"logical_processors": 4' in dumps(cpu, sort_keys=True)


def test_all_exported_public_value_objects_are_json_serializable() -> None:
    qname = QualifiedName("computecommons.example", "thing")
    capability = Capability(
        qname, version="1", value=ip_address("192.0.2.1"), properties={"tags": ("a", "b")}
    )
    entity_id = EntityId(UUID("12345678-1234-5678-1234-567812345678"))
    entity = Entity(entity_id, "entity", {"role": "test"})
    resource = Resource(entity, qname)
    iface_address = InterfaceAddress(
        ip_address("192.0.2.10"), ip_network("192.0.2.0/24"), ip_address("192.0.2.255"), "global"
    )
    cpu = CPUInfo(
        CPUArchitecture.X86_64,
        8,
        physical_cores=4,
        sockets=1,
        vendor="Example",
        model="v1",
        minimum_frequency=Frequency.megahertz(800),
        maximum_frequency=Frequency.gigahertz(4),
        endianness=Endianness.LITTLE,
        features=frozenset({"sse4", "aes"}),
    )
    memory = MemoryInfo(
        ByteSize.gibibytes(16),
        available=ByteSize.gibibytes(8),
        page_size=ByteSize.kibibytes(4),
        swap_total=ByteSize.gibibytes(2),
        swap_available=ByteSize.gibibytes(1),
    )
    machine = Machine(
        "node-01", cpu, memory, machine_id="mid", firmware="uefi", chassis_type="rack"
    )
    os = OperatingSystem(OperatingSystemFamily.LINUX, "Linux", "6", "stable", "linux", "6.1")
    runtime = RuntimeEnvironment("cpython", "3.13", "/usr/bin/python", {"ENV": "test"})
    kernel = KernelInfo("linux", "6.1", "generic")
    storage_capacity = StorageCapacity(ByteSize.gibibytes(100), ByteSize.gibibytes(40))
    filesystem = FilesystemInfo("ext4", "root", "fs-uuid", ("rw",))
    requirement = CapabilityRequirement(qname, "1", {"tags": ("a",)}, optional=True)
    match = RequirementMatch(requirement, MatchStatus.SATISFIED, capability, "ok")
    layer = ExecutionLayer(IsolationKind.APPLICATION_CONTAINER, "oci", "docker", "abc")

    samples = [
        capability,
        Component(resource, state={"up": True}, capabilities=(capability,)),
        entity,
        entity_id,
        Report("summary", ("detail",)),
        resource,
        Result(value=capability),
        Result(error="error"),
        Snapshot(datetime(2026, 1, 2, tzinfo=UTC), "unit-test", {"id": entity_id}),
        cpu,
        machine,
        memory,
        Cluster("cluster", "Cluster", "prod", "region", ("node",), {"tier": "test"}),
        DeploymentEnvironment("prod", "Production", "prod", {"owner": "platform"}),
        Environment("env", "Env", "test", {}),
        Node("node", "Node", "cluster", "zone", ("192.0.2.10",), {"role": "worker"}),
        Region("region", "Region", "provider", {}),
        Topology("topology", "Topology"),
        Workload("workload", "Workload"),
        Zone("zone", "Zone", "region", {}),
        qname,
        iface_address,
        MACAddress("00-11-22-33-44-55"),
        NetworkEndpoint(ip_address("192.0.2.10"), 443, TransportProtocol.TCP),
        NetworkInterface(
            "eth0",
            InterfaceKind.ETHERNET,
            1,
            MACAddress("00:11:22:33:44:55"),
            1500,
            True,
            Bandwidth.gigabits(1),
            (iface_address,),
        ),
        Route(ip_network("0.0.0.0/0"), ip_address("192.0.2.1"), "eth0", 100, "main", "static"),
        DNSRecord("example.test", "A", ip_address("192.0.2.10"), 60, 10),
        SocketDescriptor(
            SocketAddressFamily.IPV4,
            SocketKind.STREAM,
            TransportProtocol.TCP,
            NetworkEndpoint("127.0.0.1", 80, TransportProtocol.TCP),
        ),
        requirement,
        match,
        MatchReport((match,)),
        Filesystem("ext4", "Extended filesystem", True, True),
        MediaType("application", "json", ("json",), "JSON"),
        OperatingSystemRelease("Ubuntu", OperatingSystemFamily.LINUX, "Canonical"),
        RegistryMetadata(
            "test",
            "source",
            "1",
            "compact",
            "https://example.test",
            "2026",
            "2026-01-01",
            "2026-01-02",
        ),
        ServicePort("https", 443, TransportProtocol.TCP, "HTTPS"),
        Vendor("example", "Example", "https://example.test"),
        FileSystem("xfs", "data", "uuid", ("rw",)),
        filesystem,
        Mount("/mnt", "/dev/sda1", "ext4", False, ("rw",)),
        MountPoint("/", "/dev/root", "ext4", True, ("ro",)),
        storage_capacity,
        StorageDevice("disk0", "Disk", storage_capacity, False, "/dev/sda", "model", "serial"),
        StorageVolume("vol0", "Volume", storage_capacity, filesystem, "disk0"),
        Volume("vol1", "Volume 1", storage_capacity, filesystem, "disk0"),
        Host(machine, os, runtime, "example.test", kernel),
        Kernel("linux", "6.1", "generic"),
        kernel,
        os,
        runtime,
        Service("sshd", "running", "SSH"),
        User("alice", 1000, "/home/alice"),
        Bandwidth(1_000),
        ByteSize(1024),
        Duration(1_000_000),
        Frequency(2_400_000_000),
        Percentage(99.9),
        ExecutionContext((layer,)),
        layer,
    ]

    for sample in samples:
        _assert_json_compatible(sample)
