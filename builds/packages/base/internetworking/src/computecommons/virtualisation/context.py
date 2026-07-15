from __future__ import annotations

from dataclasses import dataclass

from computecommons.enums import IsolationKind


@dataclass(frozen=True, slots=True)
class ExecutionLayer:
    kind: IsolationKind
    technology: str | None = None
    provider: str | None = None
    identifier: str | None = None


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    layers: tuple[ExecutionLayer, ...]

    def __post_init__(self) -> None:
        if not self.layers:
            raise ValueError("execution context must contain at least one layer")
        object.__setattr__(self, "layers", tuple(self.layers))

    @property
    def is_virtualized(self) -> bool:
        return any(layer.kind is not IsolationKind.BARE_METAL for layer in self.layers)

    @property
    def innermost(self) -> ExecutionLayer:
        return self.layers[-1]
