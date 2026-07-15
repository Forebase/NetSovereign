from dataclasses import FrozenInstanceError

import pytest

from computecommons.enums import CPUArchitecture, OperatingSystemFamily
from computecommons.static import (
    FILESYSTEM_BY_NAME,
    MEDIA_TYPE_BY_VALUE,
    VENDOR_BY_SLUG,
    find_filesystem,
    find_media_type,
    find_media_type_by_extension,
    find_operating_system,
    find_service_ports,
    find_vendor,
    normalize_architecture,
    normalize_filesystem,
    normalize_media_type,
    normalize_operating_system,
    normalize_vendor,
    operating_system_family,
)


def test_architecture_aliases() -> None:
    assert normalize_architecture("AMD64") is CPUArchitecture.X86_64
    assert normalize_architecture("mystery") is CPUArchitecture.UNKNOWN


def test_port_lookup() -> None:
    assert {item.port for item in find_service_ports("domain")} == {53}


def test_filesystem_registry_lookup() -> None:
    filesystem = find_filesystem("ISO-9660")

    assert normalize_filesystem(" HFSPlus ") == "hfs+"
    assert filesystem is FILESYSTEM_BY_NAME["iso9660"]
    assert filesystem is not None
    assert filesystem.case_sensitive is False
    assert find_filesystem("unknownfs") is None

    with pytest.raises(FrozenInstanceError):
        FILESYSTEM_BY_NAME["ext4"].name = "other"  # type: ignore[misc]


def test_media_type_registry_lookup() -> None:
    media_type = find_media_type_by_extension(".jpg")

    assert normalize_media_type("IMAGE/JPG") == "image/jpeg"
    assert media_type is MEDIA_TYPE_BY_VALUE["image/jpeg"]
    assert media_type is not None
    assert media_type.value == "image/jpeg"
    assert find_media_type("application/json") is MEDIA_TYPE_BY_VALUE["application/json"]
    assert find_media_type_by_extension("unknown") is None


def test_operating_system_registry_lookup() -> None:
    operating_system = find_operating_system("Darwin")

    assert normalize_operating_system("Red Hat Enterprise Linux") == "rhel"
    assert operating_system is not None
    assert operating_system.family is OperatingSystemFamily.MACOS
    assert operating_system_family("win64") is OperatingSystemFamily.WINDOWS
    assert operating_system_family("mystery") is OperatingSystemFamily.UNKNOWN


def test_vendor_registry_lookup() -> None:
    vendor = find_vendor("MSFT")

    assert normalize_vendor("Red Hat") == "red-hat"
    assert vendor is VENDOR_BY_SLUG["microsoft"]
    assert vendor is not None
    assert vendor.name == "Microsoft"
    assert find_vendor("unknown") is None
