from __future__ import annotations

import ast
import importlib
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from pathlib import Path
from ipaddress import ip_address, ip_network
from types import MappingProxyType
from uuid import UUID

import pytest

from computecommons import static
from computecommons.base import Capability, Component, Entity, EntityId, Report, Resource, Result, Snapshot
from computecommons.deployment import Cluster, DeploymentEnvironment, Node
from computecommons.enums import InterfaceKind, IsolationKind, OperatingSystemFamily, TransportProtocol
from computecommons.identity import QualifiedName
from computecommons.network import InterfaceAddress, MACAddress, NetworkEndpoint, NetworkInterface, Route
from computecommons.network.dns import DNSRecord
from computecommons.network.socket import SocketAddressFamily, SocketDescriptor, SocketKind
from computecommons.requirements import CapabilityRequirement, MatchReport, MatchStatus, RequirementMatch
from computecommons.serialization import to_primitive
from computecommons.static import Filesystem, MediaType, OperatingSystemRelease, RegistryMetadata, ServicePort, Vendor
from computecommons.system import Kernel, Service, User
from computecommons.virtualisation import ExecutionContext, ExecutionLayer

PACKAGE_NAMES = [
    "computecommons",
    "computecommons.base",
    "computecommons.compute",
    "computecommons.deployment",
    "computecommons.enums",
    "computecommons.errors",
    "computecommons.identity",
    "computecommons.network",
    "computecommons.parsing",
    "computecommons.requirements",
    "computecommons.serialization",
    "computecommons.static",
    "computecommons.storage",
    "computecommons.system",
    "computecommons.typing",
    "computecommons.units",
    "computecommons.virtualisation",
]


@pytest.mark.parametrize("package_name", PACKAGE_NAMES)
def test_package_init_exports_are_importable_public_api(package_name: str) -> None:
    package = importlib.import_module(package_name)

    assert package.__all__, f"{package_name} should declare a public API"
    for public_name in package.__all__:
        assert hasattr(package, public_name), f"{package_name}.{public_name} is not importable"


def test_additional_value_objects_construct_and_validate_core_shapes() -> None:
    qname = QualifiedName("example.ns", "capability")
    capability = Capability(qname, version="1", properties={"tier": "gold"})
    entity = Entity(EntityId.parse("12345678-1234-5678-1234-567812345678"), "node", {"role": "test"})
    resource = Resource(entity, qname)
    component = Component(resource, capabilities=[capability])
    snapshot = Snapshot(datetime(2026, 7, 15, tzinfo=UTC), metadata={"source": "unit"})
    report = Report("ok", ["detail"])
    requirement = CapabilityRequirement(qname, required_properties={"tier": "gold"})
    match = RequirementMatch(requirement, MatchStatus.SATISFIED, capability)
    match_report = MatchReport([match])
    layer = ExecutionLayer(IsolationKind.APPLICATION_CONTAINER, technology="oci")
    context = ExecutionContext([layer])

    assert component.capabilities == (capability,)
    assert snapshot.metadata == {"source": "unit"}
    assert report.details == ("detail",)
    assert Result(value="ok").ok is True
    assert match_report.satisfied is True
    assert context.innermost == layer

    with pytest.raises(ValueError, match="namespace"):
        QualifiedName(" ", "capability")
    with pytest.raises(ValueError, match="timezone-aware"):
        Snapshot(datetime(2026, 7, 15))
    with pytest.raises(ValueError, match="at least one layer"):
        ExecutionContext([])


