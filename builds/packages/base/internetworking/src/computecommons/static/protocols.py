from __future__ import annotations

from types import MappingProxyType

IP_PROTOCOL_NUMBERS = MappingProxyType(
    {1: "icmp", 6: "tcp", 17: "udp", 41: "ipv6", 58: "icmpv6", 132: "sctp"}
)
