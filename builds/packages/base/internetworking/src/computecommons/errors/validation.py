from .base import ComputeCommonsError


class ValidationError(ComputeCommonsError, ValueError):
    """Raised when a value cannot satisfy a computecommons invariant."""
