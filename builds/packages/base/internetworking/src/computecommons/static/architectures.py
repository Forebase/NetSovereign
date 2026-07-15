from __future__ import annotations

from types import MappingProxyType

from computecommons.enums import CPUArchitecture

from .metadata import RegistryMetadata

ARCHITECTURE_ALIASES_METADATA = RegistryMetadata(
    name="architecture-aliases",
    source="Curated aliases for common CPU architectures",
    version="0.1.0",
    published_at="2026-07-15",
)


ARCHITECTURE_ALIASES = MappingProxyType(
    {
        "amd64": CPUArchitecture.X86_64,
        "x86_64": CPUArchitecture.X86_64,
        "x64": CPUArchitecture.X86_64,
        "i386": CPUArchitecture.X86,
        "i686": CPUArchitecture.X86,
        "aarch64": CPUArchitecture.ARM64,
        "arm64": CPUArchitecture.ARM64,
        "armv7l": CPUArchitecture.ARM,
        "riscv64": CPUArchitecture.RISCV64,
        "ppc64le": CPUArchitecture.PPC64LE,
        "s390x": CPUArchitecture.S390X,
        "wasm32": CPUArchitecture.WASM32,
    }
)


def normalize_architecture(value: str) -> CPUArchitecture:
    return ARCHITECTURE_ALIASES.get(value.strip().lower(), CPUArchitecture.UNKNOWN)
