from __future__ import annotations

from dataclasses import dataclass

from computecommons.enums import InterfaceKind, TransportProtocol
from computecommons.units import Bandwidth

from .address import IPAddress, IPNetwork, InterfaceAddress, MACAddress


@dataclass(frozen=True, slots=True)
class NetworkEndpoint:
    host: str | IPAddress
    port: int
    transport: TransportProtocol

    def __post_init__(self) -> None:
        if not 0 <= self.port <= 65535:
            raise ValueError("port must be between 0 and 65535")
        if isinstance(self.host, str) and not self.host.strip():
            raise ValueError("host cannot be empty")


@dataclass(frozen=True, slots=True)
class NetworkInterface:
    name: str
    kind: InterfaceKind
    index: int | None = None
    mac_address: MACAddress | None = None
    mtu: int | None = None
    is_up: bool | None = None
    speed: Bandwidth | None = None
    addresses: tuple[InterfaceAddress, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("interface name cannot be empty")
        if self.index is not None and self.index < 0:
            raise ValueError("interface index cannot be negative")
        if self.mtu is not None and self.mtu < 1:
            raise ValueError("MTU must be positive")
        object.__setattr__(self, "addresses", tuple(self.addresses))


@dataclass(frozen=True, slots=True)
class Route:
    destination: IPNetwork
    gateway: IPAddress | None = None
    interface: str | None = None
    metric: int | None = None
    table: int | str | None = None
    protocol: str | None = None

    def __post_init__(self) -> None:
        if self.gateway is not None and self.gateway.version != self.destination.version:
            raise ValueError("gateway and destination IP versions must match")
        if self.metric is not None and self.metric < 0:
            raise ValueError("route metric cannot be negative")
