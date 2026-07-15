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
