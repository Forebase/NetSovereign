from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegistryMetadata:
    """Provenance metadata for a compact static registry."""

    name: str
    source: str
    source_url: str | None = None
    version: str | None = None
    published_at: str | None = None
    retrieved_at: str | None = None
