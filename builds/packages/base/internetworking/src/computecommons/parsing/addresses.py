from __future__ import annotations

import re
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network

from computecommons.network.address import MACAddress

IPAddress = IPv4Address | IPv6Address
IPNetwork = IPv4Network | IPv6Network

_MIN_PORT = 0
_MAX_PORT = 65535
_ZONE = re.compile(r"%[A-Za-z0-9_.~-]+$")


def _require_text(value: str, *, name: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{name} cannot be empty")
    return text


def parse_ip_address(value: str) -> IPAddress:
    """Parse an IPv4 or IPv6 address without resolving host names."""
    text = _require_text(value, name="IP address")
    # ipaddress intentionally rejects scoped IPv6 strings; strip the purely local
    # zone token so callers can parse interface-form values without host lookup.
    text = _ZONE.sub("", text)
    return ip_address(text)


def parse_ip_network(value: str, *, strict: bool = False) -> IPNetwork:
    """Parse an IPv4 or IPv6 network without reading host routing state."""
    return ip_network(_require_text(value, name="IP network"), strict=strict)


def parse_port(value: str | int) -> int:
    if isinstance(value, int):
        port = value
    else:
        text = _require_text(value, name="port")
        if not text.isdecimal():
            raise ValueError(f"Invalid port: {value!r}")
        port = int(text)
    if not _MIN_PORT <= port <= _MAX_PORT:
        raise ValueError(f"port must be between {_MIN_PORT} and {_MAX_PORT}")
    return port


def parse_host_port(value: str, *, default_port: int | None = None) -> tuple[str, int | None]:
    """Parse host[:port] or [IPv6-literal][:port] without DNS resolution."""
    text = _require_text(value, name="endpoint")
    fallback_port = None if default_port is None else parse_port(default_port)
    if text.startswith("["):
        host, sep, rest = text[1:].partition("]")
        if not sep:
            raise ValueError("Bracketed host is missing closing bracket")
        if not host.strip():
            raise ValueError("host cannot be empty")
        if rest.startswith(":"):
            return host, parse_port(rest[1:])
        if rest:
            raise ValueError("Unexpected text after bracketed host")
        return host, fallback_port

    host, sep, port = text.rpartition(":")
    if sep and ":" not in host:
        if not host.strip():
            raise ValueError("host cannot be empty")
        return host, parse_port(port)
    return text, fallback_port


def parse_endpoint(
    value: str, *, default_port: int | None = None
) -> tuple[str | IPAddress, int | None]:
    """Parse an endpoint, converting literal IP hosts to ipaddress objects."""
    host, port = parse_host_port(value, default_port=default_port)
    try:
        return parse_ip_address(host), port
    except ValueError:
        if not host.strip():
            raise ValueError("host cannot be empty") from None
        return host, port


def parse_mac_address(value: str) -> MACAddress:
    """Parse and normalize colon, hyphen, dotted, or compact MAC notation."""
    return MACAddress(_require_text(value, name="MAC address"))
