from __future__ import annotations

import re
from dataclasses import dataclass
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network

type IPAddress = IPv4Address | IPv6Address
type IPNetwork = IPv4Network | IPv6Network

_MAC_HEX = re.compile(r"^[0-9a-f]{12}$")


@dataclass(frozen=True, order=True, slots=True)
class MACAddress:
    value: str

    def __post_init__(self) -> None:
        compact = self.value.lower().replace(":", "").replace("-", "").replace(".", "")
        if not _MAC_HEX.fullmatch(compact):
            raise ValueError(f"Invalid MAC address: {self.value!r}")
        normalized = ":".join(compact[index : index + 2] for index in range(0, 12, 2))
        object.__setattr__(self, "value", normalized)

    @property
    def is_multicast(self) -> bool:
        return bool(int(self.value[:2], 16) & 1)

    @property
    def is_locally_administered(self) -> bool:
        return bool(int(self.value[:2], 16) & 2)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class InterfaceAddress:
    address: IPAddress
    network: IPNetwork | None = None
    broadcast: IPAddress | None = None
    scope: str | None = None

    def __post_init__(self) -> None:
        if self.network is not None and self.address.version != self.network.version:
            raise ValueError("address and network IP versions must match")
        if self.broadcast is not None and self.address.version != self.broadcast.version:
            raise ValueError("address and broadcast IP versions must match")
