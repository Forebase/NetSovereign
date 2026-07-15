import pytest

from computecommons.compute import CPUInfo, Machine, MemoryInfo, normalize_architecture
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


def test_architecture_api_reexports_canonical_helpers() -> None:
    from computecommons.compute import CPUArchitecture as PackageCPUArchitecture
    from computecommons.compute.architecture import (
        ARCHITECTURE_ALIASES,
    )
    from computecommons.compute.architecture import (
        CPUArchitecture as ModuleCPUArchitecture,
    )
    from computecommons.compute.architecture import (
        normalize_architecture as module_normalize_architecture,
    )
    from computecommons.static import normalize_architecture as static_normalize_architecture

    assert ModuleCPUArchitecture is CPUArchitecture
    assert PackageCPUArchitecture is CPUArchitecture
    assert module_normalize_architecture is static_normalize_architecture
    assert normalize_architecture("AMD64") is CPUArchitecture.X86_64
    assert ARCHITECTURE_ALIASES["amd64"] is CPUArchitecture.X86_64


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
