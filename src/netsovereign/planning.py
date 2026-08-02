"""Pure, provider-neutral sovereign change admission and reconciliation planning."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import Field

from .base import DomainModel
from .manifest import build_manifest
from .specification import WorldSpec
from .validation import has_errors, validate_spec


class ChangeClassification(StrEnum):
    CANONICAL_INTENT = "canonical_intent"
    CAPABILITY = "capability"
    PROVIDER_BINDING = "provider_binding"
    OBSERVED_DRIFT = "observed_drift"


class ChangeOperation(StrEnum):
    ADD = "add"
    MODIFY = "modify"
    REMOVE = "remove"


class Risk(StrEnum):
    LOW = "low"
    GOVERNED = "governed"
    AUTONOMY_REGRESSION = "autonomy_regression"
    EXTERNAL_DEPENDENCY = "external_dependency"
    TRUST = "trust"
    EXPOSURE = "exposure"


class ObservedFact(DomainModel):
    """A non-canonical observation addressed by a stable semantic path."""

    path: str
    value: Any


class ObservedStateSnapshot(DomainModel):
    api_version: str = Field(default="netsovereign.io/observed/v0.2", alias="apiVersion")
    world_id: str
    observed_at: datetime
    provenance: str
    facts: list[ObservedFact] = Field(default_factory=list)


class AcceptedWorldRevision(DomainModel):
    world_id: str
    revision: str
    parent_revision: str | None = None
    world_digest: str
    manifest_digest: str


class Change(DomainModel):
    id: str
    classification: ChangeClassification
    operation: ChangeOperation
    path: str
    subject_id: str | None = None
    before: Any = None
    after: Any = None
    authority_id: str | None = None
    mandate_id: str | None = None
    risk: Risk = Risk.LOW
    approval_required: bool = False
    explanation: str


class AdmissionIssue(DomainModel):
    code: str
    message: str
    path: str


class AdmissionDecision(DomainModel):
    api_version: str = "netsovereign.io/admission/v0.2"
    admitted: bool
    current: AcceptedWorldRevision
    proposed: AcceptedWorldRevision
    changes: list[Change]
    drift: list[Change]
    issues: list[AdmissionIssue]
    approval_gates: list[str]
    explanation: str


class PlanStep(DomainModel):
    id: str
    change_id: str
    action: str
    target: str
    depends_on: list[str] = Field(default_factory=list)
    preconditions: list[str]
    expected_outcomes: list[str]
    reversible: bool
    authority_id: str | None = None
    mandate_id: str | None = None


class ReconciliationPlan(DomainModel):
    api_version: str = "netsovereign.io/plan/v0.2"
    world_id: str
    from_revision: str
    to_revision: str
    admitted: bool
    plan_digest: str
    steps: list[PlanStep]
    drift: list[Change]
    approval_gates: list[str]
    execution: str = "not_permitted"
    explanation: str = "Provider-neutral plan only; no infrastructure was touched."


_SET_LIKE_LIST_FIELDS = {
    "accepted_audiences",
    "actions",
    "authority_exports",
    "claims",
    "controls",
    "dns_suffixes",
    "egress",
    "ingress",
    "mail_domains",
    "resource_classes",
    "resources",
}


def _normalise(value: Any, path: tuple[str, ...] = ()) -> Any:
    """Normalise maps and domain sets without changing JSON-array semantics.

    In particular, arrays below a provider binding's free-form ``configuration`` are
    deliberately order-sensitive.
    """

    if isinstance(value, dict):
        return {key: _normalise(value[key], (*path, key)) for key in sorted(value)}
    if isinstance(value, list):
        items = [_normalise(item, (*path, "[]")) for item in value]
        in_provider_configuration = "configuration" in path and any(
            part in {"providerBindings", "provider_bindings"} for part in path
        )
        collection_is_set = bool(path) and (
            path[-1] in _COLLECTIONS
            or path[-1] in {"providerBindings", "externalDependencies"}
            or path[-1] in _SET_LIKE_LIST_FIELDS
            or path[-1] in {"peers", "authority_imports", "mirrors"}
        )
        if collection_is_set and not in_provider_configuration:
            return sorted(
                items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"))
            )
        return items
    return value


def canonical_json(value: Any) -> str:
    """Return stable JSON independent of declaration ordering and formatting."""

    if isinstance(value, DomainModel):
        value = value.model_dump(mode="json", by_alias=True)
    return json.dumps(_normalise(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode()).hexdigest()


def accepted_revision(spec: WorldSpec, parent_revision: str | None = None) -> AcceptedWorldRevision:
    diagnostics = validate_spec(spec)
    manifest_value: Any = (
        {"invalid_world": spec.model_dump(mode="json")}
        if has_errors(diagnostics)
        else build_manifest(spec)
    )
    return AcceptedWorldRevision(
        world_id=spec.world.id,
        revision=spec.world.revision,
        parent_revision=parent_revision,
        world_digest=digest(spec),
        manifest_digest=digest(manifest_value),
    )


_COLLECTIONS = (
    "institutions",
    "authorities",
    "mandates",
    "resources",
    "registrations",
    "allocations",
    "grants",
    "delegations",
    "capabilities",
    "provider_bindings",
    "external_dependencies",
)


def _key(collection: str, item: dict[str, Any]) -> str:
    if collection == "provider_bindings":
        return str(item["capability"])
    return str(item["id"])


def _classification(path: str) -> ChangeClassification:
    if path.startswith("capabilities/"):
        return ChangeClassification.CAPABILITY
    if path.startswith("provider_bindings/"):
        return ChangeClassification.PROVIDER_BINDING
    return ChangeClassification.CANONICAL_INTENT


def _authority_for(spec: WorldSpec, collection: str, item: dict[str, Any]) -> str | None:
    if collection == "authorities":
        return next((a.id for a in spec.authorities if a.kind == "world_root"), None)
    for field in ("authority_id", "authority", "from_authority_id", "registry_authority_id"):
        if item.get(field):
            return str(item[field])
    if collection in {"institutions", "capabilities", "external_dependencies"}:
        roots = [a.id for a in spec.authorities if a.kind == "world_root"]
        return roots[0] if roots else None
    return None


def _governed_dimensions(
    spec: WorldSpec,
    collection: str,
    path: str,
    operation: ChangeOperation,
    item: Any,
) -> tuple[str, list[str], str]:
    """Derive mandate action, resource classes, and jurisdiction for a change."""

    action = "revoke" if operation == ChangeOperation.REMOVE else "declare"
    resource_classes: list[str] = []
    if collection == "resources" and isinstance(item, dict) and item.get("resource_class"):
        resource_classes = [str(item["resource_class"])]
    elif collection == "registrations":
        action, resource_classes = "admit", ["registration"]
    elif collection == "allocations" and isinstance(item, dict):
        action, resource_classes = (
            "allocate",
            [
                next(
                    (
                        str(resource.resource_class)
                        for resource in spec.resources
                        if resource.id == item.get("resource_id")
                    ),
                    "number",
                )
            ],
        )
    elif collection == "grants":
        action = "delegate"
    elif collection in {"delegations", "mandates"} and isinstance(item, dict):
        action, resource_classes = (
            "delegate",
            [str(value) for value in item.get("resource_classes", [])],
        )
    elif collection == "institutions":
        action, resource_classes = "admit", ["organisation"]
    elif collection in {"authorities", "capabilities", "external_dependencies"}:
        resource_classes = ["world"]
    elif path.startswith("boundary/"):
        action, resource_classes = (
            ("expose", ["route"]) if "exposed" in canonical_json(item) else ("route", ["route"])
        )
    elif path.startswith(("autonomy/", "world/")):
        resource_classes = ["world"]
    return action, resource_classes, spec.world.id


def _constraints_allow(
    constraints: dict[str, Any], operation: ChangeOperation, path: str, subject: str | None
) -> bool:
    """Evaluate the generic constraint vocabulary; unknown constraints fail closed."""

    known = {"operations", "paths", "subject_ids"}
    if set(constraints) - known:
        return False
    if constraints.get("operations") and str(operation) not in constraints["operations"]:
        return False
    if constraints.get("paths") and path not in constraints["paths"]:
        return False
    return not constraints.get("subject_ids") or subject in constraints["subject_ids"]


def _mandate_for(
    spec: WorldSpec,
    authority_id: str | None,
    action: str,
    resource_classes: list[str],
    jurisdiction: str,
    operation: ChangeOperation,
    path: str,
    subject: str | None,
    observed_at: datetime | None = None,
) -> str | None:
    """Select an active mandate applicable to every governed dimension."""

    candidates: list[str] = []
    for mandate in spec.mandates:
        if mandate.authority_id != authority_id or mandate.status != "active":
            continue
        if action not in mandate.actions or not set(resource_classes) <= set(
            mandate.resource_classes
        ):
            continue
        if mandate.jurisdiction not in {jurisdiction, "*"}:
            continue
        if mandate.validity:
            if observed_at is None:
                continue
            if mandate.validity.not_before and observed_at < mandate.validity.not_before:
                continue
            if mandate.validity.not_after and observed_at > mandate.validity.not_after:
                continue
        if not _constraints_allow(mandate.constraints, operation, path, subject):
            continue
        candidates.append(mandate.id)
    return sorted(candidates)[0] if candidates else None


def compare_worlds(
    current: WorldSpec, proposed: WorldSpec, evaluated_at: datetime | None = None
) -> list[Change]:
    """Semantically compare declarations while keeping bindings out of canonical meaning."""

    before = current.model_dump(mode="json")
    after = proposed.model_dump(mode="json")
    changes: list[Change] = []

    def add(
        path: str,
        operation: ChangeOperation,
        old: Any,
        new: Any,
        subject: str | None = None,
        collection: str = "world",
    ) -> None:
        classification = _classification(path)
        authority = _authority_for(
            proposed if operation != ChangeOperation.REMOVE else current,
            collection,
            new if isinstance(new, dict) else old if isinstance(old, dict) else {},
        )
        authority_spec = proposed if operation != ChangeOperation.REMOVE else current
        if path.startswith("boundary/"):
            authority = next(
                (a.id for a in authority_spec.authorities if a.kind == "transit"), None
            )
        elif path.startswith(("autonomy/", "world/")):
            authority = next(
                (a.id for a in authority_spec.authorities if a.kind == "world_root"), None
            )
        governed_item = new if new is not None else old
        action, resource_classes, jurisdiction = _governed_dimensions(
            authority_spec, collection, path, operation, governed_item
        )
        mandate = _mandate_for(
            current,
            authority,
            action,
            resource_classes,
            jurisdiction,
            operation,
            path,
            subject,
            evaluated_at,
        )
        risk = (
            Risk.GOVERNED if classification == ChangeClassification.CANONICAL_INTENT else Risk.LOW
        )
        approval = risk != Risk.LOW
        if path == "autonomy/target" and old != new:
            risk, approval = Risk.AUTONOMY_REGRESSION, True
        if path.startswith("external_dependencies/") and operation != ChangeOperation.REMOVE:
            risk, approval = Risk.EXTERNAL_DEPENDENCY, bool((new or {}).get("required", True))
        if path.startswith("boundary/") and (
            "federat" in canonical_json(new) or "exposed" in canonical_json(new)
        ):
            risk, approval = (
                (Risk.TRUST if "federat" in canonical_json(new) else Risk.EXPOSURE),
                True,
            )
        ident = digest({"path": path, "operation": operation, "before": old, "after": new})[7:19]
        changes.append(
            Change(
                id=f"change-{ident}",
                classification=classification,
                operation=operation,
                path=path,
                subject_id=subject,
                before=old,
                after=new,
                authority_id=authority,
                mandate_id=mandate,
                risk=risk,
                approval_required=approval,
                explanation=f"{operation.value.title()} {path} ({classification.value}).",
            )
        )

    # World metadata (revision is lineage metadata, not an institutional change).
    for field in ("id", "name", "lifecycle", "description"):
        if before["world"].get(field) != after["world"].get(field):
            add(
                f"world/{field}",
                ChangeOperation.MODIFY,
                before["world"].get(field),
                after["world"].get(field),
            )
    if before["autonomy"] != after["autonomy"]:
        for field in sorted(set(before["autonomy"]) | set(after["autonomy"])):
            if before["autonomy"].get(field) != after["autonomy"].get(field):
                add(
                    f"autonomy/{field}",
                    ChangeOperation.MODIFY,
                    before["autonomy"].get(field),
                    after["autonomy"].get(field),
                )
    for collection in _COLLECTIONS:
        old_items = {_key(collection, item): item for item in before[collection]}
        new_items = {_key(collection, item): item for item in after[collection]}
        for item_id in sorted(set(old_items) | set(new_items)):
            path = f"{collection}/{item_id}"
            if item_id not in old_items:
                add(path, ChangeOperation.ADD, None, new_items[item_id], item_id, collection)
            elif item_id not in new_items:
                add(path, ChangeOperation.REMOVE, old_items[item_id], None, item_id, collection)
            elif _normalise(old_items[item_id], (collection, item_id)) != _normalise(
                new_items[item_id], (collection, item_id)
            ):
                add(
                    path,
                    ChangeOperation.MODIFY,
                    old_items[item_id],
                    new_items[item_id],
                    item_id,
                    collection,
                )
    for field in sorted(set(before["boundary"]) | set(after["boundary"])):
        if _normalise(before["boundary"].get(field)) != _normalise(after["boundary"].get(field)):
            add(
                f"boundary/{field}",
                ChangeOperation.MODIFY,
                before["boundary"].get(field),
                after["boundary"].get(field),
            )
    return sorted(changes, key=lambda change: (change.path, change.operation))


def _resolve_semantic_path(document: Any, path: str) -> Any:
    """Resolve list members by stable ``id`` (or binding capability), never position alone."""

    value = document
    segments = path.strip("/").split("/")
    for index, part in enumerate(segments):
        if isinstance(value, list):
            collection = segments[index - 1] if index else ""
            key = "capability" if collection in {"providerBindings", "provider_bindings"} else "id"
            value = next(
                item for item in value if isinstance(item, dict) and str(item.get(key)) == part
            )
        else:
            value = value[part]
    return value


def _observed_drift(proposed: WorldSpec, observed: ObservedStateSnapshot | None) -> list[Change]:
    if observed is None:
        return []
    declared = proposed.model_dump(mode="json")
    drift: list[Change] = []
    for fact in sorted(observed.facts, key=lambda item: item.path):
        try:
            value = _resolve_semantic_path(declared, fact.path)
        except (KeyError, StopIteration, TypeError):
            value = None
        if _normalise(value) != _normalise(fact.value):
            drift.append(
                Change(
                    id=f"drift-{digest(fact.model_dump(mode='json'))[7:19]}",
                    classification=ChangeClassification.OBSERVED_DRIFT,
                    operation=ChangeOperation.MODIFY,
                    path=fact.path,
                    before=fact.value,
                    after=value,
                    explanation=f"Observed evidence from {observed.provenance} differs from declared intent.",
                )
            )
    return drift


def admit_change(
    current: WorldSpec, proposed: WorldSpec, observed: ObservedStateSnapshot | None = None
) -> AdmissionDecision:
    changes = compare_worlds(current, proposed, observed.observed_at if observed else None)
    issues: list[AdmissionIssue] = []
    if current.world.id != proposed.world.id:
        issues.append(
            AdmissionIssue(
                code="world_id_changed",
                path="world/id",
                message="A world ID cannot be changed in place.",
            )
        )
    if current.world.revision == proposed.world.revision and changes:
        issues.append(
            AdmissionIssue(
                code="revision_not_advanced",
                path="world/revision",
                message="A meaningful change requires a new revision.",
            )
        )
    for diagnostic in validate_spec(proposed):
        if diagnostic.severity == "error":
            issues.append(
                AdmissionIssue(
                    code=diagnostic.code, path=diagnostic.location, message=diagnostic.message
                )
            )
    for change in changes:
        if (
            change.operation == ChangeOperation.REMOVE
            and change.classification == ChangeClassification.CANONICAL_INTENT
        ):
            issues.append(
                AdmissionIssue(
                    code="implicit_deletion",
                    path=change.path,
                    message="Retire stable objects explicitly instead of deleting them.",
                )
            )
        if change.path.startswith("authorities/") and change.operation == ChangeOperation.MODIFY:
            old, new = change.before or {}, change.after or {}
            if old.get("kind") != new.get("kind") or old.get("scope") != new.get("scope"):
                issues.append(
                    AdmissionIssue(
                        code="authority_identity_redefined",
                        path=change.path,
                        message="A stable authority identity cannot silently change meaning.",
                    )
                )
            if (
                old.get("source") != new.get("source")
                and old.get("source") != "local"
                and new.get("source") == "local"
            ):
                issues.append(
                    AdmissionIssue(
                        code="import_became_local",
                        path=change.path,
                        message="Imported authority cannot be converted silently into local authority.",
                    )
                )
        if (
            change.path.startswith("resources/")
            and change.operation == ChangeOperation.MODIFY
            and (change.before or {}).get("resource_class")
            != (change.after or {}).get("resource_class")
        ):
            issues.append(
                AdmissionIssue(
                    code="resource_identity_redefined",
                    path=change.path,
                    message="A stable resource identity cannot silently change class.",
                )
            )
        governed = (
            change.classification == ChangeClassification.CANONICAL_INTENT
            and not change.path.startswith("world/")
        )
        if governed and not change.mandate_id and not change.path.startswith("mandates/"):
            issues.append(
                AdmissionIssue(
                    code="missing_applicable_mandate",
                    path=change.path,
                    message="No applicable active mandate permits this governed change.",
                )
            )
        if (
            change.path == "boundary/authority_imports"
            and "peered" in canonical_json(change.before)
            and "federated" in canonical_json(change.after)
        ):
            issues.append(
                AdmissionIssue(
                    code="peering_acquired_trust",
                    path=change.path,
                    message="Peering cannot acquire trust through an ordinary update.",
                )
            )
    if observed and observed.world_id != proposed.world.id:
        issues.append(
            AdmissionIssue(
                code="observed_world_mismatch",
                path="observed/world_id",
                message="Observed evidence belongs to another world.",
            )
        )
    gates = sorted(
        {
            f"approve:{str(change.risk)}:{change.id}"
            for change in changes
            if change.approval_required
        }
    )
    drift = _observed_drift(proposed, observed)
    admitted = not issues
    return AdmissionDecision(
        admitted=admitted,
        current=accepted_revision(current),
        proposed=accepted_revision(proposed, current.world.revision),
        changes=changes,
        drift=drift,
        issues=sorted(issues, key=lambda item: (item.path, item.code)),
        approval_gates=gates,
        explanation=(
            "Proposal is coherent and admitted subject to listed approvals."
            if admitted
            else "Proposal is rejected; resolve every admission issue before planning convergence."
        ),
    )


def build_plan(decision: AdmissionDecision) -> ReconciliationPlan:
    steps: list[PlanStep] = []
    if decision.admitted:
        convergence = [*decision.changes, *decision.drift]
        for index, change in enumerate(convergence, 1):
            step_id = f"step-{index:04d}"
            is_drift = change.classification == ChangeClassification.OBSERVED_DRIFT
            preconditions = [
                f"accepted revision is {decision.current.revision}",
                f"proposed world digest is {decision.proposed.world_digest}",
            ]
            if is_drift:
                preconditions.append(f"observed {change.path} still equals recorded evidence")
            if change.mandate_id:
                preconditions.append(f"mandate {change.mandate_id} remains active")
            if change.approval_required:
                preconditions.append(f"approval approve:{str(change.risk)}:{change.id} is recorded")
            steps.append(
                PlanStep(
                    id=step_id,
                    change_id=change.id,
                    action="reconcile_drift" if is_drift else str(change.operation),
                    target=change.path,
                    depends_on=[steps[-1].id] if steps else [],
                    preconditions=preconditions,
                    expected_outcomes=[
                        (
                            f"observed {change.path} converges to declared value"
                            if is_drift
                            else f"declared {change.path} equals the proposed revision"
                        )
                    ],
                    reversible=not is_drift and change.operation != ChangeOperation.REMOVE,
                    authority_id=change.authority_id,
                    mandate_id=change.mandate_id,
                )
            )
    payload = {
        "world": decision.proposed.world_id,
        "from": decision.current.revision,
        "to": decision.proposed.revision,
        "current_world_digest": decision.current.world_digest,
        "proposed_world_digest": decision.proposed.world_digest,
        "proposed_manifest_digest": decision.proposed.manifest_digest,
        "changes": [change.model_dump(mode="json") for change in decision.changes],
        "drift": [change.model_dump(mode="json") for change in decision.drift],
        "steps": [s.model_dump(mode="json") for s in steps],
    }
    return ReconciliationPlan(
        world_id=decision.proposed.world_id,
        from_revision=decision.current.revision,
        to_revision=decision.proposed.revision,
        admitted=decision.admitted,
        plan_digest=digest(payload),
        steps=steps,
        drift=decision.drift,
        approval_gates=decision.approval_gates,
    )
