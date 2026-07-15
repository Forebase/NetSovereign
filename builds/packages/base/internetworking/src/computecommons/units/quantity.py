from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, order=True, slots=True)
class ByteSize:
    bytes: int

    def __post_init__(self) -> None:
        if self.bytes < 0:
            raise ValueError("Byte size cannot be negative")

    @classmethod
    def kibibytes(cls, value: int | float) -> ByteSize:
        return cls(round(value * 1024))

    @classmethod
    def mebibytes(cls, value: int | float) -> ByteSize:
        return cls(round(value * 1024**2))

    @classmethod
    def gibibytes(cls, value: int | float) -> ByteSize:
        return cls(round(value * 1024**3))

    @classmethod
    def tebibytes(cls, value: int | float) -> ByteSize:
        return cls(round(value * 1024**4))

    def __str__(self) -> str:
        value = float(self.bytes)
        for suffix in ("B", "KiB", "MiB", "GiB", "TiB", "PiB"):
            if value < 1024 or suffix == "PiB":
                return f"{value:g} {suffix}"
            value /= 1024
        raise AssertionError("unreachable")


@dataclass(frozen=True, order=True, slots=True)
class Frequency:
    hertz: int

    def __post_init__(self) -> None:
        if self.hertz < 0:
            raise ValueError("Frequency cannot be negative")

    @classmethod
    def megahertz(cls, value: int | float) -> Frequency:
        return cls(round(value * 1_000_000))

    @classmethod
    def gigahertz(cls, value: int | float) -> Frequency:
        return cls(round(value * 1_000_000_000))


@dataclass(frozen=True, order=True, slots=True)
class Bandwidth:
    bits_per_second: int

    def __post_init__(self) -> None:
        if self.bits_per_second < 0:
            raise ValueError("Bandwidth cannot be negative")

    @classmethod
    def megabits(cls, value: int | float) -> Bandwidth:
        return cls(round(value * 1_000_000))

    @classmethod
    def gigabits(cls, value: int | float) -> Bandwidth:
        return cls(round(value * 1_000_000_000))


@dataclass(frozen=True, order=True, slots=True)
class Duration:
    nanoseconds: int

    def __post_init__(self) -> None:
        if self.nanoseconds < 0:
            raise ValueError("Duration cannot be negative")

    @classmethod
    def seconds(cls, value: int | float) -> Duration:
        return cls(round(value * 1_000_000_000))

    def as_timedelta(self) -> timedelta:
        return timedelta(microseconds=self.nanoseconds / 1000)


@dataclass(frozen=True, order=True, slots=True)
class Percentage:
    value: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.value <= 100.0:
            raise ValueError("Percentage must be between 0 and 100")
