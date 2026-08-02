"""NetSovereign sovereign domain foundation."""

from .manifest import WorldManifest, build_manifest
from .specification import WorldSpec
from .validation import Diagnostic, validate_spec

__all__ = ["Diagnostic", "WorldManifest", "WorldSpec", "build_manifest", "validate_spec"]
__version__ = "0.1.0"
