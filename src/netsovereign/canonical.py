"""The single versioned canonical JSON contract used by every engine layer."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .base import DomainModel

CANONICALIZATION_PROFILE = "netsovereign.canonical-json/v1"
DIGEST_ALGORITHM = "sha256"

SET_LIKE_COLLECTIONS = {
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
    "providerBindings",
    "externalDependencies",
    "peers",
    "authority_imports",
    "mirrors",
}

SET_LIKE_FIELDS = {
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


def normalise(value: Any, path: tuple[str, ...] = ()) -> Any:
    """Normalise maps and declared sets while retaining ordered JSON arrays."""

    if isinstance(value, float) and (value != value or value in {float("inf"), float("-inf")}):
        raise ValueError("non-finite numbers are not canonical JSON")
    if isinstance(value, dict):
        return {key: normalise(value[key], (*path, key)) for key in sorted(value)}
    if isinstance(value, list):
        items = [normalise(item, (*path, "[]")) for item in value]
        in_provider_configuration = "configuration" in path and any(
            part in {"providerBindings", "provider_bindings"} for part in path
        )
        collection_is_set = bool(path) and (
            path[-1] in SET_LIKE_COLLECTIONS or path[-1] in SET_LIKE_FIELDS
        )
        if collection_is_set and not in_provider_configuration:
            return sorted(
                items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":"))
            )
        return items
    return value


def canonical_json(value: Any) -> str:
    """Return stable JSON under the NetSovereign v0.2 canonicalization profile."""

    if isinstance(value, DomainModel):
        value = value.model_dump(mode="json", by_alias=True)
    return json.dumps(
        normalise(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return DIGEST_ALGORITHM + ":" + hashlib.sha256(canonical_json(value).encode()).hexdigest()
