"""Pure, provider-neutral sovereign change admission and reconciliation planning."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import Field, model_validator

from .authority import MandateConstraints, ResourceClass
from .base import DomainModel
from .canonical import canonical_json, digest
from .canonical import normalise as _normalise
from .manifest import build_manifest
from .specification import WorldSpec
from .validation import has_errors, validate_spec

__all__ = ["canonical_json", "digest"]


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


class GovernedAction(StrEnum):
    DECLARE = "declare"
    ADMIT = "admit"
    ALLOCATE = "allocate"
    DELEGATE = "delegate"
    REVOKE = "revoke"
    ROUTE = "route"
    EXPOSE = "expose"


class GovernanceRequirement(DomainModel):
    action: GovernedAction
    resource_classes: list[ResourceClass]
    jurisdiction: str


class AdmissionStatus(StrEnum):
    REJECTED = "rejected"
    PENDING_APPROVAL = "pending_approval"
    ADMITTED = "admitted"


class ApprovalEvidence(DomainModel):
    approval_id: str
    approved_at: datetime
    provenance: str


class ObservedFact(DomainModel):
    """A non-canonical observation addressed by a stable semantic path."""

    path: str
    status: Literal["present", "absent", "unknown", "unreadable"] = "present"
    value: Any = None
    observed_at: datetime | None = None
    provenance: str | None = None


class ObservedStateSnapshot(DomainModel):
    api_version: str = Field(default="netsovereign.io/observed/v0.2", alias="apiVersion")
    world_id: str
    observed_at: datetime
    provenance: str
    facts: list[ObservedFact] = Field(default_factory=list)

    @model_validator(mode="after")
    def coherent_snapshot(self) -> ObservedStateSnapshot:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        paths = [fact.path for fact in self.facts]
        if len(paths) != len(set(paths)):
            raise ValueError("observed fact paths must be unique")
        if any(fact.observed_at and fact.observed_at.tzinfo is None for fact in self.facts):
            raise ValueError("fact observed_at must include a timezone")
        return self


class AcceptedWorldRevision(DomainModel):
    world_id: str
    revision: str
    parent_revision: str | None = None
    declaration_digest: str
    canonical_intent_digest: str
    materialization_digest: str
    world_digest: str
    manifest_digest: str | None


class ParentRevisionReference(DomainModel):
    revision: str
    declaration_digest: str


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
    governance: GovernanceRequirement | None = None
    risk: Risk = Risk.LOW
    approval_required: bool = False
    actionable: bool = True
    explanation: str


class AdmissionIssue(DomainModel):
    code: str
    message: str
    path: str


class AdmissionDecision(DomainModel):
    api_version: str = "netsovereign.io/admission/v0.2"
    admitted: bool
    status: AdmissionStatus
    evaluated_at: datetime | None = None
    current: AcceptedWorldRevision
    proposed: AcceptedWorldRevision
    changes: list[Change]
    drift: list[Change]
    issues: list[AdmissionIssue]
    approval_gates: list[str]
    approvals: list[ApprovalEvidence] = Field(default_factory=list)
    explanation: str


class PredicateKind(StrEnum):
    ACCEPTED_REVISION_EQUALS = "accepted_revision_equals"
    PROPOSED_DIGEST_EQUALS = "proposed_digest_equals"
    OBSERVATION_EQUALS = "observation_equals"
    MANDATE_ACTIVE = "mandate_active"
    APPROVAL_PRESENT = "approval_present"


class PlanPredicate(DomainModel):
    kind: PredicateKind
    revision: str | None = None
    digest: str | None = None
    mandate_id: str | None = None
    approval_id: str | None = None
    path: str | None = None
    value_digest: str | None = None


class ExpectedOutcome(DomainModel):
    kind: Literal["semantic_path_equals"] = "semantic_path_equals"
    path: str
    value: Any
    value_digest: str


class Reversibility(StrEnum):
    REVERSIBLE = "reversible"
    CONDITIONALLY_REVERSIBLE = "conditionally_reversible"
    IRREVERSIBLE = "irreversible"
    UNKNOWN = "unknown"


class PlanStep(DomainModel):
    id: str
    change_id: str
    action: str
    target: str
    depends_on: list[str] = Field(default_factory=list)
    preconditions: list[PlanPredicate]
    expected_outcomes: list[ExpectedOutcome]
    reversible: bool
    reversibility: Reversibility
    reversibility_reason: str
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


def accepted_revision(spec: WorldSpec, parent_revision: str | None = None) -> AcceptedWorldRevision:
    diagnostics = validate_spec(spec)
    declaration = spec.model_dump(mode="json", by_alias=True)
    intent = {key: value for key, value in declaration.items() if key != "providerBindings"}
    intent["world"] = {key: value for key, value in intent["world"].items() if key != "revision"}
    materialization = {
        "capabilities": declaration["capabilities"],
        "providerBindings": declaration["providerBindings"],
    }
    declaration_digest = digest(declaration)
    return AcceptedWorldRevision(
        world_id=spec.world.id,
        revision=spec.world.revision,
        parent_revision=parent_revision,
        declaration_digest=declaration_digest,
        canonical_intent_digest=digest(intent),
        materialization_digest=digest(materialization),
        world_digest=declaration_digest,
        manifest_digest=None if has_errors(diagnostics) else digest(build_manifest(spec)),
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

_LIFECYCLE_TRANSITIONS = {
    "proposed": {"active", "retired"},
    "deferred": {"active", "retired"},
    "active": {"suspended", "retired"},
    "suspended": {"active", "retired"},
    "retired": set(),
}

_AUTONOMY_LEVEL = {
    "externally_dependent": 0,
    "partially_autonomous": 1,
    "authority_autonomous": 2,
}


def _lifecycle_status(collection: str, value: dict[str, Any]) -> str:
    if collection == "authorities":
        return str((value.get("lifecycle") or {}).get("status", "active"))
    return str(value.get("status", "active"))


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
) -> GovernanceRequirement:
    """Derive mandate action, resource classes, and jurisdiction for a change."""

    action = (
        GovernedAction.REVOKE if operation == ChangeOperation.REMOVE else GovernedAction.DECLARE
    )
    retiring = (path == "world/lifecycle" and item == "retired") or (
        isinstance(item, dict)
        and (
            item.get("status") == "retired"
            or (item.get("lifecycle") or {}).get("status") == "retired"
        )
    )
    if retiring:
        action = GovernedAction.REVOKE
    resource_classes: list[ResourceClass] = []
    if collection == "resources" and isinstance(item, dict) and item.get("resource_class"):
        resource_classes = [ResourceClass(item["resource_class"])]
    elif collection == "registrations":
        action, resource_classes = GovernedAction.ADMIT, [ResourceClass.REGISTRATION]
    elif collection == "allocations" and isinstance(item, dict):
        action, resource_classes = (
            GovernedAction.ALLOCATE,
            [
                next(
                    (
                        ResourceClass(resource.resource_class)
                        for resource in spec.resources
                        if resource.id == item.get("resource_id")
                    ),
                    ResourceClass.NUMBER,
                )
            ],
        )
    elif collection == "grants":
        action = GovernedAction.DELEGATE
    elif collection in {"delegations", "mandates"} and isinstance(item, dict) and not retiring:
        action, resource_classes = (
            GovernedAction.DELEGATE,
            [ResourceClass(value) for value in item.get("resource_classes", [])],
        )
    elif collection == "institutions" and not retiring:
        action, resource_classes = GovernedAction.ADMIT, [ResourceClass.ORGANISATION]
    elif collection in {"authorities", "capabilities", "external_dependencies"}:
        resource_classes = [ResourceClass.WORLD]
    elif path.startswith("boundary/"):
        action, resource_classes = (
            (GovernedAction.EXPOSE, [ResourceClass.ROUTE])
            if path == "boundary/real_internet" and item == "exposed"
            else (GovernedAction.ROUTE, [ResourceClass.ROUTE])
        )
    elif path.startswith(("autonomy/", "world/")):
        resource_classes = [ResourceClass.WORLD]
    return GovernanceRequirement(
        action=action, resource_classes=resource_classes, jurisdiction=spec.world.id
    )


def _constraints_allow(
    constraints: MandateConstraints,
    operation: ChangeOperation,
    path: str,
    subject: str | None,
) -> bool:
    """Evaluate the versioned, provider-neutral mandate constraints."""

    if constraints.operations and str(operation) not in constraints.operations:
        return False
    if constraints.paths and path not in constraints.paths:
        return False
    return not constraints.subject_ids or subject in constraints.subject_ids


def _mandate_for(
    spec: WorldSpec,
    authority_id: str | None,
    requirement: GovernanceRequirement,
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
        if requirement.action not in mandate.actions or not set(
            requirement.resource_classes
        ) <= set(mandate.resource_classes):
            continue
        if mandate.jurisdiction not in {requirement.jurisdiction, "*"}:
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
        governance = _governed_dimensions(
            authority_spec, collection, path, operation, governed_item
        )
        mandate = _mandate_for(
            current,
            authority,
            governance,
            operation,
            path,
            subject,
            evaluated_at,
        )
        risk = (
            Risk.GOVERNED if classification == ChangeClassification.CANONICAL_INTENT else Risk.LOW
        )
        approval = risk != Risk.LOW
        if path == "autonomy/target" and _AUTONOMY_LEVEL[str(new)] < _AUTONOMY_LEVEL[str(old)]:
            risk, approval = Risk.AUTONOMY_REGRESSION, True
        if path.startswith("external_dependencies/") and operation != ChangeOperation.REMOVE:
            risk, approval = Risk.EXTERNAL_DEPENDENCY, bool((new or {}).get("required", True))
        federated_import = path == "boundary/authority_imports" and any(
            item.get("mode") == "federated" for item in (new or [])
        )
        if (path == "boundary/cross_world" and new == "federated") or federated_import:
            risk, approval = Risk.TRUST, True
        if path == "boundary/real_internet" and new == "exposed":
            risk, approval = Risk.EXPOSURE, True
        ident = digest({"path": path, "operation": operation, "before": old, "after": new})
        changes.append(
            Change(
                id=f"change-{ident[7:]}",
                classification=classification,
                operation=operation,
                path=path,
                subject_id=subject,
                before=old,
                after=new,
                authority_id=authority,
                mandate_id=mandate,
                governance=(
                    governance if classification == ChangeClassification.CANONICAL_INTENT else None
                ),
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
        if fact.status in {"unknown", "unreadable"}:
            continue
        declared_exists = True
        try:
            value = _resolve_semantic_path(declared, fact.path)
        except (KeyError, StopIteration, TypeError):
            declared_exists = False
            value = None
        differs = fact.status == "absent" and declared_exists
        differs = differs or (
            fact.status == "present"
            and (not declared_exists or _normalise(value) != _normalise(fact.value))
        )
        if differs:
            collection = fact.path.strip("/").split("/", 1)[0]
            governed_item = value if isinstance(value, dict) else {}
            authority = _authority_for(proposed, collection, governed_item)
            if fact.path.startswith("boundary/"):
                authority = next((a.id for a in proposed.authorities if a.kind == "transit"), None)
            elif fact.path.startswith(("world/", "autonomy/")):
                authority = next(
                    (a.id for a in proposed.authorities if a.kind == "world_root"), None
                )
            governance = _governed_dimensions(
                proposed, collection, fact.path, ChangeOperation.MODIFY, value
            )
            mandate = _mandate_for(
                proposed,
                authority,
                governance,
                ChangeOperation.MODIFY,
                fact.path,
                fact.path.split("/", 2)[1] if "/" in fact.path else None,
                fact.observed_at or observed.observed_at,
            )
            evidence_value = {"status": "absent"} if fact.status == "absent" else fact.value
            provenance = fact.provenance or observed.provenance
            drift.append(
                Change(
                    id=f"drift-{digest(fact.model_dump(mode='json'))[7:]}",
                    classification=ChangeClassification.OBSERVED_DRIFT,
                    operation=(
                        ChangeOperation.ADD if fact.status == "absent" else ChangeOperation.MODIFY
                    ),
                    path=fact.path,
                    before=evidence_value,
                    after=value,
                    authority_id=authority,
                    mandate_id=mandate,
                    governance=governance,
                    actionable=declared_exists,
                    explanation=f"Observed evidence from {provenance} differs from declared intent.",
                )
            )
    return drift


def admit_change(
    current: WorldSpec,
    proposed: WorldSpec,
    observed: ObservedStateSnapshot | None = None,
    *,
    evaluated_at: datetime | None = None,
    approvals: list[ApprovalEvidence] | None = None,
    parent: ParentRevisionReference | None = None,
) -> AdmissionDecision:
    changes = compare_worlds(current, proposed, evaluated_at)
    issues: list[AdmissionIssue] = []
    for diagnostic in validate_spec(current):
        if diagnostic.severity == "error":
            issues.append(
                AdmissionIssue(
                    code=f"invalid_current_{diagnostic.code}",
                    path=diagnostic.location,
                    message=f"Accepted world is invalid: {diagnostic.message}",
                )
            )
    current_reference = accepted_revision(current)
    if parent and (
        parent.revision != current_reference.revision
        or parent.declaration_digest != current_reference.declaration_digest
    ):
        issues.append(
            AdmissionIssue(
                code="stale_parent_revision",
                path="proposal/parent",
                message="Proposal parent revision and digest do not match the accepted world.",
            )
        )
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
            identity_fields = ("kind", "scope", "operator_institution_id", "controls", "source")
            if any(
                _normalise(old.get(field)) != _normalise(new.get(field))
                for field in identity_fields
            ):
                issues.append(
                    AdmissionIssue(
                        code="authority_identity_redefined",
                        path=change.path,
                        message="A stable authority identity cannot silently change meaning.",
                    )
                )
            if old.get("source") != "local" and new.get("source") == "local":
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
            and any(
                (change.before or {}).get(field) != (change.after or {}).get(field)
                for field in ("resource_class", "authority_id")
            )
        ):
            issues.append(
                AdmissionIssue(
                    code="resource_identity_redefined",
                    path=change.path,
                    message="A stable resource identity cannot silently change class.",
                )
            )
        governed = change.classification == ChangeClassification.CANONICAL_INTENT
        if governed and not change.mandate_id:
            issues.append(
                AdmissionIssue(
                    code="missing_applicable_mandate",
                    path=change.path,
                    message="No applicable active mandate permits this governed change.",
                )
            )
        collection = change.path.split("/", 1)[0]
        if change.operation == ChangeOperation.MODIFY and collection in {
            "authorities",
            "institutions",
            "mandates",
        }:
            old_status = _lifecycle_status(collection, change.before or {})
            new_status = _lifecycle_status(collection, change.after or {})
            if old_status != new_status and new_status not in _LIFECYCLE_TRANSITIONS[old_status]:
                issues.append(
                    AdmissionIssue(
                        code="invalid_lifecycle_transition",
                        path=change.path,
                        message=f"Lifecycle transition {old_status} -> {new_status} is not permitted.",
                    )
                )
        if (
            change.path == "world/lifecycle"
            and str(change.after) not in _LIFECYCLE_TRANSITIONS[str(change.before)]
        ):
            issues.append(
                AdmissionIssue(
                    code="invalid_lifecycle_transition",
                    path=change.path,
                    message=f"Lifecycle transition {change.before} -> {change.after} is not permitted.",
                )
            )
        if (
            change.path == "boundary/authority_imports"
            and any(item.get("mode") == "peered" for item in (change.before or []))
            and any(item.get("mode") == "federated" for item in (change.after or []))
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
    supplied_approvals = sorted(approvals or [], key=lambda item: item.approval_id)
    approved_ids = {item.approval_id for item in supplied_approvals}
    outstanding_gates = [gate for gate in gates if gate not in approved_ids]
    drift = _observed_drift(proposed, observed)
    status = (
        AdmissionStatus.REJECTED
        if issues
        else AdmissionStatus.PENDING_APPROVAL
        if outstanding_gates
        else AdmissionStatus.ADMITTED
    )
    admitted = status == AdmissionStatus.ADMITTED
    return AdmissionDecision(
        admitted=admitted,
        status=status,
        evaluated_at=evaluated_at,
        current=current_reference,
        proposed=accepted_revision(proposed, current.world.revision),
        changes=changes,
        drift=drift,
        issues=sorted(issues, key=lambda item: (item.path, item.code)),
        approval_gates=outstanding_gates,
        approvals=supplied_approvals,
        explanation=(
            "Proposal is coherent, authorised, and admitted."
            if admitted
            else "Proposal is coherent and authorised but awaits required approval."
            if status == AdmissionStatus.PENDING_APPROVAL
            else "Proposal is rejected; resolve every admission issue before planning convergence."
        ),
    )


def _dependency_targets(change: Change) -> set[str]:
    """Return changed semantic targets that must converge before this change."""

    item = change.after if isinstance(change.after, dict) else {}
    collection = change.path.split("/", 1)[0]
    dependencies: set[str] = set()
    if collection == "authorities" and item.get("operator_institution_id"):
        dependencies.add(f"institutions/{item['operator_institution_id']}")
    elif collection == "mandates" and item.get("authority_id"):
        dependencies.add(f"authorities/{item['authority_id']}")
    elif collection == "resources":
        for field in ("authority_id", "registry_authority_id", "registrar_authority_id"):
            if item.get(field):
                dependencies.add(f"authorities/{item[field]}")
    elif collection == "registrations":
        if item.get("resource_id"):
            dependencies.add(f"resources/{item['resource_id']}")
        for field in ("registry_authority_id", "registrar_authority_id"):
            if item.get(field):
                dependencies.add(f"authorities/{item[field]}")
    elif collection == "allocations":
        if item.get("resource_id"):
            dependencies.add(f"resources/{item['resource_id']}")
        if item.get("authority_id"):
            dependencies.add(f"authorities/{item['authority_id']}")
    elif collection == "grants" and item.get("authority_id"):
        dependencies.add(f"authorities/{item['authority_id']}")
    elif collection == "delegations":
        for field in ("from_authority_id", "to_authority_id"):
            if item.get(field):
                dependencies.add(f"authorities/{item[field]}")
    elif collection == "provider_bindings" and item.get("capability"):
        dependencies.add(f"capabilities/{item['capability']}")
    return dependencies


def build_plan(decision: AdmissionDecision) -> ReconciliationPlan:
    steps: list[PlanStep] = []
    if decision.status != AdmissionStatus.REJECTED:
        convergence = [
            *decision.changes,
            *(change for change in decision.drift if change.actionable),
        ]
        step_ids = {change.id: f"step-{index:04d}" for index, change in enumerate(convergence, 1)}
        target_steps: dict[str, list[str]] = {}
        for change in convergence:
            target_steps.setdefault(change.path, []).append(step_ids[change.id])
        for index, change in enumerate(convergence, 1):
            step_id = f"step-{index:04d}"
            is_drift = change.classification == ChangeClassification.OBSERVED_DRIFT
            preconditions = [
                PlanPredicate(
                    kind=PredicateKind.ACCEPTED_REVISION_EQUALS,
                    revision=decision.current.revision,
                    digest=decision.current.declaration_digest,
                ),
                PlanPredicate(
                    kind=PredicateKind.PROPOSED_DIGEST_EQUALS,
                    digest=decision.proposed.declaration_digest,
                ),
            ]
            if is_drift:
                preconditions.append(
                    PlanPredicate(
                        kind=PredicateKind.OBSERVATION_EQUALS,
                        path=change.path,
                        value_digest=digest(change.before),
                    )
                )
            if change.mandate_id:
                preconditions.append(
                    PlanPredicate(
                        kind=PredicateKind.MANDATE_ACTIVE,
                        mandate_id=change.mandate_id,
                    )
                )
            if change.approval_required:
                preconditions.append(
                    PlanPredicate(
                        kind=PredicateKind.APPROVAL_PRESENT,
                        approval_id=f"approve:{str(change.risk)}:{change.id}",
                    )
                )
            reversibility = (
                Reversibility.IRREVERSIBLE
                if change.operation == ChangeOperation.REMOVE
                else Reversibility.CONDITIONALLY_REVERSIBLE
                if change.classification == ChangeClassification.PROVIDER_BINDING
                else Reversibility.UNKNOWN
            )
            dependency_ids = {
                dependency_step
                for target in _dependency_targets(change)
                for dependency_step in target_steps.get(target, [])
                if dependency_step != step_id
            }
            if is_drift:
                dependency_ids.update(
                    dependency_step
                    for dependency_step in target_steps.get(change.path, [])
                    if dependency_step != step_id
                )
            steps.append(
                PlanStep(
                    id=step_id,
                    change_id=change.id,
                    action="reconcile_drift" if is_drift else str(change.operation),
                    target=change.path,
                    depends_on=sorted(dependency_ids),
                    preconditions=preconditions,
                    expected_outcomes=[
                        ExpectedOutcome(
                            path=change.path,
                            value=change.after,
                            value_digest=digest(change.after),
                        )
                    ],
                    reversible=reversibility == Reversibility.CONDITIONALLY_REVERSIBLE,
                    reversibility=reversibility,
                    reversibility_reason=(
                        "Removal has no provider-neutral inverse."
                        if reversibility == Reversibility.IRREVERSIBLE
                        else "A prior replaceable binding can be restored if retained."
                        if reversibility == Reversibility.CONDITIONALLY_REVERSIBLE
                        else "v0.2 cannot prove runtime reversibility without a provider contract."
                    ),
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
