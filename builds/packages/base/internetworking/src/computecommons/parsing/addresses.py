from __future__ import annotations

from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network

IPAddress = IPv4Address | IPv6Address
IPNetwork = IPv4Network | IPv6Network


def parse_ip_address(value: str) -> IPAddress:
    return ip_address(value.strip())


def parse_ip_network(value: str, *, strict: bool = False) -> IPNetwork:
    return ip_network(value.strip(), strict=strict)


def parse_host_port(value: str, *, default_port: int | None = None) -> tuple[str, int | None]:
    text = value.strip()
    if text.startswith("["):
        host, sep, rest = text[1:].partition("]")
        if not sep:
            raise ValueError("Bracketed host is missing closing bracket")
        if rest.startswith(":"):
            return host, int(rest[1:])
        if rest:
            raise ValueError("Unexpected text after bracketed host")
        return host, default_port
    host, sep, port = text.rpartition(":")
    if sep and ":" not in host:
        return host, int(port)
    return text, default_port
