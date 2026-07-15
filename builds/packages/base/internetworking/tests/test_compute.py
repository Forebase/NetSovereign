import pytest

from computecommons.compute import CPUInfo, Machine, MemoryInfo
from computecommons.enums import CPUArchitecture
from computecommons.units import ByteSize


def test_machine_model() -> None:
    machine = Machine(
        hostname="node-01",
        cpu=CPUInfo(architecture=CPUArchitecture.X86_64, logical_processors=8),
        memory=MemoryInfo(total=ByteSize.gibibytes(16)),
    )
    assert machine.cpu.logical_processors == 8


def test_available_memory_cannot_exceed_total() -> None:
    with pytest.raises(ValueError):
        MemoryInfo(total=ByteSize(10), available=ByteSize(11))


def test_architecture_module_imports() -> None:
    import computecommons.compute.architecture

    assert computecommons.compute.architecture is not None
def test_compute_import_paths_export_same_models() -> None:
    from computecommons.compute import CPUInfo as PackageCPUInfo
    from computecommons.compute import Machine as PackageMachine
    from computecommons.compute import MemoryInfo as PackageMemoryInfo
    from computecommons.compute.cpu import CPUInfo as ModuleCPUInfo
    from computecommons.compute.machine import Machine as ModuleMachine
    from computecommons.compute.memory import MemoryInfo as ModuleMemoryInfo

    assert PackageCPUInfo is ModuleCPUInfo
    assert PackageMemoryInfo is ModuleMemoryInfo
    assert PackageMachine is ModuleMachine
