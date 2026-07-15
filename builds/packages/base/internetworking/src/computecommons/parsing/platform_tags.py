from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PlatformTag:
    os: str
    architecture: str
    variant: str | None = None

    def __post_init__(self) -> None:
        if not self.os or not self.architecture:
            raise ValueError("Platform tags require os and architecture")

    def __str__(self) -> str:
        return "/".join(part for part in (self.os, self.architecture, self.variant) if part)


def parse_platform_tag(value: str) -> PlatformTag:
    parts = [part.strip().lower() for part in value.split("/")]
    if len(parts) not in (2, 3) or any(not part for part in parts):
        raise ValueError("Platform tags must be 'os/architecture[/variant]'")
    return PlatformTag(*parts)
