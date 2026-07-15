from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from .metadata import RegistryMetadata


@dataclass(frozen=True, slots=True)
class Vendor:
    slug: str
    name: str
    homepage: str | None = None


VENDORS_METADATA = RegistryMetadata(
    name="vendors",
    source="Curated aliases for common compute vendors",
    version="0.1.0",
    published_at="2026-07-15",
)


VENDORS: tuple[Vendor, ...] = (
    Vendor("amazon", "Amazon", "https://aws.amazon.com/"),
    Vendor("amd", "AMD", "https://www.amd.com/"),
    Vendor("apple", "Apple", "https://www.apple.com/"),
    Vendor("canonical", "Canonical", "https://canonical.com/"),
    Vendor("google", "Google", "https://cloud.google.com/"),
    Vendor("ibm", "IBM", "https://www.ibm.com/"),
    Vendor("intel", "Intel", "https://www.intel.com/"),
    Vendor("microsoft", "Microsoft", "https://www.microsoft.com/"),
    Vendor("red-hat", "Red Hat", "https://www.redhat.com/"),
    Vendor("oracle", "Oracle", "https://www.oracle.com/"),
)

VENDOR_BY_SLUG = MappingProxyType({item.slug: item for item in VENDORS})
VENDOR_ALIASES = MappingProxyType(
    {
        "amazon": "amazon",
        "aws": "amazon",
        "amd": "amd",
        "advanced micro devices": "amd",
        "apple": "apple",
        "canonical": "canonical",
        "google": "google",
        "gcp": "google",
        "ibm": "ibm",
        "intel": "intel",
        "microsoft": "microsoft",
        "msft": "microsoft",
        "red hat": "red-hat",
        "red-hat": "red-hat",
        "oracle": "oracle",
    }
)


def normalize_vendor(value: str) -> str | None:
    return VENDOR_ALIASES.get(value.strip().lower())


def find_vendor(value: str) -> Vendor | None:
    normalized = normalize_vendor(value)
    if normalized is None:
        return None
    return VENDOR_BY_SLUG[normalized]
