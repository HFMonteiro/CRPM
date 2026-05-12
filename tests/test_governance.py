import pytest

from crpm.governance import build_governance_context, get_domain_template, get_privacy_mode, redact_identifier


def test_privacy_modes_define_redaction_posture() -> None:
    public_mode = get_privacy_mode("public_demo")
    restricted_mode = get_privacy_mode("restricted_health_adjacent")

    assert public_mode.case_id_policy == "synthetic_or_aliased"
    assert restricted_mode.case_id_policy == "aliased_only"
    assert public_mode.allows_raw_records is False
    assert restricted_mode.allows_raw_records is False


def test_redact_identifier_is_stable_and_does_not_leak_raw_value() -> None:
    redacted = redact_identifier("patient-12345", prefix="case")

    assert redacted.startswith("case-")
    assert "patient" not in redacted
    assert "12345" not in redacted
    assert redacted == redact_identifier("patient-12345", prefix="case")


def test_domain_template_documents_ccr_first_event_default() -> None:
    template = get_domain_template("ccr_screening")

    assert template.default_first_event_gate == "Invitation"
    assert template.non_clinical_scope is True
    assert "colorectal cancer screening" in template.description.lower()


def test_governance_context_is_json_safe_and_rejects_unknown_values() -> None:
    context = build_governance_context(privacy_mode="restricted_health_adjacent", domain_template="ccr_screening")

    assert context["privacy_mode"] == "restricted_health_adjacent"
    assert context["domain_template"] == "ccr_screening"
    assert context["non_clinical_scope"] is True

    with pytest.raises(ValueError):
        build_governance_context(privacy_mode="unknown", domain_template="ccr_screening")
    with pytest.raises(ValueError):
        build_governance_context(privacy_mode="public_demo", domain_template="unknown")
