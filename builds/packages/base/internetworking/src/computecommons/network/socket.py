from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from computecommons.enums import TransportProtocol

from .endpoint import NetworkEndpoint


class SocketAddressFamily(StrEnum):
    IPV4 = "ipv4"
    IPV6 = "ipv6"
    UNIX = "unix"


class SocketKind(StrEnum):
    STREAM = "stream"
    DATAGRAM = "datagram"
    RAW = "raw"


@dataclass(frozen=True, slots=True)
class SocketDescriptor:
    family: SocketAddressFamily
    kind: SocketKind
    protocol: TransportProtocol | None = None
    local_endpoint: NetworkEndpoint | None = None
    remote_endpoint: NetworkEndpoint | None = None


__all__ = ["SocketAddressFamily", "SocketDescriptor", "SocketKind"]
