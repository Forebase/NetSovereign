from enum import StrEnum


class InterfaceKind(StrEnum):
    ETHERNET = "ethernet"
    WIFI = "wifi"
    LOOPBACK = "loopback"
    BRIDGE = "bridge"
    BOND = "bond"
    VLAN = "vlan"
    TUNNEL = "tunnel"
    VIRTUAL = "virtual"
    CELLULAR = "cellular"
    UNKNOWN = "unknown"


class TransportProtocol(StrEnum):
    TCP = "tcp"
    UDP = "udp"
    SCTP = "sctp"
    DCCP = "dccp"
    QUIC = "quic"
