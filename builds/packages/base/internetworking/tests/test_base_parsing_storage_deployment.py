from collections.abc import Callable
from dataclasses import FrozenInstanceError

import pytest

from computecommons.base import Component, Resource
from computecommons.deployment import Cluster
from computecommons.identity import QualifiedName
from computecommons.parsing import (
    parse_byte_size,
    parse_host_port,
    parse_ip_address,
    parse_platform_tag,
    parse_version,
)
from computecommons.requirements import Capability
from computecommons.serialization import to_primitive
from computecommons.storage import (
    FileSystem,
    MountPoint,
    StorageCapacity,
    StorageDevice,
    StorageVolume,
)
from computecommons.system import Kernel, Service, User
from computecommons.units import ByteSize


def test_resource_component_immutable_and_serializable() -> None:
    kind = QualifiedName.parse("compute:node")
    resource = Resource(kind=kind, id="node-1", labels={"role": "worker"})
    component = Component(
        name=QualifiedName.parse("runtime:python"),
        capabilities=(Capability(QualifiedName.parse("lang:python"), version="3.12"),),
        metadata={"resource": resource},
    )

    with pytest.raises(FrozenInstanceError):
        resource.id = "other"  # type: ignore[misc]
    with pytest.raises(TypeError):
        resource.labels["role"] = "control"  # type: ignore[index]

    primitive = to_primitive(component)
    assert primitive["name"] == {"namespace": "runtime", "name": "python"}
    assert primitive["metadata"]["resource"]["id"] == "node-1"


def test_resource_validation() -> None:
    with pytest.raises(ValueError):
        Resource(kind=QualifiedName.parse("compute:node"), id="")


def test_parsing_helpers_are_pure_value_parsers() -> None:
    assert str(parse_ip_address(" 127.0.0.1 ")) == "127.0.0.1"
    assert parse_host_port("[::1]:443") == ("::1", 443)
    assert parse_host_port("example.test", default_port=80) == ("example.test", 80)
    assert parse_byte_size("1.5 KiB") == ByteSize(1536)
    assert str(parse_version("v1.2.3-rc1")) == "1.2.3-rc1"
    assert str(parse_platform_tag("linux/amd64")) == "linux/amd64"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: StorageCapacity(total=ByteSize(10), available=ByteSize(11)),
        lambda: StorageDevice(id=""),
        lambda: StorageVolume(id=""),
        lambda: FileSystem(type=""),
        lambda: MountPoint(path="relative"),
        lambda: Cluster(id=""),
        lambda: Kernel(name=""),
        lambda: Service(name=""),
        lambda: User(name=""),
        lambda: User(name="root", uid=-1),
    ],
)
def test_neutral_value_object_validation(factory: Callable[[], object]) -> None:
    with pytest.raises(ValueError):
        factory()


def test_neutral_value_object_serialization_and_immutability() -> None:
    volume = StorageVolume(
        id="vol-1",
        capacity=StorageCapacity(total=ByteSize.gibibytes(1)),
        filesystem=FileSystem(type="ext4"),
    )
    assert to_primitive(volume)["capacity"]["total"]["bytes"] == 1024**3
    with pytest.raises(FrozenInstanceError):
        volume.id = "vol-2"  # type: ignore[misc]
