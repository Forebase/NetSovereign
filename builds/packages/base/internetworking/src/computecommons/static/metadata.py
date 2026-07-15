from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegistryMetadata:
    """Provenance and curation metadata for a compact static registry.

    Static registries in the core package are intentionally small, curated
    snapshots. Complete externally maintained registries should be distributed
    through optional data packages instead of being embedded here.
    """

    name: str
    source: str
    package_curation_version: str
    compactness_notes: str
    source_url: str | None = None
    source_version: str | None = None
    published_at: str | None = None
    retrieved_at: str | None = None