def test_additional_network_and_static_value_objects_construct_and_validate() -> None:
    mac = MACAddress("AA:BB:CC:DD:EE:FF")
    iface_address = InterfaceAddress(ip_address("192.0.2.10"), ip_network("192.0.2.0/24"))
    interface = NetworkInterface("eth0", InterfaceKind.ETHERNET, addresses=[iface_address], mac_address=mac)
    route = Route(ip_network("0.0.0.0/0"), gateway=ip_address("192.0.2.1"), interface="eth0", metric=10)
    endpoint = NetworkEndpoint("example.test", 443, TransportProtocol.TCP)
    dns_record = DNSRecord("example.test", "A", "192.0.2.10", ttl=60)
    socket = SocketDescriptor(SocketAddressFamily.IPV4, SocketKind.STREAM, local_endpoint=NetworkEndpoint("127.0.0.1", 443, TransportProtocol.TCP))

    assert interface.addresses == (iface_address,)
    assert route.metric == 10
    assert endpoint.port == 443
    assert dns_record.value == "192.0.2.10"
    assert socket.family is SocketAddressFamily.IPV4
    assert MediaType("application", "json", ("json",)).extensions == ("json",)
    assert Filesystem("ext4", "Fourth extended filesystem", journaling=True).journaling is True
    assert OperatingSystemRelease("linux", OperatingSystemFamily.LINUX).family is OperatingSystemFamily.LINUX
    assert ServicePort("https", 443, TransportProtocol.TCP).port == 443
    assert Vendor("example", "Example Inc.").slug == "example"
    assert RegistryMetadata("registry", "curated", "0.1.0", "compact").name == "registry"

    with pytest.raises(ValueError, match="MAC"):
        MACAddress("not-a-mac")
    with pytest.raises(ValueError, match="metric"):
        Route(ip_network("0.0.0.0/0"), metric=-1)
    with pytest.raises(ValueError, match="DNS"):
        DNSRecord("example.test", "A", "")


def test_mapping_fields_collection_normalization_and_registry_immutability() -> None:
    qname = QualifiedName("example", "thing")
    capability = Capability(qname, properties={"key": "value"})
    requirement = CapabilityRequirement(qname, required_properties={"key": "value"})
    entity = Entity(labels={"env": "test"})
    context = ExecutionContext([ExecutionLayer(IsolationKind.BARE_METAL)])

    assert isinstance(capability.properties, MappingProxyType)
    assert isinstance(requirement.required_properties, MappingProxyType)
    assert isinstance(entity.labels, MappingProxyType)
    assert context.layers == (ExecutionLayer(IsolationKind.BARE_METAL),)
    assert isinstance(static.MEDIA_TYPES, tuple)
    assert isinstance(static.MEDIA_TYPE_BY_VALUE, MappingProxyType)

    with pytest.raises(TypeError):
        capability.properties["key"] = "other"  # type: ignore[index]
    with pytest.raises(TypeError):
        static.MEDIA_TYPE_BY_VALUE["text/plain"] = static.MEDIA_TYPES[0]  # type: ignore[index]
    with pytest.raises(AttributeError):
        static.MEDIA_TYPES.append(MediaType("text", "csv"))  # type: ignore[attr-defined]
    with pytest.raises(FrozenInstanceError):
        context.layers[0].technology = "vm"  # type: ignore[misc]


def test_representative_nested_objects_serialize_to_json_safe_primitives() -> None:
    qname = QualifiedName("example", "compute")
    capability = Capability(qname, value={"endpoint": NetworkEndpoint("api.example.test", 443, TransportProtocol.TCP)})
    entity = Entity(EntityId(UUID("12345678-1234-5678-1234-567812345678")), "api", {"team": "platform"})
    component = Component(Resource(entity, qname), capabilities=[capability])
    deployment = Cluster("cluster-1", environment_id="prod", node_ids=["node-1"])
    node = Node("node-1", cluster_id="cluster-1", addresses=["10.0.0.5"])
    payload = {"component": component, "deployment": deployment, "nodes": [node]}

    primitive = to_primitive(payload)

    assert primitive["component"]["capabilities"][0]["value"]["endpoint"]["port"] == 443
    assert primitive["component"]["resource"]["entity"]["labels"] == {"team": "platform"}
    assert primitive["deployment"]["node_ids"] == ["node-1"]
    assert primitive["nodes"][0]["addresses"] == ["10.0.0.5"]


def test_core_package_does_not_import_forbidden_discovery_or_orchestration_libraries() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "computecommons"
    forbidden_roots = {
        "subprocess",
        "socket",
        "docker",
        "kubernetes",
        "boto3",
        "botocore",
        "google.cloud",
        "azure",
        "psutil",
        "distro",
        "platformdirs",
        "winreg",
        "wmi",
    }
    discovered: list[tuple[str, int, str]] = []

    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            imported_names: list[str] = []
            if isinstance(node, ast.Import):
                imported_names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.append(node.module)
            for name in imported_names:
                if any(name == forbidden or name.startswith(f"{forbidden}.") for forbidden in forbidden_roots):
                    discovered.append((str(path.relative_to(root)), node.lineno, name))

    assert discovered == []
