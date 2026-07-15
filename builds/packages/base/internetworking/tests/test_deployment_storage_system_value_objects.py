from dataclasses import FrozenInstanceError

import pytest

from computecommons.compute import CPUInfo, Machine, MemoryInfo
from computecommons.deployment import Cluster, DeploymentEnvironment, Node, Region, Topology, Workload, Zone
from computecommons.deployment._warnings import NotImplementedWarning
from computecommons.enums import CPUArchitecture, OperatingSystemFamily
from computecommons.serialization import to_primitive
from computecommons.storage import FilesystemInfo, Mount, StorageCapacity, StorageDevice, Volume
from computecommons.system import Host, KernelInfo, OperatingSystem, RuntimeEnvironment
from computecommons.units import ByteSize


def test_deployment_value_objects_are_immutable_and_serializable() -> None:
    environment = DeploymentEnvironment(id="prod", kind="production", labels={"owner": "platform"})
    region = Region(id="us-east", provider="example")
    zone = Zone(id="us-east-1a", region_id=region.id)
    node = Node(id="node-1", cluster_id="cluster-1", zone_id=zone.id, addresses=["10.0.0.10"])
    cluster = Cluster(
        id="cluster-1",
        environment_id=environment.id,
        region_id=region.id,
        node_ids=[node.id],
    )

    primitive = to_primitive(cluster)

    assert primitive["node_ids"] == ["node-1"]
    assert to_primitive(environment)["labels"] == {"owner": "platform"}
    with pytest.raises(FrozenInstanceError):
        node.id = "node-2"  # type: ignore[misc]
    with pytest.raises(TypeError):
        environment.labels["owner"] = "other"  # type: ignore[index]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: DeploymentEnvironment(id=" "),
        lambda: Region(id="region", provider=" "),
        lambda: Zone(id="zone", region_id=" "),
        lambda: Node(id="node", addresses=("",)),
        lambda: Cluster(id="cluster", node_ids=("node-1", " ")),
    ],
)
def test_deployment_value_object_validation(factory: object) -> None:
    with pytest.raises(ValueError):
        factory()


def test_deployment_skeletons_warn_not_implemented() -> None:
    with pytest.warns(NotImplementedWarning):
        Topology(id="topology-1")
    with pytest.warns(NotImplementedWarning):
        Workload(id="workload-1")


def test_storage_value_objects_are_immutable_and_serializable() -> None:
    capacity = StorageCapacity(total=ByteSize.gibibytes(2), available=ByteSize.gibibytes(1))
    filesystem = FilesystemInfo(type="ext4", mount_options=["noatime"])
    device = StorageDevice(id="disk-1", capacity=capacity, path="/dev/sda", rotational=False)
    volume = Volume(id="vol-1", capacity=capacity, filesystem=filesystem, device_id=device.id)
    mount = Mount(path="/data", device="/dev/sda1", filesystem_type=filesystem.type, options=["noatime"])

    assert to_primitive(device)["capacity"]["total"]["bytes"] == 2 * 1024**3
    assert to_primitive(volume)["filesystem"]["mount_options"] == ["noatime"]
    assert to_primitive(mount)["options"] == ["noatime"]
    with pytest.raises(FrozenInstanceError):
        volume.id = "vol-2"  # type: ignore[misc]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: FilesystemInfo(type=" "),
        lambda: FilesystemInfo(type="ext4", mount_options=("",)),
        lambda: StorageDevice(id="disk", path="dev/sda"),
        lambda: Volume(id="volume", device_id=" "),
        lambda: Mount(path="relative"),
        lambda: Mount(path="/data", options=("",)),
    ],
)
def test_storage_value_object_validation(factory: object) -> None:
    with pytest.raises(ValueError):
        factory()


def test_system_value_objects_are_immutable_and_serializable() -> None:
    machine = Machine(
        hostname="host-1",
        cpu=CPUInfo(architecture=CPUArchitecture.X86_64, logical_processors=4),
        memory=MemoryInfo(total=ByteSize.gibibytes(8)),
    )
    operating_system = OperatingSystem(family=OperatingSystemFamily.LINUX, name="Linux", version="6.1")
    kernel = KernelInfo(name="Linux", release="6.1.0")
    runtime = RuntimeEnvironment(implementation="cpython", version="3.12", variables={"ENV": "test"})
    host = Host(machine=machine, operating_system=operating_system, runtime=runtime, kernel=kernel)

    primitive = to_primitive(host)

    assert primitive["operating_system"]["family"] == "linux"
    assert primitive["runtime"]["variables"] == {"ENV": "test"}
    with pytest.raises(FrozenInstanceError):
        runtime.version = "3.13"  # type: ignore[misc]
    with pytest.raises(TypeError):
        runtime.variables["ENV"] = "prod"  # type: ignore[index]


@pytest.mark.parametrize(
    "factory",
    [
        lambda: OperatingSystem(family=OperatingSystemFamily.UNKNOWN, name=" "),
        lambda: KernelInfo(name=""),
        lambda: RuntimeEnvironment(implementation="", version="3.12"),
        lambda: RuntimeEnvironment(implementation="cpython", version=""),
    ],
)
def test_system_value_object_validation(factory: object) -> None:
    with pytest.raises(ValueError):
        factory()
