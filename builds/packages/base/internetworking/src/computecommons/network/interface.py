from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from computecommons.enums import InterfaceKind
from computecommons.units import Bandwidth

from .address import InterfaceAddress, MACAddress

_MIN_MTU = 68
_MAX_MTU = 65535
_INTERFACE_NAME = re.compile(r"^[A-Za-z0-9_.:-]{1,15}$")


@dataclass(frozen=True, slots=True)
class NetworkInterface:
    name: str
    kind: InterfaceKind
    index: int | None = None
    mac_address: MACAddress | None = None
    mtu: int | None = None
    is_up: bool | None = None
    speed: Bandwidth | None = None
    addresses: Sequence[InterfaceAddress] = ()

    def __post_init__(self) -> None:
        if not _INTERFACE_NAME.fullmatch(self.name):
            raise ValueError(
                "interface name must be 1-15 characters containing only letters, "
                "numbers, underscores, periods, colons, or hyphens"
            )
        if self.index is not None and self.index < 0:
            raise ValueError("interface index cannot be negative")
        if self.mtu is not None and not _MIN_MTU <= self.mtu <= _MAX_MTU:
            raise ValueError(f"MTU must be between {_MIN_MTU} and {_MAX_MTU}")
        object.__setattr__(self, "addresses", tuple(self.addresses))


__all__ = ["NetworkInterface"]
