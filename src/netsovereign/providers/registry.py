"""Deterministic, injected provider registry."""

from __future__ import annotations

from .contracts import CapabilityRequirement, Provider, ProviderDescriptor


class ProviderResolutionError(ValueError):
    """A stable resolution failure with a machine-readable code."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def _compatible(required: str, offered: str) -> bool:
    return required.split(".", 1)[0] == offered.split(".", 1)[0]


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        identity = provider.describe().id
        if identity in self._providers:
            raise ProviderResolutionError(
                "duplicate_provider", f"provider {identity!r} is registered"
            )
        self._providers[identity] = provider

    def descriptors(self) -> list[ProviderDescriptor]:
        return [self._providers[key].describe() for key in sorted(self._providers)]

    def get(self, provider_id: str) -> Provider:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise ProviderResolutionError("requested_provider_absent", provider_id) from exc

    def resolve(
        self, requirement: CapabilityRequirement, provider_id: str | None = None
    ) -> Provider:
        candidates = [self.get(provider_id)] if provider_id else list(self._providers.values())
        supported: list[Provider] = []
        incompatible = False
        for provider in candidates:
            descriptor = provider.describe()
            declarations = [item for item in descriptor.capabilities if item.id == requirement.id]
            if declarations and any(
                _compatible(requirement.version, item.version) for item in declarations
            ):
                supported.append(provider)
            elif declarations:
                incompatible = True
        if not supported:
            code = (
                "capability_version_incompatible"
                if incompatible
                else (
                    "requested_provider_unsupported"
                    if provider_id
                    else "no_provider_supports_capability"
                )
            )
            raise ProviderResolutionError(
                code, f"cannot resolve {requirement.id}@{requirement.version}"
            )
        if len(supported) > 1:
            raise ProviderResolutionError("ambiguous_provider", requirement.id)
        descriptor = supported[0].describe()
        if not descriptor.available or not descriptor.healthy:
            raise ProviderResolutionError("provider_unavailable", descriptor.id)
        return supported[0]
