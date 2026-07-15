from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, TypeVar, runtime_checkable

T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)


@runtime_checkable
class Identifiable(Protocol):
    id: object


@runtime_checkable
class Named(Protocol):
    name: str | None


@runtime_checkable
class Serializable(Protocol):
    def to_primitive(self) -> Mapping[str, Any]: ...


@runtime_checkable
class Parser(Protocol[T_co]):
    def parse(self, value: str) -> T_co: ...


@runtime_checkable
class Resolver(Protocol[T_contra, T_co]):
    def resolve(self, value: T_contra) -> T_co: ...


@runtime_checkable
class Detector(Protocol[T_co]):
    def detect(self) -> T_co | None: ...


@runtime_checkable
class Provider(Protocol[T_co]):
    """Structural provider contract for gathering base-layer values."""

    name: str

    def provide(self) -> T_co: ...
