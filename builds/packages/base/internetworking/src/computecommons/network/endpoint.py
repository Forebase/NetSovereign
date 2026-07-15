from __future__ import annotations

from dataclasses import dataclass

from computecommons.enums import TransportProtocol

from .address import IPAddress

_MIN_PORT = 0
_MAX_PORT = 65535


@dataclass(frozen=True, slots=True)
class NetworkEndpoint:
    host: str | IPAddress
    port: int
    transport: TransportProtocol

    def __post_init__(self) -> None:
        if isinstance(self.host, str) and not self.host.strip():
            raise ValueError("host cannot be empty")
        if not _MIN_PORT <= self.port <= _MAX_PORT:
            raise ValueError(f"port must be between {_MIN_PORT} and {_MAX_PORT}")


__all__ = ["NetworkEndpoint"]
