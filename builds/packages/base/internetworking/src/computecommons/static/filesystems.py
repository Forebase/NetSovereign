from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class Filesystem:
    name: str
    description: str
    case_sensitive: bool = True
    journaling: bool = False


FILESYSTEMS: tuple[Filesystem, ...] = (
    Filesystem("ext4", "Fourth extended filesystem", journaling=True),
    Filesystem("xfs", "XFS filesystem", journaling=True),
    Filesystem("btrfs", "B-tree filesystem", journaling=True),
    Filesystem("zfs", "ZFS filesystem", journaling=True),
    Filesystem("ntfs", "New Technology File System", case_sensitive=False, journaling=True),
    Filesystem("fat32", "File Allocation Table 32", case_sensitive=False),
    Filesystem("exfat", "Extensible File Allocation Table", case_sensitive=False),
    Filesystem("apfs", "Apple File System", case_sensitive=False, journaling=True),
    Filesystem("hfs+", "Hierarchical File System Plus", case_sensitive=False, journaling=True),
    Filesystem("iso9660", "ISO 9660 optical disc filesystem", case_sensitive=False),
)

FILESYSTEM_BY_NAME = MappingProxyType({item.name: item for item in FILESYSTEMS})
FILESYSTEM_ALIASES = MappingProxyType(
    {
        "ext4": "ext4",
        "xfs": "xfs",
        "btrfs": "btrfs",
        "zfs": "zfs",
        "ntfs": "ntfs",
        "fat": "fat32",
        "fat32": "fat32",
        "exfat": "exfat",
        "apfs": "apfs",
        "hfs": "hfs+",
        "hfs+": "hfs+",
        "hfsplus": "hfs+",
        "iso9660": "iso9660",
        "iso-9660": "iso9660",
    }
)


def normalize_filesystem(value: str) -> str | None:
    return FILESYSTEM_ALIASES.get(value.strip().lower())


def find_filesystem(value: str) -> Filesystem | None:
    normalized = normalize_filesystem(value)
    if normalized is None:
        return None
    return FILESYSTEM_BY_NAME[normalized]
