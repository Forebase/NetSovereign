import pytest

from computecommons.units import Bandwidth, ByteSize, Frequency, Percentage


def test_byte_size_constructors() -> None:
    assert ByteSize.gibibytes(2).bytes == 2 * 1024**3
    assert str(ByteSize.mebibytes(1)) == "1 MiB"


def test_quantities_reject_negative_values() -> None:
    with pytest.raises(ValueError):
        ByteSize(-1)
    with pytest.raises(ValueError):
        Frequency(-1)
    with pytest.raises(ValueError):
        Bandwidth(-1)


def test_percentage_range() -> None:
    assert Percentage(50).value == 50
    with pytest.raises(ValueError):
        Percentage(101)
