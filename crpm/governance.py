"""Governance, privacy-mode, and domain-template metadata for CRPM."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PrivacyMode:
    key: str
    label: str
    case_id_policy: str
    allows_raw_records: bool
    description: str


@dataclass(frozen=True)
class DomainTemplate:
    key: str
    label: str
    description: str
    default_first_event_gate: str
    semantic_profile: str
    non_clinical_scope: bool = True


PRIVACY_MODES: dict[str, PrivacyMode] = {
    "public_demo": PrivacyMode(
        key="public_demo",
        label="Public demo",
        case_id_policy="synthetic_or_aliased",
        allows_raw_records=False,
        description="For public screenshots, teaching demos, and synthetic sample data.",
    ),
    "internal_operational": PrivacyMode(
        key="internal_operational",
        label="Internal operational",
        case_id_policy="aliased_preferred",
        allows_raw_records=False,
        description="For local operational monitoring with privacy-safe summaries by default.",
    ),
    "restricted_health_adjacent": PrivacyMode(
        key="restricted_health_adjacent",
        label="Restricted health-adjacent",
        case_id_policy="aliased_only",
        allows_raw_records=False,
        description="For sensitive healthcare-adjacent logs where raw identifiers must not appear in outputs.",
    ),
}

DOMAIN_TEMPLATES: dict[str, DomainTemplate] = {
    "generic": DomainTemplate(
        key="generic",
        label="Generic process",
        description="Generic case-centric process mining template.",
        default_first_event_gate="",
        semantic_profile="generic",
    ),
    "ccr_screening": DomainTemplate(
        key="ccr_screening",
        label="CCR screening",
        description="Colorectal cancer screening pathway template for research and operational monitoring.",
        default_first_event_gate="Invitation",
        semantic_profile="ccr_screening",
    ),
}


def get_privacy_mode(key: str | None) -> PrivacyMode:
    """Return a supported privacy mode or raise a clear validation error."""

    normalized = (key or "restricted_health_adjacent").strip()
    try:
        return PRIVACY_MODES[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported privacy_mode: {normalized}") from exc


def get_domain_template(key: str | None) -> DomainTemplate:
    """Return a supported domain template or raise a clear validation error."""

    normalized = (key or "ccr_screening").strip()
    try:
        return DOMAIN_TEMPLATES[normalized]
    except KeyError as exc:
        raise ValueError(f"Unsupported domain_template: {normalized}") from exc


def redact_identifier(value: Any, *, prefix: str = "id") -> str:
    """Build a stable alias for a sensitive identifier without preserving the raw value."""

    digest = hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()[:10]
    return f"{prefix}-{digest}"


def build_governance_context(
    *,
    privacy_mode: str | None = "restricted_health_adjacent",
    domain_template: str | None = "ccr_screening",
) -> dict[str, Any]:
    """Build JSON-safe governance metadata for manifests and batch configs."""

    privacy = get_privacy_mode(privacy_mode)
    template = get_domain_template(domain_template)
    return {
        "privacy_mode": privacy.key,
        "privacy_label": privacy.label,
        "case_id_policy": privacy.case_id_policy,
        "allows_raw_records": privacy.allows_raw_records,
        "domain_template": template.key,
        "domain_label": template.label,
        "semantic_profile": template.semantic_profile,
        "default_first_event_gate": template.default_first_event_gate,
        "non_clinical_scope": template.non_clinical_scope,
    }


__all__ = [
    "DOMAIN_TEMPLATES",
    "PRIVACY_MODES",
    "DomainTemplate",
    "PrivacyMode",
    "build_governance_context",
    "get_domain_template",
    "get_privacy_mode",
    "redact_identifier",
]
