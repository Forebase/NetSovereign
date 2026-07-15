from __future__ import annotations

from dataclasses import dataclass

from computecommons.enums import TransportProtocol

from .metadata import RegistryMetadata


@dataclass(frozen=True, slots=True)
class ServicePort:
    service: str
    port: int
    transport: TransportProtocol
    description: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.port <= 65535:
            raise ValueError("port must be between 0 and 65535")


WELL_KNOWN_PORTS_METADATA = RegistryMetadata(
    name="well-known-ports",
    source="Curated subset of the IANA Service Name and Transport Protocol Port Number Registry",
    source_url="https://www.iana.org/assignments/service-names-port-numbers/service-names-port-numbers.xhtml",
    retrieved_at="2026-07-15",
)


WELL_KNOWN_PORTS: tuple[ServicePort, ...] = (
    ServicePort("ssh", 22, TransportProtocol.TCP, "Secure Shell"),
    ServicePort("domain", 53, TransportProtocol.TCP, "Domain Name System"),
    ServicePort("domain", 53, TransportProtocol.UDP, "Domain Name System"),
    ServicePort("http", 80, TransportProtocol.TCP, "Hypertext Transfer Protocol"),
    ServicePort("https", 443, TransportProtocol.TCP, "HTTP over TLS"),
)


def find_service_ports(service: str) -> tuple[ServicePort, ...]:
    normalized = service.strip().lower()
    return tuple(item for item in WELL_KNOWN_PORTS if item.service == normalized)
