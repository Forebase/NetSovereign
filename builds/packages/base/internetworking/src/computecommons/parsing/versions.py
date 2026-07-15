from __future__ import annotations

import re
from dataclasses import dataclass

_VERSION = re.compile(
    r"^\s*v?(\d+)(?:\.(\d+))?(?:\.(\d+))?"
    r"(?:[-+.]?([A-Za-z0-9][A-Za-z0-9._-]*))?\s*$"
)


@dataclass(frozen=True, order=True, slots=True)
class Version:
    major: int
    minor: int = 0
    patch: int = 0
    suffix: str | None = None

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.suffix}" if self.suffix else base


def parse_version(value: str) -> Version:
    match = _VERSION.fullmatch(value)
    if not match:
        raise ValueError(f"Invalid version: {value!r}")
    major, minor, patch, suffix = match.groups()
    return Version(int(major), int(minor or 0), int(patch or 0), suffix)
