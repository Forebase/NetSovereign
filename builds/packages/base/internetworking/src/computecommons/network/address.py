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
        compact = self._compact(self.value)
        if not _MAC_HEX.fullmatch(compact):
            raise ValueError(f"Invalid MAC address: {self.value!r}")
        normalized = ":".join(compact[index : index + 2] for index in range(0, 12, 2))
        object.__setattr__(self, "value", normalized)

    @staticmethod
    def _compact(value: str) -> str:
        lowered = value.lower()
        for separator in (":", "-"):
            if separator in lowered:
                parts = lowered.split(separator)
                if len(parts) == 6 and all(1 <= len(part) <= 2 for part in parts):
                    return "".join(part.zfill(2) for part in parts)
        return lowered.replace(":", "").replace("-", "").replace(".", "")

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
        if not isinstance(self.address, IPv4Address | IPv6Address):
            raise TypeError("address must be an IPv4Address or IPv6Address")
        if self.network is not None and not isinstance(self.network, IPv4Network | IPv6Network):
            raise TypeError("network must be an IPv4Network or IPv6Network")
        if self.broadcast is not None and not isinstance(self.broadcast, IPv4Address | IPv6Address):
            raise TypeError("broadcast must be an IPv4Address or IPv6Address")
        if self.network is not None and self.address.version != self.network.version:
            raise ValueError("address and network IP versions must match")
        if self.broadcast is not None and self.address.version != self.broadcast.version:
            raise ValueError("address and broadcast IP versions must match")
