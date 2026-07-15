from collections.abc import Callable
from ipaddress import IPv4Address, IPv6Address

import pytest

from computecommons.parsing import (
    RuntimeDescriptor,
    compare_versions,
    parse_byte_size,
    parse_endpoint,
    parse_host_port,
    parse_ip_address,
    parse_ip_network,
    parse_mac_address,
    parse_platform_tag,
    parse_port,
    parse_version,
)
from computecommons.units import ByteSize


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("512 B", ByteSize(512)),
        ("10 KiB", ByteSize(10 * 1024)),
        ("5 MiB", ByteSize(5 * 1024**2)),
        ("2 GiB", ByteSize(2 * 1024**3)),
        ("1 TB", ByteSize(1000**4)),
        ("1.5 KiB", ByteSize(1536)),
    ],
)
def test_parse_byte_size_units(value: str, expected: ByteSize) -> None:
    assert parse_byte_size(value) == expected


@pytest.mark.parametrize("value", ["", "ten MB", "1 XB", "-1 B", "1.2.3 KiB"])
def test_parse_byte_size_rejects_malformed_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_byte_size(value)


def test_parse_addresses_networks_endpoints_and_mac_addresses() -> None:
    assert parse_ip_address(" 192.0.2.1 ") == IPv4Address("192.0.2.1")
    assert parse_ip_address("fe80::1%eth0") == IPv6Address("fe80::1")
    assert str(parse_ip_network("192.0.2.9/24")) == "192.0.2.0/24"
    assert parse_port("443") == 443
    assert parse_host_port("[2001:db8::1]:8443") == ("2001:db8::1", 8443)
    assert parse_endpoint("[2001:db8::1]:443") == (IPv6Address("2001:db8::1"), 443)
    assert parse_endpoint("example.test", default_port=80) == ("example.test", 80)
    assert str(parse_mac_address("AABB.CCDD.EEFF")) == "aa:bb:cc:dd:ee:ff"


@pytest.mark.parametrize(
    "factory",
    [
        lambda: parse_ip_address(""),
        lambda: parse_ip_address("example.test"),
        lambda: parse_ip_network("192.0.2.1/24", strict=True),
        lambda: parse_port("http"),
        lambda: parse_port(70000),
        lambda: parse_host_port(":443"),
        lambda: parse_host_port("[::1"),
        lambda: parse_host_port("host:"),
        lambda: parse_mac_address("aa:bb:cc"),
    ],
)
def test_parse_address_helpers_reject_malformed_inputs(factory: Callable[[], object]) -> None:
    with pytest.raises(ValueError):
        factory()


def test_parse_versions_and_compare_prerelease_tokens() -> None:
    assert str(parse_version("v1.2")) == "1.2.0"
    assert compare_versions("1.2.3-rc1", "1.2.3") < 0
    assert compare_versions("1.2.3", "1.2.4") < 0
    assert compare_versions(parse_version("1.2.3"), "1.2.3") == 0


@pytest.mark.parametrize("value", ["", "version-one", "1..2", "1.2.3.4.5"])
def test_parse_version_rejects_malformed_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_version(value)


def test_parse_platform_tags_normalizes_neutral_descriptors() -> None:
    tag = parse_platform_tag("cpython@3.12/linux/amd64")
    assert tag.os == "linux"
    assert tag.architecture == "amd64"
    assert tag.cpu_architecture.value == "x86_64"
    assert tag.runtime == RuntimeDescriptor("cpython", "3.12")
    assert str(tag) == "linux/amd64/cpython@3.12"

    darwin = parse_platform_tag("darwin arm64")
    assert darwin.os == "macos"
    assert darwin.architecture == "arm64"


@pytest.mark.parametrize("value", ["", "linux", "linux/", "linux/amd64/variant/extra/too-much"])
def test_parse_platform_tag_rejects_malformed_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_platform_tag(value)
