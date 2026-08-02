"""NetSovereign deterministic CLI."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from pydantic import ValidationError

from .io import load_spec
from .manifest import build_manifest, explain_manifest
from .specification import WorldSpec
from .validation import has_errors, validate_spec

app = typer.Typer(no_args_is_help=True, help="Validate and explain sovereign world intent.")


def _parse(path: Path) -> WorldSpec:
    try:
        return load_spec(path)
    except (OSError, ValidationError, ValueError) as exc:
        typer.echo(f"STRUCTURE_ERROR {path}: {exc}", err=True)
        raise typer.Exit(2) from exc


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


if __name__ == "__main__":
    app()
