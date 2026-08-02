"""Provider-neutral capability contracts and the non-operational fake provider."""

from .contracts import *  # noqa: F403
from .fake import FakeProvider
from .registry import ProviderRegistry

__all__ = ["FakeProvider", "ProviderRegistry"]
