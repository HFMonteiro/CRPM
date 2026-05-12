import json

import pandas as pd
import pytest

from crpm.config_schema import validate_analysis_config
from crpm.run_manifest import build_run_manifest, manifest_to_json


def test_analysis_config_validates_privacy_and_domain_template() -> None:
    config = validate_analysis_config(
        {
            "source": {"type": "xes", "path": "examples/screening_conformance_demo.xes"},
            "governance": {"privacy_mode": "restricted_health_adjacent", "domain_template": "ccr_screening"},
        }
    )

    assert config.governance.privacy_mode == "restricted_health_adjacent"
    assert config.governance.domain_template == "ccr_screening"

    with pytest.raises(ValueError):
        validate_analysis_config(
            {
                "source": {"type": "xes", "path": "examples/screening_conformance_demo.xes"},
                "governance": {"privacy_mode": "raw_export"},
            }
        )


def test_run_manifest_includes_governance_context_without_identifiers() -> None:
    manifest = build_run_manifest(
        input_name=r"C:\Analyst\Private\redacted_cohort.xes",
        log_signature="source-signature-without-identifiers",
        source_metadata={"source_type": "XES", "display_name": r"C:\Analyst\Private\redacted_cohort.xes"},
        analysis_signature="analysis",
        filter_key="filter",
        workflow_cohort_policy="first_event_direct",
        start_filter="Invitation",
        date_filter_mode="case",
        start_date=None,
        end_date=None,
        selected_algorithms=["Inductive (IMf)"],
        enable_train_test=False,
        random_seed=42,
        followup_days=None,
        split_info={},
        analysis_summary={},
        denominator_registry={},
        log_quality={},
        stage_timings={},
        comparison_df=pd.DataFrame(),
        governance_context={"privacy_mode": "restricted_health_adjacent", "domain_template": "ccr_screening"},
    )
    payload = manifest_to_json(manifest)

    assert manifest["governance"]["privacy_mode"] == "restricted_health_adjacent"
    assert manifest["governance"]["domain_template"] == "ccr_screening"
    assert r"C:\Analyst\Private" not in payload
    assert "redacted_cohort.xes" in payload


def test_readme_documents_governance_and_headless_config() -> None:
    readme = json.dumps(open("README.md", encoding="utf-8").read())

    assert "Headless Batch Config" in readme
    assert "privacy_mode" in readme
    assert "domain_template" in readme
