from __future__ import annotations

import re
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

from .address import IPAddress, IPNetwork

_INTERFACE_NAME = re.compile(r"^[A-Za-z0-9_.:-]{1,15}$")


@dataclass(frozen=True, slots=True)
class Route:
    destination: IPNetwork
    gateway: IPAddress | None = None
    interface: str | None = None
    metric: int | None = None
    table: int | str | None = None
    protocol: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.destination, IPv4Network | IPv6Network):
            raise TypeError("destination must be an IPv4Network or IPv6Network")
        if self.gateway is not None:
            if not isinstance(self.gateway, IPv4Address | IPv6Address):
                raise TypeError("gateway must be an IPv4Address or IPv6Address")
            if self.gateway.version != self.destination.version:
                raise ValueError("gateway and destination IP versions must match")
        if self.interface is not None and not _INTERFACE_NAME.fullmatch(self.interface):
            raise ValueError("interface name must be 1-15 valid interface characters")
        if self.metric is not None and self.metric < 0:
            raise ValueError("route metric cannot be negative")
        if isinstance(self.table, int) and self.table < 0:
            raise ValueError("route table cannot be negative")
        if isinstance(self.table, str) and not self.table.strip():
            raise ValueError("route table cannot be empty")
        if self.protocol is not None and not self.protocol.strip():
            raise ValueError("route protocol cannot be empty")


__all__ = ["Route"]
