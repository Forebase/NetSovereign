from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .address import IPAddress

DNSRecordType = Literal["A", "AAAA", "CNAME", "MX", "NS", "PTR", "SOA", "SRV", "TXT"]


@dataclass(frozen=True, slots=True)
class DNSRecord:
    name: str
    record_type: DNSRecordType
    value: str | IPAddress
    ttl: int | None = None
    priority: int | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("DNS record name cannot be empty")
        if isinstance(self.value, str) and not self.value.strip():
            raise ValueError("DNS record value cannot be empty")
        if self.ttl is not None and self.ttl < 0:
            raise ValueError("DNS record TTL cannot be negative")
        if self.priority is not None and self.priority < 0:
            raise ValueError("DNS record priority cannot be negative")


__all__ = ["DNSRecord", "DNSRecordType"]
