from computecommons.compute import CPUInfo
from computecommons.enums import CPUArchitecture
from computecommons.serialization import dumps, to_primitive


def test_dataclass_and_enum_serialization() -> None:
    cpu = CPUInfo(architecture=CPUArchitecture.ARM64, logical_processors=4)
    value = to_primitive(cpu)
    assert value["architecture"] == "arm64"
    assert '"logical_processors": 4' in dumps(cpu, sort_keys=True)
