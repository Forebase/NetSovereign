from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from computecommons.enums import OperatingSystemFamily


@dataclass(frozen=True, slots=True)
class OperatingSystemRelease:
    name: str
    family: OperatingSystemFamily
    vendor: str | None = None


OPERATING_SYSTEMS: tuple[OperatingSystemRelease, ...] = (
    OperatingSystemRelease("linux", OperatingSystemFamily.LINUX),
    OperatingSystemRelease("ubuntu", OperatingSystemFamily.LINUX, "canonical"),
    OperatingSystemRelease("debian", OperatingSystemFamily.LINUX),
    OperatingSystemRelease("fedora", OperatingSystemFamily.LINUX, "red-hat"),
    OperatingSystemRelease("rhel", OperatingSystemFamily.LINUX, "red-hat"),
    OperatingSystemRelease("windows", OperatingSystemFamily.WINDOWS, "microsoft"),
    OperatingSystemRelease("windows-server", OperatingSystemFamily.WINDOWS, "microsoft"),
    OperatingSystemRelease("macos", OperatingSystemFamily.MACOS, "apple"),
    OperatingSystemRelease("freebsd", OperatingSystemFamily.BSD),
    OperatingSystemRelease("android", OperatingSystemFamily.ANDROID, "google"),
    OperatingSystemRelease("ios", OperatingSystemFamily.IOS, "apple"),
)

OPERATING_SYSTEM_BY_NAME = MappingProxyType({item.name: item for item in OPERATING_SYSTEMS})
OPERATING_SYSTEM_ALIASES = MappingProxyType(
    {
        "linux": "linux",
        "gnu/linux": "linux",
        "ubuntu": "ubuntu",
        "debian": "debian",
        "fedora": "fedora",
        "red hat enterprise linux": "rhel",
        "rhel": "rhel",
        "windows": "windows",
        "win32": "windows",
        "win64": "windows",
        "windows server": "windows-server",
        "windows-server": "windows-server",
        "darwin": "macos",
        "macos": "macos",
        "mac os": "macos",
        "osx": "macos",
        "freebsd": "freebsd",
        "android": "android",
        "ios": "ios",
    }
)


def normalize_operating_system(value: str) -> str | None:
    return OPERATING_SYSTEM_ALIASES.get(value.strip().lower())


def find_operating_system(value: str) -> OperatingSystemRelease | None:
    normalized = normalize_operating_system(value)
    if normalized is None:
        return None
    return OPERATING_SYSTEM_BY_NAME[normalized]


def operating_system_family(value: str) -> OperatingSystemFamily:
    operating_system = find_operating_system(value)
    if operating_system is None:
        return OperatingSystemFamily.UNKNOWN
    return operating_system.family
