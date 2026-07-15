from __future__ import annotations

from types import MappingProxyType

from .metadata import RegistryMetadata

IP_PROTOCOL_NUMBERS_METADATA = RegistryMetadata(
    name="ip-protocol-numbers",
    source="Curated subset of the IANA Protocol Numbers registry",
    source_url="https://www.iana.org/assignments/protocol-numbers/protocol-numbers.xhtml",
    retrieved_at="2026-07-15",
)


IP_PROTOCOL_NUMBERS = MappingProxyType(
    {1: "icmp", 6: "tcp", 17: "udp", 41: "ipv6", 58: "icmpv6", 132: "sctp"}
)
