"""Shared, strict model primitives."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """A domain object: unknown/provider fields are never silently accepted."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True, use_enum_values=True)
