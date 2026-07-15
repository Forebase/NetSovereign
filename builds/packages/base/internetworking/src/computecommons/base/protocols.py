from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, TypeVar, runtime_checkable

T_co = TypeVar("T_co", covariant=True)


@runtime_checkable
class Identifiable(Protocol):
    @property
    def id(self) -> object: ...


@runtime_checkable
class Named(Protocol):
    @property
    def name(self) -> str | None: ...


@runtime_checkable
class Serializable(Protocol):
    def to_primitive(self) -> Mapping[str, Any]: ...


@runtime_checkable
class Parser(Protocol[T_co]):
    def parse(self, value: str) -> T_co: ...


@runtime_checkable
class Resolver(Protocol[T_co]):
    def resolve(self) -> T_co: ...


@runtime_checkable
class Detector(Protocol[T_co]):
    def detect(self) -> T_co | None: ...


@runtime_checkable
class Provider(Protocol[T_co]):
    def collect(self) -> T_co: ...
