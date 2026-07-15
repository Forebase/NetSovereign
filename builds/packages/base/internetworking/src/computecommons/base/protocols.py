from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

T_co = TypeVar("T_co", covariant=True)


@runtime_checkable
class Identifiable(Protocol):
    @property
    def id(self) -> object: ...


@runtime_checkable
class Named(Protocol):
    @property
    def name(self) -> str | None: ...


class Parser(Protocol[T_co]):
    def parse(self, value: str) -> T_co: ...


class Resolver(Protocol[T_co]):
    def resolve(self) -> T_co: ...


class Detector(Protocol[T_co]):
    def detect(self) -> T_co | None: ...


class Provider(Protocol[T_co]):
    def collect(self) -> T_co: ...
