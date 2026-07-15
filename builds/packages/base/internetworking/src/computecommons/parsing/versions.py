from __future__ import annotations

import re
from dataclasses import dataclass
from functools import total_ordering

_VERSION = re.compile(
    r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?"
    r"(?:[-+.]?([A-Za-z0-9][A-Za-z0-9._-]*))?\s*$"
)
_PRECEDENCE = {
    "dev": -4,
    "a": -3,
    "alpha": -3,
    "b": -2,
    "beta": -2,
    "pre": -1,
    "preview": -1,
    "rc": -1,
}
_TOKEN = re.compile(r"\d+|[A-Za-z]+")


@total_ordering
@dataclass(frozen=True, slots=True)
class Version:
    major: int
    minor: int = 0
    patch: int = 0
    suffix: str | None = None

    def __post_init__(self) -> None:
        if min(self.major, self.minor, self.patch) < 0:
            raise ValueError("version numbers cannot be negative")

    def _key(self) -> tuple[int, int, int, tuple[object, ...]]:
        return (self.major, self.minor, self.patch, _suffix_key(self.suffix))

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._key() < other._key()

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.suffix}" if self.suffix else base


def _suffix_key(suffix: str | None) -> tuple[object, ...]:
    if suffix is None:
        return (0,)
    parts: list[object] = [-1]
    for token in _TOKEN.findall(suffix.lower()):
        if token.isdecimal():
            parts.extend((1, int(token)))
        else:
            parts.extend((0, _PRECEDENCE.get(token, token)))
    return tuple(parts)


def parse_version(value: str) -> Version:
    match = _VERSION.fullmatch(value)
    if not match:
        raise ValueError(f"Invalid version: {value!r}")
    major, minor, patch, suffix = match.groups()
    if suffix is not None and suffix[0].isdigit() and "." in suffix:
        raise ValueError(f"Invalid version: {value!r}")
    return Version(int(major), int(minor or 0), int(patch or 0), suffix)


def compare_versions(left: str | Version, right: str | Version) -> int:
    left_version = parse_version(left) if isinstance(left, str) else left
    right_version = parse_version(right) if isinstance(right, str) else right
    return (left_version > right_version) - (left_version < right_version)
