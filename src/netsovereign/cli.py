"""NetSovereign deterministic CLI."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
import yaml
from pydantic import BaseModel, ValidationError

from .controlplane.repository import SQLiteControlPlaneRepository
from .io import load_spec
from .manifest import build_manifest, explain_manifest
from .planning import (
    ApprovalEvidence,
    ObservedStateSnapshot,
    ParentRevisionReference,
    ReconciliationPlan,
    admit_change,
    build_plan,
    compare_worlds,
)
from .providers.fake import FakeProvider
from .providers.registry import ProviderRegistry
from .runtime import InMemoryExecutionRepository, RuntimeExecutor, compile_plan, offline_demo_facts
from .specification import WorldSpec
from .validation import has_errors, validate_spec

app = typer.Typer(no_args_is_help=True, help="Validate and explain sovereign world intent.")
control_plane_app = typer.Typer(help="Operate the durable local control plane.")
app.add_typer(control_plane_app, name="control-plane")


@control_plane_app.command("init")
def control_plane_init(
    database: Annotated[Path, typer.Option(envvar="NETENGINE_CONTROL_PLANE_PATH")] = Path(
        ".netengine-control.db"
    ),
) -> None:
    """Initialise or inspect a local durable control-plane schema."""
    repository = SQLiteControlPlaneRepository(database)
    row = repository.connection.execute(
        "SELECT value FROM cp_metadata WHERE key='schema_version'"
    ).fetchone()
    repository.connection.close()
    _emit({"database": str(database), "schema_version": int(row[0]), "status": "ready"})


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


def _plain(value: object) -> object:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _emit(
    value: object,
    output_format: str = "json",
    compact: bool = False,
    output: Path | None = None,
) -> None:
    plain = _plain(value)
    if output_format == "json":
        rendered = json.dumps(plain, indent=None if compact else 2, sort_keys=True)
    elif output_format == "yaml":
        rendered = yaml.safe_dump(plain, sort_keys=True)
    else:
        typer.echo("output format must be json or yaml", err=True)
        raise typer.Exit(2)
    if output:
        output.write_text(rendered + ("" if rendered.endswith("\n") else "\n"), encoding="utf-8")
    else:
        typer.echo(rendered)


def _json(value: object) -> None:
    _emit(value)


def _approvals(paths: list[Path] | None) -> list[ApprovalEvidence]:
    evidence: list[ApprovalEvidence] = []
    for path in paths or []:
        try:
            evidence.append(
                ApprovalEvidence.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
            )
        except (OSError, ValidationError, ValueError) as exc:
            typer.echo(f"APPROVAL_STRUCTURE_ERROR {path}: {exc}", err=True)
            raise typer.Exit(2) from exc
    return evidence


def _parent(revision: str | None, declaration_digest: str | None) -> ParentRevisionReference | None:
    if bool(revision) != bool(declaration_digest):
        typer.echo("--parent-revision and --parent-digest must be supplied together", err=True)
        raise typer.Exit(2)
    if revision and declaration_digest:
        return ParentRevisionReference(revision=revision, declaration_digest=declaration_digest)
    return None


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
    current: Path,
    proposed: Path,
    observed: Annotated[Path | None, typer.Option()] = None,
    evaluated_at: Annotated[datetime | None, typer.Option()] = None,
    approval: Annotated[list[Path] | None, typer.Option("--approval")] = None,
    parent_revision: Annotated[str | None, typer.Option()] = None,
    parent_digest: Annotated[str | None, typer.Option()] = None,
    output_format: Annotated[str, typer.Option("--format")] = "json",
    compact: Annotated[bool, typer.Option()] = False,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Evaluate declared authority and emit a stable admission decision."""
    decision = admit_change(
        _parse(current),
        _parse(proposed),
        _observed(observed),
        evaluated_at=evaluated_at,
        approvals=_approvals(approval),
        parent=_parent(parent_revision, parent_digest),
    )
    _emit(decision, output_format, compact, output)
    if decision.status == "rejected":
        raise typer.Exit(1)
    if decision.status == "pending_approval":
        raise typer.Exit(3)


@app.command()
def plan(
    current: Path,
    proposed: Path,
    observed: Annotated[Path | None, typer.Option()] = None,
    evaluated_at: Annotated[datetime | None, typer.Option()] = None,
    approval: Annotated[list[Path] | None, typer.Option("--approval")] = None,
    parent_revision: Annotated[str | None, typer.Option()] = None,
    parent_digest: Annotated[str | None, typer.Option()] = None,
    output_format: Annotated[str, typer.Option("--format")] = "json",
    compact: Annotated[bool, typer.Option()] = False,
    output: Annotated[Path | None, typer.Option()] = None,
) -> None:
    """Emit a non-executable, provider-neutral convergence plan."""
    decision = admit_change(
        _parse(current),
        _parse(proposed),
        _observed(observed),
        evaluated_at=evaluated_at,
        approvals=_approvals(approval),
        parent=_parent(parent_revision, parent_digest),
    )
    _emit(build_plan(decision), output_format, compact, output)
    if decision.status == "rejected":
        raise typer.Exit(1)
    if decision.status == "pending_approval":
        raise typer.Exit(3)


@app.command("execute")
def execute_command(
    plan_file: Path,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Compile and execute an admitted plan through the in-memory fake provider."""
    try:
        intent_plan = ReconciliationPlan.model_validate(
            yaml.safe_load(plan_file.read_text(encoding="utf-8"))
        )
        registry = ProviderRegistry()
        registry.register(FakeProvider())
        executable = compile_plan(intent_plan, registry)
        report = asyncio.run(
            RuntimeExecutor(registry, InMemoryExecutionRepository()).execute(
                executable,
                dry_run=dry_run,
                facts=offline_demo_facts(executable, datetime.now(UTC)),
            )
        )
    except (OSError, ValidationError, ValueError) as exc:
        typer.echo(f"EXECUTION_ERROR {plan_file}: {exc}", err=True)
        raise typer.Exit(1) from exc
    _emit(report)


if __name__ == "__main__":
    app()
