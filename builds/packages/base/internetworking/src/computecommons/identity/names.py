from __future__ import annotations

import re
from dataclasses import dataclass

_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True, order=True, slots=True)
class QualifiedName:
    namespace: str
    name: str

    def __post_init__(self) -> None:
        if not _SEGMENT.fullmatch(self.namespace):
            raise ValueError(f"Invalid namespace: {self.namespace!r}")
        if not _SEGMENT.fullmatch(self.name):
            raise ValueError(f"Invalid name: {self.name!r}")

    @classmethod
    def parse(cls, value: str) -> QualifiedName:
        namespace, separator, name = value.partition(":")
        if not separator:
            raise ValueError("Qualified names must use 'namespace:name'")
        return cls(namespace=namespace, name=name)

    def __str__(self) -> str:
        return f"{self.namespace}:{self.name}"
