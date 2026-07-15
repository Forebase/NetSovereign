from ipaddress import IPv6Address, ip_address, ip_network

import pytest

from computecommons.enums import InterfaceKind, TransportProtocol
from computecommons.network import (
    InterfaceAddress,
    MACAddress,
    NetworkEndpoint,
    NetworkInterface,
    Route,
)


def test_mac_address_normalizes_common_forms() -> None:
    assert str(MACAddress("AA-BB-CC-DD-EE-FF")) == "aa:bb:cc:dd:ee:ff"
    assert str(MACAddress("aabb.ccdd.eeff")) == "aa:bb:cc:dd:ee:ff"
    assert str(MACAddress("A:B:C:D:E:F")) == "0a:0b:0c:0d:0e:0f"


@pytest.mark.parametrize(
    "value",
    ["", "aa:bb:cc:dd:ee", "gg:bb:cc:dd:ee:ff", "aa:bb:cc:dd:ee:ff:00"],
)
def test_mac_address_rejects_invalid_forms(value: str) -> None:
    with pytest.raises(ValueError, match="Invalid MAC address"):
        MACAddress(value)


def test_endpoint_accepts_hostname_and_ip_address_hosts() -> None:
    assert NetworkEndpoint("localhost", 443, TransportProtocol.TCP).port == 443
    endpoint = NetworkEndpoint(ip_address("2001:db8::1"), 53, TransportProtocol.UDP)
    assert isinstance(endpoint.host, IPv6Address)
    assert endpoint.host.version == 6


@pytest.mark.parametrize("port", [-1, 65536])
def test_endpoint_validates_port_range(port: int) -> None:
    with pytest.raises(ValueError, match="port"):
        NetworkEndpoint("localhost", port, TransportProtocol.TCP)


def test_endpoint_rejects_empty_hostnames() -> None:
    with pytest.raises(ValueError, match="host"):
        NetworkEndpoint(" ", 443, TransportProtocol.TCP)


def test_interface_accepts_addresses_and_normalized_mac() -> None:
    address = InterfaceAddress(
        address=ip_address("192.0.2.10"),
        network=ip_network("192.0.2.0/24"),
    )
    interface = NetworkInterface(
        name="eth0",
        kind=InterfaceKind.ETHERNET,
        mac_address=MACAddress("AA-BB-CC-DD-EE-FF"),
        mtu=1500,
        addresses=(address,),
    )

    assert interface.addresses == (address,)
    assert str(interface.mac_address) == "aa:bb:cc:dd:ee:ff"


@pytest.mark.parametrize("name", ["", "bad name", "bad/name", "x" * 16])
def test_interface_validates_name(name: str) -> None:
    with pytest.raises(ValueError, match="interface name"):
        NetworkInterface(name=name, kind=InterfaceKind.ETHERNET)


@pytest.mark.parametrize("mtu", [67, 65536])
def test_interface_validates_mtu_range(mtu: int) -> None:
    with pytest.raises(ValueError, match="MTU"):
        NetworkInterface(name="eth0", kind=InterfaceKind.ETHERNET, mtu=mtu)


def test_interface_address_requires_consistent_ip_versions() -> None:
    with pytest.raises(ValueError, match="versions"):
        InterfaceAddress(address=ip_address("192.0.2.10"), network=ip_network("2001:db8::/64"))


def test_route_accepts_matching_destination_and_gateway_versions() -> None:
    route = Route(
        destination=ip_network("0.0.0.0/0"),
        gateway=ip_address("192.0.2.1"),
        interface="eth0",
        metric=10,
    )

    assert str(route.gateway) == "192.0.2.1"


def test_route_rejects_mismatched_destination_and_gateway_versions() -> None:
    with pytest.raises(ValueError, match="versions"):
        Route(destination=ip_network("2001:db8::/64"), gateway=ip_address("192.0.2.1"))


def test_route_rejects_non_network_destination() -> None:
    with pytest.raises(TypeError, match="destination"):
        Route(destination="0.0.0.0/0")  # type: ignore[arg-type]


def test_route_validates_interface_and_metric() -> None:
    with pytest.raises(ValueError, match="interface"):
        Route(destination=ip_network("0.0.0.0/0"), interface="bad/name")
    with pytest.raises(ValueError, match="metric"):
        Route(destination=ip_network("0.0.0.0/0"), metric=-1)
