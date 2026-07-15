"""Architecture helpers exposed from the compute package.

The canonical architecture enum lives in :mod:`computecommons.enums.compute`, and
normalization data lives in :mod:`computecommons.static.architectures`. This module
provides the compute-package import path for that accepted public API without
introducing duplicate value objects.
"""

from computecommons.enums import CPUArchitecture
from computecommons.static import ARCHITECTURE_ALIASES, normalize_architecture

__all__ = ["ARCHITECTURE_ALIASES", "CPUArchitecture", "normalize_architecture"]
