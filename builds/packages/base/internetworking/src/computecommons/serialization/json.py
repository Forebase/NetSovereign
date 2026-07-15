from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from types import MappingProxyType
from typing import Any
from uuid import UUID

_JSON_SCALAR = str | int | float | bool
_IP_VALUE = IPv4Address | IPv6Address | IPv4Network | IPv6Network


def _sort_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def to_primitive(value: Any) -> Any:
    """Recursively convert supported values to JSON-compatible primitives."""
    if value is None or isinstance(value, _JSON_SCALAR):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, UUID | _IP_VALUE):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, timedelta):
        return value.total_seconds()
    if is_dataclass(value) and not isinstance(value, type):
        return {item.name: to_primitive(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping | MappingProxyType):
        return {str(key): to_primitive(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [to_primitive(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted((to_primitive(item) for item in value), key=_sort_key)
    raise TypeError(f"Unsupported value for serialization: {type(value).__name__}")


def dumps(value: Any, *, indent: int | None = None, sort_keys: bool = False) -> str:
    return json.dumps(to_primitive(value), indent=indent, sort_keys=sort_keys)
