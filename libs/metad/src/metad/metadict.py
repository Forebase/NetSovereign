"""
MetaDict - A metadictionary development framework kit for Python 3.13+.
"""

from __future__ import annotations

import json
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    TypeVar,
    Union,
    get_origin,
    get_args,
)
from dataclasses import dataclass, field
from functools import partial
import inspect


__version__ = "0.1.0"


class ValidationError(Exception):
    """Raised when a field validation fails."""
    def __init__(self, field: str, value: Any, message: str):
        self.field = field
        self.value = value
        self.message = message
        super().__init__(f"Validation error for field '{field}': {message}")


@dataclass
class Field:
    """
    Defines a metadata field for a MetaDict.
    """
    type: Optional[Type] = None
    default: Any = None
    required: bool = True
    validator: Optional[Callable[[Any], bool]] = None
    description: Optional[str] = None
    alias: Optional[str] = None          # Alternative key name
    default_factory: Optional[Callable[[], Any]] = None

    def __post_init__(self):
        if self.default_factory and self.default is not None:
            raise ValueError("Cannot specify both default and default_factory")
        if self.default_factory and self.required:
            # A factory implies a default, so it's not required
            self.required = False

    def get_default(self) -> Any:
        if self.default_factory is not None:
            return self.default_factory()
        return self.default


class MetaDictMeta(type):
    """Metaclass that collects field definitions from class attributes."""
    def __new__(cls, name, bases, dct):
        # Collect fields from class-level Field instances
        fields = {}
        for key, value in list(dct.items()):
            if isinstance(value, Field):
                fields[key] = value
                # Remove from class attributes to avoid conflicts
                del dct[key]
        dct['_fields'] = fields
        return super().__new__(cls, name, bases, dct)


class MetaDict(dict, metaclass=MetaDictMeta):
    """
    A dictionary with a metadata schema. Fields are defined as class attributes
    with Field objects. Supports validation, type coercion, and nested structures.
    """

    _fields: Dict[str, Field] = {}  # Will be populated by metaclass

    def __init__(self, *args, **kwargs):
        # Prepare initial data from args/kwargs
        data = dict(*args, **kwargs) if args else {}
        data.update(kwargs)

        # Perform validation and store
        super().__init__()
        self._internal = {}  # internal storage to avoid triggering validation loop

        # Set defaults for missing fields
        for key, field in self._fields.items():
            if key not in data:
                if field.required:
                    raise ValueError(f"Missing required field '{key}'")
                # Set default
                self._internal[key] = field.get_default()
            else:
                self._internal[key] = None  # placeholder, will be set via __setitem__

        # Now set the provided values, which triggers validation
        for key, value in data.items():
            self[key] = value

        # Check for any extra fields not defined if we want strict mode? We'll allow extras by default.
        # But we could add a config option later.

    def __getitem__(self, key):
        # Check alias
        key = self._resolve_alias(key)
        if key in self._internal:
            return self._internal[key]
        raise KeyError(key)

    def __setitem__(self, key, value):
        key = self._resolve_alias(key)
        field = self._fields.get(key)
        if field is None:
            # Allow arbitrary fields? We'll allow, but we could raise.
            # For now, we allow extras without metadata.
            self._internal[key] = value
            return

        # Validate and convert
        converted = self._validate_and_convert(key, value, field)
        self._internal[key] = converted

    def __delitem__(self, key):
        key = self._resolve_alias(key)
        if key in self._internal:
            del self._internal[key]
        else:
            raise KeyError(key)

    def __getattr__(self, key):
        # Attribute access: try to get from dict
        if key in self._internal:
            return self._internal[key]
        # For methods or other attributes, fallback to normal
        raise AttributeError(f"'MetaDict' object has no attribute '{key}'")

    def __setattr__(self, key, value):
        # Avoid recursion for internal attributes
        if key.startswith('_') or key in ('_fields', '_internal'):
            super().__setattr__(key, value)
        else:
            # Treat as item assignment
            self[key] = value

    def __delattr__(self, key):
        if key in self._internal:
            del self[key]
        else:
            super().__delattr__(key)

    def __iter__(self):
        return iter(self._internal)

    def __len__(self):
        return len(self._internal)

    def __contains__(self, key):
        key = self._resolve_alias(key)
        return key in self._internal

    def _resolve_alias(self, key: str) -> str:
        """Return the canonical field name for an alias, or the key itself."""
        for fname, field in self._fields.items():
            if field.alias == key:
                return fname
        return key

    def _validate_and_convert(self, key: str, value: Any, field: Field) -> Any:
        """Apply type conversion and validator."""
        # Type conversion
        if field.type is not None:
            # If type is a MetaDict subclass, instantiate it
            if isinstance(field.type, type) and issubclass(field.type, MetaDict):
                if not isinstance(value, MetaDict) and not isinstance(value, dict):
                    raise ValidationError(key, value, f"Expected dict or MetaDict, got {type(value).__name__}")
                # If it's already a MetaDict of correct type, use it, else instantiate
                if isinstance(value, field.type):
                    converted = value
                else:
                    converted = field.type(value)
            else:
                # Handle generic types like List[int], Optional[str]
                origin = get_origin(field.type)
                if origin is not None:
                    # For List, we could attempt conversion for each element, but keep simple
                    # For now, just check if value is instance of the origin (list, etc.)
                    if not isinstance(value, origin):
                        try:
                            converted = field.type(value)  # attempt coercion
                        except (TypeError, ValueError):
                            raise ValidationError(key, value, f"Expected {field.type}, got {value}")
                    else:
                        converted = value
                else:
                    # Simple type
                    if not isinstance(value, field.type):
                        try:
                            converted = field.type(value)
                        except (TypeError, ValueError):
                            raise ValidationError(key, value, f"Expected {field.type.__name__}, got {type(value).__name__}")
                    else:
                        converted = value
        else:
            converted = value

        # Validator
        if field.validator is not None:
            if not field.validator(converted):
                raise ValidationError(key, converted, "Validator failed")

        return converted

    def to_dict(self, recursive: bool = True) -> Dict[str, Any]:
        """Export to plain dict. If recursive, convert nested MetaDicts."""
        result = {}
        for key, value in self._internal.items():
            if recursive and isinstance(value, MetaDict):
                result[key] = value.to_dict(recursive=True)
            else:
                result[key] = value
        return result

    def to_json(self, **kwargs) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MetaDict:
        """Create a MetaDict instance from a plain dict."""
        return cls(data)

    @classmethod
    def from_json(cls, json_str: str, **kwargs) -> MetaDict:
        """Create a MetaDict from a JSON string."""
        data = json.loads(json_str, **kwargs)
        return cls.from_dict(data)

    def __repr__(self):
        return f"{self.__class__.__name__}({self.to_dict()})"

    def __str__(self):
        return str(self.to_dict())


