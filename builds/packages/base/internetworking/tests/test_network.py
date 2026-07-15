from ipaddress import ip_address, ip_network

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


def test_endpoint_validates_port() -> None:
    with pytest.raises(ValueError):
        NetworkEndpoint("localhost", 65536, TransportProtocol.TCP)


def test_interface_and_route() -> None:
    address = InterfaceAddress(
        address=ip_address("192.0.2.10"),
        network=ip_network("192.0.2.0/24"),
    )
    interface = NetworkInterface(
        name="eth0",
        kind=InterfaceKind.ETHERNET,
        addresses=(address,),
    )
    route = Route(
        destination=ip_network("0.0.0.0/0"),
        gateway=ip_address("192.0.2.1"),
        interface="eth0",
    )
    assert interface.addresses[0] == address
    assert str(route.gateway) == "192.0.2.1"
