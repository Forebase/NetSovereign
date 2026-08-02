"""NetSovereign deterministic CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import yaml
from pydantic import BaseModel, ValidationError

from .io import load_spec
from .manifest import build_manifest, explain_manifest
from .planning import ObservedStateSnapshot, admit_change, build_plan, compare_worlds
from .specification import WorldSpec
from .validation import has_errors, validate_spec

app = typer.Typer(no_args_is_help=True, help="Validate and explain sovereign world intent.")


def _parse(path: Path) -> WorldSpec:
    try:
        return load_spec(path)
    except (OSError, ValidationError, ValueError) as exc:
        typer.echo(f"STRUCTURE_ERROR {path}: {exc}", err=True)
        raise typer.Exit(2) from exc


def _observed(path: Path | None) -> ObservedStateSnapshot | None:
    if path is None:
        return None
    try:
        return ObservedStateSnapshot.model_validate(
            yaml.safe_load(path.read_text(encoding="utf-8"))
        )
    except (OSError, ValidationError, ValueError) as exc:
        typer.echo(f"OBSERVED_STRUCTURE_ERROR {path}: {exc}", err=True)
        raise typer.Exit(2) from exc


def _json(value: object) -> None:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    elif isinstance(value, list):
        value = [
            item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in value
        ]
    typer.echo(json.dumps(value, indent=2, sort_keys=True))


@app.command()
def validate(path: Path) -> None:
    """Structurally and semantically validate a world declaration."""
    diagnostics = validate_spec(_parse(path))
    for item in diagnostics:
        typer.echo(f"{str(item.severity).upper()} {item.code} {item.location}: {item.message}")
    if has_errors(diagnostics):
        raise typer.Exit(1)
    typer.echo(f"VALID {path} ({len(diagnostics)} warning(s))")


@app.command()
def manifest(path: Path) -> None:
    """Emit the deterministic provider-neutral world manifest as JSON."""
    spec = _parse(path)
    diagnostics = validate_spec(spec)
    if has_errors(diagnostics):
        typer.echo("semantic validation failed", err=True)
        raise typer.Exit(1)
    typer.echo(json.dumps(build_manifest(spec).model_dump(mode="json"), indent=2, sort_keys=True))


@app.command()
def explain(path: Path) -> None:
    """Explain world authority and assurance posture."""
    spec = _parse(path)
    if has_errors(validate_spec(spec)):
        typer.echo("semantic validation failed", err=True)
        raise typer.Exit(1)
    typer.echo(explain_manifest(build_manifest(spec)))


@app.command("diff")
def diff_command(current: Path, proposed: Path) -> None:
    """Emit a deterministic semantic change set; provider bindings remain separate."""
    _json(compare_worlds(_parse(current), _parse(proposed)))


@app.command()
def admit(
    current: Path, proposed: Path, observed: Annotated[Path | None, typer.Option()] = None
) -> None:
    """Evaluate declared authority and emit a stable admission decision."""
    decision = admit_change(_parse(current), _parse(proposed), _observed(observed))
    _json(decision)
    if not decision.admitted:
        raise typer.Exit(1)


@app.command()
def plan(
    current: Path, proposed: Path, observed: Annotated[Path | None, typer.Option()] = None
) -> None:
    """Emit a non-executable, provider-neutral convergence plan."""
    decision = admit_change(_parse(current), _parse(proposed), _observed(observed))
    _json(build_plan(decision))
    if not decision.admitted:
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
